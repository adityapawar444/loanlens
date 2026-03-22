from datetime import date
from decimal import Decimal

from loanlens.config import AppConfig
from loanlens.engine.schedule import generate_schedule
from loanlens.engine.simulate import (
    _build_output,
    compare_prepay_vs_invest,
    simulate_prepayment,
    simulate_rate_change,
    simulate_recurring,
)
from loanlens.models import AdjustmentMode, LoanProfile, RoiType


def _loan() -> LoanProfile:
    return LoanProfile(
        name="Simulation Loan",
        bank_name="Bank",
        account_number="SIM123",
        sanction_amount=Decimal("5000000"),
        disbursed_amount=Decimal("5000000"),
        disbursement_date=date(2024, 4, 1),
        roi_initial=Decimal("8.75"),
        roi_type=RoiType.FLOATING,
        tenure_months=240,
        emi_start_date=date(2024, 5, 1),
        emi_day=5,
        adjustment_mode=AdjustmentMode.ADJUST_EMI,
        prepayment_charges_pct=Decimal("0"),
        emi_rounding="rupee",
    )


def test_simulate_prepayment_reduce_tenure() -> None:
    loan = _loan().model_copy(update={"adjustment_mode": AdjustmentMode.ADJUST_TENURE})
    current_schedule = generate_schedule(loan, [], [], [], [], AppConfig())

    result = simulate_prepayment(
        loan,
        current_schedule,
        Decimal("200000"),
        date(2024, 10, 5),
        "REDUCE_TENURE",
        False,
        AppConfig(),
    )

    assert result.months_saved > 0


def test_simulate_prepayment_reduce_emi() -> None:
    loan = _loan().model_copy(update={"adjustment_mode": AdjustmentMode.ADJUST_EMI})
    current_schedule = generate_schedule(loan, [], [], [], [], AppConfig())

    result = simulate_prepayment(
        loan,
        current_schedule,
        Decimal("1000000"),
        date(2024, 10, 5),
        "REDUCE_EMI",
        False,
        AppConfig(),
    )

    assert result.new_emi < current_schedule[0].emi_amount


def test_compare_prepay_vs_invest_sign_flips() -> None:
    low = compare_prepay_vs_invest(Decimal("200000"), Decimal("50000"), 24, Decimal("5"))
    high = compare_prepay_vs_invest(Decimal("200000"), Decimal("50000"), 24, Decimal("20"))

    assert low.net_prepayment_advantage > Decimal("0")
    assert high.net_prepayment_advantage < Decimal("0")


def test_simulate_recurring_saves_several_years() -> None:
    loan = _loan().model_copy(update={"adjustment_mode": AdjustmentMode.ADJUST_TENURE})
    current_schedule = generate_schedule(loan, [], [], [], [], AppConfig())

    result = simulate_recurring(
        loan,
        current_schedule,
        Decimal("5000"),
        date(2024, 6, 5),
        "REDUCE_TENURE",
        AppConfig(),
    )

    assert result.months_saved >= 24


def test_simulate_rate_change_updates_emi() -> None:
    loan = _loan()
    current_schedule = generate_schedule(loan, [], [], [], [], AppConfig())

    result = simulate_rate_change(
        loan,
        current_schedule,
        Decimal("9.50"),
        date(2025, 5, 5),
        "REDUCE_EMI",
        AppConfig(),
    )

    assert result.new_emi >= current_schedule[0].emi_amount


def test_compare_zero_months_and_build_output_no_reference() -> None:
    compare = compare_prepay_vs_invest(Decimal("100000"), Decimal("0"), 0, Decimal("10"))
    assert compare.investment_value == Decimal("100000")

    schedule = generate_schedule(_loan(), [], [], [], [], AppConfig())
    output = _build_output(schedule, schedule)
    assert output.new_emi == schedule[0].emi_amount
