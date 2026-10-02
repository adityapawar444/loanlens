# LoanLens engine package
from .auto_deduct import auto_deduct_payments
from .emi import calculate_emi, calculate_tenure
from .metrics import calculate_metrics
from .renderer import (
    render_ledger,
    render_od_savings,
    render_schedule,
    render_simulator,
    render_summary,
)
from .schedule import generate_schedule
from .types import (
    AmortizationRow,
    LoanData,
    OdSavingsData,
    SummaryMetrics,
)

__all__ = [
    "calculate_emi",
    "calculate_tenure",
    "generate_schedule",
    "calculate_metrics",
    "auto_deduct_payments",
    "render_summary",
    "render_od_savings",
    "render_schedule",
    "render_simulator",
    "render_ledger",
    "LoanData",
    "AmortizationRow",
    "SummaryMetrics",
    "OdSavingsData",
]
