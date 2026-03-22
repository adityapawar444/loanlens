from __future__ import annotations

from decimal import Decimal
from typing import TypedDict
from uuid import UUID

from loanlens.config import AppConfig
from loanlens.models import LoanProfile, ScheduleRow
from loanlens.store.base import StoreBase


class InterestCertificate(TypedDict):
    loan: LoanProfile
    financial_year: str
    rows: list[ScheduleRow]
    total_interest: Decimal


class CertService:
    def __init__(self, store: StoreBase, config: AppConfig) -> None:
        self._store = store
        self._config = config

    def interest_certificate(
        self,
        loan_id: UUID,
        financial_year: str,
    ) -> InterestCertificate:
        del self._config
        loan = self._store.get_loan(loan_id)
        if loan is None:
            msg = f"Loan {loan_id} not found"
            raise ValueError(msg)
        schedule = self._store.get_schedule(loan_id)
        if not schedule:
            msg = f"Schedule for loan {loan_id} not found"
            raise ValueError(msg)
        start_year = int(financial_year.split("-")[0])
        rows = [
            row
            for row in schedule
            if (row.due_date.year == start_year and row.due_date.month >= 4)
            or (row.due_date.year == start_year + 1 and row.due_date.month <= 3)
        ]
        total_interest = sum((row.interest_component for row in rows), start=Decimal("0"))
        return {
            "loan": loan,
            "financial_year": financial_year,
            "rows": rows,
            "total_interest": total_interest,
        }
