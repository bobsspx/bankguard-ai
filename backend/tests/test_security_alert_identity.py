
from uuid import UUID

import pytest

from app.services.security_alert_identity import (
    security_alert_identity,
)


def test_same_event_produces_same_identity():
    event_id = UUID(int=100)

    first = security_alert_identity(
        "FAILED_LOGIN_BURST", event_id
    )
    second = security_alert_identity(
        "FAILED_LOGIN_BURST", event_id
    )

    assert first == second


def test_different_events_have_different_identities():
    first = security_alert_identity(
        "FAILED_LOGIN_BURST", UUID(int=100)
    )
    second = security_alert_identity(
        "FAILED_LOGIN_BURST", UUID(int=101)
    )

    assert first != second


def test_identity_contains_rule_and_event():
    event_id = UUID(int=100)

    result = security_alert_identity(
        "FAILED_LOGIN_BURST", event_id
    )

    assert result == f"FAILED_LOGIN_BURST:{event_id}"


def test_unknown_rule_is_rejected():
    with pytest.raises(ValueError, match="Unsupported"):
        security_alert_identity(
            "UNKNOWN_RULE", UUID(int=100)
        )


def test_invalid_event_id_is_rejected():
    with pytest.raises(TypeError, match="UUID"):
        security_alert_identity(
            "FAILED_LOGIN_BURST",
            "not-a-uuid",
        )
