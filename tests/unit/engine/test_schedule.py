from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from loanlens.config import AppConfig
from loanlens.engine.schedule import (
    _apply_adjustment_mode,
    _monthly_od_saving,
    _status_for_row,
    generate_schedule,
)
from loanlens.models import (
    AdjustmentMode,
    LoanProfile,
    Moratorium,
    MoratoriumType,
    ODTransaction,
    Payment,
    RateRevision,
    RoiType,
    ScheduleStatus,
)


def test_generate_schedule_basic_exact_rows() -> None:
    loan = LoanProfile(
        name="One Year Loan",
        bank_name="Test",
        account_number="123",
        sanction_amount=Decimal("120000"),
        disbursed_amount=Decimal("120000"),
        disbursement_date=date(2024, 4, 1),
        roi_initial=Decimal("12"),
        roi_type=RoiType.FLOATING,
        tenure_months=12,
        emi_start_date=date(2024, 5, 1),
        emi_day=5,
        adjustment_mode=AdjustmentMode.ADJUST_EMI,
        prepayment_charges_pct=Decimal("0"),
        emi_rounding="rupee",
    )

    rows = generate_schedule(loan, [], [], [], [], AppConfig())

    assert len(rows) == 12
    assert rows[0].due_date == date(2024, 5, 5)
    assert rows[0].opening_principal == Decimal("120000.00")
    assert rows[0].emi_amount == Decimal("10662")
    assert rows[0].interest_component == Decimal("1200.00")
    assert rows[0].principal_component == Decimal("9462.00")
    assert rows[0].closing_principal == Decimal("110538.00")
    assert rows[-1].due_date == date(2025, 4, 5)
    assert rows[-1].emi_amount == Decimal("10660.16")
    assert rows[-1].interest_component == Decimal("105.55")
    assert rows[-1].closing_principal == Decimal("0.00")


def test_generate_schedule_applies_rate_revision_mid_loan(test_loan: LoanProfile) -> None:
    revision = RateRevision(
        loan_id=test_loan.loan_id,
        effective_date=date(2025, 5, 5),
        old_roi=Decimal("8.75"),
        new_roi=Decimal("9.25"),
        adjustment_mode=AdjustmentMode.ADJUST_EMI,
    )

    rows = generate_schedule(test_loan, [revision], [], [], [], AppConfig())

    assert rows[11].emi_amount == Decimal("44186")
    assert rows[12].emi_amount > rows[11].emi_amount


def test_generate_schedule_handles_moratorium_with_capitalisation(test_loan: LoanProfile) -> None:
    moratorium = Moratorium(
        loan_id=test_loan.loan_id,
        from_date=date(2024, 7, 5),
        to_date=date(2024, 8, 5),
        moratorium_type=MoratoriumType.INTEREST_CAPITALISE,
    )

    rows = generate_schedule(test_loan, [], [moratorium], [], [], AppConfig())

    moratorium_rows = [row for row in rows if row.status == ScheduleStatus.MORATORIUM]
    assert len(moratorium_rows) == 2
    assert moratorium_rows[0].closing_principal > moratorium_rows[0].opening_principal
    assert len(rows) > test_loan.tenure_months


def test_generate_schedule_applies_prepayment_reduce_tenure() -> None:
    loan = LoanProfile(
        name="Prepay Loan",
        bank_name="Test",
        account_number="123",
        sanction_amount=Decimal("1000000"),
        disbursed_amount=Decimal("1000000"),
        disbursement_date=date(2024, 1, 1),
        roi_initial=Decimal("10"),
        roi_type=RoiType.FLOATING,
        tenure_months=24,
        emi_start_date=date(2024, 2, 1),
        emi_day=5,
        adjustment_mode=AdjustmentMode.ADJUST_TENURE,
        prepayment_charges_pct=Decimal("0"),
        emi_rounding="rupee",
    )
    payment = Payment(
        loan_id=loan.loan_id,
        payment_date=date(2024, 6, 5),
        amount=Decimal("100000"),
        payment_type="PREPAYMENT",
    )

    rows = generate_schedule(loan, [], [], [payment], [], AppConfig())

    assert len(rows) < 24
    assert rows[4].prepayment_amount == Decimal("100000.00")


def test_generate_schedule_applies_prepayment_reduce_emi() -> None:
    loan = LoanProfile(
        name="Prepay Loan",
        bank_name="Test",
        account_number="123",
        sanction_amount=Decimal("1000000"),
        disbursed_amount=Decimal("1000000"),
        disbursement_date=date(2024, 1, 1),
        roi_initial=Decimal("10"),
        roi_type=RoiType.FLOATING,
        tenure_months=24,
        emi_start_date=date(2024, 2, 1),
        emi_day=5,
        adjustment_mode=AdjustmentMode.ADJUST_EMI,
        prepayment_charges_pct=Decimal("0"),
        emi_rounding="rupee",
    )
    payment = Payment(
        loan_id=loan.loan_id,
        payment_date=date(2024, 6, 5),
        amount=Decimal("100000"),
        payment_type="PREPAYMENT",
    )

    rows = generate_schedule(loan, [], [], [payment], [], AppConfig())

    assert rows[5].emi_amount < rows[4].emi_amount


def test_schedule_helpers_cover_remaining_branches() -> None:
    assert _status_for_row(date(2099, 1, 1), None, [], Decimal("0")) == ScheduleStatus.UPCOMING
    assert _status_for_row(date(2024, 1, 1), None, [], Decimal("1")) == ScheduleStatus.PREPAID
    payment = Payment(
        loan_id=LoanProfile(
            name="Tmp",
            bank_name="Tmp",
            account_number="1",
            sanction_amount=Decimal("1000"),
            disbursed_amount=Decimal("1000"),
            disbursement_date=date(2024, 1, 1),
            roi_initial=Decimal("10"),
            roi_type=RoiType.FLOATING,
            tenure_months=1,
            emi_start_date=date(2024, 2, 1),
            emi_day=5,
            adjustment_mode=AdjustmentMode.ADJUST_EMI,
            prepayment_charges_pct=Decimal("0"),
            emi_rounding="rupee",
        ).loan_id,
        payment_date=date(2024, 1, 1),
        amount=Decimal("100"),
        payment_type="EMI",
    )
    assert _status_for_row(date(2024, 1, 1), None, [payment], Decimal("0")) == ScheduleStatus.PAID
    moratorium = Moratorium(
        loan_id=payment.loan_id,
        from_date=date(2024, 1, 1),
        to_date=date(2024, 1, 1),
        moratorium_type=MoratoriumType.INTEREST_DEFER,
    )
    assert (
        _status_for_row(date(2024, 1, 1), moratorium, [], Decimal("0"))
        == ScheduleStatus.MORATORIUM
    )
    assert _monthly_od_saving(Decimal("1000"), date(2024, 1, 5), Decimal("10"), []) == Decimal("0")
    od_txn = ODTransaction(
        od_account_id=uuid4(),
        loan_id=payment.loan_id,
        txn_type="DEPOSIT",
        amount=Decimal("500"),
        txn_date=date(2024, 1, 2),
        balance_after=Decimal("500"),
    )
    assert (
        _monthly_od_saving(Decimal("1000"), date(2024, 1, 5), Decimal("10"), [od_txn])
        > Decimal("0")
    )

    assert _apply_adjustment_mode(
        AdjustmentMode.ADJUST_EMI,
        Decimal("1000"),
        Decimal("10"),
        0,
        Decimal("100"),
        "rupee",
    ) == (Decimal("100"), 0)
    assert _apply_adjustment_mode(
        AdjustmentMode.ADJUST_TENURE,
        Decimal("1000"),
        Decimal("0"),
        12,
        Decimal("100"),
        "rupee",
    ) == (Decimal("100"), 10)

    with pytest.raises(ValueError):
        _apply_adjustment_mode(
            AdjustmentMode.ADJUST_TENURE,
            Decimal("1000"),
            Decimal("12"),
            12,
            Decimal("1"),
            "rupee",
        )
