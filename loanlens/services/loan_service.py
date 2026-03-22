from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from loanlens.config import AppConfig
from loanlens.models import LoanProfile
from loanlens.store.base import StoreBase


class LoanService:
    def __init__(self, store: StoreBase, config: AppConfig) -> None:
        self._store = store
        self._config = config

    def create(self, loan: LoanProfile) -> LoanProfile:
        self._store.save_loan(loan)
        self._store.append_audit(
            {
                "timestamp": datetime.now().isoformat(),
                "command": "loan add",
                "loan_id": str(loan.loan_id),
            }
        )
        return loan

    def get(self, loan_id: UUID) -> LoanProfile | None:
        return self._store.get_loan(loan_id)

    def list(self, *, include_archived: bool = False) -> list[LoanProfile]:
        loans = self._store.list_loans()
        if include_archived:
            return loans
        return [loan for loan in loans if not loan.is_archived]

    def update(self, loan_id: UUID, updates: dict[str, Any]) -> LoanProfile:
        del self._config
        loan = self._store.get_loan(loan_id)
        if loan is None:
            msg = f"Loan {loan_id} not found"
            raise ValueError(msg)
        previous = loan.model_dump(mode="json")
        updated = loan.model_copy(update=updates)
        self._store.save_loan(updated)
        for field, new_value in updates.items():
            self._store.append_audit(
                {
                    "timestamp": datetime.now().isoformat(),
                    "command": "loan edit",
                    "loan_id": str(loan_id),
                    "field": field,
                    "old_value": previous.get(field),
                    "new_value": new_value,
                }
            )
        return updated

    def archive(self, loan_id: UUID) -> LoanProfile:
        loan = self._store.get_loan(loan_id)
        if loan is None:
            msg = f"Loan {loan_id} not found"
            raise ValueError(msg)
        archived = loan.model_copy(update={"is_archived": True})
        self._store.save_loan(archived)
        self._store.append_audit(
            {
                "timestamp": datetime.now().isoformat(),
                "command": "loan archive",
                "loan_id": str(loan_id),
                "field": "is_archived",
                "old_value": False,
                "new_value": True,
            }
        )
        return archived
