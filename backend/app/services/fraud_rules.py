from dataclasses import (
    asdict,
    dataclass,
)
from datetime import (
    datetime,
    timezone,
)
from decimal import Decimal


HIGH_AMOUNT_THRESHOLD = Decimal(
    "6500"
)

RAPID_TRANSACTION_THRESHOLD = 3


@dataclass(frozen=True)
class RuleContext:
    amount: Decimal

    transaction_country: str
    account_country: str

    occurred_at: datetime

    device_trusted: bool | None

    recent_transaction_count: int


@dataclass(frozen=True)
class RuleHit:
    code: str
    points: int
    description: str


@dataclass(frozen=True)
class FraudEvaluation:
    score: int
    risk_level: str
    reasons: list[RuleHit]

    def reason_dicts(
        self,
    ) -> list[dict]:
        return [
            asdict(reason)
            for reason in self.reasons
        ]


def get_risk_level(
    score: int,
) -> str:
    if score >= 75:
        return "critical"

    if score >= 50:
        return "high"

    if score >= 25:
        return "medium"

    return "low"


def evaluate_rules(
    context: RuleContext,
) -> FraudEvaluation:
    reasons: list[RuleHit] = []

    # RULE 1
    # High-value transaction
    if (
        context.amount
        >= HIGH_AMOUNT_THRESHOLD
    ):
        reasons.append(
            RuleHit(
                code="HIGH_AMOUNT",
                points=35,
                description=(
                    "Transaction amount "
                    "is at or above "
                    "$6,500."
                ),
            )
        )

    # RULE 2
    # Cross-border transaction
    if (
        context.transaction_country
        != context.account_country
    ):
        reasons.append(
            RuleHit(
                code="CROSS_BORDER",
                points=25,
                description=(
                    "Transaction country "
                    "differs from account "
                    "country."
                ),
            )
        )

    # RULE 3
    # Unusual transaction time
    occurred_utc = (
        context.occurred_at
        .astimezone(timezone.utc)
    )

    if 0 <= occurred_utc.hour < 5:
        reasons.append(
            RuleHit(
                code="UNUSUAL_HOUR",
                points=15,
                description=(
                    "Transaction occurred "
                    "between 00:00 and "
                    "04:59 UTC."
                ),
            )
        )

    # RULE 4
    # Unknown or untrusted device
    if context.device_trusted is not True:
        reasons.append(
            RuleHit(
                code="UNTRUSTED_DEVICE",
                points=15,
                description=(
                    "Transaction used an "
                    "unknown or untrusted "
                    "device."
                ),
            )
        )

    # RULE 5
    # Transaction velocity
    if (
        context.recent_transaction_count
        >= RAPID_TRANSACTION_THRESHOLD
    ):
        reasons.append(
            RuleHit(
                code="RAPID_VELOCITY",
                points=25,
                description=(
                    "Account performed at "
                    "least 3 other "
                    "transactions within "
                    "10 minutes."
                ),
            )
        )

    score = min(
        sum(
            rule.points
            for rule in reasons
        ),
        100,
    )

    return FraudEvaluation(
        score=score,
        risk_level=get_risk_level(
            score
        ),
        reasons=reasons,
    )