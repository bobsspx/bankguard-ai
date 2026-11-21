
"""Account-level login history coverage metadata."""

import uuid

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    String,
    CheckConstraint,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class DeviceHistoryCoverage(Base):
    __tablename__ = "device_history_coverage"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    account_id = Column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id"),
        nullable=False,
    )

    coverage_started_at = Column(
        DateTime(timezone=True),
        nullable=False,
    )

    verified_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    coverage_ended_at = Column(DateTime(timezone=True), nullable=True)
    verification_reference = Column(String(200), nullable=True)

    verification_source = Column(
        String(100),
        nullable=True,
    )

    status = Column(
        String(20),
        nullable=False,
        default="unverified",
        server_default="unverified",
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "coverage_ended_at IS NULL OR "
            "(coverage_ended_at >= coverage_started_at "
            "AND verified_at IS NOT NULL AND verified_at >= coverage_ended_at)",
            name="ck_device_history_coverage_interval",
        ),
        UniqueConstraint(
            "account_id",
            name="uq_device_history_coverage_account",
        ),
        CheckConstraint(
            "status IN ('unverified', 'verified')",
            name="ck_device_history_coverage_status",
        ),
        CheckConstraint(
            "status <> 'verified' OR "
            "(verified_at IS NOT NULL "
            "AND verification_source IS NOT NULL)",
            name="ck_device_history_coverage_verification",
        ),
    )
