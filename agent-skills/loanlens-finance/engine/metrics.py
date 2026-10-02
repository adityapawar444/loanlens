"""
metrics.py — Summary metrics calculation.

Port of calculations.ts calculateMetrics (L235-298).
"""

from __future__ import annotations

import datetime
from typing import Optional

from .emi import calculate_emi
from .schedule import _format_date_only, _parse_date_only
from .types import AmortizationRow, LoanData, SummaryMetrics


def calculate_metrics(
    data: LoanData,
    schedule: list[AmortizationRow],
    today_date: Optional[str] = None,
) -> SummaryMetrics:
    """
    Calculate summary metrics from the schedule.

    Matches calculations.ts calculateMetrics (L235-298).
    today_date is a YYYY-MM-DD string (or None for today).
    """
    if len(schedule) == 0:
        return SummaryMetrics(
            currentPhase="moratorium",
            outstandingPrincipal=0,
            effectivePrincipal=0,
            effectiveInterestRate=0,
            nextDueDate="",
            nextInstallmentAmount=0,
            projectedEmi=0,
            projectedClosureDate="",
            interestPaidToDate=0,
            principalPaidToDate=0,
            totalInterestProjected=0,
            interestSavedTillNow=0,
            interestSavedThisYear=0,
            disbursedAmount=0,
            sanctionedAmount=data.loanDetails.sanctionedAmount,
        )

    # Parse today (L256-258)
    if today_date is not None:
        today = _parse_date_only(today_date)
    else:
        today = datetime.date.today()

    today_str = _format_date_only(today)
    current_year = today.year

    # Row classification (L259-261)
    next_row = None
    for row in schedule:
        if row.dueDate >= today_str:
            next_row = row
            break
    if next_row is None:
        next_row = schedule[-1]

    past_rows = [row for row in schedule if row.dueDate < today_str]
    this_year_rows = [
        row for row in past_rows if int(row.dueDate[:4]) == current_year
    ]

    # Computed fields (L263-268)
    disbursed_amount = sum(d.amount for d in data.disbursements)
    interest_paid_to_date = sum(row.interest for row in past_rows)
    principal_paid_to_date = sum(row.principal for row in past_rows)
    total_interest_projected = sum(row.interest for row in schedule)
    interest_saved_till_now = sum(
        row.baselineInterest - row.interest for row in past_rows
    )
    interest_saved_this_year = sum(
        row.baselineInterest - row.interest for row in this_year_rows
    )

    # Current annual rate
    sorted_rates = sorted(data.rateHistory, key=lambda r: r.effectiveDate)
    current_annual_rate = sorted_rates[-1].annualRate if sorted_rates else 0

    # Effective interest rate (L270-272)
    if next_row.openingBalance > 0:
        raw = (current_annual_rate * next_row.effectivePrincipal) / next_row.openingBalance
        effective_interest_rate = float(f"{raw:.2f}")
    else:
        effective_interest_rate = current_annual_rate

    # Projected EMI (L274-279)
    projected_emi = data.loanDetails.currentCommunicatedEmi
    if (
        data.loanDetails.policy.onPrepayment == "adjust_emi"
        and next_row.phase == "moratorium"
    ):
        projected_emi = calculate_emi(
            next_row.openingBalance,
            current_annual_rate,
            data.loanDetails.totalTenureMonths - data.loanDetails.moratoriumMonths,
        )
    elif next_row.phase == "emi":
        projected_emi = next_row.installment

    # Projected closure date (L289)
    projected_closure_date = schedule[-1].dueDate

    return SummaryMetrics(
        currentPhase=next_row.phase,
        outstandingPrincipal=next_row.openingBalance,
        effectivePrincipal=next_row.effectivePrincipal,
        effectiveInterestRate=effective_interest_rate,
        nextDueDate=next_row.dueDate,
        nextInstallmentAmount=next_row.installment,
        projectedEmi=projected_emi,
        projectedClosureDate=projected_closure_date,
        interestPaidToDate=interest_paid_to_date,
        principalPaidToDate=principal_paid_to_date,
        totalInterestProjected=total_interest_projected,
        interestSavedTillNow=interest_saved_till_now,
        interestSavedThisYear=interest_saved_this_year,
        disbursedAmount=disbursed_amount,
        sanctionedAmount=data.loanDetails.sanctionedAmount,
    )
