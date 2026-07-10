"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { 
  Menu, 
  X, 
  LayoutDashboard, 
  ReceiptText, 
  CalendarRange, 
  Calculator, 
  PiggyBank,
  Settings as SettingsIcon 
} from "lucide-react";

const links = [
  { href: "/", label: "Summary", icon: LayoutDashboard },
  { href: "/ledger", label: "Ledger", icon: ReceiptText },
  { href: "/od-savings", label: "OD Savings", icon: PiggyBank },
  { href: "/schedule", label: "Schedule", icon: CalendarRange },
  { href: "/simulator", label: "Simulator", icon: Calculator },
  { href: "/settings", label: "Settings", icon: SettingsIcon },
];

export default function NavigationDrawer() {
  const [isOpen, setIsOpen] = useState(false);
  const pathname = usePathname();
  const drawerRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    const drawer = drawerRef.current;
    if (!drawer) {
      return;
    }

    const focusable = drawer.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    const first = focusable[0];
    const last = focusable[focusable.length - 1];

    first?.focus();

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        setIsOpen(false);
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
  }, [isOpen]);

  return (
    <>
      <button
        onClick={() => setIsOpen(true)}
        aria-haspopup="dialog"
        aria-expanded={isOpen}
        aria-controls="navigation-drawer"
        className="rounded-xl border border-slate-200 bg-white p-2 -ml-2 text-slate-500 shadow-sm transition-colors hover:border-teal-200 hover:text-teal-700 focus:outline-none focus:ring-2 focus:ring-teal-200"
      >
        <Menu className="h-6 w-6" />
      </button>

      {isOpen && (
        <div 
          className="fixed inset-0 z-40 bg-slate-950/45 backdrop-blur-sm transition-opacity"
          onClick={() => setIsOpen(false)}
          aria-hidden="true"
        />
      )}

      <aside
        id="navigation-drawer"
        ref={drawerRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="navigation-drawer-title"
        className={`fixed top-0 left-0 z-50 h-full w-80 border-r border-slate-200 bg-white shadow-[20px_0_60px_rgba(15,23,42,0.18)] transform transition-transform duration-300 ease-in-out ${
          isOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex flex-col h-full">
          <div className="border-b border-slate-200 bg-[linear-gradient(135deg,#f8fafc_0%,#eef6f7_100%)] px-6 py-5">
            <div className="flex items-center justify-between">
              <div>
                <h2 id="navigation-drawer-title" className="text-sm font-semibold uppercase tracking-[0.22em] text-slate-500">Menu</h2>
                <p className="mt-1 text-xs text-slate-600">Navigate the dashboard sections</p>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                aria-label="Close navigation drawer"
                className="rounded-lg p-2 -mr-2 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700 focus:outline-none focus:ring-2 focus:ring-teal-200"
              >
                <X className="h-6 w-6" />
              </button>
            </div>
          </div>

          <nav className="flex-1 px-4 py-6 space-y-2 bg-white">
            {links.map((link) => {
              const Icon = link.icon;
              const isActive = pathname === link.href;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={() => setIsOpen(false)}
                  className={`flex items-center gap-3 rounded-2xl border px-4 py-3 text-sm font-medium transition-colors ${
                    isActive 
                      ? "border-teal-100 bg-teal-50 text-teal-800 shadow-sm" 
                      : "border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:bg-slate-50 hover:text-slate-950"
                  }`}
                >
                  <span className={`rounded-xl p-2 ${isActive ? "bg-white text-teal-700" : "bg-slate-50 text-slate-400"}`}>
                    <Icon className="h-4 w-4" />
                  </span>
                  {link.label}
                </Link>
              );
            })}
          </nav>

          <div className="border-t border-slate-200 p-6 bg-slate-50">
            <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
               <p className="mb-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-400">Status</p>
               <p className="text-sm font-medium text-slate-950">Live dashboard active</p>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
