import { describe, it, expect } from "vitest";
import { calculateEmi, calculateTenure, generateSchedule } from "./calculations";
import { LoanData } from "./types";

describe("Financial Calculations", () => {
  it("should calculate correct EMI", () => {
    // 1,00,00,000 at 7.6% for 300 months
    const emi = calculateEmi(10000000, 7.6, 300);
    expect(emi).toBe(74551);
  });

  it("should calculate correct tenure for fixed EMI", () => {
    // 1,00,00,000 at 7.6%, EMI 91,143
    const tenure = calculateTenure(10000000, 7.6, 91143);
    // Solving n = ln(EMI / (EMI - P*r)) / ln(1+r)
    // P*r = 10000000 * (7.6/12/100) = 63333.33
    // EMI / (EMI - P*r) = 91143 / (91143 - 63333.33) = 91143 / 27809.67 = 3.277
    // ln(3.277) / ln(1.00633) = 1.187 / 0.00631 = 188.1
    expect(tenure).toBe(189);
  });

  it("should respect fixed EMI policy at moratorium exit", () => {
    const mockData: LoanData = {
      loanDetails: {
        lender: "Test",
        accountNumber: "123",
        sanctionedAmount: 11965000,
        totalTenureMonths: 300,
        moratoriumMonths: 2,
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
        { id: "1", date: "2027-01-01", amount: 6000000 }
      ],
      rateHistory: [
        { id: "1", effectiveDate: "2027-01-01", annualRate: 7.6 }
      ],
      odBalanceLog: [],
      prepayments: [],
      paymentLog: []
    };

    const schedule = generateSchedule(mockData);
    const emiPhaseStart = schedule.find(row => row.phase === "emi");
    
    expect(emiPhaseStart).toBeDefined();
    expect(emiPhaseStart?.installment).toBe(91143);
  });

  it("should match Row 19 of the PDF schedule exactly (EMI start)", () => {
    const pdfData: LoanData = {
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
        { id: "1", date: "2026-01-31", amount: 5982984 },
        { id: "2", date: "2026-06-02", amount: 438152 }
      ],
      rateHistory: [
        { id: "1", effectiveDate: "2026-01-31", annualRate: 7.6 }
      ],
      odBalanceLog: [],
      prepayments: [],
      paymentLog: []
    };

    const schedule = generateSchedule(pdfData);
    const row19 = schedule[18]; // Period 19 is Aug 2027

    expect(row19.dueDate).toBe("2027-08-10");
    expect(row19.openingBalance).toBe(6421136);
    expect(row19.installment).toBe(91143);
    // 6421136 * 0.076 * 31 / 365 = 41447.19
    expect(row19.interest).toBe(41447);
    expect(row19.principal).toBe(49696);
    expect(row19.closingBalance).toBe(6371440);
  });

  it("should adjust the final installment to close the loan exactly", () => {
    const mockData: LoanData = {
      loanDetails: {
        lender: "Test",
        accountNumber: "123",
        sanctionedAmount: 1000000,
        totalTenureMonths: 12,
        moratoriumMonths: 0,
        moratoriumAnchor: "first_disbursement",
        dueDateDay: 10,
        dayCountConvention: 365,
        currentCommunicatedEmi: 100000,
        policy: {
          onRateChange: "adjust_tenure",
          onDisbursementDuringEmi: "adjust_tenure",
          onPrepayment: "adjust_tenure"
        }
      },
      disbursements: [
        { id: "1", date: "2026-01-01", amount: 100000 }
      ],
      rateHistory: [
        { id: "1", effectiveDate: "2026-01-01", annualRate: 12 }
      ],
      odBalanceLog: [],
      prepayments: [],
      paymentLog: []
    };

    const schedule = generateSchedule(mockData);
    const lastRow = schedule[schedule.length - 1];
    expect(lastRow.closingBalance).toBe(0);
  });
});
