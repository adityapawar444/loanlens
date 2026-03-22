from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from loanlens.models import AdjustmentMode, LoanProfile, RoiType


def test_loan_profile_rejects_disbursed_greater_than_sanction() -> None:
    with pytest.raises(ValidationError):
        LoanProfile(
            name="Bad Loan",
            bank_name="Bank",
            account_number="123",
            sanction_amount=Decimal("10"),
            disbursed_amount=Decimal("11"),
            disbursement_date=date(2024, 1, 1),
            roi_initial=Decimal("8"),
            roi_type=RoiType.FLOATING,
            tenure_months=12,
            emi_start_date=date(2024, 2, 1),
            emi_day=1,
            adjustment_mode=AdjustmentMode.ADJUST_EMI,
            prepayment_charges_pct=Decimal("0"),
            emi_rounding="rupee",
        )
