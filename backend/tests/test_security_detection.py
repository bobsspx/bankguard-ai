import pytest

from datetime import datetime, timedelta, timezone

from app.services.security_detection import (
    LoginAttempt,
    detect_failed_login_burst,
)


BASE_TIME = datetime(
    2026, 10, 18, 12, 0,
    tzinfo=timezone.utc,
)


def attempt(number, *, account="ACC-001", success=False):
    return LoginAttempt(
        event_id=f"EVT-{number}",
        account_id=account,
        success=success,
        occurred_at=BASE_TIME + timedelta(minutes=number),
    )


def test_detect_five_failed_logins():
    events = [attempt(i) for i in range(5)]

    result = detect_failed_login_burst(
        events[-1], events[:-1]
    )

    assert result is not None
    assert result.rule_code == "FAILED_LOGIN_BURST"
    assert result.severity == "high"
    assert result.event_count == 5
    assert len(result.evidence_ids) == 5


def test_four_failures_do_not_trigger():
    events = [attempt(i) for i in range(4)]

    result = detect_failed_login_burst(
        events[-1], events[:-1]
    )

    assert result is None


def test_different_accounts_not_counted():
    current = attempt(4)
    history = [
        attempt(i, account="ACC-002")
        for i in range(4)
    ]

    result = detect_failed_login_burst(
        current, history
    )

    assert result is None


def test_successful_login_not_counted():
    history = [attempt(i) for i in range(4)]
    current = attempt(4, success=True)

    result = detect_failed_login_burst(
        current, history
    )

    assert result is None


def test_old_future_and_duplicate_events_not_counted():
    current = attempt(20)
    history = [
        attempt(0),
        attempt(21),
        attempt(18),
        attempt(18),
        attempt(19),
    ]

    result = detect_failed_login_burst(
        current, history
    )

    assert result is None


def test_exact_ten_minute_boundary():
    current = attempt(10)
    history = [
        attempt(0),
        attempt(1),
        attempt(2),
        attempt(3),
    ]

    result = detect_failed_login_burst(
        current, history
    )

    assert result is not None
    assert result.event_count == 5


def test_event_outside_ten_minute_window():
    current = attempt(11)
    history = [
        attempt(0),
        attempt(1),
        attempt(2),
        attempt(3),
    ]

    result = detect_failed_login_burst(
        current, history
    )

    assert result is None


def test_conflicting_duplicate_event_rejected():
    current = attempt(5)

    conflicting = LoginAttempt(
        event_id="EVT-1",
        account_id="ACC-001",
        success=False,
        occurred_at=BASE_TIME + timedelta(minutes=2),
    )

    with pytest.raises(ValueError, match="Conflicting"):
        detect_failed_login_burst(
            current,
            [attempt(1), conflicting],
        )


def test_naive_timestamp_rejected():
    current = LoginAttempt(
        event_id="EVT-1",
        account_id="ACC-001",
        success=False,
        occurred_at=datetime(2026, 10, 18, 12, 0),
    )

    with pytest.raises(
        ValueError,
        match="Timezone-aware",
    ):
        detect_failed_login_burst(
            current, []
        )
