
"""Tests for multi-rule security alert registration."""

from app.services.security_alert_preview import SUPPORTED_RULES
from app.services.security_alert_identity import (
    SUPPORTED_SECURITY_RULES,
    security_alert_identity,
)
from uuid import uuid4

import pytest


REQUIRED_RULES = {
    "FAILED_LOGIN_BURST",
    "NEW_DEVICE_LOGIN",
}


def test_preview_supports_both_rules():
    assert REQUIRED_RULES <= set(SUPPORTED_RULES)


def test_identity_supports_both_rules():
    assert REQUIRED_RULES <= set(SUPPORTED_SECURITY_RULES)


@pytest.mark.parametrize("rule", sorted(REQUIRED_RULES))
def test_identity_is_deterministic(rule):
    event_id = uuid4()

    first = security_alert_identity(rule, event_id)
    second = security_alert_identity(rule, event_id)

    assert first == second
    assert rule in first
    assert str(event_id) in first


def test_rules_produce_different_identities():
    event_id = uuid4()

    failed_login = security_alert_identity(
        "FAILED_LOGIN_BURST", event_id
    )
    new_device = security_alert_identity(
        "NEW_DEVICE_LOGIN", event_id
    )

    assert failed_login != new_device


def test_unknown_rule_still_rejected():
    with pytest.raises(ValueError):
        security_alert_identity(
            "UNKNOWN_RULE",
            uuid4(),
        )
