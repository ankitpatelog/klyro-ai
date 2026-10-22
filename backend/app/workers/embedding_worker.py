"""Redis-driven document embedding worker. Run: python -m app.workers.embedding_worker.

    BRPOP embedding:jobs
BRPOP means:
Wait until a job arrives
→ remove one job from the queue
→ process it
→ wait for the next job

"""



import asyncio
import io
import json
import logging
import sys
import uuid
from collections.abc import Sequence

import httpx
from pypdf import PdfReader
from redis.exceptions import RedisError, TimeoutError as RedisTimeoutError
from sqlalchemy import text

from app.core.config import settings
from app.core.redis import create_redis_client
from app.db.session import SessionLocal


logger = logging.getLogger(__name__)
QUEUE_NAME = "embedding:jobs"
STATUS_CHANNEL = "document:status"
CHUNK_SIZE = 3_200
CHUNK_OVERLAP = 400
EMBEDDING_BATCH_SIZE = 64


def _supabase_headers() -> dict[str, str]:
    api_key = settings.SUPABASE_SERVICE_ROLE_KEY
    headers = {"apikey": api_key}
    if not api_key.startswith("sb_"):
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _require_settings() -> None:
    missing = [name for name, value in {
        "SUPABASE_URL": settings.SUPABASE_URL,
        "SUPABASE_SERVICE_ROLE_KEY": settings.SUPABASE_SERVICE_ROLE_KEY,
        "QDRANT_URL": settings.QDRANT_URL,
        "EMBEDDING_API_KEY": settings.EMBEDDING_API_KEY,
    }.items() if not value]
    if missing:
        raise RuntimeError(f"Worker configuration missing: {', '.join(missing)}")


def _chunks(text_value: str) -> list[str]:
    text_value = "\n".join(line.strip() for line in text_value.splitlines() if line.strip())
    if not text_value:
        return []
    result: list[str] = []
    start = 0
    while start < len(text_value):
        end = min(len(text_value), start + CHUNK_SIZE)
        if end < len(text_value):
            split_at = max(text_value.rfind("\n", start, end), text_value.rfind(" ", start, end))
            if split_at > start + CHUNK_SIZE // 2:
                end = split_at
        result.append(text_value[start:end].strip())
        if end == len(text_value):
            break
        start = end - CHUNK_OVERLAP
    return [chunk for chunk in result if chunk]


def _extract_text(filename: str, content: bytes) -> str:
    extension = filename.rsplit(".", 1)[-1].lower()
    if extension == "pdf":
        reader = PdfReader(io.BytesIO(content))
        return "\n\n".join((page.extract_text() or "").strip() for page in reader.pages)
    if extension in {"txt", "md", "markdown", "csv"}:
        return content.decode("utf-8-sig")
    raise ValueError("Unsupported document type")

# updare redis document status chanel
async def _publish(redis, document_id: str, status_value: str, progress: int, **extra: object) -> None:
    await redis.publish(STATUS_CHANNEL, json.dumps({
        "document_id": document_id, "status": status_value, "progress": progress, **extra,
    }))


async def _download_file(storage_path: str) -> bytes:
    url = f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/{settings.SUPABASE_STORAGE_BUCKET}/{storage_path}"
    headers = _supabase_headers()
    async with httpx.AsyncClient(timeout=90) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.content


async def _embed(chunk_batch: Sequence[str]) -> list[list[float]]:
    url = f"{settings.EMBEDDING_API_URL.rstrip('/')}/embeddings"
    headers = {"Authorization": f"Bearer {settings.EMBEDDING_API_KEY}", "Content-Type": "application/json"}
    body = {"model": settings.EMBEDDING_MODEL, "input": list(chunk_batch), "dimensions": settings.EMBEDDING_DIMENSIONS}
    async with httpx.AsyncClient(timeout=90) as client:
        response = await client.post(url, headers=headers, json=body)
        response.raise_for_status()
    return [item["embedding"] for item in sorted(response.json()["data"], key=lambda item: item["index"])]


async def _ensure_qdrant_collection() -> None:
    base_url = settings.QDRANT_URL.rstrip("/")
    headers = {"api-key": settings.QDRANT_API_KEY} if settings.QDRANT_API_KEY else {}
    async with httpx.AsyncClient(timeout=30) as client:
        existing = await client.get(f"{base_url}/collections/{settings.QDRANT_COLLECTION}", headers=headers)
        if existing.status_code == 404:
            created = await client.put(
                f"{base_url}/collections/{settings.QDRANT_COLLECTION}", headers=headers,
                json={"vectors": {"size": settings.EMBEDDING_DIMENSIONS, "distance": "Cosine"}},
            )
            created.raise_for_status()
        else:
            existing.raise_for_status()


async def _upsert_qdrant(points: list[dict[str, object]]) -> None:
    headers = {"api-key": settings.QDRANT_API_KEY} if settings.QDRANT_API_KEY else {}
    url = f"{settings.QDRANT_URL.rstrip('/')}/collections/{settings.QDRANT_COLLECTION}/points?wait=true"
    async with httpx.AsyncClient(timeout=90) as client:
        response = await client.put(url, headers=headers, json={"points": points})
        response.raise_for_status()

# update status on both document and job_embeddigns model in psql
async def _claim_job(document_id: str) -> dict[str, object] | None:
    async with SessionLocal() as db:
        claimed = await db.execute(text("""
            UPDATE embedding_jobs SET status = 'processing', attempts = attempts + 1, locked_at = NOW(), updated_at = NOW()
            WHERE document_id = :document_id AND status = 'queued' RETURNING document_id
        """), {"document_id": document_id})
        if not claimed.mappings().first():
            await db.rollback()
            return None
        document = await db.execute(text("""
            SELECT id, user_id, knowledge_base_id, filename, storage_path
            FROM documents WHERE id = :document_id
        """), {"document_id": document_id})
        await db.execute(text("UPDATE documents SET status = 'processing', updated_at = NOW() WHERE id = :document_id"), {"document_id": document_id})
        await db.commit()
        return dict(document.mappings().one())


async def _update_progress(document_id: str, completed: int, total: int) -> None:
    progress = max(1, min(99, int(completed * 100 / total)))
    async with SessionLocal() as db:
        await db.execute(text("""
            UPDATE documents SET total_chunks = :total, embedded_chunks = :completed, updated_at = NOW()
            WHERE id = :document_id
        """), {"document_id": document_id, "total": total, "completed": completed})
        await db.execute(text("UPDATE embedding_jobs SET progress = :progress, updated_at = NOW() WHERE document_id = :document_id"), {"document_id": document_id, "progress": progress})
        await db.commit()


async def _finish(document_id: str, error: str | None = None) -> None:
    status_value = "failed" if error else "completed"
    async with SessionLocal() as db:
        await db.execute(text("""
            UPDATE documents SET status = :status, error_message = :error, updated_at = NOW() WHERE id = :document_id
        """), {"document_id": document_id, "status": status_value, "error": error})
        await db.execute(text("""
            UPDATE embedding_jobs SET status = :status, progress = :progress, error_message = :error,
                completed_at = CASE WHEN CAST(:status AS VARCHAR(20)) = 'completed' THEN NOW() ELSE NULL END, updated_at = NOW()
            WHERE document_id = :document_id
        """), {"document_id": document_id, "status": status_value, "progress": 100 if not error else 0, "error": error})
        await db.commit()


async def process_job(redis, document_id: str) -> None:
    # store in db
    document = await _claim_job(document_id)
    if not document:
        return
        # update redis status for document
    await _publish(redis, document_id, "processing", 1)
    try:
        document_text = _extract_text(str(document["filename"]), await _download_file(str(document["storage_path"])))
        chunks = _chunks(document_text)
        if not chunks:
            raise ValueError("No extractable text was found in this document")
        await _ensure_qdrant_collection()
        total = len(chunks)
        for start in range(0, total, EMBEDDING_BATCH_SIZE):
            chunk_batch = chunks[start:start + EMBEDDING_BATCH_SIZE]
            vectors = await _embed(chunk_batch)
            points: list[dict[str, object]] = []
            for offset, (chunk, vector) in enumerate(zip(chunk_batch, vectors)):
                index = start + offset
                points.append({
                    "id": str(uuid.uuid5(uuid.UUID(document_id), str(index))), "vector": vector,
                    "payload": {"user_id": str(document["user_id"]), "knowledge_base_id": str(document["knowledge_base_id"]),
                                "document_id": document_id, "chunk_index": index, "source_file_name": str(document["filename"]), "text": chunk},
                })
            await _upsert_qdrant(points)
            completed = min(start + len(chunk_batch), total)
            await _update_progress(document_id, completed, total)
            await _publish(redis, document_id, "processing", int(completed * 100 / total), total_chunks=total, embedded_chunks=completed)
        await _finish(document_id)
        await _publish(redis, document_id, "completed", 100, total_chunks=total, embedded_chunks=total)
    except Exception as exc:
        logger.exception("Embedding failed for document %s", document_id)
        message = str(exc)[:500] or "Embedding failed"
        await _finish(document_id, message)
        await _publish(redis, document_id, "failed", 0, error_message=message)


async def main() -> None:
    # _require_settings()
    redis = create_redis_client()
    await redis.ping()
    logger.info("Embedding worker started; waiting on %s", QUEUE_NAME)
    try:
        while True:
            # Keep the Redis blocking duration shorter than a configured client
            # socket timeout. Some hosted Redis URLs set socket_timeout=5.
            item = None
            try:
                item = await redis.brpop(QUEUE_NAME, timeout=1)
            except RedisTimeoutError:
                # An empty queue / hosted Redis socket timing out is not a job failure.
                logger.debug("Timed out while waiting for an embedding job; retrying")
                continue
            except RedisError:
                logger.exception("Redis queue connection failed; retrying in 2 seconds")
                await asyncio.sleep(2)
                continue
            if not item:
                continue


            _, raw_job = item
            # ("embedding:jobs", '{"document_id":"abc-123","user_id":"..."}')
            try:
                document_id = str(json.loads(raw_job)["document_id"])
                await process_job(redis,document_id )
            except (json.JSONDecodeError, KeyError, TypeError):
                logger.exception("Discarding malformed embedding job: %r", raw_job)
    finally:
        await redis.aclose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
