"use client";

import { calculateMetrics, generateSchedule } from "@/lib/calculations";
import { AmortizationRow, Disbursement, LoanData, OdBalanceLog, Prepayment, RateHistory } from "@/lib/types";
import { useMemo, useState } from "react";
import {
  Banknote,
  Building2,
  Calculator,
  ClipboardList,
  Info,
  LucideIcon,
  Plus,
  Sparkles,
  Target,
  Trash2,
  TrendingUp,
  Wallet,
} from "lucide-react";

type ScenarioChange =
  | { type: "prepayment"; data: Prepayment }
  | { type: "rate"; data: RateHistory }
  | { type: "od"; data: OdBalanceLog }
  | { type: "disbursement"; data: Disbursement };

export default function SimulatorClient({ baseData, todayStr }: { baseData: LoanData; todayStr: string }) {
  const [changes, setChanges] = useState<ScenarioChange[]>([]);
  const [activeTab, setActiveTab] = useState<"prepayment" | "rate" | "od" | "disbursement">("prepayment");
  const [formDate, setFormDate] = useState("");
  const [formValue, setFormValue] = useState(0);

  const today = useMemo(() => {
    const date = new Date(todayStr);
    return new Date(date.getFullYear(), date.getMonth(), date.getDate());
  }, [todayStr]);

  const simulatedData = useMemo(() => {
    const data: LoanData = JSON.parse(JSON.stringify(baseData));
    changes.forEach((change) => {
      if (change.type === "prepayment") data.prepayments.push(change.data);
      if (change.type === "rate") data.rateHistory.push(change.data);
      if (change.type === "od") data.odBalanceLog.push(change.data);
      if (change.type === "disbursement") data.disbursements.push(change.data);
    });
    return data;
  }, [baseData, changes]);

  const baseSchedule = useMemo(() => generateSchedule(baseData, today), [baseData, today]);
  const baseMetrics = useMemo(() => calculateMetrics(baseData, baseSchedule, today), [baseData, baseSchedule, today]);
  const simSchedule = useMemo(() => generateSchedule(simulatedData, today), [simulatedData, today]);
  const simMetrics = useMemo(() => calculateMetrics(simulatedData, simSchedule, today), [simulatedData, simSchedule, today]);

  // Next 6 installments from today
  const next6Base = useMemo(() => {
    return baseSchedule.filter((row) => row.dueDate > todayStr).slice(0, 6);
  }, [baseSchedule, todayStr]);

  const next6Sim = useMemo(() => {
    return simSchedule.filter((row) => row.dueDate > todayStr).slice(0, 6);
  }, [simSchedule, todayStr]);

  const formatter = new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  });

  const interestSaved = baseMetrics.totalInterestProjected - simMetrics.totalInterestProjected;
  const closureShift = baseSchedule.length - simSchedule.length;

  // Disbursement validation
  const totalDisbursed = baseData.disbursements.reduce((s, d) => s + d.amount, 0);
  const sanctionedAmount = baseData.loanDetails.sanctionedAmount;
  const remainingDrawable = sanctionedAmount - totalDisbursed;
  const simDisbursementsTotal = changes
    .filter((c) => c.type === "disbursement")
    .reduce((s, c) => s + (c as { type: "disbursement"; data: Disbursement }).data.amount, 0);
  const wouldExceedLimit =
    activeTab === "disbursement" &&
    formValue > 0 &&
    totalDisbursed + simDisbursementsTotal + formValue > sanctionedAmount;
  const remainingAfterSim = remainingDrawable - simDisbursementsTotal;

  const hasDisbursementChanges = changes.some((c) => c.type === "disbursement");
  const simDisbursedTotal = totalDisbursed + simDisbursementsTotal;

  // OD savings & effective rate metrics
  const baseTotalOdSavings = baseSchedule.reduce((s, r) => s + r.interestSavings, 0);
  const simTotalOdSavings = simSchedule.reduce((s, r) => s + r.interestSavings, 0);
  const odSavingsDelta = simTotalOdSavings - baseTotalOdSavings;
  const nominalRate = baseData.rateHistory.length > 0 ? baseData.rateHistory[baseData.rateHistory.length - 1].annualRate : 0;
  const numberFormatter = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 });

  const addChange = () => {
    if (!formDate || formValue <= 0) return;
    if (wouldExceedLimit) return;

    const id = Math.random().toString(36).slice(2, 11);
    let newChange: ScenarioChange;

    if (activeTab === "prepayment") {
      newChange = { type: "prepayment", data: { id, date: formDate, amount: formValue } };
    } else if (activeTab === "rate") {
      newChange = { type: "rate", data: { id, effectiveDate: formDate, annualRate: formValue } };
    } else if (activeTab === "od") {
      newChange = { type: "od", data: { id, date: formDate, balance: formValue } };
    } else {
      newChange = { type: "disbursement", data: { id, date: formDate, amount: formValue } };
    }

    setChanges((current) => [...current, newChange]);
    setFormDate("");
    setFormValue(0);
  };

  const sortedChanges = [...changes].sort((left, right) => {
    const leftDate = left.type === "rate" ? left.data.effectiveDate : left.data.date;
    const rightDate = right.type === "rate" ? right.data.effectiveDate : right.data.date;
    return leftDate.localeCompare(rightDate);
  });

  const valueLabel = () => {
    if (activeTab === "rate") return "New Rate (%)";
    if (activeTab === "od") return "New Balance (INR)";
    return "Amount (INR)";
  };

  const valuePlaceholder = () => {
    if (activeTab === "rate") return "e.g. 7.85";
    if (activeTab === "disbursement") return "e.g. 1500000";
    return "e.g. 500000";
  };

  return (
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-12">
      <div className="space-y-5 lg:col-span-4">
        <section className="rounded-[28px] border border-slate-200 bg-white p-5 shadow-[0_12px_45px_rgba(15,23,42,0.05)]">
          <div className="flex items-center gap-2">
            <Plus className="h-4 w-4 text-teal-700" />
            <h3 className="text-base font-semibold tracking-tight text-slate-950">Scenario Inputs</h3>
          </div>
          <p className="mt-1 text-sm text-slate-600">Layer hypothetical changes on top of the current schedule engine. No saved loan records are modified.</p>

          <div className="mt-4 grid grid-cols-2 gap-1 rounded-2xl border border-slate-200 bg-slate-50 p-1">
            <TabButton active={activeTab === "prepayment"} onClick={() => setActiveTab("prepayment")} label="Prepay" icon={Banknote} />
            <TabButton active={activeTab === "rate"} onClick={() => setActiveTab("rate")} label="Rate" icon={TrendingUp} />
            <TabButton active={activeTab === "od"} onClick={() => setActiveTab("od")} label="OD Bal" icon={Wallet} />
            <TabButton active={activeTab === "disbursement"} onClick={() => setActiveTab("disbursement")} label="Disburse" icon={Building2} />
          </div>

          {/* Disbursement info chip */}
          {activeTab === "disbursement" && (
            <div className="mt-4 rounded-2xl border border-violet-100 bg-violet-50 px-4 py-3">
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-violet-600">Sanctioned Limit</p>
              <div className="mt-2 space-y-1">
                <div className="flex justify-between text-xs text-slate-600">
                  <span>Disbursed (actual)</span>
                  <span className="font-semibold">{formatter.format(totalDisbursed)}</span>
                </div>
                {simDisbursementsTotal > 0 && (
                  <div className="flex justify-between text-xs text-violet-700">
                    <span>Simulated additions</span>
                    <span className="font-semibold">+ {formatter.format(simDisbursementsTotal)}</span>
                  </div>
                )}
                <div className="my-1.5 border-t border-violet-100" />
                <div className="flex justify-between text-xs text-slate-600">
                  <span>Remaining drawable</span>
                  <span className={`font-semibold ${remainingAfterSim <= 0 ? "text-rose-600" : "text-emerald-700"}`}>
                    {formatter.format(Math.max(0, remainingAfterSim))}
                  </span>
                </div>
                <div className="flex justify-between text-xs text-slate-400">
                  <span>of {formatter.format(sanctionedAmount)} sanctioned</span>
                </div>
              </div>
            </div>
          )}

          <div className="mt-4 space-y-4">
            <div>
              <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Effective date</label>
              <input
                type="date"
                value={formDate}
                onChange={(event) => setFormDate(event.target.value)}
                className="w-full rounded-2xl border border-slate-200 bg-white px-3 py-3 text-sm shadow-sm outline-none transition-colors focus:border-teal-300 focus:ring-4 focus:ring-teal-100"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                {valueLabel()}
              </label>
              <input
                type="number"
                step={activeTab === "rate" ? "0.01" : "1"}
                value={formValue || ""}
                onChange={(event) => setFormValue(Number(event.target.value))}
                placeholder={valuePlaceholder()}
                className={`w-full rounded-2xl border bg-white px-3 py-3 text-sm shadow-sm outline-none transition-colors focus:ring-4 ${
                  wouldExceedLimit
                    ? "border-rose-300 focus:border-rose-300 focus:ring-rose-100"
                    : "border-slate-200 focus:border-teal-300 focus:ring-teal-100"
                }`}
              />
              {wouldExceedLimit && (
                <p className="mt-1.5 text-[11px] font-semibold text-rose-600">
                  Exceeds sanctioned limit. Max drawable: {formatter.format(Math.max(0, remainingAfterSim))}
                </p>
              )}
            </div>
            <button
              onClick={addChange}
              disabled={wouldExceedLimit || !formDate || formValue <= 0}
              className="flex w-full items-center justify-center gap-2 rounded-2xl bg-slate-950 py-3 text-sm font-semibold text-white shadow-lg shadow-slate-200 transition-colors hover:bg-teal-700 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <Sparkles className="h-4 w-4" />
              Add to Scenario
            </button>
          </div>
        </section>

        <section className="rounded-[28px] border border-slate-200 bg-white p-5 shadow-[0_12px_45px_rgba(15,23,42,0.05)]">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h3 className="text-base font-semibold tracking-tight text-slate-950">Scenario Timeline</h3>
              <p className="mt-1 text-sm text-slate-600">Ordered list of the assumptions currently being applied.</p>
            </div>
            {changes.length > 0 ? (
              <button
                onClick={() => setChanges([])}
                className="text-[10px] font-semibold uppercase tracking-[0.16em] text-rose-500 transition-colors hover:text-rose-600"
              >
                Clear all
              </button>
            ) : null}
          </div>

          <div className="mt-4 space-y-3">
            {sortedChanges.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-5 text-sm text-slate-500">
                Add a prepayment, rate change, OD balance, or disbursement to start a scenario.
              </div>
            ) : (
              sortedChanges.map((change, index) => {
                const colorMap = {
                  prepayment: "bg-emerald-100 text-emerald-700",
                  rate: "bg-blue-100 text-blue-700",
                  od: "bg-amber-100 text-amber-700",
                  disbursement: "bg-violet-100 text-violet-700",
                };
                const labelMap = {
                  prepayment: "Prepayment",
                  rate: "Rate Change",
                  od: "OD Adjustment",
                  disbursement: "Disbursement",
                };
                const dateStr = change.type === "rate" ? change.data.effectiveDate : change.data.date;
                const valueStr =
                  change.type === "rate"
                    ? `${change.data.annualRate}%`
                    : formatter.format(
                        change.type === "prepayment"
                          ? change.data.amount
                          : change.type === "od"
                            ? change.data.balance
                            : change.data.amount,
                      );
                return (
                  <div key={index} className="group flex items-center justify-between rounded-2xl border border-slate-200 bg-slate-50 px-3 py-3">
                    <div className="flex items-center gap-3">
                      <div className={`rounded-xl p-2 ${colorMap[change.type]}`}>
                        {change.type === "prepayment" ? (
                          <Banknote className="h-4 w-4" />
                        ) : change.type === "rate" ? (
                          <TrendingUp className="h-4 w-4" />
                        ) : change.type === "od" ? (
                          <Wallet className="h-4 w-4" />
                        ) : (
                          <Building2 className="h-4 w-4" />
                        )}
                      </div>
                      <div>
                        <p className="text-xs font-semibold text-slate-950">{labelMap[change.type]}</p>
                        <p className="mt-0.5 text-[11px] text-slate-500">
                          {dateStr} • {valueStr}
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={() => setChanges((current) => current.filter((item) => item !== change))}
                      className="rounded-lg p-1 text-slate-300 opacity-0 transition-all hover:bg-white hover:text-rose-500 group-hover:opacity-100"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                );
              })
            )}
          </div>
        </section>
      </div>

      <div className="space-y-5 lg:col-span-8">
        {/* Hero banner */}
        <section className="relative overflow-hidden rounded-[32px] border border-slate-200 bg-[linear-gradient(135deg,#0f172a_0%,#134e4a_100%)] p-6 text-white shadow-[0_20px_60px_rgba(15,23,42,0.22)] md:p-7">
          <div className="absolute right-0 top-0 p-8 opacity-10">
            <Calculator className="h-28 w-28" />
          </div>
          <div className="relative z-10 flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-teal-100">
                {interestSaved >= 0 ? "Total Interest Savings" : "Total Interest Increase"}
              </p>
              <p className="mt-3 text-4xl font-semibold tracking-tight md:text-5xl">{formatter.format(Math.abs(interestSaved))}</p>
              <p className="mt-2 text-sm text-slate-200">
                Compared against the current projection using your present data and loan policy.
              </p>
              {hasDisbursementChanges && (
                <p className="mt-1.5 text-xs text-violet-300">
                  Includes {formatter.format(simDisbursementsTotal)} in simulated disbursements
                </p>
              )}
              {odSavingsDelta !== 0 && changes.length > 0 && (
                <p className={`mt-1 text-xs ${odSavingsDelta > 0 ? "text-emerald-300" : "text-amber-300"}`}>
                  OD savings shift: {formatter.format(Math.abs(odSavingsDelta))} {odSavingsDelta > 0 ? "more" : "less"} projected savings from OD offset
                </p>
              )}
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <HeroInfo
                label="New projected closure"
                value={simMetrics.projectedClosureDate}
                helper={`${simSchedule.length} months remaining`}
              />
              <HeroInfo
                label="Tenure movement"
                value={closureShift === 0 ? "Unchanged" : `${Math.abs(closureShift)} months`}
                helper={closureShift >= 0 ? "Earlier than baseline" : "Longer than baseline"}
              />
            </div>
          </div>
        </section>

        {/* Comparison cards */}
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <ComparisonCard
            title="Total Interest Payable"
            base={formatter.format(baseMetrics.totalInterestProjected)}
            sim={formatter.format(simMetrics.totalInterestProjected)}
            isBetter={simMetrics.totalInterestProjected < baseMetrics.totalInterestProjected}
          />
          <ComparisonCard
            title="Loan Tenure"
            base={`${baseSchedule.length} months`}
            sim={`${simSchedule.length} months`}
            isBetter={simSchedule.length < baseSchedule.length}
          />
          <ComparisonCard
            title="Projected EMI"
            base={formatter.format(baseMetrics.projectedEmi)}
            sim={formatter.format(simMetrics.projectedEmi)}
            isBetter={simMetrics.projectedEmi <= baseMetrics.projectedEmi}
            subtext="Post-moratorium estimate"
          />
          <ComparisonCard
            title="Effective Rate"
            base={`${numberFormatter.format(baseMetrics.effectiveInterestRate)}%`}
            sim={`${numberFormatter.format(simMetrics.effectiveInterestRate)}%`}
            isBetter={simMetrics.effectiveInterestRate < baseMetrics.effectiveInterestRate}
            subtext={`vs ${numberFormatter.format(nominalRate)}% nominal`}
          />
          <ComparisonCard
            title="Total Disbursed"
            base={`${formatter.format(totalDisbursed)}`}
            sim={`${formatter.format(simDisbursedTotal)}`}
            isBetter={false}
            isNeutralOverride={simDisbursedTotal === totalDisbursed}
            subtext={`of ${formatter.format(sanctionedAmount)} sanctioned`}
          />
          <ComparisonCard
            title="OD Savings (Projected)"
            base={formatter.format(baseTotalOdSavings)}
            sim={formatter.format(simTotalOdSavings)}
            isBetter={simTotalOdSavings > baseTotalOdSavings}
            subtext="Lifetime interest avoided via OD offset"
          />
          <div className="rounded-[24px] border border-slate-200 bg-slate-50 p-4 md:col-span-2">
            <div className="flex items-center gap-2">
              <Target className="h-4 w-4 text-teal-700" />
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Policy note</p>
            </div>
            <p className="mt-3 text-sm leading-6 text-slate-600">
              Simulated results respect your selected `Fixed EMI` or `Fixed Tenure` behavior from settings.
            </p>
          </div>
        </div>

        {/* Next 6 Installments Preview */}
        <Next6Preview baseRows={next6Base} simRows={next6Sim} formatter={formatter} hasChanges={changes.length > 0} />

        {/* Guidance */}
        <section className="rounded-[28px] border border-slate-200 bg-white p-5 shadow-[0_12px_45px_rgba(15,23,42,0.05)]">
          <div className="flex items-center gap-2">
            <Info className="h-4 w-4 text-teal-700" />
            <h3 className="text-base font-semibold tracking-tight text-slate-950">Scenario Guidance</h3>
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <GuidanceCard title="Prepayments" body="Useful for one-time lump sum reductions or recurring manual overpayments." />
            <GuidanceCard title="Rate changes" body="Simulate repricing risk without editing the base account history." />
            <GuidanceCard title="OD balances" body="Model how cash parked in OD changes effective principal and interest cost." />
            <GuidanceCard title="Disbursements" body="Simulate future tranches from your builder to see the impact on interest cost and loan tenure before the money is drawn." />
          </div>
        </section>
      </div>
    </div>
  );
}

// ─── Sub-components ────────────────────────────────────────────────────────────

function TabButton({
  active,
  onClick,
  label,
  icon: Icon,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
  icon: LucideIcon;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex flex-1 items-center justify-center rounded-xl px-3 py-2 text-[10px] font-black uppercase tracking-wider transition-all ${
        active ? "bg-white text-teal-700 shadow-sm" : "text-slate-500 hover:text-slate-700"
      }`}
    >
      <Icon className="mr-2 h-3 w-3" />
      {label}
    </button>
  );
}

function ComparisonCard({
  title,
  base,
  sim,
  isBetter,
  subtext,
  isNeutralOverride,
}: {
  title: string;
  base: string;
  sim: string;
  isBetter: boolean;
  subtext?: string;
  isNeutralOverride?: boolean;
}) {
  const isNeutral = isNeutralOverride ?? base === sim;

  return (
    <div className="rounded-[24px] border border-slate-200 bg-white p-4 shadow-[0_12px_45px_rgba(15,23,42,0.05)]">
      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">{title}</p>
      <div className="mt-4 space-y-3">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400">Current</p>
          <p className="mt-1 text-sm font-semibold text-slate-950">{base}</p>
        </div>
        <div>
          <div className="flex items-center gap-2">
            <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400">Scenario</p>
            <span
              className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.16em] ${
                isNeutral
                  ? "bg-slate-100 text-slate-600"
                  : isBetter
                    ? "bg-emerald-50 text-emerald-700"
                    : "bg-amber-50 text-amber-700"
              }`}
            >
              {isNeutral ? "Same" : isBetter ? "Better" : "Higher"}
            </span>
          </div>
          <p className="mt-1 text-base font-semibold text-slate-950">{sim}</p>
        </div>
      </div>
      {subtext ? <p className="mt-3 text-xs text-slate-500">{subtext}</p> : null}
    </div>
  );
}

function HeroInfo({ label, value, helper }: { label: string; value: string; helper: string }) {
  return (
    <div className="rounded-2xl bg-white/8 px-4 py-3 ring-1 ring-white/10">
      <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-teal-100">{label}</p>
      <p className="mt-1.5 text-lg font-semibold text-white">{value}</p>
      <p className="mt-1 text-xs text-slate-200">{helper}</p>
    </div>
  );
}

function GuidanceCard({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
      <p className="text-sm font-semibold text-slate-950">{title}</p>
      <p className="mt-1.5 text-sm leading-6 text-slate-600">{body}</p>
    </div>
  );
}

function Next6Preview({
  baseRows,
  simRows,
  formatter,
  hasChanges,
}: {
  baseRows: AmortizationRow[];
  simRows: AmortizationRow[];
  formatter: Intl.NumberFormat;
  hasChanges: boolean;
}) {
  const baseTotalOutflow = baseRows.reduce((s, r) => s + r.installment, 0);
  const simTotalOutflow = simRows.reduce((s, r) => s + r.installment, 0);
  const totalDelta = simTotalOutflow - baseTotalOutflow;

  const baseTotalOdSaved = baseRows.reduce((s, r) => s + r.interestSavings, 0);
  const simTotalOdSaved = simRows.reduce((s, r) => s + r.interestSavings, 0);
  const odSavingsDelta = simTotalOdSaved - baseTotalOdSaved;

  const formatMonth = (dueDate: string) => {
    const [year, month] = dueDate.split("-");
    const date = new Date(Number(year), Number(month) - 1, 1);
    return date.toLocaleString("en-IN", { month: "short", year: "numeric" });
  };

  return (
    <section className="rounded-[28px] border border-slate-200 bg-white p-5 shadow-[0_12px_45px_rgba(15,23,42,0.05)]">
      <div className="flex items-center gap-2">
        <ClipboardList className="h-4 w-4 text-teal-700" />
        <h3 className="text-base font-semibold tracking-tight text-slate-950">Next 6 Installments</h3>
      </div>
      <p className="mt-1 text-sm text-slate-600">Near-term cash flow impact of your scenario.</p>

      {!hasChanges && (
        <p className="mt-3 text-xs text-slate-400 italic">Add a scenario change above to see the per-installment impact.</p>
      )}

      <div className="mt-4 overflow-auto rounded-2xl border border-slate-200">
        <table className="w-full text-left text-xs">
          <thead className="border-b border-slate-200 bg-slate-50 text-[10px] uppercase tracking-[0.16em] text-slate-500">
            <tr>
              <th className="px-3 py-2.5">Due</th>
              <th className="px-3 py-2.5">Phase</th>
              <th className="px-3 py-2.5 text-slate-400">Current Instl.</th>
              <th className="px-3 py-2.5 text-slate-400">Current Int.</th>
              <th className="px-3 py-2.5 text-slate-400">Current Princ.</th>
              <th className="px-3 py-2.5 text-emerald-600">OD Saved</th>
              <th className="px-3 py-2.5 border-l border-slate-200 text-slate-700">Scenario Instl.</th>
              <th className="px-3 py-2.5 text-slate-700">Scenario Int.</th>
              <th className="px-3 py-2.5 text-slate-700">Scenario Princ.</th>
              <th className="px-3 py-2.5 text-emerald-700">OD Saved</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {baseRows.map((baseRow, i) => {
              const simRow = simRows[i] ?? null;
              const installmentDelta = simRow ? simRow.installment - baseRow.installment : null;
              const odSavedDelta = simRow ? simRow.interestSavings - baseRow.interestSavings : null;
              const isClosed = simRow === null;

              return (
                <tr key={baseRow.dueDate} className={`${isClosed ? "bg-emerald-50" : "hover:bg-slate-50/70"}`}>
                  {/* Due date */}
                  <td className="px-3 py-2.5 font-medium text-slate-700">{formatMonth(baseRow.dueDate)}</td>
                  {/* Phase badge */}
                  <td className="px-3 py-2.5">
                    <span
                      className={`inline-flex rounded-full px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider ${
                        baseRow.phase === "moratorium"
                          ? "bg-slate-100 text-slate-500"
                          : "bg-teal-50 text-teal-700"
                      }`}
                    >
                      {baseRow.phase === "moratorium" ? "Morat." : "EMI"}
                    </span>
                  </td>
                  {/* Base columns */}
                  <td className="px-3 py-2.5 text-slate-500">{formatter.format(baseRow.installment)}</td>
                  <td className="px-3 py-2.5 text-slate-500">{formatter.format(baseRow.interest)}</td>
                  <td className="px-3 py-2.5 text-slate-500">{formatter.format(baseRow.principal)}</td>
                  <td className="px-3 py-2.5 text-emerald-600">{formatter.format(baseRow.interestSavings)}</td>
                  {/* Sim columns */}
                  {isClosed ? (
                    <td colSpan={4} className="px-3 py-2.5 text-center text-[10px] font-semibold text-emerald-700">
                      Loan closed 🎉
                    </td>
                  ) : (
                    <>
                      <td className="border-l border-slate-200 px-3 py-2.5">
                        <div className="flex items-center gap-1.5">
                          <span className="font-semibold text-slate-950">{formatter.format(simRow.installment)}</span>
                          {installmentDelta !== null && installmentDelta !== 0 && (
                            <span
                              className={`text-[10px] font-bold ${
                                installmentDelta > 0 ? "text-amber-600" : "text-emerald-600"
                              }`}
                            >
                              {installmentDelta > 0 ? "↑" : "↓"} {formatter.format(Math.abs(installmentDelta))}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-3 py-2.5 text-slate-700">{formatter.format(simRow.interest)}</td>
                      <td className="px-3 py-2.5 text-slate-700">{formatter.format(simRow.principal)}</td>
                      <td className="px-3 py-2.5">
                        <div className="flex items-center gap-1.5">
                          <span className="font-semibold text-emerald-700">{formatter.format(simRow.interestSavings)}</span>
                          {odSavedDelta !== null && odSavedDelta !== 0 && (
                            <span
                              className={`text-[10px] font-bold ${
                                odSavedDelta > 0 ? "text-emerald-600" : "text-amber-600"
                              }`}
                            >
                              {odSavedDelta > 0 ? "↑" : "↓"} {formatter.format(Math.abs(odSavedDelta))}
                            </span>
                          )}
                        </div>
                      </td>
                    </>
                  )}
                </tr>
              );
            })}
          </tbody>
          <tfoot className="border-t border-slate-200 bg-slate-50 text-[10px]">
            <tr>
              <td colSpan={2} className="px-3 py-2.5 font-semibold uppercase tracking-[0.14em] text-slate-500">
                6-Month Total
              </td>
              <td className="px-3 py-2.5 font-semibold text-slate-600">{formatter.format(baseTotalOutflow)}</td>
              <td colSpan={2} className="px-3 py-2.5 text-slate-400">outflow</td>
              <td className="px-3 py-2.5 font-semibold text-emerald-600">{formatter.format(baseTotalOdSaved)}</td>
              <td className="border-l border-slate-200 px-3 py-2.5 font-semibold text-slate-950">
                {formatter.format(simTotalOutflow)}
              </td>
              <td colSpan={2} className="px-3 py-2.5">
                {totalDelta === 0 ? (
                  <span className="text-slate-400">Same as current</span>
                ) : (
                  <span className={`font-bold ${totalDelta > 0 ? "text-amber-600" : "text-emerald-600"}`}>
                    {totalDelta > 0 ? "▲" : "▼"} {formatter.format(Math.abs(totalDelta))}{" "}
                    {totalDelta > 0 ? "more" : "less"}
                  </span>
                )}
              </td>
              <td className="px-3 py-2.5">
                {odSavingsDelta === 0 ? (
                  <span className="text-slate-400">Same</span>
                ) : (
                  <span className={`font-bold ${odSavingsDelta > 0 ? "text-emerald-600" : "text-amber-600"}`}>
                    {odSavingsDelta > 0 ? "▲" : "▼"} {formatter.format(Math.abs(odSavingsDelta))}
                  </span>
                )}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    </section>
  );
}
