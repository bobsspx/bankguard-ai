
from dataclasses import replace
from uuid import UUID

import pytest

from app.services.security_alert_preview import (
    SecurityAlertPreview,
)
from app.services.security_evidence import (
    build_security_evidence,
)


def preview():
    return SecurityAlertPreview(
        alert_type="FAILED_LOGIN_BURST",
        severity="high",
        title="Multiple failed login attempts",
        description="Synthetic detection",
        login_event_id=UUID(int=5),
        evidence_ids=tuple(
            UUID(int=i) for i in range(1, 6)
        ),
    )


def test_builds_complete_evidence():
    result = build_security_evidence(preview())

    assert result["evidence_version"] == "security-evidence-v1"
    assert result["rule_code"] == "FAILED_LOGIN_BURST"
    assert result["event_count"] == 5
    assert len(result["evidence_event_ids"]) == 5
    assert result["triggering_event_id"] in result["evidence_event_ids"]


def test_evidence_is_deterministic():
    original = preview()
    reversed_preview = replace(
        original,
        evidence_ids=tuple(reversed(original.evidence_ids)),
    )

    assert build_security_evidence(original) == (
        build_security_evidence(reversed_preview)
    )


def test_rejects_duplicate_events():
    item = replace(
        preview(),
        evidence_ids=(
            UUID(int=5),
            UUID(int=5),
        ),
    )

    with pytest.raises(ValueError, match="Duplicate"):
        build_security_evidence(item)


def test_rejects_missing_trigger():
    item = replace(
        preview(),
        login_event_id=UUID(int=99),
    )

    with pytest.raises(ValueError, match="Triggering"):
        build_security_evidence(item)


def test_rejects_empty_evidence():
    item = replace(preview(), evidence_ids=())

    with pytest.raises(ValueError, match="empty"):
        build_security_evidence(item)
