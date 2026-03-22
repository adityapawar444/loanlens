from datetime import date
from decimal import Decimal

import pytest

from loanlens.models import AdjustmentMode, LoanProfile, RoiType


@pytest.fixture
def test_loan() -> LoanProfile:
    return LoanProfile(
        name="Test SBI Loan",
        bank_name="SBI",
        account_number="SBI12345678",
        sanction_amount=Decimal("5000000"),
        disbursed_amount=Decimal("5000000"),
        disbursement_date=date(2024, 4, 1),
        roi_initial=Decimal("8.75"),
        roi_type=RoiType.FLOATING,
        tenure_months=240,
        emi_start_date=date(2024, 5, 1),
        emi_day=5,
        adjustment_mode=AdjustmentMode.ADJUST_EMI,
        prepayment_charges_pct=Decimal("0"),
        emi_rounding="rupee",
    )
