from datetime import date
from decimal import Decimal

import pytest

from loanlens.engine.moratorium import calculate_moratorium_impact
from loanlens.models import AdjustmentMode, LoanProfile, Moratorium, MoratoriumType, RoiType


def _loan() -> LoanProfile:
    return LoanProfile(
        name="Moratorium Loan",
        bank_name="Bank",
        account_number="123",
        sanction_amount=Decimal("1000000"),
        disbursed_amount=Decimal("1000000"),
        disbursement_date=date(2024, 1, 1),
        roi_initial=Decimal("12"),
        roi_type=RoiType.FLOATING,
        tenure_months=120,
        emi_start_date=date(2024, 2, 1),
        emi_day=5,
        adjustment_mode=AdjustmentMode.ADJUST_EMI,
        prepayment_charges_pct=Decimal("0"),
        emi_rounding="rupee",
    )


def test_calculate_moratorium_impact_capitalise() -> None:
    loan = _loan()
    moratorium = Moratorium(
        loan_id=loan.loan_id,
        from_date=date(2024, 4, 5),
        to_date=date(2024, 5, 5),
        moratorium_type=MoratoriumType.INTEREST_CAPITALISE,
    )

    result = calculate_moratorium_impact(loan, moratorium)

    assert result.moratorium_months == 2
    assert result.interest_accrued == Decimal("20000.00")
    assert result.new_principal == Decimal("1020000.00")


def test_calculate_moratorium_impact_interest_defer() -> None:
    loan = _loan()
    moratorium = Moratorium(
        loan_id=loan.loan_id,
        from_date=date(2024, 4, 5),
        to_date=date(2024, 5, 5),
        moratorium_type=MoratoriumType.INTEREST_DEFER,
    )

    result = calculate_moratorium_impact(loan, moratorium)

    assert result.deferred_amount == Decimal("20000.00")
    assert result.new_principal == Decimal("1000000.00")


def test_calculate_moratorium_impact_full_defer_matches_capitalise() -> None:
    loan = _loan()
    moratorium = Moratorium(
        loan_id=loan.loan_id,
        from_date=date(2024, 4, 5),
        to_date=date(2024, 5, 5),
        moratorium_type=MoratoriumType.FULL_DEFER,
    )

    result = calculate_moratorium_impact(loan, moratorium)

    assert result.interest_accrued == Decimal("20000.00")
    assert result.new_principal == Decimal("1020000.00")


def test_calculate_moratorium_impact_rejects_wrong_loan() -> None:
    loan = _loan()
    other = _loan()
    moratorium = Moratorium(
        loan_id=other.loan_id,
        from_date=date(2024, 4, 5),
        to_date=date(2024, 5, 5),
        moratorium_type=MoratoriumType.INTEREST_DEFER,
    )

    with pytest.raises(ValueError):
        calculate_moratorium_impact(loan, moratorium)
