import uuid
from datetime import datetime

from pydantic import BaseModel


class User(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    password_hash: str
    is_active: bool
    email_verified_at: datetime | None
    created_at: datetime







# users model sql

# CREATE TABLE IF NOT EXISTS users (
#     id                 UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
#     email              VARCHAR(320) NOT NULL UNIQUE,
#     full_name          VARCHAR(120) NOT NULL,
#     password_hash      VARCHAR(255) NOT NULL,
#     is_active          BOOLEAN      NOT NULL DEFAULT TRUE,
#     email_verified_at  TIMESTAMPTZ  NULL,
#     created_at         TIMESTAMPTZ  NOT NULL DEFAULT now()
# );