from datetime import timedelta
from uuid import UUID

import pytest

from app.services.security_processing import process_customer_login_event
from app.services.security_event_store import LoginEventNotFoundError
from test_new_device_workflow import session, ACCOUNT, EVENT, NOW


@pytest.mark.parametrize("known,source,status", [
    (False, "bankguard-history-import-v2", "created"),
    (True, "bankguard-history-import-v2", "no_detection"),
    (False, "untrusted", "inconclusive"),
])
def test_shared_boundary_dispatches_successful_customer_events(known, source, status):
    db = session(known=known, source=source)
    result = process_customer_login_event(db, EVENT)
    assert result.rule_code == "NEW_DEVICE_LOGIN"
    assert result.status == status
    if status != "created":
        db.add.assert_not_called()
    db.commit.assert_not_called()
    db.rollback.assert_not_called()


@pytest.mark.parametrize("count,status", [(3, "no_detection"), (4, "created")])
def test_shared_boundary_dispatches_failed_customer_events(count, status):
    db = session(success=False)
    db.execute.return_value.mappings.return_value.all.return_value = [
        dict(id=UUID(int=20+i), account_id=ACCOUNT, success=False, occurred_at=NOW-timedelta(minutes=i+1))
        for i in range(count)
    ]
    result = process_customer_login_event(db, EVENT)
    assert result.rule_code == "FAILED_LOGIN_BURST"
    assert result.status == status
    db.commit.assert_not_called()
    db.rollback.assert_not_called()


def test_missing_customer_event_never_writes():
    db = session()
    db.scalar.side_effect = None
    db.scalar.return_value = None
    with pytest.raises(LoginEventNotFoundError):
        process_customer_login_event(db, EVENT)
    db.add.assert_not_called()


def test_pending_changes_rejected_before_queries():
    db = session()
    db.dirty = {object()}
    with pytest.raises(ValueError, match="pending writes"):
        process_customer_login_event(db, EVENT)
    db.scalar.assert_not_called()
