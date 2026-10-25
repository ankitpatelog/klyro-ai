"""LiteLLM-backed generation gateway with retries, cooldowns, and model fallback."""

from functools import lru_cache
import logging

import httpx

try:
    from litellm import Router
except ImportError:  # Keep the RAG endpoint usable until dependencies are installed.
    Router = None

from app.core.config import settings

logger = logging.getLogger(__name__)

def _configured_fallback_models() -> list[str]:
    return [model.strip() for model in settings.LITELLM_FALLBACK_MODELS.split(",") if model.strip()]


@lru_cache(maxsize=1)
def get_generation_router():
    """Create one process-wide router so cooldown state survives individual requests."""
    if Router is None:
        raise RuntimeError("LiteLLM is not installed")
    model_list = [{
        "model_name": "rag-primary",
        "litellm_params": {"model": settings.LITELLM_PRIMARY_MODEL, "api_key": settings.GROQ_API_KEY},
    }]
    fallback_names: list[str] = []
    for index, model in enumerate(_configured_fallback_models(), start=1):
        name = f"rag-fallback-{index}"
        model_list.append({
            "model_name": name,
            "litellm_params": {"model": model, "api_key": settings.GROQ_API_KEY},
        })
        fallback_names.append(name)

    return Router(
        model_list=model_list,
        fallbacks=[{"rag-primary": fallback_names}] if fallback_names else [],
        num_retries=settings.LITELLM_NUM_RETRIES,
        allowed_fails=1,
        cooldown_time=settings.LITELLM_COOLDOWN_SECONDS,
    )


async def _direct_generation_fallback(messages: list[dict[str, str]]) -> str:
    """Temporary compatibility path used only when LiteLLM is unavailable locally."""
    models = [settings.LITELLM_PRIMARY_MODEL, *_configured_fallback_models()]
    last_error: httpx.HTTPStatusError | None = None
    url = f"{settings.GENERATION_API_URL.rstrip('/')}/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {settings.GROQ_API_KEY}"}
    async with httpx.AsyncClient(timeout=settings.LITELLM_TIMEOUT_SECONDS) as client:
        for model in models:
            provider, _, model_name = model.partition("/")
            if provider != "groq" or not model_name:
                raise RuntimeError("Install LiteLLM to use a non-Groq fallback model")
            response = await client.post(url, headers=headers, json={"model": model_name, "messages": messages, "temperature": 0.1})
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                last_error = exc
                continue
            content = response.json()["choices"][0]["message"]["content"]
            if content:
                return str(content).strip()
    raise last_error or RuntimeError("No configured generation model returned an answer")


async def generate_chat_completion(messages: list[dict[str, str]]) -> str:
    """Generate through the primary model, falling back only on router-eligible failures."""
    if not settings.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not configured")
    if Router is None:
        logger.warning("LiteLLM is not installed; using the temporary direct Groq compatibility path")
        return await _direct_generation_fallback(messages)
    response = await get_generation_router().acompletion(
        model="rag-primary",
        messages=messages,
        temperature=0.1,
        timeout=settings.LITELLM_TIMEOUT_SECONDS,
    )
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("Generation provider returned an empty response")
    return str(content).strip()
