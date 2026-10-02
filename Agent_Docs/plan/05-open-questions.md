# D5 — Open Questions

**Produced:** 2026-09-19  
**Updated:** 2026-09-20

Decisions requiring confirmation, ranked by plan impact. Each includes the default I chose and what changes if you disagree.

---

## Q1. TOON vs. an established format (e.g., CSV, Parquet, JSONL)

**Default chosen:** Custom TOON (TSV with `[N]` headers and typed columns).

**Rationale:** TOON is the format named in your prompt. No existing npm/PyPI package for "TOON" was found, so I designed a minimal TSV-based spec (see D2 §A). It achieves ~60% token reduction over pretty JSON while staying human-readable.

**Impact if you disagree:**
- *CSV* — similar savings but no typed headers; requires quoting rules; audit-trail JSON fields (nested arrays) are harder to encode. Converter design stays the same, just different output format.
- *JSONL (one JSON object per line)* — saves ~30% tokens (eliminates indentation but keeps repeated keys). Simpler to implement (no custom parser). Would simplify the "LLM edit safety" concern since each line is valid JSON.
- *Keep pretty JSON* — simplest; ~3,330 tokens total for both files (acceptable for Claude's context window). Eliminates the converter workstream entirely, saving ~2 tasks (P1-02 + half of P1-10). **This is the most impactful alternative — it removes an entire workstream.**

**Plan change if dropped:** Remove WS-1 (converter), remove P1-02, simplify P1-10. Engine reads/writes JSON directly. Saves ~1 hour of Phase 1 work. Token cost rises from ~1,350 to ~3,330 but is still well within Claude's context limit.

---

## Q2. Python as the engine runtime vs. TypeScript

**Default chosen:** Python 3.10+ (Claude Desktop's code execution runs Python).

**Rationale:** Claude Desktop's sandboxed code interpreter supports Python. The engine must run in Phase 2 inside Claude.

**Impact if you disagree:**
- *Keep TypeScript* — the engine already exists and is tested. But Phase 2 cannot execute it in Claude Desktop. Would need a separate Node.js environment or force Tier C (no code execution, reasoning-only fallback).
- *Both (Python primary, TS as reference)* — more work but maximum safety. Already partially covered by the parity harness.

**Plan change:** If TypeScript, drop P1-04 (Python engine port), P1-07 (parity harness), and all Python test infrastructure. Phase 2 would be Tier C only. **Significant reduction in Phase 2 capabilities.**

---

## Q3. Should `autoDeductPayments` be an explicit operation or triggered automatically?

**Default chosen:** Explicit operation (`W14: process_due_payments`) in the skill. The skill asks the user to run it, rather than auto-triggering on every data read.

**Rationale:** The current app's "read causes write" pattern is a side-effect that makes the system harder to reason about. In a conversational interface, explicit operations are safer and more transparent.

**Impact if you disagree:**
- *Keep auto-trigger* — the engine would call `process_due_payments` internally before every report or mutation, matching the app's behaviour exactly. Risk: if Claude's date is wrong, deductions happen for wrong months.
- *Hybrid* — auto-trigger on read reports, explicit for mutations.

**Plan change:** Minor — changes the engine's `load_data()` function and the skill protocol. Adds a `today` validation step.

---

## Q4. Should the skill enforce over-allocation limits that the app does not?

**Default chosen:** Match the app — warn but don't block. Show the same amber/red warnings as the app when goal allocations exceed the allocatable balance or the full OD balance.

**Rationale:** The app deliberately allows over-allocation with a warning. Changing this behaviour would break parity.

**Impact if you disagree:**
- *Block over-allocation past reserve* — `edit_goal` would reject `allocatedAmount` changes that push `totalAllocated > allocatableBalance`. Safer but breaks parity with the app.
- *Block over-allocation past OD balance* — even stricter; prevents the "critical" state entirely.

**Plan change:** Adds validation logic to `W10: edit_goal` in the operations module. Small change.

---

## Q5. `HISTORICAL_PAYMENT_DATES` — keep hardcoded or derive from data?

**Default chosen:** Keep the hardcoded set in the logic spec and Python engine, matching the TypeScript source exactly.

**Rationale:** The set covers the first 5 moratorium months where bank PDF statements were manually entered. The logic is that these months have *actual* bank-charged amounts that differ from the computed interest. Changing this would alter the schedule output and break parity.

**Impact if you disagree:**
- *Derive from paymentLog entries with `type: "pre_emi_interest"`* — would automatically extend the override set as new months are added. More maintainable long-term. But would change the engine's behaviour for future months (if a pre_emi_interest entry exists for, say, Jul 2026, it would also be overridden).
- *Remove the override entirely* — simplifies the engine; all months use computed interest. Breaks parity with existing schedule output.

**Plan change:** If derived: modify the schedule engine and update the parity harness tolerance. Medium effort.

---

## Q6. Sensitive data handling — should TOON files contain the account number?

**Default chosen:** Redact the account number in TOON files and pre-rendered reports. Store it only in the JSON reference copy (which is not used by the engine).

**Rationale:** The prompt says "keep sensitive identifiers out of skill and instruction text." The account number is used nowhere in calculations — it's purely display metadata.

**Impact if you disagree:**
- *Include account number* — simpler (no redaction step); the user might want it for reference when talking to the bank. Risk: if TOON files are shared or pasted into conversation, the account number is exposed.
- *Encrypt/mask* — more complex; show last 4 digits only (`****4041`).

**Plan change:** Minimal — affects the converter's redaction logic and the renderer's display.

---

## Q7. Google Drive fallback — should Phase 1 build the Drive integration?

**Default chosen:** No. Phase 1 targets local-folder storage only. Drive integration is deferred to Phase 2 if local storage doesn't work.

**Rationale:** Local storage is simpler and sufficient for a single-user tool. Drive adds complexity (create-only API, no overwrite, search latency) that may not be needed.

**Impact if you disagree:**
- *Build Drive MCP integration in Phase 1* — adds ~2 tasks to Phase 1 (converter writes to Drive format, read-back verification). Requires the MCP Google Drive tool to be available and tested.

**Plan change:** Adds P1-12 (Drive adapter) and P1-13 (Drive round-trip test). ~1 hour additional work.

---

## Q8. Report token budgets — are they appropriate?

**Default chosen:**
| Report | Budget | Hard Limit |
|---|---|---|
| Summary | 400 | 600 |
| OD Savings | 600 | 900 |
| Schedule | 800 | 1200 |
| Simulator | 600 | 900 |
| Ledger | 500 | 800 |

**Rationale:** These budgets balance information density with Claude's output window. The summary is intentionally tight; the schedule needs more room for the table.

**Impact if you disagree:**
- *Tighter budgets* — would require dropping some fields from reports. The summary could go as low as ~250 tokens by removing the waterfall section.
- *Looser budgets* — would allow more detail (e.g., full contribution history in OD savings, more schedule rows). Could double the schedule window from 6 to 12 rows.

**Plan change:** Affects the renderer templates (P1-06). Minor.

---

## Q9. Simulator in the skill — should it support "apply to actuals"?

**Default chosen:** No. The simulator is read-only, matching the app. Simulated changes are not persisted.

**Rationale:** The app's simulator is explicitly read-only (confirmed in D0 §4). The previous plan mentioned an "apply to actuals" button that was never implemented.

**Impact if you disagree:**
- *Add "apply scenario"* — the `simulate` operation would have a `commit: bool` parameter. If `commit=True`, the simulated changes would be applied as real mutations. This is a new feature not in the app.

**Plan change:** Adds validation and commit logic to the simulator operation. Medium effort — needs careful handling of multi-change transactions.

---

## Q10. Phase 2 model availability — Opus vs. Sonnet in Claude Desktop

**Default chosen:** Task breakdown uses tier names (Opus-class / Sonnet-class / Haiku-class) for Phase 2 tasks, not specific versions, because the Claude Desktop model lineup may differ.

**Rationale:** The prompt instructs this approach (D4 rules, bullet 4).

**Impact if you disagree:** None — this is a naming convention, not a capability constraint. The rubric already specifies which tasks need higher reasoning.

---

## Summary: Impact Ranking

| Rank | Question | Impact if answer changes |
|---|---|---|
| 🔴 1 | Q1: TOON vs. keep JSON | Removes/adds entire workstream (~2 tasks, ~1 hour) |
| 🔴 2 | Q2: Python vs. TypeScript | Removes Python port entirely; Phase 2 = Tier C only |
| 🟡 3 | Q5: HISTORICAL_PAYMENT_DATES | Changes engine behaviour and parity baseline |
| 🟡 4 | Q3: Auto-deduct explicit vs. auto | Changes skill protocol and safety model |
| 🟢 5 | Q9: Simulator "apply to actuals" | New feature scope |
| 🟢 6 | Q4: Over-allocation enforcement | Minor validation change |
| 🟢 7 | Q7: Drive integration in Phase 1 | Adds ~2 tasks |
| 🟢 8 | Q6: Account number in TOON | Minor redaction logic |
| 🟢 9 | Q8: Token budgets | Renderer template tweaks |
| ⚪ 10 | Q10: Phase 2 model naming | No plan change |
