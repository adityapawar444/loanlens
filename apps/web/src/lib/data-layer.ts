import fs from "fs/promises";
import path from "path";
import { LoanData, LoanDataSchema } from "./types";
import { autoDeductPayments } from "./calculations";
import { readOdData, writeOdData } from "./od-savings-data-layer";

const DATA_FILE = path.join(process.cwd(), "data", "loan_data.json");

export async function readData(): Promise<LoanData> {
  try {
    const content = await fs.readFile(DATA_FILE, "utf-8");
    const data = JSON.parse(content);
    const loanData = LoanDataSchema.parse(data);

    // Run auto-deductions using server's current local date
    const today = new Date();
    const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
    
    const odData = await readOdData();
    const { loanChanged, odChanged } = autoDeductPayments(loanData, odData, todayStr);
    
    if (loanChanged) {
      const validatedLoanData = LoanDataSchema.parse(loanData);
      await fs.writeFile(DATA_FILE, JSON.stringify(validatedLoanData, null, 2), "utf-8");
    }
    if (odChanged) {
      await writeOdData(odData);
    }

    return loanData;
  } catch (error) {
    console.error("Error reading data:", error);
    throw new Error("Failed to read loan data");
  }
}

export async function writeData(data: LoanData): Promise<void> {
  try {
    const validatedData = LoanDataSchema.parse(data);
    await fs.writeFile(DATA_FILE, JSON.stringify(validatedData, null, 2), "utf-8");
  } catch (error) {
    console.error("Error writing data:", error);
    throw new Error("Failed to write loan data");
  }
}
