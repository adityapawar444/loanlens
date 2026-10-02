# P1-11: Token Measurements

## Goal
Measure token counts for all key bundle artifacts and verify none exceed their budgets. Record measurements in `manifest.json`.

## Inputs
- `loanlens-bundle/` — complete bundle (from P1-10)

## Outputs
- Updated `loanlens-bundle/manifest.json` with `token_measurements` section

## What to Measure
| Artifact | Budget |
|---|---|
| `data/loan_data.v001.toon` | — (record, no budget) |
| `data/od_savings.v001.toon` | — (record, no budget) |
| `reports/summary_*.md` | ≤ 400 tokens |
| `reports/od_savings_*.md` | ≤ 600 tokens |
| `reports/schedule_*.md` | ≤ 800 tokens |
| `reports/ledger_*.md` | ≤ 500 tokens |
| `SKILL.md` | — (record) |
| `project-instructions.md` | — (record) |
| Total TOON data | — (record, compare vs JSON) |

## Method
Use `len(text) / 4` as a conservative token estimate (cl100k_base). If `tiktoken` is available, use it for exact counts. Record the method used.

## Verifier
```bash
python -c "
import json
m = json.load(open('loanlens-bundle/manifest.json'))
assert 'token_measurements' in m
print(json.dumps(m['token_measurements'], indent=2))
"
```

## Done Signal
Token measurements recorded in manifest. No report exceeds its budget.
