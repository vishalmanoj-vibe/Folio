# Store Index — Auto-Generated

> **Generated**: 2026-06-04 23:49  
> **Do not edit** — run `python .agents/generated/sync_docs.py` to refresh.
> For exact JSON shapes and safe access patterns, see `docs/store_contracts.md`.

---

**Total stores**: 30  (all seeded in `app.py`)

| Store ID | Storage Type | Seeded at Line |
|----------|-------------|----------------|
| `signals-store` | `local` | 194 |
| `theme-store` | `local` | 196 |
| `watchlist-signals-store` | `local` | 195 |
| `ai-pending-tasks-store` | `session` | 211 |
| `analytics-period-store` | `session` | 220 |
| `benchmark-pending-store` | `session` | 214 |
| `intel-period-store` | `session` | 221 |
| `intel-pred-store` | `session` | 222 |
| `pending-tasks-store` | `session` | 210 |
| `period-store` | `session` | 216 |
| `pnl-mode-store` | `session` | 217 |
| `positions-period-store` | `session` | 224 |
| `positions-selected-ticker` | `session` | 223 |
| `ticker-store` | `session` | 218 |
| `treemap-mode-store` | `session` | 219 |
| `watchlist-period-store` | `session` | 226 |
| `watchlist-selected-ticker` | `session` | 225 |
| `alerts-store` | `memory` | 193 |
| `compact-mode-store` | `memory` | 197 |
| `folio-table-state-v3` | `memory` | 198 |
| `nav-link-store` | `memory` | 208 |
| `palette-ticker-store` | `memory` | 235 |
| `portfolio-store` | `memory` | 191 |
| `refresh-trigger-store` | `memory` | 209 |
| `research-chat-store` | `memory` | 227 |
| `research-ticker-store` | `memory` | 228 |
| `research-usage-store` | `memory` | 229 |
| `setup-is-first-run-store` | `memory` | 185 |
| `txn-store` | `memory` | 190 |
| `watchlist-store` | `memory` | 192 |

---

## Storage Type Reference

| Type | Persists across | Cleared by |
|------|----------------|-----------|
| `local` | Browser sessions, refreshes | Manual clear or new device |
| `session` | Page navigations within tab | Closing the tab |
| `memory` | Nothing (in-memory only) | Any page refresh |
| *(default)* | Nothing (same as memory) | Any page refresh |