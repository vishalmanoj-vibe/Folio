# Execution Checklist — Folio Launch Readiness Fix

- [x] **Stage 2: Build**
  - [x] Implement `_wait_and_open_browser` thread in `launcher.py`
  - [x] Update `scripts/Folio.command` to delegate browser launch to `launcher.py`
  - [x] Create `scripts/install_shortcut.py` to sync Desktop shortcut
  - [x] Save build log in `.agents/production_artifacts/build_log.md`

- [x] **Stage 3: Verify & Stabilize**
  - [x] Run isolation tests for `launcher.py`
  - [x] Audit process cleanup & verify no orphan processes remain
  - [x] Run `ruff check` and `ruff format`

- [x] **Stage 4: Finalize & Document**
  - [x] Update `docs/reference/known_issues.md` with BUG-026 permanent resolution
  - [x] Run `python3 .agents/generated/sync_docs.py`
  - [x] Archive spec to `spec_phase26.md`

- [x] **Stage 5: Reflect & Learn**
  - [x] Finalize build report
