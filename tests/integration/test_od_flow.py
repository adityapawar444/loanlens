from datetime import date
from decimal import Decimal

import pytest

from loanlens.config import AppConfig
from loanlens.models import LoanProfile
from loanlens.services.loan_service import LoanService
from loanlens.services.od_service import ODService
from loanlens.store.json_store import JsonStore


def test_od_flow(tmp_path, test_loan: LoanProfile) -> None:
    config = AppConfig(data_dir=tmp_path)
    store = JsonStore(config)
    loan_service = LoanService(store, config)
    od_service = ODService(store, config)

    loan_service.create(test_loan)
    deposit = od_service.deposit(test_loan.loan_id, Decimal("500000"), date(2024, 5, 1))
    withdrawal = od_service.withdraw(test_loan.loan_id, Decimal("100000"), date(2024, 5, 10))
    impact = od_service.impact(
        test_loan.loan_id,
        from_date=date(2024, 5, 1),
        to_date=date(2024, 5, 31),
    )

    assert deposit.balance_after == Decimal("500000")
    assert withdrawal.balance_after == Decimal("400000")
    assert impact["current_balance"] == Decimal("400000")
    assert isinstance(impact["estimated_savings"], Decimal)
    assert impact["estimated_savings"] > Decimal("0")


def test_od_flow_guards(tmp_path, test_loan: LoanProfile) -> None:
    config = AppConfig(data_dir=tmp_path)
    store = JsonStore(config)
    LoanService(store, config).create(test_loan)
    od_service = ODService(store, config)

    with pytest.raises(ValueError, match="cannot go below zero"):
        od_service.withdraw(test_loan.loan_id, Decimal("1"), date(2024, 5, 1))

    with pytest.raises(ValueError, match="cannot exceed limit"):
        od_service.deposit(test_loan.loan_id, Decimal("6000000"), date(2024, 5, 1))
