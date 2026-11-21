
"""Document new-device evidence limitations."""

from uuid import uuid4

from app.services.security_alert_preview import (
    SecurityAlertPreview,
)
from app.services.security_evidence import (
    build_security_evidence,
)


def make_preview():
    event_id = uuid4()
    return SecurityAlertPreview(
        alert_type="NEW_DEVICE_LOGIN",
        severity="medium",
        login_event_id=event_id,
        evidence_ids=(str(event_id),),
        account_id=str(uuid4()),
        event_count=1,
        title="New device login",
        description="Synthetic test",
    )


def test_snapshot_contains_event_evidence():
    preview = make_preview()
    snapshot = build_security_evidence(preview)

    assert snapshot["rule_code"] == "NEW_DEVICE_LOGIN"
    assert snapshot["event_count"] == 1
    assert snapshot["triggering_event_id"] == str(
        preview.login_event_id
    )


def test_snapshot_does_not_claim_verified_history():
    snapshot = build_security_evidence(make_preview())

    assert "history_verified" not in snapshot
    assert "history_complete" not in snapshot
