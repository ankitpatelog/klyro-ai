
import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.redis import create_redis_client
from app.workers.embedding_worker import run_worker, validate_worker_settings


@asynccontextmanager
async def lifespan(_: FastAPI):
    if len(settings.JWT_SECRET_KEY) < 32:
        raise RuntimeError("JWT_SECRET_KEY must be set to a value of at least 32 characters")
    app_redis = create_redis_client()
    await app_redis.ping()
    app.state.redis = app_redis
    worker_task = None
    if settings.RUN_EMBEDDING_WORKER:
        validate_worker_settings()
        worker_task = asyncio.create_task(run_worker(), name="embedding-worker")
    try:
        yield
    finally:
        if worker_task:
            worker_task.cancel()
            with suppress(asyncio.CancelledError):
                await worker_task
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






# Start server
#   → validate JWT secret
#   → connect and test Redis
#   → save Redis client on app.state
#   → yield: serve API requests
# Stop server
#   → close Redis connection
