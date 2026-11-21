from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from sqlalchemy.dialects import postgresql

from app.services.new_device_history_verification import TRUSTED_HISTORY_SOURCE
from app.services.new_device_workflow import persist_new_device_event, verified_new_device_preview
from app.services.security_alert_persistence import create_security_alert
from app.services.security_alert_workflow import EvidenceConflictError, persist_security_alert_with_evidence
from app.services.security_evidence import build_security_evidence

ACCOUNT, EVENT, DEVICE, ALERT = [UUID(int=i) for i in range(1, 5)]
NOW = datetime.now(timezone.utc) - timedelta(days=1)


def session(*, known=False, success=True, source=TRUSTED_HISTORY_SOURCE):
    db = MagicMock()
    db.new = db.dirty = db.deleted = set()
    db.connection.return_value.dialect.name = "postgresql"
    db.connection.return_value.get_isolation_level.return_value = "REPEATABLE READ"
    current = SimpleNamespace(id=EVENT, account_id=ACCOUNT, device_id=DEVICE,
                              success=success, occurred_at=NOW)
    account = SimpleNamespace(id=ACCOUNT, created_at=NOW - timedelta(days=30))
    coverage = SimpleNamespace(account_id=ACCOUNT, status="verified",
        coverage_started_at=account.created_at, verified_at=NOW, verification_source=source,
        coverage_ended_at=NOW, verification_reference="synthetic-manifest-1")

    def scalar(statement):
        if getattr(statement, "is_insert", False):
            return ALERT
        entity = statement.column_descriptions[0]["entity"].__name__
        return {"Account": account, "LoginEvent": current,
                "DeviceHistoryCoverage": coverage}[entity]

    db.scalar.side_effect = scalar
    db.scalars.return_value.all.return_value = [SimpleNamespace(
        id=UUID(int=20), account_id=ACCOUNT, device_id=DEVICE,
        success=True, occurred_at=NOW-timedelta(days=1),
    )] if known else []
    return db


def test_verified_event_stages_alert_evidence_and_audit_without_commit():
    db = session()
    result = persist_new_device_event(db, account_id=ACCOUNT, current_event_id=EVENT)
    assert result.created and result.alert_id == ALERT
    assert db.add.call_count == 2
    snapshot = db.add.call_args_list[0].args[0].snapshot
    assert snapshot["rule_code"] == "NEW_DEVICE_LOGIN"
    assert snapshot["evidence_event_ids"] == [str(EVENT)]
    insert = next(c.args[0] for c in db.scalar.call_args_list if getattr(c.args[0], "is_insert", False))
    sql = str(insert.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
    assert "ON CONFLICT" in sql and "NEW_DEVICE_LOGIN" in sql
    for method in ("commit", "flush", "rollback"):
        getattr(db, method).assert_not_called()


@pytest.mark.parametrize("changes", [{"known": True}, {"success": False}, {"source": "unknown"}])
def test_ineligible_events_never_insert(changes):
    db = session(**changes)
    with pytest.raises(ValueError):
        persist_new_device_event(db, account_id=ACCOUNT, current_event_id=EVENT)
    assert not any(getattr(c.args[0], "is_insert", False) for c in db.scalar.call_args_list)
    db.add.assert_not_called()


def test_read_committed_transaction_is_rejected_before_verification():
    db = session()
    db.connection.return_value.get_isolation_level.return_value = "READ COMMITTED"
    with pytest.raises(ValueError, match="repeatable snapshot"):
        verified_new_device_preview(db, account_id=ACCOUNT, current_event_id=EVENT)
    db.scalar.assert_not_called()


def test_forged_preview_is_rejected_before_insert():
    from dataclasses import replace
    db = session()
    preview = verified_new_device_preview(db, account_id=ACCOUNT, current_event_id=EVENT)
    with pytest.raises(ValueError, match="differs"):
        create_security_alert(db, replace(preview, description="forged"))
    assert not any(getattr(c.args[0], "is_insert", False) for c in db.scalar.call_args_list)


@pytest.mark.parametrize("conflicting", [False, True])
def test_retry_preserves_original_evidence(conflicting):
    db = session()
    preview = verified_new_device_preview(db, account_id=ACCOUNT, current_event_id=EVENT)
    original_scalar = db.scalar.side_effect
    def scalar(statement):
        if getattr(statement, "is_insert", False):
            return None
        entity = statement.column_descriptions[0]["entity"].__name__
        if entity == "Alert":
            return ALERT
        if entity == "SecurityAlertEvidence":
            return {} if conflicting else build_security_evidence(preview)
        return original_scalar(statement)
    db.scalar.side_effect = scalar
    if conflicting:
        with pytest.raises(EvidenceConflictError):
            persist_security_alert_with_evidence(db, preview)
    else:
        result = persist_security_alert_with_evidence(db, preview)
        assert result.alert_id == ALERT and not result.created
    db.add.assert_not_called()
    db.commit.assert_not_called()
