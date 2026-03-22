from loanlens.config import AppConfig, StorageBackend
from loanlens.store.sqlite_store import SqliteStore


def test_sqlite_store_round_trip(tmp_path, test_loan) -> None:
    config = AppConfig(data_dir=tmp_path, storage_backend=StorageBackend.SQLITE)
    store = SqliteStore(config)
    store.save_loan(test_loan)

    loaded = store.get_loan(test_loan.loan_id)

    assert loaded is not None
    assert loaded.loan_id == test_loan.loan_id
