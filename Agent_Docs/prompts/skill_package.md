# P1-12 — Package LoanLens as a Self-Contained Claude Skill

**Run this in:** Antigravity CLI (Opus 4.6 or Sonnet 5 High preferred — this involves rewriting orchestration text precisely and must not silently break the validated engine)
**Depends on:** The existing `loanlens-bundle/` (already built, parity-tested, in this repo at `~/codebase/gemini-projects/home-loan-dashboard/loanlens-bundle/`)
**Produces:** `loanlens-finance/` — a directory formatted as a proper Claude Skill, ready to zip and upload to claude.ai / Claude Desktop via Settings → Capabilities → Skills (or Customize → Skills)

---

## Context You Need

We're moving away from splitting LoanLens across a claude.ai Project + Google Drive. The new architecture:

- **The Skill package** (this task's output) hosts everything that doesn't change at runtime: the protocol instructions, the Python calculation engine, the formula spec, and the pre-rendered fallback reports. It's uploaded once as a zip and then works in _any_ Claude chat — it is no longer tied to a specific Project.
- **Google Drive** (folder ID `1INKH5EtY6y8xUB4Jfk1_PEGOcI4hR1yo`, already populated) holds _only_ the two files that actually mutate over time: `loan_data.v*.toon` and `od_savings.v*.toon`. This is a hard constraint, not a preference — a Skill's bundled files are static once uploaded; there is no mechanism for Claude to write a new version back into an installed skill from inside a chat. Versioned data has to live somewhere Claude _can_ write new files, which is Drive.
- The claude.ai "LoanLens" Project becomes a dev artifact only — it is not part of the runtime path anymore. Do not treat anything in `project-instructions.md` as authoritative; fold any still-relevant behavioral rules from it directly into the new `SKILL.md` instead.

## Do NOT Do

- Do **not** re-derive, "improve," or rewrite any of the calculation logic in `engine/*.py`. Those files already passed the full TS↔Python parity harness (8/8 scenarios). Copy them byte-for-byte. If you think you see a bug, flag it in your output summary — do not silently fix it.
- Do **not** include `data/loan_data.json`, `data/od_savings_data.json`, `data/*.toon`, `fixtures/`, `tests/`, `generate_manifest.py`, `generate_reports.py`, `check_pii.sh`, `requirements.txt`, or the old bundle's `manifest.json` in the skill package. None of these belong in a runtime skill bundle (data is mutable → Drive; the rest is build-time tooling or dev-time verification, not needed once the engine is validated).
- Do **not** invent a `data/manifest.json` version-pointer file. Version resolution for the two Drive files is by `modifiedTime`, not a manifest.

## Task

### Step 1 — Read the source bundle

Read, in full:

- `loanlens-bundle/engine/*.py` (all 9 files: `__init__.py`, `types.py`, `emi.py`, `schedule.py`, `metrics.py`, `operations.py`, `renderer.py`, `converter.py`, `auto_deduct.py`)
- `loanlens-bundle/spec/logic-spec.md`
- `loanlens-bundle/spec/schemas.md`
- `loanlens-bundle/reports/*.md` (all 4 pre-rendered reports)
- `loanlens-bundle/SKILL.md` (the previous draft, for content you can reuse)
- `loanlens-bundle/project-instructions.md` (for behavioral rules worth folding in)

### Step 2 — Create the skill directory structure

```
loanlens-finance/
├── SKILL.md
├── engine/
│   ├── __init__.py
│   ├── types.py
│   ├── emi.py
│   ├── schedule.py
│   ├── metrics.py
│   ├── operations.py
│   ├── renderer.py
│   ├── converter.py
│   └── auto_deduct.py
├── spec/
│   ├── logic-spec.md
│   └── schemas.md
└── reports/
    ├── summary_20260919.md
    ├── od_savings_20260919.md
    ├── schedule_20260919.md
    └── ledger_20260919.md
```

Copy `engine/`, `spec/`, and `reports/` contents verbatim from `loanlens-bundle/`. Do not modify file contents in this step.

### Step 3 — Write `SKILL.md`

This is the core deliverable. It needs valid YAML frontmatter (`name`, `description`) followed by the full protocol. Structure it as follows:

```yaml
---
name: loanlens-finance
description: |
  [Write a complete description — what the skill does, when Claude should use it,
  and the keywords that should trigger it: home loan, EMI, OD balance, overdraft,
  prepayment, interest saved, tenure, amortization schedule, loan closure, etc.
  This field drives trigger accuracy, so be thorough — see the description
  requirements at https://claude.com/docs/skills/how-to.md if you have access
  to fetch it; otherwise use the trigger language already in
  loanlens-bundle/SKILL.md's "Trigger" section as your base.]
---
```

Below the frontmatter, include these sections (adapt from `loanlens-bundle/SKILL.md`, but with the changes below applied):

1. **Description / Purpose** — one paragraph, what LoanLens does.

2. **Drive Configuration** — this section changes from the previous draft:
   - Folder ID: `1INKH5EtY6y8xUB4Jfk1_PEGOcI4hR1yo`
   - State explicitly: **this Drive folder now contains only the two mutable data files** — `loan_data.v*.toon` and `od_savings.v*.toon`. Nothing else should be fetched from Drive; the engine, spec, and reports all ship inside this skill package and are read from the skill's own bundled files at runtime.
   - Version resolution: search the Drive folder for files matching each pattern; the file with the most recent `modifiedTime` is current. No manifest file is used for this.

3. **Protocol** — rewrite the steps so that:
   - Step 1 (Resolve data) — only resolves the two data files from Drive, as above.
   - Step 2 (Load) — parse the TOON files to JSON using this skill's own bundled `engine/converter.py` (loaded from the skill directory, not fetched from anywhere).
   - Step 3 (Compute) — run this skill's own bundled `engine/schedule.py` and `engine/metrics.py`. Always pass `today_date` explicitly; the engine never reads the system clock.
   - Step 4 (Render or Mutate) — same as before: read ops call `engine/renderer.py` functions and display output verbatim; write ops call `engine/operations.py` functions, dry-run → confirm (per the confirmation policy table) → commit by writing a new incremented-version file to the same Drive folder.
   - Step 5 (Respond).

4. **Available Operations** — carry over the R1–R5 / W1–W15 tables from `loanlens-bundle/SKILL.md` unchanged (function signatures, descriptions, confirmation policy).

5. **Formatting Rules** — carry over (INR Indian digit grouping via `engine/renderer.py:fmt_inr()`, date format, deterministic rendering, no PII in output). Fold in the behavioral rules from `project-instructions.md` that are still relevant (always use the engine, never estimate, always pass today's date explicitly, dry-run before mutating, check invariants after mutating).

6. **Error Handling** — carry over, but drop or clearly caveat the "run the parity check against fixtures/" line since `fixtures/` is not part of this skill package. Replace with: if a computed value looks wrong, re-verify the daily interest accrual loop logic against `spec/logic-spec.md` rather than assuming a fixture is available.

7. **Invariants** — carry over unchanged (disbursed ≤ sanctioned, OD balance ≥ 0, goal allocations ≥ 0, unique payment log dates per due date, TOON `[N]` header integrity, round-trip integrity).

8. **File Paths** — update this table to reflect that `engine/`, `spec/`, and `reports/` are paths _within this skill's own directory_ (available in Claude's execution environment once the skill is active), while only `data/*.toon` refers to the external Google Drive folder.

### Step 4 — Self-check before finishing

1. Confirm every engine file still imports cleanly as a package: `python -c "from engine.schedule import generate_schedule; from engine.metrics import calculate_metrics; from engine.operations import *; print('OK')"` run from inside `loanlens-finance/`.
2. Grep for PII: `grep -riE "83990600004041|aditya|shravi|pawar" loanlens-finance/SKILL.md loanlens-finance/reports/*.md loanlens-finance/spec/*.md` — must return nothing.
3. Confirm `SKILL.md`'s YAML frontmatter parses as valid YAML (`python -c "import yaml; yaml.safe_load(open('loanlens-finance/SKILL.md').read().split('---')[1])"`).
4. Confirm no file in `loanlens-finance/` references `data/manifest.json`, `fixtures/`, or `tests/` as something Claude should fetch at runtime — a grep for those strings should only appear (if at all) in caveat/error-handling text explaining they're _not_ available, never in the main protocol steps.
5. Report the final directory tree and total size of `loanlens-finance/` (should be small — a few hundred KB at most, dominated by `spec/logic-spec.md` and `engine/operations.py`).

### Step 5 — Package for handoff

```bash
zip -r loanlens-finance.zip loanlens-finance/
```

Produce this zip at the repo root. Do not include the old `loanlens-bundle/` in the zip.

## Definition of Done

- `loanlens-finance/` exists with exactly the structure in Step 2 — no data files, no fixtures, no tests, no build scripts
- `SKILL.md` has valid YAML frontmatter and a complete rewritten protocol per Step 3
- All 9 engine files are byte-identical to the versions in `loanlens-bundle/engine/` (verify with `diff -r loanlens-bundle/engine/ loanlens-finance/engine/` — must be empty)
- No PII anywhere in the package
- `loanlens-finance.zip` exists and is ready to upload

## Handoff Notes for the Next Session (Claude, after upload)

Once uploaded, confirm the skill triggers on a query like "what's my next EMI?", that it correctly finds the two Drive files by `modifiedTime`, and that a full read (`show_summary`) and one mutation (`update_od_balance`) both work end-to-end before considering this migration complete.
