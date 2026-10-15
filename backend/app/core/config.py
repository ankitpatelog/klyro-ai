from pydantic_settings import BaseSettings, SettingsConfigDict
import os


class Settings(BaseSettings):
    # Reads the DB URL from the environment variable NEON_DATABASE_URL
    DATABASE_URL: str = os.getenv("NEON_DATABASE_URL", "")
    NEON_DATABASE_PASS: str = os.getenv("NEON_DATABASE_PASS", "")
    AWS_ENDPOINT_URL_S3: str = os.getenv("AWS_ENDPOINT_URL_S3", "")
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_REGION: str = os.getenv("AWS_REGION", "")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    REDIS_URL: str = "redis://localhost:6379/0"
    COOKIE_SECURE: bool = True
    COOKIE_SAMESITE: str = "lax"
    CORS_ORIGINS: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
