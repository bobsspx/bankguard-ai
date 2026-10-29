
"""New-device login detection: pure, read-only logic."""

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID


@dataclass(frozen=True)
class DeviceLogin:
    event_id: UUID
    account_id: UUID
    device_id: UUID | None
    success: bool
    occurred_at: datetime


@dataclass(frozen=True)
class NewDeviceDetection:
    rule_code: str
    triggering_event_id: UUID
    account_id: UUID
    device_id: UUID
    severity: str


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Timezone-aware datetime required")
    return value.astimezone(timezone.utc)


def detect_new_device_login(
    current: DeviceLogin,
    history: list[DeviceLogin],
    *,
    history_complete: bool = False,
) -> NewDeviceDetection | None:
    """Detect first successful use of a device.

    Incomplete history is inconclusive, not proof of
    a new device.
    """
    current_time = _utc(current.occurred_at)

    if not current.success or current.device_id is None:
        return None

    if not history_complete:
        return None

    for event in history:
        event_time = _utc(event.occurred_at)

        if event.event_id == current.event_id:
            continue

        if event_time >= current_time:
            continue

        if event.account_id != current.account_id:
            continue

        if event.success and event.device_id == current.device_id:
            return None

    return NewDeviceDetection(
        rule_code="NEW_DEVICE_LOGIN",
        triggering_event_id=current.event_id,
        account_id=current.account_id,
        device_id=current.device_id,
        severity="medium",
    )
