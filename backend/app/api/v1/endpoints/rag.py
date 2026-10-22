"""Authenticated RAG endpoint. It streams SSE events but can also return one JSON answer."""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.core.redis import get_redis
from app.models.user import User
from app.repositories.document import completed_document_count
from app.repositories.knowledge_bases import get_knowledge_base
from app.repositories.rag import add_message, conversation_messages, get_or_create_conversation, recent_messages, save_trace
from app.schemas.rag import RagAnswerResponse, RagMessageResponse, RagQuestionRequest
from app.services.rag.workflow import RagState, run_workflow

router = APIRouter()


def _event(name: str, payload: dict) -> bytes:
    return f"event: {name}\ndata: {json.dumps(payload)}\n\n".encode()


async def _persist(db: AsyncSession, state: RagState) -> None:
    elapsed = int((time.perf_counter() - state.started_at) * 1000)
    await add_message(db, state.conversation_id, "user", state.question)
    await add_message(db, state.conversation_id, "assistant", state.answer)
    await save_trace(db, request_id=state.request_id, conversation_id=state.conversation_id, user_id=state.user_id,
                     knowledge_base_id=state.knowledge_base_id, status=state.status,
                     termination_reason=state.termination_reason, latency_ms=elapsed, input_tokens=0, output_tokens=0,
                     metadata={"rewritten_query": state.rewritten_query, "candidate_count": len(state.candidates),
                               "evidence_count": len(state.evidence), "retry_count": state.retries}, error=state.error)
    await db.commit()


async def _enforce_user_rate_limit(redis: Redis, user_id: str) -> None:
    """Fair-use application limit; this deliberately does not attempt to evade provider quotas."""
    key = f"rag:rate:user:{user_id}"
    current = await redis.incr(key)
    if current == 1:
        await redis.expire(key, 60)
    if current > settings.RAG_USER_REQUESTS_PER_MINUTE:
        retry_after = max(1, await redis.ttl(key))
        raise HTTPException(status_code=429, detail="Too many RAG requests; please retry shortly", headers={"Retry-After": str(retry_after)})


async def _require_rag_ready_knowledge_base(
    db: AsyncSession, *, knowledge_base_id: uuid.UUID, current_user: User
) -> None:
    """RAG starts only after a base owns at least two successfully embedded documents."""
    kb = await get_knowledge_base(db, knowledge_base_id, current_user.id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    ready_documents = await completed_document_count(db, knowledge_base_id, current_user.id)
    if ready_documents < 2:
        raise HTTPException(
            status_code=409,
            detail="Upload and finish embedding at least 2 documents before starting this knowledge base chat",
        )


@router.get("/knowledge-bases/{knowledge_base_id}/conversation", response_model=list[RagMessageResponse])
async def get_knowledge_base_conversation(
    knowledge_base_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Load this user's ongoing RAG chat history for one knowledge base."""
    await _require_rag_ready_knowledge_base(db, knowledge_base_id=knowledge_base_id, current_user=current_user)
    conversation_id = await get_or_create_conversation(
        db, conversation_id=None, user_id=str(current_user.id), knowledge_base_id=str(knowledge_base_id)
    )
    messages = await conversation_messages(
        db, conversation_id=conversation_id, user_id=str(current_user.id), knowledge_base_id=str(knowledge_base_id)
    )
    await db.commit()
    return messages


@router.post("/questions", response_model=RagAnswerResponse)
async def ask_question(payload: RagQuestionRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db), redis: Redis = Depends(get_redis)):
    """Ask a KB-scoped question. `stream=true` returns server-sent events: meta, token, sources, done."""
    await _enforce_user_rate_limit(redis, str(current_user.id))
    await _require_rag_ready_knowledge_base(db, knowledge_base_id=payload.knowledge_base_id, current_user=current_user)
    try:
        conversation_id = await get_or_create_conversation(db, conversation_id=str(payload.conversation_id) if payload.conversation_id else None,
                                                            user_id=str(current_user.id), knowledge_base_id=str(payload.knowledge_base_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    state = RagState(request_id=str(uuid.uuid4()), user_id=str(current_user.id), knowledge_base_id=str(payload.knowledge_base_id),
                     conversation_id=conversation_id, question=payload.question, history=await recent_messages(db, conversation_id))
    state = await run_workflow(state, redis)
    await _persist(db, state)
    now = datetime.now(timezone.utc)
    result = RagAnswerResponse(request_id=uuid.UUID(state.request_id), conversation_id=uuid.UUID(conversation_id), answer=state.answer,
                               citations=state.citations, status=state.status, termination_reason=state.termination_reason, created_at=now)
    if not payload.stream:
        return result

    async def stream():
        yield _event("meta", {"request_id": state.request_id, "conversation_id": conversation_id, "status": state.status})
        # Controlled token-sized chunks keep the response streamable after citation validation is complete.
        for word in state.answer.split(" "):
            yield _event("token", {"text": word + " "})
            await asyncio.sleep(0)
        yield _event("sources", {"citations": [citation.model_dump() for citation in result.citations]})
        yield _event("done", {"status": state.status, "termination_reason": state.termination_reason})
    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
