from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class ScheduleStatus(StrEnum):
    UPCOMING = "UPCOMING"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    MORATORIUM = "MORATORIUM"
    PREPAID = "PREPAID"


class ScheduleRow(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    loan_id: UUID
    instalment_number: int
    due_date: date
    opening_principal: Decimal
    emi_amount: Decimal
    interest_component: Decimal
    principal_component: Decimal
    prepayment_amount: Decimal = Decimal("0")
    closing_principal: Decimal
    cumulative_interest: Decimal
    cumulative_principal: Decimal
    od_interest_saved: Decimal = Decimal("0")
    status: ScheduleStatus = ScheduleStatus.UPCOMING

    @field_validator(
        "opening_principal",
        "emi_amount",
        "interest_component",
        "principal_component",
        "prepayment_amount",
        "closing_principal",
        "cumulative_interest",
        "cumulative_principal",
        "od_interest_saved",
    )
    @classmethod
    def _non_negative_decimal(cls, value: Decimal) -> Decimal:
        if value < Decimal("0"):
            msg = "value must be non-negative"
            raise ValueError(msg)
        return value
