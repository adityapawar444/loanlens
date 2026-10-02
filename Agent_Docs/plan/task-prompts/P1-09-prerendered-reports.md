# P1-09: Pre-Rendered Reports (Tier C Fallback)

## Goal
Generate pre-rendered markdown reports from current loan data using the Python engine. These reports serve as the Tier C fallback when code execution is unavailable in Claude Desktop.

## Inputs
- `loanlens-bundle/engine/renderer.py` — render functions (from P1-06)
- `loanlens-bundle/engine/schedule.py`, `metrics.py` — computation (from P1-04)
- `data/loan_data.json`, `data/od_savings_data.json` — current data

## Outputs
- `loanlens-bundle/reports/summary_20260919.md`
- `loanlens-bundle/reports/od_savings_20260919.md`
- `loanlens-bundle/reports/schedule_20260919.md`
- `loanlens-bundle/reports/ledger_20260919.md`

## Constraints
- Pin `today_date` to `2026-09-19`
- Redact account number: use `[REDACTED]` or omit entirely
- Redact personal names in sources: use `Source 1`, `Source 2`, etc.
- Each report must be within its token budget (summary ≤400, OD ≤600, schedule ≤800, ledger ≤500)

## Verifier
```bash
ls loanlens-bundle/reports/ | wc -l  # must be 4
grep -r "83990600004041" loanlens-bundle/reports/  # must return nothing
```

## Done Signal
4 report files exist. No PII. Within token budgets.
