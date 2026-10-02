"""
renderer.py — Deterministic Markdown report rendering for LoanLens.

Implements R1–R5 report renderers as defined in design.md §C.
The renderer NEVER re-derives numbers — it takes pre-computed values
from the engine (schedule + metrics) and formats them into Markdown.

Formatting rules (design.md §C Formatting Rules):
  - INR: Indian digit grouping  ₹12,34,567
  - Dates: "10 Aug 2026" in rendered output, YYYY-MM-DD internally
  - Rendering is deterministic: same inputs → same output always
"""

from __future__ import annotations

import calendar
import datetime
from typing import Optional

from .metrics import calculate_metrics
from .schedule import generate_schedule
from .types import AmortizationRow, LoanData, OdSavingsData, SummaryMetrics


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

_MONTH_ABBR = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr",
    5: "May", 6: "Jun", 7: "Jul", 8: "Aug",
    9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
}


def fmt_inr(amount: float) -> str:
    """Format a number in Indian Rupee notation.

    Examples:
        fmt_inr(1234567)  → '₹12,34,567'
        fmt_inr(91143)    → '₹91,143'
        fmt_inr(0)        → '₹0'
        fmt_inr(-50000)   → '-₹50,000'
    """
    n = int(round(amount))
    negative = n < 0
    s = str(abs(n))

    if len(s) <= 3:
        formatted = s
    else:
        # Last group of 3
        formatted = s[-3:]
        s = s[:-3]
        # Remaining groups of 2
        while s:
            formatted = s[-2:] + "," + formatted
            s = s[:-2]

    return ("-₹" if negative else "₹") + formatted


def fmt_date(date_str: str) -> str:
    """Convert YYYY-MM-DD to '10 Aug 2026' format."""
    try:
        d = datetime.date.fromisoformat(date_str)
        return f"{d.day} {_MONTH_ABBR[d.month]} {d.year}"
    except (ValueError, KeyError):
        return date_str


def fmt_pct(value: float, decimals: int = 1) -> str:
    """Format a percentage value, e.g. 6.69 → '6.69%'."""
    return f"{value:.{decimals}f}%"


def _month_label(date_str: str) -> str:
    """Return 'Sep 2026' from '2026-09-10'."""
    try:
        d = datetime.date.fromisoformat(date_str)
        return f"{_MONTH_ABBR[d.month]} {d.year}"
    except (ValueError, KeyError):
        return date_str


def _ym(date_str: str) -> tuple[int, int]:
    """Return (year, month) from a YYYY-MM-DD string."""
    parts = date_str.split("-")
    return int(parts[0]), int(parts[1])


# ---------------------------------------------------------------------------
# R1 — Summary Report
# ---------------------------------------------------------------------------

def render_summary(
    loan_data: LoanData,
    od_data: OdSavingsData,
    today_date: str,
    schedule: Optional[list[AmortizationRow]] = None,
    metrics: Optional[SummaryMetrics] = None,
) -> str:
    """
    R1: Render the LoanLens Summary report.

    Token budget: ≤ 400 tokens.
    """
    if schedule is None:
        schedule = generate_schedule(loan_data, today_date)
    if metrics is None:
        metrics = calculate_metrics(loan_data, schedule, today_date)

    # Phase label
    if metrics.currentPhase == "moratorium":
        moratorium_months = loan_data.loanDetails.moratoriumMonths
        # Count periods up to today to find current moratorium month
        past = [r for r in schedule if r.dueDate < today_date and r.phase == "moratorium"]
        current_month = len(past) + 1
        phase_label = f"Moratorium ({current_month} of {moratorium_months} months)"
    else:
        phase_label = "EMI"

    # Closure month label
    closure_date = fmt_date(metrics.projectedClosureDate) if metrics.projectedClosureDate else "—"

    # EMI start label (first EMI-phase row)
    emi_start = ""
    for row in schedule:
        if row.phase == "emi":
            emi_start = _month_label(row.dueDate)
            break

    # OD Waterfall
    sorted_od = sorted(loan_data.odBalanceLog, key=lambda x: x.date)
    latest_od_balance = sorted_od[-1].balance if sorted_od else 0.0
    emi_reserve = od_data.emiReserve
    allocatable = latest_od_balance - emi_reserve
    allocated = sum(g.allocatedAmount for g in od_data.goals if g.isActive)
    over_allocated = allocated - allocatable

    # Next due label
    next_due = (
        f"{fmt_date(metrics.nextDueDate)} · {fmt_inr(metrics.nextInstallmentAmount)}"
        if metrics.nextDueDate else "—"
    )

    # Projected EMI label
    proj_emi_label = fmt_inr(metrics.projectedEmi)
    if emi_start:
        proj_emi_label += f" (from {emi_start})"

    lines = [
        f"## 📊 LoanLens Summary — {fmt_date(today_date)}",
        "",
        f"**Phase:** {phase_label}",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Outstanding Principal | {fmt_inr(metrics.outstandingPrincipal)} |",
        f"| OD Balance | {fmt_inr(latest_od_balance)} |",
        f"| Effective Principal | {fmt_inr(metrics.effectivePrincipal)} |",
        f"| Effective Rate | {fmt_pct(metrics.effectiveInterestRate, 2)} |",
        f"| Next Due | {next_due} |",
        f"| Projected EMI | {proj_emi_label} |",
        f"| Projected Closure | {closure_date} |",
        "",
        "**Interest:**",
        "| | Amount |",
        "|---|---|",
        f"| Paid to Date | {fmt_inr(metrics.interestPaidToDate)} |",
        f"| Saved to Date | {fmt_inr(metrics.interestSavedTillNow)} |",
        f"| Saved This Year | {fmt_inr(metrics.interestSavedThisYear)} |",
        f"| Total Projected | {fmt_inr(metrics.totalInterestProjected)} |",
        "",
        "**OD Waterfall:**",
        "| | Amount |",
        "|---|---|",
        f"| OD Balance | {fmt_inr(latest_od_balance)} |",
        f"| EMI Reserve | {fmt_inr(emi_reserve)} |",
        f"| Allocatable | {fmt_inr(max(0, allocatable))} |",
        f"| Allocated to Goals | {fmt_inr(allocated)} |",
    ]

    if over_allocated > 0:
        lines.append(f"| ⚠️ Over-allocated | {fmt_inr(over_allocated)} |")
    else:
        lines.append(f"| ✅ Unallocated | {fmt_inr(-over_allocated)} |")

    pct_disbursed = (
        (metrics.disbursedAmount / metrics.sanctionedAmount * 100)
        if metrics.sanctionedAmount > 0 else 0
    )
    lines.append("")
    lines.append(
        f"Disbursed: {fmt_inr(metrics.disbursedAmount)} / {fmt_inr(metrics.sanctionedAmount)} "
        f"({pct_disbursed:.1f}%)"
    )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# R2 — OD Savings Report
# ---------------------------------------------------------------------------

def render_od_savings(
    loan_data: LoanData,
    od_data: OdSavingsData,
    today_date: str,
    schedule: Optional[list[AmortizationRow]] = None,
    metrics: Optional[SummaryMetrics] = None,
) -> str:
    """
    R2: Render the OD Savings report.

    Token budget: ≤ 600 tokens.
    """
    if schedule is None:
        schedule = generate_schedule(loan_data, today_date)
    if metrics is None:
        metrics = calculate_metrics(loan_data, schedule, today_date)

    active_goals = [g for g in od_data.goals if g.isActive]
    met_goals = sum(1 for g in active_goals if g.allocatedAmount >= g.targetAmount)
    unmet_goals = len(active_goals) - met_goals

    # OD Waterfall values
    sorted_od = sorted(loan_data.odBalanceLog, key=lambda x: x.date)
    latest_od_balance = sorted_od[-1].balance if sorted_od else 0.0
    emi_reserve = od_data.emiReserve
    allocatable = latest_od_balance - emi_reserve
    allocated = sum(g.allocatedAmount for g in active_goals)
    over_allocated = allocated - allocatable

    # Build source name lookup
    source_map = {s.id: s.name for s in od_data.sources}

    lines = [
        f"## 💰 OD Savings — {fmt_date(today_date)}",
        "",
        "**OD Waterfall:**",
        "| | Amount |",
        "|---|---|",
        f"| OD Balance | {fmt_inr(latest_od_balance)} |",
        f"| EMI Reserve | {fmt_inr(emi_reserve)} |",
        f"| Allocatable | {fmt_inr(max(0, allocatable))} |",
        f"| Allocated | {fmt_inr(allocated)} |",
    ]

    if over_allocated > 0:
        lines.append(f"| ⚠️ Over-allocated | {fmt_inr(over_allocated)} |")
    else:
        lines.append(f"| ✅ Surplus | {fmt_inr(-over_allocated)} |")

    # Goals table
    lines += [
        "",
        f"**Goals ({len(active_goals)}):** 🟢 Met: {met_goals} · 🔴 Unmet: {unmet_goals}",
        "",
        "| Goal | Target | Allocated | Progress |",
        "|---|---|---|---|",
    ]

    for g in active_goals:
        pct = (g.allocatedAmount / g.targetAmount * 100) if g.targetAmount > 0 else 0
        check = " ✅" if g.allocatedAmount >= g.targetAmount else ""
        lines.append(
            f"| {g.name} | {fmt_inr(g.targetAmount)} | {fmt_inr(g.allocatedAmount)} | {pct:.0f}%{check} |"
        )

    # Recent contributions (last 5, sorted by date desc)
    sorted_contribs = sorted(od_data.contributions, key=lambda c: c.date, reverse=True)
    recent = sorted_contribs[:5]

    lines += [
        "",
        "**Recent Contributions:**",
        "| Date | Amount | Source |",
        "|---|---|---|",
    ]
    for c in recent:
        src_name = source_map.get(c.sourceId, c.sourceId)
        lines.append(f"| {fmt_date(c.date)} | {fmt_inr(c.amount)} | {src_name} |")

    if not recent:
        lines.append("| — | — | — |")

    # OD Balance Trend — last 6 months (use odBalanceLog)
    # Group contributions by month for deposited column
    contrib_by_month: dict[tuple[int, int], float] = {}
    for c in od_data.contributions:
        ym = _ym(c.date)
        contrib_by_month[ym] = contrib_by_month.get(ym, 0.0) + c.amount

    # Get up to last 6 OD balance log entries (sorted desc)
    sorted_od_desc = sorted(loan_data.odBalanceLog, key=lambda x: x.date, reverse=True)
    last_6 = sorted_od_desc[:6]

    lines += [
        "",
        "**OD Balance Trend (last 6 months):**",
        "| Month | Balance | Deposited |",
        "|---|---|---|",
    ]
    for log in last_6:
        ym = _ym(log.date)
        deposited = contrib_by_month.get(ym, 0.0)
        lines.append(
            f"| {_month_label(log.date)} | {fmt_inr(log.balance)} | {fmt_inr(deposited)} |"
        )

    if not last_6:
        lines.append("| — | — | — |")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# R3 — Schedule Report (Windowed)
# ---------------------------------------------------------------------------

def render_schedule(
    loan_data: LoanData,
    today_date: str,
    window: int = 6,
    schedule: Optional[list[AmortizationRow]] = None,
) -> str:
    """
    R3: Render the windowed amortization schedule report.

    Shows next ``window`` installments, yearly summary, and closure line.
    Token budget: ≤ 800 tokens.
    """
    if schedule is None:
        schedule = generate_schedule(loan_data, today_date)

    # Next N upcoming rows
    upcoming = [r for r in schedule if r.dueDate >= today_date][:window]

    lines = [
        f"## 📅 Amortization Schedule — {fmt_date(today_date)}",
        "",
        f"**Next {window} Installments:**",
        "| # | Due Date | Opening | Installment | Interest | Principal | Closing | Savings |",
        "|---|---|---|---|---|---|---|---|",
    ]

    for row in upcoming:
        lines.append(
            f"| {row.period} | {fmt_date(row.dueDate)} "
            f"| {fmt_inr(row.openingBalance)} "
            f"| {fmt_inr(row.installment)} "
            f"| {fmt_inr(row.interest)} "
            f"| {fmt_inr(row.principal)} "
            f"| {fmt_inr(row.closingBalance)} "
            f"| {fmt_inr(row.interestSavings)} |"
        )

    if not upcoming:
        lines.append("| — | — | — | — | — | — | — | — |")

    # Yearly rollup
    yearly: dict[int, dict[str, float]] = {}
    for row in schedule:
        yr = int(row.dueDate[:4])
        if yr not in yearly:
            yearly[yr] = {"interest": 0.0, "principal": 0.0, "closing": 0.0}
        yearly[yr]["interest"] += row.interest
        yearly[yr]["principal"] += row.principal
        yearly[yr]["closing"] = row.closingBalance  # last in year wins

    lines += [
        "",
        "**Yearly Summary:**",
        "| Year | Total Interest | Total Principal | Year-End Balance |",
        "|---|---|---|---|",
    ]
    for yr in sorted(yearly):
        y = yearly[yr]
        lines.append(
            f"| {yr} | {fmt_inr(y['interest'])} | {fmt_inr(y['principal'])} | {fmt_inr(y['closing'])} |"
        )

    # Closure line
    if schedule:
        last = schedule[-1]
        total_interest = sum(r.interest for r in schedule)
        total_savings = sum(r.interestSavings for r in schedule)
        lines += [
            "",
            f"**Closure:** Period {last.period} · {fmt_date(last.dueDate)} "
            f"· Total Interest: {fmt_inr(total_interest)} · Total OD Savings: {fmt_inr(total_savings)}",
        ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# R4 — Simulator Report
# ---------------------------------------------------------------------------

def render_simulator(
    base_loan: LoanData,
    sim_loan: LoanData,
    today_date: str,
    scenario_description: str,
    window: int = 6,
    base_schedule: Optional[list[AmortizationRow]] = None,
    sim_schedule: Optional[list[AmortizationRow]] = None,
) -> str:
    """
    R4: Render a simulator comparison report (base vs. simulated).

    Token budget: ≤ 600 tokens.
    """
    if base_schedule is None:
        base_schedule = generate_schedule(base_loan, today_date)
    if sim_schedule is None:
        sim_schedule = generate_schedule(sim_loan, today_date)

    base_metrics = calculate_metrics(base_loan, base_schedule, today_date)
    sim_metrics = calculate_metrics(sim_loan, sim_schedule, today_date)

    # Tenure change
    base_periods = len(base_schedule)
    sim_periods = len(sim_schedule)
    tenure_delta = sim_periods - base_periods
    tenure_label = (
        f"{abs(tenure_delta)} months {'later' if tenure_delta > 0 else 'earlier'}"
        if tenure_delta != 0 else "no change"
    )

    interest_delta = sim_metrics.totalInterestProjected - base_metrics.totalInterestProjected
    interest_label = (
        f"-{fmt_inr(-interest_delta)} saved"
        if interest_delta < 0 else f"+{fmt_inr(interest_delta)} extra"
    )

    lines = [
        f"## 🔬 Simulator — {fmt_date(today_date)}",
        "",
        f"**Scenario:** {scenario_description}",
        "",
        "| Metric | Base | Simulated | Δ |",
        "|---|---|---|---|",
        f"| Outstanding Principal | {fmt_inr(base_metrics.outstandingPrincipal)} "
        f"| {fmt_inr(sim_metrics.outstandingPrincipal)} "
        f"| {fmt_inr(sim_metrics.outstandingPrincipal - base_metrics.outstandingPrincipal)} |",
        f"| Total Interest | {fmt_inr(base_metrics.totalInterestProjected)} "
        f"| {fmt_inr(sim_metrics.totalInterestProjected)} "
        f"| {interest_label} |",
        f"| Projected Closure | {fmt_date(base_metrics.projectedClosureDate)} "
        f"| {fmt_date(sim_metrics.projectedClosureDate)} "
        f"| {tenure_label} |",
        f"| Projected EMI | {fmt_inr(base_metrics.projectedEmi)} "
        f"| {fmt_inr(sim_metrics.projectedEmi)} "
        f"| {fmt_inr(sim_metrics.projectedEmi - base_metrics.projectedEmi)} |",
    ]

    # Next window installments comparison (side by side)
    base_upcoming = [r for r in base_schedule if r.dueDate >= today_date][:window]
    sim_upcoming = [r for r in sim_schedule if r.dueDate >= today_date][:window]

    lines += [
        "",
        f"**Next {window} Installments — Base vs Simulated:**",
        "| # | Date | Base Installment | Sim Installment | Δ Interest |",
        "|---|---|---|---|---|",
    ]

    max_rows = max(len(base_upcoming), len(sim_upcoming))
    for i in range(max_rows):
        br = base_upcoming[i] if i < len(base_upcoming) else None
        sr = sim_upcoming[i] if i < len(sim_upcoming) else None
        period = br.period if br else (sr.period if sr else "—")
        date = fmt_date(br.dueDate if br else (sr.dueDate if sr else "—"))
        base_inst = fmt_inr(br.installment) if br else "—"
        sim_inst = fmt_inr(sr.installment) if sr else "—"
        delta_int = (
            fmt_inr(sr.interest - br.interest)
            if (br and sr) else "—"
        )
        lines.append(f"| {period} | {date} | {base_inst} | {sim_inst} | {delta_int} |")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# R5 — Ledger Report
# ---------------------------------------------------------------------------

def render_ledger(
    loan_data: LoanData,
    od_data: OdSavingsData,
    today_date: str,
) -> str:
    """
    R5: Render the Ledger report (disbursements, payments, OD balance history).

    Token budget: ≤ 500 tokens.
    """
    source_map = {s.id: s.name for s in od_data.sources}
    annotation_map = {
        a.odBalanceLogId: a for a in od_data.odBalanceAnnotations
    }

    # Disbursements
    sorted_disb = sorted(loan_data.disbursements, key=lambda d: d.date)

    lines = [
        f"## 📒 Ledger — {fmt_date(today_date)}",
        "",
        "**Disbursements:**",
        "| Date | Amount | Note |",
        "|---|---|---|",
    ]
    for d in sorted_disb:
        lines.append(f"| {fmt_date(d.date)} | {fmt_inr(d.amount)} | {d.note or '—'} |")

    total_disb = sum(d.amount for d in sorted_disb)
    lines.append(f"| **Total** | **{fmt_inr(total_disb)}** | |")

    # Payments
    sorted_pay = sorted(loan_data.paymentLog, key=lambda p: p.dueDate)

    lines += [
        "",
        "**Payments:**",
        "| Due Date | Type | Amount Due | Amount Paid |",
        "|---|---|---|---|",
    ]
    for p in sorted_pay:
        p_type = "Pre-EMI Interest" if p.type == "pre_emi_interest" else "EMI"
        lines.append(
            f"| {fmt_date(p.dueDate)} | {p_type} | {fmt_inr(p.amountDue)} | {fmt_inr(p.amountPaid)} |"
        )

    if not sorted_pay:
        lines.append("| — | — | — | — |")

    # OD Balance history
    sorted_od = sorted(loan_data.odBalanceLog, key=lambda x: x.date, reverse=True)

    lines += [
        "",
        "**OD Balance History:**",
        "| Date | Balance | Purpose | Note |",
        "|---|---|---|---|",
    ]
    for log in sorted_od[:12]:  # Show last 12 entries max
        ann = annotation_map.get(log.id)
        purpose = ann.purpose if ann else "—"
        note = ann.note if ann else "—"
        lines.append(
            f"| {fmt_date(log.date)} | {fmt_inr(log.balance)} | {purpose} | {note} |"
        )

    if not sorted_od:
        lines.append("| — | — | — | — |")

    return "\n".join(lines)
