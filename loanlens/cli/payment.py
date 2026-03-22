from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Literal, cast
from uuid import UUID

import typer

from loanlens.cli._common import echo_json, get_console, get_state, get_store
from loanlens.models import Payment

app = typer.Typer(help="Payment commands.")

DATE_OPTION = typer.Option(..., "--date")
PaymentTypeLiteral = Literal["EMI", "PREPAYMENT", "INTEREST_ONLY"]


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


@app.command("record")
def record(
    ctx: typer.Context,
    loan_id: UUID,
    amount: str,
    payment_date: str = DATE_OPTION,
    payment_type: str = "EMI",
    reference: str = "",
    notes: str = "",
) -> None:
    payment = Payment(
        loan_id=loan_id,
        payment_date=_parse_date(payment_date, "date"),
        amount=_parse_decimal(amount, "amount"),
        payment_type=cast(PaymentTypeLiteral, payment_type),
        reference=reference,
        notes=notes,
    )
    get_store(ctx).add_payment(payment)
    if get_state(ctx)["json_output"]:
        typer.echo(payment.model_dump_json(indent=2))
        return
    get_console(ctx).print(f"Recorded payment {payment.payment_id}")


@app.command("list")
def list_payments(ctx: typer.Context, loan_id: UUID) -> None:
    payments = get_store(ctx).list_payments(loan_id)
    if get_state(ctx)["json_output"]:
        typer.echo(
            "[\n" + ",\n".join(item.model_dump_json(indent=2) for item in payments) + "\n]"
            if payments
            else "[]"
        )
        return
    console = get_console(ctx)
    for item in payments:
        console.print(f"{item.payment_date.isoformat()} {item.payment_type} {item.amount}")


@app.command("reconcile")
def reconcile(ctx: typer.Context, loan_id: UUID) -> None:
    store = get_store(ctx)
    schedule = store.get_schedule(loan_id)
    payments = store.list_payments(loan_id)
    scheduled_dates = {row.due_date: row for row in schedule}
    recorded_dates = {
        payment.payment_date: payment
        for payment in payments
        if payment.payment_type == "EMI"
    }
    issues: list[dict[str, object]] = []
    for due_date, row in scheduled_dates.items():
        payment = recorded_dates.get(due_date)
        if payment is None and due_date < date.today():
            issues.append({"due_date": due_date.isoformat(), "issue": "missing_payment"})
        elif payment is not None and payment.amount != row.emi_amount:
            issues.append(
                {
                    "due_date": due_date.isoformat(),
                    "issue": "amount_mismatch",
                    "scheduled": str(row.emi_amount),
                    "actual": str(payment.amount),
                }
            )
    if get_state(ctx)["json_output"]:
        echo_json(issues)
        return
    console = get_console(ctx)
    if not issues:
        console.print("No reconciliation issues found.")
        return
    for issue in issues:
        console.print(str(issue))
