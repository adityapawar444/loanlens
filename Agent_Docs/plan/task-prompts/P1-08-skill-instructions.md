# P1-08: SKILL.md + Claude Project Instructions

## Goal
Draft the Claude skill definition and Project instruction text for the LoanLens conversational version. These must be complete, PII-free, and reference the correct bundle file paths.

## Inputs
- `Agent_Docs/plan/02-design.md` §G — skill design spec
- `Agent_Docs/plan/02-design.md` §D — operations catalog
- `Agent_Docs/plan/02-design.md` §C — report formats
- `loanlens-bundle/engine/` — Python engine modules (for accurate function names)

## Outputs
- `loanlens-bundle/SKILL.md` — Claude skill definition
- `loanlens-bundle/project-instructions.md` — Claude Project instruction text

## SKILL.md Requirements
1. **Description:** 1-2 sentences explaining what LoanLens does
2. **Trigger:** When user asks about home loan, EMI, OD, interest, savings, payments
3. **Protocol:** 5-step flow (resolve data → load → compute → render/mutate → respond)
4. **Operations list:** All 5 read ops (R1-R5) and 15 write ops (W1-W15) with brief descriptions
5. **Formatting rules:** INR grouping, date format, deterministic rendering
6. **Error handling:** Missing data, validation failure, computation error
7. **Invariants:** Checked after every mutation (disbursed ≤ sanctioned, OD ≥ 0, etc.)
8. **File paths:** Reference `data/`, `engine/`, `fixtures/` within the bundle

## Project Instructions Requirements
1. Context about the loan (lender type, loan type, current phase, rate, day count)
2. Key behavioural rules (use engine for math, never estimate, redact PII)
3. Reference to the SKILL.md
4. **Must NOT contain:** account numbers, personal names, specific balances

## Constraints
- Max ~120 lines for SKILL.md
- Max ~30 lines for project-instructions.md
- No PII: `grep -ri "83990600004041\|aditya\|shravi\|pawar" SKILL.md project-instructions.md` must return 0 results
- Use generic references: "the user's home loan" not "[Name]'s loan"

## Verifier
```bash
cd loanlens-bundle
# No PII
grep -ricE "83990600004041|aditya|shravi|pawar" SKILL.md project-instructions.md | grep -v ":0$" && echo "FAIL: PII found" || echo "PASS: No PII"
# All operations referenced
for op in R1 R2 R3 R4 R5 W1 W2 W3 W4 W5 W6 W7 W8 W9 W10 W11 W12 W13 W14 W15; do
  grep -q "$op" SKILL.md || echo "MISSING: $op"
done
```

## Done Signal
Both files exist. No PII found. All 20 operation IDs appear in SKILL.md.
