"""Content safety and jailbreak protection for the RAG boundary.

NeMo Guardrails is used when configured with an NVIDIA API key. A small,
fail-safe local policy remains active so an unavailable guardrail provider never
turns off jailbreak protection.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)

REFUSAL = "I can't help with that request. Please ask a safe, knowledge-base-related question."

# These catch direct attempts to make the RAG prompt or its retrieved documents
# override the application policy. NeMo then handles less obvious adversarial text.
JAILBREAK_PATTERNS = (
    r"\bignore (all |any |the )?(previous|prior|above|system) (instructions|rules|prompt)\b",
    r"\b(disregard|override|bypass) (the )?(system|safety|guardrails?|instructions?)\b",
    r"\b(reveal|show|print|dump|repeat) (the )?(system prompt|hidden prompt|developer message)\b",
    r"\b(you are now|act as) (dan|jailbreak|an unrestricted)\b",
    r"\bdo anything now\b",
)

# Targeted operational harm requests. This is deliberately narrow: discussions
# of safety, policy, history, and benign technical concepts remain allowed.
UNSAFE_REQUEST_PATTERNS = (
    r"\b(how to|steps? (to|for)|instructions? (to|for)|guide (to|for))\b.{0,100}\b(hack|phish|ransomware|malware|steal|rob|evade|bypass security)\b",
    r"\b(build|write|create)\b.{0,100}\b(malware|ransomware|keylogger|credential stealer|phishing kit)\b",
    r"\b(make|build|buy)\b.{0,100}\b(bomb|explosive|ghost gun)\b",
    r"\b(suicide|self[- ]harm)\b.{0,80}\b(how|method|best way|instructions)\b",
)


@dataclass(frozen=True)
class SafetyDecision:
    allowed: bool
    content: str
    reason: str = ""
    message: str = REFUSAL


def _matches(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL) for pattern in patterns)


def _local_check(text: str, *, direction: str) -> SafetyDecision | None:
    if direction == "input" and _matches(text, JAILBREAK_PATTERNS):
        return SafetyDecision(False, text, "jailbreak_detected")
    if _matches(text, UNSAFE_REQUEST_PATTERNS):
        return SafetyDecision(False, text, f"unsafe_{direction}_content")
    return None


@lru_cache(maxsize=1)
def _get_rails():
    """Build the NeMo rails once per worker, as recommended by NVIDIA."""
    if not settings.NEMO_GUARDRAILS_ENABLED or not settings.NVIDIA_API_KEY:
        return None
    try:
        from nemoguardrails import LLMRails, RailsConfig

        config_dir = Path(__file__).resolve().parents[1] / "guardrails"
        configured = Path(settings.NEMO_GUARDRAILS_CONFIG_PATH)
        if configured.is_absolute():
            config_dir = configured
        elif configured != Path("app/guardrails"):
            config_dir = Path.cwd() / configured
        return LLMRails(RailsConfig.from_path(str(config_dir)))
    except Exception:
        logger.exception("NeMo Guardrails could not be initialized; local safety rules remain active")
        return None


async def _nemo_check(messages: list[dict[str, str]]) -> SafetyDecision | None:
    rails = _get_rails()
    if rails is None:
        return None
    try:
        result = await rails.check_async(messages)
        if str(result.status).upper().endswith("BLOCKED"):
            return SafetyDecision(False, "", "nemo_guardrails_blocked")
        return SafetyDecision(True, str(result.content))
    except Exception:
        # Do not break RAG availability when a remote classifier is temporarily down.
        logger.exception("NeMo Guardrails check failed; using local safety rules")
        return None


async def check_input_safety(question: str) -> SafetyDecision:
    """Run deterministic jailbreak checks, then NeMo input rails."""
    return _local_check(question, direction="input") or await _nemo_check([
        {"role": "user", "content": question}
    ]) or SafetyDecision(True, question)


async def check_output_safety(question: str, answer: str) -> SafetyDecision:
    """Run NeMo output rails before the answer is stored or streamed to the user."""
    return _local_check(answer, direction="output") or await _nemo_check([
        {"role": "user", "content": question},
        {"role": "assistant", "content": answer},
    ]) or SafetyDecision(True, answer)
