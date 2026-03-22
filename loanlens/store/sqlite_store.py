from __future__ import annotations

import json
import sqlite3
from uuid import UUID

from loanlens.config import AppConfig
from loanlens.models import (
    LoanProfile,
    Moratorium,
    ODAccount,
    ODTransaction,
    Payment,
    RateRevision,
    ScheduleRow,
    SimulationResult,
)
from loanlens.store.base import StoreBase


class SqliteStore(StoreBase):
    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._path = config.data_dir / "loanlens.db"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._path)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        cursor = self._conn.cursor()
        for table in [
            "loans",
            "schedules",
            "od_accounts",
            "od_transactions",
            "payments",
            "rate_revisions",
            "moratoriums",
            "simulations",
            "audit_log",
        ]:
            cursor.execute(
                f"CREATE TABLE IF NOT EXISTS {table} (id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
            )
        self._conn.commit()

    def _upsert(self, table: str, row_id: str, payload: str) -> None:
        self._conn.execute(
            f"INSERT INTO {table} (id, payload) VALUES (?, ?) "
            f"ON CONFLICT(id) DO UPDATE SET payload=excluded.payload",
            (row_id, payload),
        )
        self._conn.commit()

    def _get_one(self, table: str, row_id: str) -> str | None:
        row = self._conn.execute(f"SELECT payload FROM {table} WHERE id = ?", (row_id,)).fetchone()
        return None if row is None else str(row["payload"])

    def _list_all(self, table: str) -> list[str]:
        rows = self._conn.execute(f"SELECT payload FROM {table}").fetchall()
        return [str(row["payload"]) for row in rows]

    def get_loan(self, loan_id: UUID) -> LoanProfile | None:
        payload = self._get_one("loans", str(loan_id))
        return None if payload is None else LoanProfile.model_validate_json(payload)

    def save_loan(self, loan: LoanProfile) -> None:
        self._upsert("loans", str(loan.loan_id), loan.model_dump_json())

    def list_loans(self) -> list[LoanProfile]:
        return [LoanProfile.model_validate_json(item) for item in self._list_all("loans")]

    def get_schedule(self, loan_id: UUID) -> list[ScheduleRow]:
        payload = self._get_one("schedules", str(loan_id))
        if payload is None:
            return []
        raw = json.loads(payload)
        return [ScheduleRow.model_validate(item) for item in raw]

    def save_schedule(self, loan_id: UUID, rows: list[ScheduleRow]) -> None:
        payload = json.dumps([row.model_dump(mode="json") for row in rows])
        self._upsert("schedules", str(loan_id), payload)

    def get_od_account(self, loan_id: UUID) -> ODAccount | None:
        accounts = [ODAccount.model_validate_json(item) for item in self._list_all("od_accounts")]
        for account in accounts:
            if account.loan_id == loan_id:
                return account
        return None

    def save_od_account(self, account: ODAccount) -> None:
        self._upsert("od_accounts", str(account.od_account_id), account.model_dump_json())

    def list_od_transactions(self, od_account_id: UUID) -> list[ODTransaction]:
        transactions = [
            ODTransaction.model_validate_json(item) for item in self._list_all("od_transactions")
        ]
        return [item for item in transactions if item.od_account_id == od_account_id]

    def add_od_transaction(self, txn: ODTransaction) -> None:
        self._upsert("od_transactions", str(txn.txn_id), txn.model_dump_json())

    def list_payments(self, loan_id: UUID) -> list[Payment]:
        payments = [Payment.model_validate_json(item) for item in self._list_all("payments")]
        return [item for item in payments if item.loan_id == loan_id]

    def add_payment(self, payment: Payment) -> None:
        self._upsert("payments", str(payment.payment_id), payment.model_dump_json())

    def list_rate_revisions(self, loan_id: UUID) -> list[RateRevision]:
        revisions = [
            RateRevision.model_validate_json(item) for item in self._list_all("rate_revisions")
        ]
        return [item for item in revisions if item.loan_id == loan_id]

    def add_rate_revision(self, revision: RateRevision) -> None:
        self._upsert("rate_revisions", str(revision.revision_id), revision.model_dump_json())

    def list_moratoriums(self, loan_id: UUID) -> list[Moratorium]:
        moratoriums = [
            Moratorium.model_validate_json(item) for item in self._list_all("moratoriums")
        ]
        return [item for item in moratoriums if item.loan_id == loan_id]

    def add_moratorium(self, moratorium: Moratorium) -> None:
        self._upsert("moratoriums", str(moratorium.moratorium_id), moratorium.model_dump_json())

    def save_simulation(self, result: SimulationResult) -> None:
        self._upsert("simulations", str(result.simulation_id), result.model_dump_json())

    def get_simulation(self, simulation_id: UUID) -> SimulationResult | None:
        payload = self._get_one("simulations", str(simulation_id))
        return None if payload is None else SimulationResult.model_validate_json(payload)

    def list_simulations(self, loan_id: UUID) -> list[SimulationResult]:
        simulations = [
            SimulationResult.model_validate_json(item) for item in self._list_all("simulations")
        ]
        return [item for item in simulations if item.loan_id == loan_id]

    def append_audit(self, entry: dict[str, object]) -> None:
        audit_id = str(len(self._list_all("audit_log")) + 1)
        self._upsert("audit_log", audit_id, json.dumps(entry))
