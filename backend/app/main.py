
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.redis import create_redis_client


@asynccontextmanager
async def lifespan(_: FastAPI):
    if len(settings.JWT_SECRET_KEY) < 32:
        raise RuntimeError("JWT_SECRET_KEY must be set to a value of at least 32 characters")
    app_redis = create_redis_client()
    await app_redis.ping()
    app.state.redis = app_redis
    try:
        yield
    finally:
        await app_redis.aclose()

app = FastAPI(
    title="Kyro-ai",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/test")
async def test():
    return {"message": "Test endpoint is working"}
