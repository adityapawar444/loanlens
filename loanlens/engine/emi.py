from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, localcontext
from typing import Literal, cast

TWELVE = Decimal("12")
ONE_HUNDRED = Decimal("100")


def calculate_monthly_rate(annual_roi: Decimal) -> Decimal:
    return annual_roi / TWELVE / ONE_HUNDRED


def _round_emi(amount: Decimal, rounding: Literal["rupee", "ten"]) -> Decimal:
    quantum = Decimal("1") if rounding == "rupee" else Decimal("10")
    return amount.quantize(quantum, rounding=ROUND_HALF_UP)


def _validate_rounding(rounding: str) -> Literal["rupee", "ten"]:
    if rounding not in {"rupee", "ten"}:
        msg = "rounding must be 'rupee' or 'ten'"
        raise ValueError(msg)
    return cast(Literal["rupee", "ten"], rounding)


def calculate_emi(
    principal: Decimal,
    annual_roi: Decimal,
    tenure_months: int,
    rounding: Literal["rupee", "ten"],
) -> Decimal:
    if tenure_months <= 0:
        msg = "tenure_months must be greater than zero"
        raise ValueError(msg)
    if principal < Decimal("0"):
        msg = "principal must be non-negative"
        raise ValueError(msg)
    if annual_roi < Decimal("0"):
        msg = "annual_roi must be non-negative"
        raise ValueError(msg)
    rounding_mode = _validate_rounding(rounding)
    if principal == Decimal("0"):
        return Decimal("0")
    if annual_roi == Decimal("0"):
        return _round_emi(principal / Decimal(tenure_months), rounding_mode)

    monthly_rate = calculate_monthly_rate(annual_roi)
    with localcontext() as ctx:
        ctx.prec = 28
        growth = (Decimal("1") + monthly_rate) ** tenure_months
        emi = principal * monthly_rate * growth / (growth - Decimal("1"))
    return _round_emi(emi, rounding_mode)
