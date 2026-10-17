"""Read-only adapter for the existing transaction feature extractor.

For consistent multi-query reads, use a fresh REPEATABLE READ transaction.
Never pass a session containing pending writes. No API exposure is added here.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.transaction import Transaction
from app.services.ml_features import FeatureRow, extract_transaction_features


class FeatureTransactionNotFoundError(LookupError):
    pass


@dataclass(frozen=True)
class TransactionSnapshot:
    id: UUID
    account_id: UUID
    device_id: UUID | None
    amount: Decimal
    currency: str
    transaction_type: str
    merchant_category: str | None
    country_code: str
    channel: str
    ip_address: str | None
    occurred_at: datetime
    created_at: datetime


SNAPSHOT_COLUMNS = tuple(
    getattr(Transaction, name) for name in TransactionSnapshot.__dataclass_fields__
)


def history_statement(target: TransactionSnapshot):
    """Filter in SQL as well as in the pure extractor; never truncate history."""
    return select(*SNAPSHOT_COLUMNS).where(
        Transaction.account_id == target.account_id,
        Transaction.id != target.id,
        Transaction.occurred_at >= target.occurred_at - timedelta(days=30),
        Transaction.occurred_at < target.occurred_at,
        Transaction.created_at <= target.created_at,
    ).order_by(Transaction.occurred_at, Transaction.id)


def load_transaction_features(db: Session, transaction_id: UUID) -> FeatureRow:
    """Load persisted values, bypassing cached ORM entities and mutable profiles.

    Does not commit, flush, rollback or close the caller's session. Historical
    account country remains unknown; identifiers are only used for joins.
    """
    if db.new or db.dirty or db.deleted:
        raise ValueError("Feature reads require a session without pending writes")
    with db.no_autoflush:
        row = db.execute(
            select(*SNAPSHOT_COLUMNS).where(Transaction.id == transaction_id)
        ).mappings().one_or_none()
        if row is None:
            raise FeatureTransactionNotFoundError(str(transaction_id))
        target = TransactionSnapshot(**row)
        # Validate target timestamps/amount before issuing the historical query.
        extract_transaction_features(target, ())
        rows = db.execute(history_statement(target)).mappings()
        history = (TransactionSnapshot(**item) for item in rows)
        return extract_transaction_features(target, history)
