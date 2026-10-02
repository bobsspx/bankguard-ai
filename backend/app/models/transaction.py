import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Transaction(Base):
    __tablename__ = "transactions"

    __table_args__ = (
        CheckConstraint(
            "amount > 0",
            name="ck_transactions_amount_positive",
        ),
        CheckConstraint(
            "transaction_type IN ("
            "'transfer', "
            "'card_payment', "
            "'cash_withdrawal', "
            "'bill_payment'"
            ")",
            name="ck_transactions_type",
        ),
        CheckConstraint(
            "channel IN ("
            "'mobile', "
            "'web', "
            "'atm', "
            "'branch', "
            "'api'"
            ")",
            name="ck_transactions_channel",
        ),
        CheckConstraint(
            "status IN ("
            "'pending', "
            "'completed', "
            "'declined', "
            "'reversed'"
            ")",
            name="ck_transactions_status",
        ),
        Index(
            "ix_transactions_occurred_at",
            "occurred_at",
        ),
        Index(
            "ix_transactions_account_occurred_at",
            "account_id",
            "occurred_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    transaction_ref: Mapped[str] = mapped_column(
        String(60),
        unique=True,
        nullable=False,
        index=True,
    )

    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id"),
        nullable=False,
        index=True,
    )

    device_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("devices.id"),
        nullable=True,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
    )

    transaction_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    merchant_category: Mapped[str | None] = mapped_column(
        String(80),
    )

    country_code: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
    )

    channel: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    ip_address: Mapped[str | None] = mapped_column(
        String(45),
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="completed",
        nullable=False,
    )

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )