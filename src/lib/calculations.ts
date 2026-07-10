import { AmortizationRow, LoanData, SummaryMetrics } from "./types";

// Historical due dates where actuals came from PDF statements.
// We now rely on paymentLog.amountDue and paymentLog.amountPaid for these months.
const HISTORICAL_PAYMENT_DATES: Set<string> = new Set([
  "2026-02-10",
  "2026-03-10",
  "2026-04-10",
  "2026-05-10",
  "2026-06-10",
]);

function parseDateOnly(dateKey: string): Date {
  const [year, month, day] = dateKey.split("-").map(Number);
  return new Date(year, month - 1, day);
}

function formatDateOnly(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

/**
 * Calculates the monthly EMI based on reducing balance method
 */
export function calculateEmi(principal: number, annualRate: number, tenureMonths: number): number {
  if (tenureMonths <= 0) return 0;
  const r = annualRate / 12 / 100;
  if (r === 0) return principal / tenureMonths;
  const emi = (principal * r * Math.pow(1 + r, tenureMonths)) / (Math.pow(1 + r, tenureMonths) - 1);
  return Math.round(emi);
}

/**
 * Calculates the remaining tenure based on a fixed EMI
 */
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

/**
 * Generates the full amortization schedule
 * @param data The loan data
 * @param todayDate Optional explicit date for 'today' (for SSR/Hydration stability)
 */
// eslint-disable-next-line @typescript-eslint/no-unused-vars
export function generateSchedule(data: LoanData, todayDate?: Date): AmortizationRow[] {
  const { loanDetails, disbursements, rateHistory, odBalanceLog, prepayments } = data;
  const schedule: AmortizationRow[] = [];

  const sortedDisbursements = [...disbursements].sort((a, b) => a.date.localeCompare(b.date));
  const sortedRates = [...rateHistory].sort((a, b) => a.effectiveDate.localeCompare(b.effectiveDate));
  const sortedOdLogs = [...odBalanceLog].sort((a, b) => a.date.localeCompare(b.date));
  const sortedPrepayments = [...prepayments].sort((a, b) => a.date.localeCompare(b.date));

  if (sortedDisbursements.length === 0) return [];

  const anchorDate = parseDateOnly(sortedDisbursements[0].date);
  let currentDate = new Date(anchorDate);
  
  let outstandingPrincipal = 0;
  let period = 1;
  let phase: "moratorium" | "emi" = "moratorium";
  let currentEmi = loanDetails.currentCommunicatedEmi || 0;
  let remainingTenure = loanDetails.totalTenureMonths;

  let dIdx = 0;
  let pIdx = 0;

  const getRateAt = (dateKey: string) => {
    if (sortedRates.length === 0) return 0;
    let rate = sortedRates[0].annualRate;
    for (let i = 0; i < sortedRates.length; i++) {
      if (sortedRates[i].effectiveDate <= dateKey) rate = sortedRates[i].annualRate;
      else break;
    }
    return rate;
  };

  const getOdBalanceAt = (dateKey: string) => {
    let balance = 0;
    for (let i = 0; i < sortedOdLogs.length; i++) {
      if (sortedOdLogs[i].date <= dateKey) balance = sortedOdLogs[i].balance;
      else break;
    }
    return balance;
  };

  while (outstandingPrincipal > 0.01 || dIdx < sortedDisbursements.length) {
    const nextDueDate = new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, loanDetails.dueDateDay);
    const dateKey = formatDateOnly(nextDueDate);

    let interestAccrued = 0;
    let baselineInterestAccrued = 0;
    const tempDate = new Date(currentDate);

    while (tempDate < nextDueDate) {
      const tempDateKey = formatDateOnly(tempDate);

      while (dIdx < sortedDisbursements.length && sortedDisbursements[dIdx].date === tempDateKey) {
        outstandingPrincipal += sortedDisbursements[dIdx].amount;
        dIdx++;
      }
      while (pIdx < sortedPrepayments.length && sortedPrepayments[pIdx].date === tempDateKey) {
        outstandingPrincipal -= sortedPrepayments[pIdx].amount;
        pIdx++;
      }

      const dailyRate = getRateAt(tempDateKey) / 100 / loanDetails.dayCountConvention;
      
      // Apply OD offset for interest calculation based on logged balance
      const odBalance = getOdBalanceAt(tempDateKey);
      const effectivePrincipal = Math.max(0, outstandingPrincipal - odBalance);
      
      interestAccrued += effectivePrincipal * dailyRate;
      baselineInterestAccrued += outstandingPrincipal * dailyRate;
      
      tempDate.setDate(tempDate.getDate() + 1);
    }

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

    let installment = 0;
    let principalPaid = 0;
    let interestPaid = Math.round(interestAccrued);
    let baselineInterest = Math.round(baselineInterestAccrued);
    let interestSavings = Math.max(0, baselineInterest - interestPaid);

    // For historical statement months: use paymentLog.amountDue as the scheduled due
    // (i.e., the amount the bank actually charged), so savings = amountDue - amountPaid.
    if (HISTORICAL_PAYMENT_DATES.has(dateKey)) {
      const loggedPayment = data.paymentLog.find(p => p.dueDate === dateKey);
      if (loggedPayment) {
        interestPaid = loggedPayment.amountPaid;
        // amountDue is the "expected" bank charge for the month — use it as the baseline
        // to correctly compute interest savings. Falls back to computed interest if not set.
        baselineInterest = loggedPayment.amountDue > 0 ? loggedPayment.amountDue : interestPaid;
        interestSavings = Math.max(0, baselineInterest - interestPaid);
        installment = interestPaid;
        principalPaid = 0;
      } else {
        // No entry yet — zero savings, show computed interest as installment
        interestSavings = 0;
        installment = interestPaid;
        principalPaid = 0;
      }
    } else {
      const loggedPayment = data.paymentLog.find(p => p.dueDate === dateKey);
      if (loggedPayment) {
        interestPaid = loggedPayment.amountPaid;
        interestSavings = Math.max(0, baselineInterest - interestPaid);
        if (phase === "moratorium") {
          installment = interestPaid;
          principalPaid = 0;
        } else {
          installment = loggedPayment.amountPaid;
          principalPaid = Math.max(0, installment - interestPaid);
          outstandingPrincipal = Math.max(0, outstandingPrincipal - principalPaid);
        }
      } else {
        if (phase === "moratorium") {
          installment = interestPaid;
          principalPaid = 0;
        } else {
          // Repayment phase
          installment = currentEmi || loanDetails.currentCommunicatedEmi;
          
          if (outstandingPrincipal + interestPaid <= installment) {
            installment = Math.round(outstandingPrincipal + interestPaid);
            principalPaid = outstandingPrincipal;
            outstandingPrincipal = 0;
          } else {
            principalPaid = installment - interestPaid;
            outstandingPrincipal = Math.max(0, outstandingPrincipal - principalPaid);
          }
        }
      }
    }

    if (phase === "emi") {
      if (loanDetails.policy.onPrepayment === "adjust_tenure") {
        remainingTenure = calculateTenure(outstandingPrincipal, getRateAt(dateKey), currentEmi);
      } else {
        remainingTenure--;
      }
    }

    schedule.push({
      period,
      dueDate: dateKey,
      openingBalance: Math.round(outstandingPrincipal + (phase === "emi" ? principalPaid : 0)),
      installment,
      interest: interestPaid,
      baselineInterest,
      interestSavings,
      principal: principalPaid,
      closingBalance: Math.round(outstandingPrincipal),
      phase,
      effectivePrincipal: Math.max(0, outstandingPrincipal - getOdBalanceAt(dateKey)),
    });

    // Check for closure BEFORE incrementing period/date to prevent extra month at 0 balance
    if (outstandingPrincipal <= 0.01 && dIdx >= sortedDisbursements.length) break;
    if (period > 600) break; // Safety break

    currentDate = new Date(nextDueDate);
    period++;
  }

  return schedule;
}

export function calculateMetrics(data: LoanData, schedule: AmortizationRow[], todayDate?: Date): SummaryMetrics {
  if (schedule.length === 0) {
    return {
      currentPhase: "moratorium",
      outstandingPrincipal: 0,
      effectivePrincipal: 0,
      effectiveInterestRate: 0,
      nextDueDate: "",
      nextInstallmentAmount: 0,
      projectedEmi: 0,
      projectedClosureDate: "",
      interestPaidToDate: 0,
      principalPaidToDate: 0,
      totalInterestProjected: 0,
      interestSavedTillNow: 0,
      interestSavedThisYear: 0,
      disbursedAmount: 0,
      sanctionedAmount: data.loanDetails.sanctionedAmount,
    };
  }

  const today = todayDate || new Date();
  const todayStr = formatDateOnly(today);
  const currentYear = today.getFullYear();
  const nextRow = schedule.find(row => row.dueDate >= todayStr) || schedule[schedule.length - 1];
  const pastRows = schedule.filter(row => row.dueDate < todayStr);
  const thisYearRows = pastRows.filter(row => Number(row.dueDate.slice(0, 4)) === currentYear);

  const disbursedAmount = data.disbursements.reduce((sum, d) => sum + d.amount, 0);
  const interestPaidToDate = pastRows.reduce((sum, row) => sum + row.interest, 0);
  const principalPaidToDate = pastRows.reduce((sum, row) => sum + row.principal, 0);
  const totalInterestProjected = schedule.reduce((sum, row) => sum + row.interest, 0);
  const interestSavedTillNow = pastRows.reduce((sum, row) => sum + (row.baselineInterest - row.interest), 0);
  const interestSavedThisYear = thisYearRows.reduce((sum, row) => sum + (row.baselineInterest - row.interest), 0);
  const currentAnnualRate = data.rateHistory.length > 0 ? data.rateHistory[data.rateHistory.length - 1].annualRate : 0;
  const effectiveInterestRate = nextRow.openingBalance > 0
    ? Number(((currentAnnualRate * nextRow.effectivePrincipal) / nextRow.openingBalance).toFixed(2))
    : currentAnnualRate;

  let projectedEmi = data.loanDetails.currentCommunicatedEmi;
  if (data.loanDetails.policy.onPrepayment === "adjust_emi" && nextRow.phase === "moratorium") {
    projectedEmi = calculateEmi(nextRow.openingBalance, currentAnnualRate, data.loanDetails.totalTenureMonths - data.loanDetails.moratoriumMonths);
  } else if (nextRow.phase === "emi") {
    projectedEmi = nextRow.installment;
  }

  return {
    currentPhase: nextRow.phase,
    outstandingPrincipal: nextRow.openingBalance,
    effectivePrincipal: nextRow.effectivePrincipal,
    effectiveInterestRate,
    nextDueDate: nextRow.dueDate,
    nextInstallmentAmount: nextRow.installment,
    projectedEmi,
    projectedClosureDate: schedule[schedule.length - 1].dueDate,
    interestPaidToDate,
    principalPaidToDate,
    totalInterestProjected,
    interestSavedTillNow,
    interestSavedThisYear,
    disbursedAmount,
    sanctionedAmount: data.loanDetails.sanctionedAmount,
  };
}
