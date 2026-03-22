from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from uuid import UUID

import typer

from loanlens.cli._common import echo_json, get_config, get_console, get_state, get_store
from loanlens.services.simulate_service import SimulateService
from loanlens.ui.formatters import format_date, format_inr

app = typer.Typer(help="Simulation commands.")

DATE_OPTION = typer.Option(..., "--date")
ROI_OPTION = typer.Option(..., "--roi")
FROM_OPTION = typer.Option(..., "--from")
LABEL_OPTION = typer.Option("", "--label")


def _parse_decimal(value: str, field_name: str) -> Decimal:
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise typer.BadParameter(f"Invalid decimal for {field_name}: {value}") from exc


def _parse_date(value: str, field_name: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise typer.BadParameter(f"Invalid date for {field_name}: {value}") from exc


def _print_output(ctx: typer.Context, result: object) -> None:
    if get_state(ctx)["json_output"]:
        if hasattr(result, "model_dump_json"):
            typer.echo(result.model_dump_json(indent=2))
            return
        echo_json(result)
        return
    console = get_console(ctx)
    if hasattr(result, "interest_saved"):
        console.print(f"Interest saved: {format_inr(result.interest_saved)}")
    if hasattr(result, "months_saved"):
        console.print(f"Months saved: {result.months_saved}")
    if hasattr(result, "new_emi"):
        console.print(f"New EMI: {format_inr(result.new_emi)}")
    if hasattr(result, "new_closure_date") and result.new_closure_date is not None:
        console.print(f"New closure date: {format_date(result.new_closure_date)}")


@app.command("prepay")
def prepay(
    ctx: typer.Context,
    loan_id: UUID,
    amount: str,
    prepayment_date: str = DATE_OPTION,
    mode: str = "REDUCE_TENURE",
) -> None:
    result = SimulateService(get_store(ctx), get_config(ctx)).prepay(
        loan_id,
        _parse_decimal(amount, "amount"),
        _parse_date(prepayment_date, "date"),
        mode,
        False,
    )
    _print_output(ctx, result)


@app.command("compare")
def compare(
    ctx: typer.Context,
    loan_id: UUID,
    amount: str,
    prepayment_date: str = DATE_OPTION,
    invest_return_pct: str = ROI_OPTION,
    mode: str = "REDUCE_TENURE",
) -> None:
    result = SimulateService(get_store(ctx), get_config(ctx)).compare(
        loan_id,
        _parse_decimal(amount, "amount"),
        _parse_date(prepayment_date, "date"),
        mode,
        _parse_decimal(invest_return_pct, "roi"),
    )
    if get_state(ctx)["json_output"]:
        typer.echo(result.model_dump_json(indent=2))
        return
    get_console(ctx).print(f"Investment value: {format_inr(result.investment_value)}")
    get_console(ctx).print(f"Net advantage: {format_inr(result.net_prepayment_advantage)}")


@app.command("recurring")
def recurring(
    ctx: typer.Context,
    loan_id: UUID,
    monthly_amount: str,
    start_date: str = DATE_OPTION,
    mode: str = "REDUCE_TENURE",
) -> None:
    result = SimulateService(get_store(ctx), get_config(ctx)).recurring(
        loan_id,
        _parse_decimal(monthly_amount, "monthly_amount"),
        _parse_date(start_date, "date"),
        mode,
    )
    _print_output(ctx, result)


@app.command("rate-change")
def rate_change(
    ctx: typer.Context,
    loan_id: UUID,
    new_roi: str = ROI_OPTION,
    effective_date: str = FROM_OPTION,
    mode: str = "REDUCE_EMI",
) -> None:
    result = SimulateService(get_store(ctx), get_config(ctx)).rate_change(
        loan_id,
        _parse_decimal(new_roi, "roi"),
        _parse_date(effective_date, "from"),
        mode,
    )
    _print_output(ctx, result)


@app.command("save")
def save(
    ctx: typer.Context,
    loan_id: UUID,
    simulation_type: str,
    amount: str,
    simulation_date: str = DATE_OPTION,
    label: str = LABEL_OPTION,
) -> None:
    service = SimulateService(get_store(ctx), get_config(ctx))
    output = service.prepay(
        loan_id,
        _parse_decimal(amount, "amount"),
        _parse_date(simulation_date, "date"),
        "REDUCE_TENURE",
        False,
    )
    result = service.save(
        loan_id,
        simulation_type,
        {"amount": amount, "date": simulation_date},
        output,
        label,
    )
    if get_state(ctx)["json_output"]:
        typer.echo(result.model_dump_json(indent=2))
        return
    get_console(ctx).print(f"Saved simulation: {result.simulation_id}")


@app.command("list")
def list_simulations(ctx: typer.Context, loan_id: UUID) -> None:
    results = SimulateService(get_store(ctx), get_config(ctx)).list(loan_id)
    if get_state(ctx)["json_output"]:
        typer.echo(
            "[\n" + ",\n".join(item.model_dump_json(indent=2) for item in results) + "\n]"
            if results
            else "[]"
        )
        return
    console = get_console(ctx)
    for item in results:
        console.print(f"{item.simulation_id} {item.simulation_type} {item.label}")


@app.command("show")
def show(ctx: typer.Context, simulation_id: UUID) -> None:
    result = SimulateService(get_store(ctx), get_config(ctx)).get(simulation_id)
    if result is None:
        raise typer.BadParameter(f"Simulation {simulation_id} not found")
    if get_state(ctx)["json_output"]:
        typer.echo(result.model_dump_json(indent=2))
        return
    get_console(ctx).print(f"{result.simulation_type} {result.label}")
