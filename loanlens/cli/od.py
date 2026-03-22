from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import cast
from uuid import UUID

import typer

from loanlens.cli._common import echo_json, get_config, get_console, get_state, get_store
from loanlens.services.od_service import ODService
from loanlens.ui.formatters import format_date, format_inr

app = typer.Typer(help="OD account commands.")
DATE_OPTION = typer.Option(None, "--date")
BALANCE_OPTION = typer.Option(None, "--balance")


def _parse_decimal(value: str, field_name: str) -> Decimal:
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise typer.BadParameter(f"Invalid decimal for {field_name}: {value}") from exc


def _parse_date(value: str | None) -> date:
    if value is None:
        return date.today()
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise typer.BadParameter(f"Invalid date: {value}") from exc


@app.command("deposit")
def deposit(
    ctx: typer.Context,
    loan_id: UUID,
    amount: str,
    txn_date: str | None = DATE_OPTION,
    notes: str = "",
) -> None:
    txn = ODService(get_store(ctx), get_config(ctx)).deposit(
        loan_id,
        _parse_decimal(amount, "amount"),
        _parse_date(txn_date),
        notes,
    )
    if get_state(ctx)["json_output"]:
        typer.echo(txn.model_dump_json(indent=2))
        return
    get_console(ctx).print(
        f"Deposited {format_inr(txn.amount)} on {format_date(txn.txn_date)}. "
        f"Balance: {format_inr(txn.balance_after)}"
    )


@app.command("withdraw")
def withdraw(
    ctx: typer.Context,
    loan_id: UUID,
    amount: str,
    txn_date: str | None = DATE_OPTION,
    notes: str = "",
) -> None:
    txn = ODService(get_store(ctx), get_config(ctx)).withdraw(
        loan_id,
        _parse_decimal(amount, "amount"),
        _parse_date(txn_date),
        notes,
    )
    if get_state(ctx)["json_output"]:
        typer.echo(txn.model_dump_json(indent=2))
        return
    get_console(ctx).print(
        f"Withdrew {format_inr(txn.amount)} on {format_date(txn.txn_date)}. "
        f"Balance: {format_inr(txn.balance_after)}"
    )


@app.command("balance")
def balance(ctx: typer.Context, loan_id: UUID) -> None:
    service = ODService(get_store(ctx), get_config(ctx))
    account = service.balance(loan_id)
    impact = service.impact(loan_id)
    if get_state(ctx)["json_output"]:
        echo_json({"account": account, "impact": impact})
        return
    estimated_savings = cast(Decimal, impact["estimated_savings"])
    get_console(ctx).print(
        f"Current balance: {format_inr(account.current_balance)}\n"
        f"Estimated savings: {format_inr(estimated_savings)}"
    )


@app.command("history")
def history(ctx: typer.Context, loan_id: UUID) -> None:
    history_rows = ODService(get_store(ctx), get_config(ctx)).history(loan_id)
    if get_state(ctx)["json_output"]:
        typer.echo(
            "[\n" + ",\n".join(txn.model_dump_json(indent=2) for txn in history_rows) + "\n]"
            if history_rows
            else "[]"
        )
        return
    console = get_console(ctx)
    for txn in history_rows:
        console.print(
            f"{format_date(txn.txn_date)} {txn.txn_type} {format_inr(txn.amount)} "
            f"-> {format_inr(txn.balance_after)}"
        )


@app.command("impact")
def impact(
    ctx: typer.Context,
    loan_id: UUID,
    balance: str | None = BALANCE_OPTION,
) -> None:
    parsed_balance = _parse_decimal(balance, "balance") if balance is not None else None
    result = ODService(get_store(ctx), get_config(ctx)).impact(loan_id, parsed_balance)
    if get_state(ctx)["json_output"]:
        echo_json(result)
        return
    average_balance = cast(Decimal, result["average_balance"])
    estimated_savings = cast(Decimal, result["estimated_savings"])
    get_console(ctx).print(
        f"Average balance: {format_inr(average_balance)}\n"
        f"Estimated savings: {format_inr(estimated_savings)}"
    )
