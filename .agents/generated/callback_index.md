# Callback Output Index — Auto-Generated

> **Generated**: 2026-05-29 11:45  
> **Do not edit** — run `python .agents/generated/sync_docs.py` to refresh.
> For ownership intent and architecture notes, see `docs/callback_ownership.md`.

---

**Total outputs indexed**: 133 across 12 files

## `app.py`

| Output ID | Property | Line | Duplicate? | Pattern? |
|-----------|----------|------|-----------|---------|
| `txn-store` | `data` | 250 | ✓ |  |
| `portfolio-store` | `data` | 322 | ✓ |  |
| `period-store` | `data` | 395 |  |  |
| `pnl-mode-store` | `data` | 405 |  |  |
| `ticker-store` | `data` | 415 |  |  |
| `treemap-mode-store` | `data` | 425 |  |  |
| `analytics-period-store` | `data` | 435 |  |  |
| `intel-period-store` | `data` | 445 |  |  |
| `intel-pred-store` | `data` | 474 |  |  |
| `intel-forecast-label` | `children` | 475 |  |  |
| `url` | `search` | 499 |  |  |
| `pending-tasks-store` | `data` | 517 | ✓ |  |
| `nav-link-store` | `data` | 551 | ✓ |  |
| `task-poll-interval` | `disabled` | 601 |  |  |

## `alert_callbacks.py`

| Output ID | Property | Line | Duplicate? | Pattern? |
|-----------|----------|------|-----------|---------|
| `alerts-banner` | `children` | 23 |  |  |
| `intel-alert-count` | `children` | 24 |  |  |
| `intel-alert-count` | `style` | 25 |  |  |

## `chart_callbacks.py`

| Output ID | Property | Line | Duplicate? | Pattern? |
|-----------|----------|------|-----------|---------|
| `ticker-selector` | `data` | 44 |  |  |
| `pnl-history-chart` | `figure` | 61 |  |  |
| `benchmark-pending-store` | `data` | 62 | ✓ |  |
| `price-chart` | `figure` | 172 |  |  |
| `portfolio-treemap` | `figure` | 207 |  |  |
| `analytics-vol-chart` | `children` | 242 |  |  |
| `corr-chart` | `figure` | 312 |  |  |
| `holdings-bubble-chart` | `figure` | 339 |  |  |
| `holdings-freshness-note` | `children` | 340 |  |  |
| `holdings-url-collapse` | `opened` | 341 | ✓ |  |
| `holdings-url-collapse` | `opened` | 403 | ✓ |  |
| `holdings-url-table` | `children` | 413 |  |  |
| `holdings-url-save-status` | `children` | 516 |  |  |
| `holdings-url-ticker-input` | `value` | 517 |  |  |
| `holdings-url-input` | `value` | 518 |  |  |

## `intelligence_callbacks.py`

| Output ID | Property | Line | Duplicate? | Pattern? |
|-----------|----------|------|-----------|---------|
| `intel-risk-cards` | `children` | 37 |  |  |
| `intel-equity-chart` | `figure` | 38 |  |  |
| `intel-drawdown-chart` | `figure` | 39 |  |  |
| `intel-alerts` | `children` | 40 |  |  |
| `intel-data-note` | `children` | 41 |  |  |
| `benchmark-pending-store` | `data` | 42 | ✓ |  |

## `portfolio_callbacks.py`

| Output ID | Property | Line | Duplicate? | Pattern? |
|-----------|----------|------|-----------|---------|
| `market-status` | `children` | 33 |  |  |
| `status-indicator-dot` | `className` | 41 |  |  |
| `last-updated-text` | `children` | 42 |  |  |
| `stat-cards` | `children` | 71 |  |  |
| `live-table` | `children` | 169 |  |  |

## `positions_callbacks.py`

| Output ID | Property | Line | Duplicate? | Pattern? |
|-----------|----------|------|-----------|---------|
| `positions-card-grid` | `children` | 56 |  |  |
| `positions-selected-ticker` | `data` | 183 |  |  |
| `etf-detail-cards` | `children` | 214 |  |  |
| `positions-tech-signals-container` | `children` | 215 |  |  |
| `ai-insight-container` | `children` | 329 |  |  |
| `positions-price-chart-container` | `children` | 419 |  |  |
| `positions-price-chart-header` | `style` | 420 |  |  |
| `positions-txn-table-container` | `children` | 535 |  |  |
| `positions-period-store` | `data` | 600 |  |  |
| `positions-period-btns` | `children` | 620 |  |  |
| `positions-detail-title` | `children` | 652 |  |  |
| `positions-ticker-dividend-container` | `children` | 668 |  |  |
| `positions-portfolio-dividend-chart-container` | `children` | 804 |  |  |
| `positions-dividend-income-chart` | `children` | 805 |  |  |
| `positions-dividend-yield-chart` | `children` | 806 |  |  |
| `positions-dividend-table` | `children` | 807 |  |  |

## `research_callbacks.py`

| Output ID | Property | Line | Duplicate? | Pattern? |
|-----------|----------|------|-----------|---------|
| `research-chat-store` | `data` | 28 |  |  |
| `research-chat-store` | `data` | 73 | ✓ |  |
| `research-input` | `value` | 74 |  |  |
| `research-usage-store` | `data` | 75 | ✓ |  |
| `research-typing-indicator` | `style` | 76 |  |  |
| `research-send-btn` | `disabled` | 77 |  |  |
| `report-cache-store` | `data` | 78 | ✓ |  |
| `ai-pending-tasks-store` | `data` | 79 | ✓ |  |
| `research-typing-indicator` | `style` | 258 | ✓ |  |
| `research-send-btn` | `disabled` | 259 | ✓ |  |
| `research-chat-store` | `data` | 272 | ✓ |  |
| `ai-pending-tasks-store` | `data` | 273 | ✓ |  |
| `report-cache-store` | `data` | 274 | ✓ |  |
| `research-chat-display` | `children` | 339 |  |  |
| `research-ticker-store` | `data` | 390 |  |  |
| `research-portfolio-summary` | `children` | 401 |  |  |
| `research-usage-display` | `children` | 455 |  |  |
| `report-download` | `data` | 525 |  |  |
| `research-chat-display` | `id` | 551 |  |  |

## `setup_callbacks.py`

| Output ID | Property | Line | Duplicate? | Pattern? |
|-----------|----------|------|-----------|---------|
| `dummy-redirect-output` | `children` | 115 |  |  |
| `setup-portfolio-table-body` | `children` | 122 |  |  |
| `setup-portfolio-rows-store` | `data` | 131 |  |  |
| `setup-portfolio-rows-store` | `data` | 145 | ✓ |  |
| `setup-portfolio-continue-btn` | `disabled` | 173 |  |  |
| `url` | `pathname` | 194 | ✓ |  |
| `setup-portfolio-feedback` | `children` | 195 |  |  |
| `txn-store` | `data` | 196 | ✓ |  |
| `url` | `pathname` | 251 | ✓ |  |
| `setup-ai-feedback` | `children` | 252 |  |  |
| `setup-ready-summary` | `children` | 303 |  |  |
| `url` | `pathname` | 345 | ✓ |  |
| `setup-is-first-run-store` | `data` | 346 | ✓ |  |
| `setup-ready-feedback` | `children` | 347 |  |  |

## `signals_callbacks.py`

| Output ID | Property | Line | Duplicate? | Pattern? |
|-----------|----------|------|-----------|---------|
| `pending-tasks-store` | `data` | 17 | ✓ |  |
| `global-signals-status-label` | `children` | 18 |  |  |
| `signals-store` | `data` | 99 |  |  |
| `watchlist-signals-store` | `data` | 100 |  |  |
| `pending-tasks-store` | `data` | 101 | ✓ |  |
| `refresh-trigger-store` | `data` | 102 |  |  |
| `global-signals-status-label` | `children` | 169 | ✓ |  |
| `signals-updated-chip` | `style` | 170 |  |  |

## `transaction_callbacks.py`

| Output ID | Property | Line | Duplicate? | Pattern? |
|-----------|----------|------|-----------|---------|
| `txn-ticker-hint` | `children` | 30 |  |  |
| `txn-price` | `value` | 31 |  |  |
| `txn-msg` | `children` | 79 |  |  |
| `txn-msg` | `style` | 80 |  |  |
| `compact-mode-store` | `data` | 81 | ✓ |  |
| `txn-log` | `children` | 125 |  |  |
| `txn-msg` | `children` | 135 | ✓ |  |

## `ui_callbacks.py`

| Output ID | Property | Line | Duplicate? | Pattern? |
|-----------|----------|------|-----------|---------|
| `theme-store` | `data` | 22 |  |  |
| `theme-icon-indicator` | `children` | 40 |  |  |
| `pdf-btn` | `children` | 47 |  |  |
| `compact-mode-store` | `data` | 54 |  |  |
| `txn-collapse` | `opened` | 55 |  |  |
| `compact-toggle-btn` | `children` | 56 |  |  |
| `compact-toggle-btn` | `className` | 57 |  |  |
| `folio-table-state-v3` | `data` | 89 |  |  |
| `nav-link-store` | `data` | 153 |  |  |
| `pending-tasks-store` | `data` | 159 | ✓ |  |

## `watchlist_callbacks.py`

| Output ID | Property | Line | Duplicate? | Pattern? |
|-----------|----------|------|-----------|---------|
| `watchlist-store` | `data` | 28 |  |  |
| `watchlist-input` | `value` | 29 |  |  |
| `watchlist-table-container` | `children` | 109 |  |  |
| `watchlist-msg` | `children` | 110 |  |  |
| `watchlist-selected-ticker` | `data` | 300 |  |  |
| `watchlist-selected-ticker` | `data` | 319 | ✓ |  |
| `watchlist-chart` | `figure` | 333 |  |  |
| `watchlist-chart-title` | `children` | 334 |  |  |
| `watchlist-period-store` | `data` | 420 |  |  |
| `{"type": "wl-period-btn", "index": ALL}` | `className` | 433 |  | ✓ |
| `watchlist-stat-cards` | `children` | 442 |  |  |
| `watchlist-tech-signals-container` | `children` | 443 |  |  |
| `watchlist-ai-insight-container` | `children` | 444 |  |  |
| `watchlist-notes-input` | `value` | 599 |  |  |
| `watchlist-notes-msg` | `children` | 609 |  |  |
| `watchlist-ticker-hint` | `children` | 623 |  |  |
