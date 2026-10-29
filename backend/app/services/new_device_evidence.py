
"""Evidence preview for confirmed new-device login detection."""

from uuid import UUID

from app.services.new_device_detection import NewDeviceDetection


def build_new_device_evidence(
    detection: NewDeviceDetection,
    *,
    history_complete: bool,
) -> dict:
    """Create a deterministic evidence snapshot.

    No database writes and no sensitive device fingerprints.
    """
    if detection.rule_code != "NEW_DEVICE_LOGIN":
        raise ValueError("Unsupported detection rule")

    if not history_complete:
        raise ValueError("Incomplete login history")

    for value in (
        detection.triggering_event_id,
        detection.account_id,
        detection.device_id,
    ):
        if not isinstance(value, UUID):
            raise ValueError("Invalid identifier")

    return {
        "evidence_version": "new-device-v1",
        "rule_code": detection.rule_code,
        "triggering_event_id": str(
            detection.triggering_event_id
        ),
        "account_id": str(detection.account_id),
        "device_id": str(detection.device_id),
        "history_complete": True,
        "event_count": 1,
        "evidence_event_ids": [
            str(detection.triggering_event_id)
        ],
    }
