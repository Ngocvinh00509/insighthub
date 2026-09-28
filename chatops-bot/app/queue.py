"""Durable, idempotent ARQ enqueue for authenticated Slack events."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

from arq import create_pool
from arq.connections import RedisSettings

from .config import get_settings
from .security import MAX_SLACK_TIMESTAMP_AGE_SECONDS

logger = logging.getLogger("chatops_bot.queue")
EVENT_TTL_SECONDS = 24 * 60 * 60


class ChatOpsQueueUnavailable(RuntimeError):
    """Redis did not durably acknowledge a Slack event job."""


def redis_settings() -> RedisSettings:
    settings = RedisSettings.from_dsn(get_settings().redis_url)
    settings.conn_timeout = 0.5
    settings.conn_retries = 0
    return settings


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


async def enqueue_slack_event(event_id: str, payload: dict[str, Any]) -> bool:
    """Queue an event once; False means its stable ARQ job already exists."""
    pool = None
    settings = get_settings()
    try:
        async with asyncio.timeout(0.75):
            pool = await create_pool(redis_settings())
            job = await pool.enqueue_job(
                "process_slack_event",
                event_id,
                payload,
                _job_id=f"{settings.chatops_queue}:event:{event_id}",
                _queue_name=settings.chatops_queue,
                _expires=EVENT_TTL_SECONDS,
            )
            emit("slack_event_enqueued" if job else "slack_event_duplicate", event_id)
            return job is not None
    except Exception:  # noqa: BLE001 - do not expose Redis details to Slack
        emit("slack_event_enqueue_failed", event_id)
        raise ChatOpsQueueUnavailable() from None
    finally:
        if pool is not None:
            try:
                async with asyncio.timeout(0.1):
                    await pool.aclose()
            except Exception:  # noqa: BLE001 - cleanup must not change acknowledgement
                logger.warning("chatops_queue_cleanup_failed")


async def claim_shared_slack_replay(fingerprint: str) -> bool:
    """Atomically claim an authenticated delivery across all Redis-connected replicas."""
    pool = None
    try:
        async with asyncio.timeout(0.75):
            pool = await create_pool(redis_settings())
            result = await pool.set(
                f"{get_settings().chatops_queue}:replay:{fingerprint}",
                "1",
                ex=MAX_SLACK_TIMESTAMP_AGE_SECONDS,
                nx=True,
            )
            return bool(result)
    except Exception:  # noqa: BLE001 - fail closed if replay protection is unavailable
        raise ChatOpsQueueUnavailable() from None
    finally:
        if pool is not None:
            try:
                async with asyncio.timeout(0.1):
                    await pool.aclose()
            except Exception:  # noqa: BLE001 - no secret or backend details in logs
                logger.warning("chatops_replay_cleanup_failed")
