# LoanLens — Logic Specification

> **Produced:** 2026-09-25
> **Source commit:** `513bbeb` (branch `main`)
> **Primary source:** [`calculations.ts`](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts) (388 lines)

---

## Table of Contents

1. [Constants & Configuration](#1-constants--configuration)
2. [Utility Functions](#2-utility-functions)
3. [EMI Calculation](#3-emi-calculation)
4. [Tenure Calculation (Inverse)](#4-tenure-calculation-inverse)
5. [Rate Lookup — Step Function](#5-rate-lookup--step-function)
6. [OD Balance Lookup — Step Function](#6-od-balance-lookup--step-function)
7. [Amortization Schedule Generation](#7-amortization-schedule-generation)
   - 7.1 [Initialisation](#71-initialisation)
   - 7.2 [Main Loop & Due Date Advancement](#72-main-loop--due-date-advancement)
   - 7.3 [Daily Interest Accrual Loop](#73-daily-interest-accrual-loop)
   - 7.4 [OD Offset & Baseline Interest](#74-od-offset--baseline-interest)
   - 7.5 [Moratorium → EMI Transition](#75-moratorium--emi-transition)
   - 7.6 [HISTORICAL_PAYMENT_DATES Override](#76-historical_payment_dates-override)
   - 7.7 [Non-Historical Payment Logic](#77-non-historical-payment-logic)
   - 7.8 [Prepayment Policy Application](#78-prepayment-policy-application)
   - 7.9 [Row Construction & Opening Balance](#79-row-construction--opening-balance)
   - 7.10 [Termination Conditions](#710-termination-conditions)
8. [Summary Metrics Calculation](#8-summary-metrics-calculation)
9. [Auto-Deduct Payments](#9-auto-deduct-payments)
10. [Rounding Inventory](#10-rounding-inventory)
11. [Interest Savings Formulas](#11-interest-savings-formulas)
12. [Invariants & Constraints](#12-invariants--constraints)

---

## 1. Constants & Configuration

### HISTORICAL_PAYMENT_DATES

A hardcoded set of due-date strings for months where actuals came from PDF bank statements. **VERIFIED** — [`calculations.ts#L4-L12`](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L4-L12)

```
{
  "2026-02-10",
  "2026-03-10",
  "2026-04-10",
  "2026-05-10",
  "2026-06-10"
}
```

**Semantics:** For these dates, the schedule relies on `paymentLog.amountDue` and `paymentLog.amountPaid` instead of computed interest/principal splits. This allows reconciliation with bank statement actuals.

---

## 2. Utility Functions

### `parseDateOnly(dateKey: string): Date`

**VERIFIED** — [`calculations.ts#L14-L17`](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L14-L17)

Splits a `YYYY-MM-DD` string on `"-"`, converts segments to integers, and creates a `Date` in local timezone: `new Date(year, month - 1, day)`.

### `formatDateOnly(date: Date): string`

**VERIFIED** — [`calculations.ts#L19-L24`](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L19-L24)

Formats a `Date` as `YYYY-MM-DD` with zero-padded month and day.

---

## 3. EMI Calculation

**VERIFIED** — [`calculations.ts#L29-L35`](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L29-L35)

```
calculateEmi(principal, annualRate, tenureMonths) → integer
```

| Step | Formula |
|---|---|
| Guard | If `tenureMonths ≤ 0` → return `0` |
| Monthly rate | `r = annualRate / 12 / 100` |
| Zero-rate guard | If `r = 0` → return `principal / tenureMonths` |
| EMI | `emi = P × r × (1+r)^n / ((1+r)^n − 1)` |
| **Rounding** | `Math.round(emi)` ← **R1** |

**Return:** nearest integer (banker's rounding via JS `Math.round`).

---

## 4. Tenure Calculation (Inverse)

**VERIFIED** — [`calculations.ts#L40-L52`](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L40-L52)

```
calculateTenure(principal, annualRate, emi) → integer | Infinity
```

| Step | Formula |
|---|---|
| Guard | If `principal ≤ 0` → return `0` |
| Monthly rate | `r = annualRate / 12 / 100` |
| Zero-rate guard | If `r = 0` → return `principal / emi` (exact division, no rounding) |
| Infinity guard | If `emi ≤ principal × r` → return `Infinity` (loan can never be paid off) |
| Intermediate | `x = emi / (emi − principal × r)` |
| Tenure | `tenure = ln(x) / ln(1 + r)` |
| **Rounding** | `Math.ceil(tenure)` (rounds **up** — not `Math.round`) |

**Note:** The Infinity guard prevents `Math.log` of a non-positive number. When `emi` equals interest-only, the principal never reduces.

---

## 5. Rate Lookup — Step Function

**VERIFIED** — [`calculations.ts#L83-L91`](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L83-L91)

```
getRateAt(dateKey: string) → number
```

Implements a **step function** over sorted `rateHistory` entries:

1. If `sortedRates` is empty → return `0`
2. Start with `rate = sortedRates[0].annualRate`
3. For each entry `i`: if `sortedRates[i].effectiveDate ≤ dateKey` then `rate = sortedRates[i].annualRate`; else `break`
4. Return `rate`

**Semantics:** Returns the annual rate of the **last** rate entry whose `effectiveDate` is on or before the query date. Between rate changes, the rate is held constant (step function, not interpolation).

**Prerequisite:** `sortedRates` is sorted ascending by `effectiveDate`. Sorting is done at [`calculations.ts#L65`](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L65).

---

## 6. OD Balance Lookup — Step Function

**VERIFIED** — [`calculations.ts#L93-L100`](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L93-L100)

```
getOdBalanceAt(dateKey: string) → number
```

Implements a **step function** over sorted `odBalanceLog` entries:

1. Start with `balance = 0`
2. For each entry `i`: if `sortedOdLogs[i].date ≤ dateKey` then `balance = sortedOdLogs[i].balance`; else `break`
3. Return `balance`

**Semantics:** Returns the OD account balance as of the query date. Before the first snapshot date, balance is `0`. Between snapshots, balance is held constant.

**Prerequisite:** `sortedOdLogs` is sorted ascending by `date`. Sorting at [`calculations.ts#L66`](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L66).

---

## 7. Amortization Schedule Generation

**VERIFIED** — [`calculations.ts#L60-L233`](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L60-L233)

```
generateSchedule(data: LoanData, todayDate?: Date) → AmortizationRow[]
```

### 7.1 Initialisation

**VERIFIED** — [`calculations.ts#L61-L81`](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L61-L81)

| Variable | Initial Value | Source |
|---|---|---|
| `sortedDisbursements` | Copy of `disbursements`, sorted ascending by `date` | L64 |
| `sortedRates` | Copy of `rateHistory`, sorted ascending by `effectiveDate` | L65 |
| `sortedOdLogs` | Copy of `odBalanceLog`, sorted ascending by `date` | L66 |
| `sortedPrepayments` | Copy of `prepayments`, sorted ascending by `date` | L67 |
| `anchorDate` | First disbursement date (parsed to `Date`) | L71 |
| `currentDate` | Copy of `anchorDate` | L72 |
| `outstandingPrincipal` | `0` | L74 |
| `period` | `1` | L75 |
| `phase` | `"moratorium"` | L76 |
| `currentEmi` | `loanDetails.currentCommunicatedEmi` or `0` | L77 |
| `remainingTenure` | `loanDetails.totalTenureMonths` | L78 |
| `dIdx` (disbursement index) | `0` | L80 |
| `pIdx` (prepayment index) | `0` | L81 |

**Early exit:** If `sortedDisbursements` is empty → return `[]`. [`calculations.ts#L69`](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L69)

### 7.2 Main Loop & Due Date Advancement

**VERIFIED** — [`calculations.ts#L102-L230`](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L102-L230)

**Loop condition:** `outstandingPrincipal > 0.01 OR dIdx < sortedDisbursements.length`

**Next due date:** `nextDueDate = new Date(currentDate.year, currentDate.month + 1, loanDetails.dueDateDay)` — always advances by one calendar month, landing on the configured due-date day. [`calculations.ts#L103`](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L103)

**Date key:** `dateKey = formatDateOnly(nextDueDate)` — the `YYYY-MM-DD` string identifying this period's due date.

**End-of-period advancement:** `currentDate = new Date(nextDueDate); period++` — [`calculations.ts#L228-L229`](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L228-L229)

### 7.3 Daily Interest Accrual Loop

**VERIFIED** — [`calculations.ts#L106-L132`](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L106-L132)

Interest is computed **day by day** between the previous due date (`currentDate`) and the next due date (`nextDueDate`).

```
interestAccrued = 0
baselineInterestAccrued = 0
tempDate = currentDate (copy)

while tempDate < nextDueDate:
    tempDateKey = formatDateOnly(tempDate)

    // Apply any disbursements falling on this day
    while dIdx < len(disbursements) AND disbursements[dIdx].date == tempDateKey:
        outstandingPrincipal += disbursements[dIdx].amount
        dIdx++

    // Apply any prepayments falling on this day
    while pIdx < len(prepayments) AND prepayments[pIdx].date == tempDateKey:
        outstandingPrincipal -= prepayments[pIdx].amount
        pIdx++

    dailyRate = getRateAt(tempDateKey) / 100 / dayCountConvention
    odBalance = getOdBalanceAt(tempDateKey)
    effectivePrincipal = max(0, outstandingPrincipal - odBalance)

    interestAccrued += effectivePrincipal × dailyRate
    baselineInterestAccrued += outstandingPrincipal × dailyRate

    tempDate += 1 day
```

**Key details:**

| Parameter | Formula | Citation |
|---|---|---|
| `dailyRate` | `getRateAt(tempDateKey) / 100 / loanDetails.dayCountConvention` | [`calculations.ts#L122`](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L122) |
| `dayCountConvention` | Configurable field, default `365` | [`types.ts#L48`](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/types.ts#L48) |

**Important:** Disbursements and prepayments are applied *before* the day's interest is calculated, so on the day of a disbursement, the new principal accrues interest for that day.

### 7.4 OD Offset & Baseline Interest

**VERIFIED** — [`calculations.ts#L124-L129`](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L124-L129)

Two parallel accumulators run in the daily loop:

| Accumulator | Principal Used | Purpose |
|---|---|---|
| `interestAccrued` | `effectivePrincipal = max(0, outstanding - odBalance)` | Actual interest with OD offset |
| `baselineInterestAccrued` | `outstandingPrincipal` (full, no offset) | Counterfactual interest without OD offset |

The difference between baseline and actual yields the **interest savings** from the OD account.

### 7.5 Moratorium → EMI Transition

**VERIFIED** — [`calculations.ts#L134-L143`](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L134-L143)

```
if phase == "moratorium" AND period > moratoriumMonths:
    phase = "emi"
    currentEmi = loanDetails.currentCommunicatedEmi

    if policy.onPrepayment == "adjust_tenure":
        remainingTenure = calculateTenure(outstandingPrincipal, getRateAt(dateKey), currentEmi)
    else:  // "adjust_emi"
        remainingTenure = totalTenureMonths - moratoriumMonths
        currentEmi = calculateEmi(outstandingPrincipal, getRateAt(dateKey), remainingTenure)
```

**Semantics:**
- Moratorium lasts for `moratoriumMonths` periods. Period numbering starts at 1.
- Transition happens when `period > moratoriumMonths` (so period `moratoriumMonths` is the last moratorium period).
- At transition:
  - **adjust_tenure:** EMI is kept fixed (bank-communicated), tenure is recalculated.
  - **adjust_emi:** Tenure is fixed (remaining = total − moratorium), EMI is recalculated to fit the current outstanding.

### 7.6 HISTORICAL_PAYMENT_DATES Override

**VERIFIED** — [`calculations.ts#L153-L168`](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L153-L168)

When `dateKey` is in `HISTORICAL_PAYMENT_DATES`:

```
loggedPayment = paymentLog.find(p => p.dueDate == dateKey)

if loggedPayment exists:
    interestPaid = loggedPayment.amountPaid
    baselineInterest = loggedPayment.amountDue > 0 ? loggedPayment.amountDue : interestPaid
    interestSavings = max(0, baselineInterest - interestPaid)
    installment = interestPaid
    principalPaid = 0
else:
    // No entry yet — zero savings, show computed interest as installment
    interestSavings = 0
    installment = interestPaid  // (the computed value from the daily loop)
    principalPaid = 0
```

**Key semantics:**
- Historical months **always** have `principalPaid = 0` (moratorium-era).
- `amountDue` serves as the "expected bank charge" (baseline for savings).
- If `amountDue ≤ 0` or absent, baseline falls back to `amountPaid` (zero savings).
- `outstanding` is **not modified** — these are interest-only payments.

### 7.7 Non-Historical Payment Logic

**VERIFIED** — [`calculations.ts#L169-L199`](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L169-L199)

When `dateKey` is NOT in `HISTORICAL_PAYMENT_DATES`:

```
loggedPayment = paymentLog.find(p => p.dueDate == dateKey)

if loggedPayment exists:
    interestPaid = loggedPayment.amountPaid
    interestSavings = max(0, baselineInterest - interestPaid)

    if phase == "moratorium":
        installment = interestPaid
        principalPaid = 0
    else:  // "emi"
        installment = loggedPayment.amountPaid
        principalPaid = max(0, installment - interestPaid)
        outstandingPrincipal = max(0, outstandingPrincipal - principalPaid)

else (no logged payment):
    if phase == "moratorium":
        installment = interestPaid
        principalPaid = 0
    else:  // "emi"
        installment = currentEmi OR loanDetails.currentCommunicatedEmi

        if outstandingPrincipal + interestPaid <= installment:
            // Final period — loan closes
            installment = round(outstandingPrincipal + interestPaid)     ← R4
            principalPaid = outstandingPrincipal
            outstandingPrincipal = 0
        else:
            principalPaid = installment - interestPaid
            outstandingPrincipal = max(0, outstandingPrincipal - principalPaid)
```

**Key detail:** In EMI phase without a logged payment, the EMI source is `currentEmi || loanDetails.currentCommunicatedEmi` — the `||` fallback ensures a non-zero installment even if `currentEmi` was somehow `0`. [`calculations.ts#L188`](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L188)

### 7.8 Prepayment Policy Application

**VERIFIED** — [`calculations.ts#L202-L208`](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L202-L208)

Applied **every period** during the EMI phase (after payment processing):

```
if phase == "emi":
    if policy.onPrepayment == "adjust_tenure":
        remainingTenure = calculateTenure(outstandingPrincipal, getRateAt(dateKey), currentEmi)
    else:  // "adjust_emi"
        remainingTenure--
```

**Semantics:**
- **adjust_tenure:** EMI stays fixed; tenure is recalculated each period based on current outstanding.
- **adjust_emi:** Tenure counts down by 1 each period; EMI was set at transition time and does not change period-over-period (it is only set once at moratorium→EMI transition).

### 7.9 Row Construction & Opening Balance

**VERIFIED** — [`calculations.ts#L210-L222`](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L210-L222)

```
schedule.push({
    period:           period,
    dueDate:          dateKey,
    openingBalance:   round(outstandingPrincipal + (phase == "emi" ? principalPaid : 0)),    ← R5
    installment:      installment,
    interest:         interestPaid,
    baselineInterest: baselineInterest,
    interestSavings:  interestSavings,
    principal:        principalPaid,
    closingBalance:   round(outstandingPrincipal),                                           ← R6
    phase:            phase,
    effectivePrincipal: max(0, outstandingPrincipal - getOdBalanceAt(dateKey)),
})
```

**Opening balance formula:**
- **EMI phase:** `round(outstanding + principalPaid)` — adds back the principal just paid to show the balance *before* the payment.
- **Moratorium phase:** `round(outstanding)` — no principal component, so opening = outstanding as-is.

**Closing balance:** Always `round(outstandingPrincipal)` after all payments.

**`effectivePrincipal` on the row:** Snapshot of `max(0, outstanding - odBalance)` at the due date, used for display/metrics.

### 7.10 Termination Conditions

**VERIFIED** — [`calculations.ts#L224-L226`](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L224-L226)

Two termination conditions are checked **after** the row is pushed but **before** incrementing period/date:

1. **Loan closure:** `outstandingPrincipal ≤ 0.01 AND dIdx ≥ sortedDisbursements.length` — loan is fully paid and no more disbursements pending.
2. **Safety break:** `period > 600` — prevents infinite loops (e.g., if EMI < interest-only). [`calculations.ts#L226`](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L226)

---

## 8. Summary Metrics Calculation

**VERIFIED** — [`calculations.ts#L235-L298`](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L235-L298)

```
calculateMetrics(data: LoanData, schedule: AmortizationRow[], todayDate?: Date) → SummaryMetrics
```

**Empty schedule guard:** Returns a zeroed-out `SummaryMetrics` with `sanctionedAmount` from data. [`calculations.ts#L236-L254`](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L236-L254)

### Row Classification

| Variable | Definition | Citation |
|---|---|---|
| `todayStr` | `formatDateOnly(todayDate \|\| new Date())` | L257 |
| `nextRow` | First row where `dueDate ≥ todayStr`, or last row | L259 |
| `pastRows` | All rows where `dueDate < todayStr` | L260 |
| `thisYearRows` | Subset of `pastRows` in the current calendar year | L261 |

### Computed Fields

| Metric | Formula | Citation |
|---|---|---|
| `disbursedAmount` | `sum(disbursements[].amount)` | L263 |
| `interestPaidToDate` | `sum(pastRows[].interest)` | L264 |
| `principalPaidToDate` | `sum(pastRows[].principal)` | L265 |
| `totalInterestProjected` | `sum(schedule[].interest)` | L266 |
| `interestSavedTillNow` | `sum(pastRows[].baselineInterest - pastRows[].interest)` | L267 |
| `interestSavedThisYear` | `sum(thisYearRows[].baselineInterest - thisYearRows[].interest)` | L268 |
| `currentAnnualRate` | Last entry in `rateHistory` (by array order, not date) | L269 |
| `effectiveInterestRate` | `(currentAnnualRate × nextRow.effectivePrincipal / nextRow.openingBalance).toFixed(2)` if `openingBalance > 0`, else `currentAnnualRate` | L270-L272 |
| `projectedClosureDate` | `schedule[last].dueDate` | L289 |

### Projected EMI Logic

**VERIFIED** — [`calculations.ts#L274-L279`](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L274-L279)

```
projectedEmi = currentCommunicatedEmi  (default)

if policy.onPrepayment == "adjust_emi" AND nextRow.phase == "moratorium":
    projectedEmi = calculateEmi(nextRow.openingBalance, currentAnnualRate, totalTenure - moratoriumMonths)
else if nextRow.phase == "emi":
    projectedEmi = nextRow.installment
```

---

## 9. Auto-Deduct Payments

**VERIFIED** — [`calculations.ts#L305-L387`](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L305-L387)

```
autoDeductPayments(loanData, odData, todayStr) → { loanChanged: boolean, odChanged: boolean }
```

### Algorithm

```
while true:
    schedule = generateSchedule(loanData)

    for each row in schedule:
        if row.dueDate > todayStr:
            break  // future, stop scanning

        if NO paymentLog entry has dueDate == row.dueDate:
            // 1. Create paymentLog entry
            loanData.paymentLog.push({
                id:         random_id(),
                dueDate:    row.dueDate,
                type:       row.phase == "moratorium" ? "pre_emi_interest" : "emi",
                amountDue:  row.installment,
                amountPaid: row.installment,
                paidDate:   row.dueDate,
            })
            loanChanged = true

            // 2. Update OD Balance dynamically so next schedule generation loop iteration is correct
            syncOdBalanceLog(loanData, odData)
            odChanged = true

            found = true
            break  // regenerate schedule after each deduction

    if not found:
        break  // all past due dates have payments
```

### Key Properties

1. **Schedule regeneration per deduction:** Each deduction changes the interest for subsequent periods, so the schedule is fully regenerated after each one. This is O(n²) in the number of unpaid periods. [`calculations.ts#L316-L317`](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L316-L317)

2. **In-place mutation:** Both `loanData` and `odData` are modified directly — no copies. [`calculations.ts#L305-L308`](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L305-L308)

3. **OD balance auto-snapshot formula:** Handled centrally by `syncOdBalanceLog`, which sums contributions and subtracts auto-deducted payments chronologically.

4. **ID generation:** `Math.random().toString(36).slice(2, 11)` — 9-character alphanumeric, non-cryptographic. [`calculations.ts#L332`](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L332)

---

## 10. Rounding Inventory

Six `Math.round()` calls exist in the codebase. All are in [`calculations.ts`](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts).

| ID | Line | Context | Expression | Result via round() |
|---|---|---|---|---|
| **R1** | [L34](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L34) | `calculateEmi` return value | `round()` of floating-point EMI from formula | Integer EMI |
| **R2** | [L147](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L147) | `interestPaid` initial assignment | `round()` of accumulated daily interest (float) | Integer interest for the period |
| **R3** | [L148](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L148) | `baselineInterest` initial assignment | `round()` of accumulated daily baseline interest (float) | Integer baseline interest for the period |
| **R4** | [L191](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L191) | Final-period installment (EMI phase, loan closure) | `round()` of `outstandingPrincipal + interestPaid` | Integer final installment |
| **R5** | [L213](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L213) | `openingBalance` in schedule row | `round()` of `outstandingPrincipal + principalPaid` (EMI) or `outstandingPrincipal` (moratorium) | Integer opening balance |
| **R6** | [L219](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L219) | `closingBalance` in schedule row | `round()` of `outstandingPrincipal` after payments | Integer closing balance |

### Additional Rounding

| ID | Line | Context | Method | Note |
|---|---|---|---|---|
| **C1** | [L51](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L51) | `calculateTenure` return | `Math.ceil(tenure)` | Rounds **up** to ensure the loan is fully paid — not `Math.round()` |
| **C2** | [L271](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L271) | `effectiveInterestRate` | `.toFixed(2)` then `Number()` | Rounds to 2 decimal places |

### Rounding Not Applied

- `interestAccrued` / `baselineInterestAccrued`: accumulated as raw floats during the daily loop — only rounded when assigned to `interestPaid` / `baselineInterest` at period end.
- `outstandingPrincipal`: tracked as a float throughout — only rounded when stored in `openingBalance` / `closingBalance` on the row.
- `principalPaid`: computed as `installment - interestPaid` — derived from already-rounded values, so it is inherently integer when inputs are integer.

---

## 11. Interest Savings Formulas

### Per-Period Savings (Standard)

**VERIFIED** — [`calculations.ts#L149`](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L149)

```
interestSavings = max(0, round(baselineInterestAccrued) - round(interestAccrued))
                = max(0, baselineInterest - interestPaid)
```

Note: `max(0, ...)` ensures savings are never negative (could happen due to rounding).

### Per-Period Savings (Historical Override)

**VERIFIED** — [`calculations.ts#L160`](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L160)

```
interestSavings = max(0, loggedPayment.amountDue - loggedPayment.amountPaid)
```

Falls back to `0` if `amountDue ≤ 0`.

### Aggregate Savings (Metrics)

**VERIFIED** — [`calculations.ts#L267-L268`](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L267-L268)

```
interestSavedTillNow  = sum(pastRows[i].baselineInterest - pastRows[i].interest)
interestSavedThisYear = sum(thisYearRows[i].baselineInterest - thisYearRows[i].interest)
```

**Note:** These sums use `baselineInterest - interest` (not `interestSavings`), meaning they can go negative for individual periods. This is a subtle difference from the per-row `interestSavings` which is clamped at 0. **INFERRED** — potential minor discrepancy between row-level and aggregate-level savings figures.

---

## 12. Invariants & Constraints

| # | Invariant | Evidence |
|---|---|---|
| I1 | `outstandingPrincipal` is never intentionally set below 0 — all subtractions use `max(0, ...)` | VERIFIED — [L126](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L126), [L180](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L180), [L196](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L196) |
| I2 | `effectivePrincipal` ≥ 0 — clamped by `max(0, outstanding - odBalance)` | VERIFIED — [L126](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L126), [L221](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L221) |
| I3 | `interestSavings` ≥ 0 — clamped by `max(0, ...)` | VERIFIED — [L149](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L149), [L160](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L160), [L173](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L173) |
| I4 | Schedule terminates in at most 601 periods (safety break at `period > 600`) | VERIFIED — [L226](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L226) |
| I5 | Moratorium phase: `principalPaid = 0` always (interest-only payments) | VERIFIED — [L162](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L162), [L167](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L167), [L176](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L176), [L185](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L185) |
| I6 | `closingBalance` = `round(outstandingPrincipal)` after all deductions for the period | VERIFIED — [L219](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L219) |
| I7 | Disbursements and prepayments are applied on their exact date, within the daily loop, before that day's interest | VERIFIED — [L113-L120](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L113-L120) |
| I8 | Rate and OD balance lookups use `≤` comparison — the value on the exact date is included | VERIFIED — [L87](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L87), [L96](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L96) |
| I9 | `calculateTenure` returns `Infinity` when EMI ≤ interest-only amount (loan can never close) | VERIFIED — [L45-L47](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L45-L47) |
| I10 | `onDisbursementDuringEmi` policy field exists in schema but is **unused** in `generateSchedule` | VERIFIED — [`types.ts#L52`](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/types.ts#L52), no reference in calculations |
| I11 | `RateHistory.spread` field exists in schema but is **unused** in calculations | VERIFIED — [`types.ts#L15`](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/types.ts#L15), no reference in calculations |
| I12 | Prepayments reduce `outstandingPrincipal` inline during the daily loop — they do NOT create a separate schedule row | VERIFIED — [L117-L120](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L117-L120) |
| I13 | `todayDate` parameter on `generateSchedule` is accepted but **not used** inside the function (it is used in `calculateMetrics`) | VERIFIED — [L59-L60](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L59-L60), `eslint-disable-next-line @typescript-eslint/no-unused-vars` |
