from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.fraud import (
    AlertFilters,
    FraudScoreFilters,
)


def test_valid_fraud_filters():
    filters = FraudScoreFilters(
        risk_level="critical",
        min_score=Decimal("75"),
        limit=20,
        offset=0,
    )

    assert (
        filters.risk_level
        == "critical"
    )

    assert (
        filters.min_score
        == Decimal("75")
    )


def test_invalid_risk_level():
    with pytest.raises(
        ValidationError
    ):
        FraudScoreFilters(
            risk_level="danger"
        )


def test_invalid_score_range():
    with pytest.raises(
        ValidationError
    ):
        FraudScoreFilters(
            min_score=Decimal(
                "101"
            )
        )


def test_limit_above_100():
    with pytest.raises(
        ValidationError
    ):
        FraudScoreFilters(
            limit=101
        )


def test_valid_alert_filters():
    filters = AlertFilters(
        severity="high",
        status="open",
    )

    assert (
        filters.status
        == "open"
    )


def test_invalid_alert_status():
    with pytest.raises(
        ValidationError
    ):
        AlertFilters(
            status="deleted"
        )