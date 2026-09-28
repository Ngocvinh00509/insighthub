"""Fail-closed prompt and response guardrails for InsightHub."""
from __future__ import annotations

import re
import unicodedata

from app.core.config import get_settings
from app.core.errors import GuardrailUnavailable, ProviderError, UnsafePrompt
from app.core.providers import post_json

_INJECTION = re.compile(
    r"(?i)\b(ignore\s+(all\s+)?previous\s+instructions?|system\s+prompt|reveal\s+(the\s+)?prompt|jailbreak|do\s+anything\s+now)\b"
)
_PII = re.compile(
    r"(?i)(?:\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b|\b(?:\d[ -]*?){13,16}\b|\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b)"
)


def sanitize_user_input(value: str) -> str:
    """Normalize Unicode and remove invisible/control characters before retrieval."""
    normalized = unicodedata.normalize("NFKC", value)
    sanitized = "".join(
        char for char in normalized if unicodedata.category(char) not in {"Cc", "Cf"} or char in "\n\t"
    ).strip()
    if not sanitized or _INJECTION.search(sanitized):
        raise UnsafePrompt()
    return sanitized


def enforce_guardrail(content: str, *, stage: str) -> None:
    """Apply local checks, then an optional Bedrock/NeMo/Llama Guard HTTP adapter."""
    if _INJECTION.search(content) or (stage == "output" and _PII.search(content)):
        raise UnsafePrompt()
    settings = get_settings()
    if settings.guardrail_mode == "local":
        return
    try:
        decision = post_json(settings.guardrail_url, headers={"Content-Type": "application/json"}, payload={"input": content, "stage": stage})
    except ProviderError as exc:
        raise GuardrailUnavailable() from exc
    if decision.get("allowed") is not True:
        raise UnsafePrompt()
