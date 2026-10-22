-- Apply after 001_documents.sql. Stores only user-visible conversation content and safe operational traces.
CREATE TABLE IF NOT EXISTS rag_conversations (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    knowledge_base_id UUID NOT NULL REFERENCES knowledgebases(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS rag_messages (
    id UUID PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES rag_conversations(id) ON DELETE CASCADE,
    role VARCHAR(16) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS rag_messages_conversation_created_idx ON rag_messages (conversation_id, created_at);

CREATE TABLE IF NOT EXISTS rag_traces (
    id UUID PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES rag_conversations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    knowledge_base_id UUID NOT NULL REFERENCES knowledgebases(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL,
    termination_reason VARCHAR(80) NOT NULL,
    latency_ms INTEGER NOT NULL DEFAULT 0,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS rag_traces_conversation_created_idx ON rag_traces (conversation_id, created_at DESC);
