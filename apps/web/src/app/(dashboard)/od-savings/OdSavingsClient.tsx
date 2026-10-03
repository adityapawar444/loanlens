"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import {
  Area,
  AreaChart,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  Banknote,
  ChevronDown,
  ChevronRight,
  CircleDollarSign,
  ClipboardList,
  History,
  Layers3,
  Pencil,
  PiggyBank,
  Plus,
  Settings2,
  Target,
  TriangleAlert,
  Wallet,
  X,
} from "lucide-react";
import type { LoanData } from "@/lib/types";
import type {
  OdSavingsData,
  OdSource,
  OdGoal,
  OdContribution,
  OdBalanceAnnotation,
  AuditRecord,
} from "@/lib/od-savings-types";
import {
  GOAL_COLORS,
  validatePositiveMoney,
  validateNonNegativeMoney,
} from "@/lib/od-savings-types";
import {
  addSource,
  editSource,
  addGoal,
  editGoal,
  addContribution,
  editContribution,
  updateEmiReserve,
  updateEmiReserveAllocated,
} from "@/lib/od-savings-actions";

// ─── Modal state discriminated union ─────────────────────────────────────────

type ModalState =
  | { type: "none" }
  | { type: "add-contribution" }
  | { type: "edit-contribution"; id: string }
  | { type: "add-goal" }
  | { type: "edit-goal"; id: string }
  | { type: "sources" }
  | { type: "add-source" }
  | { type: "edit-source"; id: string }
  | { type: "add-od-balance" }
  | { type: "edit-annotation"; odBalanceLogId: string };

// ─── Helpers ─────────────────────────────────────────────────────────────────

const SOURCE_PALETTE = GOAL_COLORS.map((c) => c.value);

function newId() {
  return Math.random().toString(36).slice(2, 11);
}

function todayStr() {
  return new Date().toISOString().slice(0, 10);
}

function fmtShort(n: number): string {
  if (n >= 10_000_000) return `${(n / 10_000_000).toFixed(1)}Cr`;
  if (n >= 100_000) return `${(n / 100_000).toFixed(1)}L`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return n.toFixed(0);
}

function formatAxisShort(v: number) {
  if (v >= 100_000) return `${Math.round(v / 100_000)}L`;
  if (v >= 1_000) return `${Math.round(v / 1_000)}k`;
  return `${Math.round(v)}`;
}

function fmtMonthLabel(yyyymm: string) {
  const [y, m] = yyyymm.split("-");
  return new Date(Number(y), Number(m) - 1, 1).toLocaleDateString("en-US", {
    month: "short",
    year: "2-digit",
  });
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function OdSavingsClient({
  loanData,
  odData,
}: {
  loanData: LoanData;
  odData: OdSavingsData;
}) {
  const [modal, setModal] = useState<ModalState>({ type: "none" });
  const [mounted, setMounted] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  // EMI Reserve inline edit state
  const [editingEmiReserve, setEditingEmiReserve] = useState(false);
  const [emiReserveInput, setEmiReserveInput] = useState(String(odData.emiReserve));
  const [emiReserveError, setEmiReserveError] = useState<string | null>(null);
  const [emiReserveSaving, setEmiReserveSaving] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 3500);
    return () => clearTimeout(t);
  }, [toast]);

  const formatter = useMemo(
    () =>
      new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: "INR",
        maximumFractionDigits: 0,
      }),
    []
  );

  // ── Derived metrics ──────────────────────────────────────────────────────

  const totalDeposited = useMemo(
    () => odData.contributions.reduce((s, c) => s + c.amount, 0),
    [odData.contributions]
  );

  const latestOdBalance = useMemo(() => {
    if (!loanData.odBalanceLog.length) return 0;
    return [...loanData.odBalanceLog].sort((a, b) => b.date.localeCompare(a.date))[0]
      .balance;
  }, [loanData.odBalanceLog]);

  const activeGoals = useMemo(
    () => odData.goals.filter((g) => g.isActive),
    [odData.goals]
  );

  const totalTargets = useMemo(
    () => activeGoals.reduce((s, g) => s + g.targetAmount, 0),
    [activeGoals]
  );

  const byGoalData = useMemo(() => {
    const map = new Map<string, number>();
    for (const g of odData.goals) {
      map.set(g.id, g.allocatedAmount);
    }
    return { map };
  }, [odData.goals]);

  const bySourceData = useMemo(() => {
    const map = new Map<string, { sourceId: string; name: string; total: number }>();
    for (const c of odData.contributions) {
      const src = odData.sources.find((s) => s.id === c.sourceId);
      const name = src?.name ?? "Unknown";
      const existing = map.get(c.sourceId) ?? { sourceId: c.sourceId, name, total: 0 };
      map.set(c.sourceId, { ...existing, total: existing.total + c.amount });
    }
    return [...map.values()].sort((a, b) => b.total - a.total);
  }, [odData.contributions, odData.sources]);

  const totalGap = totalTargets - latestOdBalance;

  // ── EMI reserve constraint metrics ──────────────────────────────────────
  const emiReserve = odData.emiReserve;

  const fundedEmiReserve = useMemo(
    () => Math.min(latestOdBalance, odData.emiReserveAllocated),
    [latestOdBalance, odData.emiReserveAllocated]
  );

  const allocatableBalance = useMemo(
    () => latestOdBalance - fundedEmiReserve,
    [latestOdBalance, fundedEmiReserve]
  );

  const totalAllocatedToGoals = useMemo(
    () => odData.goals.reduce((sum, g) => sum + g.allocatedAmount, 0),
    [odData.goals]
  );

  const freeAllocatable = allocatableBalance - totalAllocatedToGoals;
  const isOverAllocated = totalAllocatedToGoals > allocatableBalance + 0.001;
  const isCriticalOverAllocation = totalAllocatedToGoals > latestOdBalance + 0.001;
  const attributionGap = latestOdBalance - totalDeposited;

  async function handleSaveEmiReserve() {
    const n = parseFloat(emiReserveInput);
    const err = validateNonNegativeMoney(emiReserveInput, "EMI Reserve");
    if (err) { setEmiReserveError(err); return; }
    setEmiReserveSaving(true);
    setEmiReserveError(null);
    const res = await updateEmiReserve(n);
    setEmiReserveSaving(false);
    if (!res.success) { setEmiReserveError(res.error); return; }
    setEditingEmiReserve(false);
    showToast("EMI reserve updated.");
  }

  const [emiReserveRefilling, setEmiReserveRefilling] = useState(false);
  async function handleRefillEmiReserve() {
    setEmiReserveRefilling(true);
    const res = await updateEmiReserveAllocated(emiReserve);
    setEmiReserveRefilling(false);
    if (!res.success) { showToast(res.error); return; }
    showToast("EMI reserve refilled.");
  }


  // ── MoM chart data ───────────────────────────────────────────────────────

  const momData = useMemo(() => {
    const monthMap = new Map<string, { balance: number | null; deposited: number }>();
    for (const e of [...loanData.odBalanceLog].sort((a, b) =>
      a.date.localeCompare(b.date)
    )) {
      const mo = e.date.slice(0, 7);
      const ex = monthMap.get(mo) ?? { balance: null, deposited: 0 };
      monthMap.set(mo, { ...ex, balance: e.balance });
    }
    for (const c of odData.contributions) {
      const mo = c.date.slice(0, 7);
      const ex = monthMap.get(mo) ?? { balance: null, deposited: 0 };
      monthMap.set(mo, { ...ex, deposited: ex.deposited + c.amount });
    }
    let cum = 0;
    return [...monthMap.entries()]
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([mo, d]) => {
        cum += d.deposited;
        return {
          label: fmtMonthLabel(mo),
          odBalance: d.balance,
          deposited: d.deposited,
          cumDeposited: cum,
        };
      });
  }, [loanData.odBalanceLog, odData.contributions]);

  // ── Annotation lookup ────────────────────────────────────────────────────

  const annotationMap = useMemo(() => {
    const m = new Map<string, OdBalanceAnnotation>();
    for (const a of odData.odBalanceAnnotations) m.set(a.odBalanceLogId, a);
    return m;
  }, [odData.odBalanceAnnotations]);

  const resolveSource = (id: string | null | undefined) =>
    id ? (odData.sources.find((s) => s.id === id)?.name ?? "Unknown") : "Unspecified";

  const closeModal = () => setModal({ type: "none" });
  const showToast = (msg: string) => setToast(msg);

  // ── Sorted OD balance log (newest first) ─────────────────────────────────
  const sortedOdLog = useMemo(
    () => [...loanData.odBalanceLog].sort((a, b) => b.date.localeCompare(a.date)),
    [loanData.odBalanceLog]
  );

  const sortedContributions = useMemo(
    () => [...odData.contributions].sort((a, b) => b.date.localeCompare(a.date)),
    [odData.contributions]
  );

  // ─────────────────────────────────────────────────────────────────────────
  // RENDER
  // ─────────────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-6">
      {/* Toast */}
      {toast && (
        <div className="fixed bottom-6 right-6 z-[100] flex items-center gap-3 rounded-2xl border border-emerald-100 bg-emerald-50 px-4 py-3 shadow-xl">
          <div className="h-2 w-2 rounded-full bg-emerald-500" />
          <p className="text-sm font-medium text-emerald-900">{toast}</p>
          <button onClick={() => setToast(null)} className="ml-2 text-emerald-400 hover:text-emerald-700">
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {/* ── Page Header ────────────────────────────────────────────────────── */}
      <div>
        <div className="inline-flex items-center gap-2 rounded-full border border-teal-100 bg-teal-50 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-teal-700">
          <PiggyBank className="h-3 w-3" /> OD Savings
        </div>
        <h2 className="mt-3 text-2xl font-semibold tracking-tight text-slate-950">
          Savings Account Details
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          Track money put in by source and goal, monitor targets, and review OD balance trends.
        </p>
      </div>

      {/* ── KPI Strip ──────────────────────────────────────────────────────── */}
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <KpiCard
          label="Total Deposited"
          value={formatter.format(totalDeposited)}
          sub="Sum of all contributions logged"
          icon={<Wallet className="h-4 w-4" />}
          accent="teal"
        />
        <KpiCard
          label="OD Balance"
          value={formatter.format(latestOdBalance)}
          sub={
            loanData.odBalanceLog.length
              ? `As of ${[...loanData.odBalanceLog].sort((a, b) => b.date.localeCompare(a.date))[0].date}`
              : "No snapshot yet"
          }
          icon={<Banknote className="h-4 w-4" />}
          accent="blue"
        />
        <KpiCard
          label="EMI Reserve (Protected)"
          value={formatter.format(fundedEmiReserve)}
          sub={
            fundedEmiReserve < emiReserve
              ? `Underfunded (Target: ${formatter.format(emiReserve)})`
              : "Always held back — cannot be allocated"
          }
          icon={<Target className="h-4 w-4" />}
          accent="rose"
        />
        <KpiCard
          label="Allocatable Balance"
          value={formatter.format(allocatableBalance)}
          sub="OD Balance minus EMI reserve"
          icon={<Layers3 className="h-4 w-4" />}
          accent="amber"
        />
        <KpiCard
          label={freeAllocatable >= 0 ? "Free to Allocate" : "Over-Allocated"}
          value={formatter.format(Math.abs(freeAllocatable))}
          sub={freeAllocatable >= 0 ? "Allocatable minus goal allocations" : "Allocations exceed allocatable balance"}
          icon={<CircleDollarSign className="h-4 w-4" />}
          accent={freeAllocatable >= 0 ? "emerald" : "rose"}
        />
      </section>

      {/* ── Balance Waterfall ───────────────────────────────────────────────── */}
      <section className="rounded-[32px] border border-slate-200 bg-white p-5 shadow-[0_12px_45px_rgba(15,23,42,0.05)]">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h3 className="text-lg font-semibold tracking-tight text-slate-950">Balance Waterfall</h3>
            <p className="mt-1 text-sm text-slate-500">How your OD balance is structured, reserved, and allocated.</p>
          </div>
          {/* Attribution status badge */}
          <div className={`flex-shrink-0 rounded-full border px-3 py-1 text-xs font-semibold ${
            Math.abs(attributionGap) < 0.5
              ? "border-emerald-100 bg-emerald-50 text-emerald-700"
              : attributionGap > 0
              ? "border-amber-100 bg-amber-50 text-amber-700"
              : "border-blue-100 bg-blue-50 text-blue-700"
          }`}>
            {Math.abs(attributionGap) < 0.5
              ? "✓ Fully attributed"
              : attributionGap > 0
              ? `${formatter.format(attributionGap)} unattributed`
              : `${formatter.format(-attributionGap)} excess contributions`}
          </div>
        </div>

        <div className="mt-5 space-y-2">
          {/* Row 1 — OD Balance */}
          <div className="flex items-center justify-between rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
            <div className="flex items-center gap-2">
              <div className="h-3 w-3 rounded-full bg-slate-400" />
              <p className="text-sm font-semibold text-slate-800">OD Balance</p>
              <p className="text-xs text-slate-400">{sortedOdLog[0] ? `as of ${sortedOdLog[0].date}` : ""}</p>
            </div>
            <p className="text-lg font-semibold text-slate-950">{formatter.format(latestOdBalance)}</p>
          </div>

          {/* Row 2 — EMI Reserve */}
          <div className="ml-4 flex items-center justify-between rounded-2xl border border-rose-100 bg-rose-50 px-4 py-3">
            <div className="flex items-center gap-2">
              <div className="h-3 w-3 rounded-full bg-rose-400" />
              <div>
                <p className="text-sm font-semibold text-rose-800">EMI Reserve <span className="ml-1 rounded-full bg-rose-200 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-rose-700">Protected</span></p>
                <p className="text-xs text-rose-400">
                  {fundedEmiReserve < emiReserve
                    ? `Underfunded by ${formatter.format(emiReserve - fundedEmiReserve)} — need deposits`
                    : "Always held back — covers full monthly EMI"}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex flex-col items-end">
                <p className="text-base font-semibold text-rose-900">
                  {formatter.format(fundedEmiReserve)}
                </p>
                {fundedEmiReserve < emiReserve && (
                  <p className="text-[10px] text-rose-600 font-medium leading-none mt-0.5">
                    Target: {formatter.format(emiReserve)}
                  </p>
                )}
              </div>
              {!editingEmiReserve ? (
                <div className="flex items-center gap-1.5">
                  {odData.emiReserveAllocated < emiReserve && (
                    <button
                      onClick={handleRefillEmiReserve}
                      disabled={emiReserveRefilling}
                      className="flex items-center gap-1 rounded-xl bg-rose-600 px-2.5 py-1.5 text-xs font-semibold text-white hover:bg-rose-700 disabled:opacity-60"
                    >
                      {emiReserveRefilling ? "..." : "Refill"}
                    </button>
                  )}
                  <button
                    onClick={() => { setEmiReserveInput(String(emiReserve)); setEmiReserveError(null); setEditingEmiReserve(true); }}
                    className="flex items-center gap-1 rounded-xl border border-rose-200 bg-white px-2.5 py-1.5 text-xs font-medium text-rose-700 hover:bg-rose-100"
                  >
                    <Pencil className="h-3 w-3" /> Edit
                  </button>
                </div>
              ) : (
                <div className="flex items-center gap-1.5">
                  <input
                    type="number"
                    min="0"
                    step="1"
                    value={emiReserveInput}
                    onChange={(e) => setEmiReserveInput(e.target.value)}
                    className="w-28 rounded-xl border border-rose-300 bg-white px-2.5 py-1.5 text-sm outline-none focus:border-rose-500 focus:ring-2 focus:ring-rose-100"
                    autoFocus
                    onKeyDown={(e) => { if (e.key === "Enter") handleSaveEmiReserve(); if (e.key === "Escape") setEditingEmiReserve(false); }}
                  />
                  <button
                    onClick={handleSaveEmiReserve}
                    disabled={emiReserveSaving}
                    className="rounded-xl bg-rose-700 px-2.5 py-1.5 text-xs font-semibold text-white hover:bg-rose-800 disabled:opacity-60"
                  >{emiReserveSaving ? "…" : "Save"}</button>
                  <button
                    onClick={() => setEditingEmiReserve(false)}
                    className="rounded-xl border border-slate-200 px-2.5 py-1.5 text-xs text-slate-500 hover:bg-slate-100"
                  >Cancel</button>
                </div>
              )}
            </div>
          </div>
          {emiReserveError && (
            <p className="ml-4 text-xs text-rose-600">{emiReserveError}</p>
          )}

          {/* Row 3 — Allocatable */}
          <div className="ml-4 flex items-center justify-between rounded-2xl border border-teal-100 bg-teal-50 px-4 py-3">
            <div className="flex items-center gap-2">
              <div className="h-3 w-3 rounded-full bg-teal-500" />
              <div>
                <p className="text-sm font-semibold text-teal-800">Allocatable Balance</p>
                <p className="text-xs text-teal-500">OD Balance minus EMI Reserve</p>
              </div>
            </div>
            <p className="text-base font-semibold text-teal-900">{formatter.format(allocatableBalance)}</p>
          </div>

          {/* Row 4 — Allocation progress bar */}
          <div className="ml-8 space-y-2 pb-1">
            <div className="flex justify-between text-xs text-slate-500">
              <span>Allocated to goals: <span className="font-semibold text-slate-800">{formatter.format(totalAllocatedToGoals)}</span></span>
              <span className={freeAllocatable < 0 ? "font-semibold text-rose-700" : "text-slate-500"}>
                {freeAllocatable >= 0 ? `Free: ${formatter.format(freeAllocatable)}` : `Over by: ${formatter.format(-freeAllocatable)}`}
              </span>
            </div>
            <div className="h-3 overflow-hidden rounded-full bg-slate-200">
              <div
                className={`h-full rounded-full transition-all duration-500 ${
                  isCriticalOverAllocation ? "bg-rose-600" : isOverAllocated ? "bg-amber-500" : "bg-teal-500"
                }`}
                style={{ width: `${Math.min(110, allocatableBalance > 0 ? (totalAllocatedToGoals / allocatableBalance) * 100 : 0)}%` }}
              />
            </div>
            <div className="flex justify-between text-[10px] text-slate-400">
              <span>₹0</span>
              <span>{formatter.format(allocatableBalance)} (max)</span>
            </div>
          </div>

          {/* Row 5 — Attribution */}
          <div className="border-t border-slate-100 pt-3">
            <div className="flex items-center justify-between px-1">
              <p className="text-xs text-slate-500">Contribution attribution</p>
              <p className="text-xs text-slate-600">
                <span className="font-semibold">{formatter.format(totalDeposited)}</span>
                {" attributed / "}
                <span className="font-semibold">{formatter.format(latestOdBalance)}</span>
                {" OD balance"}
              </p>
            </div>
            {Math.abs(attributionGap) > 0.5 && (
              <p className={`mt-1 px-1 text-xs font-medium ${
                attributionGap > 0 ? "text-amber-600" : "text-blue-600"
              }`}>
                {attributionGap > 0
                  ? `▲ ${formatter.format(attributionGap)} of your OD balance is not yet attributed to any contribution source. Log contributions to close this gap.`
                  : `▼ Your logged contributions exceed the OD balance by ${formatter.format(-attributionGap)}. This may reflect withdrawals not captured here.`}
              </p>
            )}
          </div>
        </div>
      </section>

      {/* ── Over-allocation banners ─────────────────────────────────────────── */}
      {isCriticalOverAllocation && (
        <div className="flex items-start gap-3 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3">
          <TriangleAlert className="mt-0.5 h-5 w-5 flex-shrink-0 text-rose-600" />
          <div>
            <p className="text-sm font-semibold text-rose-800">Critical: Goal allocations exceed total OD balance</p>
            <p className="mt-0.5 text-xs text-rose-600">
              Your goal allocations ({formatter.format(totalAllocatedToGoals)}) exceed the entire OD balance ({formatter.format(latestOdBalance)}),
              including the EMI reserve. The EMI buffer is fully consumed — the next EMI may not be covered. Please reduce your allocations immediately.
            </p>
          </div>
        </div>
      )}
      {isOverAllocated && !isCriticalOverAllocation && (
        <div className="flex items-start gap-3 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3">
          <TriangleAlert className="mt-0.5 h-5 w-5 flex-shrink-0 text-amber-600" />
          <div>
            <p className="text-sm font-semibold text-amber-800">Goal allocations exceed allocatable balance</p>
            <p className="mt-0.5 text-xs text-amber-600">
              Your goal allocations ({formatter.format(totalAllocatedToGoals)}) exceed the allocatable balance ({formatter.format(allocatableBalance)}).
              {" "}This encroaches on the EMI reserve by {formatter.format(totalAllocatedToGoals - allocatableBalance)}. Review your goal allocations.
            </p>
          </div>
        </div>
      )}

      {/* ── MoM Chart ──────────────────────────────────────────────────────── */}
      <Panel
        title="OD Balance Trend"
        subtitle="Month-on-month OD balance snapshots alongside cumulative deposits."
      >
        {mounted && momData.length > 0 ? (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={momData} margin={{ top: 12, right: 10, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="gradBalance" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#0f766e" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="#0f766e" stopOpacity={0.02} />
                  </linearGradient>
                  <linearGradient id="gradDeposited" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#2563eb" stopOpacity={0.15} />
                    <stop offset="95%" stopColor="#2563eb" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#64748b" }} minTickGap={24} />
                <YAxis tick={{ fontSize: 11, fill: "#64748b" }} width={64} tickFormatter={formatAxisShort} />
                <Tooltip
                  formatter={(val: unknown, name: unknown) => [
                    typeof val === "number" ? formatter.format(val) : String(val),
                    String(name),
                  ]}
                />
                <Legend />
                <Area type="monotone" dataKey="odBalance" name="OD Balance" stroke="#0f766e" fill="url(#gradBalance)" strokeWidth={2} connectNulls />
                <Area type="monotone" dataKey="cumDeposited" name="Cumulative Deposited" stroke="#2563eb" fill="url(#gradDeposited)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        ) : !mounted ? (
          <div className="h-64 animate-pulse rounded-2xl bg-slate-100" />
        ) : (
          <EmptyState message="No OD balance or contribution data yet. Add a balance snapshot or log a contribution to see the trend." />
        )}
      </Panel>

      {/* ── By Source + By Goal ──────────────────────────────────────────────── */}
      <section className="grid gap-5 lg:grid-cols-2">
        {/* By Source */}
        <Panel title="By Source" subtitle="Contribution breakdown by funding source.">
          {bySourceData.length > 0 ? (
            <div className="space-y-4">
              {mounted && (
                <div className="h-52">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={bySourceData}
                        dataKey="total"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        innerRadius={52}
                        outerRadius={84}
                        paddingAngle={3}
                        strokeWidth={0}
                      >
                        {bySourceData.map((_, i) => (
                          <Cell key={i} fill={SOURCE_PALETTE[i % SOURCE_PALETTE.length]} />
                        ))}
                      </Pie>
                      <Tooltip
                        formatter={(v: unknown, name: unknown) => [
                          typeof v === "number" ? formatter.format(v) : String(v),
                          String(name),
                        ]}
                      />
                      <Legend
                        iconType="circle"
                        iconSize={8}
                        formatter={(value) => <span style={{ fontSize: 11, color: "#64748b" }}>{value}</span>}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              )}
              <div className="space-y-2">
                {bySourceData.map((s, i) => {
                  const pct = totalDeposited > 0 ? (s.total / totalDeposited) * 100 : 0;
                  const color = SOURCE_PALETTE[i % SOURCE_PALETTE.length];
                  return (
                    <div key={s.sourceId} className="flex items-center gap-3 rounded-2xl border border-slate-100 bg-slate-50 px-3 py-2.5">
                      <div className="h-3 w-3 flex-shrink-0 rounded-full" style={{ backgroundColor: color }} />
                      <span className="flex-1 text-sm font-medium text-slate-800 truncate">{s.name}</span>
                      <span className="text-sm font-semibold text-slate-950">{formatter.format(s.total)}</span>
                      <span className="w-10 text-right text-xs text-slate-400">{pct.toFixed(1)}%</span>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            <EmptyState message="No contributions yet. Log a contribution to see the source breakdown." />
          )}
        </Panel>

        {/* By Goal */}
        <Panel title="By Goal" subtitle="Progress toward each savings target.">
          {activeGoals.length > 0 ? (
            <div className="space-y-3">

              {/* ── Goals Summary strip ───────────────────────────────── */}
              {(() => {
                const goalsWithAlloc = activeGoals.filter(g => g.allocatedAmount > 0);
                const metGoals = activeGoals.filter(g => g.allocatedAmount >= g.targetAmount);
                const pctCount = activeGoals.length > 0 ? Math.round((metGoals.length / activeGoals.length) * 100) : 0;
                const pctAmount = totalTargets > 0 ? Math.min(100, (totalAllocatedToGoals / totalTargets) * 100) : 0;
                const remaining = Math.max(0, totalTargets - totalAllocatedToGoals);
                return (
                  <div className="rounded-2xl border border-teal-100 bg-teal-50 px-4 py-3 space-y-3">
                    <div className="flex items-center justify-between">
                      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-teal-700">Goals Summary</p>
                      <span className="rounded-full bg-teal-100 px-2.5 py-0.5 text-[11px] font-bold text-teal-800">
                        {metGoals.length}/{activeGoals.length} met
                      </span>
                    </div>

                    {/* goal count badges */}
                    <div className="grid grid-cols-3 gap-2 text-center">
                      <div className="rounded-xl bg-white px-2 py-2 shadow-sm">
                        <p className="text-lg font-bold text-slate-950">{activeGoals.length}</p>
                        <p className="text-[10px] text-slate-400 leading-tight">Active Goals</p>
                      </div>
                      <div className="rounded-xl bg-white px-2 py-2 shadow-sm">
                        <p className="text-lg font-bold text-emerald-700">{metGoals.length}</p>
                        <p className="text-[10px] text-slate-400 leading-tight">Targets Met</p>
                      </div>
                      <div className="rounded-xl bg-white px-2 py-2 shadow-sm">
                        <p className="text-lg font-bold text-amber-600">{goalsWithAlloc.length}</p>
                        <p className="text-[10px] text-slate-400 leading-tight">Funded</p>
                      </div>
                    </div>

                    {/* Amount progress */}
                    <div className="space-y-1.5">
                      <div className="flex justify-between text-[11px] text-teal-700">
                        <span>{formatter.format(totalAllocatedToGoals)} funded</span>
                        <span className="font-semibold">{pctAmount.toFixed(1)}% of {formatter.format(totalTargets)}</span>
                      </div>
                      <div className="h-2 overflow-hidden rounded-full bg-teal-100">
                        <div
                          className="h-full rounded-full bg-teal-500 transition-all duration-700"
                          style={{ width: `${pctAmount}%` }}
                        />
                      </div>
                      {remaining > 0 && (
                        <p className="text-[10px] text-teal-600">{formatter.format(remaining)} remaining across all goals</p>
                      )}
                    </div>
                  </div>
                );
              })()}

              {/* Individual goal cards */}
              {activeGoals.map((g) => {
                const contributed = byGoalData.map.get(g.id) ?? 0;
                return (
                  <GoalProgressCard
                    key={g.id}
                    goal={g}
                    contributed={contributed}
                    freeAllocatable={freeAllocatable}
                    formatter={formatter}
                    onEdit={() => setModal({ type: "edit-goal", id: g.id })}
                  />
                );
              })}
              {freeAllocatable > 0 && (
                <div className="rounded-2xl border border-amber-100 bg-amber-50 px-4 py-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <TriangleAlert className="h-3.5 w-3.5 text-amber-600" />
                      <span className="text-sm font-semibold text-amber-800">Unallocated</span>
                    </div>
                    <span className="text-sm font-semibold text-amber-800">{formatter.format(freeAllocatable)}</span>
                  </div>
                  <p className="mt-1 text-xs text-amber-600">
                    This amount is in your OD balance but not assigned to any goal. Click &apos;Fund&apos; on a goal to allocate it.
                  </p>
                </div>
              )}
            </div>
          ) : (
            <EmptyState message="No goals defined. Add a savings goal to start tracking progress." />
          )}
        </Panel>
      </section>

      {/* ── Action Panel ────────────────────────────────────────────────────── */}
      <div className="flex flex-wrap gap-3">
        <ActionButton
          icon={<Plus className="h-4 w-4" />}
          label="Log Contribution"
          primary
          onClick={() => setModal({ type: "add-contribution" })}
        />
        <ActionButton
          icon={<Target className="h-4 w-4" />}
          label="Add Goal"
          onClick={() => setModal({ type: "add-goal" })}
        />
        <ActionButton
          icon={<Settings2 className="h-4 w-4" />}
          label="Manage Sources"
          onClick={() => setModal({ type: "sources" })}
        />
        <ActionButton
          icon={<Banknote className="h-4 w-4" />}
          label="Add OD Balance"
          onClick={() => setModal({ type: "add-od-balance" })}
        />
      </div>

      {/* ── OD Balance Log ──────────────────────────────────────────────────── */}
      <Panel title="OD Balance Log" subtitle="All balance snapshots with source and purpose annotations.">
        {sortedOdLog.length > 0 ? (
          <div className="overflow-hidden rounded-2xl border border-slate-200">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-slate-200 bg-slate-50 text-[11px] uppercase tracking-[0.18em] text-slate-500">
                  <tr>
                    <th className="px-4 py-3">Date</th>
                    <th className="px-4 py-3">Balance</th>
                                                                                                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {sortedOdLog.map((entry) => {
                    
                    return (
                      <tr key={entry.id} className="hover:bg-slate-50/80">
                        <td className="px-4 py-2.5 text-slate-600">{entry.date}</td>
                        <td className="px-4 py-2.5 font-semibold text-slate-950">{formatter.format(entry.balance)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <EmptyState message="No OD balance snapshots. Add one from here or via the Ledger screen." />
        )}
      </Panel>

      {/* ── Contribution Log ────────────────────────────────────────────────── */}
      <Panel title="Contribution Log" subtitle="All deposits and sources.">
        {sortedContributions.length > 0 ? (
          <div className="overflow-hidden rounded-2xl border border-slate-200">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50 text-[11px] uppercase tracking-[0.18em] text-slate-500">
                <tr>
                  <th className="px-4 py-3">Date</th>
                  <th className="px-4 py-3">Source</th>
                  <th className="px-4 py-3">Amount</th>
                  <th className="px-4 py-3">Note</th>
                  <th className="px-4 py-3 text-center">Edit</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {sortedContributions.map((c) => {
                  const src = odData.sources.find((s) => s.id === c.sourceId);
                  return (
                    <tr key={c.id}>
                      <td className="px-4 py-2.5 text-slate-600">{c.date}</td>
                      <td className="px-4 py-2.5 text-slate-800">{src?.name ?? <span className="italic text-slate-400">Unknown</span>}</td>
                      <td className="px-4 py-2.5 font-semibold text-slate-950">{formatter.format(c.amount)}</td>
                      <td className="px-4 py-2.5 text-xs text-slate-400">{c.note ?? "—"}</td>
                      <td className="px-4 py-2.5 text-center">
                        <button
                          onClick={() => setModal({ type: "edit-contribution", id: c.id })}
                          className="inline-flex items-center gap-1 rounded-xl border border-slate-200 px-2.5 py-1.5 text-xs font-medium text-slate-600 hover:border-teal-200 hover:text-teal-700"
                        >
                          <Pencil className="h-3 w-3" /> Edit
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState message="No contributions logged yet. Click 'Log Contribution' to add one." />
        )}
      </Panel>

      {/* ─────────────────────────────────────────────────────────────────────
          MODALS
      ───────────────────────────────────────────────────────────────────── */}

      {/* Add Contribution */}
      {modal.type === "add-contribution" && (
        <ContributionModal
          mode="add"
          sources={odData.sources.filter((s) => s.isActive)}
          goals={activeGoals}
          onClose={closeModal}
          onSave={async (payload) => {
            const res = await addContribution({ ...payload, id: newId() });
            if (!res.success) return res.error;
            showToast(
              res.overAllocated
                ? "Contribution saved — allocations exceed total amount."
                : "Contribution saved."
            );
            closeModal();
          }}
        />
      )}

      {/* Edit Contribution */}
      {modal.type === "edit-contribution" && (() => {
        const c = odData.contributions.find((x) => x.id === modal.id);
        if (!c) return null;
        return (
          <ContributionModal
            mode="edit"
            initial={c}
            sources={odData.sources.filter((s) => s.isActive)}
            goals={activeGoals}
            onClose={closeModal}
            onSave={async (payload) => {
              const res = await editContribution(c.id, payload);
              if (!res.success) return res.error;
              showToast(
                res.overAllocated
                  ? "Saved — allocations now exceed the contribution amount."
                  : "Contribution updated."
              );
              closeModal();
            }}
            auditHistory={c.editHistory}
          />
        );
      })()}

      {/* Add Goal */}
      {modal.type === "add-goal" && (
        <GoalModal
          mode="add"
          onClose={closeModal}
          onSave={async (payload) => {
            const res = await addGoal({ ...payload, id: newId() });
            if (!res.success) return res.error;
            showToast("Goal added.");
            closeModal();
          }}
        />
      )}

      {/* Edit Goal */}
      {modal.type === "edit-goal" && (() => {
        const g = odData.goals.find((x) => x.id === modal.id);
        if (!g) return null;
        return (
          <GoalModal
            mode="edit"
            initial={g}
            onClose={closeModal}
            onSave={async (payload) => {
              const res = await editGoal(g.id, payload);
              if (!res.success) return res.error;
              showToast("Goal updated.");
              closeModal();
            }}
            auditHistory={g.editHistory}
          />
        );
      })()}

      {/* Sources list */}
      {modal.type === "sources" && (
        <SourcesModal
          sources={odData.sources}
          onClose={closeModal}
          onAddSource={() => setModal({ type: "add-source" })}
          onEditSource={(id) => setModal({ type: "edit-source", id })}
        />
      )}

      {/* Add Source */}
      {modal.type === "add-source" && (
        <SourceFormModal
          mode="add"
          onClose={() => setModal({ type: "sources" })}
          onSave={async (payload) => {
            const res = await addSource({ ...payload, id: newId(), createdAt: new Date().toISOString(), name: payload.name ?? "", isActive: payload.isActive ?? true });
            if (!res.success) return res.error;
            showToast("Source added.");
            setModal({ type: "sources" });
          }}
        />
      )}

      {/* Edit Source */}
      {modal.type === "edit-source" && (() => {
        const s = odData.sources.find((x) => x.id === modal.id);
        if (!s) return null;
        return (
          <SourceFormModal
            mode="edit"
            initial={s}
            onClose={() => setModal({ type: "sources" })}
            onSave={async (payload) => {
              const res = await editSource(s.id, payload);
              if (!res.success) return res.error;
              showToast("Source updated.");
              setModal({ type: "sources" });
            }}
            auditHistory={s.editHistory}
          />
        );
      })()}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// SUB-COMPONENTS — Modals
// ─────────────────────────────────────────────────────────────────────────────

type ContributionPayload = Omit<OdContribution, "id" | "editHistory">;

function ContributionModal({
  mode,
  initial,
  sources,
  goals,
  onClose,
  onSave,
  auditHistory,
}: {
  mode: "add" | "edit";
  initial?: OdContribution;
  sources: OdSource[];
  goals: OdGoal[];
  onClose: () => void;
  onSave: (payload: ContributionPayload) => Promise<string | void>;
  auditHistory?: AuditRecord[];
}) {
  const [date, setDate] = useState(initial?.date ?? todayStr());
  const [amount, setAmount] = useState(initial ? String(initial.amount) : "");
  const [sourceId, setSourceId] = useState(initial?.sourceId ?? "");
  const [note, setNote] = useState(initial?.note ?? "");
  const [allocations, setAllocations] = useState<Array<{ goalId: string; amount: string }>>([]); // Kept unused just to avoid signature changes temporarily, but will be removed. Wait, no I can just remove it and pass undefined or nothing if it's not in the type anymore.

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function validate(): boolean {
    const e: Record<string, string> = {};
    if (!date) e.date = "Date is required";
    const ae = validatePositiveMoney(amount, "Amount");
    if (ae) e.amount = ae;
    if (!sourceId) e.sourceId = "Source is required";
    setErrors(e);
    return Object.keys(e).length === 0;
  }

  async function handleSave() {
    if (!validate()) return;
    setLoading(true);
    setSubmitError(null);
    const err = await onSave({
      date,
      amount: parseFloat(amount),
      sourceId,
      note: note || undefined,
    });
    setLoading(false);
    if (err) setSubmitError(err);
  }

  return (
    <FormModal title={mode === "add" ? "Log Contribution" : "Edit Contribution"} onClose={onClose}>
      <div className="space-y-4">
        {submitError && <ErrorBanner message={submitError} />}

        <div className="grid grid-cols-2 gap-3">
          <FormField label="Date" required error={errors.date}>
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className={inputCls(errors.date)}
            />
          </FormField>
          <FormField label="Amount (₹)" required error={errors.amount}>
            <input
              type="number"
              min="0.01"
              step="0.01"
              max="100000000"
              placeholder="0"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className={inputCls(errors.amount)}
            />
          </FormField>
        </div>

        <FormField label="Source" required error={errors.sourceId}>
          <select
            value={sourceId}
            onChange={(e) => setSourceId(e.target.value)}
            className={inputCls(errors.sourceId)}
          >
            <option value="">Select a source…</option>
            {sources.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
        </FormField>

        <FormField label="Note (optional)">
          <input
            type="text"
            placeholder="e.g. July salary surplus"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            className={inputCls()}
          />
        </FormField>



        <SubmitButton label={mode === "add" ? "Save Contribution" : "Update Contribution"} loading={loading} onClick={handleSave} />
        {auditHistory && auditHistory.length > 0 && <AuditTrail records={auditHistory} />}
      </div>
    </FormModal>
  );
}

// ── Goal Modal ───────────────────────────────────────────────────────────────

type GoalPayload = Omit<OdGoal, "id" | "editHistory">;

function GoalModal({
  mode,
  initial,
  onClose,
  onSave,
  auditHistory,
}: {
  mode: "add" | "edit";
  initial?: OdGoal;
  onClose: () => void;
  onSave: (payload: GoalPayload) => Promise<string | void>;
  auditHistory?: AuditRecord[];
}) {
  const [name, setName] = useState(initial?.name ?? "");
  const [targetAmount, setTargetAmount] = useState(initial ? String(initial.targetAmount) : "");
  const [allocatedAmount, setAllocatedAmount] = useState(initial ? String(initial.allocatedAmount) : "0");
  const [targetDate, setTargetDate] = useState(initial?.targetDate ?? "");
  const [color, setColor] = useState(initial?.color ?? GOAL_COLORS[0].value);
  const [note, setNote] = useState(initial?.note ?? "");
  const [isActive, setIsActive] = useState(initial?.isActive ?? true);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function validate(): boolean {
    const e: Record<string, string> = {};
    if (!name.trim()) e.name = "Goal name is required";
    const ae = validatePositiveMoney(targetAmount, "Target amount");
    if (ae) e.targetAmount = ae;
    const ae2 = validateNonNegativeMoney(allocatedAmount, "Allocated amount");
    if (ae2) e.allocatedAmount = ae2;
    setErrors(e);
    return Object.keys(e).length === 0;
  }

  async function handleSave() {
    if (!validate()) return;
    setLoading(true);
    setSubmitError(null);
    const err = await onSave({
      name: name.trim(),
      targetAmount: parseFloat(targetAmount),
      allocatedAmount: parseFloat(allocatedAmount),
      targetDate: targetDate || undefined,
      color,
      note: note || undefined,
      isActive,
    });
    setLoading(false);
    if (err) setSubmitError(err);
  }

  return (
    <FormModal title={mode === "add" ? "Add Goal" : "Edit Goal"} onClose={onClose}>
      <div className="space-y-4">
        {submitError && <ErrorBanner message={submitError} />}

        <FormField label="Goal Name" required error={errors.name}>
          <input
            type="text"
            placeholder="e.g. Construction – 20th Floor"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className={inputCls(errors.name)}
          />
        </FormField>

        <div className="grid grid-cols-2 gap-3">
          <FormField label="Target Amount (₹)" required error={errors.targetAmount}>
            <input
              type="number"
              min="0.01"
              step="0.01"
              max="100000000"
              placeholder="0"
              value={targetAmount}
              onChange={(e) => setTargetAmount(e.target.value)}
              className={inputCls(errors.targetAmount)}
            />
          </FormField>
          <FormField label="Allocated (Funded) (₹)" required error={errors.allocatedAmount}>
            <input
              type="number"
              min="0"
              step="0.01"
              max="100000000"
              placeholder="0"
              value={allocatedAmount}
              onChange={(e) => setAllocatedAmount(e.target.value)}
              className={inputCls(errors.allocatedAmount)}
            />
          </FormField>
        </div>

        <FormField label="Target Date (optional)">
          <input
            type="date"
            value={targetDate}
            onChange={(e) => setTargetDate(e.target.value)}
            className={inputCls()}
          />
        </FormField>


        <FormField label="Colour">
          <div className="flex flex-wrap gap-2 mt-1">
            {GOAL_COLORS.map(({ value, label }) => (
              <button
                key={value}
                type="button"
                title={label}
                onClick={() => setColor(value)}
                className={`h-8 w-8 rounded-full border-2 transition-transform hover:scale-110 ${color === value ? "border-slate-950 scale-110" : "border-transparent"}`}
                style={{ backgroundColor: value }}
              />
            ))}
          </div>
        </FormField>

        <FormField label="Note (optional)">
          <input
            type="text"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            className={inputCls()}
          />
        </FormField>

        {mode === "edit" && (
          <label className="flex items-center gap-3 cursor-pointer">
            <div
              onClick={() => setIsActive(!isActive)}
              className={`relative h-6 w-11 rounded-full transition-colors ${isActive ? "bg-teal-600" : "bg-slate-300"}`}
            >
              <div className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform ${isActive ? "translate-x-5" : "translate-x-0.5"}`} />
            </div>
            <span className="text-sm font-medium text-slate-700">{isActive ? "Active" : "Archived"}</span>
          </label>
        )}

        <SubmitButton label={mode === "add" ? "Save Goal" : "Update Goal"} loading={loading} onClick={handleSave} />
        {auditHistory && auditHistory.length > 0 && <AuditTrail records={auditHistory} />}
      </div>
    </FormModal>
  );
}

// ── Sources List Modal ───────────────────────────────────────────────────────

function SourcesModal({
  sources,
  onClose,
  onAddSource,
  onEditSource,
}: {
  sources: OdSource[];
  onClose: () => void;
  onAddSource: () => void;
  onEditSource: (id: string) => void;
}) {
  const active = sources.filter((s) => s.isActive);
  const archived = sources.filter((s) => !s.isActive);

  return (
    <FormModal title="Manage Sources" onClose={onClose}>
      <div className="space-y-4">
        <button
          onClick={onAddSource}
          className="flex w-full items-center justify-center gap-2 rounded-2xl border border-dashed border-teal-300 py-3 text-sm font-medium text-teal-700 hover:bg-teal-50"
        >
          <Plus className="h-4 w-4" /> Add New Source
        </button>

        {active.length > 0 && (
          <div className="space-y-2">
            <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-400">Active</p>
            {active.map((s) => (
              <div key={s.id} className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2.5">
                <div className="flex-1">
                  <p className="text-sm font-semibold text-slate-950">{s.name}</p>
                  {s.description && <p className="text-xs text-slate-400">{s.description}</p>}
                </div>
                <button
                  onClick={() => onEditSource(s.id)}
                  className="flex items-center gap-1 rounded-xl border border-slate-200 px-2.5 py-1.5 text-xs font-medium text-slate-600 hover:border-teal-200 hover:text-teal-700"
                >
                  <Pencil className="h-3 w-3" /> Edit
                </button>
              </div>
            ))}
          </div>
        )}

        {archived.length > 0 && (
          <div className="space-y-2">
            <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-400">Archived</p>
            {archived.map((s) => (
              <div key={s.id} className="flex items-center gap-3 rounded-2xl border border-slate-100 bg-slate-50/50 px-3 py-2.5 opacity-60">
                <div className="flex-1">
                  <p className="text-sm font-medium text-slate-600 line-through">{s.name}</p>
                </div>
                <button
                  onClick={() => onEditSource(s.id)}
                  className="flex items-center gap-1 rounded-xl border border-slate-200 px-2.5 py-1.5 text-xs font-medium text-slate-500 hover:border-teal-200 hover:text-teal-700"
                >
                  <Pencil className="h-3 w-3" /> Edit
                </button>
              </div>
            ))}
          </div>
        )}

        {sources.length === 0 && (
          <EmptyState message="No sources yet. Add one to start tracking contributions by source." />
        )}
      </div>
    </FormModal>
  );
}

// ── Source Form Modal ─────────────────────────────────────────────────────────

function SourceFormModal({
  mode,
  initial,
  onClose,
  onSave,
  auditHistory,
}: {
  mode: "add" | "edit";
  initial?: OdSource;
  onClose: () => void;
  onSave: (payload: Partial<Pick<OdSource, "name" | "description" | "isActive">>) => Promise<string | void>;
  auditHistory?: AuditRecord[];
}) {
  const [name, setName] = useState(initial?.name ?? "");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [isActive, setIsActive] = useState(initial?.isActive ?? true);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSave() {
    const e: Record<string, string> = {};
    if (!name.trim()) e.name = "Source name is required";
    setErrors(e);
    if (Object.keys(e).length) return;
    setLoading(true);
    setSubmitError(null);
    const err = await onSave({ name: name.trim(), description: description || undefined, isActive });
    setLoading(false);
    if (err) setSubmitError(err);
  }

  return (
    <FormModal title={mode === "add" ? "Add Source" : "Edit Source"} onClose={onClose}>
      <div className="space-y-4">
        {submitError && <ErrorBanner message={submitError} />}

        <FormField label="Source Name" required error={errors.name}>
          <input
            type="text"
            placeholder="e.g. Monthly Salary"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className={inputCls(errors.name)}
          />
        </FormField>
        <FormField label="Description (optional)">
          <input
            type="text"
            placeholder="e.g. Net salary credited on 1st of each month"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className={inputCls()}
          />
        </FormField>
        {mode === "edit" && (
          <label className="flex items-center gap-3 cursor-pointer">
            <div
              onClick={() => setIsActive(!isActive)}
              className={`relative h-6 w-11 rounded-full transition-colors ${isActive ? "bg-teal-600" : "bg-slate-300"}`}
            >
              <div className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform ${isActive ? "translate-x-5" : "translate-x-0.5"}`} />
            </div>
            <span className="text-sm font-medium text-slate-700">{isActive ? "Active" : "Archived"}</span>
          </label>
        )}
        <SubmitButton label={mode === "add" ? "Add Source" : "Update Source"} loading={loading} onClick={handleSave} />
        {auditHistory && auditHistory.length > 0 && <AuditTrail records={auditHistory} />}
      </div>
    </FormModal>
  );
}

// ── OD Balance Modal ─────────────────────────────────────────────────────────

function OdBalanceModal({
  sources,
  onClose,
  onSave,
}: {
  sources: OdSource[];
  onClose: () => void;
  onSave: (
    entry: { id: string; date: string; balance: number },
    annotation: Omit<OdBalanceAnnotation, "editHistory">
  ) => Promise<string | void>;
}) {
  const [date, setDate] = useState(todayStr());
  const [balance, setBalance] = useState("");
  const [sourceId, setSourceId] = useState("");
  const [purpose, setPurpose] = useState("savings");
  const [note, setNote] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSave() {
    const e: Record<string, string> = {};
    if (!date) e.date = "Date is required";
    const be = validateNonNegativeMoney(balance, "Balance");
    if (be) e.balance = be;
    setErrors(e);
    if (Object.keys(e).length) return;
    setLoading(true);
    setSubmitError(null);
    const err = await onSave(
      { id: newId(), date, balance: parseFloat(balance) },
      { odBalanceLogId: "", sourceId: sourceId || null, purpose: purpose || "savings", note: note || undefined }
    );
    setLoading(false);
    if (err) setSubmitError(err);
  }

  return (
    <FormModal title="Add OD Balance" onClose={onClose}>
      <div className="space-y-4">
        {submitError && <ErrorBanner message={submitError} />}

        <div className="grid grid-cols-2 gap-3">
          <FormField label="Date" required error={errors.date}>
            <input type="date" value={date} onChange={(e) => setDate(e.target.value)} className={inputCls(errors.date)} />
          </FormField>
          <FormField label="Balance (₹)" required error={errors.balance}>
            <input type="number" min="0" step="0.01" max="100000000" placeholder="0" value={balance} onChange={(e) => setBalance(e.target.value)} className={inputCls(errors.balance)} />
          </FormField>
        </div>

        <FormField label="Source (optional)">
          <select value={sourceId} onChange={(e) => setSourceId(e.target.value)} className={inputCls()}>
            <option value="">Unspecified</option>
            {sources.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        </FormField>

        <FormField label="Purpose">
          <input type="text" value={purpose} onChange={(e) => setPurpose(e.target.value)} className={inputCls()} placeholder="savings" />
        </FormField>

        <FormField label="Note (optional)">
          <input type="text" value={note} onChange={(e) => setNote(e.target.value)} className={inputCls()} />
        </FormField>

        <SubmitButton label="Save OD Balance" loading={loading} onClick={handleSave} />
      </div>
    </FormModal>
  );
}

// ── Annotation Modal ─────────────────────────────────────────────────────────

function AnnotationModal({
  entry,
  annotation,
  sources,
  onClose,
  onSave,
}: {
  entry: { id: string; date: string; balance: number };
  annotation?: OdBalanceAnnotation;
  sources: OdSource[];
  onClose: () => void;
  onSave: (patch: Partial<Pick<OdBalanceAnnotation, "sourceId" | "purpose" | "note">>) => Promise<string | void>;
}) {
  const [sourceId, setSourceId] = useState<string>(annotation?.sourceId ?? "");
  const [purpose, setPurpose] = useState(annotation?.purpose ?? "savings");
  const [note, setNote] = useState(annotation?.note ?? "");
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const fmt = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });

  async function handleSave() {
    setLoading(true);
    setSubmitError(null);
    const err = await onSave({ sourceId: sourceId || null, purpose: purpose || "savings", note: note || undefined });
    setLoading(false);
    if (err) setSubmitError(err);
  }

  return (
    <FormModal title="Edit OD Balance Annotation" onClose={onClose}>
      <div className="space-y-4">
        <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm">
          <div className="flex justify-between">
            <span className="text-slate-500">Date</span>
            <span className="font-medium text-slate-800">{entry.date}</span>
          </div>
          <div className="mt-1 flex justify-between">
            <span className="text-slate-500">Balance</span>
            <span className="font-semibold text-slate-950">{fmt.format(entry.balance)}</span>
          </div>
          <p className="mt-2 text-[11px] text-slate-400">The balance amount is immutable once posted. Only the annotation can be changed.</p>
        </div>

        {submitError && <ErrorBanner message={submitError} />}

        <FormField label="Source (optional)">
          <select value={sourceId} onChange={(e) => setSourceId(e.target.value)} className={inputCls()}>
            <option value="">Unspecified</option>
            {sources.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        </FormField>
        <FormField label="Purpose">
          <input type="text" value={purpose} onChange={(e) => setPurpose(e.target.value)} className={inputCls()} />
        </FormField>
        <FormField label="Note (optional)">
          <input type="text" value={note} onChange={(e) => setNote(e.target.value)} className={inputCls()} />
        </FormField>

        <SubmitButton label="Save Annotation" loading={loading} onClick={handleSave} />
        {annotation && annotation.editHistory.length > 0 && <AuditTrail records={annotation.editHistory} />}
      </div>
    </FormModal>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// SUB-COMPONENTS — Display
// ─────────────────────────────────────────────────────────────────────────────

function GoalProgressCard({
  goal,
  contributed,
  freeAllocatable,
  formatter,
  onEdit,
}: {
  goal: OdGoal;
  contributed: number;
  freeAllocatable: number;
  formatter: Intl.NumberFormat;
  onEdit: () => void;
}) {
  const pct = goal.targetAmount > 0 ? Math.min(100, (contributed / goal.targetAmount) * 100) : 0;
  const gap = goal.targetAmount - contributed;
  const met = contributed >= goal.targetAmount;

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
      <div className="flex items-center gap-2">
        <div className="h-3 w-3 flex-shrink-0 rounded-full" style={{ backgroundColor: goal.color }} />
        <p className="flex-1 text-sm font-semibold text-slate-950 truncate">{goal.name}</p>
        {goal.targetDate && (
          <span className="text-[10px] text-slate-400">by {goal.targetDate}</span>
        )}
        <div className="flex items-center gap-1.5">
          <button onClick={onEdit} className="flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2 py-1 text-[10px] font-medium text-slate-600 hover:border-teal-200 hover:text-teal-700 shadow-sm">
            <Pencil className="h-3 w-3" /> Edit
          </button>
          {(!met && freeAllocatable > 0) && (
            <button onClick={onEdit} className="flex items-center gap-1 rounded-lg bg-teal-600 px-2 py-1 text-[10px] font-semibold text-white hover:bg-teal-700 shadow-sm">
               Fund
            </button>
          )}
        </div>
      </div>
      <div className="mt-3">
        <div className="mb-1.5 flex justify-between text-xs text-slate-500">
          <span>{formatter.format(contributed)}</span>
          <span>{formatter.format(goal.targetAmount)}</span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-slate-200">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{ width: `${pct}%`, backgroundColor: goal.color }}
          />
        </div>
        <div className="mt-2 flex items-center justify-between">
          <span className="text-xs font-semibold" style={{ color: goal.color }}>
            {Math.round(pct)}%
          </span>
          {met ? (
            <span className="text-xs font-semibold text-emerald-700">✓ Target met</span>
          ) : (
            <span className="text-xs text-slate-500">₹{fmtShort(gap)} remaining</span>
          )}
        </div>
        {/* Headroom indicator */}
        {!met && (
          <div className={`mt-2 rounded-xl px-2.5 py-1.5 text-[10px] ${
            freeAllocatable > 0
              ? "bg-teal-50 text-teal-700"
              : "bg-amber-50 text-amber-700"
          }`}>
            {freeAllocatable > 0
              ? `Room to allocate: ${formatter.format(Math.min(freeAllocatable, gap))} more within reserve`
              : "No headroom — allocations already at or above reserve limit"}
          </div>
        )}
      </div>
    </div>
  );
}

function KpiCard({
  label,
  value,
  sub,
  icon,
  accent,
}: {
  label: string;
  value: string;
  sub: string;
  icon: ReactNode;
  accent: "teal" | "blue" | "amber" | "emerald" | "rose";
}) {
  const tones = {
    teal: "border-teal-100 bg-teal-50 text-teal-700",
    blue: "border-blue-100 bg-blue-50 text-blue-700",
    amber: "border-amber-100 bg-amber-50 text-amber-700",
    emerald: "border-emerald-100 bg-emerald-50 text-emerald-700",
    rose: "border-rose-100 bg-rose-50 text-rose-700",
  }[accent];
  return (
    <div className={`rounded-[24px] border p-4 shadow-[0_10px_24px_rgba(15,23,42,0.04)] ${tones}`}>
      <div className="flex items-center justify-between gap-2">
        <p className="text-[11px] font-semibold uppercase tracking-[0.2em] opacity-70">{label}</p>
        <div className="rounded-xl bg-white/80 p-2">{icon}</div>
      </div>
      <p className="mt-3 text-2xl font-semibold tracking-tight text-slate-950">{value}</p>
      <p className="mt-1 text-xs text-slate-500 leading-4">{sub}</p>
    </div>
  );
}

function Panel({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
}) {
  return (
    <section className="rounded-[32px] border border-slate-200 bg-white p-5 shadow-[0_12px_45px_rgba(15,23,42,0.05)]">
      <h3 className="text-lg font-semibold tracking-tight text-slate-950">{title}</h3>
      {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
      <div className="mt-4">{children}</div>
    </section>
  );
}

function ActionButton({
  icon,
  label,
  primary,
  onClick,
}: {
  icon: ReactNode;
  label: string;
  primary?: boolean;
  onClick: () => void;
}) {
  return primary ? (
    <button
      onClick={onClick}
      className="flex items-center gap-2 rounded-2xl bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-slate-200 transition-colors hover:bg-teal-700"
    >
      {icon} {label}
    </button>
  ) : (
    <button
      onClick={onClick}
      className="flex items-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 shadow-sm transition-colors hover:border-teal-200 hover:text-teal-700"
    >
      {icon} {label}
    </button>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-2xl border border-dashed border-slate-200 py-10 text-center">
      <ClipboardList className="h-6 w-6 text-slate-300" />
      <p className="max-w-xs text-sm text-slate-400">{message}</p>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// SHARED FORM PRIMITIVES
// ─────────────────────────────────────────────────────────────────────────────

function FormModal({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  const panelRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const panel = panelRef.current;
    if (!panel) return;
    const focusable = panel.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    first?.focus();
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") { e.preventDefault(); onClose(); return; }
      if (e.key !== "Tab" || !focusable.length) return;
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last?.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first?.focus(); }
    };
    document.body.style.overflow = "hidden";
    document.addEventListener("keydown", handleKey);
    return () => { document.body.style.overflow = ""; document.removeEventListener("keydown", handleKey); };
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 px-4 backdrop-blur-sm" onClick={onClose}>
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        className="relative max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-[28px] border border-slate-200 bg-[linear-gradient(180deg,#ffffff_0%,#f8fafc_100%)] p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <button onClick={onClose} className="absolute right-4 top-4 rounded-lg p-2 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700">
          <X className="h-4 w-4" />
        </button>
        <div className="mb-5 flex items-center gap-2">
          <PiggyBank className="h-4 w-4 text-teal-700" />
          <h3 className="text-base font-semibold tracking-tight text-slate-950">{title}</h3>
        </div>
        {children}
      </div>
    </div>
  );
}

function FormField({ label, error, required, children }: { label: string; error?: string; required?: boolean; children: ReactNode }) {
  return (
    <div>
      <label className="block text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
        {label}{required && <span className="ml-1 text-rose-500">*</span>}
      </label>
      <div className="mt-1.5">{children}</div>
      {error && <p className="mt-1 text-xs text-rose-600">{error}</p>}
    </div>
  );
}

function inputCls(error?: string): string {
  return `block w-full rounded-2xl border px-3 py-2.5 text-sm outline-none transition-colors ${
    error
      ? "border-rose-300 bg-rose-50 focus:border-rose-400 focus:ring-4 focus:ring-rose-100"
      : "border-slate-200 bg-white focus:border-teal-300 focus:ring-4 focus:ring-teal-100"
  }`;
}

function SubmitButton({ label, loading, onClick }: { label: string; loading: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={loading}
      className="w-full rounded-2xl bg-slate-950 px-4 py-3 text-sm font-semibold text-white transition-colors hover:bg-teal-700 disabled:opacity-60"
    >
      {loading ? "Saving…" : label}
    </button>
  );
}

function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-2xl border border-rose-200 bg-rose-50 px-3 py-2.5">
      <TriangleAlert className="mt-0.5 h-4 w-4 flex-shrink-0 text-rose-600" />
      <p className="text-sm text-rose-700">{message}</p>
    </div>
  );
}

function AuditTrail({ records }: { records: AuditRecord[] }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border-t border-slate-100 pt-4">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 text-xs font-medium text-slate-400 hover:text-slate-700"
      >
        <History className="h-3.5 w-3.5" />
        Edit history ({records.length} change{records.length !== 1 ? "s" : ""})
        {open ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
      </button>
      {open && (
        <div className="mt-2 space-y-1.5 rounded-2xl bg-slate-50 p-3 text-xs">
          {[...records].reverse().map((r, i) => (
            <div key={i} className="text-slate-600">
              <span className="text-slate-400">{new Date(r.timestamp).toLocaleString("en-IN")} — </span>
              <span className="font-medium">{r.field}</span>
              {" "}changed from{" "}
              <span className="font-mono text-slate-500">{r.oldValue}</span>
              {" "}to{" "}
              <span className="font-mono text-slate-800">{r.newValue}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
