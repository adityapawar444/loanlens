import type { Metadata } from "next";
import { Manrope } from "next/font/google";
import "./globals.css";
import NavigationDrawer from "@/components/NavigationDrawer";

const manrope = Manrope({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Home Loan Dashboard",
  description: "Track and simulate your home loan with OD account",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${manrope.className} min-h-screen bg-slate-100 text-slate-900 antialiased`}>
        <div className="flex min-h-screen flex-col">
          {/* Header */}
          <header className="sticky top-0 z-30 flex h-16 shrink-0 items-center border-b border-slate-200/80 bg-white/85 px-4 backdrop-blur md:px-8">
            <NavigationDrawer />
            <div className="ml-4">
              <h1 className="text-sm font-semibold tracking-[0.22em] text-slate-950 uppercase">LoanTracker</h1>
              <p className="text-[11px] text-slate-500">Home loan dashboard</p>
            </div>
          </header>

          {/* Main Content */}
          <main className="flex-1 bg-[radial-gradient(circle_at_top,_rgba(15,118,110,0.08),_transparent_35%),linear-gradient(180deg,#f8fafc_0%,#eef3f6_100%)] print:bg-white">
            <div className="mx-auto w-full max-w-[1400px] p-4 md:p-8 print:max-w-none print:p-0">
              {children}
            </div>
          </main>
        </div>
      </body>
    </html>
  );
}
