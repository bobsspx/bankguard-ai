import uuid

import pytest

from app.models.investigation_case import (
    InvestigationCase,
)
from app.services.fraud_decision import (
    CaseNotReadyForDecisionError,
    DecisionReviewerConflictError,
    validate_decision_eligibility,
)


def build_case(
    *,
    status: str = "pending_review",
    assigned_to: str | None = (
        "fraud@bankguard.demo"
    ),
):
    return InvestigationCase(
        case_ref=(
            "CASE-2026-000100"
        ),
        alert_id=uuid.uuid4(),
        status=status,
        priority="high",
        assigned_to=assigned_to,
    )


def test_reviewer_can_decide_pending_review_case():
    case = build_case()

    validate_decision_eligibility(
        case,
        "reviewer@bankguard.demo",
    )


def test_case_must_be_pending_review():
    case = build_case(
        status="investigating",
    )

    with pytest.raises(
        CaseNotReadyForDecisionError
    ):
        validate_decision_eligibility(
            case,
            "reviewer@bankguard.demo",
        )


def test_investigator_cannot_review_own_case():
    case = build_case(
        assigned_to=(
            "reviewer@bankguard.demo"
        ),
    )

    with pytest.raises(
        DecisionReviewerConflictError
    ):
        validate_decision_eligibility(
            case,
            "reviewer@bankguard.demo",
        )