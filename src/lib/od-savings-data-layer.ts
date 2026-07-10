import fs from "fs/promises";
import path from "path";
import { OdSavingsData, OdSavingsDataSchema } from "./od-savings-types";

const DATA_FILE = path.join(process.cwd(), "data", "od_savings_data.json");

export async function readOdData(): Promise<OdSavingsData> {
  try {
    const content = await fs.readFile(DATA_FILE, "utf-8");
    const raw = JSON.parse(content);
    return OdSavingsDataSchema.parse(raw);
  } catch {
    // Return a clean empty structure if the file is missing or malformed
    return OdSavingsDataSchema.parse({});
  }
}

export async function writeOdData(data: OdSavingsData): Promise<void> {
  const validated = OdSavingsDataSchema.parse(data);
  await fs.writeFile(DATA_FILE, JSON.stringify(validated, null, 2), "utf-8");
}
