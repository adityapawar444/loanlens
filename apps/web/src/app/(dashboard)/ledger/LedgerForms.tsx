"use client";

import { addDisbursement, addOdBalanceLog } from "@/lib/actions";
import { useEffect, useRef, useState } from "react";
import { Banknote, Landmark, Wallet, X } from "lucide-react";

export default function LedgerForms() {
  const [activeForm, setActiveForm] = useState<"disbursement" | "od" | null>(null);

  return (
    <div className="rounded-[28px] border border-slate-200 bg-white p-5 shadow-[0_12px_45px_rgba(15,23,42,0.05)]">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h3 className="text-base font-semibold tracking-tight text-slate-950">Ledger Actions</h3>
          <p className="mt-1 text-sm text-slate-600">Add new funding or OD snapshots without leaving the operations screen.</p>
        </div>
        <div className="flex flex-wrap gap-3">
          <button
            onClick={() => setActiveForm("disbursement")}
            className="rounded-2xl bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-slate-200 transition-colors hover:bg-teal-700"
          >
            Add Disbursement
          </button>
          <button
            onClick={() => setActiveForm("od")}
            className="rounded-2xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 shadow-sm transition-colors hover:border-teal-200 hover:text-teal-700"
          >
            Log OD Balance
          </button>
        </div>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <ActionHint
          icon={<Landmark className="h-4 w-4" />}
          title="Disbursement entries"
          body="Use when the lender releases a new tranche or backfill an earlier loan release event."
        />
        <ActionHint
          icon={<Wallet className="h-4 w-4" />}
          title="OD snapshots"
          body="Keep these updated for better effective-principal and interest-saving estimates."
        />
      </div>

      {activeForm === "disbursement" ? (
        <FormModal title="Add Disbursement" onClose={() => setActiveForm(null)}>
          <form
            action={async (formData) => {
              await addDisbursement({
                id: Math.random().toString(36).slice(2, 11),
                date: formData.get("date") as string,
                amount: Number(formData.get("amount")),
                note: formData.get("note") as string,
              });
              setActiveForm(null);
            }}
            className="space-y-4"
          >
            <Field label="Date">
              <input name="date" type="date" required className={inputClassName} />
            </Field>
            <Field label="Amount">
              <input name="amount" type="number" required className={inputClassName} />
            </Field>
            <Field label="Note">
              <input name="note" type="text" className={inputClassName} />
            </Field>
            <button type="submit" className="w-full rounded-2xl bg-slate-950 px-4 py-3 text-sm font-semibold text-white transition-colors hover:bg-teal-700">
              Save Disbursement
            </button>
          </form>
        </FormModal>
      ) : null}

      {activeForm === "od" ? (
        <FormModal title="Log OD Balance" onClose={() => setActiveForm(null)}>
          <form
            action={async (formData) => {
              await addOdBalanceLog({
                id: Math.random().toString(36).slice(2, 11),
                date: formData.get("date") as string,
                balance: Number(formData.get("balance")),
              });
              setActiveForm(null);
            }}
            className="space-y-4"
          >
            <Field label="Date">
              <input name="date" type="date" required className={inputClassName} />
            </Field>
            <Field label="Balance">
              <input name="balance" type="number" required className={inputClassName} />
            </Field>
            <button type="submit" className="w-full rounded-2xl bg-slate-950 px-4 py-3 text-sm font-semibold text-white transition-colors hover:bg-teal-700">
              Save Balance
            </button>
          </form>
        </FormModal>
      ) : null}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">{label}</label>
      <div className="mt-1.5">{children}</div>
    </div>
  );
}

function ActionHint({
  icon,
  title,
  body,
}: {
  icon: React.ReactNode;
  title: string;
  body: string;
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
      <div className="flex items-center gap-2">
        <div className="rounded-xl border border-slate-200 bg-white p-2 text-teal-700">{icon}</div>
        <p className="text-sm font-semibold text-slate-950">{title}</p>
      </div>
      <p className="mt-2 text-sm leading-6 text-slate-600">{body}</p>
    </div>
  );
}

function FormModal({ title, children, onClose }: { title: string; children: React.ReactNode; onClose: () => void }) {
  const panelRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
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
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 px-4 backdrop-blur-sm" onClick={onClose}>
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="ledger-form-title"
        className="relative w-full max-w-md rounded-[28px] border border-slate-200 bg-[linear-gradient(180deg,#ffffff_0%,#f8fafc_100%)] p-6 shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <button
          onClick={onClose}
          className="absolute right-4 top-4 rounded-lg p-2 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700"
        >
          <X className="h-4 w-4" />
        </button>
        <div className="mb-6 flex items-center gap-2">
          <Banknote className="h-4 w-4 text-teal-700" />
          <h3 id="ledger-form-title" className="text-base font-semibold tracking-tight text-slate-950">
            {title}
          </h3>
        </div>
        {children}
      </div>
    </div>
  );
}

const inputClassName =
  "block w-full rounded-2xl border border-slate-200 bg-white px-3 py-3 text-sm shadow-sm outline-none transition-colors focus:border-teal-300 focus:ring-4 focus:ring-teal-100";
