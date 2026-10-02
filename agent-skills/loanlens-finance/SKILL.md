---
name: loanlens-finance
description: |
  Home loan management skill for an OD-linked (overdraft-linked) home loan
  with reducing balance and daily interest accrual. Computes amortization
  schedules, EMI breakdowns, interest saved, projected closure dates,
  overdraft savings waterfall analysis, goal tracking, and contribution
  ledgers. Simulates what-if scenarios including prepayments, rate changes,
  extra disbursements, and tenure adjustments.

  Trigger this skill when the user asks about: home loan, EMI, equated
  monthly installment, OD balance, overdraft savings, interest saved,
  interest accrued, prepayment, part-payment, lump-sum payment, rate change,
  floating rate, RLLR, tenure, loan closure, loan payoff, amortization
  schedule, repayment schedule, disbursement, tranche, loan summary,
  loan health, principal outstanding, sanctioned amount, moratorium,
  pre-EMI interest, OD waterfall, savings goal, contribution, deduction,
  due date, payment log, ledger, loan balance, daily interest, reducing
  balance, day count convention.
---

# LoanLens — Home Loan Tracker

## Description

LoanLens tracks an OD-linked home loan: it computes amortization schedules
with daily interest accrual, manages OD savings goals and contributions, and
simulates what-if scenarios (prepayments, rate changes, extra disbursements).
All financial computations are performed by a validated Python engine bundled
inside this skill — the LLM must never estimate, approximate, or do mental
math.

## Drive Configuration

- **Folder ID:** `1INKH5EtY6y8xUB4Jfk1_PEGOcI4hR1yo`
- **Contents:** This Drive folder contains **only the two mutable data files**
  that change at runtime:
  - `loan_data.v*.toon` — versioned loan data (disbursements, payments, rates)
  - `od_savings.v*.toon` — versioned OD savings data (goals, contributions,
    balances)
- **Nothing else should be fetched from Drive.** The engine, spec, and reports
  all ship inside this skill package and are read from the skill's own bundled
  files at runtime.
- **Version resolution:** Search the Drive folder for files matching each
  pattern (`loan_data.v*.toon` and `od_savings.v*.toon`). The file with the
  **most recent `modifiedTime`** is the current version. No manifest file is
  used for version resolution.

## Protocol

### Step 1 — Resolve Data

Fetch the two mutable data files from Google Drive folder
`1INKH5EtY6y8xUB4Jfk1_PEGOcI4hR1yo`:

1. List files in the folder matching `loan_data.v*.toon`.
2. List files in the folder matching `od_savings.v*.toon`.
3. For each pattern, select the file with the most recent `modifiedTime`.
4. Read both files.

### Step 2 — Load

Parse the TOON files to Pydantic models using this skill's own bundled
`engine/__init__.py`:

```python
from engine import load_data

loan_data, od_data = load_data(loan_toon_content, od_toon_content)
```

The converter is loaded from the skill directory — it is never fetched from
Drive or any external source.

### Step 3 — Compute

Run the computation engine (bundled in this skill's `engine/` directory):

```python
from engine.schedule import generate_schedule
from engine.metrics import calculate_metrics

schedule = generate_schedule(loan_data, today_date="YYYY-MM-DD")
metrics = calculate_metrics(loan_data, schedule, today_date="YYYY-MM-DD")
```

**Always pass `today_date` explicitly** as a `YYYY-MM-DD` string. The engine
never reads the system clock. Use the current date at the time of the user's
query.

### Step 4 — Render or Mutate

- **Read operations (R1–R5):** Call the matching `render_*` function in
  `engine/renderer.py`. Display the returned markdown **verbatim** — do not
  re-derive, round, or reformat any numbers.

- **Write operations (W1–W15):** Call the matching function in
  `engine/operations.py`:
  1. The function validates inputs and performs a **dry-run**, returning an
     impact summary.
  2. If confirmation is required (per the confirmation policy table below),
     show the impact summary to the user and **wait for explicit approval**
     before committing.
  3. On approval, commit the changes by converting the mutated models back to TOON using `dict_to_toon` (passing `.model_dump()` to it). Output the new TOON content inside Markdown code blocks and prompt the user to manually save them to the Google Drive folder.
  4. Before confirming the operation, **check all invariants** (see § Invariants below) using the `validate_invariants` function.

### Step 5 — Respond

Present the rendered report or the mutation result to the user.

## Available Operations

### Read Operations

| ID | Function | Description |
|----|----------|-------------|
| R1 | `render_summary(loan_data, od_data, today_date)` | Snapshot of loan health: phase, principal, OD, savings, next due date |
| R2 | `render_od_savings(loan_data, od_data, today_date)` | OD waterfall, goal progress, recent contributions, balance trend |
| R3 | `render_schedule(loan_data, today_date, window=6)` | Next N installments + yearly summary + projected closure |
| R4 | `render_simulator(base_loan, sim_loan, today_date, desc)` | Side-by-side base vs. simulated scenario comparison |
| R5 | `render_ledger(loan_data, od_data, today_date)` | Disbursement log, payment log, OD balance history |

### Write Operations

| ID | Function | Description | Confirm? |
|----|----------|-------------|----------|
| W2 | `add_disbursement(loan, date, amount, ...)` | Add a loan tranche disbursement | If >₹10L or nearing sanctioned |
| W3 | `add_prepayment(loan, date, amount, ...)` | Record a lump-sum prepayment | Always (shows tenure/interest impact) |
| W4 | `add_rate_change(loan, effective_date, rate, ...)` | Add a new interest rate effective date | Always (shows EMI/tenure impact) |
| W5 | `update_payment(loan, due_date, amount_paid, ...)` | Update a payment log entry | Auto |
| W6 | `update_emi_reserve(od, amount)` | Set the EMI reserve amount in OD | If causes over-allocation |
| W7 | `add_source(od, name, ...)` | Create a new contribution source | Auto |
| W8 | `edit_source(od, source_id, ...)` | Edit an existing source | Auto |
| W9 | `add_goal(od, name, target_amount, ...)` | Create a new savings goal | If causes over-allocation |
| W10 | `edit_goal(od, goal_id, patch)` | Edit a savings goal | If allocation change causes over-allocation |
| W11 | `add_contribution(od, date, amount, source_id, ...)` | Record a contribution to OD | Auto |
| W12 | `edit_contribution(od, contribution_id, patch)` | Edit a past contribution | Auto |
| W14 | `process_due_payments(loan, od, today_date)` | Auto-deduct due EMI/interest from OD | Always (shows deduction details) |
| W15 | `update_settings(loan, patch)` | Update loan settings (due day, policy, etc.) | Always (shows before/after) |

## Formatting Rules

- **Currency:** INR with Indian digit grouping — `₹12,34,567` not
  `₹1,234,567`. Use `engine/renderer.py:fmt_inr()`.
- **Dates:** `10 Aug 2026` in rendered reports; `YYYY-MM-DD` in data files
  and engine parameters.
- **Deterministic rendering:** Reports are produced by the engine's `render_*`
  functions. The LLM must display them **verbatim** and never re-derive,
  round, or reformat any numbers.
- **Privacy:** Never expose account numbers, personal names, or other PII in
  conversation output.
- **Always use the engine** for any financial calculation — never estimate,
  approximate, or do mental math. If the user asks a question that requires
  a number, run the engine.
- **Always pass today's date** explicitly to every engine function. Never rely
  on the system clock or allow the engine to default to `None`.
- **Dry-run before mutating** — always show the impact summary before
  committing any data change. Never commit without the user seeing the
  dry-run output first.
- **Check invariants after every mutation** — see § Invariants below.

## Error Handling

- **Missing data file:** Report the error clearly. If no matching
  `loan_data.v*.toon` or `od_savings.v*.toon` is found in the Drive folder,
  inform the user and suggest uploading or restoring the data.
- **Validation failure:** The engine raises `ValueError` with a specific
  message. Display it to the user verbatim and suggest the correction.
- **Computation error:** If a computed value looks wrong, check the test suite in `tests/` or re-verify the daily interest accrual loop logic against `spec/logic-spec.md`.
- **Stale data:** If the user references data that seems outdated, re-check
  the Drive folder for the file with the most recent `modifiedTime`.

## Invariants (checked after every mutation)

1. Total disbursed ≤ sanctioned amount (`loanDetails.sanctionedAmount`)
2. OD balance ≥ 0
3. All goal `allocatedAmount` values ≥ 0
4. `paymentLog` dates are unique (one entry per due date)
5. TOON `[N]` headers match actual row counts after conversion
6. Round-trip integrity: `toon_to_json(json_to_toon(data)) == data`

## File Paths

| Path | Location | Contents |
|------|----------|----------|
| `engine/*.py` | Bundled in this skill | Python computation engine (schedule, metrics, EMI, operations, renderer, converter) |
| `spec/logic-spec.md` | Bundled in this skill | Language-neutral formula specification |
| `spec/schemas.md` | Bundled in this skill | TOON and JSON data schemas |
| `reports/*.md` | Bundled in this skill | Pre-rendered reports for fallback (no code execution) |
| `loan_data.v*.toon` | Google Drive folder `1INKH5EtY6y8xUB4Jfk1_PEGOcI4hR1yo` | Versioned loan data (mutable) |
| `od_savings.v*.toon` | Google Drive folder `1INKH5EtY6y8xUB4Jfk1_PEGOcI4hR1yo` | Versioned OD savings data (mutable) |

## Key Facts

- **Lender type:** Bank (RLLR-linked)
- **Loan type:** OD-linked home loan (reducing balance, daily interest accrual)
- **Day count convention:** 365
- **Current phase:** Moratorium (18 months from first disbursement)
- **EMI phase begins:** August 2027
- **Current rate:** 7.6% p.a. (RLLR benchmark + spread)
- **Prepayment policy:** `adjust_tenure` (EMI stays fixed; tenure shortens)
