import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class RuleReasonResponse(
    BaseModel
):
    code: str
    points: int
    description: str


class FraudScoreResponse(
    BaseModel
):
    transaction_id: uuid.UUID
    transaction_ref: str

    rule_score: Decimal
    ml_score: Decimal
    final_score: Decimal

    risk_level: str

    rule_reasons: list[
        RuleReasonResponse
    ]

    model_version: str

    scored_at: datetime


class FraudBatchResponse(
    BaseModel
):
    processed: int

    alerts_created: int

    low: int
    medium: int
    high: int
    critical: int