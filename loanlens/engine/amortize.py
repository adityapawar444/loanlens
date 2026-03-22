from __future__ import annotations

from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal

from loanlens.models import AnnualSummary, ScheduleRow, TotalCost

TWOPLACES = Decimal("0.01")
ZERO = Decimal("0")


def _money(value: Decimal) -> Decimal:
    return value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def _financial_year_label(year: int, month: int) -> str:
    start_year = year if month >= 4 else year - 1
    end_year = (start_year + 1) % 100
    return f"{start_year}-{end_year:02d}"


def annual_summary(schedule: list[ScheduleRow]) -> list[AnnualSummary]:
    grouped: dict[str, list[ScheduleRow]] = defaultdict(list)
    for row in schedule:
        grouped[_financial_year_label(row.due_date.year, row.due_date.month)].append(row)

    summaries: list[AnnualSummary] = []
    for financial_year in sorted(grouped):
        rows = grouped[financial_year]
        interest_paid = _money(sum((row.interest_component for row in rows), start=ZERO))
        principal_repaid = _money(
            sum((row.principal_component + row.prepayment_amount for row in rows), start=ZERO)
        )
        closing_balance = rows[-1].closing_principal
        summaries.append(
            AnnualSummary(
                financial_year=financial_year,
                interest_paid=interest_paid,
                principal_repaid=principal_repaid,
                closing_balance=closing_balance,
            )
        )
    return summaries


def crossover_point(schedule: list[ScheduleRow]) -> int:
    for row in schedule:
        if row.cumulative_principal > row.cumulative_interest:
            return row.instalment_number
    return 0


def total_cost(schedule: list[ScheduleRow]) -> TotalCost:
    if not schedule:
        return TotalCost(principal=ZERO, interest=ZERO, total=ZERO)
    principal = _money(
        sum(
            (row.principal_component + row.prepayment_amount for row in schedule),
            start=ZERO,
        )
    )
    interest = _money(sum((row.interest_component for row in schedule), start=ZERO))
    total = _money(principal + interest)
    return TotalCost(principal=principal, interest=interest, total=total)
