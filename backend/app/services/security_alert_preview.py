
from dataclasses import dataclass
from uuid import UUID

from app.services.security_detection import SecurityDetection


SUPPORTED_RULES = frozenset({
    "FAILED_LOGIN_BURST",
})


@dataclass(frozen=True)
class SecurityAlertPreview:
    alert_type: str
    severity: str
    login_event_id: UUID
    evidence_ids: tuple[UUID | str, ...]

    account_id: str | None = None
    event_count: int | None = None
    title: str = "Security alert"
    description: str = "Security detection alert"


def build_security_alert_preview(
    detection: SecurityDetection,
    trigger_event_id: UUID,
) -> SecurityAlertPreview:
    if detection.rule_code not in SUPPORTED_RULES:
        raise ValueError(
            "Unsupported security detection rule"
        )

    evidence_ids = tuple(detection.evidence_ids)

    if len(evidence_ids) != len(set(evidence_ids)):
        raise ValueError("Duplicate evidence IDs")

    if detection.event_count != len(evidence_ids):
        raise ValueError("Evidence count mismatch")

    if detection.event_count <= 0:
        raise ValueError("Evidence count must be positive")

    if str(trigger_event_id) not in {
        str(evidence_id) for evidence_id in evidence_ids
    }:
        raise ValueError(
            "Triggering event is missing from evidence"
    )

    return SecurityAlertPreview(
        alert_type=detection.rule_code,
        severity=detection.severity,
        account_id=detection.account_id,
        login_event_id=trigger_event_id,
        evidence_ids=evidence_ids,
        event_count=detection.event_count,
    )
