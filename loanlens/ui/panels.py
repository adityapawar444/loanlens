from __future__ import annotations

from rich.panel import Panel

from loanlens.models import LoanProfile, ScheduleRow, TotalCost
from loanlens.ui.formatters import format_date, format_inr, format_months, format_pct


def build_loan_panel(loan: LoanProfile) -> Panel:
    body = "\n".join(
        [
            f"Loan ID: {loan.loan_id}",
            f"Bank: {loan.bank_name}",
            f"Account: {loan.account_number}",
            f"Disbursed: {format_inr(loan.disbursed_amount)}",
            f"RoI: {format_pct(loan.roi_initial)}",
            f"Tenure: {format_months(loan.tenure_months)}",
            f"EMI Start: {format_date(loan.emi_start_date)}",
            f"Adjustment: {loan.adjustment_mode.value}",
        ]
    )
    return Panel(body, title=loan.name)


def build_summary_panel(last_row: ScheduleRow | None, total: TotalCost | None = None) -> Panel:
    if last_row is None:
        return Panel("No schedule generated.", title="Summary")

    lines = [
        f"Outstanding: {format_inr(last_row.closing_principal)}",
        f"Cumulative Interest: {format_inr(last_row.cumulative_interest)}",
        f"Cumulative Principal: {format_inr(last_row.cumulative_principal)}",
    ]
    if total is not None:
        lines.append(f"Total Cost: {format_inr(total.total)}")
    return Panel("\n".join(lines), title="Summary")
