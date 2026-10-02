# LoanLens — Home Loan Tracker

## Description
LoanLens tracks an OD-linked home loan: it computes amortization schedules with daily interest accrual, manages OD savings goals and contributions, and simulates what-if scenarios (prepayments, rate changes, extra disbursements).

## Trigger
Activate when the user asks about their home loan, EMI, overdraft (OD) savings, interest calculations, amortization schedule, prepayment impact, loan closure date, or wants to update any loan data.

## Protocol
1. **Resolve data** — read `data/manifest.json` to find the current version of `loan_data` and `od_savings` TOON files.
2. **Load** — read the versioned `.toon` files from `data/`, parse them to JSON via `engine/converter.py` (`toon_to_json`).
3. **Compute** — run `engine/schedule.py` → `generate_schedule()` then `engine/metrics.py` → `calculate_metrics()`. Always pass `today_date` explicitly (YYYY-MM-DD); the engine never reads the system clock.
4. **Render or Mutate**:
   - *Read ops (R1–R5):* call the matching `render_*` function in `engine/renderer.py`. Display the returned markdown verbatim — do **not** re-derive or reformat any numbers.
   - *Write ops (W1–W15):* call the matching function in `engine/operations.py`. It validates → dry-runs → returns an impact summary. If confirmation is needed, show the summary and wait for user approval before committing.
5. **Respond** — present the rendered report or the mutation result to the user.

## Available Operations

### Read Operations
| ID | Function | Description |
|---|---|---|
| R1 | `render_summary(loan_data, od_data, today_date)` | Snapshot of loan health: phase, principal, OD, savings, next due date |
| R2 | `render_od_savings(loan_data, od_data, today_date)` | OD waterfall, goal progress, recent contributions, balance trend |
| R3 | `render_schedule(loan_data, today_date, window=6)` | Next N installments + yearly summary + projected closure |
| R4 | `render_simulator(base_loan, sim_loan, today_date, desc)` | Side-by-side base vs. simulated scenario comparison |
| R5 | `render_ledger(loan_data, od_data, today_date)` | Disbursement log, payment log, OD balance history |

### Write Operations
| ID | Function | Description | Confirm? |
|---|---|---|---|
| W1 | `update_od_balance(loan, od, date, balance, ...)` | Record a new OD balance snapshot | Auto |
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
| W13 | `edit_od_annotation(od, od_balance_log_id, ...)` | Annotate an OD balance entry | Auto |
| W14 | `process_due_payments(loan, od, today_date)` | Auto-deduct due EMI/interest from OD | Always (shows deduction details) |
| W15 | `update_settings(loan, patch)` | Update loan settings (due day, policy, etc.) | Always (shows before/after) |

## Formatting Rules
- **Currency:** INR with Indian digit grouping — `₹12,34,567` not `₹1,234,567`. Use `engine/renderer.py:fmt_inr()`.
- **Dates:** `10 Aug 2026` in rendered reports; `YYYY-MM-DD` in data files and engine parameters.
- **Deterministic rendering:** Reports are produced by the engine's `render_*` functions. The LLM must display them verbatim and never re-derive, round, or reformat any numbers.
- **Privacy:** Never expose account numbers, personal names, or other PII in conversation output.

## Error Handling
- **Missing data file:** Report the error clearly. Suggest restoring from `archive/` using the versioning protocol.
- **Validation failure:** The engine raises `ValueError` with a specific message. Display it to the user and suggest the correction.
- **Computation error:** Run the parity check against `fixtures/` to verify engine integrity. Report the discrepancy if found.
- **Stale data:** If the user references data that seems outdated, check `manifest.json` for the latest version.

## Invariants (checked after every mutation)
1. Total disbursed ≤ sanctioned amount (`loanDetails.sanctionedAmount`)
2. OD balance ≥ 0
3. All goal `allocatedAmount` values ≥ 0
4. `paymentLog` dates are unique (one entry per due date)
5. TOON `[N]` headers match actual row counts after conversion
6. Round-trip integrity: `toon_to_json(json_to_toon(data)) == data`

## File Paths (within the bundle)
| Path | Contents |
|---|---|
| `data/*.toon` | Versioned loan and OD savings data |
| `data/manifest.json` | Current version pointer + checksums |
| `engine/*.py` | Python computation engine (schedule, metrics, EMI, operations, renderer, converter) |
| `fixtures/*.json` | Golden test fixtures (8 scenarios) |
| `spec/logic-spec.md` | Language-neutral formula specification |
| `reports/*.md` | Pre-rendered reports for Tier C (no code execution) fallback |
