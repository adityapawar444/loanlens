"use server";

import { readData, writeData } from "@/lib/data-layer";
import { readOdData, writeOdData } from "@/lib/od-savings-data-layer";
import { syncOdBalanceLog } from "./sync-od-balance";
import { Disbursement, RateHistory, OdBalanceLog } from "@/lib/types";
import { revalidatePath } from "next/cache";

export async function getLoanData() {
  return await readData();
}

export async function addDisbursement(disbursement: Disbursement) {
  if (!disbursement.amount || disbursement.amount <= 0)
    throw new Error("Disbursement amount must be greater than zero.");
  if (disbursement.amount > 100_000_000)
    throw new Error("Disbursement amount cannot exceed ₹10 Crore.");
  if (!disbursement.date) throw new Error("Date is required.");
  const data = await readData();
  data.disbursements.push(disbursement);
  await writeData(data);
  revalidatePath("/");
}

export async function addRateHistory(rate: RateHistory) {
  const data = await readData();
  data.rateHistory.push(rate);
  await writeData(data);
  revalidatePath("/");
}

export async function addOdBalanceLog(log: OdBalanceLog) {
  if (log.balance === undefined || log.balance === null || isNaN(log.balance))
    throw new Error("OD balance must be a valid number.");
  if (log.balance < 0) throw new Error("OD balance cannot be negative.");
  if (log.balance > 100_000_000) throw new Error("OD balance cannot exceed ₹10 Crore.");
  if (!log.date) throw new Error("Date is required.");
  const data = await readData();
  data.odBalanceLog.push(log);
  await writeData(data);
  revalidatePath("/");
}

export async function updateLoanDetails(formData: FormData) {
  const data = await readData();
  data.loanDetails = {
    ...data.loanDetails,
    lender: formData.get("lender") as string,
    sanctionedAmount: Number(formData.get("sanctionedAmount")),
    totalTenureMonths: Number(formData.get("totalTenureMonths")),
    moratoriumMonths: Number(formData.get("moratoriumMonths")),
    dueDateDay: Number(formData.get("dueDateDay")),
    policy: {
      onRateChange: formData.get("policy.onRateChange") as "adjust_tenure" | "adjust_emi",
      onDisbursementDuringEmi: data.loanDetails.policy.onDisbursementDuringEmi,
      onPrepayment: formData.get("policy.onPrepayment") as "adjust_tenure" | "adjust_emi",
    }
  };
  await writeData(data);
  revalidatePath("/");
}

export async function updatePayment(id: string, amountPaid: number) {
  if (!amountPaid || amountPaid <= 0)
    throw new Error("Amount paid must be greater than zero.");
  if (amountPaid > 100_000_000)
    throw new Error("Amount paid cannot exceed ₹10 Crore.");
  const data = await readData();
  const payment = data.paymentLog.find(p => p.id === id);
  if (payment) {
    const diff = amountPaid - (payment.amountPaid || 0);
    payment.amountPaid = amountPaid;
    await writeData(data);
    
    if (diff > 0) {
      const odData = await readOdData();
      if (odData.emiReserveAllocated > 0) {
        odData.emiReserveAllocated = Math.max(0, odData.emiReserveAllocated - diff);
        await writeOdData(odData);
      }
    }
    
    revalidatePath("/");
  }
}

export async function updateAmountDue(id: string, amountDue: number) {
  if (amountDue === undefined || amountDue === null || isNaN(amountDue))
    throw new Error("Amount due must be a valid number.");
  if (amountDue < 0) throw new Error("Amount due cannot be negative.");
  if (amountDue > 100_000_000) throw new Error("Amount due cannot exceed ₹10 Crore.");
  const data = await readData();
  const payment = data.paymentLog.find(p => p.id === id);
  if (payment) {
    payment.amountDue = amountDue;
    await writeData(data);
    revalidatePath("/");
  }
}
