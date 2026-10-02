import pytest
from engine.schedule import generate_schedule
from engine.types import LoanData, LoanDetails, Policy, Disbursement, RateHistory

@pytest.fixture
def sample_loan():
    return LoanData(
        loanDetails=LoanDetails(
            lender="Test",
            accountNumber="123",
            sanctionedAmount=100000.0,
            totalTenureMonths=12,
            moratoriumMonths=0,
            moratoriumAnchor="first_disbursement",
            dueDateDay=10,
            currentCommunicatedEmi=8500.0,
            policy=Policy(onPrepayment="adjust_tenure")
        ),
        disbursements=[
            Disbursement(id="1", date="2027-01-01", amount=100000.0)
        ],
        rateHistory=[
            RateHistory(id="r1", effectiveDate="2027-01-01", annualRate=10.0)
        ],
        odBalanceLog=[],
        prepayments=[],
        paymentLog=[]
    )

def test_generate_schedule(sample_loan):
    schedule = generate_schedule(sample_loan)
    assert len(schedule) > 0
    assert schedule[0].dueDate == "2027-02-10"
    assert schedule[0].closingBalance < 100000.0
