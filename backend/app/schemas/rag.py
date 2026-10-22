"""Public request/response contracts for the grounded RAG endpoint."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class RagQuestionRequest(BaseModel):
    knowledge_base_id: UUID
    question: str = Field(min_length=1, max_length=4_000)
    conversation_id: UUID | None = None
    stream: bool = True


class Citation(BaseModel):
    chunk_id: str
    document_id: str
    source_file_name: str
    chunk_index: int
    excerpt: str


class RagMessageResponse(BaseModel):
    id: UUID
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime


class RagAnswerResponse(BaseModel):
    request_id: UUID
    conversation_id: UUID
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    status: Literal["answered", "clarification", "abstained", "failed"]
    termination_reason: str
    created_at: datetime
