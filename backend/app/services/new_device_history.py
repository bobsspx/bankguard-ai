
"""Read-only database adapter for device login history."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.login_event import LoginEvent
from app.services.new_device_detection import DeviceLogin


def load_prior_device_logins(
    db: Session,
    *,
    account_id: UUID,
    current_event_id: UUID,
) -> tuple[DeviceLogin, list[DeviceLogin]]:
    """Load current event and all preceding recorded events.

    This adapter does not claim the database contains
    the account's complete lifetime history.
    """
    current = db.scalar(
        select(LoginEvent).where(
            LoginEvent.id == current_event_id,
            LoginEvent.account_id == account_id,
        )
    )

    if current is None:
        raise ValueError("Login event not found")

    rows = db.scalars(
        select(LoginEvent)
        .where(
            LoginEvent.account_id == account_id,
            LoginEvent.id != current_event_id,
            LoginEvent.occurred_at < current.occurred_at,
        )
        .order_by(
            LoginEvent.occurred_at.asc(),
            LoginEvent.id.asc(),
        )
    ).all()

    def convert(row: LoginEvent) -> DeviceLogin:
        return DeviceLogin(
            event_id=row.id,
            account_id=row.account_id,
            device_id=row.device_id,
            success=row.success,
            occurred_at=row.occurred_at,
        )

    return convert(current), [convert(row) for row in rows]
