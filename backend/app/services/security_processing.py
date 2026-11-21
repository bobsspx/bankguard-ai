"""Shared boundary for processing persisted CUSTOMER login events.

The application currently has no customer-event ingestion feed. An authorized
ingestor/replay worker may call this service inside its own transaction. Staff
authentication must not call this service or fabricate customer LoginEvents.
"""
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.login_event import LoginEvent
from app.services.new_device_history_verification import verify_complete_device_history_for_event
from app.services.new_device_workflow import persist_new_device_event
from app.services.security_alert_persistence import AlertPersistenceResult
from app.services.security_alert_preview import build_security_alert_preview
from app.services.security_alert_workflow import persist_security_alert_with_evidence
from app.services.security_event_store import LoginEventNotFoundError, load_failed_login_detection
from app.services.new_device_history import load_prior_device_logins
from app.services.new_device_detection import detect_new_device_login


@dataclass(frozen=True)
class SecurityProcessingResult:
    rule_code: str
    status: str
    persistence: AlertPersistenceResult | None = None


def process_customer_login_event(db: Session, event_id: UUID) -> SecurityProcessingResult:
    """Stage one applicable rule, evidence and audit; never commit or rollback.

    Caller retries the entire transaction on serialization failure. An
    inconclusive result is not evidence that the customer used a new device.
    """
    if not isinstance(event_id, UUID):
        raise TypeError("event_id must be UUID")
    if db.new or db.dirty or db.deleted:
        raise ValueError("Security processing requires no pending writes")
    connection = db.connection()
    if connection.dialect.name != "postgresql" or connection.get_isolation_level() not in {
        "REPEATABLE READ", "SERIALIZABLE",
    }:
        raise ValueError("Security processing requires a PostgreSQL repeatable snapshot")
    with db.no_autoflush:
        current = db.scalar(select(LoginEvent).where(LoginEvent.id == event_id))
    if current is None:
        raise LoginEventNotFoundError(str(event_id))
    if not current.success:
        rule = "FAILED_LOGIN_BURST"
        detection = load_failed_login_detection(db, event_id)
        if detection is None:
            return SecurityProcessingResult(rule, "no_detection")
        result = persist_security_alert_with_evidence(
            db, build_security_alert_preview(detection, event_id),
        )
    else:
        rule = "NEW_DEVICE_LOGIN"
        verification = verify_complete_device_history_for_event(
            db, account_id=current.account_id, current_event_id=event_id,
        )
        if not verification.history_verified:
            return SecurityProcessingResult(rule, "inconclusive")
        event, history = load_prior_device_logins(db, account_id=current.account_id, current_event_id=event_id)
        if detect_new_device_login(event, history, history_complete=True) is None:
            return SecurityProcessingResult(rule, "no_detection")
        result = persist_new_device_event(db, account_id=current.account_id, current_event_id=event_id)
    return SecurityProcessingResult(rule, "created" if result.created else "existing", result)
