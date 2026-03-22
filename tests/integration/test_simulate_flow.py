from datetime import date
from decimal import Decimal

from loanlens.config import AppConfig
from loanlens.models import LoanProfile
from loanlens.services.loan_service import LoanService
from loanlens.services.simulate_service import SimulateService
from loanlens.store.json_store import JsonStore


def test_simulate_flow(tmp_path, test_loan: LoanProfile) -> None:
    config = AppConfig(data_dir=tmp_path)
    store = JsonStore(config)
    LoanService(store, config).create(test_loan)
    service = SimulateService(store, config)

    prepay = service.prepay(
        test_loan.loan_id,
        Decimal("200000"),
        date(2024, 10, 5),
        "REDUCE_TENURE",
        False,
    )
    compare = service.compare(
        test_loan.loan_id,
        Decimal("200000"),
        date(2024, 10, 5),
        "REDUCE_TENURE",
        Decimal("8"),
    )
    recurring = service.recurring(
        test_loan.loan_id,
        Decimal("5000"),
        date(2024, 6, 5),
        "REDUCE_TENURE",
    )
    saved = service.save(
        test_loan.loan_id,
        "PREPAYMENT",
        {"amount": "200000", "date": "2024-10-05"},
        prepay,
        "October prepay",
    )
    recalled = service.get(saved.simulation_id)

    assert prepay.months_saved > 0
    assert compare.investment_value > Decimal("200000")
    assert recurring.months_saved > 0
    assert recalled is not None
    assert recalled.label == "October prepay"
