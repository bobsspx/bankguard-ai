"""Reconstruct new-device previews using trusted persisted history."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.services.new_device_alert_adapter import build_new_device_alert_preview
from app.services.new_device_detection import detect_new_device_login
from app.services.new_device_history import load_prior_device_logins
from app.services.new_device_history_verification import (
    verify_complete_device_history_for_event,
)
from app.services.security_alert_preview import SecurityAlertPreview


def verified_new_device_preview(
    db: Session, *, account_id: UUID, current_event_id: UUID,
) -> SecurityAlertPreview:
    if db.new or db.dirty or db.deleted:
        raise ValueError("New-device verification requires no pending writes")

    # All verification/history reads and the eventual insert must share a
    # stable PostgreSQL snapshot. Never change caller transaction settings.
    connection = db.connection()
    if connection.dialect.name != "postgresql" or connection.get_isolation_level() not in {
        "REPEATABLE READ", "SERIALIZABLE",
    }:
        raise ValueError("New-device persistence requires a PostgreSQL repeatable snapshot")

    verification = verify_complete_device_history_for_event(
        db, account_id=account_id, current_event_id=current_event_id,
    )
    if not verification.history_verified:
        raise ValueError("Verified complete device history is required")
    current, history = load_prior_device_logins(
        db, account_id=account_id, current_event_id=current_event_id,
    )
    detection = detect_new_device_login(current, history, history_complete=True)
    if detection is None:
        raise ValueError("Event is not a new-device login")
    return build_new_device_alert_preview(detection)


def persist_new_device_event(db: Session, *, account_id: UUID, current_event_id: UUID):
    """Stage alert/evidence/audit; caller owns commit and rollback.

    Retry serialization failures by retrying the entire caller transaction.
    """
    from app.services.security_alert_workflow import persist_security_alert_with_evidence

    preview = verified_new_device_preview(
        db, account_id=account_id, current_event_id=current_event_id,
    )
    return persist_security_alert_with_evidence(db, preview)
