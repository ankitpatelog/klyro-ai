from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# Resolve configuration from the backend directory, rather than the process
# working directory. This keeps API, worker, and public-share deployments on
# the same database and Qdrant collection even when they are started from the
# repository root or a process manager.
_BACKEND_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


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
    GENERATION_MODEL: str = "openai/gpt-oss-20b"
    LITELLM_PRIMARY_MODEL: str = "groq/openai/gpt-oss-20b"
    LITELLM_FALLBACK_MODELS: str = "groq/qwen/qwen3.8-27b"
    LITELLM_NUM_RETRIES: int = 1
    LITELLM_TIMEOUT_SECONDS: int = 90
    LITELLM_COOLDOWN_SECONDS: int = 30
    NVIDIA_API_KEY: str = ""
    # Remote safety classifiers can be enabled explicitly after evaluating
    # their false-positive rate for the application's domain.
    NEMO_GUARDRAILS_ENABLED: bool = False
    NEMO_GUARDRAILS_CONFIG_PATH: str = "app/guardrails"
    RAG_RETRIEVAL_LIMIT: int = 24
    RAG_RERANK_LIMIT: int = 8
    RAG_MAX_CONTEXT_CHARS: int = 12_000
    RAG_CONTEXT_TOKEN_BUDGET: int = 3_000
    RAG_HISTORY_TOKEN_BUDGET: int = 500
    RAG_HISTORY_RECENT_MESSAGES: int = 4
    RAG_HISTORY_SUMMARY_SOURCE_TOKEN_BUDGET: int = 1_500
    RAG_HISTORY_SUMMARY_TARGET_TOKENS: int = 200
    RAG_CACHE_TTL_SECONDS: int = 600
    RAG_CACHE_SIMILARITY: float = 0.88
    # Optional provider pricing for observability. Leave at zero when pricing is
    # unknown or bundled into the provider plan; the dashboard will show $0.
    RAG_INPUT_COST_PER_MILLION_TOKENS: float = 0.0
    RAG_OUTPUT_COST_PER_MILLION_TOKENS: float = 0.0
    RAG_USER_REQUESTS_PER_MINUTE: int = 10
    RAG_GENERATION_MAX_RETRIES: int = 2
    RAG_CIRCUIT_BREAKER_SECONDS: int = 30
    # For a single-service deployment, the API starts the Redis embedding loop.
    # Set false only when deploying the worker as a separate service.
    RUN_EMBEDDING_WORKER: bool = True
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_FROM_NAME: str = "Klyro AI"
    SMTP_USE_TLS: bool = True
    EMAIL_VERIFICATION_TTL_SECONDS: int = 600

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

    model_config = SettingsConfigDict(env_file=_BACKEND_ENV_FILE, env_file_encoding="utf-8", extra="ignore")


settings = Settings()
