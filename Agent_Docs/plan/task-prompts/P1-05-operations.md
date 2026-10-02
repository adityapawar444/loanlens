# P1-05: Python Operations Module

## Goal
Implement all 15 write operations (W1-W15) for the LoanLens engine in Python, with input validation, dry-run preview, and commit semantics.

## Inputs
- `Agent_Docs/plan/02-design.md` §D — full operation catalog
- `loanlens-bundle/engine/types.py` — Pydantic models (from P1-04)
- `loanlens-bundle/engine/schedule.py` — schedule generation (from P1-04)

## Outputs
- `loanlens-bundle/engine/operations.py` — all 15 operations
- `loanlens-bundle/tests/test_operations.py` — tests (≥2 per operation)

## Operation List
W1 update_od_balance, W2 add_disbursement, W3 add_prepayment,
W4 add_rate_change, W5 update_payment, W6 update_emi_reserve,
W7 add_source, W8 edit_source, W9 add_goal, W10 edit_goal,
W11 add_contribution, W12 edit_contribution, W13 edit_od_annotation,
W14 process_due_payments, W15 update_settings

## Each Operation Must
1. Accept typed inputs (Pydantic validated)
2. Load current data from JSON/dict
3. Validate business rules (amounts > 0, ≤ 10Cr, 2dp, etc.)
4. Apply mutation to in-memory copy (dry-run)
5. Return impact summary (before/after metrics diff)
6. Optionally commit (write back to data)
7. Append to editHistory where applicable (sources, goals, contributions, annotations)

## Constraints
- `today` is always explicit, never system clock
- Over-allocation: warn but don't block (match app behaviour)
- Duplicate source name check is case-insensitive
- ID generation: use `uuid4().hex[:9]` not `Math.random()`

## Verifier
```bash
cd loanlens-bundle && python -m pytest tests/test_operations.py -v
```
All tests pass. Count of test functions ≥ 30 (2 per operation).

## Done Signal
All 15 operations implemented. All tests pass. Each operation has happy-path + validation-failure tests.
