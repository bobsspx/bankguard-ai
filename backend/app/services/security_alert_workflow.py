
"""Coordinate alert and evidence persistence in one session."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.security_alert_evidence import (
    SecurityAlertEvidence,
)
from app.services.security_alert_preview import (
    SecurityAlertPreview,
)
from app.services.security_alert_persistence import (
    AlertPersistenceResult,
    create_security_alert,
)
from app.services.security_evidence import (
    build_security_evidence,
)
from app.services.audit import write_audit_log


class EvidenceConflictError(RuntimeError):
    pass


def persist_security_alert_with_evidence(
    db: Session,
    preview: SecurityAlertPreview,
) -> AlertPersistenceResult:
    """Stage alert and evidence using the caller's transaction.

    Does not commit, flush or rollback.
    Requires the alert and evidence unique indexes.
    """

    if db.new or db.dirty or db.deleted:
        raise ValueError(
            "Workflow requires a session without pending writes"
        )

    # Validate evidence before attempting an alert insert.
    snapshot = build_security_evidence(preview)

    result = create_security_alert(db, preview)


    if result.created:
        db.add(
            SecurityAlertEvidence(
                alert_id=result.alert_id,
                snapshot=snapshot,
            )
        )

        write_audit_log(
            db,
            actor_ref="system:security-detection",
            action="security_alert.created",
            resource_type="alert",
            resource_id=str(result.alert_id),
            details={
                "rule_code": preview.alert_type,
                "triggering_event_id": str(
                    preview.login_event_id
                ),
                "evidence_version": snapshot[
                    "evidence_version"
                ],
                "event_count": snapshot["event_count"],
            },
        )

        return result


    # Existing alerts must retain their original evidence.
    existing = db.scalar(
        select(SecurityAlertEvidence.snapshot).where(
            SecurityAlertEvidence.alert_id
            == result.alert_id
        )
    )

    if existing is None:
        raise EvidenceConflictError(
            "Existing alert has no evidence snapshot"
        )

    if existing != snapshot:
        raise EvidenceConflictError(
            "Existing evidence differs from new detection"
        )

    return result
