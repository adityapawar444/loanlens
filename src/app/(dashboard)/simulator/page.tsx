import { getLoanData } from "@/lib/actions";
import SimulatorClient from "./SimulatorClient";

export default async function SimulatorPage() {
  const loanData = await getLoanData();
  const todayStr = new Date().toISOString().split("T")[0];

  return (
    <div className="space-y-6">
      <div>
        <div className="inline-flex items-center rounded-full border border-slate-200 bg-white px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-500">
          What-if analysis
        </div>
        <h2 className="mt-3 text-2xl font-semibold tracking-tight text-slate-950">Scenario simulator</h2>
        <p className="mt-1 text-sm text-slate-600">Preview the impact of prepayments, rate changes, or new disbursements.</p>
      </div>

      <SimulatorClient baseData={loanData} todayStr={todayStr} />
    </div>
  );
}
