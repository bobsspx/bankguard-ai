import pytest

from app.models.alert import Alert
from app.services.alert_triage import (
    InvalidAlertTransitionError,
    apply_alert_transition,
)


def build_alert(
    status: str = "open",
) -> Alert:
    return Alert(
        alert_type=(
            "transaction_fraud"
        ),
        severity="high",
        status=status,
        title=(
            "Potential fraudulent "
            "transaction"
        ),
        description=(
            "Synthetic fraud alert."
        ),
    )


def test_open_alert_can_move_to_investigating():
    alert = build_alert(
        "open"
    )

    previous, current = (
        apply_alert_transition(
            alert,
            "investigating",
        )
    )

    assert (
        previous
        == "open"
    )

    assert (
        current
        == "investigating"
    )

    assert (
        alert.status
        == "investigating"
    )

    assert (
        alert.resolved_at
        is None
    )


def test_investigating_alert_can_be_resolved():
    alert = build_alert(
        "investigating"
    )

    apply_alert_transition(
        alert,
        "resolved",
    )

    assert (
        alert.status
        == "resolved"
    )

    assert (
        alert.resolved_at
        is not None
    )


def test_open_alert_can_be_dismissed():
    alert = build_alert(
        "open"
    )

    apply_alert_transition(
        alert,
        "dismissed",
    )

    assert (
        alert.status
        == "dismissed"
    )

    assert (
        alert.resolved_at
        is not None
    )


def test_resolved_alert_is_terminal():
    alert = build_alert(
        "resolved"
    )

    with pytest.raises(
        InvalidAlertTransitionError
    ):
        apply_alert_transition(
            alert,
            "investigating",
        )


def test_dismissed_alert_is_terminal():
    alert = build_alert(
        "dismissed"
    )

    with pytest.raises(
        InvalidAlertTransitionError
    ):
        apply_alert_transition(
            alert,
            "open",
        )


def test_same_status_is_idempotent():
    alert = build_alert(
        "open"
    )

    previous, current = (
        apply_alert_transition(
            alert,
            "open",
        )
    )

    assert (
        previous
        == "open"
    )

    assert (
        current
        == "open"
    )

    assert (
        alert.status
        == "open"
    )