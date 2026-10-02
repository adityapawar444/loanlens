# P1-03: Golden Fixture Generation (TypeScript)

## Goal
Generate 8 golden test fixtures by RUNNING the TypeScript `generateSchedule()` and `calculateMetrics()` functions on pinned input data. Never hand-copy dashboard numbers.

## Inputs
- `src/lib/calculations.ts` — `generateSchedule`, `calculateMetrics`, `calculateEmi`
- `src/lib/types.ts` — type definitions
- Current `data/loan_data.json` for the base scenario

## Outputs
- `scripts/generate-fixtures.ts` — script that produces all fixtures
- `loanlens-bundle/fixtures/base.json`
- `loanlens-bundle/fixtures/prepayment.json` (₹5,00,000 on 2026-10-01)
- `loanlens-bundle/fixtures/rate-change.json` (7.0% from 2026-10-01)
- `loanlens-bundle/fixtures/od-change.json` (OD → ₹15,00,000 from 2026-10-01)
- `loanlens-bundle/fixtures/disbursement-during-emi.json` (₹10,00,000 on 2027-10-01)
- `loanlens-bundle/fixtures/moratorium-boundary.json` (verify period 18→19)
- `loanlens-bundle/fixtures/zero-od.json` (empty odBalanceLog)
- `loanlens-bundle/fixtures/high-prepayment.json` (₹70,00,000 on 2027-09-01)

## Each Fixture File Format
```json
{
  "scenario": "base",
  "description": "Current real data, no modifications",
  "input": { /* full LoanData object */ },
  "expected_schedule": [ /* full AmortizationRow[] */ ],
  "expected_metrics": { /* full SummaryMetrics, today=2026-09-19 */ }
}
```

## Constraints
- Use `npx tsx` to run the script
- Redact account number in fixture inputs: replace with "REDACTED"
- Pin `todayDate` to `2026-09-19` for metrics computation
- Include the FULL schedule (all rows), not just a sample

## Verifier
```bash
npx tsx scripts/generate-fixtures.ts && ls loanlens-bundle/fixtures/ | wc -l
```
Must output `8`. Each JSON must have `input`, `expected_schedule`, `expected_metrics` keys.

## Done Signal
8 fixture files exist with correct structure. Script runs without error.
