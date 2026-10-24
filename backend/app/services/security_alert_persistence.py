
"""Security alert persistence with PostgreSQL deduplication."""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.services.security_alert_preview import (
    SecurityAlertPreview,
)


RULE = "FAILED_LOGIN_BURST"


@dataclass(frozen=True)
class AlertPersistenceResult:
    alert_id: UUID
    created: bool


def create_security_alert(
    db: Session,
    preview: SecurityAlertPreview,
) -> AlertPersistenceResult:
    """Insert or reuse an alert. Caller controls transaction."""

    if preview.alert_type != RULE:
        raise ValueError("Unsupported alert type")

    if preview.severity != "high":
        raise ValueError("Unexpected severity")



    # Validate triggering event
    if not isinstance(preview.login_event_id, UUID):
        raise TypeError("login_event_id must be UUID")

    trigger_id = preview.login_event_id

    # Validate evidence is present
    if not preview.evidence_ids:
        raise ValueError("Evidence cannot be empty")

    # Normalize and validate evidence UUIDs
    normalized_ids: list[UUID] = []

    for item in preview.evidence_ids:
        if isinstance(item, UUID):
            normalized_ids.append(item)

        elif isinstance(item, str):
            try:
                normalized_ids.append(UUID(item))
            except ValueError as exc:
                raise TypeError(
                    "Evidence IDs must contain valid UUIDs"
                ) from exc

        else:
            raise TypeError(
                "Evidence IDs must be UUID or valid UUID strings"
            )

    evidence_ids = tuple(normalized_ids)

    # Reject duplicates after normalization
    if len(evidence_ids) != len(set(evidence_ids)):
        raise ValueError("Duplicate evidence IDs")

    # Ensure trigger is included in evidence
    if trigger_id not in evidence_ids:
        raise ValueError(
            "Triggering event missing from evidence"
        )


    if not preview.title.strip():
        raise ValueError("Alert title cannot be empty")

    if not preview.description.strip():
        raise ValueError("Alert description cannot be empty")

    statement = (
        insert(Alert)
        .values(
            alert_type=RULE,
            login_event_id=preview.login_event_id,
            transaction_id=None,
            severity=preview.severity,
            status="open",
            title=preview.title,
            description=preview.description,
        )
        .on_conflict_do_nothing(
            index_elements=[
                Alert.alert_type,
                Alert.login_event_id,
            ],
            index_where=(
                (Alert.alert_type == RULE)
                & Alert.login_event_id.is_not(None)
            ),
        )
        .returning(Alert.id)
    )

    inserted_id = db.scalar(statement)

    if inserted_id is not None:
        return AlertPersistenceResult(
            alert_id=inserted_id,
            created=True,
        )

    existing_id = db.scalar(
        select(Alert.id).where(
            Alert.alert_type == RULE,
            Alert.login_event_id == preview.login_event_id,
        )
    )

    if existing_id is None:
        raise RuntimeError(
            "Conflict detected but existing alert was not found"
        )

    return AlertPersistenceResult(
        alert_id=existing_id,
        created=False,
    )
