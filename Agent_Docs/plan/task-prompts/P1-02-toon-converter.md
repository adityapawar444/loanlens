# P1-02: JSON→TOON Converter + Round-Trip Tests

## Goal
Build a Python converter that transforms LoanLens JSON data files into TOON (Token-Optimized Object Notation) format and back, with lossless round-trip fidelity.

## TOON Format
- First line: `[N] entity_name` where N = row count
- Second line: tab-separated column headers with `:type` suffix (str, num, date, bool, json)
- Remaining N lines: tab-separated values
- Null/missing: empty cell. Booleans: 1/0. Dates: YYYY-MM-DD.
- Nested arrays (editHistory): encode as `json` type column

## Inputs
- `data/loan_data.json` — loan data (3,448 bytes)
- `data/od_savings_data.json` — OD savings data (9,879 bytes)
- `Agent_Docs/plan/02-design.md` §A — full TOON spec
- `src/lib/types.ts` and `src/lib/od-savings-types.ts` — Zod schemas

## Outputs
- `loanlens-bundle/engine/converter.py` — functions: `json_to_toon()`, `toon_to_json()`
- `loanlens-bundle/tests/test_converter.py` — round-trip tests
- `loanlens-bundle/data/loan_data.v001.toon`
- `loanlens-bundle/data/od_savings.v001.toon`

## Constraints
- `loanDetails` (nested singleton) stays as inline JSON within the TOON file
- `emiReserve` (scalar) stays as a key:value line
- All uniform arrays convert to TOON tables
- Account number in loanDetails must be redacted as `[REDACTED]`
- `[N]` header must match actual row count after conversion

## Verifier
```bash
cd loanlens-bundle && python -m pytest tests/test_converter.py -v
```
All tests pass. Additionally verify:
```bash
python -c "from engine.converter import json_to_toon, toon_to_json; import json; d=json.load(open('data/loan_data.json')); t=json_to_toon(d, 'loan'); r=toon_to_json(t, 'loan'); assert d==r, 'Round-trip failed'"
```

## Done Signal
All tests pass. TOON files exist. Round-trip produces identical JSON (deep equality).
