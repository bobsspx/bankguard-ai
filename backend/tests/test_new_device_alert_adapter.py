
from uuid import uuid4

import pytest

from app.services.new_device_detection import NewDeviceDetection
from app.services.new_device_alert_adapter import (
    build_new_device_alert_preview,
)


def make_detection(
    rule_code="NEW_DEVICE_LOGIN",
    severity="medium",
):
    return NewDeviceDetection(
        rule_code=rule_code,
        triggering_event_id=uuid4(),
        account_id=uuid4(),
        device_id=uuid4(),
        severity=severity,
    )


def test_builds_new_device_alert_preview():
    detection = make_detection()
    preview = build_new_device_alert_preview(detection)

    assert preview.alert_type == "NEW_DEVICE_LOGIN"
    assert preview.severity == "medium"
    assert preview.login_event_id == detection.triggering_event_id
    assert preview.event_count == 1


def test_preview_contains_triggering_evidence():
    detection = make_detection()
    preview = build_new_device_alert_preview(detection)

    assert str(detection.triggering_event_id) in preview.evidence_ids


def test_unsupported_rule_rejected():
    with pytest.raises(ValueError):
        build_new_device_alert_preview(
            make_detection(rule_code="UNKNOWN_RULE")
        )


def test_unexpected_severity_rejected():
    with pytest.raises(ValueError):
        build_new_device_alert_preview(
            make_detection(severity="critical")
        )
