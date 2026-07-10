import { getLoanData } from "@/lib/actions";
import { generateSchedule } from "@/lib/calculations";
import Link from "next/link";
import AmortizationTable from "@/components/schedule/AmortizationTable";
import EstimateNote from "@/components/common/EstimateNote";

export default async function SchedulePage() {
  const loanData = await getLoanData();
  const today = new Date();
  const schedule = generateSchedule(loanData, today);

  const formatter = new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="inline-flex items-center rounded-full border border-slate-200 bg-white px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-500">
            Detailed schedule
          </div>
          <h2 className="mt-3 text-2xl font-semibold tracking-tight text-slate-950">Amortization schedule</h2>
          <p className="mt-1 text-sm text-slate-600">Month-by-month repayment breakdown with actual and baseline interest.</p>
        </div>
        <Link
          href="/"
          className="inline-flex items-center rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm transition-colors hover:bg-slate-50"
        >
          Back to dashboard
        </Link>
      </div>

      <EstimateNote>
        All values are estimates derived from the current disbursement ledger, ROI, OD snapshots, and payment history. Closing balance is the actual principal outstanding; effective balance is shown separately.
      </EstimateNote>

      <AmortizationTable rows={schedule} formatter={formatter} maxHeightClass="max-h-[72vh]" stickyHeader />
    </div>
  );
}
