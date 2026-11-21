
from uuid import uuid4

import pytest

from app.services.new_device_detection import NewDeviceDetection
from app.services.new_device_persistence_guard import (
    validate_new_device_persistence,
)


def detection(rule="NEW_DEVICE_LOGIN", severity="medium"):
    return NewDeviceDetection(
        rule_code=rule,
        triggering_event_id=uuid4(),
        account_id=uuid4(),
        device_id=uuid4(),
        severity=severity,
    )


def test_unverified_history_rejected():
    with pytest.raises(ValueError):
        validate_new_device_persistence(
            detection(),
            history_verified=False,
        )


def test_invalid_rule_rejected():
    with pytest.raises(ValueError):
        validate_new_device_persistence(
            detection(rule="UNKNOWN"),
            history_verified=True,
        )


def test_invalid_severity_rejected():
    with pytest.raises(ValueError):
        validate_new_device_persistence(
            detection(severity="critical"),
            history_verified=True,
        )


def test_verified_detection_passes_basic_gate():
    validate_new_device_persistence(
        detection(),
        history_verified=True,
    )
