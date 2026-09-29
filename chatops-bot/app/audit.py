"""
InsightHub ChatOps Bot — Audit log (SKELETON)

Mọi tool call của bot PHẢI được ghi audit. Đây là yêu cầu bảo mật cốt lõi:
khi AI agent có quyền chạm vào hạ tầng, phải có dấu vết kiểm toán.

TODO Day 5: hoàn thiện theo gợi ý dưới.
"""
import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("chatops-bot.audit")
SENSITIVE_PATTERN = re.compile(
    r"(?i)(xox[baprs]-[\w-]+|bearer\s+\S+|(?:signing[_ -]?secret|token|authorization|webhook(?:_url)?|password)\s*[:=]\s*\S+|https://hooks\.slack\.com/\S+)"
)


def redact(value: str | None) -> str | None:
    if value is None:
        return None
    return "[REDACTED]" if SENSITIVE_PATTERN.search(value) else value


def log_operation(
    *,
    request_id: str,
    slack_user_id: str | None,
    intent: str | None,
    requested_action: str,
    permission_tier: str,
    authorization_result: str,
    execution_result: str,
    duration_ms: float,
    approval_id: str | None = None,
    error_category: str | None = None,
) -> None:
    """Emit one investigation-safe JSON record; never accept raw request bodies."""
    record: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request_id": request_id,
        "slack_user_id": redact(slack_user_id),
        "intent": redact(intent),
        "requested_action": redact(requested_action),
        "permission_tier": permission_tier,
        "authorization_result": authorization_result,
        "approval_id": redact(approval_id),
        "execution_result": execution_result,
        "duration_ms": round(max(duration_ms, 0), 3),
        "error_category": redact(error_category),
    }
    logger.info("AUDIT %s", json.dumps(record, ensure_ascii=False, separators=(",", ":")))


def log_approval_event(
    request_id: str,
    action: str,
    requester_user_id: str,
    decision: str,
    approver_user_id: str | None = None,
) -> None:
    """Record approval transitions without exposing raw mutation arguments."""
    logger.info(
        "AUDIT %s",
        json.dumps(
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "request_id": request_id,
                "action": action,
                "requester_user_id": requester_user_id,
                "approver_user_id": approver_user_id,
                "decision": decision,
            },
            ensure_ascii=False,
        ),
    )


def log_tool_call(
    user: str,
    tool: str,
    args: dict,
    result_summary: str,
    approved: bool = True,
) -> None:
    """
    Ghi 1 dòng audit cho mỗi tool call.

    TODO Day 5:
    - Ghi ra file hoặc stdout dạng structured JSON (mỗi dòng 1 record).
    - Trong production thật: đẩy sang log aggregator (Loki...).
    - Trường tối thiểu: timestamp, user, tool, args, kết quả, approved.

    Ví dụ record:
      {"ts": "...", "user": "U123", "tool": "kubectl_get_pods",
       "args": {...}, "result": "5 pods Running", "approved": true}
    """
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "user": user,
        "tool": tool,
        "args": args,
        "result": result_summary,
        "approved": approved,
    }
    # TODO: thay bằng ghi file / gửi log aggregator
    logger.info("AUDIT %s", json.dumps(record, ensure_ascii=False))
