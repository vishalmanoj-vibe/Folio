# Project Evolution & Build History

This document chronicles the technical evolution of Folio, transitioning from a basic tracking tool into a sophisticated, AI-driven market intelligence platform.

---

## Phase 1: Foundations & UI (v0.1.0 – v0.4.0)
**Theme**: Establishment of core navigation and basic P&L tracking.

*   **Initial Prototype**: Established the multi-page Dash structure with a shared sidebar and persistent stores.
*   **Design System**: Implemented the first iteration of Light/Dark mode and a basic grid layout.
*   **Early Intelligence**: Added exposure calculations and category drill-downs to understand basic asset allocation.
*   **Infrastructure**: Added the first `Developer Guide` to standardize component-based development.

---

## Phase 2: Analytics & Market Intelligence (v0.5.0 – v1.0.0)
**Theme**: Moving beyond static data with forecasting and real-time intraday tracking.

*   **Predictive Analysis**: Integrated **Facebook Prophet** for forward-looking price projections with confidence intervals.
*   **Dividend Engine**: Developed a custom "Realized Dividend" logic that matches tranche purchase dates against historical ex-dividend dates for dollar-accurate income tracking.
*   **Intraday Snapshots**: Solved the "Jagged Data" problem by implementing a local JSON snapshotting system for 5-minute intraday tracking within ASX session windows.
*   **Visualization Overhaul**: Replaced standard charts with high-density **Treemaps** for allocation and **Lollipop** charts for performance metrics.

---

## Phase 3: Performance & Scalability (v1.1.0 – v1.5.0)
**Theme**: Architectural optimization to handle growing portfolios and high-frequency data.

*   **Parallel Fetching**: Implemented `ThreadPoolExecutor` and bulk `yf.download()` requests to reduce market data loading times by ~70%.
*   **CSS Modularization**: Transitioned from a monolithic `base.css` to a component-based directory (`tokens`, `layout`, `components`), significantly reducing style collisions.
*   **State Management**: Optimized `dcc.Store` usage, separating the heavy `portfolio-store` (data) from session-scoped UI preferences.
*   **Metadata Caching**: Added persistent caching for ETF metadata to avoid redundant Yahoo Finance API calls.

---

## Phase 4: The AI Analyst & Technical Engine (v1.6.0 – v2.2.0)
**Theme**: Integrating Generative AI and quantitative technical analysis.

*   **Research Assistant**: Integrated **Google Gemini (flash-lite)** with full portfolio context awareness for interactive research.
*   **Technical Engine**: Developed a pure-pandas technical analysis engine (no external libs) to compute **RSI**, **MACD**, and **Bollinger Bands** on the fly.
*   **AI Search Service**: Enabled real-time market intelligence by integrating a live web-search service into the AI's research context.
*   **Report Generation**: Built a backend PDF service to generate weekly automated summaries with P&L performance charts and news sentiment.

---

## Phase 5: Architectural Maturity & Relational Migration (v2.3.0 – v3.0.0)
**Theme**: Robustness through SQLite persistence and a strict 4-layer modular structure.

*   **SQLite Migration**: Fully decommissioned CSV and local JSON files for core data. Implemented **SQLite in WAL (Write-Ahead Logging) mode** for superior concurrency and state persistence.
*   **Strategy Engine**: Centralized signal logic into a rule-based engine. Established the boundary where the Engine generates signals and the AI *explains* them, preventing AI "hallucination" in trading signals.
*   **Unified AI Analyst**: Consolidated Research and Reports into a single, high-performance page with deterministic caching and responsive AI insight containers.
*   **The 4-Layer Standard**: Finalized the current architectural standard:
    1.  **Presentation (Dash)**: UI and Callbacks.
    2.  **Service (Business Logic)**: Data fetching and formatting.
    3.  **Engine (Math/AI)**: Quantitative and qualitative intelligence.
    4.  **Data (Repository)**: SQLite persistence.

---

## Phase 6: Professionalization & UI Refinement (v3.1.0 – v3.5.0)
**Theme**: Polishing the visual experience and ensuring system-wide compliance.

*   **Analytics Visualization Fix**: Solved persistent "grey canvas" artifacts in Treemaps by harmonizing Plotly backgrounds with CSS surface tokens and implementing theme-aware typography for hierarchical data.
*   **Portfolio Suggestions**: Integrated the Strategy Engine directly into the main Overview table, providing instant BUY/SELL/HOLD signals alongside live P&L data.
*   **UI Standardization**: Enforced a strict **16px/24px global grid** and centralized all content wrappers into a single `section()` helper to ensure layout consistency across all pages.
*   **Intraday Resiliency**: Refined the "Today" view with 5-minute resampling, Plotly `rangebreaks` to hide non-trading hours, and a 15:00 lookback window for cross-session continuity.
*   **Compliance Audit**: Executed a 100% precision audit of the codebase, standardizing logging to use `logger.debug()` (replacing `print`) and verifying `prevent_initial_call=True` for all page-specific callbacks.

---

## Phase 7: Rendering Prioritization & Fast Startup (v3.6.0 – Current)
**Theme**: Optimizing for extreme responsiveness and zero-latency user experiences.

*   **Fast Startup Architecture**: Refactored the core application lifecycle to eliminate blocking market data fetches during initialization. The dashboard now boots instantly (<1s) using disk-cached state, with live data refreshing in the background after the UI is interactive.
*   **Rendering Prioritization**: Implemented a URL-aware callback strategy that eliminates "DOM thrashing" and UI flicker. By making rendering callbacks aware of the active page, the browser only updates visible components, significantly reducing CPU load during high-frequency market updates.
*   **Standardized Empty States**: Introduced a centralized chart fallback system (`create_empty_fig`) to ensure all visualizations maintain a professional aesthetic during loading or error states, replacing broken axes artifacts with user-friendly annotations.
