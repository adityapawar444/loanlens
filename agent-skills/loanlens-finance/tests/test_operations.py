import pytest
from engine.operations import validate_invariants, add_disbursement
from engine.types import LoanData, OdSavingsData, LoanDetails, Policy, Disbursement

@pytest.fixture
def empty_loan():
    return LoanData(
        loanDetails=LoanDetails(
            lender="Test",
            accountNumber="123",
            sanctionedAmount=10000.0,
            totalTenureMonths=120,
            moratoriumMonths=0,
            moratoriumAnchor="first_disbursement",
            dueDateDay=5,
            currentCommunicatedEmi=100.0,
            policy=Policy(onPrepayment="adjust_tenure")
        ),
        disbursements=[],
        rateHistory=[],
        odBalanceLog=[],
        prepayments=[],
        paymentLog=[]
    )

@pytest.fixture
def empty_od():
    return OdSavingsData()

def test_validate_invariants_disbursement_exceeds(empty_loan, empty_od):
    empty_loan.disbursements.append(
        Disbursement(id="1", date="2026-01-01", amount=20000.0)
    )
    with pytest.raises(ValueError, match="Total disbursed"):
        validate_invariants(empty_loan, empty_od)

def test_add_disbursement_success(empty_loan):
    impact = add_disbursement(empty_loan, "2026-01-02", "2026-01-01", 5000.0, commit=True)
    assert len(empty_loan.disbursements) == 1
    assert empty_loan.disbursements[0].amount == 5000.0
