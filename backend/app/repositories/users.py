import uuid
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(
        text("""
            SELECT id, email, full_name, password_hash,
                   is_active, email_verified_at, created_at
            FROM users
            WHERE email = :email
        """),
        {"email": email.lower()},
    )
    row = result.mappings().first()   # None when no row matches
    return User(**row) if row else None

from datetime import UTC, datetime

async def create_user(
    db: AsyncSession,
    email: str,
    full_name: str,
    password_hash: str
) -> User:


    # Prepare user values
    user_id = uuid.uuid4()
    email = email.lower()
    # ``datetime.datetime.utc()`` does not exist.  It raised an AttributeError
    # for every registration before the INSERT could run.
    created_at = datetime.now(UTC)
    is_active = True
    email_verified_at = None

    # Insert into database
    result = await db.execute(
        text("""
            INSERT INTO users (id, email, full_name, password_hash, is_active, email_verified_at, created_at)
            VALUES (:id, :email, :full_name, :password_hash, :is_active, :email_verified_at, :created_at)
            RETURNING id, email, full_name, password_hash, is_active, email_verified_at, created_at
        """),
        {
            "id": str(user_id),
            "email": email,
            "full_name": full_name,
            "password_hash": password_hash,
            "is_active": is_active,
            "email_verified_at": email_verified_at,
            "created_at": created_at,
        }
    )
    await db.commit()
    row = result.mappings().first()
    return User(**row) if row else None


async def get_user_by_id(db: AsyncSession, user_id: str) -> User | None:
    result = await db.execute(
        text("""
            SELECT id, email, full_name, password_hash, is_active, email_verified_at, created_at
            FROM users WHERE id = :id
        """),
        {"id": user_id},
    )
    row = result.mappings().first()
    return User(**row) if row else None
