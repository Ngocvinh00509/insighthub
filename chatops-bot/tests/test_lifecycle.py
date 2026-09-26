import json
import logging
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.audit import log_tool_call
from app.security import ConfirmationTokenError, ConfirmationTokenStore


def test_confirmation_token_is_accepted_once() -> None:
    store = ConfirmationTokenStore(ttl_seconds=300)
    token = store.issue("scale_insighthub", now=1000)

    assert store.confirm(token, now=1300) == "scale_insighthub"
    with pytest.raises(ConfirmationTokenError, match="invalid_confirmation_token"):
        store.confirm(token, now=1300)


def test_confirmation_token_rejects_invalid_and_expired_values() -> None:
    store = ConfirmationTokenStore(ttl_seconds=300)
    token = store.issue("scale_insighthub", now=1000)

    with pytest.raises(ConfirmationTokenError, match="invalid_confirmation_token"):
        store.confirm("not-issued", now=1000)
    with pytest.raises(ConfirmationTokenError, match="expired_confirmation_token"):
        store.confirm(token, now=1301)


def test_audit_log_contains_a_valid_json_record(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="chatops-bot.audit"):
        log_tool_call("U123", "list_pods", {"namespace": "insighthub-dev"}, "2 pods", approved=True)

    record = json.loads(caplog.records[-1].message.removeprefix("AUDIT "))
    assert record["user"] == "U123"
    assert record["tool"] == "list_pods"
    assert record["args"] == {"namespace": "insighthub-dev"}
    assert record["approved"] is True
    assert record["ts"].endswith("+00:00")
