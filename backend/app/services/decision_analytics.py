from sqlalchemy import (
    func,
    select,
)
from sqlalchemy.orm import Session

from app.models.fraud_decision import (
    FraudDecision,
)
from app.models.investigation_case import (
    InvestigationCase,
)
from app.models.transaction import (
    Transaction,
)


def calculate_confirmation_rate(
    confirmed_fraud: int,
    total_reviewed: int,
) -> float:
    if total_reviewed <= 0:
        return 0.0

    return round(
        (
            confirmed_fraud
            / total_reviewed
        )
        * 100,
        2,
    )


def get_decision_summary(
    db: Session,
) -> dict:
    rows = db.execute(
        select(
            FraudDecision.decision,
            func.count(
                FraudDecision.id
            ),
        )
        .group_by(
            FraudDecision.decision
        )
    ).all()

    counts = {
        "confirmed_fraud": 0,
        "false_positive": 0,
        "inconclusive": 0,
    }

    for (
        decision,
        count,
    ) in rows:
        if decision in counts:
            counts[decision] = int(
                count
            )

    total_reviewed = sum(
        counts.values()
    )

    reviewer_count = (
        db.scalar(
            select(
                func.count(
                    func.distinct(
                        FraudDecision
                        .reviewed_by
                    )
                )
            )
        )
        or 0
    )

    return {
        "total_reviewed":
            total_reviewed,

        "confirmed_fraud":
            counts[
                "confirmed_fraud"
            ],

        "false_positive":
            counts[
                "false_positive"
            ],

        "inconclusive":
            counts[
                "inconclusive"
            ],

        "confirmation_rate":
            calculate_confirmation_rate(
                counts[
                    "confirmed_fraud"
                ],
                total_reviewed,
            ),

        "reviewer_count":
            int(
                reviewer_count
            ),
    }


def get_decision_history(
    db: Session,
    *,
    limit: int,
    offset: int,
    decision: str | None = None,
    reviewed_by: str | None = None,
):
    filters = []

    if decision:
        filters.append(
            FraudDecision.decision
            == decision
        )

    if reviewed_by:
        clean_reviewer = (
            reviewed_by
            .strip()
            .lower()
        )

        filters.append(
            FraudDecision.reviewed_by
            == clean_reviewer
        )

    total = (
        db.scalar(
            select(
                func.count(
                    FraudDecision.id
                )
            )
            .where(
                *filters
            )
        )
        or 0
    )

    rows = db.execute(
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
            == FraudDecision
            .transaction_id,
        )
        .where(
            *filters
        )
        .order_by(
            FraudDecision.reviewed_at
            .desc()
        )
        .limit(limit)
        .offset(offset)
    ).all()

    return int(total), rows