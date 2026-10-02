# LoanLens v2 — Execution Guide

**Produced:** 2026-09-20  
**Scope:** End-to-end walkthrough for executing the Phase 1 + Phase 2 plan  
**Prerequisite:** Read [05-open-questions.md](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/Agent_Docs/plan/05-open-questions.md) and resolve at least Q1 (TOON vs JSON) and Q2 (Python vs TS) before starting.

---

## How This Guide Works

Each session below is a **self-contained Antigravity CLI run** (Phase 1) or a **Claude Desktop interaction** (Phase 2). You copy-paste the prompt file into a fresh session, let it run, verify the output, then move to the next session.

The guide is organised into **8 sessions** for Phase 1 and **4 sessions** for Phase 2. Sessions that can run in parallel are marked. Estimated wall-clock time is **5–6 hours** for Phase 1 and **1.5–2 hours** for Phase 2.

---

## Before You Start

### 1. Create the bundle directory

```bash
mkdir -p loanlens-bundle/{engine,spec,data,fixtures,tests,reports,archive}
```

### 2. Confirm your toolchain

```bash
# Node/TypeScript (for fixture generation)
npx tsx --version          # needs tsx for running TS scripts

# Python (for the engine)
python3 --version          # needs 3.10+
pip install pydantic       # engine dependency

# Test runner
pip install pytest
```

### 3. Resolve the blocking open questions

| Question | Your answer needed before... |
|---|---|
| **Q1: TOON vs JSON** | Session 2 (converter). If you choose "keep JSON", skip Session 2 entirely and adjust Session 7 (bundle) to package JSON files instead of TOON. |
| **Q2: Python vs TS** | Session 4 (engine). If you choose "keep TS", skip Sessions 4–6, build a TS-based bundle instead, and accept Tier C only in Phase 2. |
| Q3–Q10 | Can be resolved during execution; defaults are documented in each task prompt. |

---

## Phase 1 — Antigravity CLI Sessions

### Session Map

```
Session 1 ─────────────────────────────────────┐
(P1-01: Logic Spec)                             │
    │                                           │
    ├──── Session 2 (P1-02: Converter) ──┐      │
    │     [PARALLEL, skip if no TOON]    │      │
    │                                    │      │
    ├──── Session 3 (P1-03: Fixtures) ──┐│      │
    │     [PARALLEL]                    ││      │
    │                                   ││      │
    └──── Session 4 (P1-04: Engine) ────┤│      │
          [CRITICAL PATH]              ││      │
              │                        ││      │
              ▼                        ││      │
          Session 5 ───────────────────┘│      │
          (P1-05 + P1-06: Ops + Render) │      │
              │                         │      │
              ▼                         │      │
          Session 6 ────────────────────┘      │
          (P1-07: Parity Harness)              │
              │                                │
              ▼                                │
          Session 7 ───────────────────────────┘
          (P1-08 + P1-09 + P1-10: Skill + Reports + Bundle)
              │
              ▼
          Session 8
          (P1-11: Token Measurements)
```

---

### Session 1 — Logic Spec & Schemas (Opus 4.6, ~45 min)

**What:** Extract every formula, rounding point, and date rule from the codebase into two reference documents.

**How:**
1. Open a fresh Antigravity CLI session
2. Paste the contents of [`P1-01-schema-logic-spec.md`](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/Agent_Docs/plan/task-prompts/P1-01-schema-logic-spec.md)
3. Let it run to completion

**Verify before moving on:**
```bash
# Both spec files exist
ls loanlens-bundle/spec/logic-spec.md loanlens-bundle/spec/schemas.md

# Rounding points covered
CODE_ROUNDS=$(grep -c "Math.round" src/lib/calculations.ts)
SPEC_ROUNDS=$(grep -c "round()" loanlens-bundle/spec/logic-spec.md)
echo "Code has $CODE_ROUNDS round() calls; spec documents $SPEC_ROUNDS"
# Spec count should be >= code count
```

**If it fails:** The logic spec is foundational — everything downstream depends on it. Re-run with more explicit instructions to cover the missed formulas. Check that every branch in `generateSchedule` (moratorium, EMI, historical override, prepayment, closure) has a corresponding spec section.

**Output checkpoint:** Two files in `loanlens-bundle/spec/`. Read through `logic-spec.md` yourself — if any formula looks wrong, fix it now. Errors here propagate to the Python engine.

---

### Session 2 — TOON Converter (Sonnet, ~30 min) ⚡ PARALLEL

> **Skip this session entirely if you answered Q1 with "keep JSON".**

**What:** Build the JSON↔TOON converter and produce TOON data files.

**How:**
1. Open a fresh CLI session
2. Paste [`P1-02-toon-converter.md`](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/Agent_Docs/plan/task-prompts/P1-02-toon-converter.md)

**Verify:**
```bash
cd loanlens-bundle && python -m pytest tests/test_converter.py -v
# All tests pass

# Quick round-trip check
python -c "
from engine.converter import json_to_toon, toon_to_json
import json
d = json.load(open('../data/loan_data.json'))
t = json_to_toon(d, 'loan')
r = toon_to_json(t, 'loan')
# Compare ignoring key order
assert json.dumps(d, sort_keys=True) == json.dumps(r, sort_keys=True), 'Round-trip failed!'
print('Round-trip OK')
"
```

**Can run in parallel with:** Session 3, Session 4

---

### Session 3 — Golden Fixtures (Sonnet, ~30 min) ⚡ PARALLEL

**What:** Generate 8 test fixtures by actually RUNNING the TypeScript engine on pinned inputs.

**How:**
1. Open a fresh CLI session
2. Paste [`P1-03-golden-fixtures.md`](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/Agent_Docs/plan/task-prompts/P1-03-golden-fixtures.md)

**Verify:**
```bash
# Script runs successfully
npx tsx scripts/generate-fixtures.ts

# 8 fixture files exist
ls loanlens-bundle/fixtures/ | wc -l    # should be 8

# Each has the right structure
python -c "
import json, glob
for f in sorted(glob.glob('loanlens-bundle/fixtures/*.json')):
    d = json.load(open(f))
    assert 'input' in d and 'expected_schedule' in d and 'expected_metrics' in d, f
    print(f'{f}: {len(d[\"expected_schedule\"])} schedule rows, OK')
"
```

**If the TS script fails:** Check that `npx tsx` is available. You may need `npm install -D tsx` or use `npx ts-node --esm`. The script imports from `src/lib/calculations.ts` which uses ESM syntax — make sure the runner supports it.

**Can run in parallel with:** Session 2, Session 4

---

### Session 4 — Python Engine Core (Opus 4.6, ~60 min) 🔴 CRITICAL PATH

**What:** Port `calculateEmi`, `calculateTenure`, `generateSchedule`, `calculateMetrics` to Python. This is the highest-risk task.

**How:**
1. Open a fresh CLI session (use Opus 4.6 — this needs maximum reasoning)
2. Paste [`P1-04-python-engine.md`](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/Agent_Docs/plan/task-prompts/P1-04-python-engine.md)

**Verify (quick smoke test):**
```bash
cd loanlens-bundle
python -c "
from engine.emi import calculate_emi, calculate_tenure
print(f'EMI(10000000, 7.6, 300) = {calculate_emi(10000000, 7.6, 300)}')
# Should print 74551

print(f'Tenure(10000000, 7.6, 91143) = {calculate_tenure(10000000, 7.6, 91143)}')
# Should print 189
"
```

**Verify (first fixture rows):**
```bash
python -c "
from engine.schedule import generate_schedule
from engine.types import LoanData
import json

fixture = json.load(open('fixtures/base.json'))
data = LoanData(**fixture['input'])
schedule = generate_schedule(data)

for i in range(3):
    exp = fixture['expected_schedule'][i]
    act = schedule[i]
    mismatches = []
    for f in ['openingBalance','installment','interest','principal','closingBalance']:
        if getattr(act, f) != exp[f]:
            mismatches.append(f'{f}: got {getattr(act, f)}, expected {exp[f]}')
    status = 'PASS' if not mismatches else 'FAIL: ' + '; '.join(mismatches)
    print(f'Row {i}: {status}')
"
```

**If rows don't match:**
1. Check the rounding function — Python's `round()` uses banker's rounding, JS uses half-up. Use `int(x + 0.5)` instead.
2. Check date arithmetic — Python `datetime.date` handles month boundaries differently from JS `Date`.
3. Compare the daily interest accrual loop step by step for the failing row.

**Must pass before:** Session 5, Session 6

---

### Session 5 — Operations + Renderer (Sonnet, ~75 min)

**What:** Two modules in one session — the 15 write operations and the 5 report renderers.

**How:**
1. Open a fresh CLI session
2. Paste [`P1-05-operations.md`](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/Agent_Docs/plan/task-prompts/P1-05-operations.md)
3. After completion, in the **same session**, paste [`P1-06-renderer.md`](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/Agent_Docs/plan/task-prompts/P1-06-renderer.md)

**Why combine:** Both depend only on P1-04 (engine types) and have no dependency on each other. Running them sequentially in one session avoids the startup overhead of a separate session and keeps the agent's context warm with the engine types.

**Verify:**
```bash
cd loanlens-bundle
python -m pytest tests/test_operations.py -v     # All pass, ≥30 test functions
python -m pytest tests/test_renderer.py -v        # All pass

# Quick render check
python -c "
from engine.renderer import render_summary
# (will need to pass appropriate arguments — adapt based on actual function signature)
print('Renderer imports OK')
"
```

---

### Session 6 — Parity Harness (Opus 4.6, ~60 min) 🔴 CRITICAL PATH

**What:** The moment of truth — verify the Python engine matches TypeScript across all 8 scenarios.

**How:**
1. Open a fresh CLI session (Opus 4.6 — parity failures require deep debugging)
2. Paste [`P1-07-parity-harness.md`](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/Agent_Docs/plan/task-prompts/P1-07-parity-harness.md)

**Verify:**
```bash
cd loanlens-bundle && python -m pytest tests/test_parity.py -v --tb=short
```

**Expected:** 16 tests (8 schedule × 1 + 8 metrics × 1), all passing.

**If tests fail:** This is where you spend the most debugging time. Common causes:
- **Off-by-one row:** The moratorium transition (`period > moratoriumMonths`) is `>` not `>=`. Period 18 is the last moratorium month; period 19 is the first EMI month.
- **Rounding divergence:** A single daily interest accrual that rounds differently can cascade through the entire schedule. Add debug prints for the first diverging row's daily loop.
- **Date mismatch:** JS `new Date(2026, 1, 10)` is Feb 10, but Python `date(2026, 1, 10)` is Jan 10. Make sure month indexing is consistent.

**Do not proceed to Session 7 until all 16 tests pass.** This is the gate.

---

### Session 7 — Skill + Reports + Bundle (Sonnet/Opus split, ~70 min)

**What:** Three tasks in one session — SKILL.md (Opus), pre-rendered reports (Sonnet), and bundle assembly (Sonnet).

**How:**
1. Open a fresh CLI session
2. Paste [`P1-08-skill-instructions.md`](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/Agent_Docs/plan/task-prompts/P1-08-skill-instructions.md) — this one benefits from Opus reasoning
3. After completion, paste [`P1-09-prerendered-reports.md`](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/Agent_Docs/plan/task-prompts/P1-09-prerendered-reports.md)
4. After completion, paste [`P1-10-bundle-assembly.md`](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/Agent_Docs/plan/task-prompts/P1-10-bundle-assembly.md)

**Verify:**
```bash
cd loanlens-bundle

# No PII in skill or instructions
grep -riE "83990600004041|aditya|shravi|pawar" SKILL.md project-instructions.md reports/
# Should return nothing

# All operations in SKILL.md
for op in R1 R2 R3 R4 R5 W1 W2 W3 W4 W5 W6 W7 W8 W9 W10 W11 W12 W13 W14 W15; do
  grep -q "$op" SKILL.md || echo "MISSING: $op"
done

# Bundle completeness
python -c "
import json, os
m = json.load(open('manifest.json'))
missing = [f['path'] for f in m['files'] if not os.path.exists(f['path'])]
print(f'Manifest: {len(m[\"files\"])} files listed')
if missing: print(f'MISSING: {missing}')
else: print('All files present')
"

# Full test suite from within the bundle
python -m pytest tests/ -v --tb=short
```

---

### Session 8 — Token Measurements (Sonnet, ~10 min)

**What:** Measure and record token counts for all key artifacts.

**How:**
1. Open a fresh CLI session
2. Paste [`P1-11-token-measurements.md`](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/Agent_Docs/plan/task-prompts/P1-11-token-measurements.md)

**Verify:**
```bash
python -c "
import json
m = json.load(open('loanlens-bundle/manifest.json'))
tm = m.get('token_measurements', {})
for k, v in tm.items():
    print(f'  {k}: {v} tokens')
"
```

---

### 🎉 Phase 1 Complete Checklist

Before moving to Phase 2, verify every item:

```bash
cd loanlens-bundle

echo "=== Phase 1 Completion Checklist ==="

# 1. Spec files
[ -f spec/logic-spec.md ] && echo "✅ logic-spec.md" || echo "❌ logic-spec.md"
[ -f spec/schemas.md ] && echo "✅ schemas.md" || echo "❌ schemas.md"

# 2. Engine modules
for f in __init__.py types.py emi.py schedule.py metrics.py operations.py renderer.py converter.py auto_deduct.py; do
  [ -f engine/$f ] && echo "✅ engine/$f" || echo "❌ engine/$f"
done

# 3. Fixtures
FIXTURE_COUNT=$(ls fixtures/*.json 2>/dev/null | wc -l)
[ "$FIXTURE_COUNT" -eq 8 ] && echo "✅ 8 fixtures" || echo "❌ $FIXTURE_COUNT fixtures (expected 8)"

# 4. Tests
python -m pytest tests/ -q 2>&1 | tail -1

# 5. TOON data (skip if no TOON)
ls data/*.toon 2>/dev/null && echo "✅ TOON files" || echo "⚠️  No TOON files (OK if JSON-only)"

# 6. Reports
REPORT_COUNT=$(ls reports/*.md 2>/dev/null | wc -l)
[ "$REPORT_COUNT" -eq 4 ] && echo "✅ 4 pre-rendered reports" || echo "❌ $REPORT_COUNT reports"

# 7. Skill + instructions
[ -f SKILL.md ] && echo "✅ SKILL.md" || echo "❌ SKILL.md"
[ -f project-instructions.md ] && echo "✅ project-instructions.md" || echo "❌ project-instructions.md"

# 8. Manifest
[ -f manifest.json ] && echo "✅ manifest.json" || echo "❌ manifest.json"

# 9. No PII
PII_HITS=$(grep -rlE "83990600004041" . 2>/dev/null | grep -v ".json" | wc -l)
[ "$PII_HITS" -eq 0 ] && echo "✅ No PII in non-data files" || echo "❌ PII found in $PII_HITS files"

echo "==================================="
```

---

## Phase 2 — Claude Desktop Sessions

### Prerequisites

- The `loanlens-bundle/` directory from Phase 1, fully verified
- Claude Desktop (or Claude.ai with Projects support)
- The [phase2-runbook.md](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/Agent_Docs/plan/task-prompts/phase2-runbook.md) open for reference

### Session 9 — Setup (P2-01 through P2-04, ~25 min)

**What:** Determine capability tier, install the bundle, register the skill, create the project.

**Step 1: Capability Probe**

Open Claude Desktop and paste:

```
I need to test your capabilities for a project setup. Please:
1. Run this Python code: print("Hello from Python!", 1 + 1)
2. Try to list files in my home directory
3. Try to write a test file: write "loanlens test" to ~/loanlens_probe.txt
Report what worked and what didn't.
```

Record the tier:
- ✅ All three → **Tier A**
- ✅ Python + read, ❌ write → **Tier B**
- ❌ Python → **Tier C**

**Step 2: Install Bundle**

*Tier A (local filesystem):*
```bash
# In your terminal (not Claude):
cp -r loanlens-bundle ~/loanlens
```

Then tell Claude:
```
My LoanLens project files are installed at ~/loanlens/. 
Please verify you can read ~/loanlens/manifest.json and 
print the bundle version and file count.
```

*Tier C (no filesystem):*
Upload these files as Project Knowledge in Claude Desktop:
- `SKILL.md`
- `spec/logic-spec.md`
- `reports/summary_20260919.md`
- `reports/od_savings_20260919.md`
- `reports/schedule_20260919.md`
- `reports/ledger_20260919.md`
- Both TOON data files (or JSON if you skipped TOON)

**Step 3: Install Skill**

In Claude Desktop Project settings, add `SKILL.md` as a Project Knowledge file.

**Step 4: Set Project Instructions**

Paste the entire contents of `project-instructions.md` into the Project Instructions field.

**Verify:** Start a new conversation in the project and ask:
```
What do you know about my home loan?
```
Claude should reference the loan type, phase, and rate from the project instructions.

---

### Session 10 — End-to-End Report Tests (P2-05, ~30 min)

**What:** Verify all 5 report types produce correct data.

Run these queries in order, in a conversation within the LoanLens project:

```
1. "Show me my loan summary for September 19, 2026"
   → Check: outstanding principal, OD balance, effective rate, next due date

2. "Show me my OD savings breakdown"
   → Check: waterfall (OD → reserve → allocatable → goals → free)
   → Check: over-allocation warning (~₹36,179)

3. "Show me my next 6 installments"
   → Check: all should be moratorium phase, due dates on the 10th

4. "What if I make a ₹5,00,000 prepayment on October 1, 2026?"
   → Check: shows interest saved, tenure change
   → Compare against fixtures/prepayment.json expected_metrics

5. "Show me my payment and disbursement history"
   → Check: 4 disbursements, 8 payment entries
```

**What to do if numbers are wrong:**
- Tier A: Ask Claude to run the parity test: `python -m pytest ~/loanlens/tests/test_parity.py -v`
- Tier C: Numbers will be approximate — this is expected. Check that the order of magnitude is correct.

---

### Session 11 — Mutation Tests (P2-06, ~25 min)

**What:** Test write operations and rollback.

```
1. "Log a new OD balance of ₹10,00,000 for September 20, 2026"
   → Should show dry-run with before/after impact
   → Confirm the mutation
   → Then ask: "Show me my OD savings" to verify new balance

2. "Add a contribution of ₹50,000 from [your source name] on September 20, 2026"
   → Should add to contributions
   → Verify total deposited increased

3. "Update the allocation for [a goal name] to ₹2,00,000"
   → Should warn about over-allocation if applicable
   → Verify in OD savings report

4. "Undo the last change" or "Restore the previous data version"
   → Tier A: Should restore from archive/
   → Tier B/C: Should provide instructions for manual restoration
   → Verify data reverted
```

---

### Session 12 — Tuning & Routine Setup (P2-07 + P2-08, ~30 min)

**What:** Adjust report verbosity and set up the monthly routine.

**Tuning:**
```
- "Make the summary report more concise — I only need outstanding, OD balance, 
  next due, and interest saved"
  
- "In the schedule, show 12 months instead of 6"

- "When I say 'what's my loan status', show the summary"
```

**Monthly routine test:**

Simulate a monthly bank statement update:
```
Let's do a monthly update for September 2026:
1. Log OD balance of ₹9,23,964 on September 10, 2026
2. The September payment — amount due was ₹[X], amount paid was ₹[X]  
3. Process any outstanding due payments for today
4. Show me my summary
```

Verify the flow works end to end.

---

## Failure Recovery Playbook

| Scenario | What to do |
|---|---|
| **Session 1 (logic spec) is incomplete** | Re-run with the specific formulas listed as missing. The spec is a document — additive fixes are safe. |
| **Session 3 (fixtures) fails to run** | Check `tsx` installation. Try `npx ts-node --esm scripts/generate-fixtures.ts` as alternative. |
| **Session 4 (engine) produces wrong numbers** | Do NOT proceed. Compare the Python daily interest loop against `calculations.ts` L110-132 line by line. The most common bug is Python `round()` vs JS `Math.round()`. |
| **Session 6 (parity) has failures** | Fix in the Python engine, not the fixtures. Fixtures are the ground truth. Run `python -m pytest tests/test_parity.py -v -k "base"` to isolate the base scenario first. |
| **Session 7 (bundle) tests fail** | Check that the engine module imports work from the bundle root. You may need `sys.path` adjustments or a proper `pyproject.toml`. |
| **Phase 2: Claude can't find files** | Check the path (`~/loanlens/` vs `~/loanlens-bundle/`). Try absolute paths. |
| **Phase 2: Numbers are approximate (Tier C)** | Expected. Tier C relies on Claude's reasoning, not the engine. For precise numbers, you need Tier A. |
| **Phase 2: Skill doesn't trigger** | Add more trigger phrases to SKILL.md. Common phrases to add: "EMI", "home loan", "loan status", "OD balance". |

---

## Time Estimates Summary

| Session | Tasks | Model | Duration | Parallel? |
|---|---|---|---|---|
| 1 | P1-01 | Opus 4.6 | 45 min | — |
| 2 | P1-02 | Sonnet | 30 min | ⚡ with 3, 4 |
| 3 | P1-03 | Sonnet | 30 min | ⚡ with 2, 4 |
| 4 | P1-04 | Opus 4.6 | 60 min | ⚡ with 2, 3 |
| 5 | P1-05 + P1-06 | Sonnet | 75 min | — |
| 6 | P1-07 | Opus 4.6 | 60 min | — |
| 7 | P1-08 + P1-09 + P1-10 | Opus/Sonnet | 70 min | — |
| 8 | P1-11 | Sonnet | 10 min | — |
| **Phase 1 Total** | | | **~5–6 hrs** (with parallel: ~4 hrs) | |
| 9 | P2-01–04 | Haiku | 25 min | — |
| 10 | P2-05 | Sonnet | 30 min | — |
| 11 | P2-06 | Sonnet | 25 min | — |
| 12 | P2-07–08 | Haiku | 30 min | — |
| **Phase 2 Total** | | | **~2 hrs** | |
| **Grand Total** | | | **~7–8 hrs** | |

---

## Quick Reference: What Goes Where

| I want to... | Use this prompt file | Session |
|---|---|---|
| Start Phase 1 | `P1-01-schema-logic-spec.md` | 1 |
| Build the TOON converter | `P1-02-toon-converter.md` | 2 |
| Generate test fixtures | `P1-03-golden-fixtures.md` | 3 |
| Port the engine to Python | `P1-04-python-engine.md` | 4 |
| Build operations + renderer | `P1-05-operations.md` + `P1-06-renderer.md` | 5 |
| Verify TS↔Python parity | `P1-07-parity-harness.md` | 6 |
| Draft the skill + bundle it | `P1-08` + `P1-09` + `P1-10` | 7 |
| Measure tokens | `P1-11-token-measurements.md` | 8 |
| Set up Claude Desktop | `phase2-runbook.md` Steps 1–4 | 9 |
| Test reports end-to-end | `phase2-runbook.md` Step 5 | 10 |
| Test mutations + rollback | `phase2-runbook.md` Step 6 | 11 |
| Tune + set up routine | `phase2-runbook.md` Steps 7–8 | 12 |
