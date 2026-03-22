from __future__ import annotations

from datetime import date
from uuid import UUID

import typer

from loanlens.cli._common import get_config, get_console, get_state, get_store
from loanlens.models import Moratorium, MoratoriumType
from loanlens.services.od_service import ODService
from loanlens.services.schedule_service import ScheduleService

app = typer.Typer(help="Moratorium commands.")
FROM_OPTION = typer.Option(..., "--from")
TO_OPTION = typer.Option(..., "--to")
TYPE_OPTION = typer.Option(..., "--type")


def _parse_date(value: str, field_name: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise typer.BadParameter(f"Invalid date for {field_name}: {value}") from exc


@app.command("add")
def add(
    ctx: typer.Context,
    loan_id: UUID,
    from_date: str = FROM_OPTION,
    to_date: str = TO_OPTION,
    moratorium_type: MoratoriumType = TYPE_OPTION,
    reason: str = "",
    approved_by: str = "",
) -> None:
    moratorium = Moratorium(
        loan_id=loan_id,
        from_date=_parse_date(from_date, "from_date"),
        to_date=_parse_date(to_date, "to_date"),
        moratorium_type=moratorium_type,
        reason=reason,
        approved_by=approved_by,
    )
    get_store(ctx).add_moratorium(moratorium)
    ScheduleService(get_store(ctx), get_config(ctx)).mark_stale(loan_id, "moratorium added")
    if get_state(ctx)["json_output"]:
        typer.echo(moratorium.model_dump_json(indent=2))
        return
    get_console(ctx).print(f"Moratorium added: {moratorium.moratorium_type.value}")


@app.command("list")
def list_moratoriums(ctx: typer.Context, loan_id: UUID) -> None:
    moratoriums = get_store(ctx).list_moratoriums(loan_id)
    if get_state(ctx)["json_output"]:
        typer.echo(
            "[\n" + ",\n".join(item.model_dump_json(indent=2) for item in moratoriums) + "\n]"
            if moratoriums
            else "[]"
        )
        return
    console = get_console(ctx)
    for item in moratoriums:
        console.print(
            f"{item.moratorium_id} {item.moratorium_type.value} "
            f"{item.from_date.isoformat()} -> {item.to_date.isoformat()}"
        )


@app.command("impact")
def impact(ctx: typer.Context, loan_id: UUID, moratorium_id: UUID) -> None:
    result = ODService(get_store(ctx), get_config(ctx)).moratorium_impact(loan_id, moratorium_id)
    if get_state(ctx)["json_output"]:
        typer.echo(result.model_dump_json(indent=2))
        return
    get_console(ctx).print(
        f"Months: {result.moratorium_months}\n"
        f"Interest accrued: {result.interest_accrued}\n"
        f"New principal: {result.new_principal}\n"
        f"Deferred amount: {result.deferred_amount}"
    )
