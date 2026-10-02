/**
 * Golden Fixture Generator
 *
 * Runs generateSchedule() and calculateMetrics() on pinned input data
 * to produce 8 golden fixture JSON files under loanlens-bundle/fixtures/.
 *
 * Usage:  npx tsx scripts/generate-fixtures.ts
 */

import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { generateSchedule, calculateMetrics } from "../src/lib/calculations";
import type { LoanData } from "../src/lib/types";

// ---------------------------------------------------------------------------
// Paths
// ---------------------------------------------------------------------------
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");
const DATA_PATH = path.join(ROOT, "data", "loan_data.json");
const FIXTURES_DIR = path.join(ROOT, "loanlens-bundle", "fixtures");

// ---------------------------------------------------------------------------
// Pinned "today" for metrics computation (per spec)
// ---------------------------------------------------------------------------
const TODAY = new Date(2026, 8, 19); // 2026-09-19 (month is 0-indexed)

// ---------------------------------------------------------------------------
// Load base data
// ---------------------------------------------------------------------------
const rawBase: LoanData = JSON.parse(fs.readFileSync(DATA_PATH, "utf-8")) as LoanData;

/** Deep-clone the base data so each scenario gets its own copy */
function cloneBase(): LoanData {
  return JSON.parse(JSON.stringify(rawBase)) as LoanData;
}

/** Redact account number as required */
function redact(data: LoanData): LoanData {
  return {
    ...data,
    loanDetails: { ...data.loanDetails, accountNumber: "REDACTED" },
  };
}

// ---------------------------------------------------------------------------
// Fixture builder
// ---------------------------------------------------------------------------
interface Fixture {
  scenario: string;
  description: string;
  input: LoanData;
  expected_schedule: ReturnType<typeof generateSchedule>;
  expected_metrics: ReturnType<typeof calculateMetrics>;
}

function buildFixture(scenario: string, description: string, data: LoanData): Fixture {
  const schedule = generateSchedule(data, TODAY);
  const metrics = calculateMetrics(data, schedule, TODAY);
  return {
    scenario,
    description,
    input: redact(data),
    expected_schedule: schedule,
    expected_metrics: metrics,
  };
}

// ---------------------------------------------------------------------------
// Scenario definitions
// ---------------------------------------------------------------------------
const scenarios: Array<{ name: string; description: string; data: LoanData }> = [];

// 1. base — current real data, no modifications
{
  scenarios.push({
    name: "base",
    description: "Current real data, no modifications",
    data: cloneBase(),
  });
}

// 2. prepayment — ₹5,00,000 prepayment on 2026-10-01
{
  const data = cloneBase();
  data.prepayments.push({
    id: "fix-prepayment-1",
    date: "2026-10-01",
    amount: 500000,
    note: "Fixture: ₹5,00,000 prepayment on 2026-10-01",
  });
  scenarios.push({
    name: "prepayment",
    description: "₹5,00,000 prepayment on 2026-10-01",
    data,
  });
}

// 3. rate-change — rate changes to 7.0% from 2026-10-01
{
  const data = cloneBase();
  data.rateHistory.push({
    id: "fix-rate-change-1",
    effectiveDate: "2026-10-01",
    annualRate: 7.0,
    benchmark: "RLLR",
  });
  scenarios.push({
    name: "rate-change",
    description: "Interest rate changes to 7.0% from 2026-10-01",
    data,
  });
}

// 4. od-change — OD balance increases to ₹15,00,000 from 2026-10-01
{
  const data = cloneBase();
  data.odBalanceLog.push({
    id: "fix-od-change-1",
    date: "2026-10-01",
    balance: 1500000,
  });
  scenarios.push({
    name: "od-change",
    description: "OD balance set to ₹15,00,000 from 2026-10-01",
    data,
  });
}

// 5. disbursement-during-emi — additional ₹10,00,000 disbursement on 2027-10-01
//    (during EMI phase, since moratorium ends after 18 months from 2026-01-31 → mid 2027)
{
  const data = cloneBase();
  data.disbursements.push({
    id: "fix-disb-emi-1",
    date: "2027-10-01",
    amount: 1000000,
    note: "Fixture: ₹10,00,000 disbursement during EMI phase on 2027-10-01",
  });
  scenarios.push({
    name: "disbursement-during-emi",
    description: "₹10,00,000 disbursement during EMI phase on 2027-10-01",
    data,
  });
}

// 6. moratorium-boundary — verify schedule at moratorium period 18→19 boundary
//    Same as base; consumers inspect the schedule for the phase flip at period 18/19
{
  const data = cloneBase();
  scenarios.push({
    name: "moratorium-boundary",
    description:
      "Base data for verifying moratorium boundary (period 18→19 phase flip from moratorium to EMI)",
    data,
  });
}

// 7. zero-od — empty odBalanceLog
{
  const data = cloneBase();
  data.odBalanceLog = [];
  scenarios.push({
    name: "zero-od",
    description: "Empty odBalanceLog — no OD offset applied to interest",
    data,
  });
}

// 8. high-prepayment — ₹70,00,000 prepayment on 2027-09-01 (loan near-closure)
{
  const data = cloneBase();
  data.prepayments.push({
    id: "fix-high-prepay-1",
    date: "2027-09-01",
    amount: 7000000,
    note: "Fixture: ₹70,00,000 high prepayment on 2027-09-01",
  });
  scenarios.push({
    name: "high-prepayment",
    description: "₹70,00,000 prepayment on 2027-09-01 — loan near closure",
    data,
  });
}

// ---------------------------------------------------------------------------
// Generate & write fixtures
// ---------------------------------------------------------------------------
fs.mkdirSync(FIXTURES_DIR, { recursive: true });

let count = 0;
for (const { name, description, data } of scenarios) {
  const fixture = buildFixture(name, description, data);
  const outPath = path.join(FIXTURES_DIR, `${name}.json`);
  fs.writeFileSync(outPath, JSON.stringify(fixture, null, 2), "utf-8");

  // Validate required keys
  const parsed = JSON.parse(fs.readFileSync(outPath, "utf-8")) as Record<string, unknown>;
  if (!("input" in parsed && "expected_schedule" in parsed && "expected_metrics" in parsed)) {
    throw new Error(`Fixture ${name}.json is missing required keys!`);
  }

  count++;
  console.log(`✅  [${count}/8] ${name}.json written (${(fs.statSync(outPath).size / 1024).toFixed(1)} KB)`);
}

if (count !== 8) {
  throw new Error(`Expected 8 fixtures, got ${count}`);
}

console.log(`\n🎉  All ${count} fixtures generated in loanlens-bundle/fixtures/`);
