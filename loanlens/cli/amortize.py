from __future__ import annotations

from uuid import UUID

import typer

from loanlens.cli._common import get_config, get_console, get_state, get_store
from loanlens.engine.amortize import annual_summary, total_cost
from loanlens.services.schedule_service import ScheduleService
from loanlens.ui.charts import interest_vs_principal_chart
from loanlens.ui.panels import build_summary_panel
from loanlens.ui.tables import build_schedule_table

app = typer.Typer(help="Amortization commands.")


@app.command("show")
def show(ctx: typer.Context, loan_id: UUID) -> None:
    service = ScheduleService(get_store(ctx), get_config(ctx))
    rows = service.get(loan_id) or service.generate(loan_id)
    if get_state(ctx)["json_output"]:
        typer.echo("[\n" + ",\n".join(row.model_dump_json(indent=2) for row in rows) + "\n]")
        return
    get_console(ctx).print(build_schedule_table(rows))


@app.command("summary")
def summary(ctx: typer.Context, loan_id: UUID) -> None:
    service = ScheduleService(get_store(ctx), get_config(ctx))
    rows = service.get(loan_id) or service.generate(loan_id)
    summaries = annual_summary(rows)
    if get_state(ctx)["json_output"]:
        typer.echo("[\n" + ",\n".join(item.model_dump_json(indent=2) for item in summaries) + "\n]")
        return
    get_console(ctx).print(build_summary_panel(rows[-1], total_cost(rows)))


@app.command("chart")
def chart(ctx: typer.Context, loan_id: UUID) -> None:
    service = ScheduleService(get_store(ctx), get_config(ctx))
    rows = service.get(loan_id) or service.generate(loan_id)
    chart_text = interest_vs_principal_chart(rows)
    if get_state(ctx)["json_output"]:
        typer.echo(f'{{"chart": {chart_text!r}}}')
        return
    get_console(ctx).print(chart_text)
