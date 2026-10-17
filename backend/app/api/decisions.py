import uuid

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
)
from sqlalchemy.orm import Session

from app.api.dependencies import (
    require_permission,
)
from app.db.session import get_db
from app.models.staff_user import (
    StaffUser,
)
from app.schemas.decision import (
    FraudDecisionCreateRequest,
    FraudDecisionPage,
    FraudDecisionResponse,
    FraudDecisionSummaryResponse,
    FraudDecisionValue,
)
from app.services.audit import (
    write_audit_log,
)
from app.services.fraud_decision import (
    CaseNotReadyForDecisionError,
    DecisionAlertNotFoundError,
    DecisionCaseNotFoundError,
    DecisionReviewerConflictError,
    FraudDecisionAlreadyExistsError,
    FraudDecisionNotFoundError,
    create_fraud_decision,
    get_fraud_decision_by_case,
)
from app.services.decision_analytics import (
    get_decision_history,
    get_decision_summary,
)


router = APIRouter(
    prefix="/api/v1/decisions",
    tags=["decisions"],
)


def build_decision_response(
    decision,
    case_ref,
    transaction_ref,
) -> FraudDecisionResponse:
    return FraudDecisionResponse(
        id=decision.id,

        case_id=decision.case_id,

        case_ref=case_ref,

        alert_id=decision.alert_id,

        transaction_id=(
            decision.transaction_id
        ),

        transaction_ref=(
            transaction_ref
        ),

        decision=decision.decision,

        decision_reason=(
            decision.decision_reason
        ),

        reviewed_by=(
            decision.reviewed_by
        ),

        reviewed_at=(
            decision.reviewed_at
        ),

        created_at=(
            decision.created_at
        ),
    )

@router.get(
    "/summary",
    response_model=(
        FraudDecisionSummaryResponse
    ),
)
def read_decision_summary(
    db: Session = Depends(
        get_db
    ),

    _user: StaffUser = Depends(
        require_permission(
            "decisions.read"
        )
    ),
):
    return get_decision_summary(
        db
    )

@router.get(
    "/history",
    response_model=(
        FraudDecisionPage
    ),
)
def read_decision_history(
    decision: (
        FraudDecisionValue
        | None
    ) = None,

    reviewed_by: (
        str
        | None
    ) = None,

    limit: int = Query(
        default=50,
        ge=1,
        le=100,
    ),

    offset: int = Query(
        default=0,
        ge=0,
    ),

    db: Session = Depends(
        get_db
    ),

    _user: StaffUser = Depends(
        require_permission(
            "decisions.read"
        )
    ),
):
    total, rows = (
        get_decision_history(
            db,

            limit=limit,
            offset=offset,

            decision=decision,

            reviewed_by=(
                reviewed_by
            ),
        )
    )

    items = [
        build_decision_response(
            fraud_decision,
            case_ref,
            transaction_ref,
        )
        for (
            fraud_decision,
            case_ref,
            transaction_ref,
        )
        in rows
    ]

    return FraudDecisionPage(
        total=total,
        limit=limit,
        offset=offset,
        items=items,
    )

@router.get(
    "/{case_id}",
    response_model=(
        FraudDecisionResponse
    ),
)
def read_fraud_decision(
    case_id: uuid.UUID,

    db: Session = Depends(
        get_db
    ),

    _user: StaffUser = Depends(
        require_permission(
            "decisions.read"
        )
    ),
):
    try:
        (
            decision,
            case_ref,
            transaction_ref,
        ) = get_fraud_decision_by_case(
            db,
            case_id,
        )

    except FraudDecisionNotFoundError:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=(
                "Fraud decision "
                "not found."
            ),
        )

    return build_decision_response(
        decision,
        case_ref,
        transaction_ref,
    )


@router.post(
    "",
    response_model=(
        FraudDecisionResponse
    ),
    status_code=(
        status.HTTP_201_CREATED
    ),
)
def submit_fraud_decision(
    payload: FraudDecisionCreateRequest,

    request: Request,

    db: Session = Depends(
        get_db
    ),

    user: StaffUser = Depends(
        require_permission(
            "decisions.review"
        )
    ),
):
    try:
        result = create_fraud_decision(
            db,

            case_id=payload.case_id,

            decision=(
                payload.decision
            ),

            decision_reason=(
                payload.decision_reason
            ),

            reviewer_email=(
                user.email
            ),
        )

    except DecisionCaseNotFoundError:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail="Case not found.",
        )

    except DecisionAlertNotFoundError:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail="Alert not found.",
        )

    except FraudDecisionAlreadyExistsError:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "A final fraud "
                "decision already "
                "exists for this case."
            ),
        )

    except CaseNotReadyForDecisionError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=str(exc),
        )

    except DecisionReviewerConflictError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=str(exc),
        )

    fraud_decision = result[
        "decision"
    ]

    case = result["case"]

    alert = result["alert"]

    client_ip = (
        request.client.host
        if request.client
        else None
    )

    write_audit_log(
        db,

        actor_ref=user.email,

        action=(
            "FRAUD_DECISION_CREATED"
        ),

        resource_type=(
            "fraud_decision"
        ),

        resource_id=str(
            fraud_decision.id
        ),

        ip_address=client_ip,

        details={
            "case_ref":
                case.case_ref,

            "transaction_ref":
                result[
                    "transaction_ref"
                ],

            "decision":
                fraud_decision.decision,

            "reviewed_by":
                fraud_decision.reviewed_by,

            "previous_case_status":
                result[
                    "previous_case_status"
                ],

            "new_case_status":
                case.status,

            "previous_alert_status":
                result[
                    "previous_alert_status"
                ],

            "new_alert_status":
                alert.status,

            "reason_length":
                len(
                    fraud_decision
                    .decision_reason
                ),
        },
    )

    db.commit()

    db.refresh(
        fraud_decision
    )

    db.refresh(case)
    db.refresh(alert)

    return build_decision_response(
        fraud_decision,
        case.case_ref,
        result[
            "transaction_ref"
        ],
    )