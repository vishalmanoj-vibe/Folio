# /startcycle — Master Workflow

When the user runs `/startcycle [idea]`, the team will follow this high-density lifecycle to move from idea to verified production code.

---

### Stage 1 — @agent-pm: Design & Spec
1. **Research**: Read `GEMINI.md` and existing layout/callback files to ensure architectural fit.
2. **Spec**: Write a technical spec to `.agents/production_artifacts/spec.md`:
   - Feature summary (2-3 sentences).
   - Modified/New files list.
   - **Component IDs**: Define all new Dash IDs.
   - **Data Strategy**: holdings, histories, or dcc.Store?
3. **Approval**: PAUSE and get explicit user approval before any code is written.

### Stage 2 — @agent-engineer: Build
1. **Blueprint**: Read `.agents/production_artifacts/spec.md`.
2. **Registry Check**: Check `.agents/skills/registry.md` to ensure no ID collisions.
3. **Execution**: Follow the relevant `.agents/skills/*.md` files:
   - New charts → `.agents/skills/add_chart.md`
   - Data logic → `.agents/skills/data_integrity.md`
   - UI styling → `.agents/skills/ui_ux.md` & `.agents/skills/aura_design_system.md`
4. **Log**: Save a summary to `.agents/production_artifacts/build_log.md` detailing new IDs and changed files.

### Stage 3 — @agent-qa: Verify & Stabilize
1. **Audit**: Review the build against `GEMINI.md` and `.agents/skills/testing.md`.
2. **Visual Check**: Use `.agents/skills/aura_design_system.md` to verify the "Aura Ledger" look.
3. **Stability**: Ensure `prevent_initial_call=True` is on all new callbacks.
4. **Fix**: Resolve any minor stability issues directly.

### Stage 4 — @agent-docs: Finalize
1. **ReadMe**: Update the project README or create a feature-specific doc in `.agents/production_artifacts/`.
2. **Report**: Summarize the build, files changed, and instructions on how to test it.

### Stage 5 — Reflect & Learn
1. **Self-Improvement**: If we hit a new error or pattern, update the relevant `.agents/skills/*.md` or `GEMINI.md` file automatically.

---
Report to the user when the cycle is complete.