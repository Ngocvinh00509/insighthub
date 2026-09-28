"""Slack request authentication helpers."""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import time
from collections import OrderedDict
from dataclasses import dataclass
from threading import Lock

MAX_SLACK_TIMESTAMP_AGE_SECONDS = 300
SLACK_SIGNATURE_PATTERN = re.compile(r"v0=[0-9a-f]{64}")


@dataclass(frozen=True)
class SlackVerificationError(Exception):
    status_code: int
    detail: str


class ConfirmationTokenError(ValueError):
    """A confirmation token is missing, invalid, expired, or already consumed."""


class SlackReplayStore:
    """Bounded, in-process replay cache for successfully authenticated events.

    A production deployment should use a shared Redis implementation so replicas
    reject the same Slack delivery consistently. Keeping this small in-memory
    implementation makes a single-process local bot fail closed against replay
    without storing request bodies or credentials.
    """

    def __init__(
        self,
        ttl_seconds: int = MAX_SLACK_TIMESTAMP_AGE_SECONDS,
        max_entries: int = 10_000,
    ) -> None:
        if ttl_seconds <= 0 or max_entries <= 0:
            raise ValueError("ttl_seconds and max_entries must be positive")
        self._ttl_seconds = ttl_seconds
        self._max_entries = max_entries
        self._entries: OrderedDict[str, float] = OrderedDict()
        self._lock = Lock()

    def claim(self, fingerprint: str, *, now: float | None = None) -> bool:
        """Atomically reserve a fingerprint; return False when it was seen recently."""
        current_time = time.time() if now is None else now
        with self._lock:
            expired = [
                key for key, expires_at in self._entries.items() if expires_at <= current_time
            ]
            for key in expired:
                del self._entries[key]
            if fingerprint in self._entries:
                return False
            self._entries[fingerprint] = current_time + self._ttl_seconds
            while len(self._entries) > self._max_entries:
                self._entries.popitem(last=False)
            return True


slack_replay_store = SlackReplayStore()


def slack_request_fingerprint(timestamp: str, signature: str, raw_body: bytes) -> str:
    """Build an opaque replay key without retaining credentials or request data."""
    base = b"v0:" + timestamp.encode("ascii") + b":" + raw_body
    return hashlib.sha256(base + b":" + signature.encode("ascii")).hexdigest()


class ConfirmationTokenStore:
    """One-time, in-memory confirmation tokens for explicitly approved actions."""

    def __init__(self, ttl_seconds: int = 300) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        self._ttl_seconds = ttl_seconds
        self._tokens: dict[str, tuple[str, float]] = {}

    def issue(self, action: str, *, now: float | None = None) -> str:
        if not action:
            raise ValueError("action must not be empty")
        token = secrets.token_urlsafe(32)
        issued_at = time.time() if now is None else now
        self._tokens[token] = (action, issued_at + self._ttl_seconds)
        return token

    def confirm(self, token: str, *, now: float | None = None) -> str:
        record = self._tokens.pop(token, None)
        if record is None:
            raise ConfirmationTokenError("invalid_confirmation_token")
        action, expires_at = record
        current_time = time.time() if now is None else now
        if current_time > expires_at:
            raise ConfirmationTokenError("expired_confirmation_token")
        return action


def verify_slack_signature(
    *,
    signing_secret: str,
    timestamp: str | None,
    signature: str | None,
    raw_body: bytes,
    now: float | None = None,
    replay_store: SlackReplayStore | None = None,
) -> None:
    """Raise when a Slack request is unsigned, replayed, or tampered with."""
    if not signing_secret:
        raise SlackVerificationError(503, "slack_signing_secret_not_configured")
    if not timestamp or not signature:
        raise SlackVerificationError(401, "invalid_slack_signature")
    if not signature.isascii() or not SLACK_SIGNATURE_PATTERN.fullmatch(signature):
        raise SlackVerificationError(401, "invalid_slack_signature")
    if not timestamp.isascii() or not timestamp.isdecimal():
        raise SlackVerificationError(400, "invalid_slack_timestamp")
    timestamp_value = int(timestamp)
    current_time = time.time() if now is None else now
    if abs(current_time - timestamp_value) > MAX_SLACK_TIMESTAMP_AGE_SECONDS:
        raise SlackVerificationError(401, "expired_slack_timestamp")
    base = b"v0:" + timestamp.encode("ascii") + b":" + raw_body
    digest = hmac.new(signing_secret.encode("utf-8"), base, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(f"v0={digest}", signature):
        raise SlackVerificationError(401, "invalid_slack_signature")
    fingerprint = slack_request_fingerprint(timestamp, signature, raw_body)
    store = slack_replay_store if replay_store is None else replay_store
    if not store.claim(fingerprint, now=current_time):
        raise SlackVerificationError(401, "replayed_slack_request")
