from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class RoiType(StrEnum):
    FIXED = "FIXED"
    FLOATING = "FLOATING"


class AdjustmentMode(StrEnum):
    ADJUST_EMI = "ADJUST_EMI"
    ADJUST_TENURE = "ADJUST_TENURE"


class LoanProfile(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    loan_id: UUID = Field(default_factory=uuid4)
    name: str
    bank_name: str
    account_number: str
    sanction_amount: Decimal
    disbursed_amount: Decimal
    disbursement_date: date
    roi_initial: Decimal
    roi_type: RoiType
    tenure_months: int
    emi_start_date: date
    emi_day: int
    adjustment_mode: AdjustmentMode
    prepayment_charges_pct: Decimal
    emi_rounding: Literal["rupee", "ten"]
    od_linked: bool = False
    od_account_id: UUID | None = None
    property_value: Decimal | None = None
    notes: str = ""
    is_archived: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator(
        "sanction_amount",
        "disbursed_amount",
        "roi_initial",
        "prepayment_charges_pct",
        "property_value",
    )
    @classmethod
    def _non_negative_decimal(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and value < Decimal("0"):
            msg = "value must be non-negative"
            raise ValueError(msg)
        return value

    @field_validator("tenure_months")
    @classmethod
    def _tenure_positive(cls, value: int) -> int:
        if value <= 0:
            msg = "tenure_months must be greater than zero"
            raise ValueError(msg)
        return value

    @field_validator("emi_day")
    @classmethod
    def _emi_day_valid(cls, value: int) -> int:
        if not 1 <= value <= 31:
            msg = "emi_day must be between 1 and 31"
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def _validate_amounts(self) -> LoanProfile:
        if self.disbursed_amount > self.sanction_amount:
            msg = "disbursed_amount cannot exceed sanction_amount"
            raise ValueError(msg)
        if self.roi_initial <= Decimal("0"):
            msg = "roi_initial must be greater than zero"
            raise ValueError(msg)
        return self
