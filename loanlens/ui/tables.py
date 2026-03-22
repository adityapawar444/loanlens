from __future__ import annotations

from collections.abc import Sequence

from prompt_toolkit import prompt
from rich.table import Table

from loanlens.models import LoanProfile, ScheduleRow
from loanlens.ui.formatters import format_date, format_inr


def build_schedule_table(rows: Sequence[ScheduleRow]) -> Table:
    table = Table(title="Repayment Schedule")
    table.add_column("#", justify="right")
    table.add_column("Due Date")
    table.add_column("Opening Principal", justify="right")
    table.add_column("EMI", justify="right")
    table.add_column("Interest", justify="right")
    table.add_column("Principal", justify="right")
    table.add_column("Prepayment", justify="right")
    table.add_column("Closing Principal", justify="right")
    table.add_column("Status")

    for row in rows:
        table.add_row(
            str(row.instalment_number),
            format_date(row.due_date),
            format_inr(row.opening_principal),
            format_inr(row.emi_amount),
            format_inr(row.interest_component),
            format_inr(row.principal_component),
            format_inr(row.prepayment_amount),
            format_inr(row.closing_principal),
            row.status.value,
        )
    return table


def build_loan_table(loans: Sequence[LoanProfile]) -> Table:
    table = Table(title="Loans")
    table.add_column("Loan ID")
    table.add_column("Name")
    table.add_column("Bank")
    table.add_column("Disbursed", justify="right")
    table.add_column("RoI", justify="right")
    table.add_column("Tenure", justify="right")
    table.add_column("Archived")

    for loan in loans:
        table.add_row(
            str(loan.loan_id),
            loan.name,
            loan.bank_name,
            format_inr(loan.disbursed_amount),
            f"{loan.roi_initial:.2f}%",
            str(loan.tenure_months),
            "yes" if loan.is_archived else "no",
        )
    return table


def paginate_table(rows: Sequence[ScheduleRow], items_per_page: int, title: str) -> list[Table]:
    pages: list[Table] = []
    total_pages = max((len(rows) - 1) // items_per_page + 1, 1)
    for start in range(0, len(rows), items_per_page):
        chunk = rows[start : start + items_per_page]
        table = build_schedule_table(chunk)
        table.title = f"{title} ({(start // items_per_page) + 1}/{total_pages})"
        pages.append(table)
    return pages


def page_navigation_hint() -> str:
    return prompt("Navigation [n/p/q]: ", default="q")
