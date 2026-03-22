from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from uuid import UUID

import typer

from loanlens.cli._common import get_config, get_console, get_state, get_store
from loanlens.models import AdjustmentMode, RateRevision
from loanlens.services.schedule_service import ScheduleService

app = typer.Typer(help="Rate revision commands.")

ROI_OPTION = typer.Option(..., "--roi")
DATE_OPTION = typer.Option(..., "--date")
MODE_OPTION = typer.Option(AdjustmentMode.ADJUST_EMI, "--mode")


def _parse_decimal(value: str, field_name: str) -> Decimal:
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise typer.BadParameter(f"Invalid decimal for {field_name}: {value}") from exc


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise typer.BadParameter(f"Invalid date: {value}") from exc


@app.command("add")
def add(
    ctx: typer.Context,
    loan_id: UUID,
    new_roi: str = ROI_OPTION,
    effective_date: str = DATE_OPTION,
    mode: AdjustmentMode = MODE_OPTION,
) -> None:
    store = get_store(ctx)
    loan = store.get_loan(loan_id)
    if loan is None:
        raise typer.BadParameter(f"Loan {loan_id} not found")
    revision = RateRevision(
        loan_id=loan_id,
        effective_date=_parse_date(effective_date),
        old_roi=loan.roi_initial,
        new_roi=_parse_decimal(new_roi, "roi"),
        adjustment_mode=mode,
    )
    store.add_rate_revision(revision)
    ScheduleService(store, get_config(ctx)).generate(loan_id)
    if get_state(ctx)["json_output"]:
        typer.echo(revision.model_dump_json(indent=2))
        return
    get_console(ctx).print(f"Rate revision added: {revision.old_roi}% -> {revision.new_roi}%")


@app.command("list")
def list_revisions(ctx: typer.Context, loan_id: UUID) -> None:
    revisions = get_store(ctx).list_rate_revisions(loan_id)
    if get_state(ctx)["json_output"]:
        typer.echo(
            "[\n" + ",\n".join(item.model_dump_json(indent=2) for item in revisions) + "\n]"
            if revisions
            else "[]"
        )
        return
    console = get_console(ctx)
    for item in revisions:
        console.print(f"{item.effective_date.isoformat()} {item.old_roi}% -> {item.new_roi}%")


@app.command("impact")
def impact(ctx: typer.Context, loan_id: UUID) -> None:
    rows = ScheduleService(get_store(ctx), get_config(ctx)).get(loan_id)
    if not rows:
        rows = ScheduleService(get_store(ctx), get_config(ctx)).generate(loan_id)
    total_interest = sum((row.interest_component for row in rows), start=Decimal("0"))
    if get_state(ctx)["json_output"]:
        typer.echo(f'{{"loan_id": "{loan_id}", "total_interest": "{total_interest}"}}')
        return
    get_console(ctx).print(f"Projected total interest: {total_interest}")
