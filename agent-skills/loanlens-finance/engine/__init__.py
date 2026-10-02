# LoanLens engine package
from .auto_deduct import auto_deduct_payments
from .emi import calculate_emi, calculate_tenure
from .metrics import calculate_metrics
from .operations import validate_invariants
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
from .converter import toon_to_dict, dict_to_toon

def load_data(loan_toon: str, od_toon: str) -> tuple[LoanData, OdSavingsData]:
    loan_dict = toon_to_dict(loan_toon, "loan")
    od_dict = toon_to_dict(od_toon, "od")
    return LoanData(**loan_dict), OdSavingsData(**od_dict)

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
    "load_data",
    "toon_to_dict",
    "dict_to_toon",
    "validate_invariants",
]
