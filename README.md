# 🏠 LoanLens — Home Loan Dashboard

A personal finance dashboard for tracking, analysing, and optimising a home loan under an **Overdraft (OD) account structure**. Built to provide full visibility into EMI payments, outstanding balance vs. effective balance, interest savings, and OD account utilisation — all from a single, beautiful interface.

---

## ✨ Features

### 📊 Dashboard
- **KPI summary strip** — Outstanding balance, effective OD balance, cumulative interest paid, total savings
- **Outstanding vs. Effective Balance** chart — 12-month view showing the gap your OD savings create
- **Interest vs. Principal split** chart — Monthly breakdown for the current year
- **OD Benefits over time** — Running total of interest saved by parking funds in the OD account
- **Next EMI countdown** with payment status

### 📅 Amortisation Schedule
- Full loan schedule from disbursement to closure
- Per-row editing of actual vs. expected EMI amounts
- Payment status badges (Paid / Upcoming / Overdue)

### 📒 Ledger
- Month-by-month payment history
- Editable **Expected Due** amounts for Feb–Jun 2026 (corrects OD-adjusted figures)
- Savings calculation: actual paid vs. expected due
- Running totals and balance history

### 💰 OD Savings Account
Complete tracking of money parked in the OD savings account:

- **Balance Waterfall** — OD balance → EMI Reserve (protected, default ₹91,143) → Allocatable Balance → Goal allocations
- **EMI Reserve** — Inline editable, always shown as protected; amber/red banners if allocations encroach on reserve
- **Goal tracking** — Add savings goals with target amounts, target dates, and colour coding
  - Goals Summary strip: Active / Met / Funded counts + progress bar across all goals
  - Per-goal progress bars with headroom indicator (room to allocate within reserve)
  - Direct **Fund** button on each goal card
- **Contribution log** — Track inflows by source (Salary, Bonus, etc.) for attribution
- **By Source donut chart** — Visual breakdown of contributions by funding source
- **MoM OD balance trend** — Area chart of OD balance snapshots alongside cumulative deposits
- **Audit trail** — Every edit to sources, goals, and contributions is recorded with before/after diffs

### ⚙️ Settings & Simulator
- Loan parameters (principal, rate, tenure, disbursement date)
- Prepayment simulator — Model the impact of lump-sum prepayments on tenure and interest

---

## 🗂️ Project Structure

```
src/
├── app/
│   ├── (dashboard)/
│   │   ├── ledger/          # Payment history & savings ledger
│   │   ├── od-savings/      # OD savings account tracker
│   │   ├── schedule/        # Amortisation schedule
│   │   ├── settings/        # Loan settings
│   │   └── simulator/       # Prepayment simulator
│   ├── layout.tsx
│   └── page.tsx             # Redirects to dashboard
├── components/
│   └── NavigationDrawer.tsx # Side navigation
└── lib/
    ├── actions.ts            # Server actions — loan data mutations
    ├── data-layer.ts         # JSON file read/write for loan data
    ├── od-savings-actions.ts # Server actions — OD savings mutations
    ├── od-savings-data-layer.ts
    ├── od-savings-types.ts   # Zod schemas and TypeScript types
    └── types.ts              # Core loan data types
data/
    ├── loan_data.json        # Loan data store (gitignored — personal)
    └── od_savings_data.json  # OD savings store (gitignored — personal)
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | [Next.js 16](https://nextjs.org) (App Router) |
| Language | TypeScript 5 |
| Styling | Tailwind CSS v4 |
| Charts | [Recharts](https://recharts.org) |
| Validation | [Zod v4](https://zod.dev) |
| Icons | [Lucide React](https://lucide.dev) |
| Data | JSON file store via Node.js `fs` (Server Actions) |

---

## 🚀 Getting Started

### Prerequisites
- Node.js ≥ 18
- npm

### Install & run

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

### First-time setup

1. Go to **Settings** and enter your loan details (principal, interest rate, start date, tenure).
2. Go to **Ledger** and edit the expected due amounts for any months where the bank shows an OD-adjusted figure.
3. Go to **OD Savings** and:
   - Set your **EMI Reserve** (default ₹91,143 — the full monthly EMI amount).
   - Add your funding **Sources** (e.g. Salary, Bonus).
   - Add **Goals** with target amounts.
   - Log contributions and use **Fund** on each goal to allocate from your global pool.

---

## 🔒 Data & Privacy

All data is stored **locally** in `data/loan_data.json` and `data/od_savings_data.json`. These files are **gitignored by default** — your personal financial data never leaves your machine. There is no backend, no cloud sync, and no authentication layer.

---

## 📝 License

Personal use. Not intended for public distribution.
