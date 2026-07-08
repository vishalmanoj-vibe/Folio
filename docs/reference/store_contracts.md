# Store Contracts — Folio

---
Related: [`GEMINI.md`](../../GEMINI.md) | [`project_map.md`](../../.agents/project_map.md) | [`store_index.md`](../../.agents/generated/store_index.md)
---

> **Purpose**: Prevent silent callback failures by documenting the exact JSON
> shape of every major `dcc.Store`. Treat these as immutable contracts.
> If a store's shape must change, update this document AND all consuming callbacks.

---

## `portfolio-store`

**Storage type**: default (memory, cleared on refresh)  
**Single owner (writer)**: `update_portfolio_store()` in [`app.py`](../../app.py)  
**Seeded by**: `load_portfolio_snapshot()` at startup

```json
{
  "holdings": [
    {
      "ticker": "CBA",
      "ticker_yf": "CBA.AX",
      "total_shares": 10.0,
      "avg_cost": 95.00,
      "total_cost": 950.00,
      "sector": "Financials",
      "last_price": 102.50,
      "day_change_pct": 0.35,
      "day_change_abs": 0.36,
      "mkt_value": 1025.00,
      "unrealised_pnl": 75.00,
      "unrealised_pnl_pct": 7.89,
      "week_52_high": 115.00,
      "week_52_low": 88.00,
      "div_yield": 4.2,
      "fetched_at": "14:32:01"
    }
  ],
  "fetched_at": "14:32:01"
}
```

### ❌ NEVER put in `portfolio-store`
- Historical price arrays (e.g. `history`, `prices`, `ohlc`)
- `buy_tranches` lists
- Any list or array longer than ~50 items

---

## `txn-store`

**Storage type**: default (memory)  
**Single owner (writer)**: `update_txn_store()` in [`app.py`](../../app.py)  
**Seeded by**: `repo.load_transactions()` at startup

```json
[
  {
    "type": "buy",
    "ticker": "CBA",
    "shares": 10.0,
    "price": 95.00,
    "date": "2024-01-15"
  }
]
```

> `type` is always lowercase: `"buy"` or `"sell"`.  
> `ticker` is always UPPERCASE, never has `.AX` suffix.

---

## `watchlist-store`

**Storage type**: default (memory)  
**Single owner (writer)**: `update_watchlist_store()` in `watchlist_callbacks.py`  
**Seeded by**: `INITIAL_WATCHLIST_DATA` at startup

```json
{
  "holdings": [
    {
      "ticker": "WES",
      "last_price": 72.50
    }
  ],
  "fetched_at": "14:32:01"
}
```

> The startup seed is intentionally minimal. The `watchlist_callbacks.py`
> populates this with full price data after the `startup-interval` fires.

---

## `signals-store`

**Storage type**: `local` (survives browser refresh)  
**Single owner (writer)**: `generate_signals_callback()` in `signals_callbacks.py`  
**Triggered by**: `generate-signals-btn` on Positions page (manual only)

```json
{
  "raw": {
    "CBA": {
      "ticker": "CBA",
      "score": 0.62,
      "signal": "BUY",
      "reasons": ["RSI < 40", "MACD bullish crossover"],
      "rsi": 38.5,
      "macd": 0.12,
      "macd_signal": 0.08,
      "bb_label": "NEUTRAL",
      "hysteresis_forced": false
    }
  },
  "ai": {
    "CBA": {
      "verdict": "Confident",
      "explanation": "Strong momentum with healthy fundamentals.",
      "risks": "Watch for RBA rate decisions.",
      "tone": "bullish"
    }
  }
}
```

### Rules
- Access with `.get("raw", {})` and `.get("ai", {})` — never assume keys exist.
- `signal` is always one of: `"BUY"`, `"SELL"`, `"HOLD"`.
- `ai` dict may be empty `{}` if AI was skipped (score < 0.4 threshold).
- `hysteresis_forced: bool` is ALWAYS present on raw signals.

---

## `watchlist-signals-store`

**Storage type**: `local`  
**Single owner (writer)**: `generate_watchlist_signals_callback()` in `signals_callbacks.py`  
**Triggered by**: `watchlist-generate-signals-btn` on Watchlist page (manual only)

> Identical shape to `signals-store`. The `raw` entries use synthetic holding
> dicts (`avg_cost=0`, `buy_tranches=[]`) — cost-dimension scoring is skipped
> and no CGT warnings are emitted.

---

## `pending-tasks-store`

**Storage type**: `session`  
**Writers**: [`callbacks/signals_callbacks.py`](../../callbacks/signals_callbacks.py), [`app.py`](../../app.py)

```json
[
  {"id": "task-uuid-abc", "type": "refresh_portfolio"}
]
```

---

## `research-usage-store`

**Storage type**: `local`

```json
{
  "count": 3,
  "reset_date": "2024-06-01"
}
```

---

## `research-chat-store`

**Storage type**: `memory` (clears on refresh)  
**Single owner (writer)**: `research_callbacks.py` (welcome message, send prompt, and task listener callbacks)  

```json
[
  {
    "role": "assistant",
    "content": "Hi! I've loaded your portfolio..."
  },
  {
    "role": "user",
    "content": "Does VAS fit my portfolio?"
  },
  {
    "role": "assistant",
    "content": "VAS represents ASX 300, which aligns with...",
    "type": "web-search-used"
  }
]
```

### Rules
- `role` is either `"user"` or `"assistant"`.
- `content` holds the text content.
- Optional `"type"` key specifies special rendering variants: `"thinking"`, `"web-search-used"`, or `"report-ready"`.

---

## `research-ticker-store`

**Storage type**: `memory` (clears on refresh)  
**Single owner (writer)**: `update_chatbot_context()` in `research_callbacks.py`  

Stores the ticker string currently typed into the chatbot research input box (e.g. `"VAS"`), or `""` if no explicit ticker research override is set.

---

## `folio-table-state-v3`

**Storage type**: `session`

```json
{
  "search": "",
  "sort_col": "ticker",
  "sort_dir": "asc"
}
```

---

## Quick Reference — Access Patterns

```python
# ✅ Safe access — always use .get() with defaults
holdings = (portfolio_data or {}).get("holdings", [])
raw_signals = (signals_data or {}).get("raw", {})
ai_signals  = (signals_data or {}).get("ai", {})

# ❌ Unsafe — will KeyError if store is empty or None
holdings = portfolio_data["holdings"]
```
