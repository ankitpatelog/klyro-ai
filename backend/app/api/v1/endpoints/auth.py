import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis import get_redis
from app.core.security import decode_token, token_hash
from app.db.session import get_db
from app.models.user import User
from app.repositories.token_sessions import is_access_token_active
from app.repositories.users import get_user_by_id
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, RegisterResponse, TokenResponse
from app.services.auth_service import login_user, logout_user, refresh_user_tokens, register_user


router = APIRouter()
logger = logging.getLogger(__name__)
bearer_scheme = HTTPBearer(auto_error=False)

# set both token in the cookies in the / path ie main landing page
def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    cookie_options = {
        "httponly": True,
        "secure": settings.COOKIE_SECURE,
        "samesite": settings.COOKIE_SAMESITE,
        "path": "/",
    }
    response.set_cookie("access_token", access_token, max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 24 * 60 * 60, **cookie_options)
    response.set_cookie("refresh_token", refresh_token, max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60, **cookie_options)


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")


async def _active_user(db: AsyncSession, user_id: str) -> User:
    user = await get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account is inactive")
    return user


# used inside the protected route to check the available access token is valid or not for the current user
async def get_current_user(
    request: Request,
    response: Response,
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> User:
    """Validate access JWT + Redis hash, falling back to refresh-token rotation."""
    access_token = credentials.credentials if credentials else request.cookies.get("access_token")
    if access_token:
        try:
            access_payload = decode_token(access_token, "access")
            is_active = await is_access_token_active(
                redis,
                access_payload["jti"],
                access_payload["sub"],
                token_hash(access_token),
            )
            if is_active:
                return await _active_user(db, access_payload["sub"])
        except HTTPException:
            pass

    refresh_token = request.cookies.get("refresh_token")
    
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    try:
        new_access_token, new_refresh_token = await refresh_user_tokens(db, redis, refresh_token)
    except (HTTPException, ValueError) as exc:
        _clear_auth_cookies(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required") from exc

    _set_auth_cookies(response, new_access_token, new_refresh_token)
    payload = decode_token(new_access_token, "access")
    return await _active_user(db, payload["sub"])


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    try:
        user = await register_user(db, req.email, req.full_name, req.password)
        return RegisterResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            email_verified_at=user.email_verified_at,
            created_at=user.created_at,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except Exception:
        logger.exception("Registration failed for email=%s", req.email)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to register user")


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, response: Response, db: AsyncSession = Depends(get_db), redis: Redis = Depends(get_redis)):
    """
    Authenticate a user with email and password credentials. 
    If successful, issues new access and refresh tokens, sets them in cookies, and returns them in the response.
    Raises HTTP 401 if authentication fails.
    """
    try:
        access_token, refresh_token = await login_user(db, redis, req.email, req.password)
        _set_auth_cookies(response, access_token, refresh_token)
        return TokenResponse(access_token=access_token, refresh_token=refresh_token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


# generate refresh + access token when the access toekn is expired so it rotated the whole token and store new token inside the redis andd the server cookie
@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    req: RefreshRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """
    Refresh an expired or soon-to-expire access token using a valid refresh token.

    This endpoint allows clients to obtain new access and refresh tokens by presenting
    a valid refresh token (provided in the request body or cookies).
    On success, new tokens are set in cookies and returned in the response.
    If the refresh token is invalid, revoked, or expired, clears any authentication cookies
    and returns HTTP 401 Unauthorized.

    Args:
        req (RefreshRequest): The request body with an optional refresh token.
        request (Request): The incoming HTTP request, potentially carrying cookies.
        response (Response): The HTTP response object to modify cookies.
        db (AsyncSession): Database session dependency.
        redis (Redis): Redis connection dependency.

    Returns:
        TokenResponse: The new access and refresh tokens.

    Raises:
        HTTPException: 401 if the refresh token is missing, invalid, or expired.
    """
    refresh_token = req.refresh_token or request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token is required")
    try:
        access_token, new_refresh_token = await refresh_user_tokens(db, redis, refresh_token)
        _set_auth_cookies(response, access_token, new_refresh_token)
        return TokenResponse(access_token=access_token, refresh_token=new_refresh_token)
    except (HTTPException, ValueError) as exc:
        _clear_auth_cookies(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token") from exc

   
# logout
@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(req: RefreshRequest, request: Request, response: Response, redis: Redis = Depends(get_redis)):
    refresh_token = req.refresh_token or request.cookies.get("refresh_token")
    if refresh_token:
        try:
            await logout_user(redis, refresh_token)
        except (HTTPException, ValueError):
            pass
    _clear_auth_cookies(response)

# protected route -> validate user identity using jwt and return the vlaid user response
@router.get("/me", response_model=RegisterResponse)
async def me(current_user: User = Depends(get_current_user)):
    return RegisterResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        email_verified_at=current_user.email_verified_at,
        created_at=current_user.created_at,
    )
