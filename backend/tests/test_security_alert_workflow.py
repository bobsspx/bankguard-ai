
from unittest.mock import MagicMock
from uuid import UUID

import pytest

import app.services.security_alert_workflow as workflow

from app.services.security_alert_preview import (
    SecurityAlertPreview,
)
from app.services.security_alert_persistence import (
    AlertPersistenceResult,
)
from app.services.security_evidence import (
    build_security_evidence,
)


def preview():
    return SecurityAlertPreview(
        alert_type="FAILED_LOGIN_BURST",
        severity="high",
        title="Multiple failed login attempts",
        description="Synthetic security event",
        login_event_id=UUID(int=5),
        evidence_ids=tuple(
            UUID(int=i) for i in range(1, 6)
        ),
    )


def session():
    db = MagicMock()
    db.new = set()
    db.dirty = set()
    db.deleted = set()
    return db


def test_new_alert_stages_evidence(monkeypatch):
    db = session()
    monkeypatch.setattr(
        workflow,
        "create_security_alert",
        lambda db, item: AlertPersistenceResult(
            UUID(int=100), True
        ),
    )

    result = workflow.persist_security_alert_with_evidence(
        db, preview()
    )

    assert result.created is True

    from app.models.security_alert_evidence import (
        SecurityAlertEvidence,
    )

    evidence = next(
        call.args[0]
        for call in db.add.call_args_list
        if isinstance(
            call.args[0],
            SecurityAlertEvidence,
        )
    )

    assert evidence.alert_id == UUID(int=100)
    assert evidence.snapshot == build_security_evidence(
        preview()
    )

    db.commit.assert_not_called()
    db.flush.assert_not_called()


def test_existing_alert_preserves_evidence(monkeypatch):
    db = session()
    db.scalar.return_value = build_security_evidence(
        preview()
    )

    monkeypatch.setattr(
        workflow,
        "create_security_alert",
        lambda db, item: AlertPersistenceResult(
            UUID(int=100), False
        ),
    )

    result = workflow.persist_security_alert_with_evidence(
        db, preview()
    )

    assert result.created is False
    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_missing_existing_evidence_is_rejected(monkeypatch):
    db = session()
    db.scalar.return_value = None

    monkeypatch.setattr(
        workflow,
        "create_security_alert",
        lambda db, item: AlertPersistenceResult(
            UUID(int=100), False
        ),
    )

    with pytest.raises(
        workflow.EvidenceConflictError,
        match="no evidence",
    ):
        workflow.persist_security_alert_with_evidence(
            db, preview()
        )

    db.commit.assert_not_called()


def test_conflicting_evidence_is_rejected(monkeypatch):
    db = session()
    db.scalar.return_value = {
        "evidence_version": "different"
    }

    monkeypatch.setattr(
        workflow,
        "create_security_alert",
        lambda db, item: AlertPersistenceResult(
            UUID(int=100), False
        ),
    )

    with pytest.raises(
        workflow.EvidenceConflictError,
        match="differs",
    ):
        workflow.persist_security_alert_with_evidence(
            db, preview()
        )

    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_pending_writes_are_rejected():
    db = session()
    db.new = {object()}

    with pytest.raises(ValueError, match="pending writes"):
        workflow.persist_security_alert_with_evidence(
            db, preview()
        )

    db.add.assert_not_called()
    db.scalar.assert_not_called()


def test_new_alert_stages_audit_log(monkeypatch):
    db = session()

    monkeypatch.setattr(
        workflow,
        "create_security_alert",
        lambda db, item: AlertPersistenceResult(
            UUID(int=100), True
        ),
    )

    workflow.persist_security_alert_with_evidence(
        db, preview()
    )

    assert db.add.call_count == 2

    staged = [
        call.args[0]
        for call in db.add.call_args_list
    ]

    from app.models.security_alert_evidence import (
        SecurityAlertEvidence,
    )
    from app.models.audit_log import AuditLog

    assert sum(
        isinstance(item, SecurityAlertEvidence)
        for item in staged
    ) == 1

    audits = [
        item for item in staged
        if isinstance(item, AuditLog)
    ]

    assert len(audits) == 1
    assert audits[0].action == "security_alert.created"
    assert audits[0].resource_id == str(UUID(int=100))
    assert audits[0].details["event_count"] == 5

    db.commit.assert_not_called()


def test_existing_alert_does_not_stage_creation_audit(monkeypatch):
    db = session()
    db.scalar.return_value = build_security_evidence(
        preview()
    )

    monkeypatch.setattr(
        workflow,
        "create_security_alert",
        lambda db, item: AlertPersistenceResult(
            UUID(int=100), False
        ),
    )

    result = workflow.persist_security_alert_with_evidence(
        db, preview()
    )

    assert result.created is False
    db.add.assert_not_called()
    db.commit.assert_not_called()
