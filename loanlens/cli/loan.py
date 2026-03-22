from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from uuid import UUID

import typer

from loanlens.cli._common import get_config, get_console, get_state, get_store
from loanlens.models import AdjustmentMode, LoanProfile, Moratorium, MoratoriumType, RoiType
from loanlens.services.loan_service import LoanService
from loanlens.services.schedule_service import ScheduleService
from loanlens.ui.panels import build_loan_panel
from loanlens.ui.tables import build_loan_table

app = typer.Typer(help="Loan profile commands.")

NAME_OPTION = typer.Option(..., prompt=True)
BANK_OPTION = typer.Option(..., prompt=True)
ACCOUNT_OPTION = typer.Option(..., prompt=True)
MONEY_OPTION = typer.Option(..., prompt=True)
DATE_OPTION = typer.Option(..., prompt=True)
ROI_OPTION = typer.Option(..., prompt=True)
ROI_TYPE_OPTION = typer.Option(RoiType.FLOATING, prompt=True)
TENURE_OPTION = typer.Option(..., prompt=True)
EMI_DAY_OPTION = typer.Option(..., prompt=True)
ADJUSTMENT_OPTION = typer.Option(AdjustmentMode.ADJUST_EMI, prompt=True)
PREPAY_CHARGES_OPTION = typer.Option("0", prompt=True)
ROUNDING_OPTION = typer.Option("rupee", prompt=True)
MORATORIUM_OPTION = typer.Option(None, "--moratorium")
MORATORIUM_FROM_OPTION = typer.Option(None, "--moratorium-from")
MORATORIUM_TO_OPTION = typer.Option(None, "--moratorium-to")
MORATORIUM_TYPE_OPTION = typer.Option(None, "--moratorium-type")


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


@app.command("add")
def add(
    ctx: typer.Context,
    name: str = NAME_OPTION,
    bank_name: str = BANK_OPTION,
    account_number: str = ACCOUNT_OPTION,
    sanction_amount: str = MONEY_OPTION,
    disbursed_amount: str = MONEY_OPTION,
    disbursement_date: str = DATE_OPTION,
    roi_initial: str = ROI_OPTION,
    roi_type: RoiType = ROI_TYPE_OPTION,
    tenure_months: int = TENURE_OPTION,
    emi_start_date: str = DATE_OPTION,
    emi_day: int = EMI_DAY_OPTION,
    adjustment_mode: AdjustmentMode = ADJUSTMENT_OPTION,
    prepayment_charges_pct: str = PREPAY_CHARGES_OPTION,
    emi_rounding: str = ROUNDING_OPTION,
    add_moratorium: bool | None = MORATORIUM_OPTION,
    moratorium_from: str | None = MORATORIUM_FROM_OPTION,
    moratorium_to: str | None = MORATORIUM_TO_OPTION,
    moratorium_type: MoratoriumType | None = MORATORIUM_TYPE_OPTION,
) -> None:
    store = get_store(ctx)
    config = get_config(ctx)
    service = LoanService(store, config)
    loan = LoanProfile(
        name=name,
        bank_name=bank_name,
        account_number=account_number,
        sanction_amount=_parse_decimal(sanction_amount, "sanction_amount"),
        disbursed_amount=_parse_decimal(disbursed_amount, "disbursed_amount"),
        disbursement_date=_parse_date(disbursement_date, "disbursement_date"),
        roi_initial=_parse_decimal(roi_initial, "roi_initial"),
        roi_type=roi_type,
        tenure_months=tenure_months,
        emi_start_date=_parse_date(emi_start_date, "emi_start_date"),
        emi_day=emi_day,
        adjustment_mode=adjustment_mode,
        prepayment_charges_pct=_parse_decimal(
            prepayment_charges_pct,
            "prepayment_charges_pct",
        ),
        emi_rounding=emi_rounding,
    )
    created = service.create(loan)
    moratorium: Moratorium | None = None
    should_add_moratorium = add_moratorium
    if should_add_moratorium is None and not get_state(ctx)["json_output"]:
        should_add_moratorium = typer.confirm(
            "Does this loan have a moratorium?",
            default=False,
        )
    if should_add_moratorium:
        from_value = moratorium_from
        to_value = moratorium_to
        type_value = moratorium_type
        if from_value is None:
            from_value = typer.prompt("Moratorium from date (YYYY-MM-DD)")
        if to_value is None:
            to_value = typer.prompt("Moratorium to date (YYYY-MM-DD)")
        if type_value is None:
            type_value = MoratoriumType(
                typer.prompt(
                    "Moratorium type",
                    default=MoratoriumType.INTEREST_CAPITALISE.value,
                )
            )
        moratorium = Moratorium(
            loan_id=created.loan_id,
            from_date=_parse_date(from_value, "moratorium_from"),
            to_date=_parse_date(to_value, "moratorium_to"),
            moratorium_type=type_value,
        )
        store.add_moratorium(moratorium)
        ScheduleService(store, config).mark_stale(
            created.loan_id,
            "moratorium added during loan add",
        )
    if get_state(ctx)["json_output"]:
        if moratorium is None:
            typer.echo(created.model_dump_json(indent=2))
        else:
            typer.echo(
                "{\n"
                f'  "loan": {created.model_dump_json(indent=2)},\n'
                f'  "moratorium": {moratorium.model_dump_json(indent=2)}\n'
                "}"
            )
        return
    get_console(ctx).print(build_loan_panel(created))
    if moratorium is not None:
        get_console(ctx).print(f"Moratorium added: {moratorium.moratorium_type.value}")


@app.command("list")
def list_loans(ctx: typer.Context, include_archived: bool = False) -> None:
    service = LoanService(get_store(ctx), get_config(ctx))
    loans = service.list(include_archived=include_archived)
    if get_state(ctx)["json_output"]:
        typer.echo(
            "[\n" + ",\n".join(loan.model_dump_json(indent=2) for loan in loans) + "\n]"
            if loans
            else "[]"
        )
        return
    get_console(ctx).print(build_loan_table(loans))


@app.command("show")
def show(ctx: typer.Context, loan_id: UUID) -> None:
    service = LoanService(get_store(ctx), get_config(ctx))
    loan = service.get(loan_id)
    if loan is None:
        raise typer.BadParameter(f"Loan {loan_id} not found")
    if get_state(ctx)["json_output"]:
        typer.echo(loan.model_dump_json(indent=2))
        return
    get_console(ctx).print(build_loan_panel(loan))


@app.command("edit")
def edit(
    ctx: typer.Context,
    loan_id: UUID,
    name: str | None = None,
    bank_name: str | None = None,
    roi_initial: str | None = None,
    tenure_months: int | None = None,
    notes: str | None = None,
) -> None:
    updates = {
        key: value
        for key, value in {
            "name": name,
            "bank_name": bank_name,
            "roi_initial": _parse_decimal(roi_initial, "roi_initial")
            if roi_initial is not None
            else None,
            "tenure_months": tenure_months,
            "notes": notes,
        }.items()
        if value is not None
    }
    if not updates:
        raise typer.BadParameter("Provide at least one field to update")
    updated = LoanService(get_store(ctx), get_config(ctx)).update(loan_id, updates)
    if get_state(ctx)["json_output"]:
        typer.echo(updated.model_dump_json(indent=2))
        return
    get_console(ctx).print(build_loan_panel(updated))


@app.command("archive")
def archive(ctx: typer.Context, loan_id: UUID) -> None:
    archived = LoanService(get_store(ctx), get_config(ctx)).archive(loan_id)
    if get_state(ctx)["json_output"]:
        typer.echo(archived.model_dump_json(indent=2))
        return
    get_console(ctx).print(build_loan_panel(archived))
