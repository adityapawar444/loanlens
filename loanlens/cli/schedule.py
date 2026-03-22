from __future__ import annotations

from datetime import date
from pathlib import Path
from uuid import UUID

import typer

from loanlens.cli._common import get_config, get_console, get_state, get_store
from loanlens.services.schedule_service import ScheduleService
from loanlens.ui.tables import build_schedule_table

app = typer.Typer(help="Schedule commands.")

FROM_DATE_OPTION = typer.Option(None, "--from")
EXPORT_PATH_OPTION = typer.Option(..., file_okay=True, dir_okay=False, writable=True)


def _parse_date(value: str, field_name: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise typer.BadParameter(f"Invalid date for {field_name}: {value}") from exc


@app.command("show")
def show(
    ctx: typer.Context,
    loan_id: UUID,
    from_date: str | None = FROM_DATE_OPTION,
    year: int | None = None,
) -> None:
    service = ScheduleService(get_store(ctx), get_config(ctx))
    rows = service.get(loan_id)
    if not rows:
        rows = service.generate(loan_id)
    if from_date is not None:
        parsed_from_date = _parse_date(from_date, "from_date")
        rows = [row for row in rows if row.due_date >= parsed_from_date]
    if year is not None:
        rows = [row for row in rows if row.due_date.year == year]
    if get_state(ctx)["json_output"]:
        typer.echo(
            "[\n" + ",\n".join(row.model_dump_json(indent=2) for row in rows) + "\n]"
            if rows
            else "[]"
        )
        return
    get_console(ctx).print(build_schedule_table(rows))


@app.command("export")
def export(
    ctx: typer.Context,
    loan_id: UUID,
    path: Path = EXPORT_PATH_OPTION,
) -> None:
    dataframe = ScheduleService(get_store(ctx), get_config(ctx)).export_to_dataframe(loan_id)
    dataframe.to_csv(path, index=False)
    typer.echo(str(path))


@app.command("regenerate")
def regenerate(ctx: typer.Context, loan_id: UUID) -> None:
    rows = ScheduleService(get_store(ctx), get_config(ctx)).generate(loan_id)
    if get_state(ctx)["json_output"]:
        typer.echo("[\n" + ",\n".join(row.model_dump_json(indent=2) for row in rows) + "\n]")
        return
    get_console(ctx).print(build_schedule_table(rows[: get_config(ctx).items_per_page]))
