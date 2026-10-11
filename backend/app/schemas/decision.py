import uuid
from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    Field,
)


FraudDecisionValue = Literal[
    "confirmed_fraud",
    "false_positive",
    "inconclusive",
]


class FraudDecisionCreateRequest(
    BaseModel
):
    case_id: uuid.UUID

    decision: FraudDecisionValue

    decision_reason: str = Field(
        min_length=10,
        max_length=4000,
    )


class FraudDecisionResponse(
    BaseModel
):
    id: uuid.UUID

    case_id: uuid.UUID
    case_ref: str

    alert_id: uuid.UUID

    transaction_id: (
        uuid.UUID | None
    )

    transaction_ref: (
        str | None
    )

    decision: FraudDecisionValue

    decision_reason: str

    reviewed_by: str

    reviewed_at: datetime
    created_at: datetime