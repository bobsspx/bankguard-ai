import uuid

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import (
    require_permission,
)
from app.db.session import get_db
from app.models.staff_user import (
    StaffUser,
)
from app.models.transaction import (
    Transaction,
)
from app.schemas.fraud import (
    FraudBatchResponse,
    FraudScoreResponse,
)
from app.services.audit import (
    write_audit_log,
)
from app.services.fraud_scoring import (
    TransactionNotFoundError,
    score_transaction,
)

from app.models.fraud_score import FraudScore


router = APIRouter(
    prefix="/api/v1/fraud",
    tags=["fraud"],
)


def build_response(
    transaction,
    fraud_score,
) -> FraudScoreResponse:
    return FraudScoreResponse(
        transaction_id=(
            transaction.id
        ),

        transaction_ref=(
            transaction.transaction_ref
        ),

        rule_score=(
            fraud_score.rule_score
        ),

        ml_score=(
            fraud_score.ml_score
        ),

        final_score=(
            fraud_score.final_score
        ),

        risk_level=(
            fraud_score.risk_level
        ),

        rule_reasons=(
            fraud_score.rule_reasons
        ),

        model_version=(
            fraud_score.model_version
        ),

        scored_at=(
            fraud_score.scored_at
        ),
    )


@router.post(
    "/score/{transaction_id}",
    response_model=FraudScoreResponse,
)
def run_transaction_score(
    transaction_id: uuid.UUID,

    request: Request,

    db: Session = Depends(
        get_db
    ),

    user: StaffUser = Depends(
        require_permission(
            "fraud.review"
        )
    ),
):
    try:
        (
            transaction,
            fraud_score,
            _evaluation,
            alert_created,
        ) = score_transaction(
            db,
            transaction_id,
        )

    except TransactionNotFoundError:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=(
                "Transaction not found."
            ),
        )

    client_ip = (
        request.client.host
        if request.client
        else None
    )

    write_audit_log(
        db,

        actor_ref=user.email,

        action=(
            "FRAUD_SCORE_EXECUTED"
        ),

        resource_type=(
            "transaction"
        ),

        resource_id=str(
            transaction.id
        ),

        ip_address=client_ip,

        details={
            "transaction_ref":
                transaction.transaction_ref,

            "rule_score":
                int(
                    fraud_score.rule_score
                ),

            "risk_level":
                fraud_score.risk_level,

            "alert_created":
                alert_created,
        },
    )

    db.commit()
    db.refresh(fraud_score)

    return build_response(
        transaction,
        fraud_score,
    )


@router.post(
    "/score-all",
    response_model=FraudBatchResponse,
)
def run_batch_scoring(
    request: Request,

    db: Session = Depends(
        get_db
    ),

    user: StaffUser = Depends(
        require_permission(
            "fraud.review"
        )
    ),
):
    transactions = (
        db.scalars(
            select(Transaction)
            .outerjoin(
                FraudScore,
                FraudScore.transaction_id == Transaction.id,
            )
            .where(
                FraudScore.id.is_(None)
            )
            .order_by(
                Transaction.occurred_at
            )
            .limit(500)
        )
        .all()
    )

    counts = {
        "low": 0,
        "medium": 0,
        "high": 0,
        "critical": 0,
    }

    alerts_created = 0

    for transaction in transactions:
        (
            _transaction,
            _fraud_score,
            evaluation,
            created,
        ) = score_transaction(
            db,
            transaction.id,
        )

        counts[
            evaluation.risk_level
        ] += 1

        if created:
            alerts_created += 1

    client_ip = (
        request.client.host
        if request.client
        else None
    )

    write_audit_log(
        db,

        actor_ref=user.email,

        action=(
            "FRAUD_BATCH_SCORING"
        ),

        resource_type=(
            "fraud_score"
        ),

        resource_id=None,

        ip_address=client_ip,

        details={
            "processed":
                len(transactions),

            "alerts_created":
                alerts_created,

            "risk_counts":
                counts,
        },
    )

    db.commit()

    return FraudBatchResponse(
        processed=len(
            transactions
        ),

        alerts_created=(
            alerts_created
        ),

        low=counts["low"],
        medium=counts["medium"],
        high=counts["high"],
        critical=(
            counts["critical"]
        ),
    )