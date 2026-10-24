
from uuid import UUID

import pytest

from app.services.security_detection import SecurityDetection
from app.services.security_alert_preview import (
    build_security_alert_preview,
)


def detection(**changes):
    data = {
        "rule_code": "FAILED_LOGIN_BURST",
        "severity": "high",
        "account_id": "ACC-001",
        "event_count": 5,
        "evidence_ids": tuple(
            str(UUID(int=i)) for i in range(1, 6)
        ),
    }
    data.update(changes)
    return SecurityDetection(**data)


def test_builds_alert_preview():
    trigger = UUID(int=5)

    result = build_security_alert_preview(
        detection(), trigger
    )

    assert result.alert_type == "FAILED_LOGIN_BURST"
    assert result.severity == "high"
    assert result.login_event_id == trigger
    assert len(result.evidence_ids) == 5


def test_rejects_missing_trigger():
    with pytest.raises(ValueError, match="Triggering"):
        build_security_alert_preview(
            detection(), UUID(int=99)
        )


def test_rejects_inconsistent_evidence():
    with pytest.raises(ValueError, match="Evidence count"):
        build_security_alert_preview(
            detection(event_count=6), UUID(int=5)
        )


def test_rejects_unknown_rule():
    with pytest.raises(ValueError, match="Unsupported"):
        build_security_alert_preview(
            detection(rule_code="UNKNOWN"), UUID(int=5)
        )


def test_rejects_duplicate_evidence():
    ids = tuple(str(UUID(int=i)) for i in (1, 2, 3, 4, 4))

    with pytest.raises(ValueError, match="Duplicate"):
        build_security_alert_preview(
            detection(evidence_ids=ids), UUID(int=4)
        )
