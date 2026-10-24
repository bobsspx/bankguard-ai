
"""Build a deterministic security detection evidence snapshot."""

from uuid import UUID

from app.services.security_alert_preview import (
    SecurityAlertPreview,
)


EVIDENCE_VERSION = "security-evidence-v1"


def build_security_evidence(
    preview: SecurityAlertPreview,
) -> dict:
    """Return a JSON-compatible evidence snapshot."""

    # 1. Validate supported alert type
    if preview.alert_type != "FAILED_LOGIN_BURST":
        raise ValueError("Unsupported alert type")

    # 2. Validate triggering event UUID
    if not isinstance(preview.login_event_id, UUID):
        raise TypeError("Invalid triggering event UUID")

    # 3. Ensure evidence is not empty
    ids = preview.evidence_ids

    if not ids:
        raise ValueError("Evidence cannot be empty")

    # 4. Normalize evidence IDs to UUID objects
    normalized_ids: list[UUID] = []

    for evidence_id in ids:
        if isinstance(evidence_id, UUID):
            normalized_ids.append(evidence_id)

        elif isinstance(evidence_id, str):
            try:
                normalized_ids.append(UUID(evidence_id))
            except ValueError as exc:
                raise ValueError(
                    "Invalid evidence UUID"
                ) from exc

        else:
            raise TypeError(
                "Evidence IDs must be UUID or UUID strings"
            )

    evidence_ids = tuple(normalized_ids)

    # 5. Detect duplicate evidence IDs
    if len(evidence_ids) != len(set(evidence_ids)):
        raise ValueError("Duplicate evidence IDs")

    # 6. Verify triggering event is included
    trigger_id = preview.login_event_id

    if trigger_id not in set(evidence_ids):
        raise ValueError("Triggering event missing")

    # 7. Return deterministic JSON-compatible snapshot
    return {
        "evidence_version": EVIDENCE_VERSION,
        "rule_code": preview.alert_type,
        "triggering_event_id": str(trigger_id),
        "evidence_event_ids": sorted(
            str(item) for item in evidence_ids
        ),
        "event_count": len(evidence_ids),
    }
