# Project Evolution & Build History Index

This document serves as the central index chronicling the technical evolution of Folio. It links to detailed chronological logs and their corresponding feature specifications.

## ⚡ Versioning & Phase Indexing Note
Please note that early development phases contain a version numbering typo (`v3.6.0 – v3.9.0` instead of `v1.36.0 – v1.39.0`). Subsequent features follow the `v2.0.0` release and are correctly numbered under the `v2.x` tag scheme, but reset the Phase indexing back to Phase 7/8. Both paths are fully explained in their respective child logs.

---

## Chronological Tracks

### 1. [Foundations & Core Features (Phases 1–6)](BUILD_HISTORY_FOUNDATIONS.md)
*Covers the initial prototyping up to the professionalization and UI styling refinement era (v0.1.0 – v3.5.0).*
*   **Phase 1: Foundations & UI (v0.1.0 – v0.4.0)**: Core navigation structure, multi-page routing layout, exposure calculation, and light/dark theme toggle.
*   **Phase 2: Deep Dive & Market Insights (v0.5.0 – v1.0.0)**: Integrated Facebook Prophet forecasting, ex-dividend date realized income tracking, and intraday snapshots.
*   **Phase 3: Performance & Scalability (v1.1.0 – v1.5.0)**: ThreadPool market fetches, modular CSS structure, and ETF metadata caching.
*   **Phase 4: The Assistant & Technical Engine (v1.6.0 – v2.2.0)**: pure-pandas Technical indicators (RSI/MACD/BB), web news search helper, PDF reports.
    *   *Related Specs:* [spec_phase4_floating_chatbot.md](../../.agents/production_artifacts/spec_phase4_floating_chatbot.md), [spec_phase2_dividend_tracking.md](../../.agents/production_artifacts/spec_phase2_dividend_tracking.md)
*   **Phase 5: Architectural Maturity & Relational Migration (v2.3.0 – v3.0.0)**: SQLite WAL database transition, rule-based strategy engine vs AI critique, unified assistant.
    *   *Related Specs:* [spec_phase10_holdings_hierarchy.md](../../.agents/production_artifacts/spec_phase10_holdings_hierarchy.md)
*   **Phase 6: Professionalization & UI Refinement (v3.1.0 – v3.5.0)**: Plotly treemap canvas blend, table suggestion badges, 16px/24px grid standardization.
    *   *Related Specs:* [spec_phase6_dashboard_enhancements.md](../../.agents/production_artifacts/spec_phase6_dashboard_enhancements.md), [spec_phase6_deeplink_selection.md](../../.agents/production_artifacts/spec_phase6_deeplink_selection.md)

### 2. [Performance Tuning & Distributed Architecture (Phases 7–10)](BUILD_HISTORY_PERFORMANCE_ERA.md)
*Covers performance optimization, multi-tier intervals, lazy loading, and process isolation up to version v2.0.0.*
*   **Phase 7: Rendering Prioritization & UX Polish (v1.36.0 – v1.37.0)**: Fast startup cache snapshots, off-screen callback suppression, and skeleton loaders.
    *   *Related Specs:* [spec_phase7_setup_ux_improvements.md](../../.agents/production_artifacts/spec_phase7_setup_ux_improvements.md)
*   **Phase 8: Aesthetic Excellence & Chart Standardization (v1.38.0 – Current)**: Unified `apply_standard_layout` chart helper, glassmorphism headers, 200ms theme transitions.
    *   *Related Specs:* [spec_phase8_micro_animations.md](../../.agents/production_artifacts/spec_phase8_micro_animations.md)
*   **Phase 9: Performance Baseline & Multi-Tier Intervals (v1.39.0 – Current)**: CPU/memory profiling, 30s heartbeat vs 300s price interval, market closed sleep calculations, lazy Prophet imports, compact pandas series.
    *   *Related Specs:* [spec_phase9_memory_optimization.md](../../.agents/production_artifacts/spec_phase9_memory_optimization.md)
*   **Phase 10: Enterprise-Grade Memory Hygiene & Distributed Architecture (v2.0.0 – Current)**: Dual-process `launcher.py` and `worker.py`, holdings scraper offloading, drag-and-drop watchlist reordering, underlying ETF treemap.
    *   *Related Specs:* [spec_phase10_watchlist_reorder.md](../../.agents/production_artifacts/spec_phase10_watchlist_reorder.md), [spec_phase10_treemap_underlying.md](../../.agents/production_artifacts/spec_phase10_treemap_underlying.md), [spec_phase10_correlation_reactivity.md](../../.agents/production_artifacts/spec_phase10_correlation_reactivity.md), [spec_phase10_setup_prefetch.md](../../.agents/production_artifacts/spec_phase10_setup_prefetch.md)

### 3. [Onboarding, Packaging & Settings (Post-v2.0.0 Tracks)](BUILD_HISTORY_ONBOARDING_LIFECYCLE.md)
*Covers macOS App bundle build, uv installers, browser lifecycle hooks, layman dictionaries, onboarding settings wizard, and multi-provider AI config (v2.4.0 – v2.8.0).*
*   **Phase 7: Distribution, Packaging & Setup UX (v2.4.0)**: uv-based automatic installer scripts, macOS `.app` bundle, Windows startup launchers, and desktop shortcuts.
    *   *Related Specs:* [spec_phase11_packaging_uv.md](../../.agents/production_artifacts/spec_phase11_packaging_uv.md)
*   **Phase 8: Browser-Close Graceful Shutdown (v2.5.0)**: `beforeunload` beacon tracking and debounced Flask termination to match browser lifetime.
*   **Phase 11: Layman-Friendly Documentation & Onboarding Guidance (v2.6.0)**: Overhauled README, double-process structure flowchart, and finance-to-English dictionary.
    *   *Related Specs:* [spec_phase13_readme_overhaul.md](../../.agents/production_artifacts/spec_phase13_readme_overhaul.md)
*   **Phase 12: Investor Profile Settings in Onboarding Wizard (v2.7.0)**: Strategy setups, investment goal/riskTolerance dropdowns, SQLite profile persistence, and dynamic weights preview.
    *   *Related Specs:* [spec_phase14_onboarding_settings.md](../../.agents/production_artifacts/spec_phase14_onboarding_settings.md)
*   **Phase 13: Multi-Provider AI Model Selection (v2.8.0)**: abstraction gateway (`services/ai_provider.py`), active provider selection, dynamic model options, API key test connection button, settings configuration UI.
    *   *Related Specs:* [spec_phase13_multi_provider.md](../../.agents/production_artifacts/spec_phase13_multi_provider.md)
*   **Phase 14: Onboarding Graceful Restart (v2.9.0)**: Graceful Dash process restart using exit code 3 upon onboarding completion, enabling clean reload of initial holdings and transactions.
    *   *Related Specs:* [spec_phase15_graceful_restart.md](../../.agents/production_artifacts/spec_phase15_graceful_restart.md)
