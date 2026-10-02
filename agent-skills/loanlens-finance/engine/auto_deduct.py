"""
auto_deduct.py — Automatic payment deduction.

Port of calculations.ts autoDeductPayments (L305-387).
Modifies loanData and odData in-place.
"""

from __future__ import annotations

import random
import string

from .schedule import generate_schedule
from .types import (
    LoanData,
    OdBalanceAnnotation,
    OdBalanceLog,
    OdSavingsData,
    PaymentLog,
)


def _random_id() -> str:
    """Generate a 9-character alphanumeric ID matching JS Math.random().toString(36).slice(2, 11)."""
    chars = string.ascii_lowercase + string.digits
    return "".join(random.choice(chars) for _ in range(9))


def auto_deduct_payments(
    loan_data: LoanData,
    od_data: OdSavingsData,
    today_str: str,
) -> dict[str, bool]:
    """
    Automatically deducts due payments up to today_str.

    Modifies loan_data and od_data in-place.
    Returns {"loanChanged": bool, "odChanged": bool}.

    Matches calculations.ts autoDeductPayments (L305-387).
    """
    loan_changed = False
    od_changed = False

    while True:
        schedule = generate_schedule(loan_data)
        found = False

        for row in schedule:
            if row.dueDate > today_str:
                break  # Future due date

            # Check if payment already recorded
            has_payment = any(p.dueDate == row.dueDate for p in loan_data.paymentLog)
            if not has_payment:
                # 1. Determine available OD balance
                sorted_logs = sorted(loan_data.odBalanceLog, key=lambda l: l.date)
                prev_balance = 0.0
                for log in sorted_logs:
                    if log.date < row.dueDate:
                        prev_balance = log.balance
                    else:
                        break

                actual_deducted = min(row.installment, prev_balance)
                new_balance = prev_balance - actual_deducted

                # 2. Add entry to paymentLog
                loan_data.paymentLog.append(
                    PaymentLog(
                        id=_random_id(),
                        dueDate=row.dueDate,
                        type="pre_emi_interest" if row.phase == "moratorium" else "emi",
                        amountDue=row.installment,
                        amountPaid=actual_deducted,
                        paidDate=row.dueDate,
                    )
                )
                loan_changed = True

                # 3. Add entry to odBalanceLog if no snapshot exists
                has_od_log = any(log.date == row.dueDate for log in loan_data.odBalanceLog)
                if not has_od_log:
                    od_log_id = _random_id()
                    loan_data.odBalanceLog.append(
                        OdBalanceLog(
                            id=od_log_id,
                            date=row.dueDate,
                            balance=new_balance,
                        )
                    )

                    # 4. Add annotation
                    note = "Auto-deducted on EMI Day"
                    if actual_deducted < row.installment:
                        note += f" (Partial payment: {actual_deducted}/{row.installment})"

                    od_data.odBalanceAnnotations.append(
                        OdBalanceAnnotation(
                            odBalanceLogId=od_log_id,
                            sourceId=None,
                            purpose="EMI / Interest",
                            note=note,
                            editHistory=[],
                        )
                    )
                    od_changed = True

                found = True
                break  # Regenerate schedule

        if not found:
            break

    return {"loanChanged": loan_changed, "odChanged": od_changed}
