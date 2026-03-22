from decimal import Decimal

from loanlens.config import AppConfig
from loanlens.models import LoanProfile
from loanlens.services.loan_service import LoanService
from loanlens.services.schedule_service import ScheduleService
from loanlens.store.json_store import JsonStore


def test_loan_lifecycle(tmp_path, test_loan: LoanProfile) -> None:
    config = AppConfig(data_dir=tmp_path)
    store = JsonStore(config)
    loan_service = LoanService(store, config)
    schedule_service = ScheduleService(store, config)

    created = loan_service.create(test_loan)
    rows = schedule_service.generate(created.loan_id)
    archived = loan_service.archive(created.loan_id)

    assert created.loan_id == test_loan.loan_id
    assert len(rows) == 240
    assert rows[0].emi_amount == Decimal("44186")
    assert archived.is_archived is True
