# P1-04: Python Engine (Schedule + Metrics + EMI)

## Goal
Port the core LoanLens financial engine from TypeScript to Python. The Python engine must produce **byte-identical** rounded outputs for all money fields when given the same inputs as the TypeScript version.

## Inputs
- `loanlens-bundle/spec/logic-spec.md` — every formula, rounding point, date rule
- `loanlens-bundle/spec/schemas.md` — data schemas
- `src/lib/calculations.ts` — TypeScript reference implementation (for cross-checking)
- `loanlens-bundle/fixtures/base.json` — golden fixture for initial verification

## Outputs
- `loanlens-bundle/engine/__init__.py`
- `loanlens-bundle/engine/types.py` — Pydantic models mirroring Zod schemas
- `loanlens-bundle/engine/emi.py` — `calculate_emi()`, `calculate_tenure()`
- `loanlens-bundle/engine/schedule.py` — `generate_schedule()`
- `loanlens-bundle/engine/metrics.py` — `calculate_metrics()`
- `loanlens-bundle/engine/auto_deduct.py` — `auto_deduct_payments()`

## Critical Parity Rules
1. **`round()` in Python uses banker's rounding; JS `Math.round()` uses half-up.** You MUST use `int(x + 0.5)` or `math.floor(x + 0.5)` to match JS behaviour, NOT Python's built-in `round()`.
2. **Date arithmetic:** JS `new Date(year, month, day)` with `setDate(getDate()+1)` must match Python's `datetime.date` arithmetic. Pay attention to month-end boundaries.
3. **Floating-point accumulation:** Interest accrues day-by-day as float addition. Ensure the Python loop matches JS's IEEE 754 float addition order exactly. Accumulate in the same order: dailyRate first, then multiply, then add.
4. **`today` is always an explicit parameter**, never `datetime.now()`.

## Module Design

### types.py
- `LoanDetails`, `Disbursement`, `RateHistory`, `OdBalanceLog`, `Prepayment`, `PaymentLog` — Pydantic models
- `LoanData` — container model
- `AmortizationRow`, `SummaryMetrics` — output types
- `OdSavingsData` — with sources, goals, contributions, annotations

### emi.py
```python
def calculate_emi(principal: float, annual_rate: float, tenure_months: int) -> int:
    # Returns rounded EMI (half-up, not banker's)

def calculate_tenure(principal: float, annual_rate: float, emi: int) -> int | float:
    # Returns ceil(tenure) or math.inf
```

### schedule.py
```python
def generate_schedule(data: LoanData, today_date: str | None = None) -> list[AmortizationRow]:
    # Day-by-day interest accrual loop
    # Matches calculations.ts L60-232 exactly
```

### metrics.py
```python
def calculate_metrics(data: LoanData, schedule: list[AmortizationRow], today_date: str | None = None) -> SummaryMetrics:
    # Matches calculations.ts L235-298 exactly
```

## Constraints
- Python 3.10+ (use `match` statements if helpful)
- Use `pydantic` for data models (v2)
- No external dependencies beyond `pydantic` and stdlib
- No network access
- `HISTORICAL_PAYMENT_DATES` hardcoded to same 5 dates as TS

## Verifier
```bash
cd loanlens-bundle
python -c "
from engine.schedule import generate_schedule
from engine.metrics import calculate_metrics
from engine.types import LoanData
import json

fixture = json.load(open('fixtures/base.json'))
data = LoanData(**fixture['input'])
schedule = generate_schedule(data)
metrics = calculate_metrics(data, schedule, '2026-09-19')

# Check first 3 rows
for i in range(min(3, len(schedule))):
    expected = fixture['expected_schedule'][i]
    actual = schedule[i]
    for field in ['openingBalance', 'installment', 'interest', 'principal', 'closingBalance']:
        assert getattr(actual, field) == expected[field], f'Row {i} {field}: {getattr(actual, field)} != {expected[field]}'
print('First 3 rows match!')
"
```

## Done Signal
Engine loads without error. Base fixture first 3 schedule rows match exactly on all money fields. All metrics match.
