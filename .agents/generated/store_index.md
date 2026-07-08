# Store Index — Auto-Generated

> **Generated**: 2026-07-08 23:26  
> **Do not edit** — run `python .agents/generated/sync_docs.py` to refresh.
> For exact JSON shapes and safe access patterns, see `docs/reference/store_contracts.md`.

---

**Total stores**: 30  (all seeded in `app.py`)

| Store ID | Storage Type | Seeded at Line |
|----------|-------------|----------------|
| `research-usage-store` | `local` | 242 |
| `signals-store` | `local` | 207 |
| `theme-store` | `local` | 209 |
| `watchlist-signals-store` | `local` | 208 |
| `ai-pending-tasks-store` | `session` | 224 |
| `analytics-period-store` | `session` | 233 |
| `benchmark-pending-store` | `session` | 227 |
| `folio-table-state-v3` | `session` | 211 |
| `intel-period-store` | `session` | 234 |
| `intel-pred-store` | `session` | 235 |
| `pending-tasks-store` | `session` | 223 |
| `period-store` | `session` | 229 |
| `pnl-mode-store` | `session` | 230 |
| `positions-period-store` | `session` | 237 |
| `positions-selected-ticker` | `session` | 236 |
| `setup-is-first-run-store` | `session` | 198 |
| `ticker-store` | `session` | 231 |
| `treemap-mode-store` | `session` | 232 |
| `watchlist-period-store` | `session` | 239 |
| `watchlist-selected-ticker` | `session` | 238 |
| `alerts-store` | `memory` | 206 |
| `compact-mode-store` | `memory` | 210 |
| `nav-link-store` | `memory` | 221 |
| `palette-ticker-store` | `memory` | 248 |
| `portfolio-store` | `memory` | 204 |
| `refresh-trigger-store` | `memory` | 222 |
| `research-chat-store` | `memory` | 240 |
| `research-ticker-store` | `memory` | 241 |
| `txn-store` | `memory` | 203 |
| `watchlist-store` | `memory` | 205 |

---

## Storage Type Reference

| Type | Persists across | Cleared by |
|------|----------------|-----------|
| `local` | Browser sessions, refreshes | Manual clear or new device |
| `session` | Page navigations within tab | Closing the tab |
| `memory` | Nothing (in-memory only) | Any page refresh |
| *(default)* | Nothing (same as memory) | Any page refresh |