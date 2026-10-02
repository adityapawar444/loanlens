# P1-07: TS↔Python Parity Harness

## Goal
Build and run a parity test suite that verifies the Python engine produces **identical** output to the TypeScript engine for all 8 fixture scenarios. Debug and fix any mismatches.

## Inputs
- `loanlens-bundle/fixtures/*.json` — 8 golden fixtures (from P1-03)
- `loanlens-bundle/engine/` — Python engine (from P1-04)
- `src/lib/calculations.ts` — TypeScript reference (for debugging)

## Outputs
- `loanlens-bundle/tests/test_parity.py` — parametrized test suite

## Test Structure
```python
import pytest, json, glob

FIXTURES = glob.glob("fixtures/*.json")

@pytest.mark.parametrize("fixture_path", FIXTURES)
def test_schedule_parity(fixture_path):
    fixture = json.load(open(fixture_path))
    data = LoanData(**fixture["input"])
    schedule = generate_schedule(data)
    
    for i, (actual, expected) in enumerate(zip(schedule, fixture["expected_schedule"])):
        for field in ["period", "dueDate", "openingBalance", "installment",
                       "interest", "baselineInterest", "interestSavings",
                       "principal", "closingBalance", "phase", "effectivePrincipal"]:
            assert getattr(actual, field) == expected[field], \
                f"Scenario {fixture_path}, row {i}, field {field}"
    
    assert len(schedule) == len(fixture["expected_schedule"])

@pytest.mark.parametrize("fixture_path", FIXTURES)
def test_metrics_parity(fixture_path):
    fixture = json.load(open(fixture_path))
    data = LoanData(**fixture["input"])
    schedule = generate_schedule(data)
    metrics = calculate_metrics(data, schedule, "2026-09-19")
    
    for field in fixture["expected_metrics"]:
        assert getattr(metrics, field) == fixture["expected_metrics"][field], \
            f"Scenario {fixture_path}, metrics.{field}"
```

## Tolerance Rules
- **Integer money fields** (interest, principal, installment, openingBalance, closingBalance, interestSavings, baselineInterest, effectivePrincipal): **exact match** (±0)
- **Date strings** (dueDate, projectedClosureDate, nextDueDate): **exact match**
- **Period number**: **exact match**
- **Phase string**: **exact match**
- **Percentage fields** (effectiveInterestRate): match to **2 decimal places**
- **Schedule length**: **exact match**

## Common Parity Failure Points (debug checklist)
1. Python `round()` uses banker's rounding → must use `int(x + 0.5)` for half-up
2. Date month-boundary arithmetic differs between JS Date and Python datetime
3. Float accumulation order affects final rounded value — ensure same order
4. JS `String.localeCompare()` vs Python string comparison for date sorting
5. JS `Array.find()` returns first match; Python list iteration must match
6. Off-by-one in moratorium transition (`period > moratoriumMonths` not `>=`)

## Constraints
- If a parity failure is found, fix the Python engine — do NOT modify fixtures
- Document each fix with the root cause
- All 8 scenarios must pass before this task is done

## Verifier
```bash
cd loanlens-bundle && python -m pytest tests/test_parity.py -v --tb=short
```
All 16 tests (8 schedule + 8 metrics) pass.

## Done Signal
`python -m pytest tests/test_parity.py` reports 16 passed, 0 failed.
