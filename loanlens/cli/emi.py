from __future__ import annotations

from decimal import Decimal, InvalidOperation
from uuid import UUID

import typer

from loanlens.cli._common import get_config, get_console, get_state, get_store
from loanlens.engine.emi import calculate_emi
from loanlens.services.loan_service import LoanService
from loanlens.ui.formatters import format_inr

app = typer.Typer(help="EMI commands.")

PRINCIPAL_OPTION = typer.Option(..., prompt=True)
ROI_OPTION = typer.Option(..., prompt=True)
TENURE_OPTION = typer.Option(..., prompt=True)
ROUNDING_OPTION = typer.Option("rupee", prompt=True)


def _parse_decimal(value: str, field_name: str) -> Decimal:
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise typer.BadParameter(f"Invalid decimal for {field_name}: {value}") from exc


@app.command("calculate")
def calculate(
    ctx: typer.Context,
    principal: str = PRINCIPAL_OPTION,
    annual_roi: str = ROI_OPTION,
    tenure_months: int = TENURE_OPTION,
    rounding: str = ROUNDING_OPTION,
) -> None:
    emi_value = calculate_emi(
        _parse_decimal(principal, "principal"),
        _parse_decimal(annual_roi, "annual_roi"),
        tenure_months,
        rounding,  # type: ignore[arg-type]
    )
    if get_state(ctx)["json_output"]:
        typer.echo(f'{{"emi": "{emi_value}"}}')
        return
    get_console(ctx).print(f"EMI: {format_inr(emi_value)}")


@app.command("show")
def show(ctx: typer.Context, loan_id: UUID) -> None:
    loan = LoanService(get_store(ctx), get_config(ctx)).get(loan_id)
    if loan is None:
        raise typer.BadParameter(f"Loan {loan_id} not found")
    emi_value = calculate_emi(
        loan.disbursed_amount,
        loan.roi_initial,
        loan.tenure_months,
        loan.emi_rounding,
    )
    if get_state(ctx)["json_output"]:
        typer.echo(f'{{"loan_id": "{loan_id}", "emi": "{emi_value}"}}')
        return
    get_console(ctx).print(f"EMI: {format_inr(emi_value)}")
