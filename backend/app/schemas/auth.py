import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

# register user handling
class RegisterRequest(BaseModel):
    """What the client SENDS FROM FRONTEND."""
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=120)
    password: str = Field(..., min_length=8, max_length=72)  # bcrypt reads only 72 bytes

    @field_validator("full_name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("full_name cannot be blank")
        return v


class RegisterResponse(BaseModel):
    """What the API SENDS FROM BACKEND. No password and no password_hash."""
    id: uuid.UUID
    email: EmailStr
    full_name: str
    is_active: bool
    email_verified_at: datetime | None
    created_at: datetime


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=72)


class RefreshRequest(BaseModel):
    refresh_token: str | None = Field(default=None, min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class ProfileUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    email: EmailStr | None = None
    current_password: str | None = Field(default=None, min_length=1, max_length=72)
    new_password: str | None = Field(default=None, min_length=8, max_length=72)


class ConfirmAccountActionRequest(BaseModel):
    confirmation: str = Field(..., min_length=1, max_length=32)
    current_password: str = Field(..., min_length=1, max_length=72)


class VerifyEmailRequest(BaseModel):
    code: str = Field(..., pattern=r"^\d{4}$")


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., pattern=r"^\d{4}$")
    new_password: str = Field(..., min_length=8, max_length=72)
