import asyncio
import hashlib
import hmac
import json
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from arq import Retry
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app
from app.processing import PermanentSlackProcessingError, RetryableSlackProcessingError
from worker import process_slack_event

SECRET = "test-signing-secret"


def signed_headers(raw_body: bytes, timestamp: int) -> dict[str, str]:
    base = f"v0:{timestamp}:".encode() + raw_body
    signature = "v0=" + hmac.new(SECRET.encode(), base, hashlib.sha256).hexdigest()
    return {
        "X-Slack-Request-Timestamp": str(timestamp),
        "X-Slack-Signature": signature,
        "Content-Type": "application/json",
    }


def event_payload(event_id: str = "Ev-day5-1") -> bytes:
    return json.dumps(
        {
            "type": "event_callback",
            "event_id": event_id,
            "event": {"type": "app_mention", "user": "U123", "channel": "C123", "text": "check health"},
        }
    ).encode()


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("SLACK_SIGNING_SECRET", SECRET)
    async def claim_replay(_: str) -> bool:
        return True
    monkeypatch.setattr("app.main.claim_shared_slack_replay", claim_replay)
    return TestClient(app)


def test_ack_is_fast_and_does_not_run_processing_in_request(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    queued: list[str] = []

    async def enqueue(event_id: str, payload: dict) -> bool:
        await asyncio.sleep(0.02)
        queued.append(event_id)
        return True

    monkeypatch.setattr("app.main.enqueue_slack_event", enqueue)
    raw_body = event_payload()
    started_at = time.perf_counter()
    response = client.post("/slack/events", content=raw_body, headers=signed_headers(raw_body, int(time.time())))

    assert response.status_code == 200
    assert response.json() == {"ok": "true"}
    assert queued == ["Ev-day5-1"]
    assert time.perf_counter() - started_at < 3


def test_duplicate_slack_event_is_acknowledged_without_second_job(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    async def enqueue(event_id: str, payload: dict) -> bool:
        calls.append(event_id)
        return len(calls) == 1

    monkeypatch.setattr("app.main.enqueue_slack_event", enqueue)
    raw_body = event_payload("Ev-day5-duplicate")
    first = client.post("/slack/events", content=raw_body, headers=signed_headers(raw_body, int(time.time())))
    second = client.post("/slack/events", content=raw_body, headers=signed_headers(raw_body, int(time.time()) - 1))

    assert first.status_code == second.status_code == 200
    assert calls == ["Ev-day5-duplicate", "Ev-day5-duplicate"]


def test_worker_retries_retryable_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    handler = AsyncMock(side_effect=RetryableSlackProcessingError("temporary"))
    monkeypatch.setattr("worker.handle_slack_event", handler)

    with pytest.raises(Retry) as error:
        asyncio.run(process_slack_event({"job_try": 1}, "Ev-retry", {}))

    assert error.value.defer_score == 1000
    handler.assert_awaited_once_with({})


def test_worker_does_not_retry_permanent_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    handler = AsyncMock(side_effect=PermanentSlackProcessingError("bad_configuration"))
    monkeypatch.setattr("worker.handle_slack_event", handler)

    asyncio.run(process_slack_event({"job_try": 1}, "Ev-permanent", {}))

    handler.assert_awaited_once_with({})
