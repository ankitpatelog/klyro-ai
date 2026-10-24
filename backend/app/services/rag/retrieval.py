"""Authorized hybrid retrieval from Qdrant using LangChain.

Only the retrieval layer is rebuilt on LangChain abstractions
(Embeddings, BaseRetriever, Document). The embedding pipeline
(embedding_worker.py) is intentionally left untouched, as are the
async function contracts the workflow depends on.

Every Qdrant request still applies both the ``user_id`` and
``knowledge_base_id`` ACL filters, so no data is retrieved without
both ownership filters.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

import httpx
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.retrievers import BaseRetriever
from pydantic import Field, PrivateAttr

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


def _qdrant_points(response_body: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize Qdrant search and scroll responses across supported versions."""
    result = response_body.get("result", [])
    if isinstance(result, list):
        return result
    if isinstance(result, dict):
        points = result.get("points", [])
        return points if isinstance(points, list) else []
    return []


class QdrantEmbeddings(Embeddings):
    """LangChain-compatible embedding function backed by the project's embedding API."""

    async def _post(self, inputs: list[str]) -> list[list[float]]:
        url = f"{settings.EMBEDDING_API_URL.rstrip('/')}/embeddings"
        body = {
            "model": settings.EMBEDDING_MODEL,
            "input": inputs,
            "dimensions": settings.EMBEDDING_DIMENSIONS,
        }
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(
                url,
                headers={"Authorization": f"Bearer {settings.EMBEDDING_API_KEY}"},
                json=body,
            )
            response.raise_for_status()
        data = response.json()["data"]
        return [item["embedding"] for item in sorted(data, key=lambda item: item["index"])]

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        return await self._post(list(texts))

    async def aembed_query(self, text: str) -> list[float]:
        vectors = await self._post([text])
        return vectors[0]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError("async-only embeddings; use aembed_documents")

    def embed_query(self, text: str) -> list[float]:
        raise NotImplementedError("async-only embeddings; use aembed_query")


class QdrantHybridRetriever(BaseRetriever):
    """LangChain retriever combining dense Qdrant search, lexical scroll, and RRF fusion."""

    user_id: str
    knowledge_base_id: str
    limit: int = Field(default=settings.RAG_RETRIEVAL_LIMIT)

    _embeddings: QdrantEmbeddings = PrivateAttr()

    def model_post_init(self, __context: Any) -> None:
        self._embeddings = QdrantEmbeddings()

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> list[Document]:
        raise NotImplementedError("async-only retriever; use aget_relevant_documents")

    async def _aget_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> list[Document]:
        vector = await self._embeddings.aembed_query(query)
        base = settings.QDRANT_URL.rstrip("/")
        filters = _filter(self.user_id, self.knowledge_base_id)
        async with httpx.AsyncClient(timeout=45) as client:
            dense = await client.post(
                f"{base}/collections/{settings.QDRANT_COLLECTION}/points/search",
                headers=_headers(),
                json={
                    "vector": vector,
                    "filter": filters,
                    "limit": self.limit,
                    "with_payload": True,
                },
            )
            dense.raise_for_status()
            # Scroll gives lexical retrieval access to payload text while retaining exactly the same ACL filter.
            lexical = await client.post(
                f"{base}/collections/{settings.QDRANT_COLLECTION}/points/scroll",
                headers=_headers(),
                json={
                    "filter": filters,
                    "limit": min(200, self.limit * 8),
                    "with_payload": True,
                    "with_vector": False,
                },
            )
            lexical.raise_for_status()

        dense_points = _qdrant_points(dense.json())
        lexical_points = _qdrant_points(lexical.json())
        query_terms = _terms(query)

        candidates: dict[str, dict[str, Any]] = {}
        for rank, point in enumerate(dense_points, start=1):
            payload = point.get("payload") or {}
            candidates[str(point["id"])] = {
                "id": str(point["id"]),
                "payload": payload,
                "dense_rank": rank,
                "lexical_rank": None,
                "score": float(point.get("score", 0)),
            }

        lexical_scored = sorted(
            lexical_points,
            key=lambda point: len(query_terms & _terms(str((point.get("payload") or {}).get("text", "")))),
            reverse=True,
        )
        for rank, point in enumerate(lexical_scored, start=1):
            overlap = len(query_terms & _terms(str((point.get("payload") or {}).get("text", ""))))
            if overlap == 0:
                continue
            item = candidates.setdefault(
                str(point["id"]),
                {"id": str(point["id"]), "payload": point.get("payload") or {},
                 "dense_rank": None, "lexical_rank": None, "score": 0.0},
            )
            item["lexical_rank"] = rank

        # Reciprocal-rank fusion: stable and dependency-free hybrid fusion.
        for item in candidates.values():
            item["rrf"] = sum(1 / (60 + rank) for rank in (item["dense_rank"], item["lexical_rank"]) if rank)

        documents: list[Document] = []
        for item in sorted(candidates.values(), key=lambda i: i["rrf"], reverse=True):
            payload = item["payload"] or {}
            documents.append(
                Document(
                    page_content=str(payload.get("text", "")),
                    metadata={
                        "id": item["id"],
                        "dense_rank": item["dense_rank"],
                        "lexical_rank": item["lexical_rank"],
                        "score": item["score"],
                        "rrf": item["rrf"],
                        "payload": payload,
                    },
                )
            )
        return documents


async def embed_query(query: str) -> list[float]:
    """Embed a single query through the LangChain embedding function."""
    return await QdrantEmbeddings().aembed_query(query)


async def retrieve_hybrid(query: str, *, user_id: str, knowledge_base_id: str) -> list[dict[str, Any]]:
    """Combine dense Qdrant search with a lexical score over the same authorized payloads."""
    retriever = QdrantHybridRetriever(
        user_id=user_id,
        knowledge_base_id=knowledge_base_id,
        limit=settings.RAG_RETRIEVAL_LIMIT,
    )
    # BaseRetriever exposes async retrieval through ``ainvoke``. It dispatches
    # to this retriever's ``_aget_relevant_documents`` implementation.
    documents = await retriever.ainvoke(query)
    return [
        {
            "id": doc.metadata["id"],
            "payload": doc.metadata["payload"],
            "dense_rank": doc.metadata["dense_rank"],
            "lexical_rank": doc.metadata["lexical_rank"],
            "score": doc.metadata["score"],
            "rrf": doc.metadata["rrf"],
        }
        for doc in documents
    ]


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
