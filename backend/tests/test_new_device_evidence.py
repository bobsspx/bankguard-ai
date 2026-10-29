
from uuid import uuid4

import pytest

from app.services.new_device_detection import NewDeviceDetection
from app.services.new_device_evidence import (
    build_new_device_evidence,
)


def make_detection(rule="NEW_DEVICE_LOGIN"):
    return NewDeviceDetection(
        rule_code=rule,
        triggering_event_id=uuid4(),
        account_id=uuid4(),
        device_id=uuid4(),
        severity="medium",
    )


def test_builds_new_device_evidence():
    detection = make_detection()

    evidence = build_new_device_evidence(
        detection,
        history_complete=True,
    )

    assert evidence["rule_code"] == "NEW_DEVICE_LOGIN"
    assert evidence["event_count"] == 1
    assert evidence["device_id"] == str(detection.device_id)
    assert evidence["history_complete"] is True


def test_incomplete_history_rejected():
    with pytest.raises(ValueError):
        build_new_device_evidence(
            make_detection(),
            history_complete=False,
        )


def test_unsupported_rule_rejected():
    with pytest.raises(ValueError):
        build_new_device_evidence(
            make_detection("FAILED_LOGIN_BURST"),
            history_complete=True,
        )


def test_evidence_is_deterministic():
    detection = make_detection()

    first = build_new_device_evidence(
        detection,
        history_complete=True,
    )
    second = build_new_device_evidence(
        detection,
        history_complete=True,
    )

    assert first == second
    assert len(first["evidence_event_ids"]) == 1
