import HelpTooltip from "@/components/common/HelpTooltip";
import { AmortizationRow } from "@/lib/types";

export default function AmortizationTable({
  rows,
  formatter,
  maxHeightClass,
  stickyHeader = false,
}: {
  rows: AmortizationRow[];
  formatter: Intl.NumberFormat;
  maxHeightClass?: string;
  stickyHeader?: boolean;
}) {
  const totals = rows.reduce(
    (accumulator, row) => ({
      installments: accumulator.installments + row.installment,
      interest: accumulator.interest + row.interest,
      savings: accumulator.savings + row.interestSavings,
      principal: accumulator.principal + row.principal,
    }),
    { installments: 0, interest: 0, savings: 0, principal: 0 }
  );

  const stickyCellClass = stickyHeader ? "sticky left-0 z-30 bg-slate-50" : "";
  const stickyRowCellClass = stickyHeader ? "sticky left-0 z-10 bg-white" : "";
  const stickyFooterClass = stickyHeader ? "sticky left-0 z-10 bg-slate-50" : "";

  return (
    <div className="overflow-hidden rounded-[28px] border border-slate-200 bg-white shadow-[0_12px_45px_rgba(15,23,42,0.05)]">
      <div className={`overflow-auto ${maxHeightClass ?? ""}`}>
        <table className="w-full text-left text-sm">
          <thead className={`border-b border-slate-200 bg-slate-50 text-[11px] uppercase tracking-[0.18em] text-slate-500 ${stickyHeader ? "sticky top-0 z-20" : ""}`}>
            <tr>
              <th className={`px-4 py-3 text-center ${stickyCellClass}`}>Period</th>
              <th className="px-4 py-3">Due Date</th>
              <th className="px-4 py-3">Opening Bal</th>
              <th className="px-4 py-3">Installment</th>
              <th className="px-4 py-3">Interest (Actual)</th>
              <th className="px-4 py-3">Interest (Baseline)</th>
              <th className="px-4 py-3 text-teal-700">
                <div className="flex items-center gap-1.5">
                  <span>Savings</span>
                  <HelpTooltip content="Interest avoided because of OD offset." />
                </div>
              </th>
              <th className="px-4 py-3">Principal</th>
              <th className="px-4 py-3">
                <div className="flex items-center gap-1.5">
                  <span>Effective Bal</span>
                  <HelpTooltip content="Interest-bearing balance after OD adjustment." />
                </div>
              </th>
              <th className="px-4 py-3">Closing Bal</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {rows.map((row) => (
              <tr key={row.period} className="hover:bg-slate-50/80">
                <td className={`px-4 py-2.5 text-center font-medium text-slate-900 ${stickyRowCellClass}`}>{row.period}</td>
                <td className="px-4 py-2.5 text-slate-600">{row.dueDate}</td>
                <td className="px-4 py-2.5 font-mono text-xs text-slate-600">{formatter.format(row.openingBalance)}</td>
                <td className="px-4 py-2.5 font-semibold text-slate-950">{formatter.format(row.installment)}</td>
                <td className="px-4 py-2.5 font-medium text-slate-900">{formatter.format(row.interest)}</td>
                <td className="px-4 py-2.5 text-xs text-slate-400 line-through">{formatter.format(row.baselineInterest)}</td>
                <td className="px-4 py-2.5 font-medium text-emerald-700">{formatter.format(row.interestSavings)}</td>
                <td className="px-4 py-2.5 text-teal-700">{formatter.format(row.principal)}</td>
                <td className="px-4 py-2.5 font-mono text-xs text-slate-600">{formatter.format(row.effectivePrincipal)}</td>
                <td className="px-4 py-2.5 font-mono text-xs font-medium text-slate-900">{formatter.format(row.closingBalance)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot className="border-t border-slate-200 bg-slate-50">
            <tr>
              <td className={`px-4 py-3 text-center font-semibold text-slate-950 ${stickyFooterClass}`}>Totals</td>
              <td className="px-4 py-3 text-slate-500">{rows.length} rows</td>
              <td className="px-4 py-3 text-slate-500">-</td>
              <td className="px-4 py-3 font-semibold text-slate-950">{formatter.format(totals.installments)}</td>
              <td className="px-4 py-3 font-semibold text-slate-950">{formatter.format(totals.interest)}</td>
              <td className="px-4 py-3 text-slate-500">-</td>
              <td className="px-4 py-3 font-semibold text-emerald-700">{formatter.format(totals.savings)}</td>
              <td className="px-4 py-3 font-semibold text-teal-700">{formatter.format(totals.principal)}</td>
              <td className="px-4 py-3 text-slate-500">-</td>
              <td className="px-4 py-3 text-slate-500">-</td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );
}
