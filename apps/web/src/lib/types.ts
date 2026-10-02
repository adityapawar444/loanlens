import { z } from "zod";

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

export type Disbursement = z.infer<typeof DisbursementSchema>;
export type RateHistory = z.infer<typeof RateHistorySchema>;
export type OdBalanceLog = z.infer<typeof OdBalanceLogSchema>;
export type Prepayment = z.infer<typeof PrepaymentSchema>;
export type PaymentLog = z.infer<typeof PaymentLogSchema>;
export type LoanDetails = z.infer<typeof LoanDetailsSchema>;
export type LoanData = z.infer<typeof LoanDataSchema>;

export interface AmortizationRow {
  period: number;
  dueDate: string;
  openingBalance: number;
  installment: number;
  interest: number;
  baselineInterest: number; // Interest without OD offset
  interestSavings: number;
  principal: number;
  closingBalance: number;
  phase: "moratorium" | "emi";
  effectivePrincipal: number;
}

export interface SummaryMetrics {
  currentPhase: "moratorium" | "emi";
  outstandingPrincipal: number;
  effectivePrincipal: number;
  effectiveInterestRate: number;
  nextDueDate: string;
  nextInstallmentAmount: number;
  projectedEmi: number;
  projectedClosureDate: string;
  interestPaidToDate: number;
  principalPaidToDate: number;
  totalInterestProjected: number;
  interestSavedTillNow: number;
  interestSavedThisYear: number;
  disbursedAmount: number;
  sanctionedAmount: number;
}
