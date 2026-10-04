import uuid
from datetime import (
    datetime,
    timezone,
)

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.alert import Alert


class AlertNotFoundError(
    Exception
):
    pass


class InvalidAlertTransitionError(
    Exception
):
    pass


ALLOWED_TRANSITIONS = {
    "open": {
        "investigating",
        "resolved",
        "dismissed",
    },

    "investigating": {
        "resolved",
        "dismissed",
    },

    "resolved": set(),

    "dismissed": set(),
}


TERMINAL_STATUSES = {
    "resolved",
    "dismissed",
}


def apply_alert_transition(
    alert: Alert,
    new_status: str,
) -> tuple[str, str]:
    previous_status = (
        alert.status
    )

    # Idempotent request.
    if (
        previous_status
        == new_status
    ):
        return (
            previous_status,
            new_status,
        )

    allowed = (
        ALLOWED_TRANSITIONS.get(
            previous_status
        )
    )

    if allowed is None:
        raise (
            InvalidAlertTransitionError(
                (
                    "Unknown current "
                    "alert status: "
                    f"{previous_status}"
                )
            )
        )

    if new_status not in allowed:
        raise (
            InvalidAlertTransitionError(
                (
                    "Invalid alert "
                    "transition: "
                    f"{previous_status}"
                    " -> "
                    f"{new_status}"
                )
            )
        )

    alert.status = new_status

    if (
        new_status
        in TERMINAL_STATUSES
    ):
        alert.resolved_at = (
            datetime.now(
                timezone.utc
            )
        )

    else:
        alert.resolved_at = None

    return (
        previous_status,
        new_status,
    )


def triage_alert(
    db: Session,
    alert_id: uuid.UUID,
    new_status: str,
) -> tuple[Alert, str]:
    alert = db.scalar(
        select(Alert)
        .where(
            Alert.id
            == alert_id
        )
        .with_for_update()
    )

    if alert is None:
        raise AlertNotFoundError

    previous_status, _ = (
        apply_alert_transition(
            alert,
            new_status,
        )
    )

    db.add(alert)

    return (
        alert,
        previous_status,
    )