from __future__ import annotations

import json
from uuid import uuid4

import pytest

from loanlens.config import AppConfig
from loanlens.store.json_store import JsonStore


def test_json_store_round_trip(tmp_path, test_loan) -> None:
    config = AppConfig(data_dir=tmp_path)
    store = JsonStore(config)
    store.save_loan(test_loan)

    loaded = store.get_loan(test_loan.loan_id)

    assert loaded is not None
    assert loaded.loan_id == test_loan.loan_id


def test_json_store_rejects_schema_mismatch(tmp_path) -> None:
    data_dir = tmp_path
    data_dir.mkdir(exist_ok=True)
    (data_dir / "backups").mkdir(exist_ok=True)
    (data_dir / "data.json").write_text(json.dumps({"version": "999.0"}), encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported schema version"):
        JsonStore(AppConfig(data_dir=data_dir))


def test_json_store_keeps_backup_limit(tmp_path, test_loan) -> None:
    config = AppConfig(data_dir=tmp_path, backup_count=2)
    store = JsonStore(config)
    for _ in range(4):
        loan = test_loan.model_copy(update={"loan_id": uuid4()})
        store.save_loan(loan)

    backups = list((tmp_path / "backups").glob("data-*.json"))
    assert len(backups) <= 2
