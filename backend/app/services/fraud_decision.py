import uuid
from datetime import (
    datetime,
    timezone,
)

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.fraud_decision import (
    FraudDecision,
)
from app.models.investigation_case import (
    InvestigationCase,
)
from app.models.transaction import (
    Transaction,
)
from app.services.case_management import (
    apply_case_transition,
)


class DecisionCaseNotFoundError(
    Exception
):
    pass


class DecisionAlertNotFoundError(
    Exception
):
    pass


class FraudDecisionNotFoundError(
    Exception
):
    pass


class FraudDecisionAlreadyExistsError(
    Exception
):
    pass


class CaseNotReadyForDecisionError(
    Exception
):
    pass


class DecisionReviewerConflictError(
    Exception
):
    pass


def validate_decision_eligibility(
    case: InvestigationCase,
    reviewer_email: str,
) -> None:
    if case.status != "pending_review":
        raise CaseNotReadyForDecisionError(
            (
                "Case must be in "
                "pending_review status "
                "before final decision."
            )
        )

    reviewer = (
        reviewer_email
        .strip()
        .lower()
    )

    assigned = (
        case.assigned_to
        .strip()
        .lower()
        if case.assigned_to
        else None
    )

    if (
        assigned is not None
        and assigned == reviewer
    ):
        raise DecisionReviewerConflictError(
            (
                "The analyst assigned "
                "to the investigation "
                "cannot make the final "
                "fraud decision."
            )
        )


def create_fraud_decision(
    db: Session,
    *,
    case_id: uuid.UUID,
    decision: str,
    decision_reason: str,
    reviewer_email: str,
):
    case = db.scalar(
        select(
            InvestigationCase
        )
        .where(
            InvestigationCase.id
            == case_id
        )
        .with_for_update()
    )

    if case is None:
        raise DecisionCaseNotFoundError

    existing = db.scalar(
        select(
            FraudDecision
        ).where(
            FraudDecision.case_id
            == case.id
        )
    )

    if existing is not None:
        raise (
            FraudDecisionAlreadyExistsError
        )

    validate_decision_eligibility(
        case,
        reviewer_email,
    )

    alert = db.scalar(
        select(Alert)
        .where(
            Alert.id
            == case.alert_id
        )
        .with_for_update()
    )

    if alert is None:
        raise DecisionAlertNotFoundError

    clean_reason = (
        decision_reason.strip()
    )

    transaction_ref = None

    if alert.transaction_id is not None:
        transaction_ref = db.scalar(
            select(
                Transaction.transaction_ref
            ).where(
                Transaction.id
                == alert.transaction_id
            )
        )

    previous_case_status = (
        case.status
    )

    previous_alert_status = (
        alert.status
    )

    fraud_decision = FraudDecision(
        case_id=case.id,
        transaction_id=(
            alert.transaction_id
        ),
        alert_id=alert.id,
        decision=decision,
        decision_reason=(
            clean_reason
        ),
        reviewed_by=(
            reviewer_email
            .strip()
            .lower()
        ),
    )

    apply_case_transition(
        case,
        "closed",
    )

    if decision == "false_positive":
        alert.status = "dismissed"

    else:
        alert.status = "resolved"

    alert.resolved_at = datetime.now(
        timezone.utc
    )

    db.add(fraud_decision)

    db.flush()

    return {
        "decision":
            fraud_decision,

        "case":
            case,

        "alert":
            alert,

        "transaction_ref":
            transaction_ref,

        "previous_case_status":
            previous_case_status,

        "previous_alert_status":
            previous_alert_status,
    }


def get_fraud_decision_by_case(
    db: Session,
    case_id: uuid.UUID,
):
    row = db.execute(
        select(
            FraudDecision,
            InvestigationCase.case_ref,
            Transaction.transaction_ref,
        )
        .join(
            InvestigationCase,
            InvestigationCase.id
            == FraudDecision.case_id,
        )
        .outerjoin(
            Transaction,
            Transaction.id
            == FraudDecision.transaction_id,
        )
        .where(
            FraudDecision.case_id
            == case_id
        )
    ).first()

    if row is None:
        raise FraudDecisionNotFoundError

    return row