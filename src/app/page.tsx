import { getLoanData } from "@/lib/actions";
import { calculateMetrics, generateSchedule } from "@/lib/calculations";
import DashboardClient from "@/components/dashboard/DashboardClient";

export default async function SummaryPage() {
  const loanData = await getLoanData();
  const today = new Date();
  const schedule = generateSchedule(loanData, today);
  const metrics = calculateMetrics(loanData, schedule, today);
  const todayStr = today.toISOString().split("T")[0];

  return <DashboardClient loanData={loanData} schedule={schedule} metrics={metrics} todayStr={todayStr} />;
}
