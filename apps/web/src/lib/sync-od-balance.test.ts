import { describe, it, expect } from "vitest";
import { syncOdBalanceLog } from "./sync-od-balance";
import { LoanData } from "./types";
import { OdSavingsData } from "./od-savings-types";

describe("syncOdBalanceLog", () => {
  it("should calculate balance correctly from contributions and payments", () => {
    const loanData = {
      odBalanceLog: [],
      paymentLog: [
        { id: "p1", dueDate: "2026-02-10", type: "emi", amountDue: 1000, amountPaid: 1000, paidDate: "2026-02-10" },
        { id: "p2", dueDate: "2026-03-10", type: "emi", amountDue: 1000, amountPaid: 1000, paidDate: "2026-03-12" }
      ]
    } as unknown as LoanData;

    const odData = {
      contributions: [
        { id: "c1", date: "2026-01-01", amount: 5000, sourceId: "s1" },
        { id: "c2", date: "2026-02-20", amount: 2000, sourceId: "s1" }
      ],
      odBalanceAnnotations: [{ odBalanceLogId: "old", sourceId: null, purpose: "savings" }]
    } as unknown as OdSavingsData;

    syncOdBalanceLog(loanData, odData);

    expect(loanData.odBalanceLog).toHaveLength(4);
    
    // 2026-01-01: +5000 = 5000
    expect(loanData.odBalanceLog[0].date).toBe("2026-01-01");
    expect(loanData.odBalanceLog[0].balance).toBe(5000);
    
    // 2026-02-10: -1000 = 4000
    expect(loanData.odBalanceLog[1].date).toBe("2026-02-10");
    expect(loanData.odBalanceLog[1].balance).toBe(4000);
    
    // 2026-02-20: +2000 = 6000
    expect(loanData.odBalanceLog[2].date).toBe("2026-02-20");
    expect(loanData.odBalanceLog[2].balance).toBe(6000);
    
    // 2026-03-12: -1000 = 5000
    expect(loanData.odBalanceLog[3].date).toBe("2026-03-12");
    expect(loanData.odBalanceLog[3].balance).toBe(5000);

    // Annotations should be cleared
    expect(odData.odBalanceAnnotations).toHaveLength(0);
  });
});
