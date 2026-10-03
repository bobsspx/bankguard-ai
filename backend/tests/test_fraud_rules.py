from datetime import (
    datetime,
    timezone,
)
from decimal import Decimal

from app.services.fraud_rules import (
    RuleContext,
    evaluate_rules,
    get_risk_level,
)


def context(
    *,
    amount="100",
    transaction_country="LA",
    account_country="LA",
    hour=12,
    device_trusted=True,
    recent_transaction_count=0,
):
    return RuleContext(
        amount=Decimal(amount),

        transaction_country=(
            transaction_country
        ),

        account_country=(
            account_country
        ),

        occurred_at=datetime(
            2026,
            10,
            3,
            hour,
            0,
            tzinfo=timezone.utc,
        ),

        device_trusted=(
            device_trusted
        ),

        recent_transaction_count=(
            recent_transaction_count
        ),
    )


def test_normal_transaction_is_low():
    result = evaluate_rules(
        context()
    )

    assert result.score == 0
    assert result.risk_level == "low"
    assert result.reasons == []


def test_high_amount_rule():
    result = evaluate_rules(
        context(
            amount="7000"
        )
    )

    assert result.score == 35

    assert (
        result.reasons[0].code
        == "HIGH_AMOUNT"
    )


def test_cross_border_rule():
    result = evaluate_rules(
        context(
            transaction_country="TH"
        )
    )

    assert result.score == 25

    assert (
        result.reasons[0].code
        == "CROSS_BORDER"
    )


def test_unusual_hour_rule():
    result = evaluate_rules(
        context(
            hour=2
        )
    )

    assert result.score == 15


def test_untrusted_device_rule():
    result = evaluate_rules(
        context(
            device_trusted=False
        )
    )

    assert result.score == 15


def test_velocity_rule():
    result = evaluate_rules(
        context(
            recent_transaction_count=3
        )
    )

    assert result.score == 25


def test_multiple_rules_are_combined():
    result = evaluate_rules(
        context(
            amount="12000",
            transaction_country="CN",
            hour=2,
            device_trusted=False,
            recent_transaction_count=4,
        )
    )

    assert result.score == 100
    assert result.risk_level == "critical"

    assert len(
        result.reasons
    ) == 5


def test_risk_levels():
    assert get_risk_level(0) == "low"

    assert (
        get_risk_level(25)
        == "medium"
    )

    assert (
        get_risk_level(50)
        == "high"
    )

    assert (
        get_risk_level(75)
        == "critical"
    )