"""Authenticated RAG endpoint. It streams SSE events but can also return one JSON answer."""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, Security
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import bearer_scheme, get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.core.redis import get_redis
from app.models.user import User
from app.repositories.document import completed_document_count
from app.repositories.knowledge_bases import get_knowledge_base, get_public_knowledge_base
from app.repositories.rag import add_message, conversation_messages, get_or_create_conversation, save_trace
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


async def _enforce_public_rate_limit(redis: Redis, token: str) -> None:
    key = f"rag:rate:public:{token}"
    current = await redis.incr(key)
    if current == 1:
        await redis.expire(key, 60)
    if current > settings.RAG_USER_REQUESTS_PER_MINUTE:
        raise HTTPException(status_code=429, detail="Too many requests; please retry shortly")


async def _require_rag_ready_knowledge_base(
    db: AsyncSession, *, knowledge_base_id: uuid.UUID, current_user: User
) -> None:
    """RAG starts after a base owns at least one successfully embedded document."""
    kb = await get_knowledge_base(db, knowledge_base_id, current_user.id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    ready_documents = await completed_document_count(db, knowledge_base_id, current_user.id)
    if ready_documents < 1:
        raise HTTPException(
            status_code=409,
            detail="Upload and finish embedding at least 1 document before starting this knowledge base chat",
        )


async def _run_knowledge_base_question(
    *,
    db: AsyncSession,
    redis: Redis,
    knowledge_base_id: uuid.UUID,
    owner_user_id: uuid.UUID,
    question: str,
    conversation_id: str,
    persist: bool,
) -> RagState:
    """Execute the one shared retrieval and answer pipeline for every chat surface."""
    state = RagState(
        request_id=str(uuid.uuid4()),
        # Public requests resolve their owner from the share token; private
        # requests receive the authenticated user's ID. Passing the UUID
        # explicitly prevents a Knowledgebase.id being used as a user_id.
        user_id=str(owner_user_id),
        knowledge_base_id=str(knowledge_base_id),
        conversation_id=conversation_id,
        question=question,
        # Messages remain available in the private UI, but never affect retrieval.
        history=[],
    )
    state = await run_workflow(state, redis)
    if persist:
        await _persist(db, state)
    return state


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
async def ask_question(
    payload: RagQuestionRequest,
    request: Request,
    response: Response,
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """One RAG endpoint for private and shared chat; authorization is the only branch."""
    if payload.share_token:
        await _enforce_public_rate_limit(redis, payload.share_token)
        knowledge_base = await get_public_knowledge_base(db, payload.share_token)
        if not knowledge_base:
            raise HTTPException(status_code=404, detail="This shared knowledge base is unavailable")
        ready_documents = await completed_document_count(db, knowledge_base.id, knowledge_base.user_id)
        if ready_documents < 1:
            raise HTTPException(status_code=409, detail="This shared knowledge base is not ready for chat yet. Upload and finish embedding a document first.")
        conversation_id = str(uuid.uuid4())
        state = await _run_knowledge_base_question(
            db=db, redis=redis, knowledge_base_id=knowledge_base.id, owner_user_id=knowledge_base.user_id,
            question=payload.question, conversation_id=conversation_id, persist=False,
        )
    else:
        current_user = await get_current_user(request, response, credentials, db, redis)
        knowledge_base_id = payload.knowledge_base_id
        if knowledge_base_id is None:  # Guaranteed by request validation; keeps type narrowing explicit.
            raise HTTPException(status_code=422, detail="knowledge_base_id is required")
        await _enforce_user_rate_limit(redis, str(current_user.id))
        await _require_rag_ready_knowledge_base(db, knowledge_base_id=knowledge_base_id, current_user=current_user)
        try:
            conversation_id = await get_or_create_conversation(
                db, conversation_id=str(payload.conversation_id) if payload.conversation_id else None,
                user_id=str(current_user.id), knowledge_base_id=str(knowledge_base_id),
            )
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        state = await _run_knowledge_base_question(
            db=db, redis=redis, knowledge_base_id=knowledge_base_id, owner_user_id=current_user.id,
            question=payload.question, conversation_id=conversation_id, persist=True,
        )
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
