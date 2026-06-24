# Store Index — Auto-Generated

> **Generated**: 2026-06-24 18:48  
> **Do not edit** — run `python .agents/generated/sync_docs.py` to refresh.
> For exact JSON shapes and safe access patterns, see `docs/store_contracts.md`.

---

**Total stores**: 30  (all seeded in `app.py`)

| Store ID | Storage Type | Seeded at Line |
|----------|-------------|----------------|
| `signals-store` | `local` | 198 |
| `theme-store` | `local` | 200 |
| `watchlist-signals-store` | `local` | 199 |
| `ai-pending-tasks-store` | `session` | 215 |
| `analytics-period-store` | `session` | 224 |
| `benchmark-pending-store` | `session` | 218 |
| `intel-period-store` | `session` | 225 |
| `intel-pred-store` | `session` | 226 |
| `pending-tasks-store` | `session` | 214 |
| `period-store` | `session` | 220 |
| `pnl-mode-store` | `session` | 221 |
| `positions-period-store` | `session` | 228 |
| `positions-selected-ticker` | `session` | 227 |
| `ticker-store` | `session` | 222 |
| `treemap-mode-store` | `session` | 223 |
| `watchlist-period-store` | `session` | 230 |
| `watchlist-selected-ticker` | `session` | 229 |
| `alerts-store` | `memory` | 197 |
| `compact-mode-store` | `memory` | 201 |
| `folio-table-state-v3` | `memory` | 202 |
| `nav-link-store` | `memory` | 212 |
| `palette-ticker-store` | `memory` | 239 |
| `portfolio-store` | `memory` | 195 |
| `refresh-trigger-store` | `memory` | 213 |
| `research-chat-store` | `memory` | 231 |
| `research-ticker-store` | `memory` | 232 |
| `research-usage-store` | `memory` | 233 |
| `setup-is-first-run-store` | `memory` | 189 |
| `txn-store` | `memory` | 194 |
| `watchlist-store` | `memory` | 196 |

---

## Storage Type Reference

| Type | Persists across | Cleared by |
|------|----------------|-----------|
| `local` | Browser sessions, refreshes | Manual clear or new device |
| `session` | Page navigations within tab | Closing the tab |
| `memory` | Nothing (in-memory only) | Any page refresh |
| *(default)* | Nothing (same as memory) | Any page refresh |