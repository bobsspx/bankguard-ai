
"""Read-only SQLAlchemy adapter for failed-login detection."""

from datetime import timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.login_event import LoginEvent
from app.services.security_detection import (
    FAILED_LOGIN_WINDOW,
    LoginAttempt,
    SecurityDetection,
    _to_utc,
    detect_failed_login_burst,
)


class LoginEventNotFoundError(LookupError):
    pass


def load_failed_login_detection(
    db: Session,
    event_id: UUID,
) -> SecurityDetection | None:
    """Evaluate a persisted login event without writing to DB."""

    if db.new or db.dirty or db.deleted:
        raise ValueError(
            "Detection reads require no pending writes"
        )

    with db.no_autoflush:
        current = db.scalar(
            select(LoginEvent).where(
                LoginEvent.id == event_id
            )
        )

        if current is None:
            raise LoginEventNotFoundError(str(event_id))

        current_time = _to_utc(current.occurred_at)

        target = LoginAttempt(
            event_id=str(current.id),
            account_id=str(current.account_id),
            success=current.success,
            occurred_at=current.occurred_at,
        )

        if target.success:
            return None


        statement = (
            select(
                LoginEvent.id,
                LoginEvent.account_id,
                LoginEvent.success,
                LoginEvent.occurred_at,
            )
            .where(
                LoginEvent.account_id == current.account_id,
                LoginEvent.id != current.id,
                LoginEvent.success.is_(False),
                LoginEvent.occurred_at >= (
                    current_time - FAILED_LOGIN_WINDOW
                ),
                LoginEvent.occurred_at <= current_time,
            )
            .order_by(
                LoginEvent.occurred_at,
                LoginEvent.id,
            )
        )

        rows = db.execute(statement).mappings().all()



        history = [
            LoginAttempt(
                event_id=str(item["id"]),
                account_id=str(item["account_id"]),
                success=item["success"],
                occurred_at=item["occurred_at"],
            )
            for item in rows
        ]

        return detect_failed_login_burst(
            target,
            history,
        )
