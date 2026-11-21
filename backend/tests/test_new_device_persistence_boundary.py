
"""Ensure new-device alerts cannot bypass persistence safety."""

from uuid import uuid4
from unittest.mock import MagicMock

import pytest

from app.services.security_alert_preview import SecurityAlertPreview
from app.services.security_alert_persistence import (
    create_security_alert,
)
from app.services.security_alert_workflow import (
    persist_security_alert_with_evidence,
)


def new_device_preview():
    event_id = uuid4()

    return SecurityAlertPreview(
        alert_type="NEW_DEVICE_LOGIN",
        severity="medium",
        login_event_id=event_id,
        evidence_ids=(str(event_id),),
        account_id=str(uuid4()),
        event_count=1,
        title="New device login detected",
        description="Synthetic security test",
    )


def test_direct_persistence_rejects_new_device_with_pending_writes():
    db = MagicMock()

    with pytest.raises(ValueError, match="pending writes"):
        create_security_alert(db, new_device_preview())

    db.scalar.assert_not_called()
    db.execute.assert_not_called()


def test_workflow_cannot_bypass_persistence_validation():
    db = MagicMock()
    db.new = set()
    db.dirty = set()
    db.deleted = set()

    with pytest.raises(ValueError, match="repeatable snapshot"):
        persist_security_alert_with_evidence(
            db,
            new_device_preview(),
        )

    db.add.assert_not_called()
    db.commit.assert_not_called()
