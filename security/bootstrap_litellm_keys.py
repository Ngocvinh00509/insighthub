"""Create the three InsightHub LiteLLM virtual keys with bounded budgets.

Run after the LiteLLM database migration has completed. Key material is supplied via
environment variables and is never written to disk or printed by this script.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


KEYS = (
    ("insighthub-app-key", "INSIGHTHUB_APP_LITELLM_KEY", 5.00, "1d"),
    ("chatops-bot-key", "CHATOPS_BOT_LITELLM_KEY", 2.00, "1d"),
    ("coding-workflow-key", "CODING_WORKFLOW_LITELLM_KEY", 10.00, "30d"),
)


def create_key(proxy_url: str, master_key: str, alias: str, key: str, budget: float, duration: str) -> None:
    if not key.startswith("sk-"):
        raise ValueError(f"{alias} must use an sk- prefixed LiteLLM virtual key")
    body = json.dumps(
        {
            "key": key,
            "key_alias": alias,
            "models": ["insighthub-chat", "insighthub-embedding"],
            "max_budget": budget,
            "budget_duration": duration,
        }
    ).encode()
    request = urllib.request.Request(
        proxy_url.rstrip("/") + "/key/generate",
        data=body,
        method="POST",
        headers={"Authorization": f"Bearer {master_key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status not in {200, 201}:
                raise RuntimeError("LiteLLM key bootstrap failed")
    except urllib.error.HTTPError as exc:
        if exc.code == 400:
            # A repeated key value is already present; avoid rotating it unexpectedly.
            return
        raise RuntimeError("LiteLLM key bootstrap failed") from exc


def main() -> None:
    proxy_url = os.environ.get("LITELLM_PROXY_URL", "http://litellm:4000")
    master_key = os.environ["LITELLM_MASTER_KEY"]
    if not master_key.startswith("sk-"):
        raise ValueError("LITELLM_MASTER_KEY must use an sk- prefix")
    for alias, variable, budget, duration in KEYS:
        create_key(proxy_url, master_key, alias, os.environ[variable], budget, duration)


if __name__ == "__main__":
    main()
