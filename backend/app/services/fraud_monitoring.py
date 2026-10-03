from sqlalchemy import (
    func,
    select,
)
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.alert import Alert
from app.models.fraud_score import (
    FraudScore,
)
from app.models.transaction import (
    Transaction,
)
from app.schemas.fraud import (
    AlertFilters,
    FraudScoreFilters,
)


def get_fraud_summary(
    db: Session,
) -> dict[str, int]:
    total_scored = (
        db.scalar(
            select(
                func.count(
                    FraudScore.id
                )
            )
        )
        or 0
    )

    risk_rows = db.execute(
        select(
            FraudScore.risk_level,
            func.count(
                FraudScore.id
            ),
        )
        .group_by(
            FraudScore.risk_level
        )
    ).all()

    counts = {
        "low": 0,
        "medium": 0,
        "high": 0,
        "critical": 0,
    }

    for risk_level, count in risk_rows:
        if risk_level in counts:
            counts[risk_level] = (
                int(count)
            )

    open_alerts = (
        db.scalar(
            select(
                func.count(
                    Alert.id
                )
            ).where(
                Alert.status
                == "open"
            )
        )
        or 0
    )

    return {
        "total_scored":
            int(total_scored),

        "low":
            counts["low"],

        "medium":
            counts["medium"],

        "high":
            counts["high"],

        "critical":
            counts["critical"],

        "open_alerts":
            int(open_alerts),
    }


def list_fraud_scores(
    db: Session,
    filters: FraudScoreFilters,
):
    conditions = []

    if (
        filters.risk_level
        is not None
    ):
        conditions.append(
            FraudScore.risk_level
            == filters.risk_level
        )

    if (
        filters.min_score
        is not None
    ):
        conditions.append(
            FraudScore.final_score
            >= filters.min_score
        )

    count_statement = (
        select(
            func.count(
                FraudScore.id
            )
        )
        .join(
            Transaction,
            Transaction.id
            == FraudScore.transaction_id,
        )
        .join(
            Account,
            Account.id
            == Transaction.account_id,
        )
    )

    statement = (
        select(
            FraudScore,
            Transaction,
            Account.account_ref,
        )
        .join(
            Transaction,
            Transaction.id
            == FraudScore.transaction_id,
        )
        .join(
            Account,
            Account.id
            == Transaction.account_id,
        )
    )

    if conditions:
        count_statement = (
            count_statement.where(
                *conditions
            )
        )

        statement = (
            statement.where(
                *conditions
            )
        )

    total = (
        db.scalar(
            count_statement
        )
        or 0
    )

    rows = db.execute(
        statement
        .order_by(
            FraudScore.final_score
            .desc(),

            Transaction.occurred_at
            .desc(),
        )
        .limit(
            filters.limit
        )
        .offset(
            filters.offset
        )
    ).all()

    return (
        int(total),
        rows,
    )


def list_alerts(
    db: Session,
    filters: AlertFilters,
):
    conditions = []

    if (
        filters.severity
        is not None
    ):
        conditions.append(
            Alert.severity
            == filters.severity
        )

    if (
        filters.status
        is not None
    ):
        conditions.append(
            Alert.status
            == filters.status
        )

    count_statement = (
        select(
            func.count(
                Alert.id
            )
        )
    )

    statement = (
        select(
            Alert,
            Transaction.transaction_ref,
        )
        .outerjoin(
            Transaction,
            Transaction.id
            == Alert.transaction_id,
        )
    )

    if conditions:
        count_statement = (
            count_statement.where(
                *conditions
            )
        )

        statement = (
            statement.where(
                *conditions
            )
        )

    total = (
        db.scalar(
            count_statement
        )
        or 0
    )

    rows = db.execute(
        statement
        .order_by(
            Alert.created_at.desc()
        )
        .limit(
            filters.limit
        )
        .offset(
            filters.offset
        )
    ).all()

    return (
        int(total),
        rows,
    )