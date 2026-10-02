import { Info } from "lucide-react";
import { type ReactNode } from "react";

export default function EstimateNote({ children }: { children: ReactNode }) {
  return (
    <div className="flex items-start gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
      <Info className="mt-0.5 h-4 w-4 shrink-0 text-teal-700" />
      <p className="leading-6">{children}</p>
    </div>
  );
}
