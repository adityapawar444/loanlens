"use client";

import { Info } from "lucide-react";
import { type ReactNode, useId } from "react";

export default function HelpTooltip({
  content,
  label = "More information",
}: {
  content: ReactNode;
  label?: string;
}) {
  const id = useId();

  return (
    <span className="group relative inline-flex align-middle">
      <button
        type="button"
        aria-describedby={id}
        aria-label={label}
        className="inline-flex h-4 w-4 items-center justify-center rounded-full text-slate-400 transition-colors hover:text-slate-700 focus:outline-none focus:ring-2 focus:ring-teal-200"
      >
        <Info className="h-3.5 w-3.5" />
      </button>
      <span
        id={id}
        role="tooltip"
        className="pointer-events-none absolute left-1/2 top-full z-40 mt-2 hidden w-72 -translate-x-1/2 rounded-2xl border border-slate-200 bg-slate-950 px-3 py-2 text-left text-xs font-medium leading-5 text-slate-100 shadow-2xl group-hover:block group-focus-within:block"
      >
        {content}
      </span>
    </span>
  );
}
