import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.document import DocumentResponse


class KnowledgeBaseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    description: str = Field(default="", max_length=2_000)
    status: str = Field(default="active", min_length=1, max_length=50)
    document_limit: int = Field(default=10, ge=1, le=10_000)

    @field_validator("name", "status")
    @classmethod
    def strip_required_fields(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value cannot be blank")
        return value

    @field_validator("description")
    @classmethod
    def strip_description(cls, value: str) -> str:
        return value.strip()


class KnowledgeBaseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2_000)
    status: str | None = Field(default=None, min_length=1, max_length=50)
    document_limit: int | None = Field(default=None, ge=1, le=10_000)

    @field_validator("name", "status")
    @classmethod
    def strip_optional_required_fields(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("value cannot be blank")
        return value

    @field_validator("description")
    @classmethod
    def strip_optional_description(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else value


class KnowledgeBaseResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    description: str
    status: str
    document_limit: int
    created_at: datetime
    document_count: int = 0


class KnowledgeBaseDetailResponse(KnowledgeBaseResponse):
    documents: list[DocumentResponse] = Field(default_factory=list)
