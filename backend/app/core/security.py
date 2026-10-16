import hashlib
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import HTTPException, status
from pwdlib import PasswordHash

password_hasher = PasswordHash.recommended()

# passwrod hashing security

def hash_password(password : str) -> str:
    return password_hasher.hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plaintext password against the given hash."""
    return password_hasher.verify(password, password_hash)

def token_hash(token: str) -> str:
    """Return a non-reversible value safe to persist in Redis."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

# create access token
def create_access_token(user_id: str, session_id: str) -> str:
    """Create a short-lived token used to access protected API endpoints."""
    from app.core.config import settings

    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "jti": session_id,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


# create refresh token
def create_refresh_token(user_id: str) -> tuple[str, str, datetime]:
    """Create a refresh JWT and return its ID and expiry for server-side revocation."""
    from app.core.config import settings

    now = datetime.now(UTC)
    expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    token_id = str(uuid.uuid4())
    payload = {
        "sub": user_id,
        "jti": token_id,
        "type": "refresh",
        "iat": now,
        "exp": expires_at,
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, token_id, expires_at


# take refrsh token and verrigy whether its valid or not 
def decode_token(token: str, expected_type: str) -> dict:
    """Decode a JWT, verify its type, and check for required claims. Raises HTTP 401 if invalid."""
    from app.core.config import settings

    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc
    if payload.get("type") != expected_type or not payload.get("sub") or not payload.get("jti"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    return payload
