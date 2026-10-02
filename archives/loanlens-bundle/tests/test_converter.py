"""
test_converter.py — Round-trip tests for JSON↔TOON conversion.

Run with: cd loanlens-bundle && python -m pytest tests/test_converter.py -v
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

# Allow running from any CWD
BUNDLE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BUNDLE_DIR))

from engine.converter import json_to_toon, toon_to_json

DATA_DIR = BUNDLE_DIR / "data"

# ---------------------------------------------------------------------------
# Fixtures: load source JSON files
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def loan_data() -> dict:
    path = DATA_DIR / "loan_data.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def od_data() -> dict:
    path = DATA_DIR / "od_savings_data.json"
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Helper: inject [REDACTED] accountNumber into loan_data for round-trip
# ---------------------------------------------------------------------------

def _redacted_loan_data(data: dict) -> dict:
    """Return a copy of loan_data with accountNumber replaced by [REDACTED]."""
    import copy
    d = copy.deepcopy(data)
    d["loanDetails"]["accountNumber"] = "[REDACTED]"
    return d


# ---------------------------------------------------------------------------
# Structural / format tests
# ---------------------------------------------------------------------------


class TestToonStructure:
    """Verify the TOON output has the right structural shape."""

    def test_loan_toon_has_loan_details_singleton(self, loan_data):
        toon = json_to_toon(loan_data, "loan")
        assert "loanDetails:" in toon, "loanDetails singleton line must be present"

    def test_loan_toon_account_number_redacted(self, loan_data):
        toon = json_to_toon(loan_data, "loan")
        assert "83990600004041" not in toon, "Raw account number must not appear in TOON"
        assert "[REDACTED]" in toon, "[REDACTED] placeholder must be present"

    def test_loan_toon_has_all_table_headers(self, loan_data):
        toon = json_to_toon(loan_data, "loan")
        for entity in ("disbursements", "rateHistory", "odBalanceLog", "prepayments", "paymentLog"):
            assert entity in toon, f"Table '{entity}' not found in TOON"

    def test_od_toon_has_emi_reserve_scalar(self, od_data):
        toon = json_to_toon(od_data, "od")
        assert toon.startswith("emiReserve:") or "emiReserve:" in toon

    def test_od_toon_has_all_table_headers(self, od_data):
        toon = json_to_toon(od_data, "od")
        for entity in ("sources", "contributions", "goals", "odBalanceAnnotations"):
            assert entity in toon, f"Table '{entity}' not found in TOON"

    def test_toon_n_header_matches_row_count_loan(self, loan_data):
        """[N] in every table header must equal the actual number of data rows."""
        toon = json_to_toon(loan_data, "loan")
        _assert_n_headers_correct(toon)

    def test_toon_n_header_matches_row_count_od(self, od_data):
        toon = json_to_toon(od_data, "od")
        _assert_n_headers_correct(toon)

    def test_od_toon_edit_history_is_json_column(self, od_data):
        """editHistory cells must be JSON-encoded arrays."""
        toon = json_to_toon(od_data, "od")
        assert "editHistory:json" in toon, "editHistory must have :json type annotation"

    def test_loan_toon_types_present(self, loan_data):
        toon = json_to_toon(loan_data, "loan")
        assert ":num" in toon
        assert ":date" in toon
        assert ":str" in toon


def _assert_n_headers_correct(toon: str) -> None:
    """Parse every [N] entity_name header and verify N == actual subsequent row count."""
    lines = toon.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        m = re.match(r"^\[(\d+)\]\s+(\S+)$", line)
        if m:
            declared_n = int(m.group(1))
            entity = m.group(2)
            # Skip the column header line (i+1), then count data rows
            data_start = i + 2
            data_end = data_start + declared_n
            actual_rows = lines[data_start:data_end]
            assert len(actual_rows) == declared_n, (
                f"Table '{entity}': [N]={declared_n} but found {len(actual_rows)} data rows"
            )
            i = data_end
        else:
            i += 1


# ---------------------------------------------------------------------------
# Round-trip tests (primary correctness check)
# ---------------------------------------------------------------------------


class TestRoundTrip:
    """Verify that json_to_toon → toon_to_json produces deep-equal JSON."""

    def test_loan_round_trip_disbursements(self, loan_data):
        toon = json_to_toon(loan_data, "loan")
        restored = toon_to_json(toon, "loan")
        assert restored["disbursements"] == loan_data["disbursements"]

    def test_loan_round_trip_rate_history(self, loan_data):
        toon = json_to_toon(loan_data, "loan")
        restored = toon_to_json(toon, "loan")
        assert restored["rateHistory"] == loan_data["rateHistory"]

    def test_loan_round_trip_od_balance_log(self, loan_data):
        toon = json_to_toon(loan_data, "loan")
        restored = toon_to_json(toon, "loan")
        assert restored["odBalanceLog"] == loan_data["odBalanceLog"]

    def test_loan_round_trip_prepayments_empty(self, loan_data):
        toon = json_to_toon(loan_data, "loan")
        restored = toon_to_json(toon, "loan")
        assert restored["prepayments"] == []

    def test_loan_round_trip_payment_log(self, loan_data):
        toon = json_to_toon(loan_data, "loan")
        restored = toon_to_json(toon, "loan")
        assert restored["paymentLog"] == loan_data["paymentLog"]

    def test_loan_round_trip_loan_details(self, loan_data):
        """loanDetails round-trips with [REDACTED] in place of accountNumber."""
        toon = json_to_toon(loan_data, "loan")
        restored = toon_to_json(toon, "loan")
        expected = _redacted_loan_data(loan_data)["loanDetails"]
        assert restored["loanDetails"] == expected

    def test_loan_round_trip_full(self, loan_data):
        """Full deep-equality check with [REDACTED] accountNumber substituted."""
        toon = json_to_toon(loan_data, "loan")
        restored = toon_to_json(toon, "loan")
        expected = _redacted_loan_data(loan_data)
        assert restored == expected, "Full loan round-trip mismatch"

    def test_od_round_trip_emi_reserve(self, od_data):
        toon = json_to_toon(od_data, "od")
        restored = toon_to_json(toon, "od")
        assert restored["emiReserve"] == od_data["emiReserve"]

    def test_od_round_trip_sources(self, od_data):
        toon = json_to_toon(od_data, "od")
        restored = toon_to_json(toon, "od")
        assert restored["sources"] == od_data["sources"]

    def test_od_round_trip_contributions(self, od_data):
        toon = json_to_toon(od_data, "od")
        restored = toon_to_json(toon, "od")
        assert restored["contributions"] == od_data["contributions"]

    def test_od_round_trip_goals(self, od_data):
        toon = json_to_toon(od_data, "od")
        restored = toon_to_json(toon, "od")
        assert restored["goals"] == od_data["goals"]

    def test_od_round_trip_od_balance_annotations(self, od_data):
        toon = json_to_toon(od_data, "od")
        restored = toon_to_json(toon, "od")
        assert restored["odBalanceAnnotations"] == od_data["odBalanceAnnotations"]

    def test_od_round_trip_full(self, od_data):
        """Full deep-equality check for OD savings data."""
        toon = json_to_toon(od_data, "od")
        restored = toon_to_json(toon, "od")
        assert restored == od_data, "Full OD savings round-trip mismatch"

    def test_double_round_trip_loan(self, loan_data):
        """TOON→JSON→TOON→JSON must also be stable."""
        toon1 = json_to_toon(loan_data, "loan")
        mid = toon_to_json(toon1, "loan")
        toon2 = json_to_toon(mid, "loan")
        restored = toon_to_json(toon2, "loan")
        assert mid == restored, "Double round-trip not idempotent for loan data"

    def test_double_round_trip_od(self, od_data):
        toon1 = json_to_toon(od_data, "od")
        mid = toon_to_json(toon1, "od")
        toon2 = json_to_toon(mid, "od")
        restored = toon_to_json(toon2, "od")
        assert mid == restored, "Double round-trip not idempotent for OD data"


# ---------------------------------------------------------------------------
# Edge-case / null handling tests
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_arrays(self):
        """An empty array produces a header-only TOON table with [0]."""
        minimal_loan = {
            "loanDetails": {
                "lender": "Test Bank",
                "accountNumber": "0000000",
                "sanctionedAmount": 1000000,
                "totalTenureMonths": 240,
                "moratoriumMonths": 0,
                "moratoriumAnchor": "first_disbursement",
                "dueDateDay": 10,
                "dayCountConvention": 365,
                "currentCommunicatedEmi": 8000,
                "policy": {
                    "onRateChange": "adjust_tenure",
                    "onDisbursementDuringEmi": "adjust_tenure",
                    "onPrepayment": "adjust_tenure",
                },
            },
            "disbursements": [],
            "rateHistory": [],
            "odBalanceLog": [],
            "prepayments": [],
            "paymentLog": [],
        }
        toon = json_to_toon(minimal_loan, "loan")
        assert "[0] disbursements" in toon
        assert "[0] paymentLog" in toon

    def test_null_fields_survive_round_trip(self):
        """Null/missing optional fields round-trip as absent (not present with None value)."""
        disbursement_without_note = {
            "id": "test-1",
            "date": "2026-01-01",
            "amount": 500000,
            # no "note" field
        }
        minimal = {
            "loanDetails": {
                "lender": "Test",
                "accountNumber": "X",
                "sanctionedAmount": 1000000,
                "totalTenureMonths": 240,
                "moratoriumMonths": 0,
                "moratoriumAnchor": "first_disbursement",
                "dueDateDay": 10,
                "dayCountConvention": 365,
                "currentCommunicatedEmi": 8000,
                "policy": {
                    "onRateChange": "adjust_tenure",
                    "onDisbursementDuringEmi": "adjust_tenure",
                    "onPrepayment": "adjust_tenure",
                },
            },
            "disbursements": [disbursement_without_note],
            "rateHistory": [],
            "odBalanceLog": [],
            "prepayments": [],
            "paymentLog": [],
        }
        toon = json_to_toon(minimal, "loan")
        restored = toon_to_json(toon, "loan")
        # note should not appear in the restored disbursement
        assert "note" not in restored["disbursements"][0]

    def test_edit_history_with_entries_round_trips(self):
        """editHistory arrays with actual entries survive as exact JSON."""
        entry = {
            "timestamp": "2026-07-08T09:21:43.847Z",
            "field": "allocatedAmount",
            "oldValue": "0",
            "newValue": "60000",
        }
        minimal_od = {
            "emiReserve": 91143,
            "sources": [],
            "contributions": [],
            "goals": [
                {
                    "id": "test-goal",
                    "name": "Test Goal",
                    "targetAmount": 60000,
                    "allocatedAmount": 60000,
                    "color": "#0f766e",
                    "isActive": True,
                    "editHistory": [entry],
                }
            ],
            "odBalanceAnnotations": [],
        }
        toon = json_to_toon(minimal_od, "od")
        restored = toon_to_json(toon, "od")
        assert restored["goals"][0]["editHistory"] == [entry]

    def test_boolean_encoding(self):
        """isActive=True encodes as '1', False as '0', and round-trips correctly."""
        minimal_od = {
            "emiReserve": 0,
            "sources": [
                {
                    "id": "s1",
                    "name": "Test",
                    "isActive": True,
                    "createdAt": "2026-01-01T00:00:00.000Z",
                    "editHistory": [],
                },
                {
                    "id": "s2",
                    "name": "Inactive",
                    "isActive": False,
                    "createdAt": "2026-01-01T00:00:00.000Z",
                    "editHistory": [],
                },
            ],
            "contributions": [],
            "goals": [],
            "odBalanceAnnotations": [],
        }
        toon = json_to_toon(minimal_od, "od")
        assert "\t1\t" in toon or toon.count("\t1\n") > 0 or "\t1" in toon  # True → '1'
        restored = toon_to_json(toon, "od")
        assert restored["sources"][0]["isActive"] is True
        assert restored["sources"][1]["isActive"] is False

    def test_null_source_id_in_annotations_preserved(self):
        """sourceId=null in odBalanceAnnotations must survive round-trip as None."""
        minimal_od = {
            "emiReserve": 0,
            "sources": [],
            "contributions": [],
            "goals": [],
            "odBalanceAnnotations": [
                {
                    "odBalanceLogId": "abc",
                    "sourceId": None,
                    "purpose": "savings",
                    "editHistory": [],
                }
            ],
        }
        toon = json_to_toon(minimal_od, "od")
        restored = toon_to_json(toon, "od")
        assert restored["odBalanceAnnotations"][0]["sourceId"] is None

    def test_invalid_kind_raises(self):
        with pytest.raises(ValueError, match="Unknown kind"):
            json_to_toon({}, "unknown")
        with pytest.raises(ValueError, match="Unknown kind"):
            toon_to_json("", "unknown")


# ---------------------------------------------------------------------------
# TOON file existence tests (verify generated files are on disk)
# ---------------------------------------------------------------------------


class TestGeneratedFiles:
    def test_loan_toon_file_exists(self):
        path = DATA_DIR / "loan_data.v001.toon"
        assert path.exists(), f"Expected TOON file not found: {path}"

    def test_od_toon_file_exists(self):
        path = DATA_DIR / "od_savings.v001.toon"
        assert path.exists(), f"Expected TOON file not found: {path}"

    def test_loan_toon_round_trips_from_disk(self, loan_data):
        path = DATA_DIR / "loan_data.v001.toon"
        toon = path.read_text(encoding="utf-8")
        restored = toon_to_json(toon, "loan")
        expected = _redacted_loan_data(loan_data)
        assert restored == expected, "Disk TOON round-trip mismatch for loan_data"

    def test_od_toon_round_trips_from_disk(self, od_data):
        path = DATA_DIR / "od_savings.v001.toon"
        toon = path.read_text(encoding="utf-8")
        restored = toon_to_json(toon, "od")
        assert restored == od_data, "Disk TOON round-trip mismatch for od_savings"
