
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable


FAILED_LOGIN_THRESHOLD = 5
FAILED_LOGIN_WINDOW = timedelta(minutes=10)


@dataclass(frozen=True)
class LoginAttempt:
    event_id: str
    account_id: str
    success: bool
    occurred_at: datetime


@dataclass(frozen=True)
class SecurityDetection:
    rule_code: str
    severity: str
    account_id: str
    event_count: int
    evidence_ids: tuple[str, ...]


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Timezone-aware timestamp required")
    return value.astimezone(timezone.utc)


def detect_failed_login_burst(
    current: LoginAttempt,
    history: Iterable[LoginAttempt],
) -> SecurityDetection | None:
    """Detect 5 failed logins in 10 minutes for one account."""

    current_time = _to_utc(current.occurred_at)

    if current.success:
        return None

    start_time = current_time - FAILED_LOGIN_WINDOW

    matching = {current.event_id: current}

    for event in history:
        event_time = _to_utc(event.occurred_at)

        if event.account_id != current.account_id:
            continue

        if event.success:
            continue

        if not start_time <= event_time <= current_time:
            continue

        # Avoid counting the same event more than once.
        if event.event_id == current.event_id:
            continue

        
        if event.event_id in matching:
            existing = matching[event.event_id]

            if existing != event:
                raise ValueError(
                    "Conflicting login events share the same event_id"
                )

            continue

        matching[event.event_id] = event


    ordered = sorted(
        matching.values(),
        key=lambda event: (
            _to_utc(event.occurred_at),
            event.event_id,
        ),
    )

    if len(ordered) < FAILED_LOGIN_THRESHOLD:
        return None

    return SecurityDetection(
        rule_code="FAILED_LOGIN_BURST",
        severity="high",
        account_id=current.account_id,
        event_count=len(ordered),
        evidence_ids=tuple(
            event.event_id for event in ordered
        ),
    )
