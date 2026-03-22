from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ODBalanceMode(StrEnum):
    DAILY = "DAILY"
    MONTHLY_AVERAGE = "MONTHLY_AVERAGE"


class ODAccount(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    od_account_id: UUID = Field(default_factory=uuid4)
    loan_id: UUID
    limit: Decimal
    current_balance: Decimal = Decimal("0")
    balance_mode: ODBalanceMode = ODBalanceMode.DAILY
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("limit", "current_balance")
    @classmethod
    def _non_negative_amount(cls, value: Decimal) -> Decimal:
        if value < Decimal("0"):
            msg = "value must be non-negative"
            raise ValueError(msg)
        return value


class ODTransaction(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    txn_id: UUID = Field(default_factory=uuid4)
    od_account_id: UUID
    loan_id: UUID
    txn_type: Literal["DEPOSIT", "WITHDRAWAL"]
    amount: Decimal
    txn_date: date
    balance_after: Decimal
    notes: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("amount", "balance_after")
    @classmethod
    def _non_negative_amount(cls, value: Decimal) -> Decimal:
        if value < Decimal("0"):
            msg = "value must be non-negative"
            raise ValueError(msg)
        return value
