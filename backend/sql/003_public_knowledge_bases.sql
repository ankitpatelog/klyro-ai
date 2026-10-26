-- Apply after 002_rag.sql. Existing knowledge bases remain private by default.
ALTER TABLE knowledgebases
    ADD COLUMN IF NOT EXISTS visibility VARCHAR(10) NOT NULL DEFAULT 'private'
        CHECK (visibility IN ('private', 'public')),
    ADD COLUMN IF NOT EXISTS public_share_token VARCHAR(128) UNIQUE;

CREATE INDEX IF NOT EXISTS knowledgebases_public_share_token_idx
    ON knowledgebases (public_share_token)
    WHERE public_share_token IS NOT NULL;
