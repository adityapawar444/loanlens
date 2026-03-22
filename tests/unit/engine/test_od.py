from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from loanlens.engine.od import (
    build_daily_balance_series,
    calculate_daily_od_interest,
    calculate_monthly_average_balance,
    calculate_monthly_od_savings,
)
from loanlens.models import ODTransaction


def _txn(day: int, amount: str, balance_after: str, txn_type: str = "DEPOSIT") -> ODTransaction:
    loan_id = uuid4()
    od_account_id = uuid4()
    return ODTransaction(
        od_account_id=od_account_id,
        loan_id=loan_id,
        txn_type=txn_type,
        amount=Decimal(amount),
        txn_date=date(2024, 4, day),
        balance_after=Decimal(balance_after),
    )


def test_build_daily_balance_series_step_function() -> None:
    series = build_daily_balance_series(
        [_txn(2, "100000", "100000"), _txn(5, "50000", "150000")],
        date(2024, 4, 1),
        date(2024, 4, 6),
    )

    assert series[date(2024, 4, 1)] == Decimal("0.00")
    assert series[date(2024, 4, 3)] == Decimal("100000.00")
    assert series[date(2024, 4, 6)] == Decimal("150000.00")


def test_calculate_daily_od_interest_known_balances() -> None:
    outstanding = {
        date(2024, 4, 1): Decimal("1000000"),
        date(2024, 4, 2): Decimal("1000000"),
    }
    od_balances = {
        date(2024, 4, 1): Decimal("100000"),
        date(2024, 4, 2): Decimal("200000"),
    }

    interest = calculate_daily_od_interest(outstanding, od_balances, Decimal("12"))

    assert interest[date(2024, 4, 1)] == Decimal("295.89")
    assert interest[date(2024, 4, 2)] == Decimal("263.01")


def test_calculate_monthly_savings_and_average_balance() -> None:
    balances = {
        date(2024, 4, 1): Decimal("100000"),
        date(2024, 4, 2): Decimal("200000"),
        date(2024, 4, 3): Decimal("300000"),
    }

    assert calculate_monthly_od_savings(balances, Decimal("12")) == Decimal("197.26")
    assert calculate_monthly_average_balance(balances) == Decimal("200000.00")


def test_build_daily_balance_series_rejects_invalid_range() -> None:
    with pytest.raises(ValueError):
        build_daily_balance_series([], date(2024, 4, 2), date(2024, 4, 1))
