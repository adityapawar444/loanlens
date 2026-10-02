# LoanLens Codebase Audit — Reference Document

**Produced:** 2026-08-05  
**Purpose:** Ground-truth reference for porting LoanLens calculation logic to a standalone Python engine and redesigning the data model for a Google Drive–backed, conversational version.

---

## 1. Exact Data Schemas

### 1.1 `loan_data.json` — Zod Schema

From [types.ts](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/types.ts):

```typescript
export const DisbursementSchema = z.object({
  id: z.string(),
  date: z.string(),
  amount: z.number(),
  note: z.string().optional(),
});

export const RateHistorySchema = z.object({
  id: z.string(),
  effectiveDate: z.string(),
  annualRate: z.number(),
  benchmark: z.string().optional(),
  spread: z.number().optional(),
});

export const OdBalanceLogSchema = z.object({
  id: z.string(),
  date: z.string(),
  balance: z.number(),
});

export const PrepaymentSchema = z.object({
  id: z.string(),
  date: z.string(),
  amount: z.number(),
  note: z.string().optional(),
});

export const PaymentLogSchema = z.object({
  id: z.string(),
  dueDate: z.string(),
  type: z.enum(["pre_emi_interest", "emi"]),
  amountDue: z.number(),
  amountPaid: z.number(),
  paidDate: z.string(),
});

export const LoanDetailsSchema = z.object({
  lender: z.string(),
  accountNumber: z.string(),
  sanctionedAmount: z.number(),
  totalTenureMonths: z.number(),
  moratoriumMonths: z.number(),
  moratoriumAnchor: z.enum(["first_disbursement", "account_opening"]),
  dueDateDay: z.number(),
  dayCountConvention: z.number().default(365),
  currentCommunicatedEmi: z.number(),
  policy: z.object({
    onRateChange: z.enum(["adjust_tenure", "adjust_emi"]),
    onDisbursementDuringEmi: z.enum(["adjust_tenure", "adjust_emi"]),
    onPrepayment: z.enum(["adjust_tenure", "adjust_emi"]),
  }),
});

export const LoanDataSchema = z.object({
  loanDetails: LoanDetailsSchema,
  disbursements: z.array(DisbursementSchema),
  rateHistory: z.array(RateHistorySchema),
  odBalanceLog: z.array(OdBalanceLogSchema),
  prepayments: z.array(PrepaymentSchema),
  paymentLog: z.array(PaymentLogSchema),
});
```

**Representative excerpt of `loan_data.json`:**

```json
{
  "loanDetails": {
    "lender": "Bank of Baroda",
    "accountNumber": "83990600004041",
    "sanctionedAmount": 11965000,
    "totalTenureMonths": 300,
    "moratoriumMonths": 18,
    "moratoriumAnchor": "first_disbursement",
    "dueDateDay": 10,
    "dayCountConvention": 365,
    "currentCommunicatedEmi": 91143,
    "policy": {
      "onRateChange": "adjust_tenure",
      "onDisbursementDuringEmi": "adjust_tenure",
      "onPrepayment": "adjust_tenure"
    }
  },
  "disbursements": [
    { "id": "init-1", "date": "2026-01-31", "amount": 5982984, "note": "1st tranche" },
    { "id": "init-2", "date": "2026-06-02", "amount": 438152, "note": "2nd tranche" },
    { "id": "21ig6mkpq", "date": "2026-07-03", "amount": 664775, "note": "20th Floor" }
  ],
  "rateHistory": [
    { "id": "rate-1", "effectiveDate": "2026-01-31", "annualRate": 7.6, "benchmark": "RLLR" }
  ],
  "odBalanceLog": [
    { "id": "od-1", "date": "2026-06-10", "balance": 510792 },
    { "id": "0a5llq1qb", "date": "2026-08-02", "balance": 906043 }
  ],
  "prepayments": [],
  "paymentLog": [
    {
      "id": "p-1", "dueDate": "2026-02-10", "type": "pre_emi_interest",
      "amountDue": 13691, "amountPaid": 13656, "paidDate": "2026-02-10"
    }
  ]
}
```

### 1.2 `od_savings_data.json` — Zod Schema

From [od-savings-types.ts](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/od-savings-types.ts):

```typescript
export const AuditRecordSchema = z.object({
  timestamp: z.string(),
  field: z.string(),
  oldValue: z.string(),
  newValue: z.string(),
});

export const OdSourceSchema = z.object({
  id: z.string(),
  name: z.string().min(1).max(60),
  description: z.string().max(200).optional(),
  isActive: z.boolean().default(true),
  createdAt: z.string(),
  editHistory: z.array(AuditRecordSchema).default([]),
});

export const OdGoalSchema = z.object({
  id: z.string(),
  name: z.string().min(1).max(80),
  targetAmount: PositiveMoneySchema,
  allocatedAmount: NonNegativeMoneySchema.default(0),
  targetDate: z.string().optional(),
  color: z.string().default("#0f766e"),
  note: z.string().max(300).optional(),
  isActive: z.boolean().default(true),
  editHistory: z.array(AuditRecordSchema).default([]),
});

export const OdContributionSchema = z.object({
  id: z.string(),
  date: z.string().min(1),
  amount: PositiveMoneySchema,
  sourceId: z.string().min(1),
  note: z.string().max(300).optional(),
  editHistory: z.array(AuditRecordSchema).default([]),
});

export const OdBalanceAnnotationSchema = z.object({
  odBalanceLogId: z.string(),
  sourceId: z.string().nullable().default(null),
  purpose: z.string().default("savings"),
  note: z.string().max(300).optional(),
  editHistory: z.array(AuditRecordSchema).default([]),
});

export const OdSavingsDataSchema = z.object({
  emiReserve: z.number().min(0).default(91143),
  sources: z.array(OdSourceSchema).default([]),
  contributions: z.array(OdContributionSchema).default([]),
  goals: z.array(OdGoalSchema).default([]),
  odBalanceAnnotations: z.array(OdBalanceAnnotationSchema).default([]),
});
```

**Money validation helpers** (applied to amounts/balances):

```typescript
export const PositiveMoneySchema = z
  .number()
  .positive("Amount must be greater than zero")
  .max(100_000_000, "Amount cannot exceed ₹10 Crore")
  .refine(
    (v) => Math.round(v * 100) === v * 100,
    "Amount can have at most 2 decimal places"
  );

export const NonNegativeMoneySchema = z
  .number()
  .min(0, "Balance cannot be negative")
  .max(100_000_000, "Balance cannot exceed ₹10 Crore")
  .refine(
    (v) => Math.round(v * 100) === v * 100,
    "Balance can have at most 2 decimal places"
  );
```

**Representative excerpt of `od_savings_data.json`:**

```json
{
  "emiReserve": 91143,
  "sources": [
    { "id": "mhk74l284", "name": "Aditya", "description": "From Salary",
      "isActive": true, "createdAt": "2026-07-08T09:03:36.884Z", "editHistory": [] }
  ],
  "contributions": [
    { "id": "yyy2fwjqv", "date": "2026-05-30", "amount": 198000,
      "sourceId": "31q8x1ylm", "editHistory": [] }
  ],
  "goals": [
    { "id": "4hsdm8lou", "name": "Shravi Future Investments", "targetAmount": 60000,
      "allocatedAmount": 60000, "targetDate": "2026-07-30", "color": "#0f766e",
      "isActive": true,
      "editHistory": [
        { "timestamp": "2026-07-08T09:21:43.847Z", "field": "allocatedAmount",
          "oldValue": "0", "newValue": "60000" }
      ] }
  ],
  "odBalanceAnnotations": [
    { "odBalanceLogId": "la8jgbv9p", "sourceId": null, "purpose": "savings",
      "editHistory": [ /* ... */ ] }
  ]
}
```

---

## 2. Stored vs. Derived

> [!IMPORTANT]
> This section is the most critical for the Python port. Every dashboard value is traced to its origin.

| Dashboard Value | Stored or Derived? | Source/Function |
|---|---|---|
| **Outstanding Principal** | **Derived** at request time | [calculateMetrics](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L234) reads `nextRow.openingBalance` from the schedule. The schedule itself derives it via day-by-day simulation in [generateSchedule](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L59). |
| **Effective Principal** | **Derived** | `max(0, outstandingPrincipal - odBalance)` — computed per-day inside `generateSchedule` (L125) and also in `calculateMetrics` via `nextRow.effectivePrincipal` (L282). |
| **OD Balance** (latest) | **Stored** in `loan_data.json → odBalanceLog[]` | The OD Savings Client reads latest via: `[...loanData.odBalanceLog].sort((a, b) => b.date.localeCompare(a.date))[0].balance` |
| **Next EMI / Next Installment** | **Derived** | `calculateMetrics`: `nextRow.installment` where `nextRow = schedule.find(row => row.dueDate >= todayStr)` (L258). |
| **Next Due Date** | **Derived** | Same as above — `nextRow.dueDate` (L285). |
| **Interest / Principal Split** | **Derived** per row | Each `AmortizationRow` has `interest` and `principal` fields, computed daily inside `generateSchedule`. |
| **Interest Paid To Date** | **Derived** | `pastRows.reduce((sum, row) => sum + row.interest, 0)` in `calculateMetrics` (L263). |
| **Principal Paid To Date** | **Derived** | `pastRows.reduce((sum, row) => sum + row.principal, 0)` in `calculateMetrics` (L264). |
| **Total Projected Interest** | **Derived** | `schedule.reduce((sum, row) => sum + row.interest, 0)` (L265). |
| **Interest Saved Till Now** | **Derived** | `pastRows.reduce((sum, row) => sum + (row.baselineInterest - row.interest), 0)` (L266). |
| **Interest Saved This Year** | **Derived** | Same formula but filtered to rows where `dueDate.year === currentYear` (L267). |
| **Effective Interest Rate** | **Derived** | `(currentAnnualRate * nextRow.effectivePrincipal) / nextRow.openingBalance` (L269-270). |
| **Projected EMI** | **Derived** | Uses `currentCommunicatedEmi` or `nextRow.installment` depending on phase (L273-278). |
| **Projected Closure Date** | **Derived** | `schedule[schedule.length - 1].dueDate` (L288). |
| **Disbursed Amount** | **Derived** | `data.disbursements.reduce((sum, d) => sum + d.amount, 0)` (L262). |
| **EMI Reserve** | **Stored** | `od_savings_data.json → emiReserve` field. |
| **Total Deposited (OD contributions)** | **Derived** | `odData.contributions.reduce((s, c) => s + c.amount, 0)` in OdSavingsClient (L149). |
| **Allocatable Balance** | **Derived** | `Math.max(0, latestOdBalance - emiReserve)` (OdSavingsClient L194). |
| **Total Allocated To Goals** | **Derived** | `odData.goals.reduce((sum, g) => sum + g.allocatedAmount, 0)` (L199). But each goal's `allocatedAmount` is **stored** in the JSON. |
| **Free Allocatable** | **Derived** | `allocatableBalance - totalAllocatedToGoals` (L203). |
| **Over-allocation flags** | **Derived** | `isOverAllocated = totalAllocatedToGoals > allocatableBalance + 0.001` (L204). `isCriticalOverAllocation = totalAllocatedToGoals > latestOdBalance + 0.001` (L205). |
| **Per-goal allocated amount** | **Stored** | `OdGoal.allocatedAmount` in `od_savings_data.json`. Updated via `editGoal` server action. |
| **MoM OD Balance Trend** | **Derived** from stored snapshots | See Section 8. |
| **By-source contribution breakdown** | **Derived** | Aggregated in OdSavingsClient from `contributions[]` grouped by `sourceId` (L177-186). |
| **Payment status (Paid/Due needed)** | **Derived** at render time | Ledger page checks `HISTORICAL_PAYMENT_DATES.has(payment.dueDate)` and `payment.amountDue === payment.amountPaid`. |
| **Days-until-due countdown** | **Derived** | `DashboardClient` L288-294: date arithmetic on `metrics.nextDueDate` vs `todayStr`. |
| **Health status badge** | **Derived** | `calculateHealthStatus()` in DashboardClient L1215-1289 — composite score from OD ratio, savings ratio, principal ratio, rate ratio. |

### Summary

**Stored facts (what must be persisted):**
- `loanDetails` (static config)
- `disbursements[]` (append-only log)
- `rateHistory[]` (append-only log)
- `odBalanceLog[]` (append-only snapshot log)
- `prepayments[]` (append-only log)
- `paymentLog[]` (amountDue and amountPaid — manually edited)
- `emiReserve` (single number)
- `sources[]` (name/description/active status)
- `contributions[]` (date/amount/sourceId)
- `goals[]` (name/target/allocatedAmount/color/dates)
- `odBalanceAnnotations[]` (links OD log entries to sources)

**Everything else is computed from these at render time.**

---

## 3. EMI / Amortisation Formula

### 3.1 EMI Calculation

From [calculations.ts L28-34](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L28-L34):

```typescript
export function calculateEmi(principal: number, annualRate: number, tenureMonths: number): number {
  if (tenureMonths <= 0) return 0;
  const r = annualRate / 12 / 100;
  if (r === 0) return principal / tenureMonths;
  const emi = (principal * r * Math.pow(1 + r, tenureMonths)) / (Math.pow(1 + r, tenureMonths) - 1);
  return Math.round(emi);
}
```

### 3.2 Tenure Calculation (inverse)

From [calculations.ts L39-51](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L39-L51):

```typescript
export function calculateTenure(principal: number, annualRate: number, emi: number): number {
  if (principal <= 0) return 0;
  const r = annualRate / 12 / 100;
  if (r === 0) return principal / emi;
  
  if (emi <= principal * r) {
    return Infinity;
  }
  
  const x = emi / (emi - principal * r);
  const tenure = Math.log(x) / Math.log(1 + r);
  return Math.ceil(tenure);
}
```

### 3.3 Schedule Generation (full amortisation engine)

From [generateSchedule — calculations.ts L59-231](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/lib/calculations.ts#L59-L231):

**Key architectural choices:**

1. **Day-by-day interest accrual**: The engine iterates day-by-day between due dates. It does NOT use monthly simplifications.

2. **Date handling**: Uses **system local time** via `new Date(year, month-1, day)`. Date strings are `YYYY-MM-DD` parsed via `split("-").map(Number)` into a local Date.

3. **Day-count convention**: Always 365. The field `dayCountConvention` exists in the schema but is hardcoded to `365` in the current data.

4. **Money representation**: **Floating-point rupees** throughout. Not integer paise. Rounding to nearest integer rupee happens via `Math.round()` at specific points.

**The core interest loop (per billing period):**

```typescript
while (tempDate < nextDueDate) {
  const tempDateKey = formatDateOnly(tempDate);

  // Apply disbursements on this exact date
  while (dIdx < sortedDisbursements.length && sortedDisbursements[dIdx].date === tempDateKey) {
    outstandingPrincipal += sortedDisbursements[dIdx].amount;
    dIdx++;
  }
  // Apply prepayments on this exact date
  while (pIdx < sortedPrepayments.length && sortedPrepayments[pIdx].date === tempDateKey) {
    outstandingPrincipal -= sortedPrepayments[pIdx].amount;
    pIdx++;
  }

  const dailyRate = getRateAt(tempDateKey) / 100 / loanDetails.dayCountConvention;
  
  // OD offset: interest is charged on effective principal
  const odBalance = getOdBalanceAt(tempDateKey);
  const effectivePrincipal = Math.max(0, outstandingPrincipal - odBalance);
  
  interestAccrued += effectivePrincipal * dailyRate;
  baselineInterestAccrued += outstandingPrincipal * dailyRate;
  
  tempDate.setDate(tempDate.getDate() + 1);
}
```

**OD offset definition:**
```
effectivePrincipal = max(0, outstandingPrincipal - odBalance)
```
Where `odBalance` is the most recent `odBalanceLog` entry with `date <= currentDate` (step-function / constant until next snapshot).

**Rounding rules:**
- `interestPaid = Math.round(interestAccrued)` — rounded to nearest rupee
- `baselineInterest = Math.round(baselineInterestAccrued)` — rounded to nearest rupee
- `interestSavings = Math.max(0, baselineInterest - interestPaid)` — floored at 0
- EMI: `Math.round(emi)` — in `calculateEmi()`
- Closing balance: `Math.round(outstandingPrincipal)`
- Opening balance: `Math.round(outstandingPrincipal + principalPaid)` for EMI phase

**Historical payment override (HISTORICAL_PAYMENT_DATES):**

For the hardcoded set `{"2026-02-10", "2026-03-10", "2026-04-10", "2026-05-10", "2026-06-10"}`:

```typescript
if (HISTORICAL_PAYMENT_DATES.has(dateKey)) {
  const loggedPayment = data.paymentLog.find(p => p.dueDate === dateKey);
  if (loggedPayment) {
    interestPaid = loggedPayment.amountPaid;
    baselineInterest = loggedPayment.amountDue > 0 ? loggedPayment.amountDue : interestPaid;
    interestSavings = Math.max(0, baselineInterest - interestPaid);
    installment = interestPaid;
    principalPaid = 0;
  }
}
```

For these months, the **bank's actual charge** (`amountPaid`) replaces the computed interest, and `amountDue` is used as the baseline for savings calculation.

**Moratorium → EMI transition:**

```typescript
if (phase === "moratorium" && period > loanDetails.moratoriumMonths) {
  phase = "emi";
  currentEmi = loanDetails.currentCommunicatedEmi;
  if (loanDetails.policy.onPrepayment === "adjust_tenure") {
    remainingTenure = calculateTenure(outstandingPrincipal, getRateAt(dateKey), currentEmi);
  } else {
    remainingTenure = loanDetails.totalTenureMonths - loanDetails.moratoriumMonths;
    currentEmi = calculateEmi(outstandingPrincipal, getRateAt(dateKey), remainingTenure);
  }
}
```

> [!NOTE]
> The moratorium check is `period > moratoriumMonths`, meaning: if `moratoriumMonths = 18`, the moratorium covers periods 1–18, and EMI begins at period 19. The **transition to EMI uses `currentCommunicatedEmi`** (the bank's stated figure) when policy is `adjust_tenure`, NOT a freshly computed EMI from the outstanding balance.

### 3.4 Timezone / Date Anchor

- **Dates are parsed as local time**: `new Date(year, month-1, day)` creates a midnight-local Date.
- The `todayDate` parameter (optional) is used only for `calculateMetrics`, not for `generateSchedule`.
- There is **no explicit timezone conversion** — the system runs in whatever TZ the Node.js server uses.
- For the dashboard pages, `todayStr` is generated via `new Date().toISOString().split("T")[0]` (UTC date string) on the server, but then re-parsed as local time in the client via `new Date(date.getFullYear(), date.getMonth(), date.getDate())`.

---

## 4. OD Waterfall / Reserve Logic

### 4.1 Waterfall Allocation Order

The waterfall is computed **entirely on the client side** in [OdSavingsClient.tsx](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/app/(dashboard)/od-savings/OdSavingsClient.tsx):

```
OD Balance (latest snapshot from odBalanceLog)
  └─ EMI Reserve (emiReserve field, default ₹91,143) → PROTECTED
     └─ Allocatable Balance = max(0, latestOdBalance - emiReserve)
        └─ Goal Allocations (sum of all goals' allocatedAmount)
           └─ Free Allocatable = allocatableBalance - totalAllocatedToGoals
```

**Exact code:**

```typescript
const emiReserve = odData.emiReserve;

const allocatableBalance = useMemo(
  () => Math.max(0, latestOdBalance - emiReserve),
  [latestOdBalance, emiReserve]
);

const totalAllocatedToGoals = useMemo(
  () => odData.goals.reduce((sum, g) => sum + g.allocatedAmount, 0),
  [odData.goals]
);

const freeAllocatable = allocatableBalance - totalAllocatedToGoals;
const isOverAllocated = totalAllocatedToGoals > allocatableBalance + 0.001;
const isCriticalOverAllocation = totalAllocatedToGoals > latestOdBalance + 0.001;
```

### 4.2 Reserve Encroachment Detection

> [!WARNING]
> The amber/red banners are **purely UI warnings**. There is **no server-side enforcement** preventing over-allocation past the reserve.

**Two severity levels:**

1. **Amber warning** (`isOverAllocated`): When `totalAllocatedToGoals > allocatableBalance`. Meaning: goal allocations exceed OD minus reserve, but are still within the total OD balance. The message reads: *"This encroaches on the EMI reserve by {amount}. Review your goal allocations."*

2. **Red/critical warning** (`isCriticalOverAllocation`): When `totalAllocatedToGoals > latestOdBalance`. Meaning: goal allocations exceed the entire OD balance. The message reads: *"including the EMI reserve. The EMI buffer is fully consumed — the next EMI may not be covered."*

**Neither is enforced**: The `editGoal` server action validates only that `allocatedAmount` passes `NonNegativeMoneySchema` (≥ 0, ≤ ₹10 Cr, at most 2 decimals). It does **not** check against the reserve or OD balance.

### 4.3 Goal Status Logic

Goals have no explicit `status` field. Status is **derived from stored fields**:

| Status | Condition | Code |
|---|---|---|
| **Active** | `goal.isActive === true` and `allocatedAmount < targetAmount` | Filtered via `odData.goals.filter(g => g.isActive)` |
| **Funded** / **Met** | `goal.allocatedAmount >= goal.targetAmount` | Checked inline in the UI rendering. There is no stored "funded" or "met" flag — it's a comparison rendered at display time. |
| **Inactive** | `goal.isActive === false` | Toggled via `editGoal(id, { isActive: false })` |

The **Goals Summary strip** in the UI counts Active/Met/Funded:
- Met count = goals where `allocatedAmount >= targetAmount`
- The terms "Funded" and "Met" are used interchangeably in the UI

---

## 5. Prepayment Simulator Logic

### 5.1 Architecture: Pure Read-Only Projection

The simulator is implemented in [SimulatorClient.tsx](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/app/(dashboard)/simulator/SimulatorClient.tsx) as a **client-side-only, read-only projection**. It:

1. Deep-clones the base loan data: `JSON.parse(JSON.stringify(baseData))`
2. Appends hypothetical changes to the clone
3. Runs `generateSchedule()` and `calculateMetrics()` on both base and simulated data
4. Displays the diff

**It never calls any server action and never writes to disk.**

### 5.2 Exact Formula

The simulator reuses the **exact same** `generateSchedule` and `calculateMetrics` functions as the real dashboard. There is no separate simulation engine.

```typescript
const simulatedData = useMemo(() => {
  const data: LoanData = JSON.parse(JSON.stringify(baseData));
  changes.forEach((change) => {
    if (change.type === "prepayment") data.prepayments.push(change.data);
    if (change.type === "rate") data.rateHistory.push(change.data);
    if (change.type === "od") data.odBalanceLog.push(change.data);
  });
  return data;
}, [baseData, changes]);

const baseSchedule = useMemo(() => generateSchedule(baseData, today), [baseData, today]);
const baseMetrics = useMemo(() => calculateMetrics(baseData, baseSchedule, today), [...]);
const simSchedule = useMemo(() => generateSchedule(simulatedData, today), [simulatedData, today]);
const simMetrics = useMemo(() => calculateMetrics(simulatedData, simSchedule, today), [...]);
```

### 5.3 Diff Metrics Displayed

```typescript
const interestSaved = baseMetrics.totalInterestProjected - simMetrics.totalInterestProjected;
const closureShift = baseSchedule.length - simSchedule.length; // months
```

Displayed comparisons:
- Total Interest Payable (base vs. sim)
- Loan Tenure in months (base vs. sim)
- Projected EMI (base vs. sim)
- New projected closure date
- Tenure movement (months earlier/later)

### 5.4 Supported Scenario Change Types

```typescript
type ScenarioChange =
  | { type: "prepayment"; data: Prepayment }     // lump-sum
  | { type: "rate"; data: RateHistory }           // rate change
  | { type: "od"; data: OdBalanceLog };           // OD balance adjustment
```

Multiple changes can be combined in a single scenario. Changes are applied in array order (pushed to the respective arrays in the cloned data).

> [!NOTE]
> There is no "Apply to actuals" button. The plan document described one, but the code **does not implement** saving simulator scenarios to disk. The `DisbursementDuringEMI` scenario type from the plan is also **not implemented** in the simulator UI — only Prepayment, Rate, and OD Balance changes are available.

---

## 6. Server Action Wiring

### 6.1 Mutation Map

| Mutation | Server Action | Zod Validation | Writes To | Audit Trail? |
|---|---|---|---|---|
| **Add disbursement** | `addDisbursement()` | Manual: `amount > 0`, `amount ≤ 10Cr`, `date` required. **Not** via Zod parse — inline checks. | `loan_data.json → disbursements[]` | ❌ No |
| **Add OD balance log** | `addOdBalanceLog()` | Manual: `balance ≥ 0`, `≤ 10Cr`, not NaN, date required | `loan_data.json → odBalanceLog[]` | ❌ No |
| **Add rate history** | `addRateHistory()` | **No validation at all** — directly pushes to array | `loan_data.json → rateHistory[]` | ❌ No |
| **Update payment (amount paid)** | `updatePayment(id, amountPaid)` | Manual: `> 0`, `≤ 10Cr` | `loan_data.json → paymentLog[].amountPaid` | ❌ No |
| **Update amount due** | `updateAmountDue(id, amountDue)` | Manual: `≥ 0`, `≤ 10Cr`, not NaN | `loan_data.json → paymentLog[].amountDue` | ❌ No |
| **Update loan details** | `updateLoanDetails(formData)` | **No validation** — raw `Number(formData.get(...))` | `loan_data.json → loanDetails` | ❌ No |
| **Update EMI reserve** | `updateEmiReserve(amount)` | Manual: `≥ 0`, `≤ 10Cr`, 2 decimal check | `od_savings_data.json → emiReserve` | ❌ No |
| **Add source** | `addSource(source)` | Duplicate name check (case-insensitive) | `od_savings_data.json → sources[]` | ❌ Created with `editHistory: []` |
| **Edit source** | `editSource(id, patch)` | Duplicate name check | `od_savings_data.json → sources[].{name,description,isActive}` | ✅ `diffAudit()` records field changes |
| **Add goal** | `addGoal(goal)` | `PositiveMoneySchema.safeParse(targetAmount)` | `od_savings_data.json → goals[]` | ❌ Created with `editHistory: []` |
| **Edit goal** | `editGoal(id, patch)` | `PositiveMoneySchema` on `targetAmount`, `NonNegativeMoneySchema` on `allocatedAmount` | `od_savings_data.json → goals[].{...}` | ✅ `diffAudit()` records |
| **Add contribution** | `addContribution(contribution)` | `PositiveMoneySchema.safeParse(amount)` | `od_savings_data.json → contributions[]` | ❌ Created with `editHistory: []` |
| **Edit contribution** | `editContribution(id, patch)` | `PositiveMoneySchema` on `amount` | `od_savings_data.json → contributions[].{...}` | ✅ `diffAudit()` records |
| **Add OD balance with annotation** | `addOdBalanceWithAnnotation(entry, annotation)` | `NonNegativeMoneySchema` on balance, date required | **Both files**: `loan_data.json → odBalanceLog[]` AND `od_savings_data.json → odBalanceAnnotations[]` | ❌ Created with `editHistory: []` |
| **Edit OD balance annotation** | `editOdBalanceAnnotation(id, patch)` | None on patch values | `od_savings_data.json → odBalanceAnnotations[].{sourceId,purpose,note}` | ✅ `diffAudit()` records |

### 6.2 Audit Trail Shape

```typescript
function makeAudit(field: string, oldValue: unknown, newValue: unknown): AuditRecord {
  return {
    timestamp: new Date().toISOString(),
    field,
    oldValue: JSON.stringify(oldValue ?? null),
    newValue: JSON.stringify(newValue ?? null),
  };
}
```

Resulting record shape:
```json
{
  "timestamp": "2026-07-08T09:21:43.847Z",
  "field": "allocatedAmount",
  "oldValue": "0",
  "newValue": "60000"
}
```

Values are JSON-stringified (so strings get double-quoted: `"\"#0f766e\""`).

### 6.3 Invalid Input Handling

- **loan_data actions** (`addDisbursement`, `addOdBalanceLog`, `updatePayment`, `updateAmountDue`): **throw Error** on invalid input. No try/catch in the form handlers — errors propagate to the Next.js error boundary.
- **od-savings actions**: Return `{ success: false, error: "..." }` — the UI displays errors inline.
- **No validation for past dates, duplicate dates, or already-closed months**. You can add a disbursement in the past, edit a payment for any month, or log an OD balance for any date. There are no temporal guards.
- **No over-allocation enforcement**: You can allocate more to goals than the OD balance allows. See Section 4.2.

### 6.4 Write Path

All writes follow the same pattern:
1. `readData()` / `readOdData()` — reads JSON file, parses through Zod
2. Mutate the in-memory object
3. `writeData()` / `writeOdData()` — re-validates through Zod, writes back to JSON file with `JSON.stringify(data, null, 2)`
4. `revalidatePath("/")` or `revalidatePath("/od-savings")` — tells Next.js to re-fetch the page

> [!WARNING]
> There is no concurrency control. Two simultaneous writes could cause a lost update (read-modify-write race condition on the JSON file).

---

## 7. Current Period & Payment-Status Resolution

### 7.1 "Currently Due" Month

**Computed, not stored.** The "next due" row is determined by:

```typescript
// In calculateMetrics:
const todayStr = formatDateOnly(today);
const nextRow = schedule.find(row => row.dueDate >= todayStr) || schedule[schedule.length - 1];
```

This finds the first schedule row whose due date is today or in the future. `today` comes from `new Date()` on the server at render time.

### 7.2 Payment Status Badges

> [!IMPORTANT]
> **There are no Paid/Upcoming/Overdue badges in the current code.** The README mentions "Payment status badges (Paid / Upcoming / Overdue)" for the Amortisation Schedule page, but a grep for "Overdue" across the entire codebase returns **zero results**. The schedule table ([AmortizationTable.tsx](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/components/schedule/AmortizationTable.tsx)) renders only numeric columns — no status column exists.

The **Ledger page** does have a soft status indicator: rows in `HISTORICAL_PAYMENT_DATES` where `amountDue === amountPaid` get an amber "Due needed" tag, indicating the user hasn't yet entered the bank's actual charge. This is not a Paid/Overdue status — it's a data-completeness prompt.

### 7.3 Next-EMI Countdown

Computed in [DashboardClient.tsx L288-294](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/components/dashboard/DashboardClient.tsx#L288-L294):

```typescript
const daysUntilDue = useMemo(() => {
  if (!metrics.nextDueDate) return null;
  const [dy, dm, dd] = metrics.nextDueDate.split("-").map(Number);
  const due = new Date(dy, dm - 1, dd);
  const [ty, tm, td] = todayStr.split("-").map(Number);
  const today = new Date(ty, tm - 1, td);
  return Math.max(0, Math.round((due.getTime() - today.getTime()) / (1000 * 60 * 60 * 24)));
}, [metrics.nextDueDate, todayStr]);
```

Displayed as: *"X days until the next installment of ₹Y."*  
When `daysUntilDue <= 7`, the tone changes to "positive" (green highlight).

---

## 8. Historical Snapshots (MoM OD Balance Trend)

### 8.1 Is it a persisted time series?

**Partially.** The OD balance "trend" chart uses `loan_data.json → odBalanceLog[]` which is an **append-only log of manually entered snapshots**. Each entry is:

```json
{ "id": "od-1", "date": "2026-06-10", "balance": 510792 }
```

These are **not automatically generated** — the user manually logs them via the Ledger or OD Savings page. The chart is NOT a derived-on-demand reconstruction from contributions; it uses the actual stored snapshots.

### 8.2 Chart Data Construction

From [OdSavingsClient.tsx L224-250](file:///home/aditya/codebase/gemini-projects/home-loan-dashboard/src/app/(dashboard)/od-savings/OdSavingsClient.tsx#L224-L250):

```typescript
const momData = useMemo(() => {
  const monthMap = new Map<string, { balance: number | null; deposited: number }>();
  // Group OD balance log entries by month (YYYY-MM), take LAST entry per month
  for (const e of [...loanData.odBalanceLog].sort((a, b) =>
    a.date.localeCompare(b.date)
  )) {
    const mo = e.date.slice(0, 7);
    const ex = monthMap.get(mo) ?? { balance: null, deposited: 0 };
    monthMap.set(mo, { ...ex, balance: e.balance });
  }
  // Sum contributions per month
  for (const c of odData.contributions) {
    const mo = c.date.slice(0, 7);
    const ex = monthMap.get(mo) ?? { balance: null, deposited: 0 };
    monthMap.set(mo, { ...ex, deposited: ex.deposited + c.amount });
  }
  // Build cumulative deposited alongside monthly OD balance
  let cum = 0;
  return [...monthMap.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([mo, d]) => {
      cum += d.deposited;
      return {
        label: fmtMonthLabel(mo),
        odBalance: d.balance,      // last snapshot balance for that month
        deposited: d.deposited,     // total contributions for that month
        cumDeposited: cum,          // cumulative contributions to date
      };
    });
}, [loanData.odBalanceLog, odData.contributions]);
```

### 8.3 What Triggers a New Snapshot

A new snapshot is created when the user:
1. Clicks "Log OD Balance" on the Ledger page → calls `addOdBalanceLog()` → writes to `loan_data.json`
2. Or uses "Add OD Balance" on the OD Savings page → calls `addOdBalanceWithAnnotation()` → writes to both `loan_data.json` and `od_savings_data.json`

There is **no automatic snapshotting** — no cron job, no scheduled write, no trigger on contribution. The user must manually enter each snapshot.

---

## 9. Constants & Defaults

### 9.1 Current Hardcoded Values in `loan_data.json`

| Parameter | Current Value | Location |
|---|---|---|
| Lender | Bank of Baroda | `loanDetails.lender` |
| Account Number | 83990600004041 | `loanDetails.accountNumber` |
| Sanctioned Amount | ₹1,19,65,000 (11,965,000) | `loanDetails.sanctionedAmount` |
| Total Tenure | 300 months (25 years) | `loanDetails.totalTenureMonths` |
| Moratorium | 18 months | `loanDetails.moratoriumMonths` |
| Moratorium Anchor | `first_disbursement` | `loanDetails.moratoriumAnchor` |
| Due Date Day | 10th | `loanDetails.dueDateDay` |
| Day Count Convention | 365 | `loanDetails.dayCountConvention` |
| Communicated EMI | ₹91,143 | `loanDetails.currentCommunicatedEmi` |
| First Disbursement | 2026-01-31 (₹59,82,984) | `disbursements[0]` |
| Interest Rate | 7.6% annual (RLLR) | `rateHistory[0]` |

### 9.2 Constants in Code

```typescript
// calculations.ts L5-11 — Hardcoded historical payment dates
const HISTORICAL_PAYMENT_DATES: Set<string> = new Set([
  "2026-02-10", "2026-03-10", "2026-04-10", "2026-05-10", "2026-06-10",
]);

// calculations.ts L225 — Safety break
if (period > 600) break;  // Maximum 600 months (50 years)

// od-savings-types.ts L115 — Default EMI reserve
emiReserve: z.number().min(0).default(91143),

// Multiple places — Maximum monetary value
100_000_000  // ₹10 Crore cap on all monetary inputs

// od-savings-types.ts L51-60 — Goal color palette
const GOAL_COLOR_VALUES = [
  "#0f766e", "#2563eb", "#f59e0b", "#16a34a",
  "#e11d48", "#7c3aed", "#ea580c", "#0891b2",
];
```

### 9.3 Values That Should Become Configurable

- `HISTORICAL_PAYMENT_DATES` — currently hardcoded; should be derived from `paymentLog` entries with `type: "pre_emi_interest"`
- The 600-period safety break — probably fine as-is but should be documented
- The `moratoriumAnchor` is configurable (`first_disbursement` | `account_opening`) but currently only `first_disbursement` logic is effectively used
- `dayCountConvention` is stored but never checked for leap years (366)

---

## 10. Discrepancies from the README

### 10.1 Payment Status Badges — NOT IMPLEMENTED

README says: *"Payment status badges (Paid / Upcoming / Overdue)"*

**Reality:** No such badges exist anywhere in the codebase. The schedule table has no status column. The term "Overdue" does not appear anywhere in the source code.

### 10.2 CSV Export — NOT IMPLEMENTED

README says: *"Full loan schedule from disbursement to closure"* (implied CSV via the plan document).

**Reality:** No CSV export functionality exists.

### 10.3 "Apply Scenario to Actuals" — NOT IMPLEMENTED

The plan document (Section 5.9) describes an "Apply this scenario as actual" action that would write simulator changes to `loan_data.json`.

**Reality:** The simulator is purely client-side and read-only. There is no mechanism to persist scenario changes.

### 10.4 Saved/Named Scenarios — NOT IMPLEMENTED

The plan described saved scenarios for side-by-side comparison.

**Reality:** Scenarios exist only in React state and are lost on page navigation.

### 10.5 Side-by-Side Policy Comparison — NOT IMPLEMENTED

The plan described showing both `adjust_emi` and `adjust_tenure` outcomes simultaneously for the same change.

**Reality:** The simulator uses the saved policy from settings. There is no policy toggle in the simulator UI.

### 10.6 Audit Trail Coverage

README says: *"Every edit to sources, goals, and contributions is recorded with before/after diffs"*

**Reality:** Audit trail is wired for:
- ✅ Sources (via `editSource`)
- ✅ Goals (via `editGoal`)  
- ✅ Contributions (via `editContribution`)
- ✅ OD Balance Annotations (via `editOdBalanceAnnotation`)
- ❌ NOT for: Disbursements, rate history, payment log edits, loan details changes, EMI reserve changes

So the README claim is **correct for OD savings entities** but there is **no audit trail** for core loan data mutations.

### 10.7 `onDisbursementDuringEmi` Policy — Schema Only

The `policy.onDisbursementDuringEmi` field exists in the Zod schema and JSON but is:
- **Not exposed** in the Settings UI (only `onRateChange` and `onPrepayment` are editable)
- **Not used** in the calculation engine — the engine only checks `onPrepayment` policy

### 10.8 Rate Reset Frequency — NOT TRACKED

The plan mentioned tracking benchmark type, spread, and reset frequency. The schema has `benchmark` and `spread` as optional fields in `RateHistorySchema`, but:
- `spread` is never used in calculations
- There is no rate-reset-frequency field
- Rate changes are purely manual entries

### 10.9 Processing Fees / Total Cost — NOT IMPLEMENTED

Mentioned as optional in the plan. Not present in schema or code.

### 10.10 Disbursement New During EMI — NOT SPECIALLY HANDLED

In `generateSchedule`, new disbursements during the EMI phase simply increase `outstandingPrincipal` on the exact date. But the code does not trigger a recalculation of EMI/tenure at that point — it only recalculates tenure at the end of each billing period via `calculateTenure()` when `onPrepayment === "adjust_tenure"`. The `onDisbursementDuringEmi` policy is effectively ignored.
