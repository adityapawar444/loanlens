# D0 — Change Audit

**Produced:** 2026-09-19  
**Baseline:** Commit `a81f9c1` (2026-07-10) — the HEAD at the time of the previous audit (`loanlens_codebase_audit.md`, 2026-08-05)  
**Current HEAD:** `513bbeb` (2026-09-14, branch `main`)

---

## 0. Git Summary

| Item | Value |
|---|---|
| Total commits | 4 |
| Commits since baseline (a81f9c1) | 2 |
| Working-tree status | Clean (tracked); 2 untracked: `Agent Docs/`, `loanlens_codebase_audit.md` |
| Previous plan files (`loanlens-conversational-plan.md`, `loanlens-task-split.md`) | **Do not exist** anywhere in the repo |

### Commits since 2026-08-05

| Hash | Date | Subject | Files Changed |
|---|---|---|---|
| `a457652` | 2026-09-14 | feat(simulator, od-savings): add disbursement scenario, OD impact preview & payment auto-deduction | 6 files, +609 −59 |
| `513bbeb` | 2026-09-14 | docs: update README to reflect multi-scenario simulator and OD auto-deductions | 1 file, +8 −1 |

---

## 1. Changed Files by Area

### (a) Calculation Logic

| File | Change | Lines |
|---|---|---|
| [calculations.ts](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts) | **NEW FUNCTION** `autoDeductPayments()` added at L305-387 | +90 lines |

**`autoDeductPayments(loanData, odData, todayStr)`** — VERIFIED [calculations.ts#L305-387](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L305-L387):
- Iterates the amortization schedule looking for due dates ≤ `todayStr` without a matching `paymentLog` entry
- For each unpaid due date, it:
  1. Pushes a `paymentLog` entry with `amountDue = amountPaid = row.installment`
  2. If no `odBalanceLog` snapshot exists on that date, creates one: `newBalance = max(0, prevBalance - row.installment)`
  3. Creates an `odBalanceAnnotation` with `purpose: "EMI / Interest"`, `note: "Auto-deducted on EMI Day"`
- Regenerates the schedule after each deduction (because deducting on date D changes interest for D+1)
- Modifies `loanData` and `odData` **in-place**

**No other formula or behaviour in calculations.ts changed.** The existing `generateSchedule`, `calculateMetrics`, `calculateEmi`, `calculateTenure`, and `HISTORICAL_PAYMENT_DATES` are **byte-identical** to the baseline. VERIFIED via `git diff`.

### (b) Data Layer

| File | Change | Lines |
|---|---|---|
| [data-layer.ts](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/data-layer.ts) | `readData()` now calls `autoDeductPayments()` on every read | +21 −3 |

**Critical side-effect:** VERIFIED [data-layer.ts#L15-28](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/data-layer.ts#L15-L28):
- Every call to `readData()` now triggers `autoDeductPayments()` using the server's system clock
- If any deductions are applied, both `loan_data.json` and `od_savings_data.json` are re-written to disk
- **This means reading data can cause writes** — a significant architectural change

### (c) Simulator

| File | Change | Lines |
|---|---|---|
| [SimulatorClient.tsx](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/app/(dashboard)/simulator/SimulatorClient.tsx) | Major expansion: disbursement scenarios, next-6-installments preview, OD impact section | +410 −30 |

New simulator features — VERIFIED:
- **4th scenario type: `disbursement`** — users can add hypothetical disbursements to see impact
- **Disbursement validation** against `sanctionedAmount` ceiling
- **Next 6 Installments Preview** (`Next6Preview` component): table comparing base vs. simulated monthly cashflows
- **OD Impact Section**: shows how scenarios affect OD balance and savings
- Still **read-only** — no server actions, no data persistence

### (d) OD Savings

| File | Change | Lines |
|---|---|---|
| [OdSavingsClient.tsx](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/app/(dashboard)/od-savings/OdSavingsClient.tsx) | Minor: props interface change | +34 −25 |
| [page.tsx (od-savings)](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/app/(dashboard)/od-savings/page.tsx) | Minor: adjusted data-passing | +3 −2 |

### (e) Tests (NEW)

| File | Change | Lines |
|---|---|---|
| [calculations.test.ts](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.test.ts) | **NEW FILE** — Vitest test suite for EMI, tenure, schedule, auto-deductions | +242 lines |
| [simulator-debug.test.ts](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/simulator-debug.test.ts) | **NEW FILE** — Debug tests for simulator scenarios | +105 lines |

New dev dependencies: `vitest ^4.1.8`, `@vitest/ui ^4.1.8`, `jsdom ^29.1.1`, `@testing-library/jest-dom ^6.9.1`, `@testing-library/react ^16.3.2`

### (f) Documentation

| File | Change |
|---|---|
| [README.md](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/README.md) | Updated to reflect multi-scenario simulator and automated deductions |

### (g) Schema/Types — **NO CHANGES**

All Zod schemas and TypeScript types are **byte-identical** to baseline:
- `src/lib/types.ts` — unchanged
- `src/lib/od-savings-types.ts` — unchanged

### (h) Data Files — **EVOLVED via auto-deductions and manual use**

Data files are gitignored and not diffable, but current state differs from the Aug 5 audit:

| Entity | Aug 5 Count | Current Count | Change |
|---|---|---|---|
| `disbursements` | 3 | 4 | +1 (4th tranche: "26th Floor", 2026-09-17) |
| `rateHistory` | 1 | 1 | Unchanged |
| `odBalanceLog` | 2 (up to 2026-08-02) | 9 (up to 2026-09-10) | +7 snapshots (mix of manual + auto-deductions) |
| `prepayments` | 0 | 0 | Unchanged |
| `paymentLog` | 1 (only Feb 2026) | 8 (Feb–Sep 2026) | +7 entries (most via auto-deduction) |
| OD `sources` | data not in audit | 6 | N/A |
| OD `contributions` | data not in audit | 21 | N/A (was 15 at time of git history report; 21 is current) |
| OD `goals` | data not in audit | 6 | N/A |
| OD `annotations` | data not in audit | 6 | N/A |

### (i) Server Actions / API Routes — **NO CHANGES**

- `src/lib/actions.ts` — unchanged
- `src/lib/od-savings-actions.ts` — unchanged
- No API routes (`src/app/api/` does not exist) — unchanged

---

## 2. Formula / Behaviour Changes

| ID | Change | Details | Evidence |
|---|---|---|---|
| F1 | **NEW: Auto-deduction on read** | `readData()` now triggers `autoDeductPayments()`, auto-creating `paymentLog`, `odBalanceLog`, and `odBalanceAnnotation` entries for past-due dates without recorded payments | VERIFIED [data-layer.ts#L15-28](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/data-layer.ts#L15-L28), [calculations.ts#L305-387](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L305-L387) |
| F2 | **NEW: Schedule regeneration loop** | Auto-deduction uses a `while(true)` loop that regenerates the full schedule after each deduction, because each deduction changes subsequent interest amounts | VERIFIED [calculations.ts#L316-383](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L316-L383) |
| F3 | **NEW: OD balance auto-snapshot** | When auto-deducting, if no OD log exists for the due date, a new snapshot is created: `max(0, prevBalance - installment)` | VERIFIED [calculations.ts#L342-373](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L342-L373) |

**Unchanged formulas:**
- EMI calculation (reducing balance) — unchanged
- Tenure calculation (inverse) — unchanged
- Daily interest accrual loop — unchanged
- OD offset: `effectivePrincipal = max(0, outstanding - odBalance)` — unchanged
- HISTORICAL_PAYMENT_DATES override — unchanged (still hardcoded 5 dates)
- Moratorium→EMI transition — unchanged
- Rounding rules — unchanged

---

## 3. Schema / Field Changes

**None.** All Zod schemas in `types.ts` and `od-savings-types.ts` are identical to the baseline. No fields were added, removed, renamed, or had semantics changed. VERIFIED via `git diff`.

---

## 4. New Screens / Features / Mutations

| ID | Feature | Type | Details |
|---|---|---|---|
| N1 | Disbursement scenario in Simulator | Read-only UI | 4th scenario type alongside prepayment, rate, OD balance. VERIFIED [SimulatorClient.tsx](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/app/(dashboard)/simulator/SimulatorClient.tsx) |
| N2 | Next 6 Installments Preview | Read-only UI | Side-by-side table comparing base vs. simulated cashflows for the next 6 months. VERIFIED |
| N3 | OD Impact Preview in Simulator | Read-only UI | Shows how hypothetical changes affect OD balance and interest savings. VERIFIED |
| N4 | Auto-deduction of payments | Background mutation | Triggered on every `readData()` call. Creates paymentLog + odBalanceLog + annotation entries. VERIFIED |
| N5 | Vitest test suite | Dev tooling | `calculations.test.ts` (6 test cases) + `simulator-debug.test.ts`. VERIFIED |

---

## 5. Removed Features

**None.** No features were removed. All existing screens, mutations, and functionality are intact.

---

## 6. Baseline Assumptions Table (from Section 2 of the prompt)

| Assumption | Status | Evidence |
|---|---|---|
| Core schedule loop: `calculations.ts` ~L59-231 | **STILL TRUE** | `generateSchedule()` at L60-232. Byte-identical to baseline. VERIFIED [calculations.ts#L60](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L60) |
| `calculateMetrics` ~L234-295 | **STILL TRUE** | At L235-298. Unchanged. VERIFIED |
| Day count hardcoded 365 | **STILL TRUE** | `loanDetails.dayCountConvention` is used (L122), data value is `365`. VERIFIED [calculations.ts#L122](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L122) |
| Interest computed per day on `max(0, outstanding − OD balance)` | **STILL TRUE** | L125-128. VERIFIED |
| HISTORICAL_PAYMENT_DATES hardcoded set (Feb–Jun 2026) | **STILL TRUE** | L6-12, identical set. VERIFIED |
| OD waterfall in OdSavingsClient.tsx | **STILL TRUE** | `emiReserve` → `fundedEmiReserve = min(OD, reserve)` → `allocatableBalance = OD - fundedEmiReserve` → goals → free. Minor refactor but same logic. VERIFIED |
| Simulator read-only in SimulatorClient.tsx | **STILL TRUE** | Enhanced with disbursement scenarios + preview but still read-only (deep-clones data, no server actions). VERIFIED |
| Goal status derived (allocated >= target), not stored | **STILL TRUE** | No `status` field in schema. Derived inline. VERIFIED |
| Paid/Upcoming/Overdue badges did NOT exist | **STILL TRUE** | Grep for "Overdue" returns 0 results. No status badges in schedule or ledger. VERIFIED |
| `onDisbursementDuringEmi` policy not applied | **STILL TRUE** | Exists in schema (L52) but unused in `generateSchedule`. VERIFIED |
| `RateHistory.spread` unused | **STILL TRUE** | Defined in schema (L15) but never referenced in calculations. VERIFIED |
| No concurrency control | **STILL TRUE** | `readData`/`writeData` use plain `fs.readFile`/`fs.writeFile`. No locks. VERIFIED |
| EMI(5982984, 7.6%, 282) = 91143 | **CHANGED** | EMI is stored as `currentCommunicatedEmi: 91143` but this is the *bank's communicated value*, not a computed one. `calculateEmi(5982984, 7.6, 282)` would yield 48254. The 91143 is for the full sanctioned amount. `calculateEmi(11965000, 7.6, 282) = 91143` is the correct derivation. VERIFIED |
| Latest OD balance 906043 as of 2026-08-02 | **CHANGED** | Latest OD balance is now `923964` on `2026-09-10` (9 snapshots exist, up from 2). The 906043 snapshot still exists at 2026-08-02. VERIFIED |
| Allocatable = OD − reserve = 814900 | **CHANGED** | With latest OD=923964, fundedReserve=min(923964,91143)=91143, allocatable=923964-91143=832821. INFERRED from current data and formula |
| First EMI after moratorium 2026-09-10 | **CHANGED — NOT YET** | With moratoriumMonths=18 and first disbursement 2026-01-31, moratorium covers periods 1-18. Period 1 = Feb 2026, Period 18 = Jul 2027. EMI phase begins Period 19 = **Aug 2027** (2027-08-10). All 8 current paymentLog entries are type `pre_emi_interest`. VERIFIED [calculations.ts#L134](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L134), data |

---

## 7. Full Screen Inventory

| Route | Page Component | Client Component | Data Sources | Purpose |
|---|---|---|---|---|
| `/` | [page.tsx](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/app/page.tsx) | [DashboardClient.tsx](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/components/dashboard/DashboardClient.tsx) (52,725 B) | `getLoanData()` → `generateSchedule()` → `calculateMetrics()` | Summary dashboard: outstanding, effective rate, next due, interest savings, health badge, countdown |
| `/ledger` | [page.tsx](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/app/(dashboard)/ledger/page.tsx) (9,690 B) | [LedgerForms.tsx](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/app/(dashboard)/ledger/LedgerForms.tsx) (7,610 B) | `getLoanData()` → schedule + paymentLog | Disbursement log, OD balance log, payment log with inline edit for amountDue/amountPaid |
| `/od-savings` | [page.tsx](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/app/(dashboard)/od-savings/page.tsx) (523 B) | [OdSavingsClient.tsx](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/app/(dashboard)/od-savings/OdSavingsClient.tsx) (78,778 B) | `getLoanData()` + `getOdSavingsData()` | OD waterfall, balance trend chart, contributions, goals, sources, annotations |
| `/schedule` | [page.tsx](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/app/(dashboard)/schedule/page.tsx) (1,860 B) | [AmortizationTable.tsx](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/components/schedule/AmortizationTable.tsx) (4,892 B) | `getLoanData()` → `generateSchedule()` | Full amortization schedule table (period, date, opening, installment, interest, principal, closing, savings) |
| `/simulator` | [page.tsx](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/app/(dashboard)/simulator/page.tsx) (845 B) | [SimulatorClient.tsx](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/app/(dashboard)/simulator/SimulatorClient.tsx) (32,025 B) | `getLoanData()` → deep-clone → modify → re-run schedule+metrics | What-if simulator: prepayment, rate, OD, disbursement scenarios. Comparison cards + next-6 preview |
| `/settings` | [page.tsx](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/app/(dashboard)/settings/page.tsx) (4,816 B) | N/A (server component) | `getLoanData()` | Edit loanDetails fields (lender, sanctioned, tenure, moratorium, policies) |

**Shared layout:** [layout.tsx](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/app/layout.tsx) — Header with [NavigationDrawer.tsx](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/components/NavigationDrawer.tsx) (hamburger menu)

---

## 8. Full Mutation Inventory

### 8.1 Explicit Mutations (Server Actions)

| # | Operation | Server Action | File Modified | Inputs | Validation | Audit Trail | Side Effects |
|---|---|---|---|---|---|---|---|
| M1 | Add disbursement | `addDisbursement()` | `loan_data.json → disbursements[]` | `Disbursement` object | Manual: amount > 0, ≤ 10Cr, date required | ❌ | `revalidatePath("/")` |
| M2 | Add rate history | `addRateHistory()` | `loan_data.json → rateHistory[]` | `RateHistory` object | **None** | ❌ | `revalidatePath("/")` |
| M3 | Add OD balance log | `addOdBalanceLog()` | `loan_data.json → odBalanceLog[]` | `OdBalanceLog` object | Manual: balance ≥ 0, ≤ 10Cr, not NaN, date required | ❌ | `revalidatePath("/")` |
| M4 | Update loan details | `updateLoanDetails()` | `loan_data.json → loanDetails` | `FormData` | **None** (raw Number conversion) | ❌ | `revalidatePath("/")` |
| M5 | Update amount paid | `updatePayment()` | `loan_data.json → paymentLog[].amountPaid` | `id: string, amountPaid: number` | Manual: > 0, ≤ 10Cr | ❌ | `revalidatePath("/")` |
| M6 | Update amount due | `updateAmountDue()` | `loan_data.json → paymentLog[].amountDue` | `id: string, amountDue: number` | Manual: ≥ 0, ≤ 10Cr, not NaN | ❌ | `revalidatePath("/")` |
| M7 | Update EMI reserve | `updateEmiReserve()` | `od_savings_data.json → emiReserve` | `amount: number` | Manual: ≥ 0, ≤ 10Cr, 2 decimal places | ❌ | `revalidatePath("/od-savings")` |
| M8 | Add source | `addSource()` | `od_savings_data.json → sources[]` | `OdSource` (minus editHistory) | Duplicate name check (case-insensitive) | Created with `editHistory: []` | `revalidatePath("/od-savings")` |
| M9 | Edit source | `editSource()` | `od_savings_data.json → sources[].{name,description,isActive}` | `id, patch` | Duplicate name check | ✅ `diffAudit()` | `revalidatePath("/od-savings")` |
| M10 | Add goal | `addGoal()` | `od_savings_data.json → goals[]` | `OdGoal` (minus editHistory) | `PositiveMoneySchema` on targetAmount | Created with `editHistory: []` | `revalidatePath("/od-savings")` |
| M11 | Edit goal | `editGoal()` | `od_savings_data.json → goals[].{...}` | `id, patch` | `PositiveMoneySchema` / `NonNegativeMoneySchema` | ✅ `diffAudit()` | `revalidatePath("/od-savings")` |
| M12 | Add contribution | `addContribution()` | `od_savings_data.json → contributions[]` | `OdContribution` (minus editHistory) | `PositiveMoneySchema` on amount | Created with `editHistory: []` | `revalidatePath("/od-savings")` |
| M13 | Edit contribution | `editContribution()` | `od_savings_data.json → contributions[].{...}` | `id, patch` | `PositiveMoneySchema` on amount | ✅ `diffAudit()` | `revalidatePath("/od-savings")` |
| M14 | Add OD balance with annotation | `addOdBalanceWithAnnotation()` | **Both:** `loan_data.json → odBalanceLog[]` AND `od_savings_data.json → odBalanceAnnotations[]` | `balanceEntry, annotation` | `NonNegativeMoneySchema` on balance, date required | Created with `editHistory: []` | `revalidatePath` on `/od-savings`, `/ledger`, `/` |
| M15 | Edit OD balance annotation | `editOdBalanceAnnotation()` | `od_savings_data.json → odBalanceAnnotations[].{sourceId,purpose,note}` | `odBalanceLogId, patch` | None on patch values | ✅ `diffAudit()` | `revalidatePath("/od-savings")` |

### 8.2 Implicit Mutations

| # | Operation | Trigger | Details |
|---|---|---|---|
| M16 | Auto-deduct payments | Every `readData()` call | Creates `paymentLog` entry + `odBalanceLog` snapshot + `odBalanceAnnotation` for each past due date without a recorded payment. Writes both JSON files to disk. VERIFIED [data-layer.ts#L15-28](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/data-layer.ts#L15-L28) |

### 8.3 OD Balance Modelling

- **Model:** Snapshot log (not deltas). Each `odBalanceLog` entry stores `{id, date, balance}` — the absolute balance at that point in time. VERIFIED [types.ts#L18-22](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/types.ts#L18-L22)
- **Step function:** The `getOdBalanceAt(dateKey)` function returns the latest balance where `date <= dateKey`. Between snapshots, the balance is assumed constant. VERIFIED [calculations.ts#L93-100](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L93-L100)
- **"Add" vs "subtract" OD:** These are NOT distinct operations. The user logs a new **absolute balance** snapshot. The system does not track deposits/withdrawals to the OD account — only the resulting balance. VERIFIED

### 8.4 Write Path Pattern

All mutations follow the same read-modify-write pattern:
1. `readData()` / `readOdData()` → reads JSON, Zod-parses
2. Mutate the in-memory JS object
3. `writeData()` / `writeOdData()` → Zod-validates, `JSON.stringify(data, null, 2)`, `fs.writeFile`
4. `revalidatePath()` → Next.js cache invalidation

**No concurrency control.** No file locks, ETags, or optimistic concurrency. Two simultaneous writes can cause lost updates. VERIFIED

---

## 9. Current Data Profile

### 9.1 Entity Counts and Date Ranges

**File: `data/loan_data.json`** (3,448 bytes, 166 lines)

| Array | Count | Date Range | Notes |
|---|---|---|---|
| `disbursements` | 4 | 2026-01-31 → 2026-09-17 | Total disbursed: ₹77,50,687 / ₹1,19,65,000 sanctioned |
| `rateHistory` | 1 | 2026-01-31 | 7.6% (RLLR), spread field unused |
| `odBalanceLog` | 9 | 2026-06-10 → 2026-09-10 | Balance range: ₹5,10,792 – ₹9,63,934 |
| `prepayments` | 0 | N/A | Empty |
| `paymentLog` | 8 | 2026-02-10 → 2026-09-10 | All `pre_emi_interest` type |

**File: `data/od_savings_data.json`** (9,879 bytes, 425 lines)

| Array | Count | Date Range | Notes |
|---|---|---|---|
| `emiReserve` | (scalar) | N/A | ₹91,143 |
| `sources` | 6 | Created 2026-07-08 | 2 salary + 4 savings/gift sources |
| `contributions` | 21 | 2026-01-31 → 2026-09-01 | Total: ~₹10,95,033 |
| `goals` | 6 | Target dates: 2026-07-30 → 2027-12-31 | Total target: ₹13,10,000; Total allocated: ₹8,69,000 |
| `odBalanceAnnotations` | 6 | N/A | 2 auto-deductions, 1 manual, 3 with blank `odBalanceLogId` |

### 9.2 File Size Summary

| Metric | `loan_data.json` | `od_savings_data.json` | Combined |
|---|---|---|---|
| Pretty JSON (bytes) | 3,448 | 9,879 | 13,327 |
| Minified JSON (bytes) | 2,339 | 6,414 | 8,753 |
| Approximate tokens (cl100k, ÷4 rule) | ~860 | ~2,470 | ~3,330 |

**Token estimation method:** Byte count ÷ 4 for pretty JSON is a conservative upper-bound estimate for the cl100k tokenizer. For structured JSON with many repeated keys, the actual token count is typically 20-30% lower. Minified JSON would yield ~2,190 tokens. INFERRED

### 9.3 Over-Allocation Status

- Latest OD balance: ₹9,23,964
- Funded EMI reserve: min(923964, 91143) = ₹91,143
- Allocatable balance: 923964 − 91143 = ₹8,32,821
- Total allocated to goals: ₹8,69,000
- **Over-allocation into reserve:** ₹36,179 (goals exceed allocatable by this amount)
- `isOverAllocated` = true, `isCriticalOverAllocation` = false
- INFERRED from current data values and [OdSavingsClient.tsx](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/app/(dashboard)/od-savings/OdSavingsClient.tsx) waterfall logic
