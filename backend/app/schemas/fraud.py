import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import (
    BaseModel,
    Field,
)


RiskLevel = Literal[
    "low",
    "medium",
    "high",
    "critical",
]

AlertStatus = Literal[
    "open",
    "investigating",
    "resolved",
    "dismissed",
]


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


class FraudScoreFilters(
    BaseModel
):
    risk_level: (
        RiskLevel | None
    ) = None

    min_score: (
        Decimal | None
    ) = Field(
        default=None,
        ge=0,
        le=100,
    )

    limit: int = Field(
        default=50,
        ge=1,
        le=100,
    )

    offset: int = Field(
        default=0,
        ge=0,
    )


class FraudScoreListItem(
    BaseModel
):
    transaction_id: uuid.UUID
    transaction_ref: str

    account_ref: str

    amount: Decimal
    currency: str

    country_code: str
    channel: str

    occurred_at: datetime

    rule_score: Decimal
    ml_score: Decimal
    final_score: Decimal

    risk_level: str

    rule_reasons: list[
        RuleReasonResponse
    ]

    model_version: str
    scored_at: datetime


class FraudScorePage(
    BaseModel
):
    total: int
    limit: int
    offset: int

    items: list[
        FraudScoreListItem
    ]


class FraudSummaryResponse(
    BaseModel
):
    total_scored: int

    low: int
    medium: int
    high: int
    critical: int

    open_alerts: int


class AlertFilters(
    BaseModel
):
    severity: (
        RiskLevel | None
    ) = None

    status: (
        AlertStatus | None
    ) = None

    limit: int = Field(
        default=50,
        ge=1,
        le=100,
    )

    offset: int = Field(
        default=0,
        ge=0,
    )

class AlertTriageRequest(
    BaseModel
):
    status: AlertStatus

    note: (
        str | None
    ) = Field(
        default=None,
        max_length=1000,
    )

class AlertResponse(
    BaseModel
):
    id: uuid.UUID

    transaction_id: (
        uuid.UUID | None
    )

    transaction_ref: (
        str | None
    )

    alert_type: str
    severity: str
    status: str

    title: str
    description: str

    created_at: datetime

    resolved_at: (
        datetime | None
    )


class AlertPage(
    BaseModel
):
    total: int
    limit: int
    offset: int

    items: list[
        AlertResponse
    ]