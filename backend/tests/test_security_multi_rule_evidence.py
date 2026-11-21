
from uuid import uuid4

import pytest

from app.services.security_alert_preview import SecurityAlertPreview
from app.services.security_evidence import build_security_evidence


def make_preview(rule_code):
    event_id = uuid4()

    return SecurityAlertPreview(
        alert_type=rule_code,
        severity="high" if rule_code == "FAILED_LOGIN_BURST" else "medium",
        login_event_id=event_id,
        evidence_ids=(str(event_id),),
        account_id=str(uuid4()),
        event_count=1,
        title="Test security alert",
        description="Synthetic test evidence",
    )


@pytest.mark.parametrize(
    "rule_code",
    ["FAILED_LOGIN_BURST", "NEW_DEVICE_LOGIN"],
)
def test_evidence_supports_registered_rules(rule_code):
    preview = make_preview(rule_code)

    snapshot = build_security_evidence(preview)

    assert snapshot["rule_code"] == rule_code
    assert snapshot["event_count"] == 1
    assert snapshot["triggering_event_id"] == str(
        preview.login_event_id
    )


def test_evidence_is_deterministic():
    preview = make_preview("NEW_DEVICE_LOGIN")

    first = build_security_evidence(preview)
    second = build_security_evidence(preview)

    assert first == second


def test_unknown_rule_rejected():
    preview = make_preview("UNKNOWN_RULE")

    with pytest.raises(ValueError):
        build_security_evidence(preview)
