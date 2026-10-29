
"""Convert validated new-device detections into alert previews."""

from uuid import UUID

from app.services.new_device_detection import NewDeviceDetection
from app.services.security_alert_preview import SecurityAlertPreview


def build_new_device_alert_preview(
    detection: NewDeviceDetection,
) -> SecurityAlertPreview:
    if detection.rule_code != "NEW_DEVICE_LOGIN":
        raise ValueError("Unsupported detection rule")

    if detection.severity != "medium":
        raise ValueError("Unexpected severity")

    for value in (
        detection.triggering_event_id,
        detection.account_id,
        detection.device_id,
    ):
        if not isinstance(value, UUID):
            raise TypeError("Expected UUID identifiers")

    return SecurityAlertPreview(
        alert_type="NEW_DEVICE_LOGIN",
        severity=detection.severity,
        login_event_id=detection.triggering_event_id,
        evidence_ids=(str(detection.triggering_event_id),),
        account_id=str(detection.account_id),
        event_count=1,
        title="New device login detected",
        description="Successful login from a previously unseen device.",
    )
