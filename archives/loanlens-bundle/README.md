# LoanLens Bundle v1.0.0

**Data snapshot:** 19 Sep 2026 · **Source commit:** 513bbeb · **Tests:** 182 passing

LoanLens is a conversational home loan tracker for Claude Desktop. It computes amortization schedules with daily OD-linked interest, manages savings goals, and lets you update loan data through plain-language commands.

---

## Quick Start

```bash
# 1. Verify tests pass
cd loanlens-bundle
python -m pytest tests/ -v          # 182 tests, all passing

# 2. Regenerate pre-rendered reports (if needed)
python generate_reports.py          # writes to reports/

# 3. Rebuild manifest after any file change
python generate_manifest.py         # writes manifest.json
```

Then follow [`phase2-runbook.md`](phase2-runbook.md) to activate in Claude Desktop.

---

## Directory Layout

```
loanlens-bundle/
├── SKILL.md                    ← Claude skill definition (install this)
├── project-instructions.md     ← Claude Project instructions (paste this)
├── phase2-runbook.md           ← Step-by-step activation guide
├── manifest.json               ← File inventory with SHA256 checksums
├── requirements.txt            ← Python dependencies (pydantic>=2.0)
│
├── data/
│   ├── loan_data.v001.toon     ← Loan data in TOON format (current)
│   ├── od_savings.v001.toon    ← OD savings data in TOON format (current)
│   ├── loan_data.json          ← Loan data in JSON (reference copy)
│   └── od_savings_data.json    ← OD savings data in JSON (reference copy)
│
├── engine/                     ← Python computation engine
│   ├── schedule.py             ← generate_schedule() — amortization rows
│   ├── metrics.py              ← calculate_metrics() — summary figures
│   ├── emi.py                  ← calculate_emi(), calculate_tenure()
│   ├── operations.py           ← All 15 write operations (W1–W15)
│   ├── renderer.py             ← render_summary/od_savings/schedule/simulator/ledger()
│   ├── converter.py            ← json_to_toon(), toon_to_json()
│   ├── auto_deduct.py          ← auto_deduct_payments()
│   └── types.py                ← Pydantic models
│
├── spec/
│   ├── logic-spec.md           ← Language-neutral formula specification
│   └── schemas.md              ← Data schema documentation
│
├── fixtures/                   ← Golden test fixtures (8 scenarios)
│   ├── base.json
│   ├── prepayment.json
│   ├── rate-change.json
│   ├── od-change.json
│   ├── disbursement-during-emi.json
│   ├── moratorium-boundary.json
│   ├── zero-od.json
│   └── high-prepayment.json
│
├── tests/
│   ├── test_parity.py          ← TS↔Python schedule/metrics parity (16 tests)
│   ├── test_operations.py      ← W1–W15 operation unit tests
│   ├── test_converter.py       ← TOON round-trip tests
│   └── test_renderer.py        ← Report rendering tests
│
└── reports/                    ← Pre-rendered Tier C fallback (19 Sep 2026)
    ├── summary_20260919.md
    ├── od_savings_20260919.md
    ├── schedule_20260919.md
    └── ledger_20260919.md
```

---

## Capability Tiers

| Tier | Code Execution | File Write | What Works |
|---|---|---|---|
| **A** | ✅ | ✅ | Full: live reports, mutations, versioned storage |
| **B** | ✅ | ❌ | Live compute; mutations need manual file update |
| **C** | ❌ | ❌ | Pre-rendered reports only (from `reports/`) |

See `phase2-runbook.md` §1 for how to determine your tier.

---

## Operations Reference

### Read (R1–R5)
| ID | What it does |
|---|---|
| R1 `show_summary` | Loan health snapshot: phase, principal, OD, next due |
| R2 `show_od_savings` | OD waterfall, goal progress, contribution history |
| R3 `show_schedule` | Next N installments + yearly summary + closure date |
| R4 `simulate` | Hypothetical scenario comparison (before vs. after) |
| R5 `show_ledger` | Disbursements, payments, OD balance history |

### Write (W1–W15)
| ID | What it does |
|---|---|
| W1 `update_od_balance` | Record a new OD balance snapshot |
| W2 `add_disbursement` | Add a loan tranche |
| W3 `add_prepayment` | Record a lump-sum prepayment |
| W4 `add_rate_change` | Add a new interest rate |
| W5 `update_payment` | Correct a payment log entry |
| W6 `update_emi_reserve` | Set EMI reserve in OD |
| W7 `add_source` | Create a contribution source |
| W8 `edit_source` | Edit a source |
| W9 `add_goal` | Create a savings goal |
| W10 `edit_goal` | Edit a goal |
| W11 `add_contribution` | Record a deposit to OD |
| W12 `edit_contribution` | Edit a contribution |
| W13 `edit_od_annotation` | Annotate an OD balance entry |
| W14 `process_due_payments` | Auto-deduct due payments from OD |
| W15 `update_settings` | Change loan settings (due day, policy) |

---

## Key Design Decisions

- **TOON format:** ~60% token reduction vs pretty JSON for array-heavy data
- **Engine-mediated mutations:** Claude never hand-edits TOON; the Python engine always recomputes `[N]` headers
- **Deterministic rendering:** `render_*` functions produce identical output for identical input — the LLM displays verbatim, never re-derives numbers
- **Daily interest accrual:** `effectivePrincipal = max(0, outstanding - OD_balance)` × daily rate, summed per period
- **`today` is always explicit:** Engine never reads the system clock

See `spec/logic-spec.md` for full formula details.
