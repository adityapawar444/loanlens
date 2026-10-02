
import { describe, it, expect } from "vitest";
import { generateSchedule, calculateMetrics } from "./calculations";
import { LoanData } from "./types";

describe("Simulator Specific Debugging", () => {
  const baseData: LoanData = {
    loanDetails: {
      lender: "Bank of Baroda",
      accountNumber: "83990600004041",
      sanctionedAmount: 11965000,
      totalTenureMonths: 300,
      moratoriumMonths: 18,
      moratoriumAnchor: "first_disbursement",
      dueDateDay: 10,
      dayCountConvention: 365,
      currentCommunicatedEmi: 91143,
      policy: {
        onRateChange: "adjust_tenure",
        onDisbursementDuringEmi: "adjust_tenure",
        onPrepayment: "adjust_tenure"
      }
    },
    disbursements: [
      { id: "init-1", date: "2026-01-31", amount: 5982984 },
      { id: "init-2", date: "2026-06-02", amount: 438152 }
    ],
    rateHistory: [
      { id: "rate-1", effectiveDate: "2026-01-31", annualRate: 7.6 }
    ],
    odBalanceLog: [],
    prepayments: [],
    paymentLog: []
  };

  it("should calculate correct tenure for base data (no OD)", () => {
    const schedule = generateSchedule(baseData, new Date("2026-06-18"));
    // With 64.21L and 91k EMI, it should close far before the 300-month sanction tenor.
    expect(schedule.length).toBe(112);
    expect(schedule[schedule.length - 1].closingBalance).toBeLessThanOrEqual(0.01);
  });

  it("should expose dashboard KPI metrics", () => {
    const schedule = generateSchedule(baseData, new Date("2026-06-18"));
    const metrics = calculateMetrics(baseData, schedule, new Date("2026-06-18"));

    expect(metrics.interestPaidToDate).toBeGreaterThan(0);
    expect(metrics.principalPaidToDate).toBeGreaterThanOrEqual(0);
    expect(metrics.interestSavedTillNow).toBeGreaterThanOrEqual(0);
    expect(metrics.interestSavedThisYear).toBeGreaterThanOrEqual(0);
    expect(metrics.effectiveInterestRate).toBeGreaterThan(0);
  });

  it("should keep closing balance unchanged when OD reduces interest only", () => {
    const odOnlyData: LoanData = {
      loanDetails: {
        lender: "Bank of Baroda",
        accountNumber: "83990600004041",
        sanctionedAmount: 11965000,
        totalTenureMonths: 300,
        moratoriumMonths: 2,
        moratoriumAnchor: "first_disbursement",
        dueDateDay: 11,
        dayCountConvention: 365,
        currentCommunicatedEmi: 91143,
        policy: {
          onRateChange: "adjust_tenure",
          onDisbursementDuringEmi: "adjust_tenure",
          onPrepayment: "adjust_tenure"
        }
      },
      disbursements: [{ id: "init-1", date: "2026-01-01", amount: 1000000 }],
      rateHistory: [{ id: "rate-1", effectiveDate: "2026-01-01", annualRate: 12 }],
      odBalanceLog: [{ id: "od-1", date: "2026-01-15", balance: 250000 }],
      prepayments: [],
      paymentLog: []
    };

    const schedule = generateSchedule(odOnlyData, new Date("2026-01-20"));
    const firstRow = schedule[0];

    expect(firstRow.closingBalance).toBe(1000000);
    expect(firstRow.effectivePrincipal).toBeLessThan(firstRow.closingBalance);
    expect(firstRow.interestSavings).toBeGreaterThan(0);
  });

  it("should show even shorter tenure with high OD balance", () => {
    const odData: LoanData = {
      ...baseData,
      odBalanceLog: [{ id: "od-sim", date: "2026-06-20", balance: 5000000 }] // 50L OD balance
    };
    const baseSchedule = generateSchedule(baseData, new Date("2026-06-18"));
    const odSchedule = generateSchedule(odData, new Date("2026-06-18"));
    
    expect(odSchedule.length).toBeLessThan(baseSchedule.length);
  });

  it("should handle the 'adjust_tenure' policy correctly during transition", () => {
      const schedule = generateSchedule(baseData, new Date("2026-06-18"));
      const emiStart = schedule.find(r => r.period === 19);
      expect(emiStart?.phase).toBe("emi");
      expect(emiStart?.installment).toBe(91143);
  });
});
