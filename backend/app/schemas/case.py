import uuid
from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    Field,
)


CaseStatus = Literal[
    "open",
    "investigating",
    "pending_review",
    "closed",
]


CasePriority = Literal[
    "low",
    "medium",
    "high",
    "critical",
]


class CaseCreateRequest(
    BaseModel
):
    alert_id: uuid.UUID

    priority: (
        CasePriority | None
    ) = None

    assigned_to: (
        str | None
    ) = Field(
        default=None,
        max_length=100,
    )

    note: (
        str | None
    ) = Field(
        default=None,
        max_length=2000,
    )


class CaseUpdateRequest(
    BaseModel
):
    status: (
        CaseStatus | None
    ) = None

    priority: (
        CasePriority | None
    ) = None

    assigned_to: (
        str | None
    ) = Field(
        default=None,
        max_length=100,
    )

    note: (
        str | None
    ) = Field(
        default=None,
        max_length=2000,
    )


class CaseFilters(
    BaseModel
):
    status: (
        CaseStatus | None
    ) = None

    priority: (
        CasePriority | None
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


class CaseResponse(
    BaseModel
):
    id: uuid.UUID
    case_ref: str

    alert_id: uuid.UUID

    transaction_id: (
        uuid.UUID | None
    )

    transaction_ref: (
        str | None
    )

    alert_severity: str

    status: str
    priority: str

    assigned_to: (
        str | None
    )

    notes: (
        str | None
    )

    created_at: datetime
    updated_at: datetime


class CasePage(
    BaseModel
):
    total: int
    limit: int
    offset: int

    items: list[
        CaseResponse
    ]