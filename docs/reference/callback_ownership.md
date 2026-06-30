# Callback Output Ownership Map — Folio

> **Purpose**: Every `Output` ID is owned by exactly ONE callback in ONE file.
> Before adding any callback, check this map. Duplicate Outputs cause silent
> Dash crashes. If using `allow_duplicate=True`, document the reason inline.
>
> **Last synced**: 2026-06-09

---

## `app.py` (Global / Cross-Page)

| Output ID | Property | Notes |
|-----------|----------|-------|
| `txn-store` | `data` | Single writer for all transactions. `allow_duplicate=True` for startup sync. |
| `portfolio-store` | `data` | Single writer. `allow_duplicate=True` for store pattern. |
| `period-store` | `data` | Period picker sync. |
| `pnl-mode-store` | `data` | Mode toggle sync. |
| `ticker-store` | `data` | Ticker selector sync. |
| `treemap-mode-store` | `data` | Treemap mode sync. |
| `analytics-period-store` | `data` | Analytics period sync. |
| `intel-period-store` | `data` | Intelligence period sync. |
| `intel-pred-store` | `data` | Forecast toggle. |
| `intel-forecast-label` | `children` | Label next to toggle. |
| `url` | `search` | Startup maintenance trigger only. |
| `pending-tasks-store` | `data` | Startup hydration. `allow_duplicate=True`. |
| `nav-link-store` | `data` | Clientside no-op. `allow_duplicate=True`. |
| `task-poll-interval` | `disabled` | Clientside task manager. |
| `[picker_id]` | `value` | Clientside store→UI sync loop (6 pickers). |

---

## `callbacks/portfolio_callbacks.py`

| Output ID | Property | Notes |
|-----------|----------|-------|
| `market-status` | `children` | Live market badge. |
| `status-indicator-dot` | `className` | Pulsing dot class. |
| `last-updated-text` | `children` | "Updated HH:MM" text. |
| `stat-cards` | `children` | KPI summary cards. |
| `live-table` | `children` | Main holdings table. |

---

## `callbacks/chart_callbacks.py`

| Output ID | Property | Notes |
|-----------|----------|-------|
| `ticker-selector` | `options` | Ticker dropdown population. |
| `pnl-history-chart` | `figure` | Core P&L equity curve. |
| `benchmark-pending-store` | `data` | Benchmark task ID (shared write, see also `intelligence_callbacks`). |
| `price-chart` | `figure` | Analytics normalised price chart. |
| `portfolio-treemap` | `figure` | Allocation treemap. Also outputs to `holdings-freshness-note` (`children`) and `holdings-url-collapse` (`opened`). |
| `analytics-vol-chart` | `figure` | Volatility bar chart. |
| `corr-chart` | `figure` | Correlation heatmap. |
| `holdings-freshness-note` | `children` | ETF data freshness note (owned by `portfolio_treemap`). |
| `holdings-url-collapse` | `opened` | ETF URL form toggle (2 callbacks: `toggle_url_collapse` and `portfolio_treemap` with `allow_duplicate=True`). |
| `holdings-url-table` | `children` | ETF URL table. |
| `holdings-url-save-status` | `children` | ETF URL save status. |
| `holdings-url-ticker-input` | `value` | ETF URL ticker field reset. |
| `holdings-url-input` | `value` | ETF URL field reset. |

---

## `callbacks/positions_callbacks.py`

| Output ID | Property | Notes |
|-----------|----------|-------|
| `positions-card-grid` | `children` | Ticker card grid. |
| `positions-selected-ticker` | `data` | Store — active card. |
| `etf-detail-cards` | `children` | Metrics card grid. |
| `positions-tech-signals-container` | `children` | Technical signal badges. |
| `ai-insight-container` | `children` | AI explanation block. |
| `positions-price-chart-container` | `children` | Price chart wrapper. |
| `positions-price-chart-header` | `children` | Chart section header. |
| `positions-txn-table-container` | `children` | Transaction table wrapper. |
| `positions-period-store` | `data` | Period selection store. |
| `positions-period-btns` | `children` | Period button row. |
| `positions-detail-title` | `children` | Detail panel heading. |
| `positions-ticker-dividend-container` | `children` | Per-ticker dividend block. |
| `positions-portfolio-dividend-chart-container` | `children` | Portfolio dividend chart container. |
| `positions-dividend-income-chart` | `figure` | Dividend income chart. |
| `positions-dividend-yield-chart` | `figure` | Dividend yield chart. |
| `positions-dividend-table` | `children` | Dividend table. |

---

## `callbacks/watchlist_callbacks.py`

| Output ID | Property | Notes |
|-----------|----------|-------|
| `watchlist-store` | `data` | Watchlist market data store. |
| `watchlist-input` | `value` | Input field reset after add. |
| `watchlist-table-container` | `children` | Full watchlist table. |
| `watchlist-msg` | `children` | Status/error message. |
| `watchlist-selected-ticker` | `data` | Active watchlist ticker (2 callbacks: row click + card select). |
| `watchlist-chart` | `figure` | Price history chart. |
| `watchlist-chart-title` | `children` | Chart title. |
| `watchlist-period-store` | `data` | Period store. |
| `{"type": "wl-period-btn", ...}` | `variant` | Period button active state. |
| `watchlist-stat-cards` | `children` | Stat card grid. |
| `watchlist-tech-signals-container` | `children` | Technical badges. |
| `watchlist-ai-insight-container` | `children` | AI insights block. |
| `watchlist-notes-input` | `value` | Notes textarea. |
| `watchlist-notes-msg` | `children` | Notes save status. |
| `watchlist-ticker-hint` | `children` | Ticker name hint. |

---

## `callbacks/signals_callbacks.py`

| Output ID | Property | Notes |
|-----------|----------|-------|
| `pending-tasks-store` | `data` | Task enqueue (allow_duplicate). |
| `global-signals-status-label` | `children` | Status label (2 callbacks: start + complete). |
| `signals-store` | `data` | Portfolio signals. |
| `watchlist-signals-store` | `data` | Watchlist signals. |
| `refresh-trigger-store` | `data` | Trigger for store refresh. |
| `signals-updated-chip` | `children` | "Updated" chip display. |

---

## `callbacks/intelligence_callbacks.py`

| Output ID | Property | Notes |
|-----------|----------|-------|
| `intel-risk-cards` | `children` | Risk KPI cards. |
| `intel-equity-chart` | `figure` | Equity curve. |
| `intel-drawdown-chart` | `figure` | Drawdown chart. |
| `intel-alerts` | `children` | Smart alert cards. |
| `intel-data-note` | `children` | Data annotation. |
| `benchmark-pending-store` | `data` | Benchmark task ID (shared with chart_callbacks). |

---

## `callbacks/ui_callbacks.py`

| Output ID | Property | Notes |
|-----------|----------|-------|
| `theme-store` | `data` | Light/dark toggle. |
| `theme-toggle-hidden` | `children` | Clientside theme synchronizer hook. |
| `pdf-btn-hidden` | `children` | Clientside print export trigger hook. |
| `compact-mode-store` | `data` | Compact toggle. |
| `txn-collapse` | `is_open` | Transaction form collapse. |
| `compact-toggle-btn` | `children` | Button label + style. |
| `folio-table-state-v3` | `data` | Table sort/search state. |
| `nav-link-store` | `data` | Active nav tracking. |
| `pending-tasks-store` | `data` | Task poll (allow_duplicate). |
| `palette-ticker-store` | `data` | Sync tickers for command palette. |

---

## `callbacks/alert_callbacks.py`

| Output ID | Property | Notes |
|-----------|----------|-------|
| `alerts-banner` | `children` | Global alert strip. |
| `intel-alert-count` | `children` | Nav badge count (2 callbacks). |

---

## `callbacks/transaction_callbacks.py`

| Output ID | Property | Notes |
|-----------|----------|-------|
| `txn-ticker-hint` | `children` | Ticker name hint. |
| `txn-price` | `value` | Price field auto-fill / edit populate. `allow_duplicate=True`. |
| `txn-msg` | `children` | Status feedback (multiple callbacks). |
| `compact-mode-store` | `data` | Compact store side-effect on submit. |
| `txn-log` | `children` | Transaction log table. |
| `txn-type` | `value` | Edit populate and reset form. `allow_duplicate=True`. |
| `txn-ticker` | `value` | Edit populate and reset form. `allow_duplicate=True`. |
| `txn-shares` | `value` | Edit populate and reset form. `allow_duplicate=True`. |
| `txn-date` | `value` | Edit populate and reset form. `allow_duplicate=True`. |
| `txn-editing-id-store` | `data` | Tracks transaction ID being edited. `allow_duplicate=True`. |
| `txn-submit` | `children` | Toggle label Add/Update. `allow_duplicate=True`. |
| `txn-cancel` | `style` | Toggle display visible/hidden. `allow_duplicate=True`. |
| `txn-collapse` | `opened` | Expand form when editing. `allow_duplicate=True`. |

---

## `callbacks/setup_callbacks.py`

| Output ID | Property | Notes |
|-----------|----------|-------|
| `dummy-redirect-output` | `children` | Clientside redirect guard. |
| `setup-portfolio-table-body` | `children` | Setup table. |
| `setup-portfolio-rows-store` | `data` | Setup rows (2 callbacks). |
| `setup-portfolio-continue-btn` | `disabled` | Continue button state. |
| `url` | `pathname` | Redirect after setup steps. |
| `setup-portfolio-feedback` | `children` | Setup feedback text. |
| `txn-store` | `data` | Setup commits transactions (allow_duplicate). |
| `setup-ai-feedback` | `children` | AI key feedback. |
| `setup-is-first-run-store` | `data` | First-run flag. |
| `setup-ready-feedback` | `children` | Final ready feedback. |
| `setup-init-tasks-store` | `data` | Session store for task IDs + phase. Primary: `auto_start_fetch`. Secondary: `poll_init_progress` (allow_duplicate). |
| `setup-poll-interval` | `disabled` | Poll interval on/off. Primary: `auto_start_fetch`. Secondary: `poll_init_progress` (allow_duplicate). |
| `setup-init-step-list` | `children` | Per-task step rows (poll_init_progress). |
| `setup-init-progress-label` | `children` | "X of Y tasks" label (poll_init_progress). |
| `setup-init-progress-bar` | `style` | Progress bar fill width (poll_init_progress). |
| `setup-init-status-msg` | `children` | Timeout warning message (poll_init_progress). |
| `setup-ready-launch-btn` | `disabled` | Gated by critical task completion (poll_init_progress). |
| `setup-ready-summary` | `children` | Phase B summary content (poll_init_progress). |
| `setup-ready-summary` | `style` | Show/hide summary box (poll_init_progress). |
| `setup-init-progress-container` | `style` | Show/hide progress tracker (poll_init_progress). |
| `setup-init-title` | `children` | Dynamic title text (poll_init_progress). |
| `setup-init-subtitle` | `children` | Dynamic subtitle text (poll_init_progress). |

---

## `callbacks/research_callbacks.py`

| Output ID | Property | Notes |
|-----------|----------|-------|
| `research-chat-store` | `data` | Chat history (multiple callbacks for init/send/stream). |
| `research-input` | `value` | Input field reset. |
| `research-usage-store` | `data` | Usage counter. |
| `research-typing-indicator` | `children` | Typing animation. |
| `research-send-btn` | `disabled` | Send button state. |
| `report-cache-store` | `data` | Report cache (multiple callbacks). |
| `ai-pending-tasks-store` | `data` | AI task tracking. |
| `research-chat-display` | `children` | Chat display (2 callbacks). |
| `research-ticker-store` | `data` | Active research ticker. |
| `research-usage-display` | `children` | Usage counter display. |
| `report-download` | `data` | File download trigger. |
| `chatbot-window` | `style` | Chatbot open/closed visibility state. |
| `chatbot-trigger` | `style` | Floating trigger button visibility state. |
| `chatbot-context-bar` | `children` | Active page & ticker context display. |
| `qp-1` | `children`, `style` | Custom dynamic quick prompt 1. |
| `qp-2` | `children`, `style` | Custom dynamic quick prompt 2. |
| `qp-3` | `children`, `style` | Custom dynamic quick prompt 3. |
| `qp-4` | `children`, `style` | Custom dynamic quick prompt 4. |

---

## `callbacks/settings_callbacks.py`

| Output ID | Property | Notes |
|-----------|----------|-------|
| `settings-investment-goal` | `value` | Initial settings load. |
| `settings-risk-tolerance` | `value` | Initial settings load. |
| `settings-tax-bracket` | `value` | Initial settings load. |
| `settings-chat-model` | `value` | AI chat model selection (Standard/Enhanced). |
| `settings-report-model` | `value` | AI report model selection (Standard/Enhanced). |
| `settings-weights-preview-container` | `children` | Dynamic strategy weights preview. |
| `settings-save-status` | `children` | Settings save confirmation message. |

---

## Rules

1. **Before adding a new callback**, grep this file for the Output ID.
2. **If the ID is already owned**, you cannot add another Output to it without `allow_duplicate=True` — and that should be rare and intentional.
3. **After adding a new callback**, update this file.
4. **Pattern-matched outputs** (e.g. `{"type": "pos-card", "index": ALL}`) are owned by the callback file where they're defined — document them in the Pattern-Matched section of `registry.md`.
