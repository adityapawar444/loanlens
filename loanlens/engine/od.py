from __future__ import annotations

from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from loanlens.models import ODTransaction

ZERO = Decimal("0")
TWOPLACES = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    return value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def build_daily_balance_series(
    transactions: list[ODTransaction],
    from_date: date,
    to_date: date,
) -> dict[date, Decimal]:
    if to_date < from_date:
        msg = "to_date cannot be before from_date"
        raise ValueError(msg)

    txns = sorted(transactions, key=lambda txn: txn.txn_date)
    balance_by_date: dict[date, Decimal] = {}
    current_date = from_date
    current_balance = ZERO
    txn_index = 0

    while current_date <= to_date:
        while txn_index < len(txns) and txns[txn_index].txn_date <= current_date:
            current_balance = txns[txn_index].balance_after
            txn_index += 1
        balance_by_date[current_date] = _money(current_balance)
        current_date += timedelta(days=1)

    return balance_by_date


def calculate_daily_od_interest(
    outstanding_by_date: dict[date, Decimal],
    od_balance_by_date: dict[date, Decimal],
    annual_roi: Decimal,
) -> dict[date, Decimal]:
    daily_rate = annual_roi / Decimal("365") / Decimal("100")
    interest_by_date: dict[date, Decimal] = {}
    for current_date, outstanding in outstanding_by_date.items():
        od_balance = od_balance_by_date.get(current_date, ZERO)
        effective_principal = max(outstanding - od_balance, ZERO)
        interest_by_date[current_date] = _money(effective_principal * daily_rate)
    return interest_by_date


def calculate_monthly_od_savings(
    od_balance_by_date: dict[date, Decimal],
    annual_roi: Decimal,
) -> Decimal:
    daily_rate = annual_roi / Decimal("365") / Decimal("100")
    savings = sum((balance * daily_rate for balance in od_balance_by_date.values()), start=ZERO)
    return _money(savings)


def calculate_monthly_average_balance(od_balance_by_date: dict[date, Decimal]) -> Decimal:
    if not od_balance_by_date:
        return ZERO
    total_balance = sum(od_balance_by_date.values(), start=ZERO)
    return _money(total_balance / Decimal(len(od_balance_by_date)))
