# P1-01: Schema Extraction & Logic Spec

## Goal
Extract every formula, rounding point, date rule, and invariant from the LoanLens TypeScript codebase into two reference documents: a language-neutral logic spec and a data schema reference.

## Inputs
- `src/lib/calculations.ts` — core engine (388 lines): `calculateEmi`, `calculateTenure`, `generateSchedule`, `calculateMetrics`, `autoDeductPayments`
- `src/lib/types.ts` — Zod schemas for loan data (105 lines)
- `src/lib/od-savings-types.ts` — Zod schemas for OD savings data (145 lines)
- `Agent_Docs/plan/00-change-audit.md` — verified code behaviour references

## Outputs
- `loanlens-bundle/spec/logic-spec.md` — every formula with exact rounding rules
- `loanlens-bundle/spec/schemas.md` — every entity, field, type, constraint, default

## Logic Spec Must Cover
1. EMI formula: `P × r × (1+r)^n / ((1+r)^n - 1)`, `r = rate/12/100`, `Math.round()`
2. Tenure inverse: `ceil(ln(EMI/(EMI-P×r)) / ln(1+r))`, Infinity guard
3. Daily interest loop: day-by-day between due dates, `dailyRate = rate/100/dayCount`
4. OD offset: `effectivePrincipal = max(0, outstanding - odBalanceAt(date))`
5. Baseline interest: accrued on full outstanding (no OD offset)
6. Interest savings: `max(0, round(baseline) - round(interest))`
7. HISTORICAL_PAYMENT_DATES override (L6-12, L153-168): exact set and logic
8. Moratorium→EMI transition (L134-143): `period > moratoriumMonths`
9. Prepayment policy: adjust_tenure vs adjust_emi (L137-142, L202-207)
10. Rate lookup: step function, last rate where `effectiveDate <= dateKey` (L83-91)
11. OD balance lookup: step function, last balance where `date <= dateKey` (L93-100)
12. Safety break: `period > 600` (L226)
13. Rounding inventory: every `Math.round()` call with its context
14. autoDeductPayments: loop, schedule regeneration, OD snapshot creation (L305-387)
15. Opening balance formula: `round(outstanding + principalPaid)` for EMI phase

## Schema Doc Must Cover
- Every Zod schema with field names, types, constraints (min/max/regex/enum/default)
- PositiveMoneySchema and NonNegativeMoneySchema validation rules
- AuditRecord shape
- Which entities have editHistory vs. which don't

## Constraints
- Evidence rule: cite file:line for every claim
- Mark each claim VERIFIED or INFERRED
- Do NOT copy account numbers into the spec

## Verifier
```bash
# Count rounding points in code vs spec
CODE_ROUNDS=$(grep -c "Math.round" src/lib/calculations.ts)
SPEC_ROUNDS=$(grep -c "round()" loanlens-bundle/spec/logic-spec.md)
echo "Code: $CODE_ROUNDS, Spec: $SPEC_ROUNDS — spec must be >= code count"
```

## Done Signal
Both files exist. Every `Math.round()`, every date operation, and every branch in `generateSchedule` has a corresponding spec entry. Schema doc covers all 13 Zod schemas.
