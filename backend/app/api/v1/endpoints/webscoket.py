import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from redis.exceptions import RedisError
from sqlalchemy import text

from app.db.session import SessionLocal


logger = logging.getLogger(__name__)

router = APIRouter()

STATUS_CHANNEL = "document:status"


def _status_message(status: str, progress: int) -> str:
    if status == "queued":
        return "Queued for processing"
    if status == "completed":
        return "Document is ready to chat with"
    if status == "failed":
        return "Document processing failed"
    if progress < 15:
        return "Preparing document"
    if progress < 30:
        return "Extracting and chunking text"
    return "Creating embeddings"


async def _current_document_status(document_id: str) -> dict[str, object] | None:
    """Send a snapshot so a client cannot miss fast Redis pub/sub events."""
    async with SessionLocal() as db:
        result = await db.execute(text("""
            SELECT d.id, d.status, d.total_chunks, d.embedded_chunks, d.error_message,
                   COALESCE(j.progress, 0) AS progress
            FROM documents d
            LEFT JOIN embedding_jobs j ON j.document_id = d.id
            WHERE d.id = :document_id
        """), {"document_id": document_id})
        row = result.mappings().first()
    if not row:
        return None
    progress = int(row["progress"] or (100 if row["status"] == "completed" else 0))
    status = str(row["status"])
    return {
        "document_id": str(row["id"]), "status": status, "progress": progress,
        "total_chunks": int(row["total_chunks"] or 0),
        "embedded_chunks": int(row["embedded_chunks"] or 0),
        "error_message": row["error_message"], "message": _status_message(status, progress),
    }


@router.websocket("/ws/documents/{document_id}")
async def document_status_websocket(websocket: WebSocket, document_id: str) -> None:
    """Forward Redis document status events to the matching WebSocket client."""
    await websocket.accept()

    pubsub = websocket.app.state.redis.pubsub()
    try:
        snapshot = await _current_document_status(document_id)
        if snapshot:
            await websocket.send_json(snapshot)
        await pubsub.subscribe(STATUS_CHANNEL)

        while True:
            message = await pubsub.get_message(
                ignore_subscribe_messages=True,
                timeout=1.0,
            )
            if message is None:
                continue

            raw_payload = message["data"]
            try:
                payload = json.loads(raw_payload)
            except (TypeError, json.JSONDecodeError):
                logger.warning("Ignoring invalid Redis status message: %r", raw_payload)
                continue

            if str(payload.get("document_id")) != str(document_id):
                continue
            
            # redis msg -> get data -> conver into json format -> send as json response of document status
            await websocket.send_json(payload)
    except WebSocketDisconnect:
        logger.debug("Document status WebSocket disconnected: %s", document_id)
    except RedisError:
        logger.exception("Redis status subscription failed for document %s", document_id)
        await websocket.close(code=1011, reason="Status updates are temporarily unavailable")
    finally:
        try:
            await pubsub.unsubscribe(STATUS_CHANNEL)
        finally:
            await pubsub.aclose()
