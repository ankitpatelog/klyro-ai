
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from datetime import UTC, datetime

from app.models.user import User
from app.repositories.users import get_user_by_email, get_user_by_id, create_user
from app.core.security import create_access_token, create_refresh_token, decode_token, hash_password, token_hash, verify_password
from app.repositories.token_sessions import create_session, delete_session_if_refresh_matches, rotate_session

# register user
async def register_user(db: AsyncSession, email: str, full_name: str, password: str) -> User:
    """
    Registers a new user with the provided email, full name, and password.
    Raises ValueError if a user with the given email already exists.
    """

    # Kube: Check for DB connection presence before any queries
    if db is None:
        raise RuntimeError("Database connection is not present.")

    normalized_email = email.strip().lower()

    existing_user = await get_user_by_email(db, normalized_email)
    if existing_user:
        raise ValueError("A user with this email already exists.")

    password_hash = hash_password(password)
    try:
        # this will try to make    user in the db
        user = await create_user(
            db=db,
            email=normalized_email,
            full_name=full_name.strip(),
            password_hash=password_hash
        )
        return user
    except Exception as e:
        raise RuntimeError(f"Failed to create user: {e}")

# login
async def login_user(db: AsyncSession, redis: Redis, email: str, password: str) -> tuple[str, str]:
    user = await get_user_by_email(db, email.strip().lower())
    if not user or not user.is_active or not verify_password(password, user.password_hash):
        raise ValueError("Invalid email or password")
    return await _issue_tokens(redis, str(user.id))


# generate both access + refresh token 
async def _issue_tokens(redis: Redis, user_id: str) -> tuple[str, str]:
    access_token, refresh_token, session_id, expires_at = _new_token_pair(user_id)
    ttl = max(1, int((expires_at - datetime.now(UTC)).total_seconds()))
    await create_session(
        redis,
        session_id=session_id,
        user_id=user_id,
        access_hash=token_hash(access_token),
        refresh_hash=token_hash(refresh_token),
        expires_in_seconds=ttl,
    )
    return access_token, refresh_token


# return both token pair
def _new_token_pair(user_id: str) -> tuple[str, str, str, datetime]:
    refresh_token, session_id, expires_at = create_refresh_token(user_id)
    return create_access_token(user_id, session_id), refresh_token, session_id, expires_at



async def refresh_user_tokens(db: AsyncSession, redis: Redis, refresh_token: str) -> tuple[str, str]:
    payload = decode_token(refresh_token, "refresh")
    user_id, token_id = payload["sub"], payload.get("jti")
    if not token_id:
        raise ValueError("Refresh token is invalid")
    user = await get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise ValueError("User account is inactive")
    access_token, new_refresh_token, new_session_id, refresh_expires_at = _new_token_pair(user_id)
    rotated = await rotate_session(
        redis,
        old_session_id=token_id,
        old_refresh_hash=token_hash(refresh_token),
        new_session_id=new_session_id,
        user_id=user_id,
        new_access_hash=token_hash(access_token),
        new_refresh_hash=token_hash(new_refresh_token),
        expires_in_seconds=max(1, int((refresh_expires_at - datetime.now(UTC)).total_seconds())),
    )
    if not rotated:
        raise ValueError("Refresh token is invalid or has been revoked")
    return access_token, new_refresh_token


async def logout_user(redis: Redis, refresh_token: str) -> None:
    payload = decode_token(refresh_token, "refresh")
    token_id = payload.get("jti")
    if not token_id or not await delete_session_if_refresh_matches(redis, token_id, token_hash(refresh_token)):
        raise ValueError("Refresh token is invalid or has already been revoked")




