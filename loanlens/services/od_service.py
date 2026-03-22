from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from loanlens.config import AppConfig
from loanlens.engine.moratorium import calculate_moratorium_impact
from loanlens.engine.od import (
    build_daily_balance_series,
    calculate_monthly_average_balance,
    calculate_monthly_od_savings,
)
from loanlens.models import MoratoriumImpact, ODAccount, ODTransaction
from loanlens.store.base import StoreBase


class ODService:
    def __init__(self, store: StoreBase, config: AppConfig) -> None:
        self._store = store
        self._config = config

    def _get_or_create_account(self, loan_id: UUID) -> ODAccount:
        account = self._store.get_od_account(loan_id)
        if account is not None:
            return account
        loan = self._store.get_loan(loan_id)
        if loan is None:
            msg = f"Loan {loan_id} not found"
            raise ValueError(msg)
        account = ODAccount(
            loan_id=loan_id,
            limit=loan.disbursed_amount,
            balance_mode=self._config.od_balance_mode,
        )
        self._store.save_od_account(account)
        return account

    def deposit(
        self,
        loan_id: UUID,
        amount: Decimal,
        txn_date: date,
        notes: str = "",
    ) -> ODTransaction:
        if amount <= Decimal("0"):
            msg = "deposit amount must be greater than zero"
            raise ValueError(msg)
        account = self._get_or_create_account(loan_id)
        new_balance = account.current_balance + amount
        if new_balance > account.limit:
            msg = "OD balance cannot exceed limit"
            raise ValueError(msg)
        updated_account = account.model_copy(update={"current_balance": new_balance})
        self._store.save_od_account(updated_account)
        txn = ODTransaction(
            od_account_id=account.od_account_id,
            loan_id=loan_id,
            txn_type="DEPOSIT",
            amount=amount,
            txn_date=txn_date,
            balance_after=new_balance,
            notes=notes,
        )
        self._store.add_od_transaction(txn)
        return txn

    def withdraw(
        self,
        loan_id: UUID,
        amount: Decimal,
        txn_date: date,
        notes: str = "",
    ) -> ODTransaction:
        if amount <= Decimal("0"):
            msg = "withdrawal amount must be greater than zero"
            raise ValueError(msg)
        account = self._get_or_create_account(loan_id)
        new_balance = account.current_balance - amount
        if new_balance < Decimal("0"):
            msg = "OD balance cannot go below zero"
            raise ValueError(msg)
        updated_account = account.model_copy(update={"current_balance": new_balance})
        self._store.save_od_account(updated_account)
        txn = ODTransaction(
            od_account_id=account.od_account_id,
            loan_id=loan_id,
            txn_type="WITHDRAWAL",
            amount=amount,
            txn_date=txn_date,
            balance_after=new_balance,
            notes=notes,
        )
        self._store.add_od_transaction(txn)
        return txn

    def balance(self, loan_id: UUID) -> ODAccount:
        return self._get_or_create_account(loan_id)

    def history(self, loan_id: UUID) -> list[ODTransaction]:
        account = self._get_or_create_account(loan_id)
        return self._store.list_od_transactions(account.od_account_id)

    def impact(
        self,
        loan_id: UUID,
        balance: Decimal | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> dict[str, Decimal | str]:
        loan = self._store.get_loan(loan_id)
        if loan is None:
            msg = f"Loan {loan_id} not found"
            raise ValueError(msg)
        account = self._get_or_create_account(loan_id)
        transactions = self._store.list_od_transactions(account.od_account_id)
        if balance is not None:
            transactions = [
                ODTransaction(
                    od_account_id=account.od_account_id,
                    loan_id=loan_id,
                    txn_type="DEPOSIT",
                    amount=balance,
                    txn_date=from_date or date.today(),
                    balance_after=balance,
                )
            ]

        start = from_date or loan.emi_start_date
        end = to_date or date.today()
        series = build_daily_balance_series(transactions, start, end)
        average_balance = calculate_monthly_average_balance(series)
        savings = calculate_monthly_od_savings(series, loan.roi_initial)
        return {
            "balance_mode": account.balance_mode.value,
            "current_balance": account.current_balance,
            "average_balance": average_balance,
            "estimated_savings": savings,
        }

    def moratorium_impact(self, loan_id: UUID, moratorium_id: UUID) -> MoratoriumImpact:
        loan = self._store.get_loan(loan_id)
        if loan is None:
            msg = f"Loan {loan_id} not found"
            raise ValueError(msg)
        moratorium = next(
            (
                item
                for item in self._store.list_moratoriums(loan_id)
                if item.moratorium_id == moratorium_id
            ),
            None,
        )
        if moratorium is None:
            msg = f"Moratorium {moratorium_id} not found"
            raise ValueError(msg)
        return calculate_moratorium_impact(loan, moratorium)
