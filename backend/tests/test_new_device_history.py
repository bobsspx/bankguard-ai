
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.login_event import LoginEvent

from app.services.new_device_history import (
    load_prior_device_logins,
)
from app.services.new_device_detection import (
    detect_new_device_login,
)


NOW = datetime(2026, 10, 28, tzinfo=timezone.utc)


def test_read_only_history_does_not_flush_pending_login():
    engine = create_engine("sqlite:///:memory:")
    LoginEvent.__table__.create(engine)
    account_id, event_id = uuid4(), uuid4()
    try:
        with engine.begin() as connection:
            connection.execute(LoginEvent.__table__.insert().values(
                id=event_id, account_id=account_id, success=True,
                ip_address="127.0.0.1", country_code="TH", occurred_at=NOW,
            ))
        with Session(engine) as db:
            # Deliberately incomplete pending row: an autoflush would fail.
            pending = LoginEvent(account_id=account_id)
            db.add(pending)
            current, history = load_prior_device_logins(
                db, account_id=account_id, current_event_id=event_id,
            )
            assert current.event_id == event_id
            assert history == []
            assert pending in db.new
            assert pending.id is None
    finally:
        engine.dispose()


def event(account, device, minutes):
    return SimpleNamespace(
        id=uuid4(),
        account_id=account,
        device_id=device,
        success=True,
        occurred_at=NOW + timedelta(minutes=minutes),
    )


def test_loads_current_and_prior_events():
    account = uuid4()
    old = event(account, uuid4(), -10)
    current = event(account, uuid4(), 0)

    db = MagicMock()
    db.scalar.return_value = current
    db.scalars.return_value.all.return_value = [old]

    result, history = load_prior_device_logins(
        db,
        account_id=account,
        current_event_id=current.id,
    )

    assert result.event_id == current.id
    assert len(history) == 1
    assert history[0].event_id == old.id


def test_missing_current_event_rejected():
    db = MagicMock()
    db.scalar.return_value = None

    with pytest.raises(ValueError):
        load_prior_device_logins(
            db,
            account_id=uuid4(),
            current_event_id=uuid4(),
        )


def test_incomplete_history_does_not_raise_alert():
    account = uuid4()
    current = event(account, uuid4(), 0)

    db = MagicMock()
    db.scalar.return_value = current
    db.scalars.return_value.all.return_value = []

    result, history = load_prior_device_logins(
        db,
        account_id=account,
        current_event_id=current.id,
    )

    detection = detect_new_device_login(
        result,
        history,
        history_complete=False,
    )

    assert detection is None


def test_empty_database_history_is_not_proof_of_new_device():
    account = uuid4()
    current = event(account, uuid4(), 0)

    db = MagicMock()
    db.scalar.return_value = current
    db.scalars.return_value.all.return_value = []

    loaded_current, history = load_prior_device_logins(
        db,
        account_id=account,
        current_event_id=current.id,
    )

    assert history == []

    result = detect_new_device_login(
        loaded_current,
        history,
        history_complete=False,
    )

    assert result is None

