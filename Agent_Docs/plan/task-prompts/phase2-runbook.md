# Phase 2 Runbook — Claude Desktop

**Purpose:** Step-by-step instructions to install and verify the LoanLens conversational version in Claude Desktop. This runbook assumes you have the `loanlens-bundle/` directory from Phase 1.

---

## Prerequisites
- Claude Desktop (or Claude.ai with Projects + code execution)
- The `loanlens-bundle/` directory (from Phase 1)
- ~2 hours

---

## Step 1: Capability Probe (5 min)

Test what Claude Desktop can do:

**Paste this into Claude:**
```
Can you run Python code? Try: print(1 + 1)
Can you read files from my local filesystem? Try reading: ~/test.txt
Can you write files to my local filesystem? Try writing "hello" to: ~/loanlens_test.txt
```

**Record the tier:**
- ✅ Code execution + ✅ Read + ✅ Write → **Tier A** (full capability)
- ✅ Code execution + ✅ Read + ❌ Write → **Tier B** (read-only storage)
- ❌ Code execution → **Tier C** (reasoning only)

---

## Step 2: Install Bundle (10 min)

### Tier A/B: Local Folder
1. Copy `loanlens-bundle/` to `~/loanlens/`
2. Tell Claude: "My LoanLens data is in ~/loanlens/"

### Tier C: Paste into Project
1. Upload `SKILL.md` as a Project file
2. Upload `spec/logic-spec.md` as a Project file
3. Upload all 4 pre-rendered reports as Project files
4. Upload both TOON data files as Project files

---

## Step 3: Install Skill (5 min)

**Paste this into a Claude Project Knowledge file:**

*[Copy the entire contents of `loanlens-bundle/SKILL.md` here]*

---

## Step 4: Create Project (5 min)

**Paste this as the Project Instructions:**

*[Copy the entire contents of `loanlens-bundle/project-instructions.md` here]*

---

## Step 5: End-to-End Tests (30 min)

Run each test in a new conversation within the Project:

### Test 5.1: Summary Report
**Query:** "Show me my loan summary for today"
**Expected:** Report shows outstanding principal, OD balance, effective rate, next due date, interest savings. Compare key values against `fixtures/base.json` → `expected_metrics`.

### Test 5.2: OD Savings Report
**Query:** "Show me my OD savings breakdown"
**Expected:** Waterfall (OD balance → reserve → allocatable → goals → free). Goal table with 6 goals. Over-allocation warning (~₹36,179).

### Test 5.3: Schedule Report
**Query:** "Show me my next 6 installments"
**Expected:** Table with 6 rows. All moratorium phase (until period 18). Due dates on the 10th of each month.

### Test 5.4: Simulator
**Query:** "What happens if I make a ₹5,00,000 prepayment on October 1st?"
**Expected:** Comparison showing interest saved, tenure change. Values should be close to `fixtures/prepayment.json` → `expected_metrics` (exact match for Tier A; approximate for Tier C).

### Test 5.5: Ledger
**Query:** "Show me my payment history"
**Expected:** 4 disbursements, 8 payment log entries, 9 OD balance snapshots.

---

## Step 6: Mutation Tests (25 min)

### Test 6.1: Update OD Balance
**Query:** "Log a new OD balance of ₹10,00,000 on September 20, 2026"
**Expected:** Dry-run shows impact (new allocatable balance, over-allocation status change). After confirmation, data is updated.
**Verify:** "Show me my OD savings" → latest balance should be ₹10,00,000.

### Test 6.2: Add Contribution
**Query:** "Log a contribution of ₹50,000 from [Source 1] on September 20, 2026"
**Expected:** Contribution added. Total contributions increase by ₹50,000.
**Verify:** "Show me my OD savings" → total deposited should increase.

### Test 6.3: Edit Goal Allocation
**Query:** "Allocate ₹1,00,000 to [Goal 1]"
**Expected:** Over-allocation warning if total exceeds allocatable. After confirmation, goal updated.
**Verify:** "Show me my goals" → allocation updated.

### Test 6.4: Rollback
**Query:** "Something went wrong, can you restore the previous version?"
**Expected (Tier A):** Restore from `archive/` directory. Data reverts to pre-mutation state.
**Expected (Tier B/C):** Instructions to manually replace data files.

---

## Step 7: Tuning (15 min)

Based on the test results, adjust:

1. **Report verbosity:** If reports are too long, ask Claude to "make the summary more concise." If too short, "include more detail in the schedule."
2. **Trigger sensitivity:** If the skill doesn't activate on certain queries, add trigger phrases to SKILL.md.
3. **Formatting:** If INR grouping or date formatting is off, check the renderer settings.

---

## Step 8: Monthly Update Routine (15 min)

### When You Receive Your Bank Statement (around the 15th of each month):

1. **Log the actual OD balance:** "Log OD balance of ₹X,XX,XXX on [date from statement]"
2. **Update payment if different from auto-deduction:** "Update the payment for [month] — amount due was ₹X, amount paid was ₹Y"
3. **Log any new disbursement:** "Add a disbursement of ₹X on [date] for [purpose]"
4. **Log contributions:** "Log a contribution of ₹X from [source] on [date]"
5. **Process due payments:** "Process any due payments for today"
6. **Review:** "Show me my summary" — verify everything looks correct

### If a Rate Change Occurs:
"Add a rate change to X.X% effective [date], benchmark [RLLR/other]"

### Quarterly Review:
"Show me my schedule" + "Simulate a ₹X prepayment on [date]" — to evaluate prepayment options

---

## Troubleshooting

| Problem | Solution |
|---|---|
| "I can't find the data files" | Check the file path. Try `ls ~/loanlens/data/` |
| "The numbers don't match the app" | Run `python -m pytest tests/test_parity.py` to check engine accuracy |
| "Over-allocation warning but I want to proceed" | Confirm when prompted — the system warns but doesn't block |
| "Auto-deduction created wrong entries" | Rollback to previous version, manually correct, re-run |
| "Tier C: numbers seem approximate" | Expected — without code execution, Claude reasons through formulas. Use Tier A for precise calculations. |
