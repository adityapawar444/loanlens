from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

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

SCHEMA_VERSION = "1.0"


class JsonStoreData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    version: str = SCHEMA_VERSION
    loans: dict[str, LoanProfile] = Field(default_factory=dict)
    od_accounts: dict[str, ODAccount] = Field(default_factory=dict)
    od_transactions: list[ODTransaction] = Field(default_factory=list)
    schedules: dict[str, list[ScheduleRow]] = Field(default_factory=dict)
    payments: list[Payment] = Field(default_factory=list)
    rate_revisions: list[RateRevision] = Field(default_factory=list)
    moratoriums: list[Moratorium] = Field(default_factory=list)
    simulations: dict[str, SimulationResult] = Field(default_factory=dict)
    audit_log: list[dict[str, object]] = Field(default_factory=list)


class JsonStore(StoreBase):
    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._path = config.data_file
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._config.backup_dir.mkdir(parents=True, exist_ok=True)
        self._data = self._load()

    def _load(self) -> JsonStoreData:
        if not self._path.exists():
            data = JsonStoreData()
            self._write_data(data, backup=False)
            return data

        payload = json.loads(self._path.read_text(encoding="utf-8"))
        version = payload.get("version")
        if version != SCHEMA_VERSION:
            msg = f"Unsupported schema version: {version!r}. Expected {SCHEMA_VERSION!r}."
            raise ValueError(msg)
        return JsonStoreData.model_validate(payload)

    def _rotate_backups(self) -> None:
        backups = sorted(self._config.backup_dir.glob("data-*.json"))
        while len(backups) > self._config.backup_count:
            oldest = backups.pop(0)
            oldest.unlink(missing_ok=True)

    def _backup_current(self) -> None:
        if not self._path.exists():
            return
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        backup_path = self._config.backup_dir / f"data-{timestamp}.json"
        shutil.copy2(self._path, backup_path)
        self._rotate_backups()

    def _write_data(self, data: JsonStoreData, *, backup: bool = True) -> None:
        if backup:
            self._backup_current()
        with NamedTemporaryFile("w", encoding="utf-8", dir=self._path.parent, delete=False) as tmp:
            tmp.write(data.model_dump_json(indent=2))
            temp_path = Path(tmp.name)
        temp_path.replace(self._path)

    def _persist(self) -> None:
        self._write_data(self._data)

    def get_loan(self, loan_id: UUID) -> LoanProfile | None:
        return self._data.loans.get(str(loan_id))

    def save_loan(self, loan: LoanProfile) -> None:
        self._data.loans[str(loan.loan_id)] = loan
        self._persist()

    def list_loans(self) -> list[LoanProfile]:
        return list(self._data.loans.values())

    def get_schedule(self, loan_id: UUID) -> list[ScheduleRow]:
        return list(self._data.schedules.get(str(loan_id), []))

    def save_schedule(self, loan_id: UUID, rows: list[ScheduleRow]) -> None:
        self._data.schedules[str(loan_id)] = rows
        self._persist()

    def get_od_account(self, loan_id: UUID) -> ODAccount | None:
        for account in self._data.od_accounts.values():
            if account.loan_id == loan_id:
                return account
        return None

    def save_od_account(self, account: ODAccount) -> None:
        self._data.od_accounts[str(account.od_account_id)] = account
        self._persist()

    def list_od_transactions(self, od_account_id: UUID) -> list[ODTransaction]:
        return [txn for txn in self._data.od_transactions if txn.od_account_id == od_account_id]

    def add_od_transaction(self, txn: ODTransaction) -> None:
        self._data.od_transactions.append(txn)
        self._persist()

    def list_payments(self, loan_id: UUID) -> list[Payment]:
        return [payment for payment in self._data.payments if payment.loan_id == loan_id]

    def add_payment(self, payment: Payment) -> None:
        self._data.payments.append(payment)
        self._persist()

    def list_rate_revisions(self, loan_id: UUID) -> list[RateRevision]:
        return [revision for revision in self._data.rate_revisions if revision.loan_id == loan_id]

    def add_rate_revision(self, revision: RateRevision) -> None:
        self._data.rate_revisions.append(revision)
        self._persist()

    def list_moratoriums(self, loan_id: UUID) -> list[Moratorium]:
        return [
            moratorium
            for moratorium in self._data.moratoriums
            if moratorium.loan_id == loan_id
        ]

    def add_moratorium(self, moratorium: Moratorium) -> None:
        self._data.moratoriums.append(moratorium)
        self._persist()

    def save_simulation(self, result: SimulationResult) -> None:
        self._data.simulations[str(result.simulation_id)] = result
        self._persist()

    def get_simulation(self, simulation_id: UUID) -> SimulationResult | None:
        return self._data.simulations.get(str(simulation_id))

    def list_simulations(self, loan_id: UUID) -> list[SimulationResult]:
        return [result for result in self._data.simulations.values() if result.loan_id == loan_id]

    def append_audit(self, entry: dict[str, object]) -> None:
        self._data.audit_log.append(entry)
        self._persist()
