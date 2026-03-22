from __future__ import annotations

from pathlib import Path

try:
    import reportlab  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover
    reportlab = None


def export_text(content: str, path: Path) -> Path:
    if reportlab is None:
        msg = "reportlab is not installed"
        raise RuntimeError(msg)
    # Graceful placeholder export until richer PDF formatting is added.
    path.write_text(content, encoding="utf-8")
    return path
