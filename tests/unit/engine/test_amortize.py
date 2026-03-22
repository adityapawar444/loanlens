from datetime import date
from decimal import Decimal

from loanlens.config import AppConfig
from loanlens.engine.amortize import annual_summary, crossover_point, total_cost
from loanlens.engine.schedule import generate_schedule
from loanlens.models import AdjustmentMode, LoanProfile, RoiType


def _annual_schedule() -> list:
    loan = LoanProfile(
        name="One Year Loan",
        bank_name="Test",
        account_number="123",
        sanction_amount=Decimal("120000"),
        disbursed_amount=Decimal("120000"),
        disbursement_date=date(2024, 4, 1),
        roi_initial=Decimal("12"),
        roi_type=RoiType.FLOATING,
        tenure_months=12,
        emi_start_date=date(2024, 5, 1),
        emi_day=5,
        adjustment_mode=AdjustmentMode.ADJUST_EMI,
        prepayment_charges_pct=Decimal("0"),
        emi_rounding="rupee",
    )
    return generate_schedule(loan, [], [], [], [], AppConfig())


def test_annual_summary() -> None:
    schedule = _annual_schedule()

    summaries = annual_summary(schedule)

    assert len(summaries) == 2
    assert summaries[0].financial_year == "2024-25"
    assert summaries[0].interest_paid == Decimal("7836.61")
    assert summaries[1].closing_balance == Decimal("0.00")


def test_crossover_point() -> None:
    assert crossover_point(_annual_schedule()) == 1


def test_total_cost() -> None:
    result = total_cost(_annual_schedule())
    assert result.principal == Decimal("120000.00")
    assert result.interest == Decimal("7942.16")
    assert result.total == Decimal("127942.16")


def test_amortize_empty_schedule_edge_cases() -> None:
    assert crossover_point([]) == 0
    empty = total_cost([])
    assert empty.principal == Decimal("0")
    assert empty.total == Decimal("0")
