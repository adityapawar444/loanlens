"use client";

import Link from "next/link";
import { type ReactNode, useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowUpRight,
  Banknote,
  CalendarDays,
  CircleDollarSign,
  CircleHelp,
  Coins,
  Gauge,
  Info,
  Layers3,
  LineChart as LineChartIcon,
  PiggyBank,
  ShieldCheck,
  Sparkles,
  TrendingDown,
  Wallet,
  X,
} from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { AmortizationRow, LoanData, SummaryMetrics } from "@/lib/types";
import HelpTooltip from "@/components/common/HelpTooltip";
import EstimateNote from "@/components/common/EstimateNote";
import AmortizationTable from "@/components/schedule/AmortizationTable";

type HorizonKey = "ytd" | "5y" | "10y" | "full";
type TableRangeKey = "12m" | "24m" | "5y" | "all";
type WhyKey = "effectivePrincipal" | "odImpact" | "interestSaved" | "effectiveRate" | "futureInterest";

const HORIZON_OPTIONS: Array<{ key: HorizonKey; label: string; months: number | null }> = [
  { key: "ytd", label: "This Year", months: 12 },
  { key: "5y", label: "5Y", months: 60 },
  { key: "10y", label: "10Y", months: 120 },
  { key: "full", label: "Full", months: null },
];

const TABLE_OPTIONS: Array<{ key: TableRangeKey; label: string; months: number | null }> = [
  { key: "12m", label: "12 Months", months: 12 },
  { key: "24m", label: "24 Months", months: 24 },
  { key: "5y", label: "5 Years", months: 60 },
  { key: "all", label: "All", months: null },
];

const COLORS = {
  ink: "#0f172a",
  slate: "#64748b",
  teal: "#0f766e",
  blue: "#2563eb",
  amber: "#f59e0b",
  emerald: "#16a34a",
  rose: "#e11d48",
};

function ChartSkeleton() {
  return (
    <div className="relative w-full h-full flex flex-col justify-end gap-2 animate-pulse px-2 py-4">
      <div className="flex items-end justify-between w-full h-[80%] gap-4 px-4">
        <div className="bg-slate-200/80 rounded-t-lg w-full h-[40%]" />
        <div className="bg-slate-200/80 rounded-t-lg w-full h-[65%]" />
        <div className="bg-slate-200/80 rounded-t-lg w-full h-[50%]" />
        <div className="bg-slate-200/80 rounded-t-lg w-full h-[85%]" />
        <div className="bg-slate-200/80 rounded-t-lg w-full h-[70%]" />
        <div className="bg-slate-200/80 rounded-t-lg w-full h-[95%]" />
      </div>
      <div className="h-[2px] bg-slate-200 w-full rounded" />
      <div className="flex justify-center gap-4 mt-2">
        <div className="h-3 w-16 bg-slate-200/85 rounded-full" />
        <div className="h-3 w-16 bg-slate-200/85 rounded-full" />
      </div>
    </div>
  );
}

export default function DashboardClient({
  loanData,
  schedule,
  metrics,
  todayStr,
}: {
  loanData: LoanData;
  schedule: AmortizationRow[];
  metrics: SummaryMetrics;
  todayStr: string;
}) {
  const [selectedHorizon, setSelectedHorizon] = useState<HorizonKey>("ytd");
  const [selectedTableRange, setSelectedTableRange] = useState<TableRangeKey>("12m");
  const [openWhyKey, setOpenWhyKey] = useState<WhyKey | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setMounted(true);
  }, []);

  const formatter = useMemo(
    () =>
      new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: "INR",
        maximumFractionDigits: 0,
      }),
    []
  );

  const numberFormatter = useMemo(
    () =>
      new Intl.NumberFormat("en-IN", {
        maximumFractionDigits: 1,
      }),
    []
  );

  const currentIndex = Math.max(0, schedule.findIndex((row) => row.dueDate >= todayStr));
  const currentRate = loanData.rateHistory.at(-1)?.annualRate ?? 0;
  const odOffset = Math.max(0, metrics.outstandingPrincipal - metrics.effectivePrincipal);
  const futureInterest = Math.max(0, metrics.totalInterestProjected - metrics.interestPaidToDate);
  const payoffProgress = clampPercent(
    metrics.disbursedAmount > 0
      ? ((metrics.disbursedAmount - metrics.outstandingPrincipal) / metrics.disbursedAmount) * 100
      : 0
  );
  const remainingMonths = Math.max(0, schedule.length - currentIndex);
  const remainingTenureLabel = formatRemainingTenure(remainingMonths);
  const closureMonthLabel = formatMonthLabel(metrics.projectedClosureDate);
  const effectiveRateDelta = Math.max(0, currentRate - metrics.effectiveInterestRate);
  const aheadOfBaseline = odOffset > 0 || metrics.interestSavedTillNow > 0;
  const postedRows = schedule.slice(0, currentIndex);
  const currentRow = schedule[currentIndex] ?? schedule.at(-1);
  const baselineInterestPaidToDate = postedRows.reduce((sum, row) => sum + row.baselineInterest, 0);

  const healthStatus = calculateHealthStatus({
    odOffset,
    outstanding: metrics.outstandingPrincipal,
    interestSaved: metrics.interestSavedTillNow,
    totalProjectedInterest: metrics.totalInterestProjected,
    principalPaid: metrics.principalPaidToDate,
    disbursed: metrics.disbursedAmount,
    currentRate,
    effectiveRate: metrics.effectiveInterestRate,
  });

  const healthBreakdown = [
    { label: "Outstanding Principal", value: formatter.format(metrics.outstandingPrincipal) },
    { label: "Effective Principal", value: formatter.format(metrics.effectivePrincipal) },
    { label: "OD Offset", value: formatter.format(odOffset) },
    { label: "Interest Saved", value: formatter.format(metrics.interestSavedTillNow) },
    { label: "Remaining Tenure", value: remainingTenureLabel },
  ];

  const whyContent = {
    effectivePrincipal: {
      title: "Effective Principal",
      rows: [
        { label: "Outstanding Principal", value: formatter.format(metrics.outstandingPrincipal) },
        { label: "Current OD Offset", value: formatter.format(odOffset) },
        { label: "Interest Charged On", value: formatter.format(metrics.effectivePrincipal) },
      ],
      footnote: "Effective principal is the current interest-bearing balance after OD support is applied.",
    },
    odImpact: {
      title: "OD Offset Impact",
      rows: [
        { label: "Outstanding Principal", value: formatter.format(metrics.outstandingPrincipal) },
        { label: "Current OD Balance", value: formatter.format(odOffset) },
        { label: "Difference", value: formatter.format(odOffset) },
        { label: "Interest Charged On", value: formatter.format(metrics.effectivePrincipal) },
      ],
      footnote: "OD reduces the balance used for interest calculation. It does not rewrite the principal outstanding.",
    },
    interestSaved: {
      title: "Interest Saved",
      rows: [
        { label: "Baseline Interest Posted", value: formatter.format(baselineInterestPaidToDate) },
        { label: "Actual Interest Posted", value: formatter.format(metrics.interestPaidToDate) },
        { label: "Savings Realized", value: formatter.format(metrics.interestSavedTillNow) },
      ],
      footnote: "This compares actual interest against the baseline schedule for the periods posted so far.",
    },
    effectiveRate: {
      title: "Effective Rate",
      rows: [
        { label: "Nominal Rate", value: `${numberFormatter.format(currentRate)}%` },
        { label: "OD-driven Reduction", value: `${numberFormatter.format(effectiveRateDelta)}%` },
        { label: "Effective Rate", value: `${numberFormatter.format(metrics.effectiveInterestRate)}%` },
      ],
      footnote: "This is the realized equivalent rate after current OD-assisted savings are factored in.",
    },
    futureInterest: {
      title: "Future Interest",
      rows: [
        { label: "Projected Total Interest", value: formatter.format(metrics.totalInterestProjected) },
        { label: "Interest Already Paid", value: formatter.format(metrics.interestPaidToDate) },
        { label: "Remaining Future Interest", value: formatter.format(futureInterest) },
      ],
      footnote: "Projected from today until the current closure date using the live repayment schedule.",
    },
  } satisfies Record<WhyKey, { title: string; rows: Array<{ label: string; value: string }>; footnote: string }>;

  const currentYear = Number(todayStr.slice(0, 4));

  const horizonRows = useMemo(() => {
    if (selectedHorizon === "ytd") {
      // Show all schedule rows within the current calendar year (Jan–Dec)
      return schedule.filter((row) => Number(row.dueDate.slice(0, 4)) === currentYear);
    }
    const months = HORIZON_OPTIONS.find((option) => option.key === selectedHorizon)?.months ?? null;
    return sliceRows(schedule, currentIndex, months);
  }, [currentIndex, currentYear, schedule, selectedHorizon]);

  const tableRows = useMemo(
    () => sliceRows(schedule, currentIndex, TABLE_OPTIONS.find((option) => option.key === selectedTableRange)?.months ?? null),
    [currentIndex, schedule, selectedTableRange]
  );

  const chartSeries = useMemo(() => buildChartSeries(horizonRows), [horizonRows]);

  const compositionCards = [
    {
      title: "Principal",
      primaryLabel: "Paid",
      primaryValue: formatter.format(metrics.principalPaidToDate),
      secondaryLabel: "Remaining",
      secondaryValue: formatter.format(Math.max(0, metrics.outstandingPrincipal)),
      progress: metrics.disbursedAmount > 0 ? clampPercent((metrics.principalPaidToDate / metrics.disbursedAmount) * 100) : 0,
      accentClass: "bg-teal-600",
    },
    {
      title: "Interest",
      primaryLabel: "Paid",
      primaryValue: formatter.format(metrics.interestPaidToDate),
      secondaryLabel: "Projected",
      secondaryValue: formatter.format(futureInterest),
      progress:
        metrics.totalInterestProjected > 0
          ? clampPercent((metrics.interestPaidToDate / metrics.totalInterestProjected) * 100)
          : 0,
      accentClass: "bg-blue-600",
    },
    {
      title: "Funding",
      primaryLabel: "Disbursed",
      primaryValue: formatter.format(metrics.disbursedAmount),
      secondaryLabel: "Sanctioned",
      secondaryValue: formatter.format(metrics.sanctionedAmount),
      progress:
        metrics.sanctionedAmount > 0 ? clampPercent((metrics.disbursedAmount / metrics.sanctionedAmount) * 100) : 0,
      accentClass: "bg-amber-500",
    },
  ];

  const insights = buildInsights({
    formatter,
    odOffset,
    remainingMonths,
    metrics,
    currentRate,
    effectiveRateDelta,
    aheadOfBaseline,
    futureInterest,
  });

  // Compute moratorium end date for the Loan Details panel
  const moratoriumEndDate = useMemo(() => {
    const firstDate = loanData.disbursements[0]?.date;
    if (!firstDate) return "-";
    const [y, m, d] = firstDate.split("-").map(Number);
    const end = new Date(y, m - 1 + loanData.loanDetails.moratoriumMonths, d);
    return end.toLocaleDateString("en-US", { month: "short", year: "numeric", timeZone: "UTC" });
  }, [loanData.disbursements, loanData.loanDetails.moratoriumMonths]);

  // Days until next due date
  const daysUntilDue = useMemo(() => {
    if (!metrics.nextDueDate) return null;
    const [dy, dm, dd] = metrics.nextDueDate.split("-").map(Number);
    const due = new Date(dy, dm - 1, dd);
    const [ty, tm, td] = todayStr.split("-").map(Number);
    const today = new Date(ty, tm - 1, td);
    return Math.max(0, Math.round((due.getTime() - today.getTime()) / (1000 * 60 * 60 * 24)));
  }, [metrics.nextDueDate, todayStr]);

  const monthlySummary = [
    {
      title: "OD savings this month",
      body: `Saved ${formatter.format(currentRow?.interestSavings ?? 0)} in the current schedule month through OD offset.`,
      tone: "positive" as const,
    },
    {
      title: "YTD interest saved",
      body: `${formatter.format(metrics.interestSavedThisYear)} saved so far in ${currentYear} versus the baseline schedule.`,
      tone: metrics.interestSavedThisYear > 0 ? ("positive" as const) : ("neutral" as const),
    },
    {
      title: "Current month interest",
      body: `Bank is charging ${formatter.format(currentRow?.interest ?? 0)} in interest for this schedule cycle.`,
      tone: "neutral" as const,
    },
    {
      title: "Disbursement progress",
      body: `${formatter.format(metrics.disbursedAmount)} of ${formatter.format(metrics.sanctionedAmount)} sanctioned amount released so far.`,
      tone: "neutral" as const,
    },
    {
      title: "Next due in",
      body: daysUntilDue !== null ? `${daysUntilDue} day${daysUntilDue === 1 ? "" : "s"} until the next installment of ${formatter.format(metrics.nextInstallmentAmount)}.` : "Due date unavailable.",
      tone: daysUntilDue !== null && daysUntilDue <= 7 ? ("positive" as const) : ("neutral" as const),
    },
  ];

  return (
    <div className="space-y-4 print:space-y-4">
      <section className="grid gap-5 md:grid-cols-6 xl:grid-cols-12">
        <div className="col-span-full overflow-hidden rounded-[32px] border border-slate-200 bg-[linear-gradient(135deg,#07111f_0%,#103338_54%,#eef8f7_140%)] p-6 text-white shadow-[0_22px_70px_rgba(15,23,42,0.22)] md:p-8 print:shadow-none">
          <div className="grid gap-5 md:grid-cols-6 xl:grid-cols-12 xl:items-stretch">
            <div className="md:col-span-2 xl:col-span-3">
              <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-teal-100/80">Overview</p>
              <h2 className="mt-3 text-3xl font-semibold tracking-tight text-white md:text-[2.25rem]">
                Home Loan Dashboard
              </h2>
              <p className="mt-3 max-w-sm text-sm leading-6 text-slate-200">
                Track loan payoff, OD savings, and repayment progress.
              </p>
              <div className="mt-6 inline-flex items-center rounded-full border border-white/15 bg-white/8 px-3 py-1.5 text-xs font-medium text-teal-100">
                {aheadOfBaseline ? "Ahead of baseline due to OD efficiency" : "Tracking close to baseline plan"}
              </div>
            </div>

            <div className="md:col-span-2 xl:col-span-5 rounded-[28px] bg-white/10 p-5 backdrop-blur-sm ring-1 ring-white/10">
              <div className="flex items-center justify-between">
                <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-teal-100/80">Outstanding principal</p>
                <Wallet className="h-4 w-4 text-teal-100" />
              </div>
              <p className="mt-4 text-4xl font-semibold tracking-tight text-white">
                {formatter.format(metrics.outstandingPrincipal)}
              </p>

              <div className="mt-6 grid gap-4 sm:grid-cols-3">
                <HeroStat
                  label="Effective Principal"
                  value={formatter.format(metrics.effectivePrincipal)}
                  tone="text-white"
                  tooltip="Outstanding principal minus OD offset balance. This is the amount currently attracting interest."
                  onWhy={() => setOpenWhyKey("effectivePrincipal")}
                />
                <HeroStat
                  label="OD Offset Impact"
                  value={formatter.format(odOffset)}
                  tone="text-emerald-300"
                  tooltip="Reduction in interest-bearing principal due to funds parked in the OD account."
                  onWhy={() => setOpenWhyKey("odImpact")}
                />
                <HeroStat
                  label="Am I Ahead?"
                  value={aheadOfBaseline ? "Yes" : "On Plan"}
                  tone="text-teal-200"
                />
              </div>
            </div>

            <div className="md:col-span-2 xl:col-span-4 rounded-[28px] bg-white p-5 text-slate-950 shadow-[0_12px_35px_rgba(15,23,42,0.12)]">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">Debt freedom</p>
                  <p className="mt-3 text-2xl font-semibold tracking-tight">{closureMonthLabel}</p>
                  <p className="mt-1 text-sm text-slate-600">Projected closure</p>
                </div>
                <ProgressRing value={payoffProgress} />
              </div>
              <div className="mt-5 flex items-end justify-between gap-4 rounded-2xl bg-slate-50 p-4">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Remaining tenure</p>
                  <p className="mt-2 text-lg font-semibold text-slate-950">{remainingTenureLabel}</p>
                </div>
                <div className="text-right">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Loan completed</p>
                  <p className="mt-2 text-lg font-semibold text-teal-700">{numberFormatter.format(payoffProgress)}%</p>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-6">
            <EstimateNote>
              All summary values are generated from your current disbursements, rate history, OD snapshots, and payment log. They are live projections, not bank-issued statement values.
            </EstimateNote>
          </div>
        </div>
      </section>

      <section className="rounded-[28px] border border-slate-200 bg-white px-4 py-4 shadow-[0_12px_45px_rgba(15,23,42,0.05)] md:px-5">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h3 className="text-base font-semibold tracking-tight text-slate-950">This Month</h3>
            <p className="mt-1 text-sm text-slate-600">Quick changes driven by current OD balance, rates, and posted schedule rows.</p>
          </div>
          <CalendarDays className="hidden h-4 w-4 text-slate-400 sm:block" />
        </div>
        <div className="mt-4 grid gap-3 xl:grid-cols-5">
          {monthlySummary.map((item) => (
            <MonthlySummaryCard key={item.title} {...item} />
          ))}
        </div>
      </section>

      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
        <CompactKpiCard
          title="Interest Saved"
          value={formatter.format(metrics.interestSavedTillNow)}
          subtext="Lifetime savings till date. June savings are not fully reflected."
          icon={<PiggyBank className="h-4 w-4" />}
          accent="emerald"
          tooltip="Difference between actual interest charged and the baseline loan scenario."
          onWhy={() => setOpenWhyKey("interestSaved")}
        />
        <CompactKpiCard
          title="Interest Paid"
          value={formatter.format(metrics.interestPaidToDate)}
          subtext="Paid so far"
          icon={<Banknote className="h-4 w-4" />}
          accent="blue"
        />
        <CompactKpiCard
          title="Next Installment"
          value={formatter.format(metrics.nextInstallmentAmount)}
          subtext={`Due ${formatDueDate(metrics.nextDueDate)}`}
          icon={<CalendarDays className="h-4 w-4" />}
          accent="teal"
        />
        <CompactKpiCard
          title="Effective Rate"
          value={`${numberFormatter.format(metrics.effectiveInterestRate)}%`}
          subtext={`vs ${numberFormatter.format(currentRate)}% nominal`}
          icon={<Gauge className="h-4 w-4" />}
          accent="amber"
          tooltip="The equivalent interest rate after factoring in OD-driven savings."
          onWhy={() => setOpenWhyKey("effectiveRate")}
        />
        <CompactKpiCard
          title="Future Interest"
          value={formatter.format(futureInterest)}
          subtext="Projected from today until closure"
          icon={<Coins className="h-4 w-4" />}
          accent="blue"
          tooltip="Estimated interest payable from today until projected closure."
          onWhy={() => setOpenWhyKey("futureInterest")}
        />
        <CompactKpiCard
          title="Projected EMI"
          value={formatter.format(metrics.projectedEmi)}
          subtext="Current projection"
          icon={<CircleDollarSign className="h-4 w-4" />}
          accent="rose"
        />
      </section>

      <section className="grid gap-4 md:grid-cols-6 xl:grid-cols-12">
        <Panel
          className="md:col-span-6 xl:col-span-8 h-full"
          title="Loan Health"
          subtitle="Status-based assessment of how effectively OD balances and repayments are reducing borrowing costs."
        >
          <div className="grid gap-5 lg:grid-cols-[minmax(0,0.45fr)_minmax(0,0.55fr)] lg:items-start h-full">
            <div className="rounded-[28px] bg-[linear-gradient(135deg,#0f172a_0%,#163c46_100%)] px-5 py-5 text-white">
              <div className="flex items-center gap-2">
                <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-teal-100/80">Loan Efficiency Status</p>
                <HelpTooltip content="Assessment of how effectively OD balances and repayments are reducing borrowing costs." />
              </div>
              <div className="mt-3 flex items-center gap-3">
                <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] ${healthStatus.badgeClass}`}>
                  {healthStatus.label}
                </span>
                <ShieldCheck className="h-5 w-5 text-teal-100" />
              </div>
              <p className="mt-3 text-sm text-slate-200">{healthStatus.summary}</p>
              <div className="mt-4 grid gap-2">
                {healthStatus.reasons.map((reason) => (
                  <p key={reason} className="text-sm text-teal-50">
                    {reason}
                  </p>
                ))}
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {healthBreakdown.map((item) => (
                <InfoPill key={item.label} label={item.label} value={item.value} />
              ))}
            </div>
          </div>
        </Panel>

        <Panel className="print:hidden md:col-span-6 xl:col-span-4 h-full" title="Loan Details" subtitle="Loan parameters and configuration details.">
          <div className="grid gap-3 sm:grid-cols-2">
            <InfoPill label="Lender" value={loanData.loanDetails.lender} />
            <InfoPill label="Account" value={loanData.loanDetails.accountNumber} />
            <InfoPill label="Sanctioned Amount" value={formatter.format(metrics.sanctionedAmount)} />
            <InfoPill label="Disbursed Amount" value={formatter.format(metrics.disbursedAmount)} />
            <InfoPill label="Current ROI" value={`${numberFormatter.format(currentRate)}%`} />
            <InfoPill label="Moratorium End" value={moratoriumEndDate} />
            <InfoPill label="Loan Start Date" value={loanData.disbursements[0]?.date ?? "-"} />
            <InfoPill label="Tenure" value={`${loanData.loanDetails.totalTenureMonths} months`} />
          </div>
        </Panel>
      </section>

      <section className="grid gap-5 md:grid-cols-6 xl:grid-cols-12">
        <Panel
          className="md:col-span-6 xl:col-span-12"
          title="Loan Progression"
          subtitle={selectedHorizon === "ytd" ? `Full calendar year ${currentYear} — past actuals and projected months side by side.` : "The first answer here should always be balance, mix, and OD impact."}
          action={<PillSelector<HorizonKey> options={HORIZON_OPTIONS} value={selectedHorizon} onChange={setSelectedHorizon} />}
        >
          <div className="grid gap-4 xl:grid-cols-12">
            <ChartPanel
              className="xl:col-span-6"
              title="Outstanding vs Effective Balance"
              subtitle="How much OD is pulling down the interest-bearing balance."
              icon={<Layers3 className="h-4 w-4" />}
            >
              {mounted ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartSeries} margin={{ top: 12, right: 10, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="heroOutstanding" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor={COLORS.ink} stopOpacity={0.22} />
                        <stop offset="95%" stopColor={COLORS.ink} stopOpacity={0.02} />
                      </linearGradient>
                      <linearGradient id="heroEffective" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor={COLORS.teal} stopOpacity={0.22} />
                        <stop offset="95%" stopColor={COLORS.teal} stopOpacity={0.02} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="label" tick={{ fontSize: 11, fill: COLORS.slate }} minTickGap={24} />
                    <YAxis tick={{ fontSize: 11, fill: COLORS.slate }} width={68} tickFormatter={(value) => formatAxisShort(value)} />
                    <Tooltip content={<ChartTooltip formatter={formatter} />} />
                    <Legend />
                    <Area type="monotone" dataKey="outstandingBalance" name="Outstanding" stroke={COLORS.ink} fill="url(#heroOutstanding)" strokeWidth={2} />
                    <Area type="monotone" dataKey="effectiveBalance" name="Effective" stroke={COLORS.teal} fill="url(#heroEffective)" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <ChartSkeleton />
              )}
            </ChartPanel>

            <ChartPanel
              className="xl:col-span-6"
              title="Interest vs Principal"
              subtitle={selectedHorizon === "ytd" ? `Full year ${currentYear} repayment mix — actual months plus projections.` : "Repayment mix for the selected horizon."}
              icon={<TrendingDown className="h-4 w-4" />}
            >
              {mounted ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartSeries} margin={{ top: 12, right: 10, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="label" tick={{ fontSize: 11, fill: COLORS.slate }} minTickGap={24} />
                    <YAxis tick={{ fontSize: 11, fill: COLORS.slate }} width={68} tickFormatter={(value) => formatAxisShort(value)} />
                    <Tooltip content={<ChartTooltip formatter={formatter} />} />
                    <Legend />
                    <Bar dataKey="interest" name="Interest" stackId="mix" fill={COLORS.amber} radius={[8, 8, 0, 0]} />
                    <Bar dataKey="principal" name="Principal" stackId="mix" fill={COLORS.teal} radius={[8, 8, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <ChartSkeleton />
              )}
            </ChartPanel>

            <ChartPanel
              className="xl:col-span-12"
              title="OD Benefit Over Time"
              subtitle={selectedHorizon === "ytd" ? `Savings trend across all of ${currentYear} — past and projected.` : "Baseline vs OD-adjusted balance, with cumulative savings trend."}
              icon={<Sparkles className="h-4 w-4" />}
            >
              {mounted ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartSeries} margin={{ top: 12, right: 10, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="label" tick={{ fontSize: 11, fill: COLORS.slate }} minTickGap={24} />
                    <YAxis yAxisId="left" tick={{ fontSize: 11, fill: COLORS.slate }} width={68} tickFormatter={(value) => formatAxisShort(value)} />
                    <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11, fill: COLORS.slate }} width={68} tickFormatter={(value) => formatAxisShort(value)} />
                    <Tooltip content={<ChartTooltip formatter={formatter} />} />
                    <Legend />
                    <Line yAxisId="left" type="monotone" dataKey="outstandingBalance" name="Baseline Loan Balance" stroke={COLORS.ink} strokeWidth={2} dot={false} />
                    <Line yAxisId="left" type="monotone" dataKey="effectiveBalance" name="OD Adjusted Balance" stroke={COLORS.teal} strokeWidth={2} dot={false} />
                    <Line yAxisId="right" type="monotone" dataKey="cumulativeSavings" name="Cumulative Savings" stroke={COLORS.emerald} strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <ChartSkeleton />
              )}
            </ChartPanel>
          </div>

          <div className="mt-4">
            <EstimateNote>
              Balance, mix, and OD benefit charts are driven by the same live schedule engine. They reflect current ledger inputs and should be read as projections, not PDF statement rows.
            </EstimateNote>
          </div>
        </Panel>
      </section>

      <section className="grid gap-4 md:grid-cols-6 xl:grid-cols-12">
        <Panel className="md:col-span-6 xl:col-span-7 h-full" title="Loan Composition Dashboard" subtitle="Compact progress views with the bar carrying the visual weight.">
          <div className="flex-1 flex flex-col justify-between gap-3">
            {compositionCards.map((card) => (
              <CompositionCard key={card.title} {...card} />
            ))}
          </div>
        </Panel>

        <Panel className="md:col-span-6 xl:col-span-5 h-full" title="Insights" subtitle="Outcome-focused takeaways instead of raw rows.">
          <div className="grid gap-3 sm:grid-cols-2">
            {insights.map((insight) => (
              <InsightCard key={insight.title} title={insight.title} body={insight.body} icon={insight.icon} tone={insight.tone} tier={insight.tier} />
            ))}
          </div>
        </Panel>
      </section>

      <section className="print:hidden">
        <div className="rounded-[28px] border border-slate-200 bg-white px-4 py-3 shadow-[0_12px_45px_rgba(15,23,42,0.05)]">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h3 className="text-base font-semibold tracking-tight text-slate-950">Simulator</h3>
              <p className="mt-1 text-sm text-slate-600">Open the full payoff simulator for scenario testing.</p>
            </div>
            <Link
              href="/simulator"
              className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-4 py-2 text-sm font-semibold text-slate-700 transition-colors hover:border-teal-200 hover:bg-teal-50 hover:text-teal-800 sm:self-start"
            >
              Open Simulator
              <ArrowUpRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </section>

      <section className="space-y-2">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 className="text-xl font-semibold tracking-tight text-slate-950">Amortization Schedule</h3>
            <p className="mt-1 text-sm text-slate-600">Detailed schedule lower on the page, with the same math as the dedicated schedule screen.</p>
          </div>
          <Link
            href="/schedule"
            className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm transition-colors hover:bg-slate-50"
          >
            Open Full Schedule
            <ArrowUpRight className="h-4 w-4" />
          </Link>
        </div>

        <div className="flex flex-wrap gap-2">
          <PillSelector<TableRangeKey> options={TABLE_OPTIONS} value={selectedTableRange} onChange={setSelectedTableRange} />
        </div>

        <EstimateNote>
          Closing balance remains the actual principal outstanding. Effective balance shows OD-adjusted interest-bearing balance, and savings isolates interest benefit without rewriting principal.
        </EstimateNote>

        <AmortizationTable rows={tableRows} formatter={formatter} maxHeightClass="max-h-[560px]" stickyHeader />
      </section>

      <WhyDrawer openKey={openWhyKey} onClose={() => setOpenWhyKey(null)} content={openWhyKey ? whyContent[openWhyKey] : null} />
    </div>
  );
}

function Panel({
  title,
  subtitle,
  action,
  className,
  children,
}: {
  title: string;
  subtitle?: string;
  action?: ReactNode;
  className?: string;
  children: ReactNode;
}) {
  return (
    <section className={`rounded-[32px] border border-slate-200 bg-white p-5 shadow-[0_12px_45px_rgba(15,23,42,0.05)] md:p-5 print:shadow-none flex flex-col ${className ?? ""}`}>
      <div className={`flex flex-col gap-3 ${action ? "lg:flex-row lg:items-center lg:justify-between" : ""}`}>
        <div>
          <h3 className="text-lg font-semibold tracking-tight text-slate-950">{title}</h3>
          {subtitle ? <p className="mt-1 text-sm text-slate-600">{subtitle}</p> : null}
        </div>
        {action}
      </div>
      <div className="mt-4 flex-1 flex flex-col">{children}</div>
    </section>
  );
}

function CompactKpiCard({
  title,
  value,
  subtext,
  icon,
  accent,
  tooltip,
  onWhy,
}: {
  title: string;
  value: string;
  subtext: string;
  icon: ReactNode;
  accent: "teal" | "emerald" | "blue" | "amber" | "rose";
  tooltip?: string;
  onWhy?: () => void;
}) {
  const tone = {
    teal: "text-teal-700 bg-teal-50 border-teal-100",
    emerald: "text-emerald-700 bg-emerald-50 border-emerald-100",
    blue: "text-blue-700 bg-blue-50 border-blue-100",
    amber: "text-amber-700 bg-amber-50 border-amber-100",
    rose: "text-rose-700 bg-rose-50 border-rose-100",
  }[accent];

  return (
    <div className={`rounded-[24px] border p-4 shadow-[0_10px_24px_rgba(15,23,42,0.04)] ${tone}`}>
      <div className="flex items-center justify-between gap-3">
        <MetricLabel label={title} tooltip={tooltip} onWhy={onWhy} />
        <div className="rounded-xl bg-white/80 p-2">{icon}</div>
      </div>
      <p className="mt-3 text-2xl font-semibold tracking-tight text-slate-950">{value}</p>
      <p className="mt-1 text-sm text-slate-600">{subtext}</p>
    </div>
  );
}

function HeroStat({
  label,
  value,
  tone,
  tooltip,
  onWhy,
}: {
  label: string;
  value: string;
  tone: string;
  tooltip?: string;
  onWhy?: () => void;
}) {
  return (
    <div className="rounded-2xl bg-white/6 p-4 ring-1 ring-white/8">
      <MetricLabel label={label} tooltip={tooltip} onWhy={onWhy} dark />
      <p className={`mt-2 text-lg font-semibold tracking-tight ${tone}`}>{value}</p>
    </div>
  );
}

function ProgressRing({ value }: { value: number }) {
  const radius = 30;
  const circumference = 2 * Math.PI * radius;
  const dashOffset = circumference - (value / 100) * circumference;

  return (
    <div className="relative h-20 w-20">
      <svg className="h-20 w-20 -rotate-90" viewBox="0 0 80 80">
        <circle cx="40" cy="40" r={radius} stroke="#e2e8f0" strokeWidth="8" fill="none" />
        <circle
          cx="40"
          cy="40"
          r={radius}
          stroke={COLORS.teal}
          strokeWidth="8"
          fill="none"
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
          strokeLinecap="round"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <p className="text-lg font-semibold text-slate-950">{Math.round(value)}%</p>
        <p className="text-[10px] uppercase tracking-[0.16em] text-slate-500">Done</p>
      </div>
    </div>
  );
}

function PillSelector<T extends string>({
  options,
  value,
  onChange,
}: {
  options: Array<{ key: T; label: string }>;
  value: T;
  onChange: (next: T) => void;
}) {
  return (
    <div className="inline-flex flex-wrap rounded-full border border-slate-200 bg-slate-50 p-1 text-xs font-medium">
      {options.map((option) => (
        <button
          key={option.key}
          onClick={() => onChange(option.key)}
          className={`rounded-full px-3 py-1.5 transition-colors ${
            value === option.key ? "bg-slate-950 text-white shadow-sm" : "text-slate-600 hover:text-slate-900"
          }`}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

function ChartPanel({
  title,
  subtitle,
  icon,
  className,
  children,
}: {
  title: string;
  subtitle: string;
  icon: ReactNode;
  className?: string;
  children: ReactNode;
}) {
  return (
    <div className={`rounded-[28px] border border-slate-200 bg-slate-50 p-4 ${className ?? ""}`}>
      <div className="flex items-start gap-3">
        <div className="rounded-xl border border-slate-200 bg-white p-2 text-slate-700">{icon}</div>
        <div>
          <h4 className="text-sm font-semibold text-slate-950">{title}</h4>
          <p className="mt-1 text-sm text-slate-600">{subtitle}</p>
        </div>
      </div>
      <div className="relative mt-3 h-[250px] w-full min-w-0">{children}</div>
    </div>
  );
}

function ChartTooltip({
  active,
  payload,
  label,
  formatter,
}: {
  active?: boolean;
  payload?: Array<{ value?: number; name?: string }>;
  label?: string;
  formatter: Intl.NumberFormat;
}) {
  if (!active || !payload?.length) {
    return null;
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white px-3 py-2 shadow-lg">
      {label ? <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">{label}</p> : null}
      <div className="mt-2 space-y-1">
        {payload
          .filter((item) => typeof item.value === "number")
          .map((item) => (
            <div key={`${item.name}-${item.value}`} className="flex items-center justify-between gap-6 text-sm">
              <span className="text-slate-600">{item.name}</span>
              <span className="font-semibold text-slate-950">{formatter.format(item.value ?? 0)}</span>
            </div>
          ))}
      </div>
    </div>
  );
}

function InfoPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
      <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">{label}</p>
      <p className="mt-2 text-sm font-semibold text-slate-950">{value}</p>
    </div>
  );
}

function MetricLabel({
  label,
  tooltip,
  onWhy,
  dark = false,
}: {
  label: string;
  tooltip?: string;
  onWhy?: () => void;
  dark?: boolean;
}) {
  return (
    <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
      <p className={`text-[11px] font-semibold uppercase tracking-[0.18em] ${dark ? "text-slate-300" : "text-slate-500"}`}>
        {label}
      </p>
      {tooltip ? <HelpTooltip content={tooltip} /> : null}
      {onWhy ? (
        <button
          type="button"
          onClick={onWhy}
          className={`text-xs font-semibold ${dark ? "text-teal-100 hover:text-white" : "text-teal-700 hover:text-teal-800"}`}
        >
          Why?
        </button>
      ) : null}
    </div>
  );
}

function CompositionCard({
  title,
  primaryLabel,
  primaryValue,
  secondaryLabel,
  secondaryValue,
  progress,
  accentClass,
}: {
  title: string;
  primaryLabel: string;
  primaryValue: string;
  secondaryLabel: string;
  secondaryValue: string;
  progress: number;
  accentClass: string;
}) {
  return (
    <div className="rounded-[22px] border border-slate-200 bg-slate-50 p-4 flex-1 flex flex-col justify-between">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold text-slate-950">{title}</p>
        <p className="text-xs font-semibold text-slate-500">{Math.round(clampPercent(progress))}% complete</p>
      </div>
      <div className="mt-2 grid grid-cols-2 gap-4">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">{primaryLabel}</p>
          <p className="mt-1 text-sm font-semibold text-slate-950">{primaryValue}</p>
        </div>
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">{secondaryLabel}</p>
          <p className="mt-1 text-sm font-semibold text-slate-950">{secondaryValue}</p>
        </div>
      </div>
      <div className="mt-2.5 h-2.5 overflow-hidden rounded-full bg-slate-200">
        <div className={`h-full rounded-full ${accentClass}`} style={{ width: `${clampPercent(progress)}%` }} />
      </div>
    </div>
  );
}

function InsightCard({
  title,
  body,
  icon,
  tone,
  tier,
}: {
  title: string;
  body: string;
  icon: ReactNode;
  tone: "positive" | "neutral";
  tier: "primary" | "secondary";
}) {
  const cardTone =
    tier === "primary"
      ? "border-teal-100 bg-[linear-gradient(180deg,#f8fffe_0%,#eefaf8_100%)]"
      : "border-slate-200 bg-slate-50";

  return (
    <div className={`rounded-2xl px-4 ${tier === "primary" ? "py-4" : "py-3.5"} ${cardTone}`}>
      <div className="flex items-start justify-between gap-3">
        <div className={`rounded-xl border p-2 ${tier === "primary" ? "border-teal-100 bg-white text-teal-700" : "border-slate-200 bg-white text-slate-700"}`}>{icon}</div>
        <span
          className={`inline-flex rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] ${
            tone === "positive" ? "bg-emerald-50 text-emerald-700" : "bg-slate-200 text-slate-700"
          }`}
        >
          {tone}
        </span>
      </div>
      <p className="mt-3 text-sm font-semibold text-slate-950">{title}</p>
      <p className="mt-1.5 text-sm leading-6 text-slate-600">{body}</p>
    </div>
  );
}

function MonthlySummaryCard({
  title,
  body,
  tone,
}: {
  title: string;
  body: string;
  tone: "positive" | "neutral";
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
      <div className="flex items-center gap-2">
        <span className={`inline-flex h-5 w-5 items-center justify-center rounded-full text-xs ${tone === "positive" ? "bg-emerald-100 text-emerald-700" : "bg-slate-200 text-slate-700"}`}>
          {tone === "positive" ? "✓" : "•"}
        </span>
        <p className="text-sm font-semibold text-slate-950">{title}</p>
      </div>
      <p className="mt-2 text-sm leading-6 text-slate-600">{body}</p>
    </div>
  );
}

function WhyDrawer({
  openKey,
  onClose,
  content,
}: {
  openKey: WhyKey | null;
  onClose: () => void;
  content: { title: string; rows: Array<{ label: string; value: string }>; footnote: string } | null;
}) {
  const panelRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!openKey) {
      return;
    }

    const panel = panelRef.current;
    if (!panel) {
      return;
    }

    const focusable = panel.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    const first = focusable[0];
    const last = focusable[focusable.length - 1];

    first?.focus();

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        return;
      }

      if (event.key !== "Tab" || focusable.length === 0) {
        return;
      }

      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last?.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first?.focus();
      }
    };

    document.body.style.overflow = "hidden";
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.body.style.overflow = "";
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [openKey, onClose]);

  if (!openKey || !content) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-slate-950/35 p-4 print:hidden" onClick={onClose}>
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="why-drawer-title"
        className="w-full max-w-xl rounded-[28px] border border-slate-200 bg-white p-5 shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <CircleHelp className="h-4 w-4 text-teal-700" />
              <h4 id="why-drawer-title" className="text-lg font-semibold tracking-tight text-slate-950">
                {content.title}
              </h4>
            </div>
            <p className="mt-2 text-sm text-slate-600">Calculation detail for the dashboard metric.</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-slate-200 text-slate-500 transition-colors hover:bg-slate-50 hover:text-slate-900"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50">
          {content.rows.map((row, index) => (
            <div key={row.label} className={`flex items-center justify-between gap-4 px-4 py-3 ${index > 0 ? "border-t border-slate-200" : ""}`}>
              <p className="text-sm text-slate-600">{row.label}</p>
              <p className="text-sm font-semibold text-slate-950">{row.value}</p>
            </div>
          ))}
        </div>
        <div className="mt-4 rounded-2xl border border-teal-100 bg-teal-50 px-4 py-3 text-sm text-teal-900">
          <div className="flex items-start gap-2">
            <Info className="mt-0.5 h-4 w-4 flex-none" />
            <p>{content.footnote}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function buildChartSeries(rows: AmortizationRow[]) {
  let cumulativeSavings = 0;

  return rows.map((row) => {
    cumulativeSavings += row.interestSavings;

    return {
      label: row.dueDate.slice(2),
      outstandingBalance: row.closingBalance,
      effectiveBalance: row.effectivePrincipal,
      interest: row.interest,
      principal: row.principal,
      cumulativeSavings,
    };
  });
}

function buildInsights({
  formatter,
  odOffset,
  remainingMonths,
  metrics,
  currentRate,
  effectiveRateDelta,
  aheadOfBaseline,
  futureInterest,
}: {
  formatter: Intl.NumberFormat;
  odOffset: number;
  remainingMonths: number;
  metrics: SummaryMetrics;
  currentRate: number;
  effectiveRateDelta: number;
  aheadOfBaseline: boolean;
  futureInterest: number;
}) {
  return [
    {
      title: "OD Impact",
      body: `OD balance reduced effective principal by ${formatter.format(odOffset)} today.`,
      icon: <Sparkles className="h-4 w-4" />,
      tone: "positive" as const,
      tier: "primary" as const,
    },
    {
      title: "Debt-free runway",
      body: `At the current pace, the loan is projected to close in ${formatRemainingTenure(remainingMonths)}.`,
      icon: <CalendarDays className="h-4 w-4" />,
      tone: "neutral" as const,
      tier: "primary" as const,
    },
    {
      title: "Future interest",
      body: `Projected future interest from here is ${formatter.format(futureInterest)}.`,
      icon: <Coins className="h-4 w-4" />,
      tone: "neutral" as const,
      tier: "primary" as const,
    },
    {
      title: "Rate efficiency",
      body: `Effective ROI is ${effectiveRateDelta > 0 ? `${effectiveRateDelta.toFixed(2)}% lower` : "in line"} than the nominal ${currentRate.toFixed(2)}% rate.`,
      icon: <Gauge className="h-4 w-4" />,
      tone: effectiveRateDelta > 0 ? ("positive" as const) : ("neutral" as const),
      tier: "secondary" as const,
    },
    {
      title: "Savings pulse",
      body: `Interest saved this year is ${formatter.format(metrics.interestSavedThisYear)} based on currently posted statement data.`,
      icon: <PiggyBank className="h-4 w-4" />,
      tone: "positive" as const,
      tier: "secondary" as const,
    },
    {
      title: "Schedule position",
      body: aheadOfBaseline
        ? "You are ahead of the baseline schedule due to OD-backed savings and lower effective balance."
        : "You are tracking close to the baseline schedule with limited OD benefit at the moment.",
      icon: <LineChartIcon className="h-4 w-4" />,
      tone: aheadOfBaseline ? ("positive" as const) : ("neutral" as const),
      tier: "secondary" as const,
    },
  ];
}

function calculateHealthStatus({
  odOffset,
  outstanding,
  interestSaved,
  totalProjectedInterest,
  principalPaid,
  disbursed,
  currentRate,
  effectiveRate,
}: {
  odOffset: number;
  outstanding: number;
  interestSaved: number;
  totalProjectedInterest: number;
  principalPaid: number;
  disbursed: number;
  currentRate: number;
  effectiveRate: number;
}) {
  const odRatio = outstanding > 0 ? Math.min(1, odOffset / outstanding) : 0;
  const savingsRatio = totalProjectedInterest > 0 ? Math.min(1, interestSaved / totalProjectedInterest) : 0;
  const principalRatio = disbursed > 0 ? Math.min(1, principalPaid / disbursed) : 0;
  const rateRatio = currentRate > 0 ? Math.min(1, Math.max(0, currentRate - effectiveRate) / currentRate) : 0;
  const composite = 40 * odRatio + 25 * savingsRatio + 20 * principalRatio + 15 * rateRatio;

  if (composite >= 65) {
    return {
      label: "Excellent",
      badgeClass: "bg-emerald-200/20 text-emerald-100 ring-1 ring-emerald-200/25",
      summary: "OD utilization and current repayment pace are materially reducing borrowing cost.",
      reasons: [
        "Effective rate is meaningfully below the nominal rate.",
        "OD offset is keeping the interest-bearing balance lower.",
        "Savings generated so far are well above a normal passive schedule.",
      ],
    };
  }

  if (composite >= 35) {
    return {
      label: "Good",
      badgeClass: "bg-teal-200/20 text-teal-50 ring-1 ring-teal-200/25",
      summary: "Current OD support is producing visible savings without changing the underlying loan terms.",
      reasons: [
        "Effective rate improvement is present.",
        "OD balance is supporting interest savings on current principal.",
        "Repayment remains ahead of or close to the baseline path.",
      ],
    };
  }

  if (composite >= 15) {
    return {
      label: "Average",
      badgeClass: "bg-amber-200/20 text-amber-100 ring-1 ring-amber-200/25",
      summary: "Some efficiency is visible, but savings are still modest relative to the remaining balance.",
      reasons: [
        "OD support exists but is not yet dominant.",
        "Effective rate is only slightly below the nominal rate.",
        "Future interest remains a large component of total cost.",
      ],
    };
  }

  return {
    label: "Needs Attention",
    badgeClass: "bg-rose-200/20 text-rose-100 ring-1 ring-rose-200/25",
    summary: "Current structure is behaving close to the baseline loan with limited OD benefit.",
    reasons: [
      "OD balance is not materially reducing the interest-bearing principal.",
      "Rate efficiency is narrow.",
      "Most of the payoff is still dependent on scheduled EMI alone.",
    ],
  };
}

function sliceRows(rows: AmortizationRow[], startIndex: number, months: number | null) {
  if (months === null) {
    return rows.slice(startIndex);
  }

  return rows.slice(startIndex, startIndex + months);
}


function clampPercent(value: number) {
  return Math.max(0, Math.min(100, value));
}

function formatRemainingTenure(months: number) {
  const years = Math.floor(months / 12);
  const remaining = months % 12;

  if (years <= 0) {
    return `${remaining} Months`;
  }

  if (remaining === 0) {
    return `${years} Years`;
  }

  return `${years} Years ${remaining} Months`;
}

function formatMonthLabel(dateKey: string) {
  if (!dateKey) return "-";
  const date = new Date(dateKey);
  return date.toLocaleDateString("en-US", { month: "short", year: "numeric", timeZone: "UTC" });
}

function formatDueDate(dateKey: string) {
  if (!dateKey) return "-";
  const date = new Date(dateKey);
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric", timeZone: "UTC" });
}

function formatAxisShort(value: number) {
  if (value >= 100000) {
    return `${Math.round(value / 100000)}L`;
  }

  if (value >= 1000) {
    return `${Math.round(value / 1000)}k`;
  }

  return `${Math.round(value)}`;
}
