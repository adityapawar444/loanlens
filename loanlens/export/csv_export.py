from __future__ import annotations

from pathlib import Path

import pandas as pd  # type: ignore[import-untyped]


def export_rows(rows: list[dict[str, object]], path: Path) -> Path:
    pd.DataFrame(rows).to_csv(path, index=False)
    return path
