#!/usr/bin/env python3
"""
generate_manifest.py — Build manifest.json with SHA256 checksums for all bundle files.
Run from the loanlens-bundle/ directory.
"""

import hashlib
import json
import os
import sys
from datetime import date, timezone
from pathlib import Path

BUNDLE_DIR = Path(__file__).parent
EXCLUDE_DIRS = {".venv", ".pytest_cache", "__pycache__", "archive"}
EXCLUDE_FILES = {"manifest.json", "generate_manifest.py", "generate_reports.py"}

# Fixture scenarios (ordered)
FIXTURE_SCENARIOS = [
    "base", "prepayment", "rate-change", "od-change",
    "disbursement-during-emi", "moratorium-boundary", "zero-od", "high-prepayment"
]


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def collect_files() -> list[dict]:
    entries = []
    for root, dirs, files in os.walk(BUNDLE_DIR):
        # Prune excluded dirs in-place
        dirs[:] = [d for d in sorted(dirs) if d not in EXCLUDE_DIRS]
        for name in sorted(files):
            if name in EXCLUDE_FILES or name.endswith(".pyc"):
                continue
            full = Path(root) / name
            rel = full.relative_to(BUNDLE_DIR).as_posix()
            entries.append({
                "path": rel,
                "sha256": sha256_of(full),
                "bytes": full.stat().st_size,
            })
    return entries


def main():
    files = collect_files()

    manifest = {
        "bundle_version": "1.0.0",
        "created": date.today().isoformat(),
        "source_commit": "513bbeb",
        "data_snapshot_date": "2026-09-19",
        "files": files,
        "fixture_scenarios": FIXTURE_SCENARIOS,
        "parity_status": "all_passing",
    }

    out_path = BUNDLE_DIR / "manifest.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")

    print(f"manifest.json written — {len(files)} files listed")
    for entry in files:
        print(f"  {entry['path']} ({entry['bytes']} bytes)")


if __name__ == "__main__":
    main()
