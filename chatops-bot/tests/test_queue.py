import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import queue


def test_enqueue_uses_stable_event_id_for_deduplication(monkeypatch: pytest.MonkeyPatch) -> None:
    pool = SimpleNamespace(enqueue_job=AsyncMock(return_value=object()), aclose=AsyncMock())
    monkeypatch.setattr(queue, "get_settings", lambda: SimpleNamespace(chatops_queue="test:chatops"))
    monkeypatch.setattr(queue, "redis_settings", lambda: object())
    monkeypatch.setattr(queue, "create_pool", AsyncMock(return_value=pool))
    payload = {"event_id": "Ev123", "event": {"type": "app_mention"}}

    queued = asyncio.run(queue.enqueue_slack_event("Ev123", payload))

    assert queued is True
    pool.enqueue_job.assert_awaited_once_with(
        "process_slack_event",
        "Ev123",
        payload,
        _job_id="test:chatops:event:Ev123",
        _queue_name="test:chatops",
        _expires=queue.EVENT_TTL_SECONDS,
    )


def test_enqueue_reports_duplicate_when_arq_job_exists(monkeypatch: pytest.MonkeyPatch) -> None:
    pool = SimpleNamespace(enqueue_job=AsyncMock(return_value=None), aclose=AsyncMock())
    monkeypatch.setattr(queue, "get_settings", lambda: SimpleNamespace(chatops_queue="test:chatops"))
    monkeypatch.setattr(queue, "redis_settings", lambda: object())
    monkeypatch.setattr(queue, "create_pool", AsyncMock(return_value=pool))

    queued = asyncio.run(queue.enqueue_slack_event("Ev-duplicate", {"event_id": "Ev-duplicate"}))

    assert queued is False
