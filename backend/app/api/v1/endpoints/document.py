import json
import logging
import re
import uuid

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.core.config import settings
from app.core.redis import get_redis
from app.db.session import get_db
from app.models.user import User
from app.repositories.document import MAX_FILE_SIZE, create_document_and_job, validate_document
from app.repositories.knowledge_bases import get_knowledge_base
from app.schemas.document import DocumentResponse


router = APIRouter()
logger = logging.getLogger(__name__)


def _storage_path(user_id: uuid.UUID, knowledge_base_id: uuid.UUID, document_id: uuid.UUID, filename: str) -> str:
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", filename).strip("._") or "document"
    return f"{user_id}/{knowledge_base_id}/{document_id}/{safe_name}"

# take the one valid file and try to uplaod on the supabase 
async def _upload_to_supabase(storage_path: str, content: bytes, mime_type: str) -> None:
    # httpx help to make the request witout blocking the main request without breaking the application
    url = f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/{settings.SUPABASE_STORAGE_BUCKET}/{storage_path}"
    headers = {
        "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": mime_type or "application/octet-stream",
        "x-upsert": "false",
    }
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(url, content=content, headers=headers)
    if response.is_error:
        logger.error("Supabase upload failed: status=%s body=%s", response.status_code, response.text[:500])
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="File storage upload failed")


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    knowledge_base_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """Upload one validated document, persist its metadata, and queue embedding work."""
    knowledge_base = await get_knowledge_base(db, knowledge_base_id, current_user.id)
    if not knowledge_base:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")

    content = await file.read(MAX_FILE_SIZE + 1)
    filename = file.filename or ""
    mime_type = (file.content_type or "").lower()
    try:
        # it returrn the file valid extension
        validate_document(filename, mime_type, content)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    document_id = uuid.uuid4()
    storage_path = _storage_path(current_user.id, knowledge_base_id, document_id, filename)
    await _upload_to_supabase(storage_path, content, mime_type)

    try:
        document = await create_document_and_job(
            db,
            document_id=document_id,
            user_id=current_user.id,
            knowledge_base_id=knowledge_base_id,
            filename=filename,
            storage_path=storage_path,
            file_size=len(content),
            mime_type=mime_type,
        )
    except Exception:
        await db.rollback()
        logger.exception("Could not create or queue document %s", document_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not queue document processing")

    # Redis is only a wake-up mechanism: embedding_jobs is the durable queue.
    # A worker can safely poll queued jobs if this notification is unavailable.
    try:

        # LPOP	Removes and returns the first element from the left.	LIFO Stacks (with LPUSH)
        await redis.lpush(
            "embedding:jobs",
            json.dumps({
                "document_id": str(document_id),
                "user_id": str(current_user.id),
                "knowledge_base_id": str(knowledge_base_id),
            }),
        )
    except Exception:
        logger.exception("Document %s is queued but Redis notification failed", document_id)

    return document
