import { getLoanData } from "@/lib/actions";
import { getOdSavingsData } from "@/lib/od-savings-actions";
import OdSavingsClient from "./OdSavingsClient";

export const metadata = {
  title: "OD Savings | Home Loan Dashboard",
  description: "Track, allocate and monitor savings in your OD account by source and goal.",
};

export default async function OdSavingsPage() {
  const loanData = await getLoanData();
  const odData = await getOdSavingsData();
  return <OdSavingsClient loanData={loanData} odData={odData} />;
}
