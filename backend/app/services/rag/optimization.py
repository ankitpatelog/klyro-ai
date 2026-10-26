"""Small, dependency-free RAG cost controls used by the answer workflow."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Iterable
from typing import Any

from redis.asyncio import Redis

_CACHE_STOP_WORDS = {
    "a", "about", "an", "and", "are", "at", "do", "does", "for", "how", "i", "in", "is", "it",
    "me", "of", "on", "the", "to", "what", "where", "which", "who", "with", "you",
}
_SEMANTIC_CACHE_VERSION = "v2"


def estimate_tokens(value: str) -> int:
    """Conservative token estimate suitable for enforcing prompt budgets without a tokenizer call."""
    return max(1, (len(value) + 3) // 4) if value else 0


def compact_history(history: list[dict[str, str]], *, recent_messages: int, budget_tokens: int) -> tuple[str, int]:
    """Keep the newest turns verbatim and compact older turns into a bounded memory."""
    if not history:
        return "", 0
    older, recent = history[:-recent_messages], history[-recent_messages:]
    sections: list[str] = []
    if older:
        # Deterministic compression avoids a second LLM call solely to summarize history.
        snippets = [f"{item.get('role', 'user')}: {item.get('content', '')[:180]}" for item in older]
        sections.append("Earlier conversation summary: " + " | ".join(snippets))
    if recent:
        sections.append("Recent conversation:\n" + "\n".join(
            f"{item.get('role', 'user')}: {item.get('content', '')}" for item in recent
        ))
    memory = "\n\n".join(sections)
    max_chars = budget_tokens * 4
    return memory[:max_chars], estimate_tokens(memory[:max_chars])


def split_history(history: list[dict[str, str]], recent_messages: int) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Separate old turns (for summarization) from the recent verbatim window."""
    if not history:
        return [], []
    return history[:-recent_messages], history[-recent_messages:]


def render_history(history: list[dict[str, str]], *, budget_tokens: int) -> str:
    rendered = "\n".join(f"{item.get('role', 'user')}: {item.get('content', '')}" for item in history)
    return rendered[:budget_tokens * 4]


def budget_evidence(evidence: Iterable[dict[str, Any]], *, max_tokens: int) -> tuple[list[dict[str, Any]], int]:
    """Fit the highest-ranked chunks into a strict context budget with source metadata."""
    selected: list[dict[str, Any]] = []
    used = 0
    for item in evidence:
        payload = item.get("payload", {})
        heading = str(payload.get("section_heading") or "Document excerpt")
        source = str(payload.get("source_file_name") or "Unknown source")
        text = str(payload.get("text") or "").strip()
        prefix = f"[chunk:{item['id']}] Source: {source} | Section: {heading}\n"
        remaining_chars = max(0, (max_tokens - used) * 4 - len(prefix))
        if remaining_chars <= 0:
            break
        clipped = text[:remaining_chars].rsplit(" ", 1)[0] if len(text) > remaining_chars else text
        rendered = prefix + clipped
        cost = estimate_tokens(rendered)
        if not clipped or used + cost > max_tokens:
            continue
        copied = {**item, "context_text": rendered}
        selected.append(copied)
        used += cost
    return selected, used


def _normalized_question(question: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", question.lower()))


def _intent_terms(question: str) -> set[str]:
    """Terms that express what the user wants, excluding conversational filler."""
    return {term for term in _normalized_question(question).split() if term not in _CACHE_STOP_WORDS}


def _cache_key(knowledge_base_id: str, question: str) -> str:
    digest = hashlib.sha256(_normalized_question(question).encode()).hexdigest()
    return f"rag:answer-cache:{_SEMANTIC_CACHE_VERSION}:{knowledge_base_id}:{digest}"


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    denominator = math.sqrt(sum(value * value for value in left)) * math.sqrt(sum(value * value for value in right))
    return sum(a * b for a, b in zip(left, right)) / denominator if denominator else 0.0


async def get_cached_answer(
    redis: Redis | None, *, knowledge_base_id: str, question: str, similarity: float,
    query_embedding: list[float] | None = None,
) -> dict[str, Any] | None:
    """Return an exact or embedding-similar cached answer for the same knowledge base only."""
    if redis is None:
        return None
    exact = await redis.get(_cache_key(knowledge_base_id, question))
    if exact:
        return json.loads(exact)
    if query_embedding is None:
        return None
    current_intent = _intent_terms(question)
    # A one-word/entity-only question is too ambiguous for semantic reuse.
    # It can still use the exact-question cache above.
    if len(current_intent) < 2:
        return None
    index_key = f"rag:answer-cache-index:{_SEMANTIC_CACHE_VERSION}:{knowledge_base_id}"
    for cache_key in await redis.lrange(index_key, 0, 24):
        raw = await redis.get(cache_key)
        if not raw:
            continue
        item = json.loads(raw)
        cached_embedding = item.get("embedding")
        cached_intent = set(item.get("intent_terms", []))
        # Prevent entity-only overlap from serving a general "What is ACEM?"
        # answer to a distinct request such as "ACEM placement details".
        if (isinstance(cached_embedding, list)
                and len(cached_intent & current_intent) >= 2
                and _cosine_similarity(query_embedding, cached_embedding) >= similarity):
            return item
    return None


async def cache_answer(
    redis: Redis | None, *, knowledge_base_id: str, question: str, answer: str,
    citations: list[dict[str, Any]], embedding: list[float], ttl_seconds: int,
) -> None:
    if redis is None:
        return
    cache_key = _cache_key(knowledge_base_id, question)
    payload = {"question": _normalized_question(question), "intent_terms": sorted(_intent_terms(question)),
               "embedding": embedding, "answer": answer, "citations": citations}
    index_key = f"rag:answer-cache-index:{_SEMANTIC_CACHE_VERSION}:{knowledge_base_id}"
    await redis.set(cache_key, json.dumps(payload), ex=ttl_seconds)
    await redis.lrem(index_key, 0, cache_key)
    await redis.lpush(index_key, cache_key)
    await redis.ltrim(index_key, 0, 24)
    await redis.expire(index_key, ttl_seconds)
