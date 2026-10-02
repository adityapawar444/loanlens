"""
emi.py — EMI and tenure calculations.

CRITICAL: Python's built-in round() uses banker's rounding (round half to even).
JS Math.round() uses half-up rounding. We use math.floor(x + 0.5) to match JS.
"""

from __future__ import annotations

import math


def _js_round(x: float) -> int:
    """Match JavaScript's Math.round() — half-up rounding, not banker's."""
    return int(math.floor(x + 0.5))


def calculate_emi(principal: float, annual_rate: float, tenure_months: int) -> int:
    """
    Calculate monthly EMI based on reducing balance method.

    Returns rounded EMI (half-up, matching JS Math.round).
    """
    if tenure_months <= 0:
        return 0
    r = annual_rate / 12 / 100
    if r == 0:
        return principal / tenure_months
    emi = (principal * r * math.pow(1 + r, tenure_months)) / (math.pow(1 + r, tenure_months) - 1)
    return _js_round(emi)


def calculate_tenure(principal: float, annual_rate: float, emi: int) -> int | float:
    """
    Calculate remaining tenure based on a fixed EMI.

    Returns ceil(tenure) or math.inf if the loan can never be paid off.
    """
    if principal <= 0:
        return 0
    r = annual_rate / 12 / 100
    if r == 0:
        return principal / emi

    if emi <= principal * r:
        return math.inf

    x = emi / (emi - principal * r)
    tenure = math.log(x) / math.log(1 + r)
    return math.ceil(tenure)
