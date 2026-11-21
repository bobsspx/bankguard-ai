"""Read persisted device-history coverage without granting trust."""

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.device_history_coverage import (
    DeviceHistoryCoverage,
)

from datetime import datetime, timezone
from app.models.login_event import LoginEvent
from app.models.account import Account


CoverageStatus = Literal[
    "missing",
    "unverified",
    "invalid",
    "pending_verification",
    "verified",
]


@dataclass(frozen=True)
class DeviceHistoryVerification:
    status: CoverageStatus
    history_verified: bool = False

def aware_utc(value: object) -> datetime | None:
    if not isinstance(value, datetime):
        return None

    if value.tzinfo is None or value.utcoffset() is None:
        return None

    return value.astimezone(timezone.utc)


def verify_device_history_coverage(
    db: Session,
    *,
    account_id: UUID,
    event_time: datetime | None = None,
) -> DeviceHistoryVerification:
    with db.no_autoflush:
        coverage = db.scalar(
            select(DeviceHistoryCoverage).where(
                DeviceHistoryCoverage.account_id == account_id
            )
        )

    if coverage is None:
        return DeviceHistoryVerification(
            status="missing",
        )

    if coverage.account_id != account_id:
        return DeviceHistoryVerification(
            status="invalid",
        )

    if coverage.status == "unverified":
        return DeviceHistoryVerification(
            status="unverified",
        )

    if coverage.status != "verified":
        return DeviceHistoryVerification(
            status="invalid",
        )

    # Assign source before checking its value.
    source = coverage.verification_source

    if not isinstance(source, str) or not source.strip():
        return DeviceHistoryVerification(
            status="invalid",
        )

    started_at = aware_utc(
        coverage.coverage_started_at,
    )
    verified_at = aware_utc(
        coverage.verified_at,
    )
    now = datetime.now(timezone.utc)


    if (
        started_at is None
        or verified_at is None
        or verified_at < started_at
        or verified_at > now
    ):
        return DeviceHistoryVerification(
            status="invalid",
        )

    if event_time is not None:
        event_time_utc = aware_utc(event_time)

        if (
            event_time_utc is None
            or event_time_utc < started_at
        ):
            return DeviceHistoryVerification(
                status="invalid",
            )

    # Valid metadata still requires full coverage verification.
    return DeviceHistoryVerification(
        status="pending_verification",
    )

def verify_device_history_for_event(
    db: Session,
    *,
    account_id: UUID,
    current_event_id: UUID,
) -> DeviceHistoryVerification:
    """Validate the persisted triggering event before inspecting coverage."""
    with db.no_autoflush:
        current = db.scalar(
            select(LoginEvent).where(
                LoginEvent.id == current_event_id,
                LoginEvent.account_id == account_id,
            )
        )

    if (
        current is None
        or current.id != current_event_id
        or current.account_id != account_id
    ):
        return DeviceHistoryVerification(status="invalid")

    current_time = aware_utc(current.occurred_at)
    if current_time is None or current_time > datetime.now(timezone.utc):
        return DeviceHistoryVerification(status="invalid")

    return verify_device_history_coverage(
        db,
        account_id=account_id,
        event_time=current_time,
    )


TRUSTED_HISTORY_SOURCE = "bankguard-history-import-v2"


def verify_complete_device_history_for_event(
    db: Session, *, account_id: UUID, current_event_id: UUID,
) -> DeviceHistoryVerification:
    """Validate an operator-controlled lifetime import attestation.

    Metadata-only verification remains inconclusive. Only the reserved importer
    source can attest completeness; no request-supplied boolean grants trust.
    The caller must use a consistent transaction snapshot for detection/writes.
    """
    result = verify_device_history_for_event(
        db, account_id=account_id, current_event_id=current_event_id,
    )
    if result.status != "pending_verification":
        return result

    with db.no_autoflush:
        account = db.scalar(select(Account).where(Account.id == account_id))
        coverage = db.scalar(select(DeviceHistoryCoverage).where(
            DeviceHistoryCoverage.account_id == account_id,
        ))
        current = db.scalar(select(LoginEvent).where(
            LoginEvent.id == current_event_id,
            LoginEvent.account_id == account_id,
        ))

    if (
        account is None or account.id != account_id
        or coverage is None or coverage.account_id != account_id
        or coverage.status != "verified"
        or coverage.verification_source != TRUSTED_HISTORY_SOURCE
        or current is None or current.id != current_event_id
        or current.account_id != account_id
    ):
        return DeviceHistoryVerification(status="invalid")

    created = aware_utc(account.created_at)
    started = aware_utc(coverage.coverage_started_at)
    verified = aware_utc(coverage.verified_at)
    ended = aware_utc(getattr(coverage, "coverage_ended_at", None))
    reference = getattr(coverage, "verification_reference", None)
    if not isinstance(reference, str) or not reference.strip():
        return DeviceHistoryVerification(status="invalid")
    occurred = aware_utc(current.occurred_at)
    if any(value is None for value in (created, started, ended, verified, occurred)):
        return DeviceHistoryVerification(status="invalid")
    if not (started <= created <= occurred <= ended <= verified <= datetime.now(timezone.utc)):
        return DeviceHistoryVerification(status="invalid")
    return DeviceHistoryVerification(status="verified", history_verified=True)

