# Store Index — Auto-Generated

> **Generated**: 2026-06-27 14:57  
> **Do not edit** — run `python .agents/generated/sync_docs.py` to refresh.
> For exact JSON shapes and safe access patterns, see `docs/store_contracts.md`.

---

**Total stores**: 30  (all seeded in `app.py`)

| Store ID | Storage Type | Seeded at Line |
|----------|-------------|----------------|
| `signals-store` | `local` | 199 |
| `theme-store` | `local` | 201 |
| `watchlist-signals-store` | `local` | 200 |
| `ai-pending-tasks-store` | `session` | 216 |
| `analytics-period-store` | `session` | 225 |
| `benchmark-pending-store` | `session` | 219 |
| `intel-period-store` | `session` | 226 |
| `intel-pred-store` | `session` | 227 |
| `pending-tasks-store` | `session` | 215 |
| `period-store` | `session` | 221 |
| `pnl-mode-store` | `session` | 222 |
| `positions-period-store` | `session` | 229 |
| `positions-selected-ticker` | `session` | 228 |
| `ticker-store` | `session` | 223 |
| `treemap-mode-store` | `session` | 224 |
| `watchlist-period-store` | `session` | 231 |
| `watchlist-selected-ticker` | `session` | 230 |
| `alerts-store` | `memory` | 198 |
| `compact-mode-store` | `memory` | 202 |
| `folio-table-state-v3` | `memory` | 203 |
| `nav-link-store` | `memory` | 213 |
| `palette-ticker-store` | `memory` | 240 |
| `portfolio-store` | `memory` | 196 |
| `refresh-trigger-store` | `memory` | 214 |
| `research-chat-store` | `memory` | 232 |
| `research-ticker-store` | `memory` | 233 |
| `research-usage-store` | `memory` | 234 |
| `setup-is-first-run-store` | `memory` | 190 |
| `txn-store` | `memory` | 195 |
| `watchlist-store` | `memory` | 197 |

---

## Storage Type Reference

| Type | Persists across | Cleared by |
|------|----------------|-----------|
| `local` | Browser sessions, refreshes | Manual clear or new device |
| `session` | Page navigations within tab | Closing the tab |
| `memory` | Nothing (in-memory only) | Any page refresh |
| *(default)* | Nothing (same as memory) | Any page refresh |