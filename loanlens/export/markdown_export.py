from __future__ import annotations

from pathlib import Path


def export_rows(rows: list[dict[str, object]], path: Path) -> Path:
    if not rows:
        path.write_text("", encoding="utf-8")
        return path
    headers = list(rows[0].keys())
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(header, "")) for header in headers) + " |")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
