import { getLoanData, updatePayment, updateAmountDue } from "@/lib/actions";
import { PaymentLog } from "@/lib/types";
import { Banknote, Clock3, Landmark, Wallet } from "lucide-react";
import LedgerForms from "./LedgerForms";

// Historical months where amountDue must be manually set to the bank's statement figure
const HISTORICAL_PAYMENT_DATES = new Set([
  "2026-02-10",
  "2026-03-10",
  "2026-04-10",
  "2026-05-10",
  "2026-06-10",
]);

export default async function LedgerPage() {
  const loanData = await getLoanData();
  const formatter = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" });

  return (
    <div className="space-y-6">
      <div>
        <div className="inline-flex items-center rounded-full border border-slate-200 bg-white px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-500">
          Operations
        </div>
        <h2 className="mt-3 text-2xl font-semibold tracking-tight text-slate-950">Ledger</h2>
        <p className="mt-1 text-sm text-slate-600">Manage disbursements, OD snapshots, and actual payment postings with lower-friction operational views.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <MetricCard icon={<Clock3 className="h-4 w-4" />} title="Payment rows" value={`${loanData.paymentLog.length}`} helper="Statement-backed entries" />
        <MetricCard icon={<Landmark className="h-4 w-4" />} title="Disbursements" value={`${loanData.disbursements.length}`} helper="Funding events recorded" />
        <MetricCard icon={<Wallet className="h-4 w-4" />} title="OD snapshots" value={`${loanData.odBalanceLog.length}`} helper="Used for effective balance tracking" />
      </div>

      <LedgerForms />

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <section className="rounded-[28px] border border-slate-200 bg-white p-5 shadow-[0_12px_45px_rgba(15,23,42,0.05)]">
          <h3 className="text-base font-semibold tracking-tight text-slate-950">Payment History</h3>
          <p className="mt-1 text-sm text-slate-600">For Feb–Jun 2026, set the <span className="font-semibold text-amber-600">Due</span> field to the bank&apos;s actual scheduled charge so savings are calculated correctly.</p>
          <div className="mt-4 space-y-3">
            {loanData.paymentLog.map((payment) => {
              const isHistorical = HISTORICAL_PAYMENT_DATES.has(payment.dueDate);
              const dueNotSet = isHistorical && payment.amountDue === payment.amountPaid;
              const saved = payment.amountDue - payment.amountPaid;
              return (
                <div key={payment.id} className={`rounded-2xl border px-4 py-3 ${dueNotSet ? "border-amber-200 bg-amber-50" : "border-slate-200 bg-slate-50"}`}>
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">{payment.dueDate}</p>
                        {dueNotSet && (
                          <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-amber-600">
                            Due needed
                          </span>
                        )}
                      </div>
                      <p className="mt-1 text-sm font-semibold text-slate-950">{formatter.format(payment.amountPaid)} paid</p>
                      <p className="mt-0.5 text-xs text-slate-500">
                        Due {formatter.format(payment.amountDue)} • Paid on {payment.paidDate}
                      </p>
                      {saved > 0 ? (
                        <p className="mt-1 text-[11px] font-semibold text-emerald-700">
                          Saved {formatter.format(saved)} vs schedule
                        </p>
                      ) : dueNotSet ? (
                        <p className="mt-1 text-[11px] text-amber-600">
                          Enter the bank&apos;s scheduled due above to compute savings
                        </p>
                      ) : null}
                    </div>
                    <PaymentEditButton payment={payment} />
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        <section className="space-y-5">
          <DataSection
            icon={<Banknote className="h-4 w-4" />}
            title="Disbursements"
            rows={loanData.disbursements.map((disbursement) => ({
              id: disbursement.id,
              title: formatter.format(disbursement.amount),
              meta: `${disbursement.date}${disbursement.note ? ` • ${disbursement.note}` : ""}`,
            }))}
          />

          <DataSection
            icon={<Wallet className="h-4 w-4" />}
            title="OD Balance Snapshots"
            rows={loanData.odBalanceLog.map((log) => ({
              id: log.id,
              title: formatter.format(log.balance),
              meta: log.date,
            }))}
          />
        </section>
      </div>
    </div>
  );
}

function MetricCard({
  icon,
  title,
  value,
  helper,
}: {
  icon: React.ReactNode;
  title: string;
  value: string;
  helper: string;
}) {
  return (
    <div className="rounded-[24px] border border-slate-200 bg-white p-4 shadow-[0_12px_45px_rgba(15,23,42,0.05)]">
      <div className="flex items-center justify-between gap-3">
        <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">{title}</p>
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-2 text-teal-700">{icon}</div>
      </div>
      <p className="mt-3 text-2xl font-semibold tracking-tight text-slate-950">{value}</p>
      <p className="mt-1 text-sm text-slate-600">{helper}</p>
    </div>
  );
}

function DataSection({
  icon,
  title,
  rows,
}: {
  icon: React.ReactNode;
  title: string;
  rows: Array<{ id: string; title: string; meta: string }>;
}) {
  return (
    <section className="rounded-[28px] border border-slate-200 bg-white p-5 shadow-[0_12px_45px_rgba(15,23,42,0.05)]">
      <div className="flex items-center gap-2">
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-2 text-teal-700">{icon}</div>
        <h3 className="text-base font-semibold tracking-tight text-slate-950">{title}</h3>
      </div>
      <div className="mt-4 space-y-3">
        {rows.map((row) => (
          <div key={row.id} className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
            <p className="text-sm font-semibold text-slate-950">{row.title}</p>
            <p className="mt-1 text-xs text-slate-500">{row.meta}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function PaymentEditButton({ payment }: { payment: PaymentLog }) {
  const isHistorical = HISTORICAL_PAYMENT_DATES.has(payment.dueDate);
  const dueMatchesPaid = payment.amountDue === payment.amountPaid;

  return (
    <div className="flex flex-col gap-2 min-w-[160px]">
      {/* Amount Paid */}
      <form
        action={async (formData) => {
          "use server";
          const amount = Number(formData.get("amount"));
          await updatePayment(payment.id, amount);
        }}
        className="flex items-center gap-1.5"
      >
        <div className="flex flex-col gap-0.5 flex-1">
          <label className="text-[9px] font-semibold uppercase tracking-[0.16em] text-slate-400">Paid</label>
          <input
            name="amount"
            type="number"
            defaultValue={payment.amountPaid}
            className="w-full rounded-xl border border-slate-200 bg-white px-2.5 py-1.5 text-xs shadow-sm outline-none focus:border-teal-300 focus:ring-4 focus:ring-teal-100"
          />
        </div>
        <button
          type="submit"
          className="mt-4 rounded-xl bg-slate-950 px-2.5 py-1.5 text-[9px] font-semibold uppercase tracking-[0.14em] text-white transition-colors hover:bg-teal-700"
        >
          ✓
        </button>
      </form>

      {/* Amount Due (only editable for historical months) */}
      {isHistorical && (
        <form
          action={async (formData) => {
            "use server";
            const due = Number(formData.get("due"));
            await updateAmountDue(payment.id, due);
          }}
          className="flex items-center gap-1.5"
        >
          <div className="flex flex-col gap-0.5 flex-1">
            <label className="text-[9px] font-semibold uppercase tracking-[0.16em] text-amber-500 flex items-center gap-1">
              Due {dueMatchesPaid && <span className="text-amber-400 font-normal normal-case tracking-normal">(needs update)</span>}
            </label>
            <input
              name="due"
              type="number"
              defaultValue={payment.amountDue}
              className={`w-full rounded-xl border px-2.5 py-1.5 text-xs shadow-sm outline-none focus:ring-4 focus:ring-amber-100 ${
                dueMatchesPaid
                  ? "border-amber-300 bg-amber-50 focus:border-amber-400"
                  : "border-slate-200 bg-white focus:border-teal-300 focus:ring-teal-100"
              }`}
            />
          </div>
          <button
            type="submit"
            className={`mt-4 rounded-xl px-2.5 py-1.5 text-[9px] font-semibold uppercase tracking-[0.14em] text-white transition-colors ${
              dueMatchesPaid ? "bg-amber-500 hover:bg-amber-600" : "bg-slate-950 hover:bg-teal-700"
            }`}
          >
            ✓
          </button>
        </form>
      )}
    </div>
  );
}
