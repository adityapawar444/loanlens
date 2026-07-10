"use client";

import { calculateMetrics, generateSchedule } from "@/lib/calculations";
import { LoanData, OdBalanceLog, Prepayment, RateHistory } from "@/lib/types";
import { useMemo, useState } from "react";
import {
  Banknote,
  Calculator,
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
  | { type: "od"; data: OdBalanceLog };

export default function SimulatorClient({ baseData, todayStr }: { baseData: LoanData; todayStr: string }) {
  const [changes, setChanges] = useState<ScenarioChange[]>([]);
  const [activeTab, setActiveTab] = useState<"prepayment" | "rate" | "od">("prepayment");
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
    });
    return data;
  }, [baseData, changes]);

  const baseSchedule = useMemo(() => generateSchedule(baseData, today), [baseData, today]);
  const baseMetrics = useMemo(() => calculateMetrics(baseData, baseSchedule, today), [baseData, baseSchedule, today]);
  const simSchedule = useMemo(() => generateSchedule(simulatedData, today), [simulatedData, today]);
  const simMetrics = useMemo(() => calculateMetrics(simulatedData, simSchedule, today), [simulatedData, simSchedule, today]);

  const formatter = new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  });

  const interestSaved = baseMetrics.totalInterestProjected - simMetrics.totalInterestProjected;
  const closureShift = baseSchedule.length - simSchedule.length;

  const addChange = () => {
    if (!formDate || formValue <= 0) return;

    const id = Math.random().toString(36).slice(2, 11);
    let newChange: ScenarioChange;

    if (activeTab === "prepayment") {
      newChange = { type: "prepayment", data: { id, date: formDate, amount: formValue } };
    } else if (activeTab === "rate") {
      newChange = { type: "rate", data: { id, effectiveDate: formDate, annualRate: formValue } };
    } else {
      newChange = { type: "od", data: { id, date: formDate, balance: formValue } };
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

  return (
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-12">
      <div className="space-y-5 lg:col-span-4">
        <section className="rounded-[28px] border border-slate-200 bg-white p-5 shadow-[0_12px_45px_rgba(15,23,42,0.05)]">
          <div className="flex items-center gap-2">
            <Plus className="h-4 w-4 text-teal-700" />
            <h3 className="text-base font-semibold tracking-tight text-slate-950">Scenario Inputs</h3>
          </div>
          <p className="mt-1 text-sm text-slate-600">Layer hypothetical changes on top of the current schedule engine. No saved loan records are modified.</p>

          <div className="mt-4 flex rounded-2xl border border-slate-200 bg-slate-50 p-1">
            <TabButton active={activeTab === "prepayment"} onClick={() => setActiveTab("prepayment")} label="Prepay" icon={Banknote} />
            <TabButton active={activeTab === "rate"} onClick={() => setActiveTab("rate")} label="Rate" icon={TrendingUp} />
            <TabButton active={activeTab === "od"} onClick={() => setActiveTab("od")} label="OD Bal" icon={Wallet} />
          </div>

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
                {activeTab === "prepayment" ? "Amount (INR)" : activeTab === "rate" ? "New Rate (%)" : "New Balance (INR)"}
              </label>
              <input
                type="number"
                step={activeTab === "rate" ? "0.01" : "1"}
                value={formValue || ""}
                onChange={(event) => setFormValue(Number(event.target.value))}
                placeholder={activeTab === "rate" ? "e.g. 7.85" : "e.g. 500000"}
                className="w-full rounded-2xl border border-slate-200 bg-white px-3 py-3 text-sm shadow-sm outline-none transition-colors focus:border-teal-300 focus:ring-4 focus:ring-teal-100"
              />
            </div>
            <button
              onClick={addChange}
              className="flex w-full items-center justify-center gap-2 rounded-2xl bg-slate-950 py-3 text-sm font-semibold text-white shadow-lg shadow-slate-200 transition-colors hover:bg-teal-700"
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
                Add a prepayment, rate change, or OD balance to start a scenario.
              </div>
            ) : (
              sortedChanges.map((change, index) => (
                <div key={index} className="group flex items-center justify-between rounded-2xl border border-slate-200 bg-slate-50 px-3 py-3">
                  <div className="flex items-center gap-3">
                    <div
                      className={`rounded-xl p-2 ${
                        change.type === "prepayment"
                          ? "bg-emerald-100 text-emerald-700"
                          : change.type === "rate"
                            ? "bg-blue-100 text-blue-700"
                            : "bg-amber-100 text-amber-700"
                      }`}
                    >
                      {change.type === "prepayment" ? (
                        <Banknote className="h-4 w-4" />
                      ) : change.type === "rate" ? (
                        <TrendingUp className="h-4 w-4" />
                      ) : (
                        <Wallet className="h-4 w-4" />
                      )}
                    </div>
                    <div>
                      <p className="text-xs font-semibold text-slate-950">
                        {change.type === "prepayment" ? "Prepayment" : change.type === "rate" ? "Rate Change" : "OD Adjustment"}
                      </p>
                      <p className="mt-0.5 text-[11px] text-slate-500">
                        {change.type === "rate" ? change.data.effectiveDate : change.data.date} •{" "}
                        {change.type === "rate"
                          ? `${change.data.annualRate}%`
                          : formatter.format(change.type === "prepayment" ? change.data.amount : change.data.balance)}
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
              ))
            )}
          </div>
        </section>
      </div>

      <div className="space-y-5 lg:col-span-8">
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
          <div className="rounded-[24px] border border-slate-200 bg-slate-50 p-4">
            <div className="flex items-center gap-2">
              <Target className="h-4 w-4 text-teal-700" />
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Policy note</p>
            </div>
            <p className="mt-3 text-sm leading-6 text-slate-600">
              Simulated results respect your selected `Fixed EMI` or `Fixed Tenure` behavior from settings.
            </p>
          </div>
        </div>

        <section className="rounded-[28px] border border-slate-200 bg-white p-5 shadow-[0_12px_45px_rgba(15,23,42,0.05)]">
          <div className="flex items-center gap-2">
            <Info className="h-4 w-4 text-teal-700" />
            <h3 className="text-base font-semibold tracking-tight text-slate-950">Scenario Guidance</h3>
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            <GuidanceCard title="Prepayments" body="Useful for one-time lump sum reductions or recurring manual overpayments." />
            <GuidanceCard title="Rate changes" body="Simulate repricing risk without editing the base account history." />
            <GuidanceCard title="OD balances" body="Model how cash parked in OD changes effective principal and interest cost." />
          </div>
        </section>
      </div>
    </div>
  );
}

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
}: {
  title: string;
  base: string;
  sim: string;
  isBetter: boolean;
  subtext?: string;
}) {
  const isNeutral = base === sim;

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
