"""Phase 5F.1: deterministic, read-only transaction features (no ML scoring).

History must be an immutable event snapshot. Current status, decisions, rule
scores, device trust and mutable account profile values are deliberately unused.
Times are UTC; history window is [event - 30 days, event), known by scoring time.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from ipaddress import ip_address
from math import isfinite
from typing import Iterable, Protocol
from uuid import UUID

FEATURE_VERSION = "transaction-features-v1"
FEATURE_NAMES = (
    "amount", "currency", "hour_utc", "weekday_utc", "channel",
    "transaction_type", "merchant_category", "country_code",
    "account_country_mismatch", "history_count_30d", "recent_count_10m",
    "recent_count_24h", "same_currency_count_30d", "mean_amount_30d",
    "amount_to_mean_30d", "recent_amount_24h", "device_missing", "ip_missing",
    "device_unseen_30d", "ip_unseen_30d",
)


class TransactionLike(Protocol):
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


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Timezone-aware timestamps are required")
    return value.astimezone(timezone.utc)


def _amount(value: Decimal) -> Decimal:
    result = Decimal(str(value))
    if not result.is_finite() or result <= 0 or not isfinite(float(result)):
        raise ValueError("Amount must be positive and finite")
    return result


def _ip(value: str | None) -> str | None:
    return str(ip_address(value)) if value else None


@dataclass(frozen=True)
class FeatureRow:
    """Identifiers/version are metadata, never model inputs."""
    transaction_id: UUID
    feature_version: str
    values: tuple[float | int | str | None, ...]

    def as_dict(self) -> dict[str, float | int | str | None]:
        return dict(zip(FEATURE_NAMES, self.values, strict=True))


def extract_transaction_features(
    transaction: TransactionLike,
    history: Iterable[TransactionLike],
    *,
    account_country_at_event: str | None = None,
) -> FeatureRow:
    """Use existing Transaction ORM objects or immutable event DTOs.

    account_country_at_event must be a separately verified historical snapshot,
    NOT today's Account.country_code. Missing context is represented by None.
    Caller must supply all available history for the 30-day window; duplicates
    in eligible history are rejected. No SQL, writes, labels or side effects.
    created_at is the conservative availability cutoff for the target; records
    arriving later are excluded even if their occurred_at is earlier.
    """
    event = _utc(transaction.occurred_at)
    known_at = _utc(transaction.created_at)
    amount = _amount(transaction.amount)
    currency = transaction.currency.upper()
    current_ip = _ip(transaction.ip_address)
    prior = []
    seen = set()
    for item in history:
        if item.id == transaction.id or item.account_id != transaction.account_id:
            continue
        when = _utc(item.occurred_at)
        if not event - timedelta(days=30) <= when < event:
            continue
        if _utc(item.created_at) > known_at:
            continue
        if item.id in seen:
            raise ValueError("Duplicate transaction in eligible history")
        seen.add(item.id)
        prior.append(item)
    # Stable accumulation order even when callers return unordered query results.
    prior.sort(key=lambda item: (_utc(item.occurred_at), str(item.id)))
    same_currency = [p for p in prior if p.currency.upper() == currency]
    amounts = [_amount(p.amount) for p in same_currency]
    mean = sum(amounts, Decimal(0)) / len(amounts) if amounts else None
    recent = [p for p in prior if _utc(p.occurred_at) >= event - timedelta(days=1)]
    recent_amount = sum(
        (_amount(p.amount) for p in recent if p.currency.upper() == currency),
        Decimal(0),
    )
    devices = {p.device_id for p in prior if p.device_id is not None}
    ips = {_ip(p.ip_address) for p in prior if p.ip_address}
    values = (
        float(amount), currency, event.hour, event.weekday(), transaction.channel,
        transaction.transaction_type, transaction.merchant_category,
        transaction.country_code.upper(),
        None if account_country_at_event is None else int(
            transaction.country_code.upper() != account_country_at_event.upper()
        ),
        len(prior),
        sum(_utc(p.occurred_at) >= event - timedelta(minutes=10) for p in prior),
        len(recent), len(same_currency),
        None if mean is None else float(mean),
        None if mean is None else float(amount / mean),
        float(recent_amount), int(transaction.device_id is None),
        int(current_ip is None),
        None if transaction.device_id is None or not devices else int(
            transaction.device_id not in devices
        ),
        None if current_ip is None or not ips else int(current_ip not in ips),
    )
    if any(isinstance(v, float) and not isfinite(v) for v in values):
        raise ValueError("Feature value exceeds finite numeric range")
    return FeatureRow(transaction.id, FEATURE_VERSION, values)
