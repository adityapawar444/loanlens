import { LoanData } from "./types";
import { OdSavingsData } from "./od-savings-types";

export function syncOdBalanceLog(loanData: LoanData, odData: OdSavingsData) {
  const events: { date: string; amount: number; id: string }[] = [];
  
  for (const c of odData.contributions) {
    events.push({ date: c.date, amount: c.amount, id: c.id });
  }
  
  for (const p of loanData.paymentLog) {
    if (p.amountPaid > 0) {
       events.push({ date: p.paidDate || p.dueDate, amount: -p.amountPaid, id: p.id });
    }
  }
  
  // Sort events chronologically. If same date, contributions (positive) before deductions (negative)
  events.sort((a, b) => {
    if (a.date !== b.date) return a.date.localeCompare(b.date);
    return b.amount - a.amount;
  });
  
  let balance = 0;
  const logMap = new Map<string, number>();
  
  for (const e of events) {
    balance += e.amount;
    balance = Math.max(0, balance);
    logMap.set(e.date, balance);
  }
  
  loanData.odBalanceLog = Array.from(logMap.entries()).map(([date, bal]) => ({
    id: `auto_${date.replace(/-/g, "")}`,
    date,
    balance: bal
  }));

  // We can clear odBalanceAnnotations since we don't use manual annotations anymore
  // Or we could leave it. It's safer to just clear it to avoid dangling references.
  odData.odBalanceAnnotations = [];
}
