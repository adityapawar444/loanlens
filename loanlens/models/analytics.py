from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator


class AnnualSummary(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    financial_year: str
    interest_paid: Decimal
    principal_repaid: Decimal
    closing_balance: Decimal

    @field_validator("interest_paid", "principal_repaid", "closing_balance")
    @classmethod
    def _non_negative(cls, value: Decimal) -> Decimal:
        if value < Decimal("0"):
            msg = "value must be non-negative"
            raise ValueError(msg)
        return value


class TotalCost(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    principal: Decimal
    interest: Decimal
    total: Decimal

    @field_validator("principal", "interest", "total")
    @classmethod
    def _non_negative(cls, value: Decimal) -> Decimal:
        if value < Decimal("0"):
            msg = "value must be non-negative"
            raise ValueError(msg)
        return value


class MoratoriumImpact(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    moratorium_months: int
    interest_accrued: Decimal
    new_principal: Decimal
    deferred_amount: Decimal

    @field_validator("interest_accrued", "new_principal", "deferred_amount")
    @classmethod
    def _non_negative_money(cls, value: Decimal) -> Decimal:
        if value < Decimal("0"):
            msg = "value must be non-negative"
            raise ValueError(msg)
        return value
