# Callback Output Index — Auto-Generated

> **Generated**: 2026-06-04 23:42  
> **Do not edit** — run `python .agents/generated/sync_docs.py` to refresh.
> For ownership intent and architecture notes, see `docs/callback_ownership.md`.

---

**Total outputs indexed**: 140 across 13 files

## `app.py`

| Output ID | Property | Line | Duplicate? | Pattern? |
|-----------|----------|------|-----------|---------|
| `txn-store` | `data` | 257 | ✓ |  |
| `portfolio-store` | `data` | 329 | ✓ |  |
| `period-store` | `data` | 402 |  |  |
| `pnl-mode-store` | `data` | 412 |  |  |
| `ticker-store` | `data` | 422 |  |  |
| `treemap-mode-store` | `data` | 432 |  |  |
| `analytics-period-store` | `data` | 442 |  |  |
| `intel-period-store` | `data` | 452 |  |  |
| `intel-pred-store` | `data` | 481 |  |  |
| `intel-forecast-label` | `children` | 482 |  |  |
| `url` | `search` | 507 |  |  |
| `pending-tasks-store` | `data` | 525 | ✓ |  |
| `nav-link-store` | `data` | 559 | ✓ |  |
| `task-poll-interval` | `disabled` | 609 |  |  |

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
| `benchmark-pending-store` | `data` | 61 | ✓ |  |
| `pnl-history-chart` | `figure` | 86 |  |  |
| `benchmark-pending-store` | `data` | 87 | ✓ |  |
| `price-chart` | `figure` | 198 |  |  |
| `portfolio-treemap` | `figure` | 233 |  |  |
| `analytics-vol-chart` | `children` | 268 |  |  |
| `corr-chart` | `figure` | 338 |  |  |
| `holdings-bubble-chart` | `figure` | 365 |  |  |
| `holdings-freshness-note` | `children` | 366 |  |  |
| `holdings-url-collapse` | `opened` | 367 | ✓ |  |
| `holdings-url-collapse` | `opened` | 429 | ✓ |  |
| `holdings-url-table` | `children` | 439 |  |  |
| `holdings-url-save-status` | `children` | 542 |  |  |
| `holdings-url-ticker-input` | `value` | 543 |  |  |
| `holdings-url-input` | `value` | 544 |  |  |

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
| `positions-card-grid` | `children` | 55 |  |  |
| `positions-selected-ticker` | `data` | 182 |  |  |
| `etf-detail-cards` | `children` | 213 |  |  |
| `positions-tech-signals-container` | `children` | 214 |  |  |
| `ai-insight-container` | `children` | 329 |  |  |
| `positions-price-chart` | `figure` | 419 |  |  |
| `positions-price-chart-header` | `style` | 420 |  |  |
| `positions-txn-table-container` | `children` | 535 |  |  |
| `positions-period-store` | `data` | 600 |  |  |
| `positions-period-btns` | `children` | 620 |  |  |
| `positions-detail-title` | `children` | 652 |  |  |
| `positions-ticker-dividend-container` | `children` | 668 |  |  |
| `positions-portfolio-dividend-chart-container` | `children` | 810 |  |  |
| `positions-dividend-income-chart` | `children` | 811 |  |  |
| `positions-dividend-yield-chart` | `children` | 812 |  |  |
| `positions-dividend-table` | `children` | 813 |  |  |

## `research_callbacks.py`

| Output ID | Property | Line | Duplicate? | Pattern? |
|-----------|----------|------|-----------|---------|
| `research-chat-store` | `data` | 27 |  |  |
| `research-chat-store` | `data` | 72 | ✓ |  |
| `research-input` | `value` | 73 |  |  |
| `research-usage-store` | `data` | 74 | ✓ |  |
| `research-typing-indicator` | `style` | 75 |  |  |
| `research-send-btn` | `disabled` | 76 |  |  |
| `report-cache-store` | `data` | 77 | ✓ |  |
| `ai-pending-tasks-store` | `data` | 78 | ✓ |  |
| `research-typing-indicator` | `style` | 257 | ✓ |  |
| `research-send-btn` | `disabled` | 258 | ✓ |  |
| `research-chat-store` | `data` | 271 | ✓ |  |
| `ai-pending-tasks-store` | `data` | 272 | ✓ |  |
| `report-cache-store` | `data` | 273 | ✓ |  |
| `research-chat-display` | `children` | 338 |  |  |
| `research-ticker-store` | `data` | 389 |  |  |
| `research-portfolio-summary` | `children` | 400 |  |  |
| `research-usage-display` | `children` | 454 |  |  |
| `report-download` | `data` | 524 |  |  |
| `research-chat-display` | `id` | 550 |  |  |

## `settings_callbacks.py`

| Output ID | Property | Line | Duplicate? | Pattern? |
|-----------|----------|------|-----------|---------|
| `settings-investment-goal` | `value` | 43 |  |  |
| `settings-risk-tolerance` | `value` | 44 |  |  |
| `settings-tax-bracket` | `value` | 45 |  |  |
| `settings-weights-preview-container` | `children` | 63 |  |  |
| `settings-save-status` | `children` | 89 |  |  |

## `setup_callbacks.py`

| Output ID | Property | Line | Duplicate? | Pattern? |
|-----------|----------|------|-----------|---------|
| `dummy-redirect-output` | `children` | 116 |  |  |
| `setup-portfolio-table-body` | `children` | 123 |  |  |
| `setup-portfolio-rows-store` | `data` | 132 |  |  |
| `setup-portfolio-rows-store` | `data` | 146 | ✓ |  |
| `setup-portfolio-continue-btn` | `disabled` | 174 |  |  |
| `url` | `pathname` | 195 | ✓ |  |
| `setup-portfolio-feedback` | `children` | 196 |  |  |
| `txn-store` | `data` | 197 | ✓ |  |
| `url` | `pathname` | 252 | ✓ |  |
| `setup-ai-feedback` | `children` | 253 |  |  |
| `setup-ready-summary` | `children` | 304 |  |  |
| `url` | `pathname` | 346 | ✓ |  |
| `setup-is-first-run-store` | `data` | 347 | ✓ |  |
| `setup-ready-feedback` | `children` | 348 |  |  |

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
| `theme-toggle-hidden` | `children` | 41 |  |  |
| `pdf-btn-hidden` | `children` | 48 |  |  |
| `compact-mode-store` | `data` | 56 |  |  |
| `txn-collapse` | `opened` | 57 |  |  |
| `compact-toggle-btn` | `children` | 58 |  |  |
| `compact-toggle-btn` | `className` | 59 |  |  |
| `folio-table-state-v3` | `data` | 91 |  |  |
| `nav-link-store` | `data` | 155 |  |  |
| `pending-tasks-store` | `data` | 161 | ✓ |  |
| `palette-ticker-store` | `data` | 221 |  |  |

## `watchlist_callbacks.py`

| Output ID | Property | Line | Duplicate? | Pattern? |
|-----------|----------|------|-----------|---------|
| `watchlist-store` | `data` | 28 |  |  |
| `watchlist-input` | `value` | 29 |  |  |
| `watchlist-table-container` | `children` | 110 |  |  |
| `watchlist-msg` | `children` | 111 |  |  |
| `watchlist-selected-ticker` | `data` | 334 |  |  |
| `watchlist-selected-ticker` | `data` | 353 | ✓ |  |
| `watchlist-chart` | `figure` | 367 |  |  |
| `watchlist-chart-title` | `children` | 368 |  |  |
| `watchlist-period-store` | `data` | 460 |  |  |
| `{"type": "wl-period-btn", "index": ALL}` | `className` | 473 |  | ✓ |
| `watchlist-stat-cards` | `children` | 482 |  |  |
| `watchlist-tech-signals-container` | `children` | 483 |  |  |
| `watchlist-ai-insight-container` | `children` | 484 |  |  |
| `watchlist-notes-input` | `value` | 639 |  |  |
| `watchlist-notes-msg` | `children` | 649 |  |  |
| `watchlist-ticker-hint` | `children` | 663 |  |  |
