from uuid import UUID
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


class DocumentStatus(str, Enum):
    UPLOADED = "uploaded"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentCreate(BaseModel):
    knowledge_base_id: UUID

    filename: str = Field( min_length=1, max_length=255)

    file_size: int 

    mime_type: str

    model_config = ConfigDict(
        extra="forbid"
    )


class DocumentResponse(BaseModel):
    id: UUID
    knowledge_base_id: UUID

    filename: str
    file_size: int
    mime_type: str

    status: DocumentStatus

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )


class DocumentStatusResponse(BaseModel):
    id: UUID
    status: DocumentStatus

    total_chunks: int = 0
    embedded_chunks: int = 0

    error_message: str | None = None

    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )