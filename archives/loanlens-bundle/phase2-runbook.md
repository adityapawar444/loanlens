# LoanLens — Phase 2 Runbook

## Overview
This runbook walks you through activating LoanLens in Claude Desktop. It is written for a single user managing their own home loan. Follow the numbered steps in order.

---

## Step 1: Capability Probe

Before installing, determine which tier of Claude Desktop you have:

| Test | Tier |
|---|---|
| Claude can run Python code AND read/write local files | **Tier A** (full) |
| Claude can run Python code but cannot write files | **Tier B** (compute-only) |
| Claude cannot run any code | **Tier C** (pre-rendered reports only) |

**How to check:** In a new Claude conversation, ask: *"Can you run this Python snippet and write the output to a file: `print('hello')`?"* If the file is created → Tier A. If it runs but no file → Tier B. If it doesn't run → Tier C.

---

## Step 2: Install the Bundle

### Tier A / B (local filesystem)
```bash
# Copy the bundle to your home directory
cp -r loanlens-bundle ~/loanlens

# Verify structure
ls ~/loanlens/
# Should see: SKILL.md  data/  engine/  fixtures/  reports/  spec/  tests/
```

### Tier C (no filesystem access)
Skip this step. You will paste file contents directly into the Claude Project.

---

## Step 3: Install the Skill

1. Open Claude Desktop → Settings → Skills (or Custom Instructions)
2. Create a new skill named **LoanLens**
3. Paste the contents of `SKILL.md` into the skill definition
4. Save

---

## Step 4: Create a Claude Project

1. Create a new Claude Project named **LoanLens**
2. In the Project Instructions field, paste the contents of `project-instructions.md`
3. **Tier A/B:** Add the bundle folder path to Project Knowledge: `~/loanlens/`
4. **Tier C only:** Upload these files to Project Knowledge:
   - `reports/summary_20260919.md`
   - `reports/od_savings_20260919.md`
   - `reports/schedule_20260919.md`
   - `reports/ledger_20260919.md`
   - `spec/logic-spec.md`
   - `data/loan_data.v001.toon`
   - `data/od_savings.v001.toon`

---

## Step 5: End-to-End Read Tests

In the LoanLens Project, run each query and verify the output matches `reports/*.md`:

```
"Show me the loan summary"             → renders summary_20260919.md content
"Show OD savings breakdown"            → renders od_savings_20260919.md content
"Show the next 6 installments"         → renders schedule_20260919.md content
"Show me the ledger"                   → renders ledger_20260919.md content
```

---

## Step 6: Mutation Tests (Tier A/B only)

Test the dry-run → confirm → commit flow for each operation type:

```
"Add a prepayment of ₹5,00,000 on 2026-10-01"
→ Should show impact summary (tenure change, interest saved)
→ Confirm → should write new TOON version

"Update the OD balance to ₹10,00,000 as of today"
→ Should auto-confirm and show updated waterfall

"Add a new goal: Emergency Fund, target ₹2,00,000, allocated ₹50,000"
→ Should show goal created confirmation

"Process due payments for today"
→ Should list what will be deducted, ask for confirmation
```

---

## Step 7: Rollback Test (Tier A only)

```
# Check the archive directory exists after a mutation
ls ~/loanlens/data/
# Should see: loan_data.v001.toon  loan_data.v002.toon  manifest.json

# Simulate corruption test
cp ~/loanlens/data/loan_data.v001.toon ~/loanlens/data/loan_data.v002.toon  # revert
# Update manifest.json to point to v001 again
```

Or ask Claude: *"Restore loan data to the previous version."*

---

## Step 8: Tuning

After confirming everything works:

1. **Verbosity:** Adjust `window` parameter in schedule queries — default is 6 installments
2. **Trigger:** If LoanLens activates unexpectedly, narrow the trigger in `SKILL.md` § Trigger
3. **PII:** Review the rendered reports; if any names appear, re-run `generate_reports.py`

---

## Step 9: Ongoing Monthly Routine

After receiving each bank statement:

1. **Update OD balance:** *"Update OD balance to ₹X,XX,XXX as of [date]"*
2. **Log the payment:** *"Process due payments for [due date]"*
3. **Add contributions:** *"Add contribution of ₹X from [source] on [date]"*
4. **Verify:** *"Show me the loan summary"* — compare outstanding principal with statement

### Annual Year-End
```bash
# Re-generate pre-rendered reports with new today_date
cd ~/loanlens
python generate_reports.py  # edit TODAY= in the script first
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| "Cannot find manifest.json" | Check bundle path; re-run Step 2 |
| Numbers differ from bank statement | Run parity check: `python -m pytest tests/ -v` |
| "Validation error: amount must be > 0" | Check the value you passed — likely a typo |
| Over-allocation warning | Review goals via OD savings report; reduce allocations |
| Tier C — data seems stale | Re-generate reports; re-upload to Project Knowledge |
