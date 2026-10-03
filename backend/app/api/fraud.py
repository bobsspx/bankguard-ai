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
    AlertFilters,
    AlertPage,
    AlertResponse,
    FraudBatchResponse,
    FraudScoreFilters,
    FraudScoreListItem,
    FraudScorePage,
    FraudScoreResponse,
    FraudSummaryResponse,
)
from app.services.audit import (
    write_audit_log,
)
from app.services.fraud_scoring import (
    TransactionNotFoundError,
    score_transaction,
)

from app.models.fraud_score import FraudScore
from typing import Annotated
from fastapi import Query
from app.services.fraud_monitoring import (
    get_fraud_summary,
    list_alerts,
    list_fraud_scores,
)


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

@router.get(
    "/summary",
    response_model=FraudSummaryResponse,
)
def read_fraud_summary(
    db: Session = Depends(
        get_db
    ),

    _user: StaffUser = Depends(
        require_permission(
            "fraud.read"
        )
    ),
):
    summary = get_fraud_summary(
        db
    )

    return FraudSummaryResponse(
        **summary
    )


@router.get(
    "/scores",
    response_model=FraudScorePage,
)
def read_fraud_scores(
    filters: Annotated[
        FraudScoreFilters,
        Query(),
    ],

    db: Session = Depends(
        get_db
    ),

    _user: StaffUser = Depends(
        require_permission(
            "fraud.read"
        )
    ),
):
    total, rows = (
        list_fraud_scores(
            db,
            filters,
        )
    )

    items = []

    for (
        fraud_score,
        transaction,
        account_ref,
    ) in rows:
        items.append(
            FraudScoreListItem(
                transaction_id=(
                    transaction.id
                ),

                transaction_ref=(
                    transaction
                    .transaction_ref
                ),

                account_ref=(
                    account_ref
                ),

                amount=(
                    transaction.amount
                ),

                currency=(
                    transaction.currency
                ),

                country_code=(
                    transaction
                    .country_code
                ),

                channel=(
                    transaction.channel
                ),

                occurred_at=(
                    transaction
                    .occurred_at
                ),

                rule_score=(
                    fraud_score
                    .rule_score
                ),

                ml_score=(
                    fraud_score
                    .ml_score
                ),

                final_score=(
                    fraud_score
                    .final_score
                ),

                risk_level=(
                    fraud_score
                    .risk_level
                ),

                rule_reasons=(
                    fraud_score
                    .rule_reasons
                ),

                model_version=(
                    fraud_score
                    .model_version
                ),

                scored_at=(
                    fraud_score
                    .scored_at
                ),
            )
        )

    return FraudScorePage(
        total=total,

        limit=filters.limit,
        offset=filters.offset,

        items=items,
    )


@router.get(
    "/alerts",
    response_model=AlertPage,
)
def read_fraud_alerts(
    filters: Annotated[
        AlertFilters,
        Query(),
    ],

    db: Session = Depends(
        get_db
    ),

    _user: StaffUser = Depends(
        require_permission(
            "alerts.read"
        )
    ),
):
    total, rows = (
        list_alerts(
            db,
            filters,
        )
    )

    items = []

    for (
        alert,
        transaction_ref,
    ) in rows:
        items.append(
            AlertResponse(
                id=alert.id,

                transaction_id=(
                    alert.transaction_id
                ),

                transaction_ref=(
                    transaction_ref
                ),

                alert_type=(
                    alert.alert_type
                ),

                severity=(
                    alert.severity
                ),

                status=(
                    alert.status
                ),

                title=(
                    alert.title
                ),

                description=(
                    alert.description
                ),

                created_at=(
                    alert.created_at
                ),

                resolved_at=(
                    alert.resolved_at
                ),
            )
        )

    return AlertPage(
        total=total,

        limit=filters.limit,
        offset=filters.offset,

        items=items,
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