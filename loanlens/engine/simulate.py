from __future__ import annotations

import calendar
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from loanlens.config import AppConfig
from loanlens.engine.schedule import generate_schedule
from loanlens.models import (
    AdjustmentMode,
    CompareResult,
    LoanProfile,
    Payment,
    RateRevision,
    ScheduleRow,
    SimulationOutput,
)

ZERO = Decimal("0")
TWOPLACES = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    return value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def _build_output(
    original_schedule: list[ScheduleRow],
    revised_schedule: list[ScheduleRow],
    reference_date: date | None = None,
    prepayment_amount: Decimal = ZERO,
) -> SimulationOutput:
    original_interest = sum((row.interest_component for row in original_schedule), start=ZERO)
    revised_interest = sum((row.interest_component for row in revised_schedule), start=ZERO)
    interest_saved = _money(max(original_interest - revised_interest, ZERO))
    months_saved = max(len(original_schedule) - len(revised_schedule), 0)
    new_emi = ZERO
    if revised_schedule:
        if reference_date is None:
            new_emi = revised_schedule[0].emi_amount
        else:
            future_row = next(
                (row for row in revised_schedule if row.due_date > reference_date),
                revised_schedule[0],
            )
            new_emi = future_row.emi_amount
    new_closure_date = revised_schedule[-1].due_date if revised_schedule else None
    effective_yield_pct = ZERO
    if prepayment_amount > ZERO and months_saved > 0:
        effective_yield_pct = _money(
            (interest_saved / prepayment_amount)
            * (Decimal("12") / Decimal(months_saved))
            * Decimal("100")
        )
    return SimulationOutput(
        revised_schedule=revised_schedule,
        months_saved=months_saved,
        interest_saved=interest_saved,
        new_emi=new_emi,
        new_closure_date=new_closure_date,
        effective_yield_pct=effective_yield_pct,
    )


def simulate_prepayment(
    loan: LoanProfile,
    current_schedule: list[ScheduleRow],
    prepayment_amount: Decimal,
    prepayment_date: date,
    mode: str,
    include_charges: bool,
    config: AppConfig,
) -> SimulationOutput:
    del include_charges
    adjustment_mode = (
        AdjustmentMode.ADJUST_TENURE if mode == "REDUCE_TENURE" else AdjustmentMode.ADJUST_EMI
    )
    payment = Payment(
        loan_id=loan.loan_id,
        payment_date=prepayment_date,
        amount=prepayment_amount,
        payment_type="PREPAYMENT",
    )
    revised_loan = loan.model_copy(update={"adjustment_mode": adjustment_mode})
    revised_schedule = generate_schedule(
        revised_loan,
        rate_revisions=[],
        moratoriums=[],
        payments=[payment],
        od_transactions=[],
        config=config,
    )
    return _build_output(
        current_schedule,
        revised_schedule,
        reference_date=prepayment_date,
        prepayment_amount=prepayment_amount,
    )


def _add_month(current_date: date) -> date:
    year = current_date.year + (current_date.month // 12)
    month = (current_date.month % 12) + 1
    day = min(current_date.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def simulate_recurring(
    loan: LoanProfile,
    current_schedule: list[ScheduleRow],
    monthly_amount: Decimal,
    start_date: date,
    mode: str,
    config: AppConfig,
) -> SimulationOutput:
    adjustment_mode = (
        AdjustmentMode.ADJUST_TENURE if mode == "REDUCE_TENURE" else AdjustmentMode.ADJUST_EMI
    )
    revised_loan = loan.model_copy(update={"adjustment_mode": adjustment_mode})
    payments: list[Payment] = []
    current_date = start_date
    for _ in range(loan.tenure_months):
        payments.append(
            Payment(
                loan_id=loan.loan_id,
                payment_date=current_date,
                amount=monthly_amount,
                payment_type="PREPAYMENT",
            )
        )
        current_date = _add_month(current_date)
    revised_schedule = generate_schedule(
        revised_loan,
        rate_revisions=[],
        moratoriums=[],
        payments=payments,
        od_transactions=[],
        config=config,
    )
    return _build_output(
        current_schedule,
        revised_schedule,
        reference_date=start_date,
        prepayment_amount=monthly_amount,
    )


def simulate_rate_change(
    loan: LoanProfile,
    current_schedule: list[ScheduleRow],
    new_roi: Decimal,
    effective_date: date,
    mode: str,
    config: AppConfig,
) -> SimulationOutput:
    adjustment_mode = (
        AdjustmentMode.ADJUST_TENURE if mode == "REDUCE_TENURE" else AdjustmentMode.ADJUST_EMI
    )
    revision = RateRevision(
        loan_id=loan.loan_id,
        effective_date=effective_date,
        old_roi=loan.roi_initial,
        new_roi=new_roi,
        adjustment_mode=adjustment_mode,
    )
    revised_schedule = generate_schedule(
        loan,
        rate_revisions=[revision],
        moratoriums=[],
        payments=[],
        od_transactions=[],
        config=config,
    )
    return _build_output(current_schedule, revised_schedule, reference_date=effective_date)


def compare_prepay_vs_invest(
    prepayment_amount: Decimal,
    interest_saved: Decimal,
    months_saved: int,
    invest_return_pct: Decimal,
) -> CompareResult:
    if months_saved <= 0:
        investment_value = prepayment_amount
    else:
        monthly_rate = invest_return_pct / Decimal("12") / Decimal("100")
        investment_value = _money(
            prepayment_amount * ((Decimal("1") + monthly_rate) ** months_saved)
        )
    net_advantage = _money(interest_saved - (investment_value - prepayment_amount))
    return CompareResult(
        prepayment_amount=prepayment_amount,
        interest_saved=interest_saved,
        months_saved=months_saved,
        invest_return_pct=invest_return_pct,
        investment_value=investment_value,
        net_prepayment_advantage=net_advantage,
    )
