---
description: Master workflow to move from idea to verified production code
---

# /startcycle — Master Workflow

When the user runs `/startcycle [idea]`, the team will follow this high-density lifecycle to move from idea to verified production code.

> **Execution Model**: This is a **fully autonomous, 5-stage pipeline**. The ONLY pause point is after Stage 1 when the spec is presented to the user for approval. Once the user approves (or clicks Proceed), the agent MUST immediately and automatically execute Stages 2 → 3 → 4 → 5 in sequence **without stopping to ask for permission between stages**. Report progress at the end of each stage as a brief inline note, then continue immediately. Do not end your turn between stages.

---

### Stage 1 — @agent-pm: Design & Spec
1. **Research**: Read `GEMINI.md` (full read-order preamble) and existing layout/callback files to ensure architectural fit.
2. **Conflict Check**: Check `docs/reference/callback_ownership.md` for any Output IDs the spec plans to add or modify. Resolve conflicts before approval — do not leave them for the engineer.
3. **Ideator Consultation**: Prior to finalizing the technical spec, the PM MUST consult with `@agent-ideator` to conduct a design and feasibility review. `@agent-ideator` will generate a structured ideation artifact evaluating:
   - Technical advantages, disadvantages, and visual ROI of the proposed changes.
   - Critical pain points (e.g., server callback latency, rendering layout shifts, Plotly limitations, or cache stale/lock states).
   - Feasibility checks against the current Python, Dash, and SQLite stack.
4. **Pain Point Resolution**: The PM must address the Ideator's feedback, refine the layout/routing strategy, and document structural solutions to mitigate each highlighted pain point before writing the spec.
5. **Spec**: Write a technical spec to `.agents/production_artifacts/spec.md`:
   - Feature summary (2-3 sentences).
   - Modified/New files list.
   - **Component IDs**: Define all new Dash IDs.
   - **Data Strategy**: holdings, histories, or dcc.Store?
   - **Resolved Pain Points**: Specific structural or logical solutions addressing the critical issues identified by the Ideator.
6. **Fallback States**: For every new UI component, define explicitly what renders when data is empty, loading, or errored.
7. **External Dependencies**: If the feature requires any new pip install package, list it explicitly in the spec and get approval before Stage 2 begins.
8. **External URLs**: If the feature calls any external URL, list every URL in the spec. Engineer agent must verify each URL returns a 200 before using it in code.
9. **Approval**: Present the spec as the `implementation_plan.md` artifact (with `RequestFeedback = true`) and PAUSE. This is the **only pause** in the entire pipeline. Once the user clicks Proceed or provides comments and proceeds, IMMEDIATELY begin Stage 2 — do not ask any follow-up questions first. If the user's approval includes comments or change requests, incorporate them into the spec before starting Stage 2.
10. **Task List**: Create `task.md` tracking all Stage 2–5 checklist items. This is your execution checklist — mark items `[/]` in progress and `[x]` done as you work.

> ✅ **Stage 1 complete → immediately begin Stage 2 (no pause)**

### Stage 2 — @agent-engineer: Build
1. **Blueprint**: Read `.agents/production_artifacts/spec.md`.
2. **Full Read Order**: Follow the 6-step sequence from `GEMINI.md` before touching any file:
   - `.agents/skills/registry.md` → `docs/reference/callback_ownership.md` → `docs/reference/store_contracts.md` → `docs/reference/known_issues.md` → `GEMINI.md` → target file.
3. **Path Finding**: Use `grep -r` to locate the exact file before editing — never scan directories. See `.agents/skills/surgical_edit.md` for the grep patterns.
4. **Surgical Edit**: Follow `.agents/skills/surgical_edit.md` for every edit. Declare what you will NOT change before writing any code. Apply the edit budget rule: if the change touches more than 2 files or 150 lines, stop and get confirmation.
5. **Store Safety**: If touching any `dcc.Store` or callback that reads one, read `docs/reference/store_contracts.md` first. Access all store data with `.get()` and defaults — never assume keys exist.
6. **Known Issues Gate**: Before touching a chart builder, pattern-matched callback, or store callback, read `docs/reference/known_issues.md` and confirm you are not re-introducing a known bug.
7. **Log**: Save a summary to `.agents/production_artifacts/build_log.md` detailing new IDs and changed files.
8. For any feature involving network requests, read `.agents/skills/data_fetching.md` before writing any code.
9. **No hardcoded external URLs without verification**: Before using any provider URL, the engineer must confirm it returns a valid response. If unverifiable at build time, implement the DDGS discovery fallback pattern from `data_fetching.md`.
10. **Path Safety**: Any new file that references a data directory, cache path, or log path must import from `config/settings.py`. No hardcoded relative strings.
11. **New Component IDs**: Every new Dash component ID must be added to `.agents/skills/registry.md` before the build is considered complete.

> ✅ **Stage 2 complete → immediately begin Stage 3 (no pause)**

### Stage 3 — @agent-qa: Verify & Stabilize
1. **Audit**: Review the build against `GEMINI.md` and `.agents/skills/testing.md`.
2. **Visual Check**: Use `.agents/skills/aura_design_system.md` to verify the "Aura Ledger" look.
3. **Stability**: Ensure correct `prevent_initial_call` usage (False/initial_duplicate for rendering callbacks, True for interactions) is on all new callbacks.
4. **Store Contract Check**: Verify all `dcc.Store` accesses in changed files use `.get()` with defaults, per `docs/reference/store_contracts.md`. A bare `data["key"]` access is a bug.
5. **Known Issues Cross-Reference**: Compare all touched files against `docs/reference/known_issues.md`. If a touched file matches a known bug's "Files affected" list, confirm the fix pattern is still present in the code.
6. **Diff Review**: Review the full diff for unintended deletions, renamed imports, changed callback wiring, and modified store keys — not just the added lines.
7. **Fix**: Resolve any minor stability issues directly.
8. For features with external data fetching, run the isolation test from `data_fetching.md` Section 12 and paste output into `build_log.md` before approving.
9. **Dependency Check**: Confirm all new packages in `requirements.txt` have been manually installed and that any manual post-install steps are documented in the build report.
10. **No Portfolio DB Modification**: QA must never delete, overwrite, or modify `portfolio.db` during any test.
11. **Orphan Process Check**: After any test that starts the app, confirm no orphan processes remain: `ps aux | grep -E "app.py|worker.py"` must return nothing after the app is closed.

> ✅ **Stage 3 complete → immediately begin Stage 4 (no pause)**

### Stage 4 — @agent-docs: Finalize
1: **ReadMe**: Update the project README or create a feature-specific doc in `.agents/production_artifacts/`.
2: **Report**: Summarize the build, files changed, and instructions on how to test it.
3: **Context Docs**: Update `docs/reference/callback_ownership.md` with any new Output IDs added during the build. Remove entries for deleted outputs.
4: Update the user documentations — `docs/guides/DEVELOPER_GUIDE.md`, `docs/guides/ALGORITHMS_AND_FEATURES.md` (if mathematical/special features added), `requirements.txt`, and `docs/history/BUILD_HISTORY.md`.
5: **Link Verification**: Run the link checking script to ensure no broken relative targets exist:
   ```bash
   python3 scratch/check_links.py
   ```
6: **Spec Archive**: After each completed cycle, copy the final approved spec from `.agents/production_artifacts/spec.md` to `.agents/production_artifacts/spec_phase{N}.md` so specs are never overwritten by the next cycle.
7: **Auto-Sync Indexes** *(mandatory final step)*: Run the following command to regenerate the callback and store index files from the live codebase. This MUST be executed before reporting completion to the user:
   ```bash
   python3 .agents/generated/sync_docs.py
   ```
   Confirm the script prints `✓ Written: .agents/generated/callback_index.md` and `✓ Written: .agents/generated/store_index.md`. If it errors, fix the error before closing the cycle.

> ✅ **Stage 4 complete → immediately begin Stage 5 (no pause)**

### Stage 5 — Reflect & Learn
1. **Self-Improvement**: If we hit a new error or pattern, update the relevant `.agents/skills/*.md` or `GEMINI.md` file automatically. If a scraper or external data feature was built, update .agents/skills/data_fetching.md with any new provider patterns, failure modes discovered, or URL structures confirmed working.

---
Report to the user when the cycle is complete.