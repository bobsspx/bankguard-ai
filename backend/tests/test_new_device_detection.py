
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.services.new_device_detection import (
    DeviceLogin,
    detect_new_device_login,
)


NOW = datetime(2026, 10, 28, 10, 0, tzinfo=timezone.utc)


def login(account, device, *, success=True, minutes=0):
    return DeviceLogin(
        event_id=uuid4(),
        account_id=account,
        device_id=device,
        success=success,
        occurred_at=NOW + timedelta(minutes=minutes),
    )


def test_new_device_detected():
    account, old_device, new_device = uuid4(), uuid4(), uuid4()

    current = login(account, new_device)
    history = [login(account, old_device, minutes=-10)]

    result = detect_new_device_login(
        current, history, history_complete=True
    )

    assert result is not None
    assert result.rule_code == "NEW_DEVICE_LOGIN"
    assert result.device_id == new_device


def test_known_device_not_detected():
    account, device = uuid4(), uuid4()

    result = detect_new_device_login(
        login(account, device),
        [login(account, device, minutes=-5)],
        history_complete=True,
    )

    assert result is None


def test_failed_login_not_detected():
    account, device = uuid4(), uuid4()

    result = detect_new_device_login(
        login(account, device, success=False),
        [],
        history_complete=True,
    )

    assert result is None


def test_incomplete_history_is_inconclusive():
    result = detect_new_device_login(
        login(uuid4(), uuid4()),
        [],
        history_complete=False,
    )

    assert result is None


def test_other_account_history_not_reused():
    device = uuid4()

    result = detect_new_device_login(
        login(uuid4(), device),
        [login(uuid4(), device, minutes=-10)],
        history_complete=True,
    )

    assert result is not None


def test_future_event_not_prior_history():
    account, device = uuid4(), uuid4()

    result = detect_new_device_login(
        login(account, device),
        [login(account, device, minutes=10)],
        history_complete=True,
    )

    assert result is not None


def test_naive_timestamp_rejected():
    account, device = uuid4(), uuid4()
    current = DeviceLogin(
        event_id=uuid4(),
        account_id=account,
        device_id=device,
        success=True,
        occurred_at=datetime(2026, 10, 28, 10, 0),
    )

    with pytest.raises(ValueError):
        detect_new_device_login(
            current, [], history_complete=True
        )


def test_previous_failed_attempt_does_not_prove_known_device():
    account, device = uuid4(), uuid4()

    current = login(account, device)
    failed_previous = login(
        account,
        device,
        success=False,
        minutes=-5,
    )

    result = detect_new_device_login(
        current,
        [failed_previous],
        history_complete=True,
    )

    assert result is not None
    assert result.rule_code == "NEW_DEVICE_LOGIN"


def test_missing_device_id_does_not_trigger():
    account = uuid4()

    current = login(account, None)

    result = detect_new_device_login(
        current,
        [],
        history_complete=True,
    )

    assert result is None


def test_same_timestamp_is_not_prior_history():
    account, device = uuid4(), uuid4()

    current = login(account, device)
    simultaneous = login(account, device)

    result = detect_new_device_login(
        current,
        [simultaneous],
        history_complete=True,
    )

    assert result is not None
