"""Authorized hybrid retrieval from Qdrant. No data is retrieved without both ownership filters."""

import re
from collections.abc import Sequence
from typing import Any

import httpx

from app.core.config import settings


def _headers() -> dict[str, str]:
    return {"api-key": settings.QDRANT_API_KEY} if settings.QDRANT_API_KEY else {}


def _filter(user_id: str, knowledge_base_id: str) -> dict[str, Any]:
    return {"must": [
        {"key": "user_id", "match": {"value": user_id}},
        {"key": "knowledge_base_id", "match": {"value": knowledge_base_id}},
    ]}


def _terms(value: str) -> set[str]:
    return {term for term in re.findall(r"[a-z0-9]{2,}", value.lower())}


async def embed_query(query: str) -> list[float]:
    url = f"{settings.EMBEDDING_API_URL.rstrip('/')}/embeddings"
    body = {"model": settings.EMBEDDING_MODEL, "input": query, "dimensions": settings.EMBEDDING_DIMENSIONS}
    async with httpx.AsyncClient(timeout=45) as client:
        response = await client.post(url, headers={"Authorization": f"Bearer {settings.EMBEDDING_API_KEY}"}, json=body)
        response.raise_for_status()
    return response.json()["data"][0]["embedding"]


async def retrieve_hybrid(query: str, *, user_id: str, knowledge_base_id: str) -> list[dict[str, Any]]:
    """Combine dense Qdrant search with a lexical score over the same authorized payloads."""
    vector = await embed_query(query)
    base = settings.QDRANT_URL.rstrip("/")
    filters = _filter(user_id, knowledge_base_id)
    async with httpx.AsyncClient(timeout=45) as client:
        dense = await client.post(f"{base}/collections/{settings.QDRANT_COLLECTION}/points/query", headers=_headers(), json={
            "query": vector, "filter": filters, "limit": settings.RAG_RETRIEVAL_LIMIT, "with_payload": True,
        })
        dense.raise_for_status()
        # Scroll gives lexical retrieval access to payload text while retaining exactly the same ACL filter.
        lexical = await client.post(f"{base}/collections/{settings.QDRANT_COLLECTION}/points/scroll", headers=_headers(), json={
            "filter": filters, "limit": min(200, settings.RAG_RETRIEVAL_LIMIT * 8), "with_payload": True,
            "with_vector": False,
        })
        lexical.raise_for_status()
    dense_points = dense.json().get("result", {}).get("points", [])
    lexical_points = lexical.json().get("result", {}).get("points", [])
    query_terms = _terms(query)
    candidates: dict[str, dict[str, Any]] = {}
    for rank, point in enumerate(dense_points, start=1):
        candidates[str(point["id"])] = {"id": str(point["id"]), "payload": point.get("payload") or {},
                                       "dense_rank": rank, "lexical_rank": None, "score": float(point.get("score", 0))}
    lexical_scored = sorted(lexical_points, key=lambda point: len(query_terms & _terms(str((point.get("payload") or {}).get("text", "")))), reverse=True)
    for rank, point in enumerate(lexical_scored, start=1):
        overlap = len(query_terms & _terms(str((point.get("payload") or {}).get("text", ""))))
        if overlap == 0:
            continue
        item = candidates.setdefault(str(point["id"]), {"id": str(point["id"]), "payload": point.get("payload") or {},
                                                           "dense_rank": None, "lexical_rank": None, "score": 0.0})
        item["lexical_rank"] = rank
    # Reciprocal-rank fusion: stable and dependency-free hybrid fusion.
    for item in candidates.values():
        item["rrf"] = sum(1 / (60 + rank) for rank in (item["dense_rank"], item["lexical_rank"]) if rank)
    return sorted(candidates.values(), key=lambda item: item["rrf"], reverse=True)


def rerank(query: str, candidates: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Lightweight lexical reranker. Replace this node with a cross-encoder when one is configured."""
    query_terms = _terms(query)
    ranked = []
    for candidate in candidates:
        text = str(candidate["payload"].get("text", ""))
        overlap = len(query_terms & _terms(text)) / max(1, len(query_terms))
        candidate["rerank_score"] = candidate["rrf"] + overlap
        ranked.append(candidate)
    return sorted(ranked, key=lambda item: item["rerank_score"], reverse=True)[:settings.RAG_RERANK_LIMIT]
