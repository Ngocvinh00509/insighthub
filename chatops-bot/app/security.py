"""Slack request authentication helpers."""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass

MAX_SLACK_TIMESTAMP_AGE_SECONDS = 300


@dataclass(frozen=True)
class SlackVerificationError(Exception):
    status_code: int
    detail: str


class ConfirmationTokenError(ValueError):
    """A confirmation token is missing, invalid, expired, or already consumed."""


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
) -> None:
    """Raise when a Slack request is unsigned, replayed, or tampered with."""
    if not signing_secret:
        raise SlackVerificationError(503, "slack_signing_secret_not_configured")
    if not timestamp or not signature:
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
