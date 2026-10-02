"""
types.py — Pydantic v2 models mirroring the Zod schemas in types.ts.

All money fields are plain floats/ints to match the TypeScript engine.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Loan Data Schemas
# ---------------------------------------------------------------------------


class Disbursement(BaseModel):
    id: str
    date: str
    amount: float
    note: Optional[str] = None


class RateHistory(BaseModel):
    id: str
    effectiveDate: str
    annualRate: float
    benchmark: Optional[str] = None
    spread: Optional[float] = None


class OdBalanceLog(BaseModel):
    id: str
    date: str
    balance: float


class Prepayment(BaseModel):
    id: str
    date: str
    amount: float
    note: Optional[str] = None


class PaymentLog(BaseModel):
    id: str
    dueDate: str
    type: Literal["pre_emi_interest", "emi"]
    amountDue: float
    amountPaid: float
    paidDate: str


class Policy(BaseModel):
    onPrepayment: Literal["adjust_tenure", "adjust_emi"]


class LoanDetails(BaseModel):
    lender: str
    accountNumber: str
    sanctionedAmount: float
    totalTenureMonths: int
    moratoriumMonths: int
    moratoriumAnchor: Literal["first_disbursement", "account_opening"]
    dueDateDay: int
    dayCountConvention: int = 365
    currentCommunicatedEmi: float
    policy: Policy


class LoanData(BaseModel):
    loanDetails: LoanDetails
    disbursements: list[Disbursement]
    rateHistory: list[RateHistory]
    odBalanceLog: list[OdBalanceLog]
    prepayments: list[Prepayment]
    paymentLog: list[PaymentLog]


# ---------------------------------------------------------------------------
# Output types (non-validated, plain models)
# ---------------------------------------------------------------------------


class AmortizationRow(BaseModel):
    period: int
    dueDate: str
    openingBalance: float
    installment: float
    interest: float
    baselineInterest: float
    interestSavings: float
    principal: float
    closingBalance: float
    phase: Literal["moratorium", "emi"]
    effectivePrincipal: float


class SummaryMetrics(BaseModel):
    currentPhase: Literal["moratorium", "emi"]
    outstandingPrincipal: float
    effectivePrincipal: float
    effectiveInterestRate: float
    nextDueDate: str
    nextInstallmentAmount: float
    projectedEmi: float
    projectedClosureDate: str
    interestPaidToDate: float
    principalPaidToDate: float
    totalInterestProjected: float
    interestSavedTillNow: float
    interestSavedThisYear: float
    disbursedAmount: float
    sanctionedAmount: float


# ---------------------------------------------------------------------------
# OD Savings types (needed by auto_deduct)
# ---------------------------------------------------------------------------


class AuditRecord(BaseModel):
    timestamp: str
    field: str
    oldValue: str
    newValue: str


class OdSource(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    isActive: bool = True
    createdAt: str
    editHistory: list[AuditRecord] = Field(default_factory=list)


class OdGoal(BaseModel):
    id: str
    name: str
    targetAmount: float
    allocatedAmount: float = 0
    targetDate: Optional[str] = None
    color: str = "#0f766e"
    note: Optional[str] = None
    isActive: bool = True
    editHistory: list[AuditRecord] = Field(default_factory=list)


class OdContribution(BaseModel):
    id: str
    date: str
    amount: float
    sourceId: str
    note: Optional[str] = None
    editHistory: list[AuditRecord] = Field(default_factory=list)


class OdBalanceAnnotation(BaseModel):
    odBalanceLogId: str
    sourceId: Optional[str] = None
    purpose: str = "savings"
    note: Optional[str] = None
    editHistory: list[AuditRecord] = Field(default_factory=list)


class OdSavingsData(BaseModel):
    emiReserve: float = 91143
    sources: list[OdSource] = Field(default_factory=list)
    contributions: list[OdContribution] = Field(default_factory=list)
    goals: list[OdGoal] = Field(default_factory=list)
    odBalanceAnnotations: list[OdBalanceAnnotation] = Field(default_factory=list)
