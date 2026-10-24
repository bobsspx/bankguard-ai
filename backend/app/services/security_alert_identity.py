
"""Deterministic identity for security alert deduplication."""

from uuid import UUID


SUPPORTED_SECURITY_RULES = frozenset({
    "FAILED_LOGIN_BURST",
})


def security_alert_identity(
    rule_code: str,
    triggering_event_id: UUID,
) -> str:
    """Return a stable identity for one security alert."""

    if rule_code not in SUPPORTED_SECURITY_RULES:
        raise ValueError("Unsupported security rule")

    if not isinstance(triggering_event_id, UUID):
        raise TypeError("triggering_event_id must be UUID")

    return (
        f"{rule_code}:"
        f"{str(triggering_event_id)}"
    )
