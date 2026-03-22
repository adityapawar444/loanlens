from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from loanlens.models.schedule import ScheduleRow


class SimulationResult(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    simulation_id: UUID = Field(default_factory=uuid4)
    loan_id: UUID
    simulation_type: Literal["PREPAYMENT", "RECURRING", "RATE_CHANGE", "COMPARE"]
    inputs: dict[str, object]
    outputs: dict[str, object]
    revised_schedule: list[ScheduleRow]
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    label: str = ""


class SimulationOutput(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    revised_schedule: list[ScheduleRow]
    months_saved: int
    interest_saved: Decimal
    new_emi: Decimal
    new_closure_date: date | None
    effective_yield_pct: Decimal

    @field_validator("interest_saved", "new_emi", "effective_yield_pct")
    @classmethod
    def _non_negative_decimal(cls, value: Decimal) -> Decimal:
        if value < Decimal("0"):
            msg = "value must be non-negative"
            raise ValueError(msg)
        return value


class CompareResult(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    prepayment_amount: Decimal
    interest_saved: Decimal
    months_saved: int
    invest_return_pct: Decimal
    investment_value: Decimal
    net_prepayment_advantage: Decimal
