import hashlib
import hmac
import json
import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.handlers import blocks, classify_intent
from app.main import app

SECRET = "test-signing-secret"


def signed_headers(raw_body: bytes, timestamp: int, secret: str = SECRET) -> dict[str, str]:
    base = f"v0:{timestamp}:".encode() + raw_body
    signature = "v0=" + hmac.new(secret.encode(), base, hashlib.sha256).hexdigest()
    return {
        "X-Slack-Request-Timestamp": str(timestamp),
        "X-Slack-Signature": signature,
        "Content-Type": "application/json",
    }


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("SLACK_SIGNING_SECRET", SECRET)
    return TestClient(app)


def test_accepts_valid_signature_and_returns_challenge(client: TestClient) -> None:
    raw_body = json.dumps({"type": "url_verification", "challenge": "challenge-value"}).encode()
    response = client.post(
        "/slack/events",
        content=raw_body,
        headers=signed_headers(raw_body, int(time.time())),
    )
    assert response.status_code == 200
    assert response.json() == {"challenge": "challenge-value"}


def test_rejects_invalid_signature(client: TestClient) -> None:
    raw_body = b'{"type":"event_callback"}'
    response = client.post(
        "/slack/events",
        content=raw_body,
        headers=signed_headers(raw_body, int(time.time()), "wrong-secret"),
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "invalid_slack_signature"


def test_rejects_expired_timestamp(client: TestClient) -> None:
    raw_body = b'{"type":"event_callback"}'
    response = client.post(
        "/slack/events",
        content=raw_body,
        headers=signed_headers(raw_body, int(time.time()) - 301),
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "expired_slack_timestamp"


def test_classifies_the_three_chatops_intents() -> None:
    assert classify_intent("InsightHub có healthy không?") == "health"
    assert classify_intent("Hôm nay ingest bao nhiêu doc?") == "ingestion"
    assert classify_intent("Pod nào đang lỗi?") == "pods"


def test_block_kit_output_redacts_token_like_values() -> None:
    response_blocks = blocks("🧪 Test", ["token=xoxb-example-secret"])
    assert response_blocks[0]["type"] == "header"
    assert "[REDACTED]" in response_blocks[1]["text"]["text"]
    assert "xoxb-example-secret" not in response_blocks[1]["text"]["text"]
