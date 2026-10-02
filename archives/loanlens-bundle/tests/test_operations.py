"""
test_operations.py — Unit tests for all 15 LoanLens write operations (W1-W15).

Each operation has at least 2 tests:
  - Happy path (valid inputs, correct mutation)
  - Validation failure (invalid inputs raise ValueError)

Total: ≥ 30 test functions.
"""

from __future__ import annotations

import copy
import pytest

from engine.types import (
    AuditRecord,
    Disbursement,
    LoanData,
    LoanDetails,
    OdBalanceAnnotation,
    OdBalanceLog,
    OdContribution,
    OdGoal,
    OdSavingsData,
    OdSource,
    PaymentLog,
    Policy,
    Prepayment,
    RateHistory,
)
from engine.operations import (
    add_contribution,
    add_disbursement,
    add_goal,
    add_goal_with_od,
    add_prepayment,
    add_rate_change,
    add_source,
    edit_contribution,
    edit_goal,
    edit_od_annotation,
    edit_source,
    process_due_payments,
    update_emi_reserve,
    update_od_balance,
    update_payment,
    update_settings,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

TODAY = "2026-09-26"


def _make_loan_data(
    extra_disbursements: list | None = None,
    extra_payments: list | None = None,
    extra_prepayments: list | None = None,
    extra_od_logs: list | None = None,
) -> LoanData:
    """Build a minimal but realistic LoanData for testing."""
    disbursements = [
        Disbursement(id="init-1", date="2026-01-31", amount=5_982_984, note="1st tranche"),
        Disbursement(id="init-2", date="2026-04-09", amount=1_480_816, note="2nd tranche"),
        Disbursement(id="init-3", date="2026-06-10", amount=2_051_200, note="3rd tranche"),
        Disbursement(id="init-4", date="2026-08-05", amount=2_000_000, note="4th tranche"),
    ]
    if extra_disbursements:
        disbursements.extend(extra_disbursements)

    od_logs = [
        OdBalanceLog(id="od-1", date="2026-06-10", balance=510_792),
        OdBalanceLog(id="od-2", date="2026-07-10", balance=750_000),
        OdBalanceLog(id="od-3", date="2026-09-10", balance=923_964),
    ]
    if extra_od_logs:
        od_logs.extend(extra_od_logs)

    payments = [
        PaymentLog(
            id="p1",
            dueDate="2026-02-10",
            type="pre_emi_interest",
            amountDue=38_000,
            amountPaid=38_000,
            paidDate="2026-02-10",
        ),
    ]
    if extra_payments:
        payments.extend(extra_payments)

    prepayments = list(extra_prepayments or [])

    return LoanData(
        loanDetails=LoanDetails(
            lender="Test Bank",
            accountNumber="REDACTED",
            sanctionedAmount=11_965_000,
            totalTenureMonths=300,
            moratoriumMonths=18,
            moratoriumAnchor="first_disbursement",
            dueDateDay=10,
            dayCountConvention=365,
            currentCommunicatedEmi=91_143,
            policy=Policy(
                onRateChange="adjust_tenure",
                onDisbursementDuringEmi="adjust_tenure",
                onPrepayment="adjust_tenure",
            ),
        ),
        disbursements=disbursements,
        rateHistory=[
            RateHistory(id="rate-1", effectiveDate="2026-01-31", annualRate=7.6, benchmark="RLLR"),
        ],
        odBalanceLog=od_logs,
        prepayments=prepayments,
        paymentLog=payments,
    )


def _make_od_data() -> OdSavingsData:
    """Build a minimal OdSavingsData for testing."""
    return OdSavingsData(
        emiReserve=91_143,
        sources=[
            OdSource(
                id="src-1",
                name="Aditya",
                description="From Salary",
                isActive=True,
                createdAt="2026-01-01T00:00:00Z",
                editHistory=[],
            ),
            OdSource(
                id="src-2",
                name="Neha",
                description="Salary",
                isActive=True,
                createdAt="2026-01-01T00:00:00Z",
                editHistory=[],
            ),
        ],
        contributions=[
            OdContribution(
                id="cont-1",
                date="2026-05-30",
                amount=198_000,
                sourceId="src-1",
                editHistory=[],
            ),
        ],
        goals=[
            OdGoal(
                id="goal-1",
                name="Emergency Fund",
                targetAmount=500_000,
                allocatedAmount=300_000,
                isActive=True,
                editHistory=[],
            ),
        ],
        odBalanceAnnotations=[
            OdBalanceAnnotation(
                odBalanceLogId="od-1",
                sourceId="src-1",
                purpose="savings",
                note="Initial deposit",
                editHistory=[],
            ),
        ],
    )


# ---------------------------------------------------------------------------
# W1 — update_od_balance
# ---------------------------------------------------------------------------


class TestUpdateOdBalance:
    def test_happy_path_dry_run(self):
        """W1: Dry-run creates impact dict without mutating original data."""
        loan = _make_loan_data()
        od = _make_od_data()
        original_count = len(loan.odBalanceLog)

        result = update_od_balance(
            loan, od, date="2026-09-26", balance=1_000_000.0, today_date=TODAY
        )

        assert result["operation"] == "update_od_balance"
        assert "before" in result
        assert "after" in result
        # Dry-run: original not mutated
        assert len(loan.odBalanceLog) == original_count

    def test_happy_path_commit(self):
        """W1: Commit appends to odBalanceLog and creates annotation."""
        loan = _make_loan_data()
        od = _make_od_data()
        original_count = len(loan.odBalanceLog)
        original_ann_count = len(od.odBalanceAnnotations)

        update_od_balance(
            loan, od, date="2026-09-26", balance=1_200_000.0, today_date=TODAY, commit=True
        )

        assert len(loan.odBalanceLog) == original_count + 1
        assert loan.odBalanceLog[-1].balance == 1_200_000.0
        assert len(od.odBalanceAnnotations) == original_ann_count + 1

    def test_invalid_negative_balance(self):
        """W1: Negative balance raises ValueError."""
        loan = _make_loan_data()
        od = _make_od_data()
        with pytest.raises(ValueError, match="balance must be >= 0"):
            update_od_balance(loan, od, date="2026-09-26", balance=-100.0, today_date=TODAY)

    def test_balance_exceeds_10cr(self):
        """W1: Balance > ₹10 Crore raises ValueError."""
        loan = _make_loan_data()
        od = _make_od_data()
        with pytest.raises(ValueError, match="<= ₹10 Crore"):
            update_od_balance(loan, od, date="2026-09-26", balance=10_00_00_001.0, today_date=TODAY)

    def test_invalid_source_id(self):
        """W1: Non-existent source_id raises ValueError."""
        loan = _make_loan_data()
        od = _make_od_data()
        with pytest.raises(ValueError, match="source_id.*not found"):
            update_od_balance(loan, od, date="2026-09-26", balance=500_000.0, today_date=TODAY, source_id="nonexistent")

    def test_over_allocation_warning(self):
        """W1: Over-allocation produces a warning but doesn't block."""
        loan = _make_loan_data()
        od = _make_od_data()
        # Balance < allocated goals = 300_000
        result = update_od_balance(loan, od, date="2026-09-26", balance=100_000.0, today_date=TODAY)
        assert any("Over-allocated" in w for w in result["warnings"])


# ---------------------------------------------------------------------------
# W2 — add_disbursement
# ---------------------------------------------------------------------------


class TestAddDisbursement:
    def test_happy_path_dry_run(self):
        """W2: Dry-run doesn't mutate loan data."""
        loan = _make_loan_data()
        original_count = len(loan.disbursements)

        result = add_disbursement(loan, today_date=TODAY, date="2026-10-01", amount=450_000.0)

        assert result["operation"] == "add_disbursement"
        assert len(loan.disbursements) == original_count

    def test_happy_path_commit(self):
        """W2: Commit appends disbursement."""
        loan = _make_loan_data()
        original_count = len(loan.disbursements)

        add_disbursement(loan, today_date=TODAY, date="2026-10-01", amount=450_000.0, commit=True)

        assert len(loan.disbursements) == original_count + 1
        assert loan.disbursements[-1].amount == 450_000.0

    def test_zero_amount_rejected(self):
        """W2: Amount = 0 raises ValueError."""
        loan = _make_loan_data()
        with pytest.raises(ValueError, match="amount must be > 0"):
            add_disbursement(loan, today_date=TODAY, date="2026-10-01", amount=0.0)

    def test_exceeds_sanctioned_rejected(self):
        """W2: Amount exceeding sanctioned limit raises ValueError."""
        loan = _make_loan_data()
        # Total disbursed = 5_982_984 + 1_480_816 + 2_051_200 + 2_000_000 = 11_515_000
        # Sanctioned = 11_965_000, remaining = 450_000
        with pytest.raises(ValueError, match="exceed.*sanctioned"):
            add_disbursement(loan, today_date=TODAY, date="2026-10-01", amount=500_000.0)


# ---------------------------------------------------------------------------
# W3 — add_prepayment
# ---------------------------------------------------------------------------


class TestAddPrepayment:
    def test_happy_path_dry_run(self):
        """W3: Dry-run computes impact without mutating data."""
        loan = _make_loan_data()
        original_count = len(loan.prepayments)

        result = add_prepayment(loan, today_date=TODAY, date="2026-10-01", amount=500_000.0)

        assert result["operation"] == "add_prepayment"
        assert len(loan.prepayments) == original_count

    def test_happy_path_commit(self):
        """W3: Commit appends prepayment."""
        loan = _make_loan_data()
        original_count = len(loan.prepayments)

        add_prepayment(loan, today_date=TODAY, date="2026-10-01", amount=500_000.0, commit=True)

        assert len(loan.prepayments) == original_count + 1
        assert loan.prepayments[-1].amount == 500_000.0

    def test_negative_amount_rejected(self):
        """W3: Negative amount raises ValueError."""
        loan = _make_loan_data()
        with pytest.raises(ValueError, match="amount must be > 0"):
            add_prepayment(loan, today_date=TODAY, date="2026-10-01", amount=-1000.0)

    def test_zero_amount_rejected(self):
        """W3: Zero amount raises ValueError."""
        loan = _make_loan_data()
        with pytest.raises(ValueError, match="amount must be > 0"):
            add_prepayment(loan, today_date=TODAY, date="2026-10-01", amount=0.0)


# ---------------------------------------------------------------------------
# W4 — add_rate_change
# ---------------------------------------------------------------------------


class TestAddRateChange:
    def test_happy_path_dry_run(self):
        """W4: Dry-run computes impact without mutating data."""
        loan = _make_loan_data()
        original_count = len(loan.rateHistory)

        result = add_rate_change(
            loan, today_date=TODAY, effective_date="2026-10-01", annual_rate=7.0
        )

        assert result["operation"] == "add_rate_change"
        assert len(loan.rateHistory) == original_count

    def test_happy_path_commit(self):
        """W4: Commit appends rate change."""
        loan = _make_loan_data()
        original_count = len(loan.rateHistory)

        add_rate_change(
            loan, today_date=TODAY, effective_date="2026-10-01", annual_rate=7.0, commit=True
        )

        assert len(loan.rateHistory) == original_count + 1
        assert loan.rateHistory[-1].annualRate == 7.0

    def test_zero_rate_rejected(self):
        """W4: Rate = 0 raises ValueError."""
        loan = _make_loan_data()
        with pytest.raises(ValueError, match="annual_rate must be > 0"):
            add_rate_change(loan, today_date=TODAY, effective_date="2026-10-01", annual_rate=0.0)

    def test_rate_above_30_rejected(self):
        """W4: Rate >= 30 raises ValueError."""
        loan = _make_loan_data()
        with pytest.raises(ValueError, match="annual_rate must be < 30"):
            add_rate_change(loan, today_date=TODAY, effective_date="2026-10-01", annual_rate=30.0)

    def test_rate_change_reduces_closure_date(self):
        """W4: Lower rate reduces total interest projected."""
        loan = _make_loan_data()
        result = add_rate_change(
            loan, today_date=TODAY, effective_date="2026-10-01", annual_rate=6.0
        )
        # Lower rate → lower total interest
        assert result["after"]["totalInterestProjected"] < result["before"]["totalInterestProjected"]


# ---------------------------------------------------------------------------
# W5 — update_payment
# ---------------------------------------------------------------------------


class TestUpdatePayment:
    def test_happy_path_update_existing(self):
        """W5: Updates an existing payment log entry."""
        loan = _make_loan_data()
        # p1 exists with due_date 2026-02-10
        result = update_payment(loan, today_date=TODAY, due_date="2026-02-10", amount_paid=40_000.0)

        assert result["operation"] == "update_payment"

    def test_happy_path_commit_existing(self):
        """W5: Commit modifies existing payment entry."""
        loan = _make_loan_data()
        original_paid = loan.paymentLog[0].amountPaid

        update_payment(
            loan, today_date=TODAY, due_date="2026-02-10", amount_paid=42_000.0, commit=True
        )

        assert loan.paymentLog[0].amountPaid == 42_000.0

    def test_happy_path_add_new_payment(self):
        """W5: Creates a new payment log entry for a date not yet logged."""
        loan = _make_loan_data()
        original_count = len(loan.paymentLog)

        update_payment(
            loan, today_date=TODAY, due_date="2026-03-10", amount_paid=38_000.0, commit=True
        )

        assert len(loan.paymentLog) == original_count + 1

    def test_invalid_date_rejected(self):
        """W5: Invalid due_date raises ValueError."""
        loan = _make_loan_data()
        with pytest.raises(ValueError, match="due_date must be a valid YYYY-MM-DD date"):
            update_payment(loan, today_date=TODAY, due_date="not-a-date", amount_paid=38_000.0)

    def test_zero_amount_rejected(self):
        """W5: Zero amount_paid raises ValueError."""
        loan = _make_loan_data()
        with pytest.raises(ValueError, match="amount_paid must be > 0"):
            update_payment(loan, today_date=TODAY, due_date="2026-02-10", amount_paid=0.0)


# ---------------------------------------------------------------------------
# W6 — update_emi_reserve
# ---------------------------------------------------------------------------


class TestUpdateEmiReserve:
    def test_happy_path_dry_run(self):
        """W6: Dry-run returns impact dict without mutating od_data."""
        loan = _make_loan_data()
        od = _make_od_data()
        original_reserve = od.emiReserve

        result = update_emi_reserve(loan, od, today_date=TODAY, amount=95_000.0)

        assert result["operation"] == "update_emi_reserve"
        assert result["before"]["emiReserve"] == original_reserve
        assert result["after"]["emiReserve"] == 95_000.0
        assert od.emiReserve == original_reserve  # Not mutated

    def test_happy_path_commit(self):
        """W6: Commit updates emiReserve."""
        loan = _make_loan_data()
        od = _make_od_data()

        update_emi_reserve(loan, od, today_date=TODAY, amount=95_000.0, commit=True)

        assert od.emiReserve == 95_000.0

    def test_negative_amount_rejected(self):
        """W6: Negative amount raises ValueError."""
        loan = _make_loan_data()
        od = _make_od_data()
        with pytest.raises(ValueError, match="amount must be >= 0"):
            update_emi_reserve(loan, od, today_date=TODAY, amount=-1000.0)

    def test_over_allocation_warning(self):
        """W6: Reserve causing over-allocation produces a warning."""
        loan = _make_loan_data()
        od = _make_od_data()
        # Latest OD balance = 923_964, allocating nearly all leaves little
        result = update_emi_reserve(loan, od, today_date=TODAY, amount=900_000.0)
        assert any("over-allocation" in w.lower() for w in result["warnings"])


# ---------------------------------------------------------------------------
# W7 — add_source
# ---------------------------------------------------------------------------


class TestAddSource:
    def test_happy_path_dry_run(self):
        """W7: Dry-run returns created source without mutating od_data."""
        od = _make_od_data()
        original_count = len(od.sources)

        result = add_source(od, name="New Source")

        assert result["operation"] == "add_source"
        assert "created" in result
        assert len(od.sources) == original_count  # Not mutated

    def test_happy_path_commit(self):
        """W7: Commit appends new source with editHistory initialized."""
        od = _make_od_data()
        original_count = len(od.sources)

        add_source(od, name="Bonus Income", description="Annual bonus", commit=True)

        assert len(od.sources) == original_count + 1
        new_src = od.sources[-1]
        assert new_src.name == "Bonus Income"
        assert new_src.isActive is True
        assert isinstance(new_src.editHistory, list)

    def test_empty_name_rejected(self):
        """W7: Empty name raises ValueError."""
        od = _make_od_data()
        with pytest.raises(ValueError, match="empty"):
            add_source(od, name="")

    def test_duplicate_name_case_insensitive_rejected(self):
        """W7: Duplicate name (case-insensitive) raises ValueError."""
        od = _make_od_data()
        with pytest.raises(ValueError, match="already exists"):
            add_source(od, name="aditya")  # "Aditya" already exists

    def test_name_too_long_rejected(self):
        """W7: Name > 60 chars raises ValueError."""
        od = _make_od_data()
        with pytest.raises(ValueError, match="60 characters"):
            add_source(od, name="A" * 61)


# ---------------------------------------------------------------------------
# W8 — edit_source
# ---------------------------------------------------------------------------


class TestEditSource:
    def test_happy_path_dry_run(self):
        """W8: Dry-run doesn't mutate source."""
        od = _make_od_data()
        original_name = od.sources[0].name

        result = edit_source(od, source_id="src-1", name="Aditya (Updated)")

        assert result["operation"] == "edit_source"
        assert od.sources[0].name == original_name  # Not mutated

    def test_happy_path_commit(self):
        """W8: Commit updates source fields and appends editHistory."""
        od = _make_od_data()

        edit_source(od, source_id="src-1", name="Aditya V2", description="Updated desc", commit=True)

        src = od.sources[0]
        assert src.name == "Aditya V2"
        assert src.description == "Updated desc"
        assert len(src.editHistory) == 2  # name + description changes

    def test_nonexistent_source_rejected(self):
        """W8: Non-existent source_id raises ValueError."""
        od = _make_od_data()
        with pytest.raises(ValueError, match="not found"):
            edit_source(od, source_id="nonexistent", name="Test")

    def test_duplicate_name_rejected(self):
        """W8: Changing name to one that already exists raises ValueError."""
        od = _make_od_data()
        with pytest.raises(ValueError, match="already exists"):
            edit_source(od, source_id="src-1", name="neha")  # "Neha" is src-2

    def test_deactivate_source(self):
        """W8: Can deactivate a source via is_active=False."""
        od = _make_od_data()
        edit_source(od, source_id="src-1", is_active=False, commit=True)
        assert od.sources[0].isActive is False
        assert len(od.sources[0].editHistory) == 1


# ---------------------------------------------------------------------------
# W9 — add_goal
# ---------------------------------------------------------------------------


class TestAddGoal:
    def test_happy_path_dry_run(self):
        """W9: Dry-run returns created goal without mutating od_data."""
        od = _make_od_data()
        original_count = len(od.goals)

        result = add_goal(od, name="Renovation", target_amount=200_000.0, today_date=TODAY)

        assert result["operation"] == "add_goal"
        assert "created" in result
        assert len(od.goals) == original_count  # Not mutated

    def test_happy_path_commit(self):
        """W9: Commit appends goal with editHistory initialized."""
        od = _make_od_data()
        original_count = len(od.goals)

        add_goal(od, name="Renovation", target_amount=200_000.0, today_date=TODAY, commit=True)

        assert len(od.goals) == original_count + 1
        new_goal = od.goals[-1]
        assert new_goal.name == "Renovation"
        assert len(new_goal.editHistory) == 1

    def test_zero_target_rejected(self):
        """W9: target_amount = 0 raises ValueError."""
        od = _make_od_data()
        with pytest.raises(ValueError, match="target_amount must be > 0"):
            add_goal(od, name="Goal", target_amount=0.0, today_date=TODAY)

    def test_empty_name_rejected(self):
        """W9: Empty goal name raises ValueError."""
        od = _make_od_data()
        with pytest.raises(ValueError, match="empty"):
            add_goal(od, name="", target_amount=100_000.0, today_date=TODAY)

    def test_over_allocation_warning(self):
        """W9: Adding allocation that causes over-allocation warns."""
        loan = _make_loan_data()
        od = _make_od_data()
        # Latest OD balance = 923_964, emiReserve = 91_143, allocatable = 832_821
        # Existing allocation = 300_000; adding 600_000 more = 900_000 > 832_821
        result = add_goal_with_od(
            loan, od, name="House Furniture", target_amount=600_000.0,
            allocated_amount=600_000.0, today_date=TODAY
        )
        assert any("Over-allocated" in w for w in result["warnings"])


# ---------------------------------------------------------------------------
# W10 — edit_goal
# ---------------------------------------------------------------------------


class TestEditGoal:
    def test_happy_path_dry_run(self):
        """W10: Dry-run computes diff without mutating goal."""
        od = _make_od_data()
        original_amount = od.goals[0].targetAmount

        result = edit_goal(od, goal_id="goal-1", patch={"targetAmount": 600_000.0})

        assert result["operation"] == "edit_goal"
        assert od.goals[0].targetAmount == original_amount  # Not mutated

    def test_happy_path_commit(self):
        """W10: Commit updates goal fields and appends editHistory."""
        od = _make_od_data()

        edit_goal(
            od, goal_id="goal-1",
            patch={"name": "Emergency Reserve", "allocatedAmount": 350_000.0},
            commit=True,
        )

        goal = od.goals[0]
        assert goal.name == "Emergency Reserve"
        assert goal.allocatedAmount == 350_000.0
        assert len(goal.editHistory) == 2

    def test_nonexistent_goal_rejected(self):
        """W10: Non-existent goal_id raises ValueError."""
        od = _make_od_data()
        with pytest.raises(ValueError, match="not found"):
            edit_goal(od, goal_id="ghost-id", patch={"name": "X"})

    def test_invalid_patch_field_rejected(self):
        """W10: Unknown patch field raises ValueError."""
        od = _make_od_data()
        with pytest.raises(ValueError, match="Invalid patch fields"):
            edit_goal(od, goal_id="goal-1", patch={"unknownField": "x"})

    def test_negative_target_rejected(self):
        """W10: Negative targetAmount raises ValueError."""
        od = _make_od_data()
        with pytest.raises(ValueError, match="targetAmount must be > 0"):
            edit_goal(od, goal_id="goal-1", patch={"targetAmount": -1000.0})


# ---------------------------------------------------------------------------
# W11 — add_contribution
# ---------------------------------------------------------------------------


class TestAddContribution:
    def test_happy_path_dry_run(self):
        """W11: Dry-run returns created contribution without mutating od_data."""
        od = _make_od_data()
        original_count = len(od.contributions)

        result = add_contribution(od, date="2026-09-20", amount=50_000.0, source_id="src-1", today_date=TODAY)

        assert result["operation"] == "add_contribution"
        assert "created" in result
        assert len(od.contributions) == original_count  # Not mutated

    def test_happy_path_commit(self):
        """W11: Commit appends contribution."""
        od = _make_od_data()
        original_count = len(od.contributions)

        add_contribution(od, date="2026-09-20", amount=50_000.0, source_id="src-1", today_date=TODAY, commit=True)

        assert len(od.contributions) == original_count + 1
        new_c = od.contributions[-1]
        assert new_c.amount == 50_000.0
        assert new_c.sourceId == "src-1"
        assert len(new_c.editHistory) == 1

    def test_nonexistent_source_rejected(self):
        """W11: Non-existent source_id raises ValueError."""
        od = _make_od_data()
        with pytest.raises(ValueError, match="not found"):
            add_contribution(od, date="2026-09-20", amount=50_000.0, source_id="ghost", today_date=TODAY)

    def test_zero_amount_rejected(self):
        """W11: Zero amount raises ValueError."""
        od = _make_od_data()
        with pytest.raises(ValueError, match="amount must be > 0"):
            add_contribution(od, date="2026-09-20", amount=0.0, source_id="src-1", today_date=TODAY)

    def test_invalid_date_rejected(self):
        """W11: Invalid date raises ValueError."""
        od = _make_od_data()
        with pytest.raises(ValueError, match="date must be a valid YYYY-MM-DD"):
            add_contribution(od, date="01-09-2026", amount=1000.0, source_id="src-1", today_date=TODAY)


# ---------------------------------------------------------------------------
# W12 — edit_contribution
# ---------------------------------------------------------------------------


class TestEditContribution:
    def test_happy_path_dry_run(self):
        """W12: Dry-run computes diff without mutating contribution."""
        od = _make_od_data()
        original_amount = od.contributions[0].amount

        result = edit_contribution(od, contribution_id="cont-1", patch={"amount": 200_000.0})

        assert result["operation"] == "edit_contribution"
        assert od.contributions[0].amount == original_amount  # Not mutated

    def test_happy_path_commit(self):
        """W12: Commit updates contribution and appends editHistory."""
        od = _make_od_data()

        edit_contribution(od, contribution_id="cont-1", patch={"amount": 200_000.0, "note": "Revised"}, commit=True)

        c = od.contributions[0]
        assert c.amount == 200_000.0
        assert c.note == "Revised"
        assert len(c.editHistory) == 2

    def test_nonexistent_contribution_rejected(self):
        """W12: Non-existent contribution_id raises ValueError."""
        od = _make_od_data()
        with pytest.raises(ValueError, match="not found"):
            edit_contribution(od, contribution_id="ghost-id", patch={"amount": 100.0})

    def test_invalid_patch_field_rejected(self):
        """W12: Unknown patch field raises ValueError."""
        od = _make_od_data()
        with pytest.raises(ValueError, match="Invalid patch fields"):
            edit_contribution(od, contribution_id="cont-1", patch={"badField": 123})

    def test_change_source_validates_existence(self):
        """W12: Patching sourceId to non-existent source raises ValueError."""
        od = _make_od_data()
        with pytest.raises(ValueError, match="Source with id.*not found"):
            edit_contribution(od, contribution_id="cont-1", patch={"sourceId": "ghost"})


# ---------------------------------------------------------------------------
# W13 — edit_od_annotation
# ---------------------------------------------------------------------------


class TestEditOdAnnotation:
    def test_happy_path_dry_run(self):
        """W13: Dry-run returns diff without mutating annotation."""
        od = _make_od_data()
        original_purpose = od.odBalanceAnnotations[0].purpose

        result = edit_od_annotation(od, od_balance_log_id="od-1", purpose="investment")

        assert result["operation"] == "edit_od_annotation"
        assert od.odBalanceAnnotations[0].purpose == original_purpose  # Not mutated

    def test_happy_path_commit(self):
        """W13: Commit updates annotation fields and appends editHistory."""
        od = _make_od_data()

        edit_od_annotation(
            od, od_balance_log_id="od-1",
            source_id="src-2", purpose="emergency", note="Updated note",
            commit=True,
        )

        ann = od.odBalanceAnnotations[0]
        assert ann.sourceId == "src-2"
        assert ann.purpose == "emergency"
        assert ann.note == "Updated note"
        assert len(ann.editHistory) == 3  # source + purpose + note

    def test_nonexistent_annotation_rejected(self):
        """W13: Non-existent od_balance_log_id raises ValueError."""
        od = _make_od_data()
        with pytest.raises(ValueError, match="not found"):
            edit_od_annotation(od, od_balance_log_id="ghost-id", purpose="test")

    def test_no_change_produces_zero_edits(self):
        """W13: Passing same values produces no audit records."""
        od = _make_od_data()
        result = edit_od_annotation(
            od, od_balance_log_id="od-1",
            source_id="src-1",  # Already "src-1"
            purpose="savings",  # Already "savings"
        )
        assert result["changes"] == 0


# ---------------------------------------------------------------------------
# W14 — process_due_payments
# ---------------------------------------------------------------------------


class TestProcessDuePayments:
    def test_happy_path_processes_unlogged_payments(self):
        """W14: Processes due dates without existing payment log entries."""
        loan = _make_loan_data()
        od = _make_od_data()
        # 2026-03-10 has no payment entry; it's before today
        result = process_due_payments(loan, od, today_date=TODAY)

        assert result["operation"] == "process_due_payments"
        assert result["payments_processed"] >= 1  # At least some unprocessed payments

    def test_commit_adds_payment_log_entries(self):
        """W14: Commit appends payment log entries for unprocessed dates."""
        loan = _make_loan_data()
        od = _make_od_data()
        original_count = len(loan.paymentLog)

        process_due_payments(loan, od, today_date=TODAY, commit=True)

        assert len(loan.paymentLog) > original_count

    def test_no_action_when_all_paid(self):
        """W14: No action when all due payments are already logged."""
        loan = _make_loan_data()
        od = _make_od_data()
        # First, process all payments
        process_due_payments(loan, od, today_date=TODAY, commit=True)
        count_after_first = len(loan.paymentLog)

        # Process again — should be idempotent
        result = process_due_payments(loan, od, today_date=TODAY, commit=True)

        assert result["payments_processed"] == 0
        assert len(loan.paymentLog) == count_after_first

    def test_invalid_date_rejected(self):
        """W14: Invalid today_date raises ValueError."""
        loan = _make_loan_data()
        od = _make_od_data()
        with pytest.raises(ValueError, match="today_date must be a valid YYYY-MM-DD"):
            process_due_payments(loan, od, today_date="not-a-date")


# ---------------------------------------------------------------------------
# W15 — update_settings
# ---------------------------------------------------------------------------


class TestUpdateSettings:
    def test_happy_path_dry_run(self):
        """W15: Dry-run computes impact without mutating loanDetails."""
        loan = _make_loan_data()
        original_emi = loan.loanDetails.currentCommunicatedEmi

        result = update_settings(loan, today_date=TODAY, patch={"dueDateDay": 15})

        assert result["operation"] == "update_settings"
        assert loan.loanDetails.currentCommunicatedEmi == original_emi  # Not mutated

    def test_happy_path_commit(self):
        """W15: Commit updates loanDetails fields."""
        loan = _make_loan_data()

        update_settings(
            loan, today_date=TODAY,
            patch={"currentCommunicatedEmi": 95_000.0},
            commit=True,
        )

        assert loan.loanDetails.currentCommunicatedEmi == 95_000.0

    def test_invalid_field_rejected(self):
        """W15: Unknown settings field raises ValueError."""
        loan = _make_loan_data()
        with pytest.raises(ValueError, match="Invalid settings fields"):
            update_settings(loan, today_date=TODAY, patch={"lender": "New Bank"})

    def test_invalid_due_date_day_rejected(self):
        """W15: dueDateDay outside 1-28 raises ValueError."""
        loan = _make_loan_data()
        with pytest.raises(ValueError, match="dueDateDay"):
            update_settings(loan, today_date=TODAY, patch={"dueDateDay": 31})

    def test_policy_field_update(self):
        """W15: Can update policy fields via patch."""
        loan = _make_loan_data()

        update_settings(
            loan, today_date=TODAY,
            patch={"onPrepayment": "adjust_emi"},
            commit=True,
        )

        assert loan.loanDetails.policy.onPrepayment == "adjust_emi"

    def test_invalid_policy_value_rejected(self):
        """W15: Invalid policy value raises ValueError."""
        loan = _make_loan_data()
        with pytest.raises(ValueError, match="adjust_tenure.*adjust_emi"):
            update_settings(loan, today_date=TODAY, patch={"onPrepayment": "bad_policy"})
