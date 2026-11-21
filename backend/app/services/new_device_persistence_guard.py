
"""Fail-closed gate before persisting new-device alerts."""

from app.services.new_device_detection import NewDeviceDetection


def validate_new_device_persistence(
    detection: NewDeviceDetection,
    *,
    history_verified: bool,
) -> None:
    if detection.rule_code != "NEW_DEVICE_LOGIN":
        raise ValueError("Unsupported security rule")

    if history_verified is not True:
        raise ValueError(
            "Verified device history is required"
        )

    if detection.severity != "medium":
        raise ValueError("Unexpected new-device severity")
