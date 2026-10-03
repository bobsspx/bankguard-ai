import uuid
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import (
    func,
    select,
)
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.alert import Alert
from app.models.device import Device
from app.models.fraud_score import (
    FraudScore,
)
from app.models.transaction import (
    Transaction,
)
from app.services.fraud_rules import (
    FraudEvaluation,
    RuleContext,
    evaluate_rules,
)


ALERT_SCORE_THRESHOLD = 50


class TransactionNotFoundError(
    Exception
):
    pass


def build_rule_context(
    db: Session,
    transaction: Transaction,
) -> RuleContext:
    account = db.get(
        Account,
        transaction.account_id,
    )

    if account is None:
        raise TransactionNotFoundError

    device_trusted: bool | None = None

    if transaction.device_id:
        device = db.get(
            Device,
            transaction.device_id,
        )

        if device is not None:
            device_trusted = (
                device.trusted
            )

    window_start = (
        transaction.occurred_at
        - timedelta(minutes=10)
    )

    recent_count = (
        db.scalar(
            select(
                func.count(
                    Transaction.id
                )
            ).where(
                Transaction.account_id
                == transaction.account_id,

                Transaction.id
                != transaction.id,

                Transaction.occurred_at
                >= window_start,

                Transaction.occurred_at
                <= transaction.occurred_at,
            )
        )
        or 0
    )

    return RuleContext(
        amount=Decimal(
            transaction.amount
        ),

        transaction_country=(
            transaction.country_code
        ),

        account_country=(
            account.country_code
        ),

        occurred_at=(
            transaction.occurred_at
        ),

        device_trusted=(
            device_trusted
        ),

        recent_transaction_count=(
            int(recent_count)
        ),
    )


def save_fraud_score(
    db: Session,
    transaction: Transaction,
    evaluation: FraudEvaluation,
) -> FraudScore:
    fraud_score = db.scalar(
        select(
            FraudScore
        ).where(
            FraudScore.transaction_id
            == transaction.id
        )
    )

    if fraud_score is None:
        fraud_score = FraudScore(
            transaction_id=(
                transaction.id
            ),

            rule_score=Decimal(
                evaluation.score
            ),

            ml_score=Decimal("0"),

            final_score=Decimal(
                evaluation.score
            ),

            risk_level=(
                evaluation.risk_level
            ),

            rule_reasons=(
                evaluation.reason_dicts()
            ),

            model_version="rules-v1",
        )

        db.add(fraud_score)

    else:
        fraud_score.rule_score = (
            Decimal(
                evaluation.score
            )
        )

        fraud_score.ml_score = (
            Decimal("0")
        )

        fraud_score.final_score = (
            Decimal(
                evaluation.score
            )
        )

        fraud_score.risk_level = (
            evaluation.risk_level
        )

        fraud_score.rule_reasons = (
            evaluation.reason_dicts()
        )

        fraud_score.model_version = (
            "rules-v1"
        )

    db.flush()

    return fraud_score


def sync_fraud_alert(
    db: Session,
    transaction: Transaction,
    evaluation: FraudEvaluation,
) -> bool:
    if (
        evaluation.score
        < ALERT_SCORE_THRESHOLD
    ):
        return False

    alert = db.scalar(
        select(
            Alert
        ).where(
            Alert.transaction_id
            == transaction.id,

            Alert.alert_type
            == "transaction_fraud",
        )
    )

    rule_codes = [
        reason.code
        for reason in evaluation.reasons
    ]

    description = (
        f"Rule score "
        f"{evaluation.score}/100. "
        f"Triggered rules: "
        f"{', '.join(rule_codes)}."
    )

    if alert is not None:
        alert.severity = (
            evaluation.risk_level
        )

        alert.title = (
            "Potential fraudulent "
            f"transaction "
            f"{transaction.transaction_ref}"
        )

        alert.description = (
            description
        )

        return False

    alert = Alert(
        transaction_id=(
            transaction.id
        ),

        login_event_id=None,

        alert_type=(
            "transaction_fraud"
        ),

        severity=(
            evaluation.risk_level
        ),

        status="open",

        title=(
            "Potential fraudulent "
            f"transaction "
            f"{transaction.transaction_ref}"
        ),

        description=description,
    )

    db.add(alert)
    db.flush()

    return True


def score_transaction(
    db: Session,
    transaction_id: uuid.UUID,
) -> tuple[
    Transaction,
    FraudScore,
    FraudEvaluation,
    bool,
]:
    transaction = db.get(
        Transaction,
        transaction_id,
    )

    if transaction is None:
        raise TransactionNotFoundError

    context = build_rule_context(
        db,
        transaction,
    )

    evaluation = evaluate_rules(
        context
    )

    fraud_score = save_fraud_score(
        db,
        transaction,
        evaluation,
    )

    alert_created = (
        sync_fraud_alert(
            db,
            transaction,
            evaluation,
        )
    )

    return (
        transaction,
        fraud_score,
        evaluation,
        alert_created,
    )