from __future__ import annotations

import calendar
from collections import defaultdict
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal, cast

from dateutil.relativedelta import relativedelta  # type: ignore[import-untyped]

from loanlens.config import AppConfig
from loanlens.engine.emi import calculate_emi, calculate_monthly_rate
from loanlens.models import (
    AdjustmentMode,
    LoanProfile,
    Moratorium,
    MoratoriumType,
    ODTransaction,
    Payment,
    RateRevision,
    ScheduleRow,
    ScheduleStatus,
)

TWOPLACES = Decimal("0.01")
ZERO = Decimal("0")


def _money(value: Decimal) -> Decimal:
    return value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def _due_date_for_offset(start_date: date, emi_day: int, offset: int) -> date:
    current = start_date + relativedelta(months=offset)
    month_last_day = calendar.monthrange(current.year, current.month)[1]
    return cast(date, current.replace(day=min(emi_day, month_last_day)))


def _payment_maps(
    payments: list[Payment],
) -> tuple[dict[date, list[Payment]], dict[int, list[Payment]]]:
    by_date: dict[date, list[Payment]] = defaultdict(list)
    by_instalment: dict[int, list[Payment]] = defaultdict(list)
    for payment in payments:
        by_date[payment.payment_date].append(payment)
        if payment.instalment_number is not None:
            by_instalment[payment.instalment_number].append(payment)
    return by_date, by_instalment


def _revision_for_date(
    revisions_by_date: dict[date, list[RateRevision]],
    due_date: date,
) -> list[RateRevision]:
    return revisions_by_date.get(due_date, [])


def _moratorium_for_date(
    moratoriums: list[Moratorium],
    due_date: date,
) -> Moratorium | None:
    for moratorium in moratoriums:
        if moratorium.from_date <= due_date <= moratorium.to_date:
            return moratorium
    return None


def _monthly_od_saving(
    opening_principal: Decimal,
    due_date: date,
    annual_roi: Decimal,
    od_transactions: list[ODTransaction],
) -> Decimal:
    if not od_transactions:
        return ZERO
    month_transactions = [
        txn
        for txn in od_transactions
        if txn.txn_date.year == due_date.year and txn.txn_date.month == due_date.month
    ]
    if not month_transactions:
        return ZERO
    last_balance = max((txn.balance_after for txn in month_transactions), default=ZERO)
    days = calendar.monthrange(due_date.year, due_date.month)[1]
    monthly_rate = annual_roi / Decimal("365") / Decimal("100")
    effective_balance = min(last_balance, opening_principal)
    return _money(effective_balance * monthly_rate * Decimal(days))


def _status_for_row(
    due_date: date,
    moratorium: Moratorium | None,
    emi_payments: list[Payment],
    prepayment_amount: Decimal,
) -> ScheduleStatus:
    if moratorium is not None:
        return ScheduleStatus.MORATORIUM
    if prepayment_amount > ZERO:
        return ScheduleStatus.PREPAID
    if emi_payments:
        return ScheduleStatus.PAID
    if due_date < date.today():
        return ScheduleStatus.OVERDUE
    return ScheduleStatus.UPCOMING


def _apply_adjustment_mode(
    adjustment_mode: AdjustmentMode,
    opening_principal: Decimal,
    annual_roi: Decimal,
    remaining_months: int,
    current_emi: Decimal,
    rounding: Literal["rupee", "ten"],
) -> tuple[Decimal, int]:
    if remaining_months <= 0:
        return current_emi, 0
    if adjustment_mode == AdjustmentMode.ADJUST_EMI:
        revised_emi = calculate_emi(opening_principal, annual_roi, remaining_months, rounding)
        return revised_emi, remaining_months

    monthly_rate = calculate_monthly_rate(annual_roi)
    if monthly_rate == ZERO:
        revised_months = int(
            (opening_principal / current_emi).to_integral_value(rounding=ROUND_HALF_UP)
        )
        return current_emi, max(revised_months, 1)

    balance = opening_principal
    months = 0
    while balance > ZERO and months < 1200:
        interest = _money(balance * monthly_rate)
        principal_component = current_emi - interest
        if principal_component <= ZERO:
            msg = "Current EMI is insufficient to amortize the loan"
            raise ValueError(msg)
        if principal_component >= balance:
            months += 1
            break
        balance = _money(balance - principal_component)
        months += 1
    return current_emi, months


def generate_schedule(
    loan: LoanProfile,
    rate_revisions: list[RateRevision],
    moratoriums: list[Moratorium],
    payments: list[Payment],
    od_transactions: list[ODTransaction],
    config: AppConfig,
) -> list[ScheduleRow]:
    del config
    monthly_rate = calculate_monthly_rate(loan.roi_initial)
    current_roi = loan.roi_initial
    rounding = loan.emi_rounding
    current_emi = calculate_emi(loan.disbursed_amount, current_roi, loan.tenure_months, rounding)
    remaining_months = loan.tenure_months
    principal = _money(loan.disbursed_amount)
    cumulative_interest = ZERO
    cumulative_principal = ZERO
    rows: list[ScheduleRow] = []

    revisions_by_date: dict[date, list[RateRevision]] = defaultdict(list)
    for revision in sorted(rate_revisions, key=lambda item: item.effective_date):
        revisions_by_date[revision.effective_date].append(revision)
    moratoriums_sorted = sorted(moratoriums, key=lambda item: item.from_date)
    payments_by_date, payments_by_instalment = _payment_maps(payments)

    instalment_number = 1
    offset = 0
    safety_counter = 0
    while principal > ZERO and remaining_months > 0:
        due_date = _due_date_for_offset(loan.emi_start_date, loan.emi_day, offset)
        for revision in _revision_for_date(revisions_by_date, due_date):
            current_roi = revision.new_roi
            adjustment_mode = revision.adjustment_mode
            current_emi, remaining_months = _apply_adjustment_mode(
                adjustment_mode,
                principal,
                current_roi,
                remaining_months,
                current_emi,
                rounding,
            )
            monthly_rate = calculate_monthly_rate(current_roi)

        moratorium = _moratorium_for_date(moratoriums_sorted, due_date)
        opening_principal = principal
        interest_component = _money(opening_principal * monthly_rate)
        principal_component = ZERO
        prepayment_amount = ZERO
        emi_amount = current_emi
        closing_principal = opening_principal

        if moratorium is not None:
            emi_amount = ZERO
            if moratorium.moratorium_type in {
                MoratoriumType.INTEREST_CAPITALISE,
                MoratoriumType.FULL_DEFER,
            }:
                closing_principal = _money(opening_principal + interest_component)
            elif moratorium.moratorium_type == MoratoriumType.INTEREST_DEFER:
                closing_principal = opening_principal
        else:
            emi_payments = payments_by_instalment.get(instalment_number, []) + payments_by_date.get(
                due_date,
                [],
            )
            regular_emi_paid = [
                payment
                for payment in emi_payments
                if payment.payment_type in {"EMI", "INTEREST_ONLY"}
            ]
            prepayments_this_month = [
                payment for payment in payments_by_date.get(due_date, [])
                if payment.payment_type == "PREPAYMENT"
            ]

            if remaining_months == 1:
                emi_amount = _money(opening_principal + interest_component)
            principal_component = _money(emi_amount - interest_component)
            if principal_component > opening_principal:
                principal_component = opening_principal
                emi_amount = _money(principal_component + interest_component)

            prepayment_amount = _money(
                sum((payment.amount for payment in prepayments_this_month), start=ZERO)
            )
            closing_principal = _money(opening_principal - principal_component - prepayment_amount)
            if closing_principal < ZERO:
                prepayment_amount = _money(prepayment_amount + closing_principal)
                closing_principal = ZERO

            if prepayment_amount > ZERO and closing_principal > ZERO:
                current_emi, remaining_months = _apply_adjustment_mode(
                    loan.adjustment_mode,
                    closing_principal,
                    current_roi,
                    remaining_months - 1,
                    current_emi,
                    rounding,
                )
            else:
                remaining_months -= 1

            status = _status_for_row(due_date, None, regular_emi_paid, prepayment_amount)
            od_interest_saved = _monthly_od_saving(
                opening_principal,
                due_date,
                current_roi,
                od_transactions,
            )
            cumulative_interest = _money(
                cumulative_interest + interest_component - od_interest_saved
            )
            cumulative_principal = _money(
                cumulative_principal + principal_component + prepayment_amount
            )
            principal = closing_principal
            rows.append(
                ScheduleRow(
                    loan_id=loan.loan_id,
                    instalment_number=instalment_number,
                    due_date=due_date,
                    opening_principal=opening_principal,
                    emi_amount=emi_amount,
                    interest_component=interest_component,
                    principal_component=principal_component,
                    prepayment_amount=prepayment_amount,
                    closing_principal=closing_principal,
                    cumulative_interest=cumulative_interest,
                    cumulative_principal=cumulative_principal,
                    od_interest_saved=od_interest_saved,
                    status=status,
                )
            )
            instalment_number += 1
            offset += 1
            safety_counter += 1
            if safety_counter > 1200:
                msg = "Schedule generation exceeded safety limit"
                raise ValueError(msg)
            continue

        od_interest_saved = ZERO
        cumulative_interest = _money(cumulative_interest + interest_component)
        principal = closing_principal
        rows.append(
            ScheduleRow(
                loan_id=loan.loan_id,
                instalment_number=instalment_number,
                due_date=due_date,
                opening_principal=opening_principal,
                emi_amount=emi_amount,
                interest_component=interest_component,
                principal_component=principal_component,
                prepayment_amount=prepayment_amount,
                closing_principal=closing_principal,
                cumulative_interest=cumulative_interest,
                cumulative_principal=cumulative_principal,
                od_interest_saved=od_interest_saved,
                status=ScheduleStatus.MORATORIUM,
            )
        )
        remaining_months += 1
        instalment_number += 1
        offset += 1
        safety_counter += 1
        if safety_counter > 1200:
            msg = "Schedule generation exceeded safety limit"
            raise ValueError(msg)

    return rows
