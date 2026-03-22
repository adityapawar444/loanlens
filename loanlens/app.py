from __future__ import annotations

import typer

from loanlens.cli import (
    amortize,
    backup,
    cert,
    dashboard,
    emi,
    export,
    loan,
    moratorium,
    od,
    payment,
    rate,
    schedule,
    simulate,
    wizard,
)
from loanlens.cli import config as config_cli
from loanlens.config import StorageBackend, load_config, save_config
from loanlens.store.json_store import JsonStore
from loanlens.store.sqlite_store import SqliteStore

app = typer.Typer(help="LoanLens home loan management CLI.")

app.add_typer(wizard.app, name="wizard")
app.add_typer(loan.app, name="loan")
app.add_typer(emi.app, name="emi")
app.add_typer(schedule.app, name="schedule")
app.add_typer(amortize.app, name="amortize")
app.add_typer(moratorium.app, name="moratorium")
app.add_typer(od.app, name="od")
app.add_typer(rate.app, name="rate")
app.add_typer(simulate.app, name="simulate")
app.add_typer(payment.app, name="payment")
app.add_typer(dashboard.app, name="dashboard")
app.add_typer(cert.app, name="cert")
app.add_typer(config_cli.app, name="config")
app.add_typer(backup.app, name="backup")
app.add_typer(export.app, name="export")


@app.callback()
def main_callback(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", help="Output machine-readable JSON."),
    no_color: bool = typer.Option(False, "--no-color", help="Disable colour output."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompts."),
    loan_id: str | None = typer.Option(None, "--loan", "-l", help="Active loan context."),
) -> None:
    config = load_config()
    if not config.config_file.exists() and ctx.invoked_subcommand != "wizard":
        if yes:
            save_config(config)
        else:
            from loanlens.cli.wizard import run_wizard

            config = run_wizard(defaults_only=False)
    store = (
        SqliteStore(config)
        if config.storage_backend == StorageBackend.SQLITE
        else JsonStore(config)
    )
    ctx.obj = {
        "config": config,
        "store": store,
        "json_output": json_output,
        "no_color": no_color,
        "yes": yes,
        "loan_id": loan_id,
    }


def main() -> None:
    app()
