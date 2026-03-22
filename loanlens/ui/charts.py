from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from loanlens.models import ScheduleRow


def interest_vs_principal_chart(schedule: list[ScheduleRow]) -> str:
    grouped: dict[int, tuple[Decimal, Decimal]] = defaultdict(lambda: (Decimal("0"), Decimal("0")))
    for row in schedule:
        interest, principal = grouped[row.due_date.year]
        grouped[row.due_date.year] = (
            interest + row.interest_component,
            principal + row.principal_component + row.prepayment_amount,
        )

    lines: list[str] = []
    for year in sorted(grouped):
        interest, principal = grouped[year]
        total = max(interest + principal, Decimal("1"))
        interest_blocks = max(int((interest / total) * Decimal("20")), 1)
        principal_blocks = max(int((principal / total) * Decimal("20")), 1)
        lines.append(f"{year}: {'#' * interest_blocks}{'=' * principal_blocks}")
    return "\n".join(lines)


def principal_paydown_mini(schedule: list[ScheduleRow]) -> str:
    if not schedule:
        return ""
    closing_values = [row.closing_principal for row in schedule]
    max_value = max(closing_values)
    if max_value == Decimal("0"):
        return "▁"
    bars = "▁▂▃▄▅▆▇█"
    output: list[str] = []
    for value in closing_values[:: max(len(closing_values) // 12, 1)]:
        idx = int((value / max_value) * Decimal(len(bars) - 1))
        output.append(bars[idx])
    return "".join(output)
