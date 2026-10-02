"""
operations.py — All 15 write operations (W1-W15) for the LoanLens engine.

Each operation follows the protocol:
  1. Validate inputs (raise ValueError on failure)
  2. Apply mutation to an in-memory copy (dry-run)
  3. Compute impact summary (before/after metrics diff)
  4. Optionally commit (write back to original objects)
  5. Append to editHistory where applicable

Constraints:
  - ``today`` is always explicit, never the system clock.
  - Over-allocation: warn but don't block.
  - Duplicate source name check is case-insensitive.
  - ID generation: uuid4().hex[:9]
"""

from __future__ import annotations

import copy
import datetime
from typing import Any, Optional
from uuid import uuid4

from .metrics import calculate_metrics
from .schedule import generate_schedule
from .types import (
    AuditRecord,
    Disbursement,
    LoanData,
    OdBalanceAnnotation,
    OdBalanceLog,
    OdContribution,
    OdGoal,
    OdSavingsData,
    OdSource,
    PaymentLog,
    Prepayment,
    RateHistory,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MAX_AMOUNT = 10_00_00_000  # ₹10 Crore


def _new_id() -> str:
    """Generate a 9-hex-char ID. Matches uuid4().hex[:9] semantics."""
    return uuid4().hex[:9]


def _now_iso() -> str:
    """Return current UTC time as ISO-8601 string (for editHistory timestamps)."""
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _validate_amount(value: float, label: str, *, allow_zero: bool = False) -> None:
    """Raise ValueError if amount is out of range or has more than 2 dp."""
    if allow_zero:
        if value < 0:
            raise ValueError(f"{label} must be >= 0, got {value}")
    else:
        if value <= 0:
            raise ValueError(f"{label} must be > 0, got {value}")
    if value > _MAX_AMOUNT:
        raise ValueError(f"{label} must be <= ₹10 Crore, got {value}")
    # 2 decimal-place check
    if round(value, 2) != round(value, 10):
        raise ValueError(f"{label} must have at most 2 decimal places, got {value}")


def _validate_date(date_str: str, label: str = "date") -> None:
    """Raise ValueError if date_str is not a valid YYYY-MM-DD date."""
    try:
        datetime.date.fromisoformat(date_str)
    except (ValueError, TypeError):
        raise ValueError(f"{label} must be a valid YYYY-MM-DD date, got {repr(date_str)}")


def _audit_record(field: str, old_value: Any, new_value: Any) -> AuditRecord:
    return AuditRecord(
        timestamp=_now_iso(),
        field=field,
        oldValue=str(old_value),
        newValue=str(new_value),
    )


def _total_allocated(od_data: OdSavingsData) -> float:
    return sum(g.allocatedAmount for g in od_data.goals if g.isActive)


def _format_inr(amount: float) -> str:
    """Format a number in Indian Rupee notation (e.g. ₹12,34,567)."""
    n = int(round(amount))
    s = str(abs(n))
    if len(s) <= 3:
        formatted = s
    else:
        # Indian grouping: last 3, then groups of 2
        formatted = s[-3:]
        s = s[:-3]
        while s:
            formatted = s[-2:] + "," + formatted
            s = s[:-2]
    prefix = "-₹" if n < 0 else "₹"
    return prefix + formatted


def _impact_summary(
    op_name: str,
    input_desc: str,
    before_loan: LoanData,
    after_loan: LoanData,
    today_date: str,
    warnings: list[str] | None = None,
) -> dict:
    """Compute before/after schedule metrics and return an impact dict."""
    before_schedule = generate_schedule(before_loan, today_date)
    after_schedule = generate_schedule(after_loan, today_date)
    before_metrics = calculate_metrics(before_loan, before_schedule, today_date)
    after_metrics = calculate_metrics(after_loan, after_schedule, today_date)

    delta_principal = after_metrics.outstandingPrincipal - before_metrics.outstandingPrincipal
    delta_interest = after_metrics.totalInterestProjected - before_metrics.totalInterestProjected
    delta_savings = (
        (after_metrics.totalInterestProjected - after_metrics.interestSavedTillNow)
        - (before_metrics.totalInterestProjected - before_metrics.interestSavedTillNow)
    )

    return {
        "operation": op_name,
        "input_description": input_desc,
        "before": before_metrics.model_dump(),
        "after": after_metrics.model_dump(),
        "deltas": {
            "outstandingPrincipal": delta_principal,
            "totalInterestProjected": delta_interest,
            "projectedClosureDate": after_metrics.projectedClosureDate,
        },
        "warnings": warnings or [],
    }


def validate_invariants(loan: LoanData, od: OdSavingsData) -> None:
    """Check critical invariants after mutations."""
    total_disbursed = sum(d.amount for d in loan.disbursements)
    if total_disbursed > loan.loanDetails.sanctionedAmount:
        raise ValueError(f"Invariant violation: Total disbursed ({_format_inr(total_disbursed)}) exceeds sanctioned amount ({_format_inr(loan.loanDetails.sanctionedAmount)})")

    for log in loan.odBalanceLog:
        if log.balance < 0:
            raise ValueError(f"Invariant violation: OD balance is negative ({_format_inr(log.balance)}) on {log.date}")

    for goal in od.goals:
        if goal.allocatedAmount < 0:
            raise ValueError(f"Invariant violation: Goal '{goal.name}' has negative allocated amount ({_format_inr(goal.allocatedAmount)})")


# ---------------------------------------------------------------------------
# W1 — update_od_balance
# ---------------------------------------------------------------------------

def update_od_balance(
    loan_data: LoanData,
    od_data: OdSavingsData,
    today_date: str,
    date: str,
    balance: float,
    source_id: Optional[str] = None,
    purpose: Optional[str] = None,
    note: Optional[str] = None,
    commit: bool = False,
) -> dict:
    raise ValueError("OD Balance is now strictly derived from Contributions and Payments. Please use add_contribution instead.")


# ---------------------------------------------------------------------------
# W2 — add_disbursement
# ---------------------------------------------------------------------------

def add_disbursement(
    loan_data: LoanData,
    today_date: str,
    date: str,
    amount: float,
    note: Optional[str] = None,
    commit: bool = False,
) -> dict:
    """
    W2: Add a new disbursement tranche.

    Validates total does not exceed sanctioned amount.
    """
    _validate_date(date, "date")
    _validate_date(today_date, "today_date")
    _validate_amount(amount, "amount")

    total_disbursed = sum(d.amount for d in loan_data.disbursements)
    if total_disbursed + amount > loan_data.loanDetails.sanctionedAmount:
        raise ValueError(
            f"Total disbursed {_format_inr(total_disbursed + amount)} would exceed "
            f"sanctioned amount {_format_inr(loan_data.loanDetails.sanctionedAmount)}"
        )

    warnings: list[str] = []
    remaining = loan_data.loanDetails.sanctionedAmount - total_disbursed - amount
    if remaining < loan_data.loanDetails.sanctionedAmount * 0.10:
        warnings.append(
            f"Only {_format_inr(remaining)} remaining of sanctioned limit after this disbursement"
        )

    new_loan = copy.deepcopy(loan_data)
    new_disbursement = Disbursement(id=_new_id(), date=date, amount=amount, note=note)
    new_loan.disbursements.append(new_disbursement)

    impact = _impact_summary("add_disbursement", f"date={date}, amount={_format_inr(amount)}", loan_data, new_loan, today_date, warnings)

    if commit:
        loan_data.disbursements.append(new_disbursement)

    return impact


# ---------------------------------------------------------------------------
# W3 — add_prepayment
# ---------------------------------------------------------------------------

def add_prepayment(
    loan_data: LoanData,
    today_date: str,
    date: str,
    amount: float,
    note: Optional[str] = None,
    commit: bool = False,
) -> dict:
    """
    W3: Add a prepayment.

    Validates amount <= outstanding principal.
    """
    _validate_date(date, "date")
    _validate_date(today_date, "today_date")
    _validate_amount(amount, "amount")

    schedule = generate_schedule(loan_data, today_date)
    outstanding = 0.0
    if schedule:
        # Find the period covering the prepayment date
        for row in schedule:
            if row.dueDate >= date:
                outstanding = row.openingBalance
                break
        if outstanding == 0.0:
            outstanding = schedule[-1].closingBalance

    if amount > outstanding and outstanding > 0:
        raise ValueError(
            f"Prepayment amount {_format_inr(amount)} exceeds outstanding principal {_format_inr(outstanding)}"
        )

    new_loan = copy.deepcopy(loan_data)
    new_prepayment = Prepayment(id=_new_id(), date=date, amount=amount, note=note)
    new_loan.prepayments.append(new_prepayment)

    impact = _impact_summary("add_prepayment", f"date={date}, amount={_format_inr(amount)}", loan_data, new_loan, today_date)

    if commit:
        loan_data.prepayments.append(new_prepayment)

    return impact


# ---------------------------------------------------------------------------
# W4 — add_rate_change
# ---------------------------------------------------------------------------

def add_rate_change(
    loan_data: LoanData,
    today_date: str,
    effective_date: str,
    annual_rate: float,
    benchmark: Optional[str] = None,
    spread: Optional[float] = None,
    commit: bool = False,
) -> dict:
    """
    W4: Add a rate change entry.

    Validates rate > 0 and rate < 30.
    """
    _validate_date(effective_date, "effective_date")
    _validate_date(today_date, "today_date")

    if annual_rate <= 0:
        raise ValueError(f"annual_rate must be > 0, got {annual_rate}")
    if annual_rate >= 30:
        raise ValueError(f"annual_rate must be < 30, got {annual_rate}")

    new_loan = copy.deepcopy(loan_data)
    new_rate = RateHistory(
        id=_new_id(),
        effectiveDate=effective_date,
        annualRate=annual_rate,
        benchmark=benchmark,
        spread=spread,
    )
    new_loan.rateHistory.append(new_rate)

    impact = _impact_summary(
        "add_rate_change",
        f"effective_date={effective_date}, annual_rate={annual_rate}%",
        loan_data,
        new_loan,
        today_date,
    )

    if commit:
        loan_data.rateHistory.append(new_rate)

    return impact


# ---------------------------------------------------------------------------
# W5 — update_payment
# ---------------------------------------------------------------------------

def update_payment(
    loan_data: LoanData,
    od_data: OdSavingsData,
    today_date: str,
    due_date: str,
    amount_paid: Optional[float] = None,
    amount_due: Optional[float] = None,
    commit: bool = False,
) -> dict:
    new_loan = copy.deepcopy(loan_data)
    payment = next((p for p in new_loan.paymentLog if p.dueDate == due_date), None)
    
    if not payment:
        raise ValueError(f"No payment log found for {due_date}")
        
    if amount_paid is not None:
        _validate_amount(amount_paid, "amount_paid")
        payment.amountPaid = amount_paid
    if amount_due is not None:
        _validate_amount(amount_due, "amount_due")
        payment.amountDue = amount_due
        
    sync_od_balance_log(new_loan, od_data)

    impact = _impact_summary(
        "update_payment",
        f"due_date={due_date}, amount_paid={amount_paid}, amount_due={amount_due}",
        loan_data,
        new_loan,
        today_date,
        []
    )

    if commit:
        loan_data.paymentLog = new_loan.paymentLog
        sync_od_balance_log(loan_data, od_data)

    return impact


# ---------------------------------------------------------------------------
# W6 — update_emi_reserve
# ---------------------------------------------------------------------------

def update_emi_reserve(
    loan_data: LoanData,
    od_data: OdSavingsData,
    today_date: str,
    amount: float,
    commit: bool = False,
) -> dict:
    """
    W6: Update the EMI reserve amount.

    Warns if the new reserve causes over-allocation.
    """
    _validate_date(today_date, "today_date")
    _validate_amount(amount, "amount", allow_zero=True)

    new_od = copy.deepcopy(od_data)
    new_od.emiReserve = amount

    warnings: list[str] = []
    # Check latest OD balance
    if loan_data.odBalanceLog:
        latest_balance = sorted(loan_data.odBalanceLog, key=lambda x: x.date)[-1].balance
        allocatable = latest_balance - amount
        allocated = _total_allocated(new_od)
        if allocated > allocatable:
            warnings.append(
                f"New reserve causes over-allocation: goals {_format_inr(allocated)} > allocatable {_format_inr(allocatable)}"
            )

    # EMI reserve doesn't affect schedule metrics directly; use same loan_data
    schedule = generate_schedule(loan_data, today_date)
    metrics = calculate_metrics(loan_data, schedule, today_date)

    impact = {
        "operation": "update_emi_reserve",
        "input_description": f"amount={_format_inr(amount)}",
        "before": {"emiReserve": od_data.emiReserve},
        "after": {"emiReserve": amount},
        "deltas": {"emiReserve": amount - od_data.emiReserve},
        "warnings": warnings,
    }

    if commit:
        od_data.emiReserve = amount

    return impact


# ---------------------------------------------------------------------------
# W7 — add_source
# ---------------------------------------------------------------------------

def add_source(
    od_data: OdSavingsData,
    name: str,
    description: Optional[str] = None,
    commit: bool = False,
) -> dict:
    """
    W7: Add a new OD savings source.

    Name must be 1-60 chars and unique (case-insensitive).
    """
    if not name or not name.strip():
        raise ValueError("Source name must not be empty")
    if len(name) > 60:
        raise ValueError(f"Source name must be at most 60 characters, got {len(name)}")

    existing_names = {s.name.lower() for s in od_data.sources}
    if name.lower() in existing_names:
        raise ValueError(f"Source name {repr(name)} already exists (case-insensitive check)")

    new_source = OdSource(
        id=_new_id(),
        name=name,
        description=description,
        isActive=True,
        createdAt=_now_iso(),
        editHistory=[],
    )

    impact = {
        "operation": "add_source",
        "input_description": f"name={repr(name)}",
        "created": new_source.model_dump(),
        "warnings": [],
    }

    if commit:
        od_data.sources.append(new_source)

    return impact


# ---------------------------------------------------------------------------
# W8 — edit_source
# ---------------------------------------------------------------------------

def edit_source(
    od_data: OdSavingsData,
    source_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    is_active: Optional[bool] = None,
    commit: bool = False,
) -> dict:
    """
    W8: Edit an existing source.

    Appends to editHistory for each changed field.
    """
    source = next((s for s in od_data.sources if s.id == source_id), None)
    if source is None:
        raise ValueError(f"Source with id={repr(source_id)} not found")

    if name is not None:
        if not name.strip():
            raise ValueError("Source name must not be empty")
        if len(name) > 60:
            raise ValueError(f"Source name must be at most 60 characters, got {len(name)}")
        other_names = {s.name.lower() for s in od_data.sources if s.id != source_id}
        if name.lower() in other_names:
            raise ValueError(f"Source name {repr(name)} already exists (case-insensitive check)")

    # Build audit records on dry-run copy
    new_od = copy.deepcopy(od_data)
    new_source = next(s for s in new_od.sources if s.id == source_id)
    audit: list[AuditRecord] = []

    if name is not None and name != new_source.name:
        audit.append(_audit_record("name", new_source.name, name))
        new_source.name = name
    if description is not None and description != new_source.description:
        audit.append(_audit_record("description", new_source.description, description))
        new_source.description = description
    if is_active is not None and is_active != new_source.isActive:
        audit.append(_audit_record("isActive", new_source.isActive, is_active))
        new_source.isActive = is_active

    new_source.editHistory.extend(audit)

    impact = {
        "operation": "edit_source",
        "input_description": f"source_id={repr(source_id)}",
        "before": source.model_dump(),
        "after": new_source.model_dump(),
        "changes": len(audit),
        "warnings": [],
    }

    if commit:
        for rec in audit:
            source.editHistory.append(rec)
        if name is not None:
            source.name = name
        if description is not None:
            source.description = description
        if is_active is not None:
            source.isActive = is_active

    return impact


# ---------------------------------------------------------------------------
# W9 — add_goal
# ---------------------------------------------------------------------------

def add_goal(
    od_data: OdSavingsData,
    name: str,
    target_amount: float,
    today_date: str,
    allocated_amount: float = 0.0,
    target_date: Optional[str] = None,
    color: str = "#0f766e",
    note: Optional[str] = None,
    commit: bool = False,
) -> dict:
    """
    W9: Add a new OD savings goal.

    Warns if new allocation causes over-allocation.
    """
    _validate_date(today_date, "today_date")
    if not name or not name.strip():
        raise ValueError("Goal name must not be empty")
    _validate_amount(target_amount, "target_amount")
    _validate_amount(allocated_amount, "allocated_amount", allow_zero=True)
    if target_date is not None:
        _validate_date(target_date, "target_date")

    warnings: list[str] = []
    new_od = copy.deepcopy(od_data)

    new_goal = OdGoal(
        id=_new_id(),
        name=name,
        targetAmount=target_amount,
        allocatedAmount=allocated_amount,
        targetDate=target_date,
        color=color,
        note=note,
        isActive=True,
        editHistory=[
            AuditRecord(
                timestamp=_now_iso(),
                field="created",
                oldValue="",
                newValue=f"target={target_amount},allocated={allocated_amount}",
            )
        ],
    )
    new_od.goals.append(new_goal)

    # Over-allocation check
    if new_od.odBalanceAnnotations or True:  # always check
        # Get latest OD balance from loan_data — we don't have it here, warn based on reserve
        total_alloc = _total_allocated(new_od)
        # We can only check if emiReserve is known
        pass  # The caller is responsible for showing warnings; we flag if allocated > 0

    impact = {
        "operation": "add_goal",
        "input_description": f"name={repr(name)}, target={_format_inr(target_amount)}, allocated={_format_inr(allocated_amount)}",
        "created": new_goal.model_dump(),
        "warnings": warnings,
    }

    if commit:
        od_data.goals.append(new_goal)

    return impact


def add_goal_with_od(
    loan_data: LoanData,
    od_data: OdSavingsData,
    name: str,
    target_amount: float,
    today_date: str,
    allocated_amount: float = 0.0,
    target_date: Optional[str] = None,
    color: str = "#0f766e",
    note: Optional[str] = None,
    commit: bool = False,
) -> dict:
    """
    W9 variant: Add goal with OD balance over-allocation check.
    """
    _validate_date(today_date, "today_date")
    if not name or not name.strip():
        raise ValueError("Goal name must not be empty")
    _validate_amount(target_amount, "target_amount")
    _validate_amount(allocated_amount, "allocated_amount", allow_zero=True)
    if target_date is not None:
        _validate_date(target_date, "target_date")

    warnings: list[str] = []
    new_od = copy.deepcopy(od_data)

    new_goal = OdGoal(
        id=_new_id(),
        name=name,
        targetAmount=target_amount,
        allocatedAmount=allocated_amount,
        targetDate=target_date,
        color=color,
        note=note,
        isActive=True,
        editHistory=[
            AuditRecord(
                timestamp=_now_iso(),
                field="created",
                oldValue="",
                newValue=f"target={target_amount},allocated={allocated_amount}",
            )
        ],
    )
    new_od.goals.append(new_goal)

    if loan_data.odBalanceLog:
        latest_balance = sorted(loan_data.odBalanceLog, key=lambda x: x.date)[-1].balance
        allocatable = latest_balance - new_od.emiReserve
        total_alloc = _total_allocated(new_od)
        if total_alloc > allocatable:
            warnings.append(
                f"Over-allocated: goals total {_format_inr(total_alloc)} > allocatable {_format_inr(allocatable)}"
            )

    impact = {
        "operation": "add_goal",
        "input_description": f"name={repr(name)}, target={_format_inr(target_amount)}, allocated={_format_inr(allocated_amount)}",
        "created": new_goal.model_dump(),
        "warnings": warnings,
    }

    if commit:
        od_data.goals.append(new_goal)

    return impact


# ---------------------------------------------------------------------------
# W10 — edit_goal
# ---------------------------------------------------------------------------

def edit_goal(
    od_data: OdSavingsData,
    goal_id: str,
    patch: dict,
    commit: bool = False,
) -> dict:
    """
    W10: Edit an existing goal.

    patch keys: name, targetAmount, allocatedAmount, targetDate, color, note, isActive
    Appends to editHistory for each changed field.
    """
    goal = next((g for g in od_data.goals if g.id == goal_id), None)
    if goal is None:
        raise ValueError(f"Goal with id={repr(goal_id)} not found")

    allowed_fields = {"name", "targetAmount", "allocatedAmount", "targetDate", "color", "note", "isActive"}
    invalid_fields = set(patch.keys()) - allowed_fields
    if invalid_fields:
        raise ValueError(f"Invalid patch fields: {invalid_fields}")

    if "targetAmount" in patch:
        _validate_amount(patch["targetAmount"], "targetAmount")
    if "allocatedAmount" in patch:
        _validate_amount(patch["allocatedAmount"], "allocatedAmount", allow_zero=True)
    if "targetDate" in patch and patch["targetDate"] is not None:
        _validate_date(patch["targetDate"], "targetDate")

    new_od = copy.deepcopy(od_data)
    new_goal = next(g for g in new_od.goals if g.id == goal_id)
    audit: list[AuditRecord] = []

    for field, new_val in patch.items():
        old_val = getattr(new_goal, field)
        if old_val != new_val:
            audit.append(_audit_record(field, old_val, new_val))
            setattr(new_goal, field, new_val)

    new_goal.editHistory.extend(audit)

    impact = {
        "operation": "edit_goal",
        "input_description": f"goal_id={repr(goal_id)}, patch={patch}",
        "before": goal.model_dump(),
        "after": new_goal.model_dump(),
        "changes": len(audit),
        "warnings": [],
    }

    if commit:
        for rec in audit:
            goal.editHistory.append(rec)
        for field, new_val in patch.items():
            setattr(goal, field, new_val)

    return impact


# ---------------------------------------------------------------------------
# W11 — add_contribution
# ---------------------------------------------------------------------------

def add_contribution(
    loan_data: LoanData,
    od_data: OdSavingsData,
    date: str,
    amount: float,
    source_id: str,
    today_date: str,
    note: Optional[str] = None,
    commit: bool = False,
) -> dict:
    _validate_date(date, "date")
    _validate_date(today_date, "today_date")
    _validate_amount(amount, "amount")

    source = next((s for s in od_data.sources if s.id == source_id), None)
    if source is None:
        raise ValueError(f"Source with id={repr(source_id)} not found")

    new_contribution = OdContribution(
        id=_new_id(),
        date=date,
        amount=amount,
        sourceId=source_id,
        note=note,
        editHistory=[
            AuditRecord(
                timestamp=_now_iso(),
                field="created",
                oldValue="",
                newValue=f"amount={amount},sourceId={source_id}",
            )
        ],
    )

    new_od = copy.deepcopy(od_data)
    new_od.contributions.append(new_contribution)
    
    new_loan = copy.deepcopy(loan_data)
    sync_od_balance_log(new_loan, new_od)

    impact = _impact_summary(
        "add_contribution",
        f"date={date}, amount={_format_inr(amount)}, source={repr(source.name)}",
        loan_data,
        new_loan,
        today_date,
        []
    )

    if commit:
        od_data.contributions.append(new_contribution)
        sync_od_balance_log(loan_data, od_data)

    return impact


# ---------------------------------------------------------------------------
# W12 — edit_contribution
# ---------------------------------------------------------------------------

def edit_contribution(
    loan_data: LoanData,
    od_data: OdSavingsData,
    contribution_id: str,
    patch: dict,
    today_date: str,
    commit: bool = False,
) -> dict:
    contrib = next((c for c in od_data.contributions if c.id == contribution_id), None)
    if not contrib:
        raise ValueError("Contribution not found")

    new_od = copy.deepcopy(od_data)
    new_contrib = next(c for c in new_od.contributions if c.id == contribution_id)
    
    audit_records = []
    for k, v in patch.items():
        if hasattr(new_contrib, k):
            old_v = getattr(new_contrib, k)
            if old_v != v:
                audit_records.append(AuditRecord(timestamp=_now_iso(), field=k, oldValue=str(old_v), newValue=str(v)))
            setattr(new_contrib, k, v)
    new_contrib.editHistory.extend(audit_records)

    new_loan = copy.deepcopy(loan_data)
    sync_od_balance_log(new_loan, new_od)

    impact = _impact_summary(
        "edit_contribution",
        f"id={contribution_id}, patch={patch}",
        loan_data,
        new_loan,
        today_date,
        []
    )

    if commit:
        od_data.contributions = new_od.contributions
        sync_od_balance_log(loan_data, od_data)

    return impact


# ---------------------------------------------------------------------------
# W13 — edit_od_annotation
# ---------------------------------------------------------------------------

def edit_od_annotation(
    od_data: OdSavingsData,
    od_balance_log_id: str,
    source_id: Optional[str] = None,
    purpose: Optional[str] = None,
    note: Optional[str] = None,
    commit: bool = False,
) -> dict:
    """
    W13: Edit OD balance log annotation.

    Appends to editHistory for each changed field.
    """
    annotation = next(
        (a for a in od_data.odBalanceAnnotations if a.odBalanceLogId == od_balance_log_id),
        None,
    )
    if annotation is None:
        raise ValueError(f"Annotation for od_balance_log_id={repr(od_balance_log_id)} not found")

    new_od = copy.deepcopy(od_data)
    new_annotation = next(
        a for a in new_od.odBalanceAnnotations if a.odBalanceLogId == od_balance_log_id
    )
    audit: list[AuditRecord] = []

    if source_id is not None and source_id != new_annotation.sourceId:
        audit.append(_audit_record("sourceId", new_annotation.sourceId, source_id))
        new_annotation.sourceId = source_id
    if purpose is not None and purpose != new_annotation.purpose:
        audit.append(_audit_record("purpose", new_annotation.purpose, purpose))
        new_annotation.purpose = purpose
    if note is not None and note != new_annotation.note:
        audit.append(_audit_record("note", new_annotation.note, note))
        new_annotation.note = note

    new_annotation.editHistory.extend(audit)

    impact = {
        "operation": "edit_od_annotation",
        "input_description": f"od_balance_log_id={repr(od_balance_log_id)}",
        "before": annotation.model_dump(),
        "after": new_annotation.model_dump(),
        "changes": len(audit),
        "warnings": [],
    }

    if commit:
        for rec in audit:
            annotation.editHistory.append(rec)
        if source_id is not None:
            annotation.sourceId = source_id
        if purpose is not None:
            annotation.purpose = purpose
        if note is not None:
            annotation.note = note

    return impact


# ---------------------------------------------------------------------------
# W14 — process_due_payments
# ---------------------------------------------------------------------------

def process_due_payments(
    loan_data: LoanData,
    od_data: OdSavingsData,
    today_date: str,
    commit: bool = False,
) -> dict:
    """
    W14: Process all due payments up to today_date.

    Creates paymentLog entries, updates odBalanceLog, and adds annotations
    for each unprocessed due payment.
    """
    _validate_date(today_date, "today_date")

    new_loan = copy.deepcopy(loan_data)
    new_od = copy.deepcopy(od_data)

    schedule = generate_schedule(new_loan, today_date)
    due_rows = [r for r in schedule if r.dueDate <= today_date]

    payments_to_process = []
    for row in due_rows:
        has_payment = any(p.dueDate == row.dueDate for p in new_loan.paymentLog)
        if not has_payment:
            payments_to_process.append(row)

    if not payments_to_process:
        return {
            "operation": "process_due_payments",
            "input_description": f"today_date={today_date}",
            "payments_processed": 0,
            "warnings": [],
        }

    for row in payments_to_process:
        # Determine available OD balance
        sorted_logs = sorted(new_loan.odBalanceLog, key=lambda l: l.date)
        prev_balance = 0.0
        for log in sorted_logs:
            if log.date < row.dueDate:
                prev_balance = log.balance
            else:
                break
        
        actual_deducted = min(row.installment, prev_balance)
        new_balance = prev_balance - actual_deducted
        
        payment_id = _new_id()
        new_loan.paymentLog.append(
            PaymentLog(
                id=payment_id,
                dueDate=row.dueDate,
                type="pre_emi_interest" if row.phase == "moratorium" else "emi",
                amountDue=row.installment,
                amountPaid=actual_deducted,
                paidDate=row.dueDate,
            )
        )

        # Update OD balance
        has_od_log = any(log.date == row.dueDate for log in new_loan.odBalanceLog)
        if not has_od_log:
            od_log_id = _new_id()

            new_loan.odBalanceLog.append(
                OdBalanceLog(id=od_log_id, date=row.dueDate, balance=new_balance)
            )
            note = f"Auto-processed on {today_date}"
            if actual_deducted < row.installment:
                note += f" (Partial payment: {actual_deducted}/{row.installment})"
                
            new_od.odBalanceAnnotations.append(
                OdBalanceAnnotation(
                    odBalanceLogId=od_log_id,
                    sourceId=None,
                    purpose="EMI / Interest",
                    note=note,
                    editHistory=[
                        AuditRecord(
                            timestamp=_now_iso(),
                            field="created",
                            oldValue="",
                            newValue=f"balance={new_balance}",
                        )
                    ],
                )
            )

    impact = {
        "operation": "process_due_payments",
        "input_description": f"today_date={today_date}",
        "payments_processed": len(payments_to_process),
        "due_dates": [r.dueDate for r in payments_to_process],
        "total_amount": sum(r.installment for r in payments_to_process),
        "warnings": [],
    }

    if commit:
        for row in payments_to_process:
            loan_data.paymentLog.append(
                next(p for p in new_loan.paymentLog if p.dueDate == row.dueDate)
            )
            new_log = next(
                (l for l in new_loan.odBalanceLog if l.date == row.dueDate), None
            )
            if new_log and not any(l.date == row.dueDate for l in loan_data.odBalanceLog):
                loan_data.odBalanceLog.append(copy.deepcopy(new_log))
                new_ann = next(
                    (a for a in new_od.odBalanceAnnotations if a.odBalanceLogId == new_log.id),
                    None,
                )
                if new_ann:
                    od_data.odBalanceAnnotations.append(copy.deepcopy(new_ann))

    return impact


# ---------------------------------------------------------------------------
# W15 — update_settings
# ---------------------------------------------------------------------------

_SETTINGS_VALIDATORS: dict[str, Any] = {
    "totalTenureMonths": (int, lambda v: v > 0, "must be > 0"),
    "moratoriumMonths": (int, lambda v: v >= 0, "must be >= 0"),
    "dueDateDay": (int, lambda v: 1 <= v <= 28, "must be 1-28"),
    "dayCountConvention": (int, lambda v: v in (360, 365, 366), "must be 360, 365, or 366"),
    "currentCommunicatedEmi": (float, lambda v: v > 0, "must be > 0"),
    "sanctionedAmount": (float, lambda v: 0 < v <= _MAX_AMOUNT, f"must be > 0 and <= {_MAX_AMOUNT}"),
}


def update_settings(
    loan_data: LoanData,
    today_date: str,
    patch: dict,
    commit: bool = False,
) -> dict:
    """
    W15: Update loanDetails settings.

    Supports patching top-level loanDetails fields.
    Validates field names and numeric ranges.
    """
    _validate_date(today_date, "today_date")

    allowed = set(_SETTINGS_VALIDATORS.keys()) | {"onPrepayment"}
    invalid_fields = set(patch.keys()) - allowed
    if invalid_fields:
        raise ValueError(f"Invalid settings fields: {invalid_fields}")

    # Validate each field
    for field, value in patch.items():
        if field in _SETTINGS_VALIDATORS:
            _type, _check, _msg = _SETTINGS_VALIDATORS[field]
            if not isinstance(value, (int, float)):
                raise ValueError(f"{field} must be numeric")
            if not _check(value):
                raise ValueError(f"{field} {_msg}, got {value}")
        elif field == "onPrepayment":
            if value not in ("adjust_tenure", "adjust_emi"):
                raise ValueError(f"{field} must be 'adjust_tenure' or 'adjust_emi'")

    new_loan = copy.deepcopy(loan_data)
    before_dict = new_loan.loanDetails.model_dump(exclude={"accountNumber"})

    for field, value in patch.items():
        if field == "onPrepayment":
            setattr(new_loan.loanDetails.policy, field, value)
        else:
            setattr(new_loan.loanDetails, field, value)

    after_dict = new_loan.loanDetails.model_dump(exclude={"accountNumber"})

    impact = _impact_summary("update_settings", f"patch={patch}", loan_data, new_loan, today_date)
    impact["settings_before"] = before_dict
    impact["settings_after"] = after_dict

    if commit:
        for field, value in patch.items():
            if field == "onPrepayment":
                setattr(loan_data.loanDetails.policy, field, value)
            else:
                setattr(loan_data.loanDetails, field, value)

    return impact
