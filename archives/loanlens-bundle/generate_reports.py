#!/usr/bin/env python3
"""
generate_reports.py — Pre-render Tier C fallback reports from current loan data.

Pins today_date to 2026-09-19.
Redacts PII: account number → [REDACTED], source names → Source 1 / Source 2 / etc.
Writes 4 report files to loanlens-bundle/reports/.
"""

import copy
import json
import os
import sys

# Ensure the bundle root is on the path
BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BUNDLE_DIR)

from engine.renderer import render_ledger, render_od_savings, render_schedule, render_summary
from engine.types import LoanData, OdSavingsData

TODAY = "2026-09-19"
REPORTS_DIR = os.path.join(BUNDLE_DIR, "reports")
DATA_DIR = os.path.join(BUNDLE_DIR, "data")


def load_json(filename: str) -> dict:
    path = os.path.join(DATA_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def redact_loan_data(raw: dict) -> dict:
    """Remove account number from loanDetails."""
    data = copy.deepcopy(raw)
    if "loanDetails" in data:
        data["loanDetails"]["accountNumber"] = "[REDACTED]"
    return data


def redact_od_data(raw: dict) -> dict:
    """Replace source names with generic labels (Source 1, Source 2, ...).
    Also redact goal names that contain known PII terms."""
    data = copy.deepcopy(raw)

    # PII terms to scan for in goal names (case-insensitive)
    PII_TERMS = {"aditya", "shravi", "neha", "pawar"}

    # Redact sources: Source 1, Source 2, ...
    sources = data.get("sources", [])
    for i, src in enumerate(sources, start=1):
        src["name"] = f"Source {i}"
        src["description"] = None  # drop description (may contain names)

    # Redact goal names that contain PII terms
    goals = data.get("goals", [])
    goal_counter = 1
    for goal in goals:
        name = goal.get("name", "")
        if any(term in name.lower() for term in PII_TERMS):
            goal["name"] = f"Goal {goal_counter}"
            # Also scrub editHistory field entries that may store old names
            for record in goal.get("editHistory", []):
                if record.get("field") == "name":
                    record["oldValue"] = "[REDACTED]"
                    record["newValue"] = "[REDACTED]"
        goal_counter += 1

    return data


def write_report(name: str, content: str) -> None:
    os.makedirs(REPORTS_DIR, exist_ok=True)
    path = os.path.join(REPORTS_DIR, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    token_est = len(content) // 4
    print(f"  Wrote {name} ({len(content)} bytes, ~{token_est} tokens)")


def main() -> None:
    print(f"Loading data (today={TODAY}) ...")

    raw_loan = load_json("loan_data.json")
    raw_od = load_json("od_savings_data.json")

    # Redact PII
    clean_loan = redact_loan_data(raw_loan)
    clean_od = redact_od_data(raw_od)

    # Parse into Pydantic models
    loan_data = LoanData(**clean_loan)
    od_data = OdSavingsData(**clean_od)

    print("Rendering reports ...")

    # R1 — Summary (≤400 tokens)
    summary = render_summary(loan_data, od_data, TODAY)
    write_report("summary_20260919.md", summary)

    # R2 — OD Savings (≤600 tokens)
    od_savings = render_od_savings(loan_data, od_data, TODAY)
    write_report("od_savings_20260919.md", od_savings)

    # R3 — Schedule (≤800 tokens)
    schedule = render_schedule(loan_data, TODAY, window=6)
    write_report("schedule_20260919.md", schedule)

    # R5 — Ledger (≤500 tokens)
    ledger = render_ledger(loan_data, od_data, TODAY)
    write_report("ledger_20260919.md", ledger)

    print("\nVerifying ...")
    files = os.listdir(REPORTS_DIR)
    print(f"  Report count: {len(files)} (need 4)")

    # PII check
    pii_terms = ["83990600004041", "Aditya", "Shravi", "Pawar"]
    for fname in files:
        fpath = os.path.join(REPORTS_DIR, fname)
        content = open(fpath).read()
        for term in pii_terms:
            if term.lower() in content.lower():
                print(f"  FAIL: PII '{term}' found in {fname}")
                sys.exit(1)

    print("  PASS: No PII found")
    print("\nDone.")


if __name__ == "__main__":
    main()
