"""ARQ worker for bounded ChatOps MCP processing and Slack replies."""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

from arq import Retry

from app.config import get_settings
from app.audit import log_operation
from app.authorization import required_tier
from app.handlers import handle_slack_event
from app.processing import PermanentSlackProcessingError, RetryableSlackProcessingError
from app.queue import redis_settings

logger = logging.getLogger("chatops_bot.worker")
MAX_ATTEMPTS = 4


def emit(event: str, event_id: str, **fields: Any) -> None:
    logger.info(
        json.dumps(
            {
                "event": event,
                "event_id": event_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **fields,
            }
        )
    )


async def process_slack_event(ctx: dict[str, Any], event_id: str, payload: dict[str, Any]) -> None:
    """Run only after the Events endpoint has authenticated and acknowledged Slack."""
    attempt = ctx.get("job_try", 1)
    started_at = time.perf_counter()
    event = payload.get("event") if isinstance(payload, dict) else None
    user_id = event.get("user") if isinstance(event, dict) and isinstance(event.get("user"), str) else None
    text = event.get("text") if isinstance(event, dict) and isinstance(event.get("text"), str) else ""
    from app.handlers import classify_intent
    intent = classify_intent(text)
    action = f"intent.{intent}" if intent else "intent.unknown"
    try:
        tier = required_tier(action).value
    except Exception:  # noqa: BLE001 - unknown actions are audit metadata only
        tier = "unknown"
    authorization_result = "allowed"
    execution_result = "completed"
    error_category = None
    try:
        await handle_slack_event(payload)
    except PermanentSlackProcessingError as exc:
        authorization_result = "denied" if "permission" in str(exc) else "not_applicable"
        execution_result = "failed"
        error_category = "permanent"
        emit("slack_event_permanent_failure", event_id, attempt=attempt)
        return
    except RetryableSlackProcessingError:
        execution_result = "retrying" if attempt < MAX_ATTEMPTS else "failed"
        error_category = "transient"
        if attempt < MAX_ATTEMPTS:
            delay = 2 ** (attempt - 1)
            emit("slack_event_retry", event_id, attempt=attempt, retry_in_seconds=delay)
            raise Retry(defer=delay) from None
        emit("slack_event_retry_exhausted", event_id, attempt=attempt)
        return
    except Exception:  # noqa: BLE001 - unexpected worker failures are retryable but sanitized
        execution_result = "retrying" if attempt < MAX_ATTEMPTS else "failed"
        error_category = "unexpected"
        if attempt < MAX_ATTEMPTS:
            delay = 2 ** (attempt - 1)
            emit("slack_event_retry", event_id, attempt=attempt, retry_in_seconds=delay)
            raise Retry(defer=delay) from None
        emit("slack_event_retry_exhausted", event_id, attempt=attempt)
        return
    else:
        emit("slack_event_completed", event_id, attempt=attempt)
    finally:
        log_operation(
            request_id=event_id,
            slack_user_id=user_id,
            intent=intent,
            requested_action=action,
            permission_tier=tier,
            authorization_result=authorization_result,
            execution_result=execution_result,
            duration_ms=(time.perf_counter() - started_at) * 1000,
            error_category=error_category,
        )


class WorkerSettings:
    functions = (process_slack_event,)
    queue_name = get_settings().chatops_queue
    redis_settings = redis_settings()
    max_jobs = 4
    job_timeout = 30
    max_tries = MAX_ATTEMPTS
    keep_result = 24 * 60 * 60
    log_results = False
