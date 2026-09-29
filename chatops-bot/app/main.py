"""HTTP entry point for the InsightHub Slack Events adapter."""
from __future__ import annotations

import json

from fastapi import FastAPI, HTTPException, Request, status

from .config import get_settings
from .queue import ChatOpsQueueUnavailable, claim_shared_slack_replay, enqueue_slack_event
from .security import SlackVerificationError, slack_request_fingerprint, verify_slack_signature

app = FastAPI(title="InsightHub ChatOps", version="0.3.0")


@app.get("/healthz")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/slack/events", status_code=status.HTTP_200_OK)
async def slack_events(request: Request) -> dict[str, str]:
    """Authenticate exact request bytes before inspecting the Slack payload."""
    raw_body = await request.body()
    settings = get_settings()
    try:
        verify_slack_signature(
            signing_secret=settings.slack_signing_secret,
            timestamp=request.headers.get("X-Slack-Request-Timestamp"),
            signature=request.headers.get("X-Slack-Signature"),
            raw_body=raw_body,
        )
    except SlackVerificationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    try:
        replay_claimed = await claim_shared_slack_replay(
            slack_request_fingerprint(
                request.headers["X-Slack-Request-Timestamp"],
                request.headers["X-Slack-Signature"],
                raw_body,
            )
        )
    except ChatOpsQueueUnavailable as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="chatops_replay_store_unavailable") from exc
    if not replay_claimed:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="replayed_slack_request")
    try:
        payload = json.loads(raw_body)
    except (TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_payload") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_payload")
    if payload.get("type") == "url_verification":
        challenge = payload.get("challenge")
        if not isinstance(challenge, str):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_challenge")
        return {"challenge": challenge}
    event_id = payload.get("event_id")
    if not isinstance(event_id, str) or not event_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_event_id")
    try:
        await enqueue_slack_event(event_id, payload)
    except ChatOpsQueueUnavailable as exc:
        # Do not ACK work that Redis did not accept durably; Slack can retry.
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="chatops_queue_unavailable") from exc
    # ACK only after Redis accepted the stable event-id job. MCP work runs in worker.py.
    return {"ok": "true"}
