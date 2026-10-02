# D4 — Task Breakdown

**Produced:** 2026-09-19

---

## Task Table

| ID | Phase | Environment | Task | Inputs | Outputs (paths) | Depends on | Verifier | Done signal | Suggested model | Suggested effort | Est. duration | Rationale |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P1-01 | 1 | Antigravity CLI | Extract data schemas and write language-neutral logic spec documenting every formula, rounding point, date rule, and invariant from `calculations.ts` and type files | `src/lib/calculations.ts`, `src/lib/types.ts`, `src/lib/od-savings-types.ts`, D0, D2 | `spec/logic-spec.md`, `spec/schemas.md` | — | `grep -c "Math.round" src/lib/calculations.ts` matches count of rounding points in logic-spec.md; every `generateSchedule` branch has a corresponding spec entry | Both spec files exist; every formula from calculations.ts is documented with evidence tags | Opus 4.6 | High | 45 min | Formula-fidelity work: a silent omission would corrupt the Python port's money math |
| P1-02 | 1 | Antigravity CLI | Build JSON↔TOON converter (Python) with round-trip fidelity tests for both data files | `spec/schemas.md`, `data/loan_data.json`, `data/od_savings_data.json` | `engine/converter.py`, `tests/test_converter.py`, `data/loan_data.v001.toon`, `data/od_savings.v001.toon` | P1-01 | `python -m pytest tests/test_converter.py -v` — all pass; diff of round-tripped JSON vs original is empty | All tests pass; TOON files exist; `[N]` headers match row counts | Sonnet-class | Medium | 30 min | Mechanical transform with clear spec; strong automated verifier catches errors |
| P1-03 | 1 | Antigravity CLI | Generate golden fixtures by running TypeScript `generateSchedule` and `calculateMetrics` on 8 pinned scenarios via `tsx` | `src/lib/calculations.ts`, pinned input data (defined in script) | `scripts/generate-fixtures.ts`, `fixtures/base.json`, `fixtures/prepayment.json`, `fixtures/rate-change.json`, `fixtures/od-change.json`, `fixtures/disbursement-during-emi.json`, `fixtures/moratorium-boundary.json`, `fixtures/zero-od.json`, `fixtures/high-prepayment.json` | P1-01 | `npx tsx scripts/generate-fixtures.ts && ls fixtures/ | wc -l` equals 8; each JSON has `input` and `expected` keys | 8 fixture files exist with correct structure; script runs without error | Sonnet-class | Medium | 30 min | Scaffolding + execution; the TS functions already exist and are tested |
| P1-04 | 1 | Antigravity CLI | Port core engine to Python: `calculateEmi`, `calculateTenure`, `generateSchedule`, `calculateMetrics` with Pydantic types | `spec/logic-spec.md`, `spec/schemas.md` | `engine/__init__.py`, `engine/types.py`, `engine/emi.py`, `engine/schedule.py`, `engine/metrics.py` | P1-01 | `python -c "from engine.schedule import generate_schedule; from engine.metrics import calculate_metrics; print('OK')"` — imports succeed; run on base fixture input and compare first 3 rows against expected | Engine loads; base fixture first 3 rows match exactly (money fields ±0) | Opus 4.6 | Max | 60 min | Core financial engine: rounding errors, off-by-one date bugs, and JS→Python Date semantics differences require max reasoning |
| P1-05 | 1 | Antigravity CLI | Implement all 15 write operations (W1-W15) in Python with validation, dry-run, and commit semantics | D2 Section D, `engine/types.py` | `engine/operations.py`, `tests/test_operations.py` | P1-04 | `python -m pytest tests/test_operations.py -v` — all pass; each W-op has at least 2 tests (happy path + validation failure) | All tests pass; operation count matches D2 catalog (15 operations) | Sonnet-class | Medium | 40 min | Standard implementation; spec is complete in D2; automated verifier catches regressions |
| P1-06 | 1 | Antigravity CLI | Build deterministic markdown renderer for all 5 report types (summary, OD savings, schedule, simulator, ledger) with INR formatting and date formatting | D2 Section C, `engine/types.py`, `engine/metrics.py` | `engine/renderer.py`, `tests/test_renderer.py` | P1-04 | `python -m pytest tests/test_renderer.py -v` — all pass; rendered reports contain `₹` and Indian digit grouping; token count measured and ≤ budget | All tests pass; 5 report functions exist; outputs contain proper formatting | Sonnet-class | Medium | 35 min | Templating work; formatting rules are explicit in D2; strong automated verifier |
| P1-07 | 1 | Antigravity CLI | Build and run TS↔Python parity harness across all 8 fixture scenarios. Debug any mismatches. | `fixtures/*.json`, Python engine | `tests/test_parity.py` | P1-03, P1-04 | `python -m pytest tests/test_parity.py -v` — all 8 scenarios pass; each test compares every row of the schedule (period, dueDate, openingBalance, installment, interest, principal, closingBalance) | All 8 scenarios pass with exact match on all money/date fields | Opus 4.6 | Max | 60 min | Cross-language parity debugging; failures require understanding both JS and Python float semantics and date handling |
| P1-08 | 1 | Antigravity CLI | Draft SKILL.md and Claude Project instruction text. Ensure no PII, correct file paths, complete operation catalog. | D2 Sections G, all operation specs | `SKILL.md`, `project-instructions.md` | P1-05, P1-06 | `grep -c "account" SKILL.md project-instructions.md` returns 0 (no account numbers); grep for all 20 operation IDs (R1-R5, W1-W15) in SKILL.md — all present | Both files exist; no PII; all operations referenced | Opus 4.6 | High | 30 min | Skill/protocol design; must be precise about triggers, error handling, and invariants |
| P1-09 | 1 | Antigravity CLI | Generate pre-rendered reports from current data for Tier C fallback. Redact identifiers. | Python engine + renderer, current data files | `reports/summary_20260919.md`, `reports/od_savings_20260919.md`, `reports/schedule_20260919.md`, `reports/ledger_20260919.md` | P1-06 | `ls reports/ | wc -l` equals 4; `grep -r "83990600004041" reports/` returns 0 (no account number); each report ≤ token budget | 4 report files exist; no PII; within token budgets | Sonnet-class | Low | 15 min | Mechanical execution of the renderer on current data; just run and verify |
| P1-10 | 1 | Antigravity CLI | Assemble handoff bundle: copy all artifacts, generate manifest.json with SHA256 checksums, verify completeness | All P1 outputs | `loanlens-bundle/` directory, `loanlens-bundle/manifest.json` | P1-02, P1-07, P1-08, P1-09 | `python -c "import json; m=json.load(open('loanlens-bundle/manifest.json')); assert len(m['files']) >= 20"` — manifest has all files; `cd loanlens-bundle && python -m pytest tests/ -v` — all tests pass from within bundle | Bundle directory complete; manifest valid; all tests pass from bundle root | Sonnet-class | Medium | 25 min | Assembly + verification; checklist-driven |
| P1-11 | 1 | Antigravity CLI | Measure token counts for all TOON files, reports, SKILL.md, and project instructions. Record in manifest. | Bundle contents | Updated `manifest.json` with token measurements | P1-10 | Token counts present in manifest for each measured file; no file exceeds its budget | All measurements recorded | Sonnet-class | Low | 10 min | Measurement; mechanical |
| P2-01 | 2 | Claude Desktop | Capability probe: determine which tier (A/B/C) applies by testing code execution and file access | Claude Desktop environment | Tier determination document | — | Run `print(1+1)` in code execution; attempt to read a local file; attempt to write a file | Tier (A, B, or C) determined and documented | Haiku-class | Low | 5 min | Simple diagnostic |
| P2-02 | 2 | Claude Desktop | Install bundle files to chosen storage location | `loanlens-bundle/` | Files in `~/loanlens/` (or Drive) | P2-01 | `manifest.json` is readable from Claude Desktop; at least one TOON file parses correctly | All bundle files accessible | Haiku-class | Low | 10 min | File copy/upload |
| P2-03 | 2 | Claude Desktop | Install LoanLens skill in Claude Desktop | `SKILL.md` | Active skill | P2-02 | Asking "show my loan summary" triggers the skill | Skill activates on loan queries | Haiku-class | Low | 5 min | Configuration |
| P2-04 | 2 | Claude Desktop | Create Claude Project with instruction text | `project-instructions.md` | Active Claude Project | P2-03 | Project is listed and active | Project created | Haiku-class | Low | 5 min | Configuration |
| P2-05 | 2 | Claude Desktop | End-to-end test: run each of the 5 report queries and compare key values against fixture expectations | Fixtures, expected values from P1-03 | Test results log | P2-04 | Each report type (summary, OD savings, schedule, simulator, ledger) returns values within tolerance of fixture expectations | All 5 report types return correct data | Sonnet-class | Medium | 30 min | Systematic verification across 5 report types |
| P2-06 | 2 | Claude Desktop | Mutation dry-run + rollback test: test 3+ mutations, verify data integrity, test rollback | Test scenarios | Test results log | P2-05 | At least 3 mutations (OD update, contribution add, goal edit) complete successfully; rollback restores data to pre-mutation state | Mutations work; rollback verified | Sonnet-class | Medium | 25 min | Testing with manual verification |
| P2-07 | 2 | Claude Desktop | Tune report verbosity and skill triggers based on real usage | User feedback | Updated SKILL.md, renderer config | P2-06 | User confirms reports are at desired verbosity | User approval | Haiku-class | Low | 15 min | Iterative refinement |
| P2-08 | 2 | Claude Desktop | Document and test monthly bank statement update procedure | Monthly routine spec | Procedure document | P2-07 | Successfully complete one simulated monthly update cycle | Monthly routine documented and tested | Haiku-class | Low | 15 min | Documentation |

---

## Summary Tables

### Tasks by Model/Effort

| Model | Low | Medium | High | Max | Total |
|---|---|---|---|---|---|
| **Opus 4.6** | — | — | 2 (P1-01, P1-08) | 2 (P1-04, P1-07) | **4** |
| **Sonnet-class** | 3 (P1-09, P1-11, P2 setup×2) | 5 (P1-02, P1-03, P1-05, P1-06, P1-10) | — | — | **8** |
| **Haiku-class** | 6 (P2-01 through P2-04, P2-07, P2-08) | 2 (P2-05, P2-06) | — | — | **8** |
| **Total** | **9** | **7** | **2** | **2** | **20** |

### Critical Path

```
P1-01 (45m) → P1-04 (60m) → P1-07 (60m) → P1-10 (25m) → P1-11 (10m)
```

**Critical path duration: ~200 minutes (3.3 hours)**

Including parallelizable work, total Phase 1 estimated duration: **~5 hours** (with parallel tracks for converter, fixtures, and renderer).

Phase 2 estimated duration: **~2 hours** (mostly configuration and testing).

### Suggested Run Order

**Phase 1 — Sequential sessions in Antigravity CLI:**

1. **Session 1 (Opus 4.6):** P1-01 — Schema extraction + logic spec
2. **Session 2 (Sonnet):** P1-02 — JSON→TOON converter (can run after P1-01)
3. **Session 3 (Sonnet):** P1-03 — Golden fixture generation (can run after P1-01, parallel with P1-02)
4. **Session 4 (Opus 4.6):** P1-04 — Python engine core (needs P1-01)
5. **Session 5 (Sonnet):** P1-05 + P1-06 — Operations + Renderer (needs P1-04, can be one session)
6. **Session 6 (Opus 4.6):** P1-07 — Parity harness (needs P1-03 + P1-04)
7. **Session 7 (Opus 4.6):** P1-08 — SKILL.md + instructions (needs P1-05)
8. **Session 8 (Sonnet):** P1-09 + P1-10 + P1-11 — Reports + bundle + measurements

**Phase 2 — Sequential steps in Claude Desktop:**

9. P2-01 → P2-04: Setup (15 min)
10. P2-05 → P2-06: Testing (55 min)
11. P2-07 → P2-08: Tuning (30 min)
