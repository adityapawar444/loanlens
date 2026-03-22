from pathlib import Path

from typer.testing import CliRunner

from loanlens.app import app
from loanlens.config import AppConfig
from loanlens.store.json_store import JsonStore


def test_cli_help_smoke() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0


def test_loan_add_can_optionally_create_moratorium(tmp_path: Path) -> None:
    runner = CliRunner()
    env = {"LOANLENS_DATA_DIR": str(tmp_path)}
    result = runner.invoke(
        app,
        [
            "--yes",
            "loan",
            "add",
            "--name",
            "Test Loan",
            "--bank-name",
            "SBI",
            "--account-number",
            "12345",
            "--sanction-amount",
            "5000000",
            "--disbursed-amount",
            "5000000",
            "--disbursement-date",
            "2024-04-01",
            "--roi-initial",
            "8.75",
            "--roi-type",
            "FLOATING",
            "--tenure-months",
            "240",
            "--emi-start-date",
            "2024-05-01",
            "--emi-day",
            "5",
            "--adjustment-mode",
            "ADJUST_EMI",
            "--prepayment-charges-pct",
            "0",
            "--emi-rounding",
            "rupee",
            "--moratorium",
            "--moratorium-from",
            "2024-07-05",
            "--moratorium-to",
            "2024-08-05",
            "--moratorium-type",
            "INTEREST_CAPITALISE",
        ],
        env=env,
    )

    assert result.exit_code == 0
    store = JsonStore(AppConfig(data_dir=tmp_path))
    loans = store.list_loans()
    assert len(loans) == 1
    moratoriums = store.list_moratoriums(loans[0].loan_id)
    assert len(moratoriums) == 1
