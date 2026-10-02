import { getLoanData, updateLoanDetails } from "@/lib/actions";

export default async function SettingsPage() {
  const loanData = await getLoanData();
  const details = loanData.loanDetails;

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <div>
        <div className="inline-flex items-center rounded-full border border-slate-200 bg-white px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-500">
          Configuration
        </div>
        <h2 className="mt-3 text-2xl font-semibold tracking-tight text-slate-950">Settings</h2>
        <p className="mt-1 text-sm text-slate-600">Configure loan parameters and recalculation policies.</p>
      </div>

      <div className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-[0_12px_45px_rgba(15,23,42,0.05)] md:p-8">
        <form action={updateLoanDetails} className="space-y-6">
          <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
            <div className="col-span-2">
              <label className="block text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Lender name</label>
              <input name="lender" defaultValue={details.lender} className="mt-2 block w-full rounded-2xl border border-slate-200 bg-slate-50 p-3 text-sm shadow-sm outline-none transition-colors focus:border-teal-300 focus:ring-4 focus:ring-teal-100" />
            </div>
            <div>
              <label className="block text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Sanctioned amount</label>
              <input name="sanctionedAmount" type="number" defaultValue={details.sanctionedAmount} className="mt-2 block w-full rounded-2xl border border-slate-200 bg-slate-50 p-3 text-sm shadow-sm outline-none transition-colors focus:border-teal-300 focus:ring-4 focus:ring-teal-100" />
            </div>
            <div>
              <label className="block text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Total tenure (months)</label>
              <input name="totalTenureMonths" type="number" defaultValue={details.totalTenureMonths} className="mt-2 block w-full rounded-2xl border border-slate-200 bg-slate-50 p-3 text-sm shadow-sm outline-none transition-colors focus:border-teal-300 focus:ring-4 focus:ring-teal-100" />
            </div>
            <div>
              <label className="block text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Moratorium months</label>
              <input name="moratoriumMonths" type="number" defaultValue={details.moratoriumMonths} className="mt-2 block w-full rounded-2xl border border-slate-200 bg-slate-50 p-3 text-sm shadow-sm outline-none transition-colors focus:border-teal-300 focus:ring-4 focus:ring-teal-100" />
            </div>
            <div>
              <label className="block text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">EMI due day</label>
              <input name="dueDateDay" type="number" defaultValue={details.dueDateDay} className="mt-2 block w-full rounded-2xl border border-slate-200 bg-slate-50 p-3 text-sm shadow-sm outline-none transition-colors focus:border-teal-300 focus:ring-4 focus:ring-teal-100" />
            </div>
          </div>

          <div className="border-t border-slate-200 pt-6">
             <h4 className="mb-4 text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-500">Recalculation policies</h4>
             <div className="space-y-4">
                <PolicySelect label="On Rate Change" name="policy.onRateChange" defaultValue={details.policy.onRateChange} />
                <PolicySelect label="On Prepayment" name="policy.onPrepayment" defaultValue={details.policy.onPrepayment} />
             </div>
          </div>

          <div className="pt-6">
            <button type="submit" className="w-full rounded-2xl bg-slate-950 px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-slate-200 transition-colors hover:bg-teal-700">
              Save Settings
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function PolicySelect({ label, name, defaultValue }: { label: string, name: string, defaultValue: string }) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
       <label className="text-sm font-medium text-slate-700">{label}</label>
       <select name={name} defaultValue={defaultValue} className="rounded-xl border border-slate-200 bg-white p-2 text-sm shadow-sm outline-none transition-colors focus:border-teal-300 focus:ring-4 focus:ring-teal-100">
          <option value="adjust_tenure">Keep EMI fixed, adjust tenure</option>
          <option value="adjust_emi">Keep tenure fixed, adjust EMI</option>
       </select>
    </div>
  )
}
