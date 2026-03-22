from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from dateutil.relativedelta import relativedelta  # type: ignore[import-untyped]

from loanlens.engine.emi import calculate_monthly_rate
from loanlens.models import LoanProfile, Moratorium, MoratoriumImpact, MoratoriumType

TWOPLACES = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    return value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def calculate_moratorium_impact(loan: LoanProfile, moratorium: Moratorium) -> MoratoriumImpact:
    if moratorium.loan_id != loan.loan_id:
        msg = "moratorium does not belong to the provided loan"
        raise ValueError(msg)

    span = relativedelta(moratorium.to_date, moratorium.from_date)
    moratorium_months = span.years * 12 + span.months + 1
    monthly_rate = calculate_monthly_rate(loan.roi_initial)
    interest_accrued = _money(loan.disbursed_amount * monthly_rate * Decimal(moratorium_months))

    if moratorium.moratorium_type in {
        MoratoriumType.INTEREST_CAPITALISE,
        MoratoriumType.FULL_DEFER,
    }:
        return MoratoriumImpact(
            moratorium_months=moratorium_months,
            interest_accrued=interest_accrued,
            new_principal=_money(loan.disbursed_amount + interest_accrued),
            deferred_amount=Decimal("0.00"),
        )

    return MoratoriumImpact(
        moratorium_months=moratorium_months,
        interest_accrued=interest_accrued,
        new_principal=_money(loan.disbursed_amount),
        deferred_amount=interest_accrued,
    )
