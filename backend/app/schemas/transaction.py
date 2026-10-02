import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    IPvAnyAddress,
    field_validator,
    model_validator,
)


TransactionType = Literal[
    "transfer",
    "card_payment",
    "cash_withdrawal",
    "bill_payment",
]

TransactionChannel = Literal[
    "mobile",
    "web",
    "atm",
    "branch",
    "api",
]

TransactionStatus = Literal[
    "pending",
    "completed",
    "declined",
    "reversed",
]


class TransactionCreate(BaseModel):
    transaction_ref: str = Field(
        min_length=6,
        max_length=60,
        pattern=r"^[A-Z0-9-]+$",
    )

    account_ref: str = Field(
        min_length=3,
        max_length=50,
    )

    device_ref: str | None = Field(
        default=None,
        max_length=80,
    )

    amount: Decimal = Field(
        gt=0,
        max_digits=18,
        decimal_places=2,
    )

    currency: str = Field(
        min_length=3,
        max_length=3,
        pattern=r"^[A-Z]{3}$",
    )

    transaction_type: TransactionType

    merchant_category: str | None = Field(
        default=None,
        max_length=80,
    )

    country_code: str = Field(
        min_length=2,
        max_length=2,
        pattern=r"^[A-Z]{2}$",
    )

    channel: TransactionChannel

    ip_address: IPvAnyAddress | None = None

    status: TransactionStatus = "completed"

    occurred_at: datetime

    @field_validator("occurred_at")
    @classmethod
    def require_timezone(
        cls,
        value: datetime,
    ) -> datetime:
        if (
            value.tzinfo is None
            or value.utcoffset() is None
        ):
            raise ValueError(
                "occurred_at must include timezone"
            )

        return value


class TransactionFilters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
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

    account_ref: str | None = Field(
        default=None,
        max_length=50,
    )

    country_code: str | None = Field(
        default=None,
        min_length=2,
        max_length=2,
        pattern=r"^[A-Z]{2}$",
    )

    channel: TransactionChannel | None = None

    status: TransactionStatus | None = None

    min_amount: Decimal | None = Field(
        default=None,
        ge=0,
    )

    max_amount: Decimal | None = Field(
        default=None,
        ge=0,
    )

    start_at: datetime | None = None

    end_at: datetime | None = None

    @model_validator(mode="after")
    def validate_ranges(self):
        if (
            self.min_amount is not None
            and self.max_amount is not None
            and self.min_amount > self.max_amount
        ):
            raise ValueError(
                "min_amount cannot exceed max_amount"
            )

        if (
            self.start_at is not None
            and self.end_at is not None
            and self.start_at > self.end_at
        ):
            raise ValueError(
                "start_at cannot exceed end_at"
            )

        return self


class TransactionResponse(BaseModel):
    id: uuid.UUID

    transaction_ref: str
    account_ref: str
    device_ref: str | None

    amount: Decimal
    currency: str

    transaction_type: str
    merchant_category: str | None

    country_code: str
    channel: str

    ip_address: str | None

    status: str

    occurred_at: datetime
    created_at: datetime


class TransactionPage(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[TransactionResponse]