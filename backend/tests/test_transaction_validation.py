from datetime import (
    datetime,
    timezone,
)
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.transaction import (
    TransactionCreate,
    TransactionFilters,
)


def valid_payload():
    return {
        "transaction_ref":
            "BG-TEST-000001",
        "account_ref":
            "BG-ACC-001",
        "device_ref":
            "BG-DEV-001",
        "amount":
            Decimal("100.00"),
        "currency":
            "USD",
        "transaction_type":
            "transfer",
        "merchant_category":
            "testing",
        "country_code":
            "LA",
        "channel":
            "mobile",
        "ip_address":
            "203.0.113.10",
        "status":
            "completed",
        "occurred_at":
            datetime.now(
                timezone.utc
            ),
    }


def test_valid_transaction():
    transaction = TransactionCreate(
        **valid_payload()
    )

    assert (
        transaction.currency
        == "USD"
    )


def test_negative_amount_rejected():
    payload = valid_payload()
    payload["amount"] = Decimal("-1")

    with pytest.raises(
        ValidationError
    ):
        TransactionCreate(
            **payload
        )


def test_naive_datetime_rejected():
    payload = valid_payload()

    payload["occurred_at"] = (
        datetime.now()
    )

    with pytest.raises(
        ValidationError
    ):
        TransactionCreate(
            **payload
        )


def test_invalid_filter_range():
    with pytest.raises(
        ValidationError
    ):
        TransactionFilters(
            min_amount=Decimal("500"),
            max_amount=Decimal("100"),
        )