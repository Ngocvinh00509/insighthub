"""HTTP entry point for the InsightHub Slack Events adapter."""
from __future__ import annotations

import json

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, status

from .config import get_settings
from .handlers import handle_slack_event
from .security import SlackVerificationError, verify_slack_signature

app = FastAPI(title="InsightHub ChatOps", version="0.3.0")


@app.get("/healthz")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/slack/events", status_code=status.HTTP_200_OK)
async def slack_events(request: Request, background_tasks: BackgroundTasks) -> dict[str, str]:
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
    # Slack receives its ACK before any potentially slow LLM/MCP work.
    background_tasks.add_task(handle_slack_event, payload)
    return {"ok": "true"}
