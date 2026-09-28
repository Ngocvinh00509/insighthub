"""Prometheus metric for provider prompt-cache savings reported by LiteLLM.

Rates are operator supplied because provider cache discounts and model pricing
change. Missing model pricing intentionally emits no savings observation.
"""
from __future__ import annotations

import json
import math
import os
from typing import Any

from litellm.integrations.custom_logger import CustomLogger
from prometheus_client import Counter


PROMPT_CACHE_SAVINGS = Counter(
    "insighthub_litellm_prompt_cache_savings_usd",
    "Estimated USD saved on provider prompt-cache reads using configured model pricing",
    ("api_key_alias", "model"),
)
ALLOWED_KEY_ALIASES = {
    "insighthub-app-key",
    "chatops-bot-key",
    "coding-workflow-key",
}
ENV_RATES = "LITELLM_PROMPT_CACHE_SAVINGS_USD_PER_MILLION_BY_MODEL"


def configured_savings_rates(raw: str | None = None) -> dict[str, float]:
    """Parse operator-maintained USD savings per one million cache-read tokens."""
    value = os.environ.get(ENV_RATES, "") if raw is None else raw
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{ENV_RATES} must be a JSON object") from exc
    if not isinstance(parsed, dict) or any(
        not isinstance(model, str)
        or not model
        or not isinstance(rate, (int, float))
        or isinstance(rate, bool)
        or not math.isfinite(rate)
        or rate < 0
        for model, rate in parsed.items()
    ):
        raise ValueError(f"{ENV_RATES} must map model names to finite non-negative USD rates")
    return {model: float(rate) for model, rate in parsed.items()}


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        result = value.model_dump()
        return result if isinstance(result, dict) else {}
    if hasattr(value, "dict"):
        result = value.dict()
        return result if isinstance(result, dict) else {}
    return {}


def _cached_prompt_tokens(response: Any) -> int:
    usage = _as_dict(_as_dict(response).get("usage", getattr(response, "usage", None)))
    prompt_details = _as_dict(usage.get("prompt_tokens_details"))
    value = prompt_details.get("cached_tokens", usage.get("cache_read_input_tokens", 0))
    return value if type(value) is int and value > 0 else 0


def _identity(kwargs: dict[str, Any]) -> tuple[str | None, str | None]:
    params = _as_dict(kwargs.get("litellm_params"))
    metadata = _as_dict(params.get("metadata"))
    key_info = _as_dict(kwargs.get("user_api_key_dict"))
    alias = (
        kwargs.get("user_api_key_alias")
        or metadata.get("user_api_key_alias")
        or metadata.get("key_alias")
        or key_info.get("key_alias")
    )
    model = kwargs.get("model") or params.get("model")
    if not isinstance(alias, str) or alias not in ALLOWED_KEY_ALIASES:
        return None, None
    if not isinstance(model, str) or not model:
        return None, None
    return alias, model


class PromptCacheSavingsLogger(CustomLogger):
    """Observe successful requests without recording prompt/response content."""

    def __init__(self) -> None:
        super().__init__()
        self.savings_rates = configured_savings_rates()

    async def async_log_success_event(
        self, kwargs: dict[str, Any], response_obj: Any, start_time: Any, end_time: Any
    ) -> None:
        alias, model = _identity(kwargs)
        if alias is None or model is None:
            return
        cached_tokens = _cached_prompt_tokens(response_obj)
        if cached_tokens <= 0:
            return
        rate = self.savings_rates.get(model)
        if rate is None or rate <= 0:
            return
        PROMPT_CACHE_SAVINGS.labels(api_key_alias=alias, model=model).inc(
            cached_tokens * rate / 1_000_000
        )


prompt_cache_savings_logger = PromptCacheSavingsLogger()
