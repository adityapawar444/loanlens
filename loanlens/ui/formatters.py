from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal


def format_inr(amount: Decimal) -> str:
    quantized = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    sign = "-" if quantized < 0 else ""
    digits = f"{abs(quantized):.2f}"
    integer_part, fractional_part = digits.split(".")
    if len(integer_part) > 3:
        head = integer_part[-3:]
        tail = integer_part[:-3]
        groups: list[str] = []
        while tail:
            groups.append(tail[-2:])
            tail = tail[:-2]
        integer_part = ",".join(reversed(groups)) + f",{head}"
    return f"{sign}₹ {integer_part}.{fractional_part}"


def format_date(d: date) -> str:
    return d.strftime("%d-%b-%Y").upper()


def format_pct(p: Decimal) -> str:
    return f"{p.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}%"


def format_months(n: int) -> str:
    years, months = divmod(n, 12)
    return f"{n} months ({years}y {months}m)"
