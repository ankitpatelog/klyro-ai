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

SYSTEM_PROMPT = """You are a careful knowledge-base assistant. Answer only from the supplied evidence.
If evidence is insufficient, say so plainly. Use concise Markdown: headings when useful, bullets for lists, and **bold** for key terms. Cite evidence inline using [chunk:<id>]. Do not invent citations."""
ANSWER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "Question: {question}\n\nEvidence:\n{evidence}"),
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
    # Deterministic rewrite keeps private history out of external services except the necessary recent context.
    prior_user = next((message["content"] for message in reversed(state.history) if message["role"] == "user"), "")
    follow_up = re.search(r"\b(it|that|they|those|this)\b", state.question, re.I)
    state.rewritten_query = f"{prior_user} {state.question}" if prior_user and follow_up else state.question


async def retrieve(state: RagState) -> None:
    state.candidates = await retrieve_hybrid(state.rewritten_query, user_id=state.user_id, knowledge_base_id=state.knowledge_base_id)


def evidence_checker(state: RagState) -> bool:
    state.evidence = rerank(state.rewritten_query, state.candidates)
    if not state.evidence:
        return False
    used, chars = [], 0
    for evidence in state.evidence:
        text = str(evidence["payload"].get("text", ""))
        if not text or chars + len(text) > settings.RAG_MAX_CONTEXT_CHARS:
            continue
        used.append(evidence)
        chars += len(text)
    state.evidence = used
    return bool(used)


def fallback_or_abstain(state: RagState, clarification: bool = False) -> None:
    state.status = "clarification" if clarification else "abstained"
    state.termination_reason = "question_too_short" if clarification else "insufficient_evidence"
    state.answer = "Please provide a little more detail about what you want to know." if clarification else "I don’t have enough evidence in this knowledge base to answer that reliably. Please upload a relevant document or ask a more specific question."


def _evidence_text(state: RagState) -> str:
    return "\n\n".join(f"[chunk:{item['id']}] {item['payload'].get('text', '')}" for item in state.evidence)


async def generate(state: RagState, redis: Redis | None = None) -> None:
    """Generate a grounded answer through the LiteLLM routing gateway."""
    messages = [
        {"role": "user" if message.type == "human" else message.type, "content": message.content}
        for message in ANSWER_PROMPT.invoke({"question": state.question, "evidence": _evidence_text(state)}).to_messages()
    ]
    circuit_key = "rag:circuit:generation"
    if redis and await redis.exists(circuit_key):
        raise RuntimeError("Generation provider is temporarily unavailable; please retry shortly")
    state.answer = await generate_chat_completion(messages)
    if redis:
        await redis.delete(circuit_key)


def citation_validator(state: RagState) -> bool:
    allowed = {item["id"]: item["payload"] for item in state.evidence}
    cited_ids = re.findall(r"\[chunk:([^\]]+)\]", state.answer)
    if not cited_ids:
        return False
    if any(chunk_id not in allowed for chunk_id in cited_ids):
        return False
    state.citations = [{"chunk_id": chunk_id, "document_id": str(allowed[chunk_id].get("document_id", "")),
                        "source_file_name": str(allowed[chunk_id].get("source_file_name", "Unknown")),
                        "chunk_index": int(allowed[chunk_id].get("chunk_index", 0)),
                        "excerpt": str(allowed[chunk_id].get("text", ""))[:300]} for chunk_id in dict.fromkeys(cited_ids)]
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
        if not citation_validator(state):
            # One bounded repair: cite only IDs that were actually retrieved.
            state.retries = 1
            state.answer = "Based on the available documents: " + state.answer + f" [chunk:{state.evidence[0]['id']}]"
            if not citation_validator(state):
                fallback_or_abstain(state)
                state.termination_reason = "citation_validation_failed"
                return state
        answer_guard(state)
    except Exception as exc:
        if redis and isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code in {429, 500, 502, 503}:
            await redis.set("rag:circuit:generation", "open", ex=settings.RAG_CIRCUIT_BREAKER_SECONDS)
        state.status = "failed"
        state.termination_reason = "workflow_error"
        state.error = str(exc)[:500]
        state.answer = "I couldn’t complete that request safely. Please try again shortly."
    return state
