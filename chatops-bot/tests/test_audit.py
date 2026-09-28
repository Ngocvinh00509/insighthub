import json
import logging
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.audit import log_operation


def test_operation_audit_has_investigation_fields_and_redacts_sensitive_values(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="chatops-bot.audit"):
        log_operation(
            request_id="Ev123",
            slack_user_id="U123",
            intent="health",
            requested_action="intent.health",
            permission_tier="read",
            authorization_result="allowed",
            approval_id="approval-token=xoxb-secret",
            execution_result="completed",
            duration_ms=12.5,
            error_category="authorization=Bearer super-secret https://hooks.slack.com/services/secret",
        )

    record = json.loads(caplog.records[-1].message.removeprefix("AUDIT "))
    assert set(record) == {
        "timestamp", "request_id", "slack_user_id", "intent", "requested_action",
        "permission_tier", "authorization_result", "approval_id", "execution_result",
        "duration_ms", "error_category",
    }
    rendered = json.dumps(record)
    assert "xoxb-secret" not in rendered
    assert "super-secret" not in rendered
    assert "hooks.slack.com" not in rendered
    assert "[REDACTED]" in rendered
