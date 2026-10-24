
from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from app.services.security_event_store import (
    LoginEventNotFoundError,
    load_failed_login_detection,
)

from sqlalchemy.dialects import postgresql
from app.models.login_event import LoginEvent


NOW = datetime(2026, 10, 18, 12, tzinfo=timezone.utc)


def event(number, *, success=False):
    return SimpleNamespace(
        id=UUID(int=number + 1),
        account_id=UUID(int=100),
        success=success,
        occurred_at=NOW + timedelta(minutes=number),
    )


def session(current, history=()):
    db = MagicMock()
    db.new = set()
    db.dirty = set()
    db.deleted = set()
    db.no_autoflush = nullcontext()
    db.scalar.return_value = current
    db.execute.return_value.mappings.return_value.all.return_value = [
        {
            "id": item.id,
            "account_id": item.account_id,
            "success": item.success,
            "occurred_at": item.occurred_at,
        }
        for item in history
    ]
    return db


def test_database_adapter_detects_burst():
    current = event(4)
    db = session(current, [event(i) for i in range(4)])

    result = load_failed_login_detection(db, current.id)

    assert result is not None
    assert result.rule_code == "FAILED_LOGIN_BURST"
    assert result.event_count == 5
    assert str(current.id) in result.evidence_ids

    db.scalar.assert_called_once()
    db.execute.assert_called_once()

    for method in ("add", "commit", "flush", "delete"):
        getattr(db, method).assert_not_called()


def test_missing_login_event():
    db = session(None)

    with pytest.raises(LoginEventNotFoundError):
        load_failed_login_detection(db, UUID(int=999))

    db.execute.assert_not_called()
    db.scalar.assert_called_once()


def test_successful_login_skips_history():
    current = event(4, success=True)
    db = session(current)

    result = load_failed_login_detection(db, current.id)

    assert result is None
    db.scalars.assert_not_called()


def test_pending_writes_rejected():
    current = event(4)
    db = session(current)
    db.new = {object()}

    with pytest.raises(ValueError, match="pending writes"):
        load_failed_login_detection(db, current.id)

    db.scalar.assert_not_called()


def test_history_query_has_required_filters():
    current = event(4)
    db = session(current, [event(i) for i in range(4)])

    load_failed_login_detection(db, current.id)

    db.execute.assert_called_once()
    statement = db.execute.call_args.args[0]

    sql = str(
        statement.compile(
            dialect=postgresql.dialect()
        )
    ).lower()

    assert "login_events.account_id =" in sql
    assert "login_events.id !=" in sql
    assert "login_events.success is false" in sql
    assert "login_events.occurred_at >=" in sql
    assert "login_events.occurred_at <=" in sql
    assert "order by" in sql
    assert "limit" not in sql


def test_history_query_uses_ten_minute_window():
    current = event(20)
    db = session(current)

    load_failed_login_detection(db, current.id)

    db.execute.assert_called_once()
    statement = db.execute.call_args.args[0]
    compiled = statement.compile(
        dialect=postgresql.dialect()
    )

    values = list(compiled.params.values())

    assert NOW + timedelta(minutes=10) in values
    assert NOW + timedelta(minutes=20) in values



def test_history_query_does_not_select_mutable_risk_fields():
    current = event(4)
    db = session(current)

    load_failed_login_detection(db, current.id)

    statement = db.execute.call_args.args[0]

    selected = {
        column.key
        for column in statement.selected_columns
    }

    assert selected == {
        "id",
        "account_id",
        "success",
        "occurred_at",
    }

    assert (
        statement.get_final_froms()[0]
        is LoginEvent.__table__
    )