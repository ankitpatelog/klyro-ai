"""PostgreSQL persistence for conversations, messages, and safe workflow traces."""

import json
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def get_or_create_conversation(
    db: AsyncSession, *, conversation_id: str | None, user_id: str, knowledge_base_id: str
) -> str:
    if conversation_id:
        row = await db.execute(text("""
            SELECT id FROM rag_conversations
            WHERE id = :id AND user_id = :user_id AND knowledge_base_id = :knowledge_base_id
        """), {"id": conversation_id, "user_id": user_id, "knowledge_base_id": knowledge_base_id})
        if not row.scalar_one_or_none():
            raise ValueError("Conversation was not found in this knowledge base")
        return conversation_id
    # A user has one ongoing RAG thread per knowledge base unless the client explicitly
    # supplies a different authorized conversation ID.
    existing = await db.execute(text("""
        SELECT id FROM rag_conversations
        WHERE user_id = :user_id AND knowledge_base_id = :knowledge_base_id
        ORDER BY created_at DESC LIMIT 1
    """), {"user_id": user_id, "knowledge_base_id": knowledge_base_id})
    existing_id = existing.scalar_one_or_none()
    if existing_id:
        return str(existing_id)
    new_id = str(uuid.uuid4())
    await db.execute(text("""
        INSERT INTO rag_conversations (id, user_id, knowledge_base_id) VALUES (:id, :user_id, :knowledge_base_id)
    """), {"id": new_id, "user_id": user_id, "knowledge_base_id": knowledge_base_id})
    return new_id


async def recent_messages(db: AsyncSession, conversation_id: str, limit: int = 8) -> list[dict[str, str]]:
    rows = await db.execute(text("""
        SELECT role, content FROM rag_messages WHERE conversation_id = :conversation_id
        ORDER BY created_at DESC LIMIT :limit
    """), {"conversation_id": conversation_id, "limit": limit})
    return [dict(row) for row in reversed(rows.mappings().all())]


async def add_message(db: AsyncSession, conversation_id: str, role: str, content: str) -> None:
    await db.execute(text("""
        INSERT INTO rag_messages (id, conversation_id, role, content) VALUES (:id, :conversation_id, :role, :content)
    """), {"id": str(uuid.uuid4()), "conversation_id": conversation_id, "role": role, "content": content})


async def conversation_messages(
    db: AsyncSession, *, conversation_id: str, user_id: str, knowledge_base_id: str
) -> list[dict[str, object]]:
    """Return messages only after proving the conversation belongs to the caller and KB."""
    rows = await db.execute(text("""
        SELECT m.id, m.role, m.content, m.created_at
        FROM rag_messages AS m
        JOIN rag_conversations AS c ON c.id = m.conversation_id
        WHERE c.id = :conversation_id AND c.user_id = :user_id AND c.knowledge_base_id = :knowledge_base_id
        ORDER BY m.created_at ASC
    """), {"conversation_id": conversation_id, "user_id": user_id, "knowledge_base_id": knowledge_base_id})
    return [dict(row) for row in rows.mappings().all()]


async def save_trace(
    db: AsyncSession, *, request_id: str, conversation_id: str, user_id: str, knowledge_base_id: str,
    status: str, termination_reason: str, latency_ms: int, input_tokens: int, output_tokens: int,
    metadata: dict[str, Any], error: str | None = None,
) -> None:
    await db.execute(text("""
        INSERT INTO rag_traces (id, conversation_id, user_id, knowledge_base_id, status, termination_reason,
            latency_ms, input_tokens, output_tokens, metadata, error_message)
        VALUES (:id, :conversation_id, :user_id, :knowledge_base_id, :status, :termination_reason,
            :latency_ms, :input_tokens, :output_tokens, CAST(:metadata AS jsonb), :error)
    """), {"id": request_id, "conversation_id": conversation_id, "user_id": user_id,
              "knowledge_base_id": knowledge_base_id, "status": status, "termination_reason": termination_reason,
              "latency_ms": latency_ms, "input_tokens": input_tokens, "output_tokens": output_tokens,
              "metadata": json.dumps(metadata), "error": error})


async def observability_summary(db: AsyncSession, *, user_id: str, days: int) -> dict[str, Any]:
    """Return aggregate RAG metrics for one owner without exposing trace content."""
    summary = await db.execute(text("""
        SELECT
            COUNT(*)::int AS request_count,
            COALESCE(SUM(input_tokens + output_tokens), 0)::int AS total_tokens,
            COALESCE(SUM(input_tokens), 0)::int AS input_tokens,
            COALESCE(SUM(output_tokens), 0)::int AS output_tokens,
            COALESCE(ROUND(AVG(latency_ms))::int, 0) AS average_latency_ms,
            COALESCE(ROUND(100.0 * AVG(CASE WHEN metadata ->> 'cache_hit' = 'true' THEN 1 ELSE 0 END), 1), 0) AS cache_hit_rate,
            COALESCE(ROUND(AVG(COALESCE((metadata ->> 'evidence_count')::int, 0)), 1), 0) AS average_retrieved_chunks
        FROM rag_traces
        WHERE user_id = :user_id AND created_at >= NOW() - (:days * INTERVAL '1 day')
    """), {"user_id": user_id, "days": days})
    models = await db.execute(text("""
        SELECT COALESCE(NULLIF(metadata ->> 'model_used', ''), 'not recorded') AS model, COUNT(*)::int AS requests
        FROM rag_traces
        WHERE user_id = :user_id AND created_at >= NOW() - (:days * INTERVAL '1 day')
        GROUP BY 1 ORDER BY requests DESC
    """), {"user_id": user_id, "days": days})
    return {**dict(summary.mappings().one()), "models": [dict(row) for row in models.mappings().all()]}
