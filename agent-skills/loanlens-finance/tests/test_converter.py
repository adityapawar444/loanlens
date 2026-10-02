import pytest
from engine.converter import dict_to_toon, toon_to_dict
from engine.types import LoanDetails, LoanData, OdSavingsData

def test_round_trip_loan():
    original_dict = {
        "loanDetails": {
            "lender": "Bank",
            "accountNumber": "12345",
            "sanctionedAmount": 1000000.0,
            "totalTenureMonths": 240,
            "moratoriumMonths": 18,
            "moratoriumAnchor": "first_disbursement",
            "dueDateDay": 10,
            "dayCountConvention": 365,
            "currentCommunicatedEmi": 10000.0,
            "policy": {
                "onPrepayment": "adjust_tenure"
            }
        },
        "disbursements": [],
        "rateHistory": [],
        "odBalanceLog": [],
        "prepayments": [],
        "paymentLog": []
    }
    
    # Dict -> TOON -> Dict
    toon_str = dict_to_toon(original_dict, "loan")
    round_trip_dict = toon_to_dict(toon_str, "loan")
    
    assert round_trip_dict == original_dict
    assert round_trip_dict["loanDetails"]["accountNumber"] == "12345"

def test_round_trip_od():
    original_dict = {
        "emiReserve": 50000.0,
        "sources": [],
        "contributions": [],
        "goals": [],
        "odBalanceAnnotations": []
    }
    
    toon_str = dict_to_toon(original_dict, "od")
    round_trip_dict = toon_to_dict(toon_str, "od")
    
    assert round_trip_dict == original_dict
