"""
schedule.py — Amortization schedule generation.

Port of calculations.ts generateSchedule (L60-232).
Day-by-day interest accrual loop with exact JS parity.

CRITICAL ROUNDING: Uses math.floor(x + 0.5) everywhere to match JS Math.round().
"""

from __future__ import annotations

import datetime
import math
from typing import Optional

from .emi import _js_round, calculate_emi, calculate_tenure
from .types import AmortizationRow, LoanData


# Historical due dates where actuals came from PDF statements.
# Matches calculations.ts L4-L12.
HISTORICAL_PAYMENT_DATES: set[str] = {
    "2026-02-10",
    "2026-03-10",
    "2026-04-10",
    "2026-05-10",
    "2026-06-10",
}


def _parse_date_only(date_key: str) -> datetime.date:
    """Parse YYYY-MM-DD string to datetime.date. Matches parseDateOnly in TS."""
    year, month, day = (int(s) for s in date_key.split("-"))
    return datetime.date(year, month, day)


def _format_date_only(d: datetime.date) -> str:
    """Format datetime.date as YYYY-MM-DD with zero-padded month/day."""
    return f"{d.year:04d}-{d.month:02d}-{d.day:02d}"


def _next_month_date(current: datetime.date, due_day: int) -> datetime.date:
    """
    Advance by one calendar month, landing on the due-date day.

    Matches JS: new Date(year, month + 1, dueDateDay)
    JS Date constructor auto-adjusts overflow (e.g., Feb 31 → Mar 3),
    and Python datetime.date does NOT. But since dueDateDay is always a
    valid day (e.g. 10), this is safe for all months.
    """
    year = current.year
    month = current.month + 1
    if month > 12:
        month -= 12
        year += 1
    # JS new Date(year, month, day) with month being 0-indexed creates
    # the date. Since we're +1 on current.month, this is equivalent.
    # Handle case where due_day might exceed days in target month
    # (matching JS Date constructor overflow behavior)
    try:
        return datetime.date(year, month, due_day)
    except ValueError:
        # Day doesn't exist in that month — advance to next month day 1
        # This matches JS Date overflow (e.g., new Date(2026, 1, 31) → March 3)
        if month == 12:
            next_month_first = datetime.date(year + 1, 1, 1)
        else:
            next_month_first = datetime.date(year, month + 1, 1)
        # Compute the overflow: due_day - days_in_month
        import calendar
        days_in_month = calendar.monthrange(year, month)[1]
        overflow = due_day - days_in_month
        return datetime.date(next_month_first.year, next_month_first.month, overflow)


def generate_schedule(
    data: LoanData, today_date: Optional[str] = None
) -> list[AmortizationRow]:
    """
    Generate the full amortization schedule.

    Matches calculations.ts generateSchedule (L60-232).
    today_date is accepted but not used (same as TS — used in calculateMetrics).
    """
    loan_details = data.loanDetails
    disbursements = data.disbursements
    rate_history = data.rateHistory
    od_balance_log = data.odBalanceLog
    prepayments = data.prepayments

    schedule: list[AmortizationRow] = []

    # Sort all arrays ascending by date (matching TS L64-67)
    sorted_disbursements = sorted(disbursements, key=lambda d: d.date)
    sorted_rates = sorted(rate_history, key=lambda r: r.effectiveDate)
    sorted_od_logs = sorted(od_balance_log, key=lambda o: o.date)
    sorted_prepayments = sorted(prepayments, key=lambda p: p.date)

    if len(sorted_disbursements) == 0:
        return []

    # Initialisation (L71-81)
    anchor_date = _parse_date_only(sorted_disbursements[0].date)
    current_date = anchor_date

    outstanding_principal: float = 0
    period = 1
    phase: str = "moratorium"
    current_emi: float = loan_details.currentCommunicatedEmi or 0
    remaining_tenure: int | float = loan_details.totalTenureMonths

    d_idx = 0  # disbursement index
    p_idx = 0  # prepayment index

    # Step functions (closures matching TS L83-100)
    def get_rate_at(date_key: str) -> float:
        if len(sorted_rates) == 0:
            return 0
        rate = sorted_rates[0].annualRate
        for entry in sorted_rates:
            if entry.effectiveDate <= date_key:
                rate = entry.annualRate
            else:
                break
        return rate

    def get_od_balance_at(date_key: str) -> float:
        balance = 0.0
        for entry in sorted_od_logs:
            if entry.date <= date_key:
                balance = entry.balance
            else:
                break
        return balance

    # Main loop (L102-230)
    while outstanding_principal > 0.01 or d_idx < len(sorted_disbursements):
        next_due_date = _next_month_date(current_date, loan_details.dueDateDay)
        date_key = _format_date_only(next_due_date)

        # Daily interest accrual loop (L106-132)
        interest_accrued: float = 0.0
        baseline_interest_accrued: float = 0.0
        temp_date = current_date

        while temp_date < next_due_date:
            temp_date_key = _format_date_only(temp_date)

            # Apply disbursements falling on this day (L113-116)
            while (
                d_idx < len(sorted_disbursements)
                and sorted_disbursements[d_idx].date == temp_date_key
            ):
                outstanding_principal += sorted_disbursements[d_idx].amount
                d_idx += 1

            # Apply prepayments falling on this day (L117-120)
            while (
                p_idx < len(sorted_prepayments)
                and sorted_prepayments[p_idx].date == temp_date_key
            ):
                outstanding_principal -= sorted_prepayments[p_idx].amount
                p_idx += 1

            # Daily rate and OD offset (L122-129)
            daily_rate = get_rate_at(temp_date_key) / 100 / loan_details.dayCountConvention
            od_balance = get_od_balance_at(temp_date_key)
            effective_principal = max(0.0, outstanding_principal - od_balance)

            interest_accrued += effective_principal * daily_rate
            baseline_interest_accrued += outstanding_principal * daily_rate

            temp_date = temp_date + datetime.timedelta(days=1)

        # Moratorium → EMI transition (L134-143)
        if phase == "moratorium" and period > loan_details.moratoriumMonths:
            phase = "emi"
            current_emi = loan_details.currentCommunicatedEmi
            if loan_details.policy.onPrepayment == "adjust_tenure":
                remaining_tenure = calculate_tenure(
                    outstanding_principal, get_rate_at(date_key), current_emi
                )
            else:
                remaining_tenure = (
                    loan_details.totalTenureMonths - loan_details.moratoriumMonths
                )
                current_emi = calculate_emi(
                    outstanding_principal, get_rate_at(date_key), remaining_tenure
                )

        # Payment processing (L145-200)
        installment: float = 0
        principal_paid: float = 0
        interest_paid: float = _js_round(interest_accrued)
        baseline_interest: float = _js_round(baseline_interest_accrued)
        interest_savings: float = max(0, baseline_interest - interest_paid)

        if date_key in HISTORICAL_PAYMENT_DATES:
            # Historical statement months (L153-168)
            logged_payment = next(
                (p for p in data.paymentLog if p.dueDate == date_key), None
            )
            if logged_payment is not None:
                interest_paid = logged_payment.amountPaid
                baseline_interest = (
                    logged_payment.amountDue
                    if logged_payment.amountDue > 0
                    else interest_paid
                )
                interest_savings = max(0, baseline_interest - interest_paid)
                installment = interest_paid
                principal_paid = 0
            else:
                interest_savings = 0
                installment = interest_paid
                principal_paid = 0
        else:
            # Non-historical payment logic (L169-199)
            logged_payment = next(
                (p for p in data.paymentLog if p.dueDate == date_key), None
            )
            if logged_payment is not None:
                interest_paid = logged_payment.amountPaid
                interest_savings = max(0, baseline_interest - interest_paid)
                if phase == "moratorium":
                    installment = interest_paid
                    principal_paid = 0
                else:
                    installment = logged_payment.amountPaid
                    principal_paid = max(0, installment - interest_paid)
                    outstanding_principal = max(
                        0, outstanding_principal - principal_paid
                    )
            else:
                if phase == "moratorium":
                    installment = interest_paid
                    principal_paid = 0
                else:
                    # Repayment phase (L187-198)
                    installment = current_emi or loan_details.currentCommunicatedEmi

                    if outstanding_principal + interest_paid <= installment:
                        # Final period — loan closes
                        installment = _js_round(outstanding_principal + interest_paid)
                        principal_paid = outstanding_principal
                        outstanding_principal = 0
                    else:
                        principal_paid = installment - interest_paid
                        outstanding_principal = max(
                            0, outstanding_principal - principal_paid
                        )

        # Prepayment policy application (L202-208)
        if phase == "emi":
            if loan_details.policy.onPrepayment == "adjust_tenure":
                remaining_tenure = calculate_tenure(
                    outstanding_principal, get_rate_at(date_key), current_emi
                )
            else:
                remaining_tenure -= 1

        # Row construction (L210-222)
        opening_balance = _js_round(
            outstanding_principal + (principal_paid if phase == "emi" else 0)
        )
        closing_balance = _js_round(outstanding_principal)

        schedule.append(
            AmortizationRow(
                period=period,
                dueDate=date_key,
                openingBalance=opening_balance,
                installment=installment,
                interest=interest_paid,
                baselineInterest=baseline_interest,
                interestSavings=interest_savings,
                principal=principal_paid,
                closingBalance=closing_balance,
                phase=phase,
                effectivePrincipal=max(
                    0, outstanding_principal - get_od_balance_at(date_key)
                ),
            )
        )

        # Termination conditions (L224-226)
        if outstanding_principal <= 0.01 and d_idx >= len(sorted_disbursements):
            break
        if period > 600:
            break  # Safety break

        current_date = next_due_date
        period += 1

    return schedule
