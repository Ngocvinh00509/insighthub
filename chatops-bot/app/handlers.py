"""Intent routing and safe Slack Block Kit replies for authenticated events."""
from __future__ import annotations

import asyncio
import json
import logging
import re
import urllib.error
import urllib.request
from typing import Any

from .config import get_settings
from .mcp_client import McpClient, McpError, McpServer

logger = logging.getLogger("chatops_bot.handlers")
SECRET_PATTERN = re.compile(r"(?i)(?:xox[baprs]-[\w-]+|(?:api[_-]?key|token|secret|password)\s*[:=]\s*\S+)")


def classify_intent(text: str) -> str | None:
    normalized = text.casefold()
    if "healthy" in normalized or "api status" in normalized:
        return "health"
    if "ingest" in normalized and ("hôm nay" in normalized or "hom nay" in normalized):
        return "ingestion"
    if "pod" in normalized and ("lỗi" in normalized or "loi" in normalized or "error" in normalized):
        return "pods"
    return None


def redact(value: str) -> str:
    return SECRET_PATTERN.sub("[REDACTED]", value)


def blocks(title: str, lines: list[str]) -> list[dict[str, Any]]:
    return [
        {"type": "header", "text": {"type": "plain_text", "text": title, "emoji": True}},
        {"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(f"• {redact(line)}" for line in lines)}},
    ]


async def handle_slack_event(payload: dict[str, Any]) -> None:
    event = payload.get("event")
    if not isinstance(event, dict) or event.get("type") != "app_mention" or event.get("bot_id"):
        return
    text, channel = event.get("text"), event.get("channel")
    if not isinstance(text, str) or not isinstance(channel, str):
        return
    await post_to_slack(channel, await build_reply(classify_intent(text)))


async def build_reply(intent: str | None) -> list[dict[str, Any]]:
    if intent == "health":
        return await health_reply()
    if intent == "ingestion":
        return await ingestion_reply()
    if intent == "pods":
        return await pods_reply()
    return blocks("🤖 InsightHub ChatOps", ["Hãy hỏi về health, số tài liệu ingest hôm nay, hoặc Pod đang lỗi."])


def prometheus_client() -> McpClient:
    settings = get_settings()
    return McpClient(McpServer(settings.prometheus_mcp_command, {"INSIGHTHUB_MCP_PROMETHEUS": "1", "INSIGHTHUB_MCP_TOOLS": "insighthub_health,prometheus_summary"}))


async def health_reply() -> list[dict[str, Any]]:
    try:
        health, requests, errors = await asyncio.gather(
            prometheus_client().call_tool("insighthub_health", {}),
            prometheus_client().call_tool("prometheus_summary", {"query": "requests_5m"}),
            prometheus_client().call_tool("prometheus_summary", {"query": "errors_5m"}),
        )
    except McpError:
        return blocks("⚠️ InsightHub health", ["Không thể đọc MCP telemetry vào lúc này."])
    return blocks("🩺 InsightHub health", [
        f"API live: {'✅' if health.get('live') else '❌'}; ready: {'✅' if health.get('ready') else '❌'}",
        f"Database ready: {'✅' if health.get('databaseReady') else '❌'}",
        f"HTTP requests (5 phút): {requests.get('value', 'không có dữ liệu')}",
        f"HTTP 5xx (5 phút): {errors.get('value', 'không có dữ liệu')}",
        "p95 latency: không có metric allowlisted.",
    ])


async def ingestion_reply() -> list[dict[str, Any]]:
    try:
        summary = await prometheus_client().call_tool("prometheus_summary", {"query": "documents"})
    except McpError:
        return blocks("⚠️ Ingestion hôm nay", ["Không thể đọc MCP telemetry vào lúc này."])
    return blocks("📥 Ingestion", ["Số ingest hôm nay: không có metric theo ngày trong MCP allowlist.", f"Tổng tài liệu hiện tại: {summary.get('value', 'không có dữ liệu')}"])


async def pods_reply() -> list[dict[str, Any]]:
    settings = get_settings()
    if settings.kubernetes_mcp_command is None:
        return blocks("⚠️ Pod triage", ["Kubernetes MCP chưa được cấu hình cho bot."])
    client = McpClient(McpServer(settings.kubernetes_mcp_command, {}))
    try:
        pods = await client.call_tool("list_pods", {"namespace": settings.kubernetes_namespace})
        await client.call_tool("get_events", {"namespace": settings.kubernetes_namespace})
    except McpError:
        return blocks("⚠️ Pod triage", ["Không thể đọc Kubernetes MCP vào lúc này."])
    values = pods.get("pods")
    if not isinstance(values, list):
        return blocks("⚠️ Pod triage", ["Kubernetes MCP trả dữ liệu không hợp lệ."])
    failures = [str(item) for item in values if any(flag in str(item) for flag in ("CrashLoopBackOff", "Pending", "restartCount"))]
    return blocks("🧯 Pod triage", failures or ["✅ Không có Pod lỗi được MCP báo cáo."])


async def post_to_slack(channel: str, message_blocks: list[dict[str, Any]]) -> None:
    token = get_settings().slack_bot_token
    if not token:
        logger.warning("Slack token is not configured")
        return
    data = json.dumps({"channel": channel, "blocks": message_blocks}).encode()
    request = urllib.request.Request("https://slack.com/api/chat.postMessage", data=data, method="POST", headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"})
    try:
        await asyncio.to_thread(urllib.request.urlopen, request, timeout=2)
    except (urllib.error.URLError, TimeoutError):
        logger.warning("Slack reply delivery failed")
