# Execution Checklist — Incremental Signal Generation

## Stage 1 — Design & Spec
- [x] Research existing signal generation architecture and store contracts
- [x] Design & feasibility review (@agent-ideator pain point resolution)
- [x] Technical spec created at `.agents/production_artifacts/spec.md`
- [x] Implementation plan created and presented for user approval

## Stage 2 — Build (@agent-engineer)
- [x] Follow GEMINI.md required read order
- [x] Modify `worker.py`: Update `handle_generate_signals` for per-ticker incremental execution & SQLite commit
- [x] Modify `callbacks/signals_callbacks.py`: Update `poll_tasks_and_update_stores` to stream running signal results into `signals-store` / `watchlist-signals-store`
- [x] Code formatting & lint checks (`ruff check --fix`, `ruff format`)
- [x] Save build log to `.agents/production_artifacts/build_log.md`

## Stage 3 — Verify & Stabilize (@agent-qa)
- [x] Verify callback stability and `prevent_initial_call` settings
- [x] Verify store contract compliance (`.get()` with defaults)
- [x] Cross-reference `docs/reference/known_issues.md`
- [x] Verify full diff for unintended side-effects
- [x] Confirm no orphaned processes or DB modifications

## Stage 4 — Finalize (@agent-docs)
- [x] Update context docs (`docs/reference/callback_ownership.md`, `.agents/skills/registry.md`)
- [x] Update developer guides / documentation as needed (build_log.md)
- [x] Verify relative links (`python3 scratch/check_links.py`) — 1 pre-existing broken link in GEMINI.md example, not introduced by this build
- [x] Archive spec to `.agents/production_artifacts/spec_phase10_incremental_signals.md`
- [x] Run auto-sync script (`python3 .agents/generated/sync_docs.py`)

## Stage 5 — Reflect & Learn
- [x] Self-improvement check — no new GEMINI.md rule needed; existing per-ticker commit pattern now codified in build_log.md

