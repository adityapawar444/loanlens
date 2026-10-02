"""
converter.py — JSON ↔ TOON conversion for LoanLens data.

TOON (Token-Optimized Object Notation) spec (from 02-design.md §A):
  [N] entity_name
  col1:type\tcol2:type\t...
  val1\tval2\t...
  ...

Types: str, num, date, bool, json
Null/missing → empty cell
Booleans → 1/0
Dates → YYYY-MM-DD (stored as str type since they look like plain strings)
Strings with tabs/newlines → JSON-encoded (prefixed with '"')
Nested arrays (editHistory) → json type column
"""

from __future__ import annotations

import copy
import json
import re
from typing import Any

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_REDACTED = "[REDACTED]"


def _cell_to_str(value: Any, typ: str) -> str:
    """Encode a Python value to a TOON cell string."""
    if value is None:
        return ""
    if typ == "bool":
        return "1" if value else "0"
    if typ == "json":
        # Compact JSON, no extra whitespace
        return json.dumps(value, separators=(",", ":"), ensure_ascii=False)
    # str, num, date
    s = str(value)
    # If the string itself contains a tab or newline, JSON-encode it
    if "\t" in s or "\n" in s or "\r" in s:
        return json.dumps(s, ensure_ascii=False)
    return s


def _cell_from_str(cell: str, typ: str) -> Any:
    """Decode a TOON cell string back to a Python value.

    Type semantics for empty cells:
      - nullable_str  -> None   (field is string | null; empty means null)
      - str, date     -> ""     (non-nullable string; empty string is valid)
      - num, bool, json -> None (absent / null)
    """
    if typ == "nullable_str":
        if cell == "":
            return None
        if cell.startswith('"'):
            return json.loads(cell)
        return cell
    if cell == "":
        return None if typ in ("num", "bool", "json") else ""
    if typ == "bool":
        return cell == "1"
    if typ == "json":
        return json.loads(cell)
    if typ == "num":
        # Prefer int when the value is a whole number
        f = float(cell)
        if f == int(f):
            return int(f)
        return f
    # str, date
    # If JSON-encoded string (starts with '"'), decode it
    if cell.startswith('"'):
        return json.loads(cell)
    return cell


def _build_toon_table(entity_name: str, rows: list[dict], columns: list[tuple[str, str]]) -> str:
    """
    Build a TOON table block.

    columns: list of (field_name, toon_type) pairs — defines column order.
    """
    header_line = f"[{len(rows)}] {entity_name}"
    col_header = "\t".join(f"{name}:{typ}" for name, typ in columns)
    data_lines = []
    for row in rows:
        cells = []
        for field, typ in columns:
            cells.append(_cell_to_str(row.get(field), typ))
        data_lines.append("\t".join(cells))
    return "\n".join([header_line, col_header] + data_lines)


def _parse_toon_table(lines: list[str], start: int) -> tuple[str, list[dict], int]:
    """
    Parse a TOON table starting at lines[start].

    Returns (entity_name, list_of_dicts, next_line_index).
    """
    header_match = re.match(r"^\[(\d+)\]\s+(\S+)$", lines[start].strip())
    if not header_match:
        raise ValueError(f"Expected TOON table header at line {start}: {lines[start]!r}")
    n = int(header_match.group(1))
    entity_name = header_match.group(2)

    col_line = lines[start + 1]
    columns = []
    for part in col_line.split("\t"):
        part = part.strip()
        if ":" in part:
            name, typ = part.rsplit(":", 1)
        else:
            name, typ = part, "str"
        columns.append((name, typ))

    rows = []
    for i in range(n):
        line = lines[start + 2 + i]
        cells = line.split("\t")
        # Pad with empty cells if the line is short
        while len(cells) < len(columns):
            cells.append("")
        row: dict = {}
        for (field, typ), cell in zip(columns, cells):
            val = _cell_from_str(cell, typ)
            row[field] = val
        rows.append(row)

    next_idx = start + 2 + n
    return entity_name, rows, next_idx


# ---------------------------------------------------------------------------
# Loan data column specs
# ---------------------------------------------------------------------------

_LOAN_DISBURSEMENTS_COLS: list[tuple[str, str]] = [
    ("id", "str"),
    ("date", "date"),
    ("amount", "num"),
    ("note", "nullable_str"),
]

_LOAN_RATE_HISTORY_COLS: list[tuple[str, str]] = [
    ("id", "str"),
    ("effectiveDate", "date"),
    ("annualRate", "num"),
    ("benchmark", "nullable_str"),
    ("spread", "num"),
]

_LOAN_OD_BALANCE_LOG_COLS: list[tuple[str, str]] = [
    ("id", "str"),
    ("date", "date"),
    ("balance", "num"),
]

_LOAN_PREPAYMENTS_COLS: list[tuple[str, str]] = [
    ("id", "str"),
    ("date", "date"),
    ("amount", "num"),
    ("note", "nullable_str"),
]

_LOAN_PAYMENT_LOG_COLS: list[tuple[str, str]] = [
    ("id", "str"),
    ("dueDate", "date"),
    ("type", "str"),
    ("amountDue", "num"),
    ("amountPaid", "num"),
    ("paidDate", "date"),
]

# ---------------------------------------------------------------------------
# OD savings data column specs
# ---------------------------------------------------------------------------

_OD_SOURCES_COLS: list[tuple[str, str]] = [
    ("id", "str"),
    ("name", "str"),
    ("description", "nullable_str"),
    ("isActive", "bool"),
    ("createdAt", "str"),
    ("editHistory", "json"),
]

_OD_CONTRIBUTIONS_COLS: list[tuple[str, str]] = [
    ("id", "str"),
    ("date", "date"),
    ("amount", "num"),
    ("sourceId", "str"),
    ("note", "nullable_str"),
    ("editHistory", "json"),
]

_OD_GOALS_COLS: list[tuple[str, str]] = [
    ("id", "str"),
    ("name", "str"),
    ("targetAmount", "num"),
    ("allocatedAmount", "num"),
    ("targetDate", "nullable_str"),
    ("color", "str"),
    ("note", "nullable_str"),
    ("isActive", "bool"),
    ("editHistory", "json"),
]

_OD_ANNOTATIONS_COLS: list[tuple[str, str]] = [
    ("odBalanceLogId", "str"),
    ("sourceId", "nullable_str"),
    ("purpose", "str"),
    ("note", "nullable_str"),
    ("editHistory", "json"),
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def dict_to_toon(data: dict, kind: str) -> str:
    """
    Convert LoanLens dict data to TOON format.

    Args:
        data: Parsed dict (loan_data or od_savings_data).
        kind: "loan" or "od".

    Returns:
        A multi-section TOON string.
    """
    if kind == "loan":
        return _loan_to_toon(data)
    elif kind == "od":
        return _od_to_toon(data)
    else:
        raise ValueError(f"Unknown kind: {kind!r}. Must be 'loan' or 'od'.")


def toon_to_dict(toon: str, kind: str) -> dict:
    """
    Convert a TOON string back to LoanLens dict data.

    Args:
        toon: TOON-formatted string.
        kind: "loan" or "od".

    Returns:
        Python dict equivalent to the original data.
    """
    if kind == "loan":
        return _toon_to_loan(toon)
    elif kind == "od":
        return _toon_to_od(toon)
    else:
        raise ValueError(f"Unknown kind: {kind!r}. Must be 'loan' or 'od'.")


# ---------------------------------------------------------------------------
# Loan conversion
# ---------------------------------------------------------------------------

def _loan_to_toon(data: dict) -> str:
    """Encode loan_data dict → TOON string."""
    sections: list[str] = []

    # --- loanDetails: singleton → compact JSON
    loan_details = data.get("loanDetails", {})
    sections.append(f"loanDetails: {json.dumps(loan_details, separators=(',', ':'), ensure_ascii=False)}")

    # --- Uniform arrays → TOON tables
    sections.append(_build_toon_table(
        "disbursements",
        _pad_optional_fields(data.get("disbursements", []), [c[0] for c in _LOAN_DISBURSEMENTS_COLS]),
        _LOAN_DISBURSEMENTS_COLS,
    ))

    sections.append(_build_toon_table(
        "rateHistory",
        _pad_optional_fields(data.get("rateHistory", []), [c[0] for c in _LOAN_RATE_HISTORY_COLS]),
        _LOAN_RATE_HISTORY_COLS,
    ))

    sections.append(_build_toon_table(
        "odBalanceLog",
        _pad_optional_fields(data.get("odBalanceLog", []), [c[0] for c in _LOAN_OD_BALANCE_LOG_COLS]),
        _LOAN_OD_BALANCE_LOG_COLS,
    ))

    sections.append(_build_toon_table(
        "prepayments",
        _pad_optional_fields(data.get("prepayments", []), [c[0] for c in _LOAN_PREPAYMENTS_COLS]),
        _LOAN_PREPAYMENTS_COLS,
    ))

    sections.append(_build_toon_table(
        "paymentLog",
        _pad_optional_fields(data.get("paymentLog", []), [c[0] for c in _LOAN_PAYMENT_LOG_COLS]),
        _LOAN_PAYMENT_LOG_COLS,
    ))

    return "\n\n".join(sections) + "\n"


def _toon_to_loan(toon: str) -> dict:
    """Decode loan TOON string → loan_data dict."""
    lines = toon.splitlines()

    data: dict = {}
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        # Singleton line: "key: <json>"
        if line.startswith("loanDetails:"):
            json_str = line[len("loanDetails:"):].strip()
            loan_details = json.loads(json_str)
            data["loanDetails"] = loan_details
            i += 1
            continue

        # Table header: "[N] entity_name"
        if re.match(r"^\[\d+\]", line):
            entity_name, rows, next_i = _parse_toon_table(lines, i)
            data[entity_name] = rows
            i = next_i
            continue

        i += 1

    # Post-process: restore typed values
    _restore_loan_arrays(data)
    return data


def _restore_loan_arrays(data: dict) -> None:
    """Fix up parsed rows: remove None-valued optional fields to match original JSON shape."""
    # disbursements: note is optional
    for row in data.get("disbursements", []):
        if row.get("note") is None:
            row.pop("note", None)

    # rateHistory: benchmark, spread are optional
    for row in data.get("rateHistory", []):
        if row.get("benchmark") is None:
            row.pop("benchmark", None)
        if row.get("spread") is None:
            row.pop("spread", None)

    # prepayments: note is optional
    for row in data.get("prepayments", []):
        if row.get("note") is None:
            row.pop("note", None)


# ---------------------------------------------------------------------------
# OD savings conversion
# ---------------------------------------------------------------------------

def _od_to_toon(data: dict) -> str:
    """Encode od_savings_data dict → TOON string."""
    sections: list[str] = []

    # --- emiReserve: scalar → key:value line
    sections.append(f"emiReserve: {data.get('emiReserve', 0)}")

    # --- Uniform arrays (with editHistory as json column) → TOON tables
    sections.append(_build_toon_table(
        "sources",
        _pad_optional_fields(data.get("sources", []), [c[0] for c in _OD_SOURCES_COLS]),
        _OD_SOURCES_COLS,
    ))

    sections.append(_build_toon_table(
        "contributions",
        _pad_optional_fields(data.get("contributions", []), [c[0] for c in _OD_CONTRIBUTIONS_COLS]),
        _OD_CONTRIBUTIONS_COLS,
    ))

    sections.append(_build_toon_table(
        "goals",
        _pad_optional_fields(data.get("goals", []), [c[0] for c in _OD_GOALS_COLS]),
        _OD_GOALS_COLS,
    ))

    sections.append(_build_toon_table(
        "odBalanceAnnotations",
        _pad_optional_fields(data.get("odBalanceAnnotations", []), [c[0] for c in _OD_ANNOTATIONS_COLS]),
        _OD_ANNOTATIONS_COLS,
    ))

    return "\n\n".join(sections) + "\n"


def _toon_to_od(toon: str) -> dict:
    """Decode OD savings TOON string → od_savings_data dict."""
    lines = toon.splitlines()

    data: dict = {}
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        # Scalar line: "emiReserve: <value>"
        if line.startswith("emiReserve:"):
            val_str = line[len("emiReserve:"):].strip()
            f = float(val_str)
            data["emiReserve"] = int(f) if f == int(f) else f
            i += 1
            continue

        # Table header
        if re.match(r"^\[\d+\]", line):
            entity_name, rows, next_i = _parse_toon_table(lines, i)
            data[entity_name] = rows
            i = next_i
            continue

        i += 1

    # Post-process optional fields
    _restore_od_arrays(data)
    return data


def _restore_od_arrays(data: dict) -> None:
    """Fix up parsed OD rows: remove None-valued optional fields to match original JSON shape."""
    # sources: description is optional
    for row in data.get("sources", []):
        if row.get("description") is None:
            row.pop("description", None)

    # contributions: note is optional
    for row in data.get("contributions", []):
        if row.get("note") is None:
            row.pop("note", None)

    # goals: targetDate, note are optional
    for row in data.get("goals", []):
        if row.get("targetDate") is None:
            row.pop("targetDate", None)
        if row.get("note") is None:
            row.pop("note", None)

    # odBalanceAnnotations: sourceId stays (it can be null → None → must be kept as None per schema)
    # note is optional
    for row in data.get("odBalanceAnnotations", []):
        if row.get("note") is None:
            row.pop("note", None)


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _pad_optional_fields(rows: list[dict], all_fields: list[str]) -> list[dict]:
    """
    Ensure every row has all expected fields (with None for missing ones).
    This makes _build_toon_table produce consistent column counts.
    """
    result = []
    for row in rows:
        padded = {}
        for field in all_fields:
            padded[field] = row.get(field)  # None if absent
        result.append(padded)
    return result
