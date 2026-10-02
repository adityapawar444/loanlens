"""
test_renderer.py — Tests for all 5 LoanLens report renderers (R1-R5).

Tests verify:
  - Required sections/headings appear in output
  - INR formatting (Indian grouping) is correct
  - Date formatting is "10 Aug 2026" style
  - Key computed values appear in output
  - Determinism: same inputs → identical output
  - Edge cases (empty data, single entry, etc.)
"""

from __future__ import annotations

import copy
import pytest

from engine.types import (
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
from engine.renderer import (
    fmt_date,
    fmt_inr,
    render_ledger,
    render_od_savings,
    render_schedule,
    render_simulator,
    render_summary,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

TODAY = "2026-09-26"


def _make_loan_data() -> LoanData:
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
        disbursements=[
            Disbursement(id="d1", date="2026-01-31", amount=5_982_984, note="1st tranche"),
            Disbursement(id="d2", date="2026-04-09", amount=1_480_816, note="2nd tranche"),
            Disbursement(id="d3", date="2026-06-10", amount=2_051_200, note="3rd tranche"),
            Disbursement(id="d4", date="2026-08-05", amount=2_000_000, note="4th tranche"),
        ],
        rateHistory=[
            RateHistory(id="r1", effectiveDate="2026-01-31", annualRate=7.6, benchmark="RLLR"),
        ],
        odBalanceLog=[
            OdBalanceLog(id="od1", date="2026-06-10", balance=510_792),
            OdBalanceLog(id="od2", date="2026-07-10", balance=750_000),
            OdBalanceLog(id="od3", date="2026-09-10", balance=923_964),
        ],
        prepayments=[],
        paymentLog=[
            PaymentLog(
                id="p1", dueDate="2026-02-10", type="pre_emi_interest",
                amountDue=38_000, amountPaid=38_000, paidDate="2026-02-10",
            ),
        ],
    )


def _make_od_data() -> OdSavingsData:
    return OdSavingsData(
        emiReserve=91_143,
        sources=[
            OdSource(id="s1", name="Aditya", description="Salary", isActive=True,
                     createdAt="2026-01-01T00:00:00Z", editHistory=[]),
            OdSource(id="s2", name="Neha", description="Salary", isActive=True,
                     createdAt="2026-01-01T00:00:00Z", editHistory=[]),
        ],
        contributions=[
            OdContribution(id="c1", date="2026-07-10", amount=99_000, sourceId="s1", editHistory=[]),
            OdContribution(id="c2", date="2026-08-15", amount=50_000, sourceId="s2", editHistory=[]),
            OdContribution(id="c3", date="2026-09-01", amount=74_000, sourceId="s1", editHistory=[]),
        ],
        goals=[
            OdGoal(id="g1", name="Emergency Fund", targetAmount=500_000,
                   allocatedAmount=500_000, isActive=True, editHistory=[]),
            OdGoal(id="g2", name="Renovation", targetAmount=400_000,
                   allocatedAmount=300_000, isActive=True, editHistory=[]),
        ],
        odBalanceAnnotations=[
            OdBalanceAnnotation(odBalanceLogId="od1", sourceId="s1", purpose="savings",
                                note="Initial", editHistory=[]),
            OdBalanceAnnotation(odBalanceLogId="od3", sourceId="s2", purpose="savings",
                                note="Sep deposit", editHistory=[]),
        ],
    )


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

class TestFmtInr:
    def test_basic(self):
        assert fmt_inr(1_234_567) == "₹12,34,567"

    def test_small(self):
        assert fmt_inr(91_143) == "₹91,143"

    def test_zero(self):
        assert fmt_inr(0) == "₹0"

    def test_negative(self):
        assert fmt_inr(-50_000) == "-₹50,000"

    def test_three_digits(self):
        assert fmt_inr(999) == "₹999"

    def test_large(self):
        assert fmt_inr(11_965_000) == "₹1,19,65,000"

    def test_rounding(self):
        # 0.6 should round to ₹1
        assert fmt_inr(0.6) == "₹1"


class TestFmtDate:
    def test_basic(self):
        assert fmt_date("2026-09-19") == "19 Sep 2026"

    def test_january(self):
        assert fmt_date("2026-01-31") == "31 Jan 2026"

    def test_december(self):
        assert fmt_date("2027-12-10") == "10 Dec 2027"

    def test_invalid_passthrough(self):
        # Invalid strings should not crash
        result = fmt_date("not-a-date")
        assert result == "not-a-date"


# ---------------------------------------------------------------------------
# R1 — render_summary
# ---------------------------------------------------------------------------

class TestRenderSummary:
    def test_heading_present(self):
        """R1: Report heading contains 'LoanLens Summary' and today's date."""
        loan = _make_loan_data()
        od = _make_od_data()
        output = render_summary(loan, od, TODAY)
        assert "LoanLens Summary" in output
        assert "26 Sep 2026" in output

    def test_phase_label(self):
        """R1: Phase label is present."""
        loan = _make_loan_data()
        od = _make_od_data()
        output = render_summary(loan, od, TODAY)
        assert "Phase" in output
        assert "Moratorium" in output

    def test_outstanding_principal_present(self):
        """R1: Outstanding principal appears with INR formatting."""
        loan = _make_loan_data()
        od = _make_od_data()
        output = render_summary(loan, od, TODAY)
        assert "Outstanding Principal" in output
        assert "₹" in output

    def test_od_waterfall_section(self):
        """R1: OD Waterfall section is present."""
        loan = _make_loan_data()
        od = _make_od_data()
        output = render_summary(loan, od, TODAY)
        assert "OD Waterfall" in output
        assert "EMI Reserve" in output
        assert "Allocatable" in output

    def test_interest_section(self):
        """R1: Interest section is present."""
        loan = _make_loan_data()
        od = _make_od_data()
        output = render_summary(loan, od, TODAY)
        assert "Interest" in output
        assert "Paid to Date" in output
        assert "Saved to Date" in output

    def test_disbursed_line(self):
        """R1: Disbursed / Sanctioned line is present."""
        loan = _make_loan_data()
        od = _make_od_data()
        output = render_summary(loan, od, TODAY)
        assert "Disbursed" in output
        assert "₹1,19,65,000" in output  # Sanctioned = 11,965,000

    def test_over_allocation_shown(self):
        """R1: Over-allocation warning shown when goals > allocatable."""
        loan = _make_loan_data()
        od = _make_od_data()
        # Allocatable = 923_964 - 91_143 = 832_821
        # Allocated = 500_000 + 300_000 = 800_000 → under, so surplus shown
        output = render_summary(loan, od, TODAY)
        assert "Unallocated" in output or "Over-allocated" in output

    def test_deterministic(self):
        """R1: Same inputs produce identical output."""
        loan = _make_loan_data()
        od = _make_od_data()
        out1 = render_summary(loan, od, TODAY)
        out2 = render_summary(loan, od, TODAY)
        assert out1 == out2

    def test_od_balance_value(self):
        """R1: Latest OD balance (₹9,23,964) appears in output."""
        loan = _make_loan_data()
        od = _make_od_data()
        output = render_summary(loan, od, TODAY)
        assert "₹9,23,964" in output

    def test_emi_reserve_value(self):
        """R1: EMI reserve (₹91,143) appears in output."""
        loan = _make_loan_data()
        od = _make_od_data()
        output = render_summary(loan, od, TODAY)
        assert "₹91,143" in output


# ---------------------------------------------------------------------------
# R2 — render_od_savings
# ---------------------------------------------------------------------------

class TestRenderOdSavings:
    def test_heading_present(self):
        """R2: Report heading contains 'OD Savings'."""
        loan = _make_loan_data()
        od = _make_od_data()
        output = render_od_savings(loan, od, TODAY)
        assert "OD Savings" in output
        assert "26 Sep 2026" in output

    def test_goals_section(self):
        """R2: Goals section lists active goals."""
        loan = _make_loan_data()
        od = _make_od_data()
        output = render_od_savings(loan, od, TODAY)
        assert "Goals" in output
        assert "Emergency Fund" in output
        assert "Renovation" in output

    def test_goal_progress_formatting(self):
        """R2: Goal with 100% allocation shows ✅."""
        loan = _make_loan_data()
        od = _make_od_data()
        output = render_od_savings(loan, od, TODAY)
        assert "✅" in output  # Emergency Fund is fully allocated

    def test_met_unmet_count(self):
        """R2: Met/unmet goal counts are present."""
        loan = _make_loan_data()
        od = _make_od_data()
        output = render_od_savings(loan, od, TODAY)
        assert "🟢 Met:" in output
        assert "🔴 Unmet:" in output

    def test_recent_contributions(self):
        """R2: Recent contributions section shows source names."""
        loan = _make_loan_data()
        od = _make_od_data()
        output = render_od_savings(loan, od, TODAY)
        assert "Recent Contributions" in output
        assert "Aditya" in output

    def test_od_balance_trend(self):
        """R2: OD Balance Trend section is present."""
        loan = _make_loan_data()
        od = _make_od_data()
        output = render_od_savings(loan, od, TODAY)
        assert "OD Balance Trend" in output

    def test_waterfall_section(self):
        """R2: OD Waterfall section present."""
        loan = _make_loan_data()
        od = _make_od_data()
        output = render_od_savings(loan, od, TODAY)
        assert "OD Waterfall" in output
        assert "Allocatable" in output

    def test_empty_contributions(self):
        """R2: Renders cleanly with no contributions."""
        loan = _make_loan_data()
        od = _make_od_data()
        od.contributions = []
        output = render_od_savings(loan, od, TODAY)
        assert "Recent Contributions" in output
        assert "—" in output  # Placeholder for empty

    def test_deterministic(self):
        """R2: Same inputs produce identical output."""
        loan = _make_loan_data()
        od = _make_od_data()
        out1 = render_od_savings(loan, od, TODAY)
        out2 = render_od_savings(loan, od, TODAY)
        assert out1 == out2

    def test_contribution_dates_formatted(self):
        """R2: Contribution dates use 'DD Mon YYYY' format."""
        loan = _make_loan_data()
        od = _make_od_data()
        output = render_od_savings(loan, od, TODAY)
        # At least one date like "01 Sep 2026" should appear
        assert "Sep 2026" in output or "Aug 2026" in output or "Jul 2026" in output


# ---------------------------------------------------------------------------
# R3 — render_schedule
# ---------------------------------------------------------------------------

class TestRenderSchedule:
    def test_heading_present(self):
        """R3: Report heading contains 'Amortization Schedule'."""
        loan = _make_loan_data()
        output = render_schedule(loan, TODAY)
        assert "Amortization Schedule" in output

    def test_next_installments_section(self):
        """R3: 'Next 6 Installments' table is present."""
        loan = _make_loan_data()
        output = render_schedule(loan, TODAY)
        assert "Next 6 Installments" in output
        assert "Installment" in output
        assert "Interest" in output
        assert "Principal" in output

    def test_yearly_summary_section(self):
        """R3: Yearly summary table is present."""
        loan = _make_loan_data()
        output = render_schedule(loan, TODAY)
        assert "Yearly Summary" in output
        assert "Total Interest" in output
        assert "Year-End Balance" in output

    def test_closure_line(self):
        """R3: Closure line is present."""
        loan = _make_loan_data()
        output = render_schedule(loan, TODAY)
        assert "Closure" in output
        assert "Total Interest" in output
        assert "Total OD Savings" in output

    def test_window_parameter(self):
        """R3: Window parameter controls number of rows shown."""
        loan = _make_loan_data()
        output_3 = render_schedule(loan, TODAY, window=3)
        output_10 = render_schedule(loan, TODAY, window=10)
        assert "Next 3 Installments" in output_3
        assert "Next 10 Installments" in output_10

    def test_row_count_respected(self):
        """R3: Output contains at most window rows in the installment table."""
        loan = _make_loan_data()
        output = render_schedule(loan, TODAY, window=6)
        # Count table data rows (lines with | that have actual numbers)
        lines = output.split("\n")
        table_start = False
        data_rows = 0
        in_installment_table = False
        for line in lines:
            if "Next 6 Installments" in line:
                in_installment_table = True
            elif in_installment_table and line.startswith("|---"):
                table_start = True
            elif in_installment_table and table_start and line.startswith("|") and "---" not in line:
                data_rows += 1
            elif in_installment_table and line == "":
                break
        assert data_rows <= 6

    def test_inr_formatting_in_table(self):
        """R3: Schedule rows contain ₹ symbols."""
        loan = _make_loan_data()
        output = render_schedule(loan, TODAY)
        assert "₹" in output

    def test_deterministic(self):
        """R3: Same inputs produce identical output."""
        loan = _make_loan_data()
        out1 = render_schedule(loan, TODAY)
        out2 = render_schedule(loan, TODAY)
        assert out1 == out2

    def test_year_2026_in_yearly_summary(self):
        """R3: Year 2026 appears in yearly summary."""
        loan = _make_loan_data()
        output = render_schedule(loan, TODAY)
        assert "2026" in output

    def test_empty_schedule_handled(self):
        """R3: Empty schedule (no disbursements) renders without crash."""
        loan = _make_loan_data()
        loan.disbursements = []
        output = render_schedule(loan, TODAY)
        assert "Amortization Schedule" in output


# ---------------------------------------------------------------------------
# R4 — render_simulator
# ---------------------------------------------------------------------------

class TestRenderSimulator:
    def test_heading_present(self):
        """R4: Report heading contains 'Simulator'."""
        loan = _make_loan_data()
        sim_loan = copy.deepcopy(loan)
        sim_loan.prepayments = [Prepayment(id="pp1", date="2026-10-01", amount=500_000)]
        output = render_simulator(loan, sim_loan, TODAY, "Add ₹5L prepayment on 1 Oct 2026")
        assert "Simulator" in output

    def test_scenario_description(self):
        """R4: Scenario description is shown."""
        loan = _make_loan_data()
        sim_loan = copy.deepcopy(loan)
        output = render_simulator(loan, sim_loan, TODAY, "Test scenario XYZ")
        assert "Test scenario XYZ" in output

    def test_comparison_table(self):
        """R4: Comparison table with Base and Simulated columns."""
        loan = _make_loan_data()
        sim_loan = copy.deepcopy(loan)
        output = render_simulator(loan, sim_loan, TODAY, "No change baseline")
        assert "Base" in output
        assert "Simulated" in output

    def test_total_interest_row(self):
        """R4: Total Interest row appears in comparison."""
        loan = _make_loan_data()
        sim_loan = copy.deepcopy(loan)
        output = render_simulator(loan, sim_loan, TODAY, "Baseline")
        assert "Total Interest" in output

    def test_prepayment_reduces_interest(self):
        """R4: Prepayment scenario shows interest reduction."""
        loan = _make_loan_data()
        sim_loan = copy.deepcopy(loan)
        sim_loan.prepayments = [Prepayment(id="pp1", date="2026-10-01", amount=500_000)]
        output = render_simulator(loan, sim_loan, TODAY, "₹5L prepayment")
        assert "saved" in output.lower() or "earlier" in output.lower()

    def test_next_installments_comparison(self):
        """R4: Next N installments comparison section is present."""
        loan = _make_loan_data()
        sim_loan = copy.deepcopy(loan)
        output = render_simulator(loan, sim_loan, TODAY, "Baseline")
        assert "Installments" in output
        assert "Base Installment" in output
        assert "Sim Installment" in output

    def test_deterministic(self):
        """R4: Same inputs produce identical output."""
        loan = _make_loan_data()
        sim_loan = copy.deepcopy(loan)
        out1 = render_simulator(loan, sim_loan, TODAY, "Baseline")
        out2 = render_simulator(loan, sim_loan, TODAY, "Baseline")
        assert out1 == out2

    def test_rate_change_scenario(self):
        """R4: Rate change scenario shows impact."""
        loan = _make_loan_data()
        sim_loan = copy.deepcopy(loan)
        sim_loan.rateHistory.append(
            RateHistory(id="r2", effectiveDate="2026-10-01", annualRate=7.0)
        )
        output = render_simulator(loan, sim_loan, TODAY, "Rate drops to 7.0%")
        assert "Simulator" in output
        assert "Rate drops to 7.0%" in output


# ---------------------------------------------------------------------------
# R5 — render_ledger
# ---------------------------------------------------------------------------

class TestRenderLedger:
    def test_heading_present(self):
        """R5: Report heading contains 'Ledger'."""
        loan = _make_loan_data()
        od = _make_od_data()
        output = render_ledger(loan, od, TODAY)
        assert "Ledger" in output
        assert "26 Sep 2026" in output

    def test_disbursements_section(self):
        """R5: Disbursements table is present."""
        loan = _make_loan_data()
        od = _make_od_data()
        output = render_ledger(loan, od, TODAY)
        assert "Disbursements" in output
        assert "1st tranche" in output
        assert "2nd tranche" in output

    def test_disbursements_total(self):
        """R5: Disbursements total row is present."""
        loan = _make_loan_data()
        od = _make_od_data()
        output = render_ledger(loan, od, TODAY)
        assert "Total" in output

    def test_disbursement_inr_formatting(self):
        """R5: Disbursement amounts use INR formatting."""
        loan = _make_loan_data()
        od = _make_od_data()
        output = render_ledger(loan, od, TODAY)
        assert "₹59,82,984" in output  # 5,982,984

    def test_payments_section(self):
        """R5: Payments table is present."""
        loan = _make_loan_data()
        od = _make_od_data()
        output = render_ledger(loan, od, TODAY)
        assert "Payments" in output
        assert "Amount Due" in output
        assert "Amount Paid" in output

    def test_payments_type_label(self):
        """R5: Payment type is human-readable."""
        loan = _make_loan_data()
        od = _make_od_data()
        output = render_ledger(loan, od, TODAY)
        assert "Pre-EMI Interest" in output

    def test_od_balance_section(self):
        """R5: OD Balance History section is present."""
        loan = _make_loan_data()
        od = _make_od_data()
        output = render_ledger(loan, od, TODAY)
        assert "OD Balance History" in output
        assert "Purpose" in output

    def test_od_annotation_shown(self):
        """R5: OD annotation note appears in the balance history."""
        loan = _make_loan_data()
        od = _make_od_data()
        output = render_ledger(loan, od, TODAY)
        assert "Sep deposit" in output

    def test_date_format(self):
        """R5: Dates in ledger use 'DD Mon YYYY' format."""
        loan = _make_loan_data()
        od = _make_od_data()
        output = render_ledger(loan, od, TODAY)
        assert "31 Jan 2026" in output  # First disbursement date

    def test_empty_payments_shows_placeholder(self):
        """R5: Empty payment log renders a placeholder row."""
        loan = _make_loan_data()
        od = _make_od_data()
        loan.paymentLog = []
        output = render_ledger(loan, od, TODAY)
        assert "Payments" in output
        assert "—" in output

    def test_deterministic(self):
        """R5: Same inputs produce identical output."""
        loan = _make_loan_data()
        od = _make_od_data()
        out1 = render_ledger(loan, od, TODAY)
        out2 = render_ledger(loan, od, TODAY)
        assert out1 == out2
