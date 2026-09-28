"""Day 5 verifier contract tests using application security primitives."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(os.environ["INSIGHTHUB_REPO_ROOT"])
sys.path.insert(0, str(REPO_ROOT / "chatops-bot"))

from app.approval import ApprovalError, ApprovalStore
from app.authorization import ApprovalRequired, PermissionDenied, PermissionPolicy, authorize_action
from app.security import SlackReplayStore, SlackVerificationError, verify_slack_signature

POLICY = PermissionPolicy(
    read_users=frozenset({"U-read"}),
    diagnostic_users=frozenset({"U-diagnostic"}),
    mutation_users=frozenset({"U-requester"}),
    approver_users=frozenset({"U-approver"}),
)
ACTION = "kubernetes.scale_deployment"
ARGUMENTS = {"namespace": "insighthub-dev", "deployment": "api", "replicas": 2}


def record(event_id: str, action: str, decision: str, user: str) -> None:
    path = Path(os.environ["INSIGHTHUB_VERIFY_OBSERVATIONS"])
    run_id = os.environ["INSIGHTHUB_VERIFY_RUN_ID"]
    payload = {"run_id": run_id, "events": []}
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
    payload["events"].append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_id": event_id,
        "action": action,
        "decision": decision,
        "user": user,
        "test_run_id": run_id,
    })
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_permission_denied() -> None:
    with pytest.raises(PermissionDenied, match="permission_denied"):
        authorize_action(POLICY, "U-untrusted", "intent.health")
    record("permission-denied", "intent.health", "denied", "U-untrusted")


def test_approval_required() -> None:
    with pytest.raises(ApprovalRequired, match="approval_required"):
        authorize_action(POLICY, "U-requester", ACTION, ARGUMENTS)
    record("approval-required", ACTION, "approval_required", "U-requester")


def test_approval_bound_to_action() -> None:
    store = ApprovalStore()
    pending = store.create(POLICY, "U-requester", ACTION, ARGUMENTS, expires_at=2_000, now=1_000)
    store.approve(POLICY, pending.request_id, "U-approver", now=1_001)
    with pytest.raises(ApprovalError, match="approval_binding_mismatch"):
        store.consume(pending.request_id, "U-requester", ACTION, {**ARGUMENTS, "replicas": 3}, now=1_002)
    record("approval-binding", ACTION, "denied", "U-requester")


def test_duplicate_event() -> None:
    store = SlackReplayStore(ttl_seconds=300)
    assert store.claim("event-fingerprint", now=1_000)
    assert not store.claim("event-fingerprint", now=1_001)
    record("duplicate-event", "slack.event", "denied", "U-test")


def test_invalid_signature() -> None:
    raw_body = b'{"type":"url_verification","challenge":"test"}'
    timestamp = "1000"
    good = hmac.new(b"correct-secret", b"v0:" + timestamp.encode() + b":" + raw_body, hashlib.sha256).hexdigest()
    with pytest.raises(SlackVerificationError, match="invalid_slack_signature"):
        verify_slack_signature(
            signing_secret="wrong-secret", timestamp=timestamp, signature=f"v0={good}",
            raw_body=raw_body, now=1_000, replay_store=SlackReplayStore(),
        )
    record("invalid-signature", "slack.signature", "denied", "U-test")
