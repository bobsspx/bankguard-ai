
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from sqlalchemy.dialects import postgresql

from app.services.security_alert_preview import (
    SecurityAlertPreview,
)
from app.services.security_alert_persistence import (
    create_security_alert,
)
from dataclasses import replace


def preview():
    return SecurityAlertPreview(
        alert_type="FAILED_LOGIN_BURST",
        severity="high",
        title="Multiple failed login attempts",
        description="Synthetic security alert",
        login_event_id=UUID(int=5),
        evidence_ids=tuple(
            UUID(int=i) for i in range(1, 6)
        ),
    )


def test_creates_new_alert():
    db = MagicMock()
    db.scalar.return_value = UUID(int=100)

    result = create_security_alert(db, preview())

    assert result.created is True
    assert result.alert_id == UUID(int=100)
    db.scalar.assert_called_once()
    db.commit.assert_not_called()


def test_reuses_existing_alert():
    db = MagicMock()
    db.scalar.side_effect = [None, UUID(int=100)]

    result = create_security_alert(db, preview())

    assert result.created is False
    assert result.alert_id == UUID(int=100)
    assert db.scalar.call_count == 2
    db.commit.assert_not_called()


def test_missing_conflict_target_raises():
    db = MagicMock()
    db.scalar.side_effect = [None, None]

    with pytest.raises(RuntimeError, match="not found"):
        create_security_alert(db, preview())


def test_insert_uses_postgresql_on_conflict():
    db = MagicMock()
    db.scalar.return_value = UUID(int=100)

    create_security_alert(db, preview())

    statement = db.scalar.call_args.args[0]
    sql = str(
        statement.compile(
            dialect=postgresql.dialect()
        )
    )

    assert "ON CONFLICT" in sql
    assert "DO NOTHING" in sql
    assert "RETURNING" in sql
    assert "login_event_id" in sql


def test_rejects_unsupported_alert():
    item = preview()
    invalid = SecurityAlertPreview(
        alert_type="UNKNOWN",
        severity=item.severity,
        title=item.title,
        description=item.description,
        login_event_id=item.login_event_id,
        evidence_ids=item.evidence_ids,
    )

    with pytest.raises(ValueError, match="Unsupported"):
        create_security_alert(MagicMock(), invalid)


def test_rejects_empty_evidence():
    db = MagicMock()
    item = replace(preview(), evidence_ids=())

    with pytest.raises(ValueError):
        create_security_alert(db, item)

    db.scalar.assert_not_called()


def test_rejects_invalid_evidence_type():
    db = MagicMock()
    item = replace(
        preview(),
        evidence_ids=(UUID(int=5), "invalid"),
    )

    with pytest.raises(TypeError, match="Evidence IDs"):
        create_security_alert(db, item)

    db.scalar.assert_not_called()


def test_rejects_empty_title():
    db = MagicMock()
    item = replace(preview(), title="   ")

    with pytest.raises(ValueError, match="title"):
        create_security_alert(db, item)

    db.scalar.assert_not_called()


def test_rejects_empty_description():
    db = MagicMock()
    item = replace(preview(), description="  ")

    with pytest.raises(ValueError, match="description"):
        create_security_alert(db, item)

    db.scalar.assert_not_called()
