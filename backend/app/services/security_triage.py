"""Security alert transitions using the shared lifecycle and audit service."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.investigation_case import InvestigationCase
from app.services.alert_triage import (
    AlertNotFoundError, InvalidAlertTransitionError, apply_alert_transition,
)
from app.services.audit import write_audit_log
from app.services.security_alert_identity import SUPPORTED_SECURITY_RULES


def read_security_alert(db: Session, alert_id: UUID, *, lock: bool = False) -> Alert:
    statement = select(Alert).where(
        Alert.id == alert_id, Alert.login_event_id.is_not(None),
        Alert.alert_type.in_(sorted(SUPPORTED_SECURITY_RULES)),
    )
    if lock:
        statement = statement.with_for_update()
    alert = db.scalar(statement)
    if alert is None:
        raise AlertNotFoundError
    return alert


def transition_security_alert(
    db: Session, *, alert_id: UUID, status: str, expected_status: str,
    reason: str, actor_ref: str,
) -> Alert:
    """Stage locked transition and audit together; caller commits/rolls back."""
    clean_reason = reason.strip()
    if not 3 <= len(clean_reason) <= 1000:
        raise ValueError("A reason of 3 to 1000 characters is required")
    alert = read_security_alert(db, alert_id, lock=True)
    if alert.status == status:
        return alert
    if alert.status != expected_status:
        raise InvalidAlertTransitionError("Alert changed; refresh before retrying")
    if status in {"resolved", "dismissed"}:
        active_case = db.scalar(select(InvestigationCase.id).where(
            InvestigationCase.alert_id == alert.id,
            InvestigationCase.status != "closed",
        ))
        if active_case is not None:
            raise InvalidAlertTransitionError("Close the linked investigation before closing this alert")
    previous, current = apply_alert_transition(alert, status)
    write_audit_log(
        db, actor_ref=actor_ref, action="security_alert.status_changed",
        resource_type="alert", resource_id=str(alert.id),
        details={"previous_status": previous, "new_status": current,
                 "reason": clean_reason, "rule_code": alert.alert_type},
    )
    return alert
