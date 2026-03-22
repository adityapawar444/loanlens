from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Payment(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    payment_id: UUID = Field(default_factory=uuid4)
    loan_id: UUID
    payment_date: date
    amount: Decimal
    payment_type: Literal["EMI", "PREPAYMENT", "INTEREST_ONLY"]
    instalment_number: int | None = None
    reference: str = ""
    notes: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("amount")
    @classmethod
    def _positive_amount(cls, value: Decimal) -> Decimal:
        if value <= Decimal("0"):
            msg = "amount must be greater than zero"
            raise ValueError(msg)
        return value
