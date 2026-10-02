# P1-06: Python Renderer (Markdown Reports)

## Goal
Build deterministic markdown report renderer for all 5 LoanLens report types.

## Inputs
- `Agent_Docs/plan/02-design.md` §C — report designs with examples
- `loanlens-bundle/engine/types.py` — Pydantic models
- `loanlens-bundle/engine/metrics.py` — metrics computation

## Outputs
- `loanlens-bundle/engine/renderer.py` — 5 render functions
- `loanlens-bundle/tests/test_renderer.py` — tests

## Report Functions
1. `render_summary(metrics, loan_data, od_data, today) -> str`
2. `render_od_savings(metrics, loan_data, od_data, today) -> str`
3. `render_schedule(schedule, metrics, today, window=6) -> str`
4. `render_simulator(base_metrics, sim_metrics, base_schedule, sim_schedule, changes) -> str`
5. `render_ledger(loan_data, today) -> str`

## Formatting Rules
- INR: Indian digit grouping (₹12,34,567 not ₹1,234,567)
- Dates: "10 Aug 2026" in reports (human-readable)
- Percentages: 2 decimal places
- Schedule: windowed (next N rows + yearly rollup + closure row)
- All output is deterministic — same inputs always produce same output

## Token Budgets
Summary ≤ 400, OD Savings ≤ 600, Schedule ≤ 800, Simulator ≤ 600, Ledger ≤ 500

## Constraints
- Never expose account number (use [REDACTED] or omit)
- Renderer takes pre-computed values — never calls the schedule engine itself
- Use `locale` or manual formatting for Indian digit grouping

## Verifier
```bash
cd loanlens-bundle && python -m pytest tests/test_renderer.py -v
```
All pass. Each rendered report contains `₹` and proper digit grouping. Token counts within budget.

## Done Signal
5 render functions exist. All tests pass. No PII in output.
