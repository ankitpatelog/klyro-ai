import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from redis.exceptions import RedisError


logger = logging.getLogger(__name__)

router = APIRouter()

STATUS_CHANNEL = "document:status"


@router.websocket("/ws/documents/{document_id}")
async def document_status_websocket(websocket: WebSocket, document_id: str) -> None:
    """Forward Redis document status events to the matching WebSocket client."""
    await websocket.accept()

    pubsub = websocket.app.state.redis.pubsub()
    try:
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
