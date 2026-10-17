from app.services.decision_analytics import (
    calculate_confirmation_rate,
)


def test_confirmation_rate():
    assert (
        calculate_confirmation_rate(
            3,
            4,
        )
        == 75.0
    )


def test_confirmation_rate_zero_total():
    assert (
        calculate_confirmation_rate(
            0,
            0,
        )
        == 0.0
    )


def test_confirmation_rate_rounds():
    assert (
        calculate_confirmation_rate(
            2,
            3,
        )
        == 66.67
    )