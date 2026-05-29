# Skill: Surgical Edit

## Objective
Make the smallest possible change that fixes the problem — no wider. Every edit must be locatable, bounded, and verifiable before it is committed.

---

## Step 0 — Find the File (Never Guess)

Before opening any file, locate the exact target using grep:

```bash
# Find a function
grep -rn 'def function_name' .

# Find a callback by its Output ID
grep -rn 'Output("output-id"' callbacks/

# Find a class
grep -rn 'class ClassName' services/

# Find where a store is consumed
grep -rn 'portfolio-store' callbacks/

# Find a component ID in layout
grep -rn '"my-component-id"' pages/ components/
```

**Rule**: One grep, read the result, open that file. Never scan `ls` output to guess a path.

---

## Step 1 — Read Before Touching

Open the target file. Before changing a single character:

1. Read the **entire function or callback** — not just the broken line.
2. Identify all `Input`, `State`, and `Output` declarations.
3. Identify all guard clauses (`if pathname !=`, `if not data`, `prevent_initial_call`).
4. Check `docs/known_issues.md` — does this file appear in a known bug's "Files affected" list?
5. Check `docs/callback_ownership.md` — is the Output ID already owned?

---

## Step 2 — Declare Boundaries Before Coding

**State out loud what you will NOT change** before making any edit:

> "I am changing only `[specific function/block]` on lines `[X–Y]`.  
> I will not touch: the function signature, the Input/Output declarations, the guard clauses, or any other function in this file."

This boundary declaration is mandatory. It forces scope formation before the edit begins and prevents accidental widening.

---

## Step 3 — Apply the Edit Budget Rule

Before writing any code, count the scope:

> **If the fix requires touching more than 2 files OR more than 150 lines total — STOP.**  
> Explain why a localised edit is insufficient before proceeding.  
> Get explicit confirmation that the wider scope is necessary.

A budget overflow almost always means the root cause diagnosis is wrong or the change is architectural (requires a plan, not a patch).

---

## Step 4 — Make the Edit

Change only the specific lines identified in Step 2. Do not:
- Reorganise imports
- Rename variables "while you're in there"
- Reformat surrounding code
- Add logging outside the changed block
- Touch any [Do Not Touch Zone](../GEMINI.md#do-not-touch-zones)

---

## Step 5 — Review the Diff Before Finalising

Before considering the edit complete, mentally (or literally with `git diff`) review the full diff:

- **No unintended deletions** — check that no existing lines were silently removed.
- **No renamed imports** — confirm no `import X` was changed to `import Y`.
- **No changed callback wiring** — confirm `Input`, `Output`, `State` declarations are identical to before (unless that was the explicit intent).
- **No modified store keys** — confirm no dict key was renamed (e.g. `"raw"` → `"signals"`), which would silently break all consumers.

If any of these appear in the diff and were not part of the declared intent — revert and re-edit.

---

## Step 6 — Post-Edit Verification

```bash
# 1. Lint and format the changed file only
ruff check <filename> --fix
ruff format <filename>

# 2. Verify the app still imports cleanly
python -c "import app" 2>&1 | head -20
```

Confirm:
- No new ruff errors in the edited file
- No unused imports introduced
- No undefined names introduced

---

## Quick Reference Checklist

```
Before editing:
[ ] Located the file with grep — did not guess
[ ] Read the entire function, not just the broken line
[ ] Checked docs/known_issues.md for this file
[ ] Checked docs/callback_ownership.md for Output ID conflicts
[ ] Declared what I will NOT change
[ ] Edit touches ≤ 2 files and ≤ 150 lines (or got explicit approval)

After editing:
[ ] Reviewed the full diff for unintended deletions, renames, and wiring changes
[ ] Ran ruff check + ruff format on the changed file
[ ] Confirmed app imports cleanly
```
