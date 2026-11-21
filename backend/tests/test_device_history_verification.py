from unittest.mock import MagicMock
from uuid import UUID

from sqlalchemy.orm import Session

from app.services.new_device_history_verification import (
    verify_device_history_coverage,
)
from datetime import datetime, timedelta, timezone

import pytest

from app.models.device_history_coverage import (
    DeviceHistoryCoverage,
)
from types import SimpleNamespace


def test_missing_coverage_does_not_verify_history():
    # Arrange: database ไม่พบ coverage ของบัญชีนี้
    db = MagicMock(spec=Session)
    db.scalar.return_value = None

    account_id = UUID(
        "00000000-0000-0000-0000-000000000001"
    )

    # Act: ขอให้ verification service ตรวจ coverage
    result = verify_device_history_coverage(
        db,
        account_id=account_id,
    )

    # Assert: ไม่พบ coverage ต้องไม่ถือว่า verified
    assert result.status == "missing"
    assert result.history_verified is False

    # การตรวจ coverage ต้องไม่เขียนข้อมูลหรือ commit
    db.add.assert_not_called()
    db.flush.assert_not_called()
    db.commit.assert_not_called()


def test_mismatched_event_id_is_rejected_without_reading_coverage():
    from app.services.new_device_history_verification import (
        verify_device_history_for_event,
    )

    account_id = UUID(int=1)
    event_id = UUID(int=10)
    db = MagicMock(spec=Session)
    db.scalar.return_value = SimpleNamespace(
        id=UUID(int=11),
        account_id=account_id,
        occurred_at=datetime.now(timezone.utc) - timedelta(days=1),
    )

    result = verify_device_history_for_event(
        db, account_id=account_id, current_event_id=event_id,
    )

    assert result.status == "invalid"
    assert result.history_verified is False
    db.scalar.assert_called_once()
    statement = db.scalar.call_args.args[0].compile()
    assert statement.params == {"id_1": event_id, "account_id_1": account_id}
    assert "login_events.id =" in str(statement)
    assert "login_events.account_id =" in str(statement)
    db.no_autoflush.__enter__.assert_called_once()
    db.add.assert_not_called()
    db.flush.assert_not_called()
    db.commit.assert_not_called()

def build_coverage(**changes):
    now = datetime.now(timezone.utc)

    values = {
        "account_id": UUID(
            "00000000-0000-0000-0000-000000000001"
        ),
        "status": "verified",
        "coverage_started_at": now - timedelta(days=30),
        "verified_at": now - timedelta(days=1),
        "verification_source": "synthetic-test-source",
    }
    values.update(changes)

    return DeviceHistoryCoverage(**values)


def check_coverage(record):
    db = MagicMock(spec=Session)
    db.scalar.return_value = record

    result = verify_device_history_coverage(
        db,
        account_id=UUID(
            "00000000-0000-0000-0000-000000000001"
        ),
    )

    db.add.assert_not_called()
    db.flush.assert_not_called()
    db.commit.assert_not_called()

    return result


def test_unverified_record_does_not_verify_history():
    record = build_coverage(status="unverified")

    result = check_coverage(record)

    assert result.status == "unverified"
    assert result.history_verified is False


@pytest.mark.parametrize("source", [None, "", "   "])
def test_verified_record_requires_nonempty_source(source):
    record = build_coverage(
        verification_source=source,
    )

    result = check_coverage(record)

    assert result.status == "invalid"
    assert result.history_verified is False


def test_verification_cannot_precede_coverage_start():
    record = build_coverage()
    record.verified_at = (
        record.coverage_started_at - timedelta(seconds=1)
    )

    result = check_coverage(record)

    assert result.status == "invalid"
    assert result.history_verified is False


def test_naive_verification_timestamp_is_invalid():
    record = build_coverage()
    record.verified_at = record.verified_at.replace(
        tzinfo=None,
    )

    result = check_coverage(record)

    assert result.status == "invalid"
    assert result.history_verified is False


def test_well_formed_record_still_requires_full_verification():
    result = check_coverage(build_coverage())

    assert result.status == "pending_verification"
    assert result.history_verified is False

def test_missing_triggering_event_is_invalid():
    from app.services.new_device_history_verification import (
        verify_device_history_for_event,
    )

    db = MagicMock(spec=Session)
    db.scalar.return_value = None

    result = verify_device_history_for_event(
        db,
        account_id=UUID(
            "00000000-0000-0000-0000-000000000001"
        ),
        current_event_id=UUID(
            "00000000-0000-0000-0000-000000000010"
        ),
    )

    assert result.status == "invalid"
    assert result.history_verified is False
    db.add.assert_not_called()
    db.flush.assert_not_called()
    db.commit.assert_not_called()


def test_triggering_event_from_another_account_is_invalid():
    from app.services.new_device_history_verification import (
        verify_device_history_for_event,
    )

    account_id = UUID(
        "00000000-0000-0000-0000-000000000001"
    )
    event_id = UUID(
        "00000000-0000-0000-0000-000000000010"
    )

    db = MagicMock(spec=Session)
    db.scalar.return_value = SimpleNamespace(
        id=event_id,
        account_id=UUID(
            "00000000-0000-0000-0000-000000000002"
        ),
        occurred_at=(
            datetime.now(timezone.utc) - timedelta(days=1)
        ),
    )

    result = verify_device_history_for_event(
        db,
        account_id=account_id,
        current_event_id=event_id,
    )

    assert result.status == "invalid"
    assert result.history_verified is False
    db.add.assert_not_called()
    db.flush.assert_not_called()
    db.commit.assert_not_called()

@pytest.mark.parametrize(
    "case, expected_status",
    [
        ("missing_timestamp", "invalid"),
        ("naive_timestamp", "invalid"),
        ("future_timestamp", "invalid"),
        ("before_coverage_start", "invalid"),
        ("at_coverage_start", "pending_verification"),
        ("inside_coverage", "pending_verification"),
    ],
)
def test_triggering_event_time_boundaries(
    case,
    expected_status,
):
    from app.services.new_device_history_verification import (
        verify_device_history_for_event,
    )

    account_id = UUID(
        "00000000-0000-0000-0000-000000000001"
    )
    event_id = UUID(
        "00000000-0000-0000-0000-000000000010"
    )

    coverage = build_coverage()
    now = datetime.now(timezone.utc)

    event_times = {
        "missing_timestamp": None,
        "naive_timestamp": now.replace(tzinfo=None),
        "future_timestamp": now + timedelta(days=1),
        "before_coverage_start": (
            coverage.coverage_started_at
            - timedelta(seconds=1)
        ),
        "at_coverage_start": coverage.coverage_started_at,
        "inside_coverage": (
            coverage.coverage_started_at
            + timedelta(days=1)
        ),
    }

    current = SimpleNamespace(
        id=event_id,
        account_id=account_id,
        occurred_at=event_times[case],
    )

    db = MagicMock(spec=Session)

    # Query แรกอ่าน event; query ถัดไปอ่าน coverage
    db.scalar.side_effect = [
        current,
        coverage,
    ]

    result = verify_device_history_for_event(
        db,
        account_id=account_id,
        current_event_id=event_id,
    )

    assert result.status == expected_status
    assert result.history_verified is False

    db.add.assert_not_called()
    db.flush.assert_not_called()
    db.commit.assert_not_called()
