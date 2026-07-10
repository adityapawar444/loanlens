import { z } from "zod";

// ─── Shared money validation helpers ────────────────────────────────────────

/** Any positive monetary amount (deposits, goals, allocations). */
export const PositiveMoneySchema = z
  .number({ error: "Amount must be a valid positive number" })
  .positive("Amount must be greater than zero")
  .max(100_000_000, "Amount cannot exceed ₹10 Crore")
  .refine(
    (v) => Math.round(v * 100) === v * 100,
    "Amount can have at most 2 decimal places"
  );

/** OD account balance — allowed to be zero but never negative. */
export const NonNegativeMoneySchema = z
  .number({ error: "Balance must be a valid number" })
  .min(0, "Balance cannot be negative")
  .max(100_000_000, "Balance cannot exceed ₹10 Crore")
  .refine(
    (v) => Math.round(v * 100) === v * 100,
    "Balance can have at most 2 decimal places"
  );

// ─── Audit trail ─────────────────────────────────────────────────────────────

export const AuditRecordSchema = z.object({
  timestamp: z.string(),
  field: z.string(),
  oldValue: z.string(),
  newValue: z.string(),
});

export type AuditRecord = z.infer<typeof AuditRecordSchema>;

// ─── OdSource ────────────────────────────────────────────────────────────────

export const OdSourceSchema = z.object({
  id: z.string(),
  name: z.string().min(1, "Source name is required").max(60, "Name is too long"),
  description: z.string().max(200, "Description is too long").optional(),
  isActive: z.boolean().default(true),
  createdAt: z.string(),
  editHistory: z.array(AuditRecordSchema).default([]),
});

export type OdSource = z.infer<typeof OdSourceSchema>;

// ─── OdGoal ──────────────────────────────────────────────────────────────────

export const GOAL_COLOR_VALUES = [
  "#0f766e",
  "#2563eb",
  "#f59e0b",
  "#16a34a",
  "#e11d48",
  "#7c3aed",
  "#ea580c",
  "#0891b2",
] as const;

export const GOAL_COLORS: ReadonlyArray<{ value: string; label: string }> = [
  { value: "#0f766e", label: "Teal" },
  { value: "#2563eb", label: "Blue" },
  { value: "#f59e0b", label: "Amber" },
  { value: "#16a34a", label: "Green" },
  { value: "#e11d48", label: "Rose" },
  { value: "#7c3aed", label: "Violet" },
  { value: "#ea580c", label: "Orange" },
  { value: "#0891b2", label: "Cyan" },
];

export const OdGoalSchema = z.object({
  id: z.string(),
  name: z.string().min(1, "Goal name is required").max(80, "Name is too long"),
  targetAmount: PositiveMoneySchema,
  allocatedAmount: NonNegativeMoneySchema.default(0),
  targetDate: z.string().optional(),
  color: z.string().default(GOAL_COLOR_VALUES[0]),
  note: z.string().max(300, "Note is too long").optional(),
  isActive: z.boolean().default(true),
  editHistory: z.array(AuditRecordSchema).default([]),
});

export type OdGoal = z.infer<typeof OdGoalSchema>;

// ─── OdContribution ──────────────────────────────────────────────────────────

export const OdContributionSchema = z.object({
  id: z.string(),
  date: z.string().min(1, "Date is required"),
  amount: PositiveMoneySchema,
  sourceId: z.string().min(1, "Source is required"),
  note: z.string().max(300, "Note is too long").optional(),
  editHistory: z.array(AuditRecordSchema).default([]),
});

export type OdContribution = z.infer<typeof OdContributionSchema>;

// ─── OdBalanceAnnotation ─────────────────────────────────────────────────────

export const OdBalanceAnnotationSchema = z.object({
  odBalanceLogId: z.string(),
  sourceId: z.string().nullable().default(null),
  purpose: z.string().default("savings"),
  note: z.string().max(300).optional(),
  editHistory: z.array(AuditRecordSchema).default([]),
});

export type OdBalanceAnnotation = z.infer<typeof OdBalanceAnnotationSchema>;

// ─── Root ─────────────────────────────────────────────────────────────────────

export const OdSavingsDataSchema = z.object({
  emiReserve: z.number().min(0).default(91143),
  sources: z.array(OdSourceSchema).default([]),
  contributions: z.array(OdContributionSchema).default([]),
  goals: z.array(OdGoalSchema).default([]),
  odBalanceAnnotations: z.array(OdBalanceAnnotationSchema).default([]),
});

export type OdSavingsData = z.infer<typeof OdSavingsDataSchema>;

// ─── Client-side money validation utilities ───────────────────────────────────

export function validatePositiveMoney(raw: string, label = "Amount"): string | undefined {
  if (!raw || raw.trim() === "") return `${label} is required`;
  const n = parseFloat(raw);
  if (isNaN(n)) return `${label} must be a valid number`;
  if (n <= 0) return `${label} must be greater than zero`;
  if (n > 100_000_000) return `${label} cannot exceed ₹10 Crore`;
  if (Math.round(n * 100) !== n * 100) return `${label} can have at most 2 decimal places`;
  return undefined;
}

export function validateNonNegativeMoney(raw: string, label = "Balance"): string | undefined {
  if (!raw || raw.trim() === "") return `${label} is required`;
  const n = parseFloat(raw);
  if (isNaN(n)) return `${label} must be a valid number`;
  if (n < 0) return `${label} cannot be negative`;
  if (n > 100_000_000) return `${label} cannot exceed ₹10 Crore`;
  if (Math.round(n * 100) !== n * 100) return `${label} can have at most 2 decimal places`;
  return undefined;
}
