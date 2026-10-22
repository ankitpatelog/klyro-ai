import uuid
from collections.abc import Mapping

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


VALID_FILE_EXTENSIONS = {"txt", "md", "markdown", "pdf", "csv"}
VALID_MIME_TYPES = {
    "txt": {"text/plain"},
    "md": {"text/markdown", "text/plain"},
    "markdown": {"text/markdown", "text/plain"},
    "pdf": {"application/pdf"},
    "csv": {"text/csv", "application/csv", "text/plain"},
}
MAX_FILE_SIZE = 20 * 1024 * 1024

_FIELDS = """
    id, knowledge_base_id, filename, file_size, mime_type, status,
    total_chunks, embedded_chunks, error_message, created_at, updated_at
"""

# check file is valid or not 
def validate_document(filename: str, mime_type: str, content: bytes) -> str:
    """Validate the filename, declared type, size, and simple file signature."""
    if not filename or "." not in filename:
        raise ValueError("A filename with a supported extension is required")

    extension = filename.rsplit(".", 1)[-1].lower()
    if extension not in VALID_FILE_EXTENSIONS:
        raise ValueError("Supported file types are PDF, TXT, Markdown, and CSV")
    if not content:
        raise ValueError("The uploaded file is empty")
    if len(content) > MAX_FILE_SIZE:
        raise ValueError("Files must be 20 MB or smaller")
    if mime_type and mime_type.lower() not in VALID_MIME_TYPES[extension]:
        raise ValueError("The file type does not match its extension")
    if extension == "pdf" and not content.startswith(b"%PDF-"):
        raise ValueError("The uploaded PDF is not a valid PDF file")

    return extension


async def create_document_and_job(
    db: AsyncSession,
    *,
    document_id: uuid.UUID,
    user_id: uuid.UUID,
    knowledge_base_id: uuid.UUID,
    filename: str,
    storage_path: str,
    file_size: int,
    mime_type: str,
) -> Mapping[str, object]:
    result = await db.execute(
        text(f"""
            INSERT INTO documents (
                id, user_id, knowledge_base_id, filename, storage_path,
                file_size, mime_type, status, total_chunks, embedded_chunks,
                created_at, updated_at
            )
            VALUES (
                :id, :user_id, :knowledge_base_id, :filename, :storage_path,
                :file_size, :mime_type, 'queued', 0, 0, NOW(), NOW()
            )
            RETURNING {_FIELDS}
        """),
        {
            "id": str(document_id),
            "user_id": str(user_id),
            "knowledge_base_id": str(knowledge_base_id),
            "filename": filename,
            "storage_path": storage_path,
            "file_size": file_size,
            "mime_type": mime_type,
        },
    )
    document = result.mappings().one()
    await db.execute(
        text("""
            INSERT INTO embedding_jobs (
                id, document_id, user_id, knowledge_base_id, status, progress,
                attempts, created_at, updated_at
            )
            VALUES (
                :id, :document_id, :user_id, :knowledge_base_id, 'queued', 0, 0, NOW(), NOW()
            )
        """),
        {
            "id": str(uuid.uuid4()),
            "document_id": str(document_id),
            "user_id": str(user_id),
            "knowledge_base_id": str(knowledge_base_id),
        },
    )
    await db.commit()
    return document


async def list_documents_for_knowledge_base(
    db: AsyncSession, knowledge_base_id: uuid.UUID, user_id: uuid.UUID
) -> list[Mapping[str, object]]:
    result = await db.execute(
        text(f"""
            SELECT {_FIELDS}
            FROM documents
            WHERE knowledge_base_id = :knowledge_base_id AND user_id = :user_id
            ORDER BY created_at DESC
        """),
        {"knowledge_base_id": str(knowledge_base_id), "user_id": str(user_id)},
    )
    return list(result.mappings().all())


async def completed_document_count(
    db: AsyncSession, knowledge_base_id: uuid.UUID, user_id: uuid.UUID
) -> int:
    """Count only documents whose vectors are ready for grounded RAG retrieval."""
    result = await db.execute(
        text("""
            SELECT COUNT(*)
            FROM documents
            WHERE knowledge_base_id = :knowledge_base_id
              AND user_id = :user_id
              AND status = 'completed'
        """),
        {"knowledge_base_id": str(knowledge_base_id), "user_id": str(user_id)},
    )
    return int(result.scalar_one())


async def delete_document(
    db: AsyncSession, document_id: uuid.UUID, knowledge_base_id: uuid.UUID, user_id: uuid.UUID
) -> str | None:
    result = await db.execute(
        text("""
            DELETE FROM documents
            WHERE id = :document_id
              AND knowledge_base_id = :knowledge_base_id
              AND user_id = :user_id
            RETURNING storage_path
        """),
        {
            "document_id": str(document_id),
            "knowledge_base_id": str(knowledge_base_id),
            "user_id": str(user_id),
        },
    )
    storage_path = result.scalar_one_or_none()
    if storage_path is not None:
        await db.commit()
    return storage_path
