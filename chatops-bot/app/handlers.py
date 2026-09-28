"""Intent routing and safe Slack Block Kit replies for authenticated events."""
from __future__ import annotations

import asyncio
import json
import logging
import re
import urllib.error
import urllib.request
from typing import Any

from .authorization import PermissionDenied, PermissionPolicy, authorize_intent
from .config import get_settings
from .mcp_client import McpClient, McpError, McpServer
from .processing import PermanentSlackProcessingError, RetryableSlackProcessingError

logger = logging.getLogger("chatops_bot.handlers")
SECRET_PATTERN = re.compile(r"(?i)(?:xox[baprs]-[\w-]+|(?:api[_-]?key|token|secret|password)\s*[:=]\s*\S+)")


def classify_intent(text: str) -> str | None:
    normalized = text.casefold()
    if any(phrase in normalized for phrase in ("healthy", "health", "api status", "system status")):
        return "health"
    if "ingest" in normalized and any(
        phrase in normalized
        for phrase in ("hôm nay", "hom nay", "count", "status", "how many", "show")
    ):
        return "ingestion"
    if "pod" in normalized and any(
        phrase in normalized
        for phrase in ("lỗi", "loi", "error", "failing", "fail", "problem")
    ):
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
    text, channel, user_id = event.get("text"), event.get("channel"), event.get("user")
    if not isinstance(text, str) or not isinstance(channel, str) or not isinstance(user_id, str):
        return
    await post_to_slack(channel, await build_reply(classify_intent(text), user_id))


async def build_reply(intent: str | None, user_id: str) -> list[dict[str, Any]]:
    if intent is None:
        return blocks("🤖 InsightHub ChatOps", ["Hãy hỏi về health, số ingestion đã xử lý, hoặc Pod đang lỗi."])
    try:
        settings = get_settings()
        authorize_intent(
            PermissionPolicy(
                read_users=settings.read_users,
                diagnostic_users=settings.diagnostic_users,
                mutation_users=settings.mutation_users,
            ),
            user_id,
            intent,
        )
    except PermissionDenied as exc:
        raise PermanentSlackProcessingError("permission_denied") from exc
    if intent == "health":
        return await health_reply()
    if intent == "ingestion":
        return await ingestion_reply()
    if intent == "pods":
        return await pods_reply()
    raise PermanentSlackProcessingError("intent_not_allowed")


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
    except McpError as exc:
        raise RetryableSlackProcessingError("prometheus_unavailable") from exc
    return blocks("🩺 InsightHub health", [
        f"API live: {'✅' if health.get('live') else '❌'}; ready: {'✅' if health.get('ready') else '❌'}",
        f"Database ready: {'✅' if health.get('databaseReady') else '❌'}",
        f"HTTP requests (5 phút): {requests.get('value', 'không có dữ liệu')}",
        f"HTTP 5xx (5 phút): {errors.get('value', 'không có dữ liệu')}",
        "Nguồn dữ liệu: Prometheus MCP read-only.",
    ])


async def ingestion_reply() -> list[dict[str, Any]]:
    try:
        summary = await prometheus_client().call_tool(
            "prometheus_summary", {"query": "ingestion_jobs_24h"}
        )
    except McpError as exc:
        raise RetryableSlackProcessingError("prometheus_unavailable") from exc
    return blocks(
        "📥 Ingestion",
        [
            f"Jobs xử lý thành công (24 giờ gần nhất): {summary.get('value', 'không có dữ liệu')}",
            "Nguồn dữ liệu: counter ingestion worker qua Prometheus MCP.",
        ],
    )


async def pods_reply() -> list[dict[str, Any]]:
    settings = get_settings()
    if settings.kubernetes_mcp_command is None:
        raise PermanentSlackProcessingError("kubernetes_mcp_not_configured")
    client = McpClient(McpServer(settings.kubernetes_mcp_command, {}))
    try:
        pods = await client.call_tool("list_pods", {"namespace": settings.kubernetes_namespace})
    except McpError as exc:
        raise RetryableSlackProcessingError("kubernetes_mcp_unavailable") from exc
    values = pods.get("pods")
    if not isinstance(values, list):
        raise RetryableSlackProcessingError("kubernetes_mcp_invalid_response")
    failures = [format_pod_failure(item) for item in values if is_pod_unhealthy(item)]
    return blocks("🧯 Pod triage", failures or ["✅ Không có Pod lỗi được MCP báo cáo."])


def is_pod_unhealthy(pod: Any) -> bool:
    if not isinstance(pod, dict):
        return False
    phase = pod.get("phase")
    restarts = pod.get("restart_count", pod.get("restartCount", 0))
    reason = pod.get("reason")
    return (
        phase not in {"Running", "Succeeded"}
        or isinstance(restarts, int) and restarts > 0
        or reason in {"CrashLoopBackOff", "Error", "ImagePullBackOff", "OOMKilled"}
    )


def format_pod_failure(pod: dict[str, Any]) -> str:
    name = pod.get("name")
    phase = pod.get("phase", "unknown")
    reason = pod.get("reason", "unspecified")
    restarts = pod.get("restart_count", pod.get("restartCount", 0))
    if not isinstance(name, str) or not name:
        return "Pod không có tên hợp lệ từ Kubernetes MCP."
    return f"{name}: phase={phase}, reason={reason}, restarts={restarts}"


async def post_to_slack(channel: str, message_blocks: list[dict[str, Any]]) -> None:
    token = get_settings().slack_bot_token
    if not token:
        raise PermanentSlackProcessingError("slack_bot_token_not_configured")
    data = json.dumps({"channel": channel, "blocks": message_blocks}).encode()
    request = urllib.request.Request("https://slack.com/api/chat.postMessage", data=data, method="POST", headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"})
    try:
        response = await asyncio.to_thread(urllib.request.urlopen, request, timeout=2)
        with response:
            body = await asyncio.to_thread(response.read)
        result = json.loads(body)
        if not isinstance(result, dict) or result.get("ok") is not True:
            raise RetryableSlackProcessingError("slack_reply_rejected")
    except urllib.error.HTTPError as exc:
        if exc.code == 429 or exc.code >= 500:
            raise RetryableSlackProcessingError("slack_reply_unavailable") from exc
        raise PermanentSlackProcessingError("slack_reply_rejected") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RetryableSlackProcessingError("slack_reply_unavailable") from exc
