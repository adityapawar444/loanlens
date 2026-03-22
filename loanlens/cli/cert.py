from __future__ import annotations

from uuid import UUID

import typer

from loanlens.cli._common import echo_json, get_config, get_console, get_state, get_store
from loanlens.services.cert_service import CertService

app = typer.Typer(help="Certificate commands.")

FY_OPTION = typer.Option(..., "--fy")


@app.command("interest")
def interest(ctx: typer.Context, loan_id: UUID, financial_year: str = FY_OPTION) -> None:
    result = CertService(get_store(ctx), get_config(ctx)).interest_certificate(
        loan_id,
        financial_year,
    )
    if get_state(ctx)["json_output"]:
        echo_json(result)
        return
    console = get_console(ctx)
    console.print(f"Loan: {result['loan'].bank_name} / {result['loan'].account_number}")
    console.print(f"Financial Year: {result['financial_year']}")
    console.print(f"Total Interest: {result['total_interest']}")
