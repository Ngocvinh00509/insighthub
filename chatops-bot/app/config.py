"""Configuration for the Slack adapter, kept outside source control."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    slack_signing_secret: str
    slack_bot_token: str | None
    prometheus_mcp_command: tuple[str, ...]
    kubernetes_mcp_command: tuple[str, ...] | None
    kubernetes_namespace: str


def get_settings() -> Settings:
    """Read the process environment for each request to support secret rotation."""
    return Settings(
        slack_signing_secret=os.environ.get("SLACK_SIGNING_SECRET", ""),
        slack_bot_token=os.environ.get("SLACK_BOT_TOKEN"),
        prometheus_mcp_command=_command_from_env("PROMETHEUS_MCP_COMMAND", ("node", "tools/mcp/src/server.mjs")),
        kubernetes_mcp_command=_optional_command_from_env("KUBERNETES_MCP_COMMAND"),
        kubernetes_namespace=os.environ.get("KUBERNETES_MCP_NAMESPACE", "insighthub-dev"),
    )


def _command_from_env(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    return _optional_command_from_env(name) or default


def _optional_command_from_env(name: str) -> tuple[str, ...] | None:
    """Commands are JSON argv arrays; subprocess execution never invokes a shell."""
    raw = os.environ.get(name)
    if not raw:
        return None
    try:
        command = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{name} must be a JSON argv array") from exc
    if not isinstance(command, list) or not command or not all(isinstance(item, str) and item for item in command):
        raise ValueError(f"{name} must be a non-empty JSON argv array")
    return tuple(command)
