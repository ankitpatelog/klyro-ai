"""Explicit RAG graph nodes. Each node updates only safe workflow state, never credentials or tokens."""

import asyncio
import re
import time
from dataclasses import dataclass, field
from typing import Any, Literal

import httpx
from langchain_core.prompts import ChatPromptTemplate
from redis.asyncio import Redis

from app.core.config import settings
from app.services.llm_gateway import generate_chat_completion
from app.services.safety_service import check_input_safety, check_output_safety
from app.services.rag.retrieval import rerank, retrieve_hybrid
from app.services.rag.optimization import budget_evidence, cache_answer, compact_history, estimate_tokens, get_cached_answer

SYSTEM_PROMPT = """You are a careful knowledge-base assistant. Answer only from the supplied evidence.
Read all supplied evidence before deciding it is insufficient, especially for questions asking for a count, list, or fact. Use concise Markdown: headings when useful, bullets for lists, and **bold** for key terms. Cite evidence inline using [chunk:<id>]. Do not invent citations."""
ANSWER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "Conversation memory (may be empty):\n{history}\n\nQuestion: {question}\n\nEvidence:\n{evidence}"),
])


@dataclass
class RagState:
    request_id: str
    user_id: str
    knowledge_base_id: str
    conversation_id: str
    question: str
    history: list[dict[str, str]] = field(default_factory=list)
    rewritten_query: str = ""
    candidates: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    answer: str = ""
    citations: list[dict[str, Any]] = field(default_factory=list)
    status: Literal["answered", "clarification", "abstained", "failed"] = "failed"
    termination_reason: str = ""
    error: str | None = None
    retries: int = 0
    cache_hit: bool = False
    context_tokens: int = 0
    history_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    started_at: float = field(default_factory=time.perf_counter)


async def input_guard(state: RagState) -> bool:
    state.question = " ".join(state.question.split())
    if not state.question:
        raise ValueError("Question cannot be empty")
    decision = await check_input_safety(state.question)
    if not decision.allowed:
        state.status = "abstained"
        state.termination_reason = decision.reason
        state.answer = decision.message
        return False
    state.question = decision.content
    return True


def query_planner(state: RagState) -> Literal["retrieve", "clarify"]:
    if len(state.question) < 3:
        return "clarify"
    return "retrieve"


def query_rewriter(state: RagState) -> None:
    # Both private and shared chat must retrieve from the exact same query.
    # Conversation history is persisted for the private UI only; it must never
    # change the document search result for an otherwise identical question.
    state.rewritten_query = state.question


async def retrieve(state: RagState) -> None:
    state.candidates = await retrieve_hybrid(state.rewritten_query, user_id=state.user_id, knowledge_base_id=state.knowledge_base_id)


def evidence_checker(state: RagState) -> bool:
    state.evidence = rerank(state.rewritten_query, state.candidates)
    if not state.evidence:
        return False
    state.evidence, state.context_tokens = budget_evidence(
        state.evidence, max_tokens=settings.RAG_CONTEXT_TOKEN_BUDGET
    )
    return bool(state.evidence)


def fallback_or_abstain(state: RagState, clarification: bool = False) -> None:
    state.status = "clarification" if clarification else "abstained"
    state.termination_reason = "question_too_short" if clarification else "insufficient_evidence"
    state.answer = "Please provide a little more detail about what you want to know." if clarification else "I don’t have enough evidence in this knowledge base to answer that reliably. Please upload a relevant document or ask a more specific question."


def _evidence_text(state: RagState) -> str:
    return "\n\n".join(str(item.get("context_text", "")) for item in state.evidence)


async def generate(state: RagState, redis: Redis | None = None) -> None:
    """Generate a grounded answer through the LiteLLM routing gateway."""
    history, state.history_tokens = compact_history(
        state.history,
        recent_messages=settings.RAG_HISTORY_RECENT_MESSAGES,
        budget_tokens=settings.RAG_HISTORY_TOKEN_BUDGET,
    )
    evidence = _evidence_text(state)
    messages = [
        {"role": "user" if message.type == "human" else message.type, "content": message.content}
        for message in ANSWER_PROMPT.invoke({"question": state.question, "history": history, "evidence": evidence}).to_messages()
    ]
    state.input_tokens = sum(estimate_tokens(message["content"]) for message in messages)
    circuit_key = "rag:circuit:generation"
    if redis and await redis.exists(circuit_key):
        raise RuntimeError("Generation provider is temporarily unavailable; please retry shortly")
    state.answer = await generate_chat_completion(messages)
    state.output_tokens = estimate_tokens(state.answer)
    if redis:
        await redis.delete(circuit_key)


def citation_validator(state: RagState) -> bool:
    allowed = {item["id"]: item["payload"] for item in state.evidence}
    cited_ids = re.findall(r"\[chunk:([^\]]+)\]", state.answer)
    valid_ids = list(dict.fromkeys(chunk_id for chunk_id in cited_ids if chunk_id in allowed))

    # Models occasionally omit citations or invent an ID. Do not discard a
    # grounded answer in that case: remove invalid IDs and attach one verified
    # evidence citation. This gives private and shared chat identical, valid
    # source handling for the same retrieval result.
    state.answer = re.sub(
        r"\s*\[chunk:([^\]]+)\]",
        lambda match: match.group(0) if match.group(1) in allowed else "",
        state.answer,
    ).strip()
    if not valid_ids:
        valid_ids = [state.evidence[0]["id"]]
        state.answer = f"{state.answer} [chunk:{valid_ids[0]}]".strip()

    state.citations = [{"chunk_id": chunk_id, "document_id": str(allowed[chunk_id].get("document_id", "")),
                        "source_file_name": str(allowed[chunk_id].get("source_file_name", "Unknown")),
                        "chunk_index": int(allowed[chunk_id].get("chunk_index", 0)),
                        "excerpt": str(allowed[chunk_id].get("text", ""))[:300]} for chunk_id in valid_ids]
    return True


def answer_guard(state: RagState) -> None:
    state.answer = re.sub(r"\s*\[chunk:[^\]]+\]", "", state.answer).strip()
    state.status = "answered"
    state.termination_reason = "grounded_answer"


async def run_workflow(state: RagState, redis: Redis | None = None) -> RagState:
    """START → guards/planner → retrieval graph → generation/repair → finalize-ready state."""
    try:
        if not await input_guard(state):
            return state
        if query_planner(state) == "clarify":
            fallback_or_abstain(state, clarification=True)
            return state
        query_rewriter(state)
        cached = await get_cached_answer(
            redis, knowledge_base_id=state.knowledge_base_id, question=state.rewritten_query,
            similarity=settings.RAG_CACHE_SIMILARITY,
        )
        if cached:
            state.answer = str(cached["answer"])
            state.citations = list(cached.get("citations", []))
            state.cache_hit = True
            state.status = "answered"
            state.termination_reason = "semantic_cache_hit"
            state.output_tokens = estimate_tokens(state.answer)
            return state
        await retrieve(state)
        if not evidence_checker(state):
            fallback_or_abstain(state)
            return state
        await generate(state, redis)
        output_decision = await check_output_safety(state.question, state.answer)
        if not output_decision.allowed:
            state.status = "abstained"
            state.termination_reason = output_decision.reason
            state.answer = output_decision.message
            state.citations = []
            return state
        state.answer = output_decision.content
        citation_validator(state)
        answer_guard(state)
        await cache_answer(
            redis, knowledge_base_id=state.knowledge_base_id, question=state.rewritten_query,
            answer=state.answer, citations=state.citations, ttl_seconds=settings.RAG_CACHE_TTL_SECONDS,
        )
    except Exception as exc:
        if redis and isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code in {429, 500, 502, 503}:
            await redis.set("rag:circuit:generation", "open", ex=settings.RAG_CIRCUIT_BREAKER_SECONDS)
        state.status = "failed"
        state.termination_reason = "workflow_error"
        state.error = str(exc)[:500]
        state.answer = "I couldn’t complete that request safely. Please try again shortly."
    return state
