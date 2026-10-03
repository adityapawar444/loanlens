import { describe, it, expect, vi, beforeEach } from "vitest";
import { updatePayment } from "./actions";

// Mock next/cache
vi.mock("next/cache", () => ({
  revalidatePath: vi.fn(),
}));

// We'll mock the data layer to return our test objects and spy on write calls
let mockLoanData: any;
let mockOdData: any;

vi.mock("@/lib/data-layer", () => ({
  readData: vi.fn(() => Promise.resolve(mockLoanData)),
  writeData: vi.fn((data) => {
    mockLoanData = data;
    return Promise.resolve();
  }),
}));

vi.mock("@/lib/od-savings-data-layer", () => ({
  readOdData: vi.fn(() => Promise.resolve(mockOdData)),
  writeOdData: vi.fn((data) => {
    mockOdData = data;
    return Promise.resolve();
  }),
}));

describe("updatePayment", () => {
  beforeEach(() => {
    mockLoanData = {
      paymentLog: [
        { id: "p1", amountDue: 50000, amountPaid: 0 },
      ],
    };
    mockOdData = {
      emiReserveAllocated: 50000,
    };
    vi.clearAllMocks();
  });

  it("should deduct the newly paid EMI amount from the emiReserveAllocated", async () => {
    // When the user pays 50000
    await updatePayment("p1", 50000);

    // The payment log should be updated
    expect(mockLoanData.paymentLog[0].amountPaid).toBe(50000);

    // The reserve should be drained by exactly 50000
    expect(mockOdData.emiReserveAllocated).toBe(0);
  });

  it("should deduct only the difference if the payment is updated", async () => {
    // Initially the user already paid 40000
    mockLoanData.paymentLog[0].amountPaid = 40000;
    
    // They update it to 50000
    await updatePayment("p1", 50000);

    // Only 10000 more should be deducted from the reserve
    expect(mockOdData.emiReserveAllocated).toBe(40000); // 50000 - 10000
  });

  it("should cap the reserve deduction at 0 (never go negative)", async () => {
    mockOdData.emiReserveAllocated = 10000;
    
    // The user pays 50000
    await updatePayment("p1", 50000);

    // The reserve shouldn't drop below 0
    expect(mockOdData.emiReserveAllocated).toBe(0);
  });
});
