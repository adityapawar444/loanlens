# P1-10: Handoff Bundle Assembly + Manifest

## Goal
Assemble all Phase 1 artifacts into a self-contained `loanlens-bundle/` directory. Generate a `manifest.json` with SHA256 checksums for every file. Verify the bundle is complete and all tests pass from within it.

## Inputs
- All outputs from P1-01 through P1-09

## Outputs
- `loanlens-bundle/manifest.json` — file list with checksums
- `loanlens-bundle/README.md` — bundle overview and quick-start

## Manifest Schema
```json
{
  "bundle_version": "1.0.0",
  "created": "2026-09-XX",
  "source_commit": "513bbeb",
  "data_snapshot_date": "2026-09-19",
  "files": [
    { "path": "engine/schedule.py", "sha256": "abc123...", "bytes": 1234 }
  ],
  "fixture_scenarios": ["base", "prepayment", ...],
  "parity_status": "all_passing"
}
```

## Checklist
- [ ] `engine/` — all .py modules (8+ files)
- [ ] `spec/` — logic-spec.md, schemas.md
- [ ] `data/` — .toon files + .json reference copies
- [ ] `fixtures/` — 8 scenario files
- [ ] `tests/` — test_parity.py, test_converter.py, test_operations.py, test_renderer.py
- [ ] `reports/` — 4 pre-rendered reports
- [ ] `SKILL.md`, `project-instructions.md`
- [ ] `phase2-runbook.md`
- [ ] `manifest.json`, `README.md`

## Verifier
```bash
cd loanlens-bundle
python -c "import json; m=json.load(open('manifest.json')); print(f'{len(m[\"files\"])} files listed'); assert len(m['files']) >= 20"
python -m pytest tests/ -v --tb=short
```
All tests pass from the bundle root. Manifest lists ≥20 files.

## Done Signal
Bundle directory is self-contained. Manifest valid. All tests pass.
