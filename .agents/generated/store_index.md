# Store Index — Auto-Generated

> **Generated**: 2026-06-30 22:15  
> **Do not edit** — run `python .agents/generated/sync_docs.py` to refresh.
> For exact JSON shapes and safe access patterns, see `docs/reference/store_contracts.md`.

---

**Total stores**: 30  (all seeded in `app.py`)

| Store ID | Storage Type | Seeded at Line |
|----------|-------------|----------------|
| `research-usage-store` | `local` | 241 |
| `signals-store` | `local` | 206 |
| `theme-store` | `local` | 208 |
| `watchlist-signals-store` | `local` | 207 |
| `ai-pending-tasks-store` | `session` | 223 |
| `analytics-period-store` | `session` | 232 |
| `benchmark-pending-store` | `session` | 226 |
| `folio-table-state-v3` | `session` | 210 |
| `intel-period-store` | `session` | 233 |
| `intel-pred-store` | `session` | 234 |
| `pending-tasks-store` | `session` | 222 |
| `period-store` | `session` | 228 |
| `pnl-mode-store` | `session` | 229 |
| `positions-period-store` | `session` | 236 |
| `positions-selected-ticker` | `session` | 235 |
| `setup-is-first-run-store` | `session` | 197 |
| `ticker-store` | `session` | 230 |
| `treemap-mode-store` | `session` | 231 |
| `watchlist-period-store` | `session` | 238 |
| `watchlist-selected-ticker` | `session` | 237 |
| `alerts-store` | `memory` | 205 |
| `compact-mode-store` | `memory` | 209 |
| `nav-link-store` | `memory` | 220 |
| `palette-ticker-store` | `memory` | 247 |
| `portfolio-store` | `memory` | 203 |
| `refresh-trigger-store` | `memory` | 221 |
| `research-chat-store` | `memory` | 239 |
| `research-ticker-store` | `memory` | 240 |
| `txn-store` | `memory` | 202 |
| `watchlist-store` | `memory` | 204 |

---

## Storage Type Reference

| Type | Persists across | Cleared by |
|------|----------------|-----------|
| `local` | Browser sessions, refreshes | Manual clear or new device |
| `session` | Page navigations within tab | Closing the tab |
| `memory` | Nothing (in-memory only) | Any page refresh |
| *(default)* | Nothing (same as memory) | Any page refresh |