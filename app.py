# app.py
"""
Folio — modular entry point
==========================================
Run:   python app.py
Open:  http://127.0.0.1:8050

Pages
-----
  /               → pages/portfolio.py
  /positions      → pages/positions.py
  /analytics      → pages/analytics.py
  /intelligence   → pages/intelligence.py
  /ai-analyst     → pages/ai_analyst.py

Responsiveness fix (Instant Load + Background Refresh)
--------------------------------------------------
To ensure a premium "Day 1" experience, the server does NOT perform blocking 
yfinance fetches on startup. Instead:
1. Stores (portfolio-store, txn-store, watchlist-store) are seeded with 
   persistent disk snapshots (load_portfolio_snapshot).
2. The UI paints immediately (under 1s) with cached data.
3. A 'startup-interval' fires 1.5s after load to trigger the first live fetch.
4. Background threads maintain snapshots during market hours.
"""

# Setup logging first
from config.logging import setup_logging
setup_logging()

import logging
logger = logging.getLogger(__name__)

import os
import sys
from dotenv import load_dotenv
load_dotenv()

# Darwin Keychain / Database key loading
if not os.environ.get("GEMINI_API_KEY"):
    try:
        from data.repository import PortfolioRepository
        db_key = PortfolioRepository().get_gemini_api_key()
        if db_key:
            os.environ["GEMINI_API_KEY"] = db_key
            logger.info("Successfully loaded GEMINI_API_KEY from database metadata.")
    except Exception as e:
        logger.debug(f"Could not load GEMINI_API_KEY from database: {e}")

import dash
from dash import html, dcc, Input, Output, State, ALL, ctx
import webbrowser
import threading
import os
import sys
import signal
import time
from datetime import datetime

from components.portfolio_layout import INDEX_STRING
from data.repository import PortfolioRepository
from core.validators import validate_transaction
from config.settings import REFRESH_INTERVAL
from data.watchlist_repository import WatchlistRepository
from services.market.market_status import is_market_open

# Callback modules
import callbacks.portfolio_callbacks      as portfolio
import callbacks.transaction_callbacks    as txn
import callbacks.chart_callbacks          as charts
import callbacks.alert_callbacks          as alerts
import callbacks.ui_callbacks             as ui
import callbacks.intelligence_callbacks   as intell_cb
import callbacks.positions_callbacks      as positions_cb
import callbacks.watchlist_callbacks      as watchlist_cb
import callbacks.research_callbacks  as research_cb
import callbacks.signals_callbacks        as signals_cb
import callbacks.setup_callbacks           as setup_cb

# ── Initial data load ─────────────────────────────────────────────────────────
repo = PortfolioRepository()

try:
    INITIAL_HISTORY: list[dict] = repo.load_transactions()
    logger.info(f"Loaded {len(INITIAL_HISTORY)} transactions from storage")
except Exception as e:
    logger.error(f"Failed to load initial storage: {e}")
    INITIAL_HISTORY = []
    logger.error(f"\nERROR loading database:\n{e}\n")

from core.engine import build_holdings
from services.market.data_fetcher import load_portfolio_snapshot
from services.market.session_cache import clear_old_caches
from services.history_cache import set_histories
# Maintenance is now deferred to worker tasks
INITIAL_HOLDINGS = build_holdings(INITIAL_HISTORY, include_tranches=False)
INITIAL_PORTFOLIO_DATA: dict = load_portfolio_snapshot(INITIAL_HOLDINGS)
logger.info("Fast-loaded portfolio from disk snapshot (SQLite).")

# ── Initial watchlist load ───────────────────────────────────────────────────
watchlist_repo = WatchlistRepository()
INITIAL_WATCHLIST = watchlist_repo.load_watchlist()
INITIAL_WATCHLIST_DATA = {}

if INITIAL_WATCHLIST:
    try:
        watchlist_holdings = [
            {"ticker": i["ticker"], "ticker_yf": i["ticker"] + ".AX", "total_shares": 0, "avg_cost": 0, "total_cost": 0, "buy_tranches": []}
            for i in INITIAL_WATCHLIST
        ]
        # Fast load from disk cache - zero network calls
        from data.repository import HistoryRepository
        h_repo = HistoryRepository()
        disk_histories = {}
        for item in INITIAL_WATCHLIST:
            ticker = item["ticker"]
            cached = h_repo.load_history(ticker)
            if cached:
                disk_histories[ticker] = cached

        # Initialize with disk data; the background interval will populate live prices
        INITIAL_WATCHLIST_DATA = {
            "holdings": [{"ticker": h["ticker"], "last_price": 0.0} for h in watchlist_holdings],
            "fetched_at": "Loading..."
        }
        if disk_histories:
            set_histories("startup_watchlist", disk_histories)
        
        # Heavy bulk refresh removed from global scope to save memory.
        # It will be triggered by the startup-interval via task queue.
        logger.info(f"Watchlist seeded from cache ({len(disk_histories)} tickers)")
    except Exception as e:
        logger.warning(f"Initial watchlist fetch failed: {e}")
        INITIAL_WATCHLIST_DATA = {"holdings": [], "fetched_at": "Error"}

# Note: Weekly report is now manually generated via the Reports page.

import dash_bootstrap_components as dbc

# ── Dash App ──────────────────────────────────────────────────────────────────
app = dash.Dash(
    __name__,
    use_pages=True,
    pages_folder="pages",
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
)

# Register onboarding wizard callbacks
setup_cb.register_setup_callbacks(app)

app.title = "Folio — Live"
app.index_string = INDEX_STRING

# Pages are loaded automatically via use_pages=True

import dash_mantine_components as dmc

from components.header import create_header

# ── Root Layout ───────────────────────────────────────────────────────────────
app.layout = dmc.MantineProvider(
    forceColorScheme="dark",
    theme={
        "fontFamily": "Inter, sans-serif",
    },
    children=html.Div(
        [
            dcc.Location(id="url", refresh=False),
            dcc.Store(id="setup-is-first-run-store", data=(not repo.is_onboarding_completed()), storage_type="session"),
            dcc.Store(id="txn-store",       data=INITIAL_HISTORY),
            dcc.Store(id="portfolio-store",     data=INITIAL_PORTFOLIO_DATA),
            dcc.Store(id="watchlist-store",     data=INITIAL_WATCHLIST_DATA),
            dcc.Store(id="alerts-store"),
            dcc.Store(id="signals-store",           data={}, storage_type="local"),
            dcc.Store(id="watchlist-signals-store", data={}, storage_type="local"),
            dcc.Store(id="theme-store",          data="dark", storage_type='local'),
            dcc.Store(id="compact-mode-store",   data=True),
            dcc.Store(id="folio-table-state-v3",   data={"search": "", "sort_col": "ticker", "sort_dir": "asc"}, storage_type='session'),
            dcc.Interval(id="live-interval", interval=30000, n_intervals=0),
            dcc.Interval(id="heartbeat-interval", interval=30000, n_intervals=0),
            dcc.Interval(id="price-interval", interval=300000, n_intervals=0),
            dcc.Interval(id="startup-interval", interval=1500, n_intervals=0, max_intervals=1),
            dcc.Interval(id="task-poll-interval", interval=2000, n_intervals=0, disabled=True),
            dcc.Store(id="nav-link-store"),
            dcc.Store(id="refresh-trigger-store", data=0),
            dcc.Store(id="pending-tasks-store", data=[], storage_type="session"),
            dcc.Store(id="ai-pending-tasks-store", data={}, storage_type="session"), # {task_id: message_index}
            dcc.Store(id="benchmark-pending-store", data=None, storage_type="session"), # task_id

            # ── Picker Stores (Session persistence) ────────────────────────────────
            dcc.Store(id="period-store",           data="max",    storage_type='session'),
            dcc.Store(id="pnl-mode-store",         data="pct",  storage_type='session'),
            dcc.Store(id="ticker-store",           data="Portfolio", storage_type='session'),
            dcc.Store(id="treemap-mode-store",     data="sector", storage_type='session'),
            dcc.Store(id="analytics-period-store", data="1mo",    storage_type='session'),
            dcc.Store(id="intel-period-store",     data="3mo",    storage_type='session'),
            dcc.Store(id="intel-pred-store",       data=False,    storage_type='session'),
            dcc.Store(id="positions-selected-ticker", data=None, storage_type='session'),
            dcc.Store(id="positions-period-store", data="3mo", storage_type='session'),
            dcc.Store(id="watchlist-selected-ticker", data=None, storage_type='session'),
            dcc.Store(id="watchlist-period-store", data="1y", storage_type='session'),
            dcc.Store(id="research-chat-store", data=[], 
                      storage_type="memory"),
            dcc.Store(id="research-ticker-store", data="", 
                      storage_type="memory"),
            dcc.Store(
                id="research-usage-store",
                data={"count": 0, "reset_date": ""},
                storage_type="local",
            ),
            
            # Global Navigation
            create_header(),
            
            # Page Content with Loading Indicator
            dash.page_container,
            
            # Dummy target for clientside redirect guards
            html.Div(id="dummy-redirect-output", style={"display": "none"}),
        ],
        className="app-container",
    )
)



# Note: _perform_refresh and direct fetch_live calls have been moved to worker.py.

# ── SINGLE OWNER: txn-store ───────────────────────────────────────────────────
@app.callback(
    Output("txn-store", "data", allow_duplicate=True),
    Input("startup-interval",      "n_intervals"),
    Input("txn-submit",           "n_clicks"),
    State("txn-type",             "value"),
    State("txn-ticker", "value"),
    State("txn-shares", "value"),
    State("txn-price", "value"),
    State("txn-date", "value"),
    State("txn-store", "data"),
    prevent_initial_call=True,
)
def update_txn_store(n_startup, n_submit, t_type, ticker, shares, price, date_str, history):
    """Only place where txn-store is updated. Handles interval sync and new additions."""
    if ctx.triggered_id == "txn-submit":
        if not all([t_type, ticker, shares is not None, price is not None, date_str]):
            return dash.no_update
        # Format date for CSV
        d_val = date_str.strftime("%Y-%m-%d") if hasattr(date_str, 'strftime') else str(date_str).strip()
        new_txn = {
            "type": str(t_type).lower(),
            "ticker": str(ticker).upper(),
            "shares": float(shares),
            "price": float(price),
            "date": d_val,
        }
        valid, _ = validate_transaction(new_txn)
        if valid:
            updated = repo.append_transaction(new_txn)
            
            from core import _cache
            # Clear all market data caches to force fresh fetch across all periods
            keys_to_clear = [k for k in _cache.keys() if k.startswith("market_data_")]
            for k in keys_to_clear:
                _cache.pop(k, None)

            # CRITICAL: Also clear market_prices SQLite entry for the affected ticker.
            # get_live_prices() checks SQLite freshness, not just in-memory cache.
            # Without this, it returns stale mkt_value/pnl calculated against the
            # OLD share count, so portfolio-store gets wrong data and other pages don't update.
            try:
                from data.database import get_connection
                _conn = get_connection()
                try:
                    _conn.execute("DELETE FROM market_prices WHERE ticker = ?", (new_txn["ticker"],))
                    _conn.commit()
                finally:
                    _conn.close()
            except Exception as _e:
                logger.warning(f"Could not clear market_prices for {new_txn['ticker']}: {_e}")

            # Enqueue a background task to refresh live prices immediately
            from data.database import enqueue_task
            enqueue_task("refresh_portfolio", priority=1)
                
            return updated
        return dash.no_update
    
    # Otherwise periodic/manual sync from storage
    return repo.load_transactions()


# ── SINGLE OWNER: portfolio-store ─────────────────────────────────────────────
@app.callback(
    Output("portfolio-store", "data", allow_duplicate=True),
    Input("txn-store",              "data"),
    Input("period-store",           "data"),
    Input("analytics-period-store", "data"),
    Input("positions-period-store", "data"),
    Input("intel-period-store",     "data"),
    Input("watchlist-period-store", "data"),
    Input("price-interval",         "n_intervals"),
    Input("startup-interval",       "n_intervals"),
    Input("refresh-trigger-store",  "data"),
    State("url", "pathname"),
    prevent_initial_call=True,
)
def update_portfolio_store(txn_data, p1, p2, p3, p4, p5, n_price, n_start, n_trigger, pathname):
    """
    Consumer only: Reads enriched portfolio data from the market_prices SQLite table.
    The worker process is responsible for updating market_prices.
    """
    if pathname and pathname.startswith("/setup"):
        logger.info("Onboarding in progress: skipping portfolio live price updates.")
        return dash.no_update

    from data.cache_manager import get_live_prices
    
    # 1. Get tickers from current txn-store
    holdings = build_holdings(txn_data, include_tranches=False)
    tickers = [h["ticker"] for h in holdings]
    
    if not tickers:
        return {"holdings": [], "fetched_at": datetime.now().strftime("%H:%M:%S")}

    try:
        # 2. Read from SQLite (Centralized cache)
        # get_live_prices is now the single source of truth for the Dash process
        prices = get_live_prices(tickers)
        
        # Merge holdings with live price metrics
        enriched = []
        for h in holdings:
            p = prices.get(h["ticker"], {})
            enriched.append({**h, **p})
            
        fetched_at = "Unknown"
        if enriched and "fetched_at" in enriched[0]:
            fetched_at = enriched[0]["fetched_at"]
            # Convert ISO to readable time
            try:
                if "T" in str(fetched_at):
                    dt = datetime.fromisoformat(str(fetched_at))
                    fetched_at = dt.strftime("%H:%M:%S")
                else:
                    fetched_at = str(fetched_at)[:8] # Already formatted or truncated
            except:
                pass

        res = {
            "holdings": enriched,
            "fetched_at": fetched_at
        }
        # Final cleanup
        import gc
        gc.collect()
        return res
    except Exception as e:
        logger.error(f"Portfolio store update failed: {e}")
        return dash.no_update

# ── Global Picker Syncing (UI -> Store) ──────────────────────────────────────
# These callbacks ensure that user interactions with UI components are persisted
# to global stores, which then drive the data fetching engine.
@app.callback(Output("period-store", "data"), Input("period-picker", "value"), State("period-store", "data"), prevent_initial_call=True)
def sync_p1(v, current): return v if v and v != current else dash.no_update

@app.callback(Output("pnl-mode-store", "data"), Input("pnl-mode", "value"), State("pnl-mode-store", "data"), prevent_initial_call=True)
def sync_mode(v, current): return v if v and v != current else dash.no_update

@app.callback(Output("ticker-store", "data"), Input("ticker-selector", "value"), State("ticker-store", "data"), prevent_initial_call=True)
def sync_tk(v, current): return v if v and v != current else dash.no_update

@app.callback(Output("treemap-mode-store", "data"), Input("treemap-mode", "value"), State("treemap-mode-store", "data"), prevent_initial_call=True)
def sync_tree(v, current): return v if v and v != current else dash.no_update

@app.callback(Output("analytics-period-store", "data"), Input("analytics-period-picker", "value"), State("analytics-period-store", "data"), prevent_initial_call=True)
def sync_p2(v, current): return v if v and v != current else dash.no_update

@app.callback(Output("intel-period-store", "data"), Input("intel-period-picker", "value"), State("intel-period-store", "data"), prevent_initial_call=True)
def sync_p3(v, current): return v if v and v != current else dash.no_update

# ── Initialization Syncing (Store -> UI on load) ──────────────────────────────
# We use Clientside Callbacks to break circular dependencies.
# This ensures that when a page is navigated to, the UI reflects the persisted state.
for picker_id, store_id in [
    ("period-picker", "period-store"),
    ("pnl-mode", "pnl-mode-store"),
    ("ticker-selector", "ticker-store"),
    ("treemap-mode", "treemap-mode-store"),
    ("analytics-period-picker", "analytics-period-store"),
    ("intel-period-picker", "intel-period-store")
]:
    app.clientside_callback(
        "function(s, p) { return (s && s !== p) ? s : window.dash_clientside.no_update; }",
        Output(picker_id, "value"),
        Input(store_id, "data"),
        State(picker_id, "value")
    )


@app.callback(
    Output("intel-pred-store", "data"),
    Output("intel-forecast-label", "children"),
    Input("intel-pred-toggle", "checked"),
)
def sync_pred(v):
    if v is None:
        return dash.no_update, dash.no_update
    label = "Forecast ON" if v else "Forecast"
    return v, label






# ── Register Callbacks ────────────────────────────────────────────────────────
portfolio.register_callbacks(app)
txn.register_callbacks(app)
charts.register_callbacks(app)
alerts.register_callbacks(app)
ui.register_callbacks(app)
positions_cb.register_callbacks(app)
intell_cb.register_callbacks(app)
watchlist_cb.register_callbacks(app)
research_cb.register_callbacks(app)
signals_cb.register_callbacks(app)


@app.callback(
    Output("url", "search"),
    Input("startup-interval", "n_intervals"),
    prevent_initial_call=True,
)
def trigger_startup_maintenance_callback(n):
    """Enqueues heavy maintenance tasks to the background worker after startup."""
    if n == 1:
        if repo.is_onboarding_completed():
            from data.database import enqueue_task
            enqueue_task("maintenance", {"gemini_api_key": os.getenv("GEMINI_API_KEY")})
            logger.info("Enqueued background maintenance task (Cache cleanup + Watchlist refresh)")
        else:
            logger.info("Onboarding in progress: skipping startup maintenance task.")
    return dash.no_update

@app.callback(
    Output("pending-tasks-store", "data", allow_duplicate=True),
    Input("startup-interval", "n_intervals"),
    State("pending-tasks-store", "data"),
    prevent_initial_call=True
)
def hydrate_pending_tasks(n, pending):
    from data.database import get_connection
    conn = get_connection()
    try:
        rows = conn.execute("SELECT task_id, task_type FROM worker_tasks WHERE status IN ('pending', 'running')").fetchall()
        new_pending = pending or []
        existing_ids = {t["id"] for t in new_pending}
        for r in rows:
            if r["task_id"] not in existing_ids:
                new_pending.append({"id": r["task_id"], "type": r["task_type"]})
        return new_pending if len(new_pending) > (len(pending or [])) else dash.no_update
    except Exception as e:
        logger.error(f"Failed to hydrate pending tasks: {e}")
        return dash.no_update
    finally:
        conn.close()
    return dash.no_update

# ── Render Performance Optimizations ──────────────────────────────────────────
app.clientside_callback(
    """
    function(data) {
        return window.dash_clientside.no_update;
    }
    """,
    Output("nav-link-store", "data", allow_duplicate=True),
    Input("url", "pathname"),
    prevent_initial_call=True,
)


# ── Browser Management ────────────────────────────────────────────────────────
def open_browser():
    """
    Automatically opens the dashboard in the default browser.
    On macOS (darwin), it forces the use of Safari to ensure consistent 
    rendering of premium CSS effects (like glassmorphism and backdrop-filters) 
    which are highly optimized in WebKit.
    """
    if os.getenv("FOLIO_HEADLESS") == "1":
        logger.info("Headless mode active; skipping browser launch.")
        return

    if sys.platform == "darwin":
        # Guaranteed to use Safari on macOS
        os.system("open -a Safari http://127.0.0.1:8050/")
    else:
        webbrowser.open_new("http://127.0.0.1:8050/")


def close_browser():
    """
    Attempts to close the dashboard tab on shutdown.
    Uses AppleScript (osascript) to find and close any Safari tabs 
    pointing to the local dashboard URL. This prevents tab bloat 
    during development.
    """
    if sys.platform == "darwin":
        logger.info("\n  Shutting down... closing browser tabs.")
        # Target both 127.0.0.1 and localhost in Safari
        cmd_safari = "osascript -e 'tell application \"Safari\" to close (every tab of every window whose URL contains \"127.0.0.1:8050\" or URL contains \"localhost:8050\")' 2>/dev/null"
        os.system(cmd_safari)


# ── Task Poll Interval Manager (Clientside) ───────────────────────────────────
app.clientside_callback(
    """
    function(p1, p2, p3) {
        // Enable interval if any store has data
        const hasPending = (p1 && p1.length > 0) || 
                          (p2 && Object.keys(p2).length > 0) || 
                          (p3 !== null && p3 !== undefined);
        return !hasPending; // returns disabled=true if NOT pending
    }
    """,
    Output("task-poll-interval", "disabled"),
    Input("pending-tasks-store", "data"),
    Input("ai-pending-tasks-store", "data"),
    Input("benchmark-pending-store", "data"),
)


def handle_exit(sig, frame):
    """Signal handler for graceful shutdown."""
    close_browser()
    sys.exit(0)


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from config.settings import DB_PATH
    print(f"  Holdings:        http://127.0.0.1:8050/")
    print(f"  Positions:       http://127.0.0.1:8050/positions")
    print(f"  Watchlist:       http://127.0.0.1:8050/watchlist")
    print(f"  Insights:        http://127.0.0.1:8050/intelligence")
    print(f"  Deep Dive:       http://127.0.0.1:8050/analytics")
    print(f"  Assistant:       http://127.0.0.1:8050/ai-analyst\n")

    # Register signals
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    # ── Background Worker ─────────────────
    # Worker is now managed by launcher.py as a separate process.

    # Start browser after a short delay
    threading.Timer(1.5, open_browser).start()

    try:
        app.run(debug=False, port=8050)
    except SystemExit:
        # handle_exit calls sys.exit(0), which raises SystemExit
        pass
    except Exception as e:
        logger.error(f"App error: {e}")
        close_browser()