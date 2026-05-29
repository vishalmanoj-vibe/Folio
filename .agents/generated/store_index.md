# Store Index — Auto-Generated

> **Generated**: 2026-05-29 13:34  
> **Do not edit** — run `python .agents/generated/sync_docs.py` to refresh.
> For exact JSON shapes and safe access patterns, see `docs/store_contracts.md`.

---

**Total stores**: 29  (all seeded in `app.py`)

| Store ID | Storage Type | Seeded at Line |
|----------|-------------|----------------|
| `signals-store` | `local` | 193 |
| `theme-store` | `local` | 195 |
| `watchlist-signals-store` | `local` | 194 |
| `ai-pending-tasks-store` | `session` | 210 |
| `analytics-period-store` | `session` | 219 |
| `benchmark-pending-store` | `session` | 213 |
| `intel-period-store` | `session` | 220 |
| `intel-pred-store` | `session` | 221 |
| `pending-tasks-store` | `session` | 209 |
| `period-store` | `session` | 215 |
| `pnl-mode-store` | `session` | 216 |
| `positions-period-store` | `session` | 223 |
| `positions-selected-ticker` | `session` | 222 |
| `ticker-store` | `session` | 217 |
| `treemap-mode-store` | `session` | 218 |
| `watchlist-period-store` | `session` | 225 |
| `watchlist-selected-ticker` | `session` | 224 |
| `alerts-store` | `memory` | 192 |
| `compact-mode-store` | `memory` | 196 |
| `folio-table-state-v3` | `memory` | 197 |
| `nav-link-store` | `memory` | 207 |
| `portfolio-store` | `memory` | 190 |
| `refresh-trigger-store` | `memory` | 208 |
| `research-chat-store` | `memory` | 226 |
| `research-ticker-store` | `memory` | 227 |
| `research-usage-store` | `memory` | 228 |
| `setup-is-first-run-store` | `memory` | 184 |
| `txn-store` | `memory` | 189 |
| `watchlist-store` | `memory` | 191 |

---

## Storage Type Reference

| Type | Persists across | Cleared by |
|------|----------------|-----------|
| `local` | Browser sessions, refreshes | Manual clear or new device |
| `session` | Page navigations within tab | Closing the tab |
| `memory` | Nothing (in-memory only) | Any page refresh |
| *(default)* | Nothing (same as memory) | Any page refresh |