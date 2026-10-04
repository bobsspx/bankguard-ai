import pytest
import uuid

from app.models.investigation_case import (
    InvestigationCase,
)
from app.services.case_management import (
    InvalidCaseTransitionError,
    append_case_note,
    apply_case_transition,
    priority_from_severity,
)


def build_case(
    status: str = "open",
):
    return InvestigationCase(
        case_ref=(
            "CASE-2026-000001"
        ),
        alert_id=uuid.uuid4(),
        status=status,
        priority="high",
    )


def test_alert_severity_maps_to_priority():
    assert (
        priority_from_severity(
            "critical"
        )
        == "critical"
    )

    assert (
        priority_from_severity(
            "high"
        )
        == "high"
    )


def test_open_case_can_start_investigation():
    case = build_case(
        "open"
    )

    apply_case_transition(
        case,
        "investigating",
    )

    assert (
        case.status
        == "investigating"
    )


def test_investigation_can_move_to_review():
    case = build_case(
        "investigating"
    )

    apply_case_transition(
        case,
        "pending_review",
    )

    assert (
        case.status
        == "pending_review"
    )


def test_pending_review_can_close():
    case = build_case(
        "pending_review"
    )

    apply_case_transition(
        case,
        "closed",
    )

    assert (
        case.status
        == "closed"
    )


def test_closed_case_is_terminal():
    case = build_case(
        "closed"
    )

    with pytest.raises(
        InvalidCaseTransitionError
    ):
        apply_case_transition(
            case,
            "investigating",
        )


def test_same_case_status_is_idempotent():
    case = build_case(
        "investigating"
    )

    previous, current = (
        apply_case_transition(
            case,
            "investigating",
        )
    )

    assert (
        previous
        == "investigating"
    )

    assert (
        current
        == "investigating"
    )


def test_case_note_is_appended():
    case = build_case()

    append_case_note(
        case,
        actor_ref=(
            "fraud@bankguard.demo"
        ),
        note=(
            "Reviewed transaction."
        ),
    )

    assert case.notes

    assert (
        "fraud@bankguard.demo"
        in case.notes
    )

    assert (
        "Reviewed transaction."
        in case.notes
    )