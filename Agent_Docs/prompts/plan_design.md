# LoanLens v2 — Change Audit + Scope + Design + Implementation Plan

# (PLANNING RUN ONLY — do not implement anything in this run)

## 0. MODE AND GUARDRAILS

- You are running in my local LoanLens repo (Next.js + TypeScript). Use maximum reasoning effort.
- This run is READ-ONLY on the repo. Do not edit, move, or delete anything under src/, data/, or config files.
- Write outputs ONLY under `/Agent Docs`.
- Do not ask me questions mid-run. When something is ambiguous, pick the most defensible default, continue, and record it in 05-open-questions.md with the default you chose and what would change if I disagree.
- Evidence rule: every claim about app behaviour must cite file:line. Mark each claim VERIFIED (read in code), RAN (observed by executing something), or INFERRED. Do not trust README, comments, or docs over code; a previous audit found the README described features that don't exist.
- Do not copy account numbers, customer IDs, or other personal identifiers into any plan document.
- No network access is needed. Do not install global packages.

## 1. BACKGROUND (you have no memory of earlier sessions; this is the context)

LoanLens tracks an OD-linked home loan (Bank of Baroda). A previous plan (2026-08-05) was to move it from a local Next.js server to a conversational setup: JSON data on Google Drive, a Python port of the calculation logic, a Claude skill, and a Claude Project. The local app has CHANGED since that plan. If loanlens-conversational-plan.md or loanlens-task-split.md exist anywhere in the repo, read them as the previous plan. Treat them as superseded wherever this prompt differs.

Revised direction (my decisions):

1. Convert the JSON data files to TOON so the data is token-efficient for LLM/Claude. Check the repo and node_modules for any TSON/TOON reference. If ambiguous, treat it as TOON and say so in the design.
2. Extract the calculation and business logic from the code into runnable form (engine + spec + test vectors).
3. Draft markdown report formats for the common reports (summary, OD Savings, Schedule, Simulator, and any other screen you find). They must mirror what the existing screens show but carry only the essential, decision-relevant data points. They are NOT full page replicas.
4. Draft a skill that performs every task the app already does: produce reports, add/subtract OD balance, add disbursement, and all other mutations the app supports.

Two phases:

- PHASE 1 — runs here, on the codebase (Antigravity CLI, Opus 4.6 = highest model I have). Contains everything that needs direct repo access. Its output is a self-contained handoff bundle.
- PHASE 2 — runs in the Claude Desktop app with NO repo access. It consumes only the Phase 1 bundle: installs the skill, wires up storage, tests end to end, tunes.

## 2. BASELINE ASSUMPTIONS TO RE-VERIFY (each may now be false)

- Core schedule loop: src/lib/calculations.ts (~L59-231); calculateMetrics (~L234-295); day count hardcoded 365; interest computed per day on max(0, outstanding − OD balance).
- HISTORICAL_PAYMENT_DATES was a hardcoded set (2026-02-10 … 2026-06-10) overriding computed pre-EMI interest.
- OD waterfall logic lived in OdSavingsClient.tsx computed values (emiReserve, allocatable, goals, contributions).
- Simulator was read-only and lived in SimulatorClient.tsx.
- Goal status derived (allocated >= target), not stored. Paid/Upcoming/Overdue badges did NOT exist despite the README.
- onDisbursementDuringEmi policy not applied; RateHistory.spread unused; no concurrency control.
- Old sanity values (tied to an old data snapshot, so expect drift): EMI(5982984, 7.6%, 282) = 91143; latest OD balance 906043 as of 2026-08-02; allocatable = OD − reserve = 814900; first EMI after moratorium 2026-09-10.
  For each: report STILL TRUE / CHANGED / NEW, with evidence.

## 3. DELIVERABLES (write in this order; keep each file tight and scannable)

### D0 — plan/00-change-audit.md

- Detect change: run `git status`, `git log --since=2026-08-05 --stat`, and diff HEAD against the commit nearest 2026-08-05. Include uncommitted and untracked changes. If not a git repo, fall back to file mtimes and say so.
- Tabulate changed files by area: calculation logic, types/schemas (Zod), data files (loan_data.json, od_savings_data.json, any new data files), screens/routes, server actions/API routes, dependencies.
- Explicit sections: (a) formula/behaviour changes, (b) schema/field changes (added, removed, renamed, semantics changed), (c) new screens/features/mutations, (d) removed features, (e) the assumptions table from section 2 with status.
- Full screen inventory: every page/route, what it shows, which data and functions feed it.
- Full mutation inventory: every operation that writes data (from UI handlers, server actions, API routes, stores). For each: inputs, validation, target file/entity, audit/editHistory behaviour, side effects. Include how OD balance is modelled (snapshot log vs deltas) and whether "add" and "subtract" are distinct operations.
- Current data profile: entity counts and date ranges per array, and approximate JSON size in bytes and tokens (state your token-estimation method).

### D1 — plan/01-scope.md

- In scope / out of scope / explicit non-goals for each workstream (TSON conversion, logic extraction, report formats, skill) and each phase.
- Feature parity matrix: every app screen and mutation → covered by report / covered by skill operation / deliberately dropped (with reason).
- Success criteria: what "the conversational version is as good as the app" means, in measurable terms (numeric parity, token budgets, mutation safety).
- Assumptions, constraints, risks (top 10, with mitigation).

### D2 — plan/02-design.md

Answer each of these, with a decision, rationale, and rejected alternatives:
A. DATA FORMAT (TSON/TOON): which structures convert well (uniform arrays such as paymentLog, odBalanceLog, rateHistory, contributions) vs which stay nested. Benchmark on the REAL data: bytes and approximate tokens for pretty JSON vs minified JSON vs TOON. Lossless JSON↔TSON round-trip requirement, plus converter design (script, language, tests). Address the fact that LLMs editing TOON by hand must keep array-length headers `[N]` consistent: define how edits are made safely (script-mediated vs constrained row-append).
B. LOGIC EXTRACTION: target runtime for the engine (Python default; justify against what Claude Desktop can actually execute; Phase 2 has to verify this). Module boundaries (engine / operations / renderer). A language-neutral LOGIC SPEC (formulas, rounding points, date rules, invariants) so Claude can fall back to reasoning if code execution is unavailable. `today` is always an explicit parameter, never the system clock. Golden-fixture strategy: generate expected outputs by RUNNING the TypeScript functions (tsx/ts-node) on pinned inputs across scenarios (base; prepayment; rate change; OD change; disbursement during EMI; moratorium boundary; overdue; edge cases). Never hand-copy dashboard numbers. Define a TS↔Python parity harness and tolerance rules (money rounding points must match exactly).
C. REPORTS: for every screen-derived report, define its purpose, the essential fields only (and what is deliberately omitted), layout, and a token budget (suggest: summary ≤ ~400 tokens, others ≤ ~800; propose your own after measuring). The Schedule must be windowed (next N rows + yearly rollup + closure), never 280 rows. Formatting rules: INR with Indian digit grouping, dates like "10 Aug 2026". Rendering must be DETERMINISTIC (renderer function in the engine emits the markdown from computed values); the LLM must not re-derive or re-format numbers. Include one rendered example per report using real current data with identifiers redacted.
D. OPERATIONS (skill's write path): a catalog of every operation (report ops and mutation ops) with input schema, validation rules, confirmation policy (e.g. over-allocation), audit trail, resulting engine recomputation, and the impact summary shown after each mutation. Cover at minimum: OD balance add/subtract/set, disbursement, prepayment, rate change, payment logging, goals, contributions, sources, EMI reserve, plus whatever else the app does. Define "dry-run then commit" semantics.
E. STORAGE AND VERSIONING (Phase 2 runtime): evaluate options — local folder accessible from Claude Desktop, Google Drive (create/search/read only; no overwrite/delete), other. Recommend one with a fallback. Keep the append-only versioned-file audit trail if it still fits. Define concurrency, rollback, and pruning stories.
F. CAPABILITY TIERS for Phase 2: Tier A = code execution + persistent write; Tier B = code execution, read-only storage; Tier C = no code execution (Claude reads TSON + logic spec + pre-rendered reports). Define what works at each tier, and what Phase 1 must pre-generate so Tier C still gives correct read-only answers.
G. SKILL DESIGN: SKILL.md structure, trigger description, protocol per conversation (resolve latest data → load → compute → render → optionally mutate), formatting rules, error handling, invariants checked after every mutation. Also the Claude Project instruction text. Keep sensitive identifiers out of skill and instruction text.
H. HANDOFF BUNDLE: exact file list and folder layout, a manifest with checksums and versions, and the Phase 2 runbook.

### D3 — plan/03-implementation-plan.md

- Phase 1 and Phase 2 as ordered milestones, with dependency graph (text or mermaid), critical path, parallelizable work, and a definition of done + acceptance tests for each phase.
- Phase 1 must contain: change-audit follow-ups, data schema extraction, JSON→TSON converter + round-trip tests, logic spec, engine + operations + renderer, TS-generated golden fixtures + parity harness, screen→report mapping + templates, mutation catalog, skill + project-instruction drafts, handoff bundle + manifest + Phase 2 runbook, token measurements.
- Phase 2 (Claude Desktop, bundle only) must contain: capability probe (which tier applies), install bundle to the chosen storage, install skill, create Project, end-to-end test script (list each query/operation with expected value taken from the fixtures), mutation dry-run + rollback test, report-verbosity/trigger tuning, and the ongoing routine (e.g. monthly bank-statement update).

### D4 — plan/04-task-breakdown.md

One table, one row per task. Columns:
ID | Phase | Environment (Antigravity CLI / Claude Desktop) | Task | Inputs | Outputs (paths) | Depends on | Verifier (a concrete command or check) | Done signal | Suggested model | Suggested effort | Est. duration | Rationale for model/effort
Rules:

- Every task has an automated or checkable verifier. Tasks without one must be split until they do.
- Phase 1 tasks are sized so each can be run as an independent CLI session.
- MODEL/EFFORT RUBRIC:
  - Models available in Phase 1: Opus 4.6 (highest) and whichever Sonnet-class model my Antigravity offers. If a cheaper tier exists, name it only when confident.
  - Opus 4.6: design decisions, formula-fidelity work where a silent error corrupts money math, reconciling parity failures, skill/protocol design.
  - Sonnet-class: mechanical transforms, converters, test scaffolding, docs, templating, anything with a strong automated verifier.
  - Effort scale: low (mechanical, spec is complete) / medium (standard implementation + tests) / high (ambiguity or cross-file reasoning) / max (design or debugging parity).
  - For Phase 2 tasks, name model TIERS (Opus-class / Sonnet-class / Haiku-class), not versions, because the Claude Desktop lineup may differ from mine.
- End with a summary table: total tasks per model/effort, critical path, and a suggested run order.

### D5 — plan/05-open-questions.md

Decisions I need to confirm, ranked by how much they would change the plan. Each has your chosen default and the impact of the alternative.

### D6 — plan/task-prompts/ (do this last; if you are running low on context, finish D0–D5 fully first and list which prompts remain)

For EACH Phase 1 task: a self-contained prompt file P1-XX-<name>.md that a fresh CLI session could run with no other context. Include the goal, exact inputs/outputs, constraints, verifier command, and done signal. Max ~60 lines each.
For Phase 2: one file, phase2-runbook.md, with numbered steps I can follow in Claude Desktop, the exact text to paste for the Project instructions, and the end-to-end test script.

## 4. QUALITY BAR (self-check before finishing)

- Every screen and every mutation found in D0 appears in the D1 parity matrix.
- Every task in D4 has a verifier and a model/effort with a rationale.
- Nothing in the design depends on a hardcoded number from the old plan.
- Phase 2 needs nothing except the handoff bundle.
- Claims are evidence-tagged; assumptions are recorded in D5, not buried in prose.

## 5. FINAL OUTPUT

When done, print: (1) the list of files written, (2) the 10-line change-audit headline (what changed since 2026-08-05), (3) the top 5 open questions, (4) the critical path and total task count by model/effort.

ALL OUTPUT SHOULD BE MARKDOWN FILES.
WRITE ALL OUTPUT MARKDOWN FILES TO `/Agent_Docs` FOLDER. CREATE SUB-FOLDERS IF REQUIRED.
