from typing import Literal
from urllib.parse import urlparse

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Pydantic reads these values from the environment and the configured .env file.
    DATABASE_URL: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int
    REDIS_URL: str
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"
    CORS_ORIGINS: str = ""
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_STORAGE_BUCKET: str = "kyroai-knowledge-base"
    QDRANT_URL: str = ""
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION: str = "knowledge_chunks"
    EMBEDDING_API_URL: str = "https://api.openai.com/v1"
    EMBEDDING_API_KEY: str = ""
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 1536
    # Groq is OpenAI-compatible; GENERATION_* keeps a provider swap possible later.
    GROQ_API_KEY: str = ""
    GENERATION_API_URL: str = "https://api.groq.com/openai/v1"
    GENERATION_API_KEY: str = ""
    GENERATION_MODEL: str = "llama-3.3-70b-versatile"
    RAG_RETRIEVAL_LIMIT: int = 24
    RAG_RERANK_LIMIT: int = 8
    RAG_MAX_CONTEXT_CHARS: int = 12_000
    RAG_USER_REQUESTS_PER_MINUTE: int = 10
    RAG_GENERATION_MAX_RETRIES: int = 2
    RAG_CIRCUIT_BREAKER_SECONDS: int = 30

    @field_validator("DATABASE_URL", mode="after")
    @classmethod
    def use_async_psycopg_driver(cls, value: str) -> str:
        if value.startswith("postgresql://"):
            return f"postgresql+psycopg://{value.removeprefix('postgresql://')}"
        return value

    @field_validator("SUPABASE_URL", mode="after")
    @classmethod
    def normalize_supabase_project_url(cls, value: str) -> str:
        """Accept either a Supabase project URL or its database connection URL."""
        value = value.strip().rstrip("/")
        if value.startswith(("postgresql://", "postgres://")):
            host = urlparse(value).hostname or ""
            if host.startswith("db.") and host.endswith(".supabase.co"):
                return f"https://{host.removeprefix('db.')}"
        return value

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
