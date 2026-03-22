from __future__ import annotations

from uuid import UUID

import pandas as pd  # type: ignore[import-untyped]

from loanlens.config import AppConfig
from loanlens.engine.schedule import generate_schedule
from loanlens.models import ScheduleRow
from loanlens.store.base import StoreBase


class ScheduleService:
    def __init__(self, store: StoreBase, config: AppConfig) -> None:
        self._store = store
        self._config = config

    def generate(self, loan_id: UUID) -> list[ScheduleRow]:
        loan = self._store.get_loan(loan_id)
        if loan is None:
            msg = f"Loan {loan_id} not found"
            raise ValueError(msg)
        od_account = self._store.get_od_account(loan_id)
        od_transactions = []
        if od_account is not None:
            od_transactions = self._store.list_od_transactions(od_account.od_account_id)
        rows = generate_schedule(
            loan=loan,
            rate_revisions=self._store.list_rate_revisions(loan_id),
            moratoriums=self._store.list_moratoriums(loan_id),
            payments=self._store.list_payments(loan_id),
            od_transactions=od_transactions,
            config=self._config,
        )
        self._store.save_schedule(loan_id, rows)
        return rows

    def get(self, loan_id: UUID) -> list[ScheduleRow]:
        return self._store.get_schedule(loan_id)

    def mark_stale(self, loan_id: UUID, reason: str) -> None:
        self._store.append_audit(
            {
                "command": "schedule stale",
                "loan_id": str(loan_id),
                "field": "schedule",
                "new_value": "STALE",
                "old_value": None,
                "reason": reason,
            }
        )

    def export_to_dataframe(self, loan_id: UUID) -> pd.DataFrame:
        rows = self._store.get_schedule(loan_id)
        return pd.DataFrame([row.model_dump(mode="json") for row in rows])
