# RAG backend guide

## What was added

`POST /rag/questions` is an authenticated, knowledge-base-scoped question endpoint. It never sends passwords, refresh tokens, or account data to an LLM. In this app, `user_id` is the tenant boundary because organizations do not yet exist.

## Flow

`input_guard → query_planner → query_rewriter → retrieve → rerank → evidence_checker → generate → citation_validator → answer_guard → finalize`

The fallback path is `evidence_checker → fallback_or_abstain → finalize`. A short question follows the clarification path. Every Qdrant request applies both `user_id` and `knowledge_base_id` filters.

## One conversation per knowledge base

Each authenticated user has an ongoing RAG conversation for each knowledge base. `POST /rag/questions` resumes that knowledge base's latest conversation automatically when `conversation_id` is omitted. The frontend can load its chat history with `GET /rag/knowledge-bases/{knowledge_base_id}/conversation`.

The chat API is available only when that knowledge base has at least **two documents with `status = completed`**. Uploaded or processing documents do not count, because their vectors are not ready to retrieve. Before then, the history and question endpoints return `409 Conflict` with a clear readiness message.

## Production optimizations and observability

The worker stores contextual chunk metadata (`document_id`, filename, chunk index, and nearest section heading). Answering uses dense and keyword retrieval fused with reciprocal-rank fusion, followed by reranking. The prompt receives only the highest-ranked chunks that fit the configured context-token budget. Older turns are summarized by the generation model into a capped memory while recent turns remain verbatim. Redis caches answers per knowledge base for exact or embedding-similar repeat questions; the cache-query embedding is reused for retrieval on a miss.

`GET /rag/observability?days=30` is owner-scoped and reports request count, input/output tokens, estimated cost, average latency, cache-hit rate, average retrieved chunks, and the models recorded in traces. Set `RAG_*_COST_PER_MILLION_TOKENS` if you want cost estimates for your provider.

## Files

- `app/services/rag/workflow.py`: graph nodes and state.
- `app/services/rag/retrieval.py`: Jina query embedding, Qdrant dense + lexical retrieval, fusion, and reranking.
- `app/repositories/rag.py`: conversations, messages, and non-secret trace persistence.
- `app/api/v1/endpoints/rag.py`: protected JSON/SSE API.
- `sql/002_rag.sql`: required database tables.

## Setup

Install the new dependency and apply the migration:

```powershell
cd D:\klyro-ai\backend
.\kyro\Scripts\python.exe -m pip install -r requirements.txt
psql $env:DATABASE_URL -f sql\002_rag.sql
```

Create a Groq API key in the Groq console and add it to `.env`:

```env
GROQ_API_KEY=your_groq_api_key
GENERATION_API_URL=https://api.groq.com/openai/v1
GENERATION_MODEL=llama-3.3-70b-versatile
```

Groq's Chat Completions endpoint is OpenAI-compatible, which is why the existing HTTP generation client needs no SDK change. The existing Jina embedding settings remain unchanged. Restart the FastAPI server after updating environment variables.

## Reliability and rate limits

The endpoint enforces a Redis-backed per-user limit (default: 10 requests/minute), retries only transient Groq failures (`429`, `500`, `502`, `503`), respects Groq's `Retry-After` response header, and opens a 30-second circuit breaker after a final transient failure. It does not rotate free API keys to evade provider quotas.

## Example

```http
POST /rag/questions
Authorization: Bearer <access-token>
Content-Type: application/json

{"knowledge_base_id":"<uuid>","question":"What does the policy say about refunds?","stream":false}
```

Set `stream: true` to receive Server-Sent Events in this order: `meta`, `token`, `sources`, and `done`.
