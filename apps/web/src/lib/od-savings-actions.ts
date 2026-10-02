"use server";

import { revalidatePath } from "next/cache";
import { readOdData, writeOdData } from "./od-savings-data-layer";
import { readData, writeData } from "./data-layer";
import { syncOdBalanceLog } from "./sync-od-balance";
import {
  OdSource,
  OdGoal,
  OdContribution,
  OdBalanceAnnotation,
  AuditRecord,
  NonNegativeMoneySchema,
  PositiveMoneySchema,
} from "./od-savings-types";

// ─── Helpers ─────────────────────────────────────────────────────────────────

function nowIso(): string {
  return new Date().toISOString();
}

function makeAudit(field: string, oldValue: unknown, newValue: unknown): AuditRecord {
  return {
    timestamp: nowIso(),
    field,
    oldValue: JSON.stringify(oldValue ?? null),
    newValue: JSON.stringify(newValue ?? null),
  };
}

function diffAudit<T extends Record<string, unknown>>(
  original: T,
  patch: Partial<T>
): AuditRecord[] {
  return Object.entries(patch)
    .filter(([key, val]) => JSON.stringify(original[key]) !== JSON.stringify(val))
    .map(([key, val]) => makeAudit(key, original[key], val));
}

type ActionResult<T = undefined> =
  | { success: true; data?: T; overAllocated?: boolean }
  | { success: false; error: string };

// ─── Data getter ─────────────────────────────────────────────────────────────

export async function getOdSavingsData() {
  return readOdData();
}

// ─── EMI Reserve ─────────────────────────────────────────────────────────────

export async function updateEmiReserve(amount: number): Promise<ActionResult> {
  if (isNaN(amount) || amount < 0)
    return { success: false, error: "EMI reserve cannot be negative." };
  if (amount > 100_000_000)
    return { success: false, error: "EMI reserve cannot exceed ₹10 Crore." };
  if (Math.round(amount * 100) !== amount * 100)
    return { success: false, error: "EMI reserve can have at most 2 decimal places." };
  const data = await readOdData();
  data.emiReserve = amount;
  await writeOdData(data);
  revalidatePath("/od-savings");
  return { success: true };
}

// ─── Sources ─────────────────────────────────────────────────────────────────

export async function addSource(
  source: Omit<OdSource, "editHistory">
): Promise<ActionResult> {
  const data = await readOdData();
  const duplicate = data.sources.some(
    (s) => s.name.trim().toLowerCase() === source.name.trim().toLowerCase()
  );
  if (duplicate) {
    return { success: false, error: "A source with this name already exists." };
  }
  data.sources.push({ ...source, editHistory: [] });
  await writeOdData(data);
  revalidatePath("/od-savings");
  return { success: true };
}

export async function editSource(
  id: string,
  patch: Partial<Pick<OdSource, "name" | "description" | "isActive">>
): Promise<ActionResult> {
  const data = await readOdData();
  const source = data.sources.find((s) => s.id === id);
  if (!source) return { success: false, error: "Source not found." };

  if (
    patch.name &&
    patch.name.trim().toLowerCase() !== source.name.trim().toLowerCase() &&
    data.sources.some(
      (s) => s.id !== id && s.name.trim().toLowerCase() === patch.name!.trim().toLowerCase()
    )
  ) {
    return { success: false, error: "A source with this name already exists." };
  }

  const audit = diffAudit(source as Record<string, unknown>, patch as Record<string, unknown>);
  Object.assign(source, patch);
  source.editHistory.push(...audit);
  await writeOdData(data);
  revalidatePath("/od-savings");
  return { success: true };
}

// ─── Goals ───────────────────────────────────────────────────────────────────

export async function addGoal(goal: Omit<OdGoal, "editHistory">): Promise<ActionResult> {
  const parse = PositiveMoneySchema.safeParse(goal.targetAmount);
  if (!parse.success) {
    return { success: false, error: parse.error.issues[0]?.message ?? "Invalid target amount." };
  }
  const data = await readOdData();
  data.goals.push({ ...goal, editHistory: [] });
  await writeOdData(data);
  revalidatePath("/od-savings");
  return { success: true };
}

export async function editGoal(
  id: string,
  patch: Partial<Omit<OdGoal, "id" | "editHistory">>
): Promise<ActionResult> {
  if (patch.targetAmount !== undefined) {
    const parse = PositiveMoneySchema.safeParse(patch.targetAmount);
    if (!parse.success) {
      return { success: false, error: parse.error.issues[0]?.message ?? "Invalid target amount." };
    }
  }
  if (patch.allocatedAmount !== undefined) {
    const parse = NonNegativeMoneySchema.safeParse(patch.allocatedAmount);
    if (!parse.success) {
      return { success: false, error: parse.error.issues[0]?.message ?? "Invalid allocated amount." };
    }
  }
  const data = await readOdData();
  const goal = data.goals.find((g) => g.id === id);
  if (!goal) return { success: false, error: "Goal not found." };

  const audit = diffAudit(goal as Record<string, unknown>, patch as Record<string, unknown>);
  Object.assign(goal, patch);
  goal.editHistory.push(...audit);
  await writeOdData(data);
  revalidatePath("/od-savings");
  return { success: true };
}

// ─── Contributions ───────────────────────────────────────────────────────────

export async function addContribution(
  contribution: Omit<OdContribution, "editHistory">
): Promise<ActionResult> {
  const parse = PositiveMoneySchema.safeParse(contribution.amount);
  if (!parse.success) {
    return { success: false, error: parse.error.issues[0]?.message ?? "Invalid amount." };
  }
  const data = await readOdData();
  const loanData = await readData();
  const full: OdContribution = { ...contribution, editHistory: [] };
  data.contributions.push(full);
  
  syncOdBalanceLog(loanData, data);
  await writeData(loanData);
  await writeOdData(data);
  revalidatePath("/od-savings");
  revalidatePath("/");
  return { success: true };
}

export async function editContribution(
  id: string,
  patch: Partial<Omit<OdContribution, "id" | "editHistory">>
): Promise<ActionResult> {
  if (patch.amount !== undefined) {
    const parse = PositiveMoneySchema.safeParse(patch.amount);
    if (!parse.success) {
      return { success: false, error: parse.error.issues[0]?.message ?? "Invalid amount." };
    }
  }
  const data = await readOdData();
  const loanData = await readData();
  const contribution = data.contributions.find((c) => c.id === id);
  if (!contribution) return { success: false, error: "Contribution not found." };

  const audit = diffAudit(
    contribution as Record<string, unknown>,
    patch as Record<string, unknown>
  );
  Object.assign(contribution, patch);
  contribution.editHistory.push(...audit);
  
  syncOdBalanceLog(loanData, data);
  await writeData(loanData);
  await writeOdData(data);
  revalidatePath("/od-savings");
  revalidatePath("/");
  return { success: true };
}

