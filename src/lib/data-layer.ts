import fs from "fs/promises";
import path from "path";
import { LoanData, LoanDataSchema } from "./types";

const DATA_FILE = path.join(process.cwd(), "data", "loan_data.json");

export async function readData(): Promise<LoanData> {
  try {
    const content = await fs.readFile(DATA_FILE, "utf-8");
    const data = JSON.parse(content);
    return LoanDataSchema.parse(data);
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
