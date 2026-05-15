import dash
from dash import Input, Output, State, ALL, ctx
import logging
import json
from datetime import datetime
from data.database import get_connection, enqueue_task

logger = logging.getLogger(__name__)

def register_callbacks(app):

    # ── Global Intelligence Generation ───────────────────────────────────────
    @app.callback(
        Output("pending-tasks-store", "data", allow_duplicate=True),
        Output("global-signals-status-label", "children"),
        Input("global-generate-signals-btn", "n_clicks"),
        State("portfolio-store", "data"),
        State("watchlist-store", "data"),
        State("signals-store", "data"),
        State("watchlist-signals-store", "data"),
        State("pending-tasks-store", "data"),
        prevent_initial_call=True
    )
    def trigger_global_intelligence(n, port_data, watch_data, port_signals, watch_signals, pending):
        if not n: return dash.no_update, dash.no_update
        
        new_pending = (pending or [])
        triggered_any = False
        today_str = datetime.now().strftime('%Y-%m-%d')
        
        from data.repository import PortfolioRepository
        from data.watchlist_repository import WatchlistRepository
        from core.engine import build_holdings

        # 1. Check Portfolio
        p_repo = PortfolioRepository()
        p_holdings = build_holdings(p_repo.load_transactions())
        p_tickers = [h["ticker"] for h in p_holdings]
        p_needs_update = True
        if p_tickers and port_signals and port_signals.get("generated_at"):
            if port_signals["generated_at"].startswith(today_str):
                cached = port_signals.get("raw", {}).keys()
                if all(t in cached for t in p_tickers):
                    p_needs_update = False
        
        if p_tickers and p_needs_update:
            task_id = enqueue_task("generate_signals", {"tickers": p_tickers, "scope": "portfolio"}, priority=3)
            new_pending.append({"id": task_id, "type": "signals", "scope": "portfolio"})
            triggered_any = True

        # 2. Check Watchlist
        w_repo = WatchlistRepository()
        w_items = w_repo.load_watchlist()
        w_tickers = [item["ticker"] for item in w_items]
        w_needs_update = True
        if w_tickers and watch_signals and watch_signals.get("generated_at"):
            if watch_signals["generated_at"].startswith(today_str):
                cached = watch_signals.get("raw", {}).keys()
                if all(t in cached for t in w_tickers):
                    w_needs_update = False
        
        if w_tickers and w_needs_update:
            task_id = enqueue_task("generate_signals", {"tickers": w_tickers, "scope": "watchlist"}, priority=3)
            new_pending.append({"id": task_id, "type": "watchlist_signals", "scope": "watchlist"})
            triggered_any = True

        if not triggered_any:
            return dash.no_update, "Already Up to Date"
            
        return new_pending, "Updating Intelligence..."

    # ── Task Polling & Result Processing (Global Stores) ────────────────────
    @app.callback(
        Output("signals-store", "data"),
        Output("watchlist-signals-store", "data"),
        Output("pending-tasks-store", "data", allow_duplicate=True),
        Input("task-poll-interval", "n_intervals"),
        State("pending-tasks-store", "data"),
        State("portfolio-store", "data"),
        State("watchlist-store", "data"),
        prevent_initial_call=True
    )
    def poll_tasks_and_update_stores(n, pending, port_data, watch_data):
        if not pending:
            return dash.no_update, dash.no_update, []
            
        conn = get_connection()
        try:
            still_pending = []
            updates_needed = {"signals": False, "watchlist_signals": False}
            
            for task in pending:
                task_id = task["id"]
                row = conn.execute("SELECT status FROM worker_tasks WHERE task_id = ?", (task_id,)).fetchone()
                
                if row:
                    if row["status"] == "complete":
                        updates_needed[task["type"]] = True
                    elif row["status"] == "failed":
                        # We still remove it from pending even if it failed
                        pass
                    else:
                        still_pending.append(task)
                else:
                    # Task not found (pruned or orphaned)
                    pass
            
            out_signals = dash.no_update
            out_watch = dash.no_update
            
            if updates_needed["signals"]:
                from data.repository import PortfolioRepository
                from core.engine import build_holdings
                p_repo = PortfolioRepository()
                p_holdings = build_holdings(p_repo.load_transactions())
                tickers = [h["ticker"] for h in p_holdings]
                out_signals = _load_signal_results(tickers, table="signal_results")

            if updates_needed["watchlist_signals"]:
                from data.watchlist_repository import WatchlistRepository
                w_repo = WatchlistRepository()
                w_items = w_repo.load_watchlist()
                tickers = [item["ticker"] for item in w_items]
                out_watch = _load_signal_results(tickers, table="watchlist_signal_results")
            
            return out_signals, out_watch, still_pending
            
        finally:
            conn.close()

    # ── Global Status UI ─────────────────────────────────────────────────────
    @app.callback(
        Output("global-signals-status-label", "children", allow_duplicate=True),
        Output("signals-updated-chip", "style"),
        Input("pending-tasks-store", "data"),
        Input("signals-store", "data"),
        Input("watchlist-signals-store", "data"),
        prevent_initial_call='initial_duplicate'
    )
    def update_global_status(pending, signals, w_signals):
        chip_style = {"display": "flex", "marginLeft": "4px", "padding": "2px 8px", "border": "0.5px solid rgba(0, 255, 255, 0.15)", "gap": "6px", "alignItems": "center"}
        
        # If any signals task is pending
        is_pending = any(t["type"] in ("signals", "watchlist_signals") for t in (pending or []))
        if is_pending:
            return "Updating Intelligence...", chip_style
        
        # Use the latest generated_at from either store
        t1 = signals.get("generated_at") if signals else None
        t2 = w_signals.get("generated_at") if w_signals else None
        
        latest = t1
        if t2:
            if not t1 or t2 > t1:
                latest = t2
            
        if latest:
            try:
                dt = datetime.fromisoformat(latest)
                return f"Updated {dt.strftime('%H:%M')}", chip_style
            except:
                return f"Updated {latest[:10]}", chip_style
            
        return "", chip_style

def _load_signal_results(tickers: list[str], table: str = "signal_results") -> dict:
    """Helper to read signal_results from SQLite and format for dcc.Store."""
    if not tickers:
        return {"raw": {}, "ai": {}}
        
    conn = get_connection()
    try:
        placeholders = ",".join(["?"] * len(tickers))
        cursor = conn.execute(f"SELECT * FROM {table} WHERE ticker IN ({placeholders})", [t.upper() for t in tickers])
        rows = cursor.fetchall()
        
        raw = {}
        ai = {}
        gen_at = None
        for r in rows:
            ticker = r["ticker"]
            if not gen_at: gen_at = r["generated_at"]
            raw[ticker] = {
                "ticker": ticker,
                "signal": r["signal"],
                "score": r["score"],
                "confidence": r["confidence"],
                "reasons": json.loads(r["reasons"]) if r["reasons"] else [],
                "indicators": json.loads(r["indicators"]) if r["indicators"] else {},
                "hysteresis_forced": bool(r["hysteresis_forced"])
            }
            # AI Insight parsing
            ai_val = r["ai_explanation"]
            if ai_val:
                try:
                    ai[ticker] = json.loads(ai_val)
                except:
                    # Fallback for legacy plain text or malformed JSON
                    ai[ticker] = {"explanation": ai_val, "verdict": "Mixed", "risks": []}
            else:
                ai[ticker] = {}
            
        return {"raw": raw, "ai": ai, "generated_at": gen_at}
    finally:
        conn.close()
