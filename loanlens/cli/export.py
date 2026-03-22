from __future__ import annotations

from pathlib import Path
from uuid import UUID

import typer

from loanlens.cli._common import get_config, get_store
from loanlens.export.csv_export import export_rows as export_csv_rows
from loanlens.export.markdown_export import export_rows as export_markdown_rows
from loanlens.export.pdf_export import export_text
from loanlens.services.schedule_service import ScheduleService

app = typer.Typer(help="Export commands.")


def _schedule_rows(ctx: typer.Context, loan_id: UUID) -> list[dict[str, object]]:
    service = ScheduleService(get_store(ctx), get_config(ctx))
    rows = service.get(loan_id) or service.generate(loan_id)
    return [row.model_dump(mode="json") for row in rows]


@app.command("csv")
def csv_export(ctx: typer.Context, loan_id: UUID, path: Path) -> None:
    typer.echo(str(export_csv_rows(_schedule_rows(ctx, loan_id), path)))


@app.command("pdf")
def pdf_export(ctx: typer.Context, loan_id: UUID, path: Path) -> None:
    rows = _schedule_rows(ctx, loan_id)
    typer.echo(str(export_text("\n".join(str(row) for row in rows), path)))


@app.command("markdown")
def markdown_export(ctx: typer.Context, loan_id: UUID, path: Path) -> None:
    typer.echo(str(export_markdown_rows(_schedule_rows(ctx, loan_id), path)))
