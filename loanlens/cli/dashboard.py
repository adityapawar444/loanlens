from __future__ import annotations

from uuid import UUID

import typer

from loanlens.cli._common import get_config, get_console, get_state, get_store
from loanlens.engine.amortize import total_cost
from loanlens.services.loan_service import LoanService
from loanlens.services.schedule_service import ScheduleService
from loanlens.ui.panels import build_loan_panel, build_summary_panel
from loanlens.ui.tables import build_loan_table

app = typer.Typer(help="Dashboard views.", invoke_without_command=True)


@app.callback()
def show(ctx: typer.Context, loan_id: UUID | None = None) -> None:
    loan_service = LoanService(get_store(ctx), get_config(ctx))
    schedule_service = ScheduleService(get_store(ctx), get_config(ctx))
    console = get_console(ctx)

    if loan_id is None:
        loans = loan_service.list()
        if get_state(ctx)["json_output"]:
            typer.echo(
                "[\n" + ",\n".join(loan.model_dump_json(indent=2) for loan in loans) + "\n]"
                if loans
                else "[]"
            )
            return
        console.print(build_loan_table(loans))
        return

    loan = loan_service.get(loan_id)
    if loan is None:
        raise typer.BadParameter(f"Loan {loan_id} not found")
    rows = schedule_service.get(loan_id) or schedule_service.generate(loan_id)
    if get_state(ctx)["json_output"]:
        typer.echo(
            "{"
            f'"loan": {loan.model_dump_json(indent=2)}, '
            f'"summary": {total_cost(rows).model_dump_json(indent=2)}'
            "}"
        )
        return
    console.print(build_loan_panel(loan))
    console.print(build_summary_panel(rows[-1], total_cost(rows)))
