# app.py
"""
Portfolio Dashboard — modular entry point
==========================================
Run:   python app.py
Open:  http://127.0.0.1:8050

Pages
-----
  /               → pages/portfolio.py
  /positions      → pages/positions.py
  /analytics      → pages/analytics.py
  /intelligence   → pages/intelligence.py
  /dividends      → pages/dividends.py

Responsiveness fix (Pre-seeded Stores)
----------------------------------
To avoid "layout shifts" or empty charts on first load, the `portfolio-store` and `txn-store` 
are seeded with `data=` at startup. The server performs a blocking market fetch BEFORE 
the app becomes available. This ensures the first paint contains live data without 
waiting for the first `dcc.Interval` cycle.
"""

# Setup logging first
from config.logging import setup_logging
setup_logging()

from dotenv import load_dotenv
load_dotenv()

import logging
logger = logging.getLogger(__name__)

import dash
from dash import html, dcc, Input, Output, State, ALL, ctx
import webbrowser
import threading
import os
import sys
import signal
import time

from components.portfolio_layout import INDEX_STRING
from data.repository import PortfolioRepository
from core.validators import validate_transaction
from config.settings import REFRESH_INTERVAL
from data.watchlist_repository import WatchlistRepository

# Callback modules
import callbacks.portfolio_callbacks      as portfolio
import callbacks.transaction_callbacks    as txn
import callbacks.chart_callbacks          as charts
import callbacks.alert_callbacks          as alerts
import callbacks.ui_callbacks             as ui
import callbacks.intelligence_callbacks   as intell_cb
import callbacks.positions_callbacks      as positions_cb
import callbacks.dividend_callbacks       as dividends_cb
import callbacks.watchlist_callbacks      as watchlist_cb
import callbacks.research_callbacks  as research_cb

# ── Initial data load ─────────────────────────────────────────────────────────
repo = PortfolioRepository()

try:
    INITIAL_HISTORY: list[dict] = repo.load_transactions()
    logger.info(f"Loaded {len(INITIAL_HISTORY)} transactions from storage")
except Exception as e:
    logger.error(f"Failed to load initial CSV: {e}")
    INITIAL_HISTORY = []
    print(f"\nERROR loading CSV:\n{e}\n")

from data.portfolio_builder import build_holdings
from services.market.data_fetcher import fetch_live
from services.market.session_cache import clear_old_caches
from services.research_memory import run_startup_maintenance

# ── Maintenance ──────────────────────────────────────────────────────────────
clear_old_caches(keep_days=1)  # Aggressive cleanup on startup

INITIAL_HOLDINGS = build_holdings(INITIAL_HISTORY)
INITIAL_PORTFOLIO_DATA: dict = {}

if INITIAL_HOLDINGS:
    try:
        INITIAL_PORTFOLIO_DATA = fetch_live(INITIAL_HOLDINGS, "max")
        print("✅ Initial portfolio data loaded")
    except Exception as e:
        logger.warning(f"Initial market fetch failed: {e}")
        INITIAL_PORTFOLIO_DATA = {"holdings": INITIAL_HOLDINGS, "histories": {}}

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
        # Load histories from disk cache first — avoids yfinance fetch on every restart
        disk_histories = {}
        for item in INITIAL_WATCHLIST:
            ticker = item["ticker"]
            cached = watchlist_repo.load_history(ticker)
            if cached:
                disk_histories[ticker] = cached

        # Only fetch live prices (5d), not full history
        live_data = fetch_live(
            watchlist_holdings, "1y",
            record_snapshots=False,
            use_disk_history=True
        )

        # Merge disk histories into result
        # use_disk_history=True already handles this in fetch_live,
        # but ensure any ticker missing from live result gets disk data
        if "histories" not in live_data:
            live_data["histories"] = {}
        for ticker, hist in disk_histories.items():
            if ticker not in live_data["histories"] or not live_data["histories"][ticker]:
                live_data["histories"][ticker] = hist

        INITIAL_WATCHLIST_DATA = live_data
        watchlist_repo.refresh_all_histories()
        run_startup_maintenance(os.getenv("GEMINI_API_KEY", ""))
        print(f"✅ Watchlist loaded from cache ({len(disk_histories)} tickers from disk)")
    except Exception as e:
        logger.warning(f"Initial watchlist fetch failed: {e}")
        INITIAL_WATCHLIST_DATA = {"holdings": [], "histories": {}}

import dash_bootstrap_components as dbc

# ── Dash App ──────────────────────────────────────────────────────────────────
app = dash.Dash(
    __name__,
    use_pages=True,
    pages_folder="pages",
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
)

app.title = "Portfolio — Live"
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
            dcc.Store(id="txn-store",       data=INITIAL_HISTORY),
            dcc.Store(id="portfolio-store",     data=INITIAL_PORTFOLIO_DATA),
            dcc.Store(id="watchlist-store",     data=INITIAL_WATCHLIST_DATA),
            dcc.Store(id="alerts-store"),
            dcc.Store(id="theme-store",          data="dark", storage_type='local'),
            dcc.Store(id="compact-mode-store",   data=True),
            dcc.Store(id="table-state-store",     data={"search": "", "sort_col": "mkt_value", "sort_dir": "desc"}, storage_type='local'),
            dcc.Interval(id="live-interval", interval=REFRESH_INTERVAL, n_intervals=0),
            dcc.Store(id="nav-link-store"),

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
        ],
        className="app-container",
    )
)

# ── Refresh logic helpers ─────────────────
def _perform_refresh(period):
    history  = repo.load_transactions()
    holdings = build_holdings(history)
    portfolio_data = fetch_live(holdings, period) if holdings else {"holdings": [], "histories": {}}
    return history, portfolio_data

# ── SINGLE OWNER: txn-store ───────────────────────────────────────────────────
@app.callback(
    Output("txn-store", "data", allow_duplicate=True),
    Input("live-interval", "n_intervals"),
    Input("refresh-btn",   "n_clicks"),
    Input("txn-submit",    "n_clicks"),
    State("txn-type", "value"),
    State("txn-ticker", "value"),
    State("txn-shares", "value"),
    State("txn-price", "value"),
    State("txn-date", "value"),
    State("txn-store", "data"),
    prevent_initial_call=True,
)
def update_txn_store(n1, n2, n_submit, t_type, ticker, shares, price, date_str, history):
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
    Input("watchlist-period-store", "data"),
    Input("live-interval",          "n_intervals"),
    Input("refresh-btn",            "n_clicks"),
    prevent_initial_call=True,
)
def update_portfolio_store(txn_data, p1, p2, p3, p4, n1, n2):
    """Only place where portfolio-store is updated. Reacts to data or timeframe changes."""
    try:
        # Determine the maximum period requested across all pages to ensure history is available
        # Order of preference: 'max' > '1y' > 'ytd' > '3mo' > '1mo' > '1d'
        period_priority = {"max": 100, "1y": 80, "ytd": 70, "3mo": 60, "1mo": 40, "1d": 20}
        requested = [p1, p2, p3, p4]
        
        # Filter None and get weights
        weights = [(period_priority.get(p, 0), p) for p in requested if p]
        
        if weights:
            # Sort by weight descending and pick the top period string
            period = sorted(weights, key=lambda x: x[0], reverse=True)[0][1]
        else:
            period = "max"

        _, data = _perform_refresh(period)
        return data
    except Exception as e:
        logger.error(f"Portfolio refresh failed: {e}")
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

@app.callback(Output("positions-period-store", "data"), Input({"type": "pos-period-btn", "index": ALL}, "n_clicks"), prevent_initial_call=True)
def sync_p4(n_list):
    if not ctx.triggered_id: return dash.no_update
    # FIX: ignore ghost clicks on dynamically generated components
    if not ctx.triggered[0]["value"] or int(ctx.triggered[0]["value"]) < 1:
        return dash.no_update
    return ctx.triggered_id["index"]




# ── Register Callbacks ────────────────────────────────────────────────────────
portfolio.register_callbacks(app)
txn.register_callbacks(app)
charts.register_callbacks(app)
alerts.register_callbacks(app)
ui.register_callbacks(app)
positions_cb.register_callbacks(app)
dividends_cb.register_callbacks(app)
intell_cb.register_callbacks(app)
watchlist_cb.register_callbacks(app)
research_cb.register_callbacks(app)


# ── Render Performance Optimizations ──────────────────────────────────────────
app.clientside_callback(
    """
    function(data) {
        return window.dash_clientside.no_update;
    }
    """,
    Output("nav-link-store", "data", allow_duplicate=True),
    Input("portfolio-store", "data"),
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
        print("\n  Shutting down... closing browser tabs.")
        # Target both 127.0.0.1 and localhost in Safari
        cmd_safari = "osascript -e 'tell application \"Safari\" to close (every tab of every window whose URL contains \"127.0.0.1:8050\" or URL contains \"localhost:8050\")' 2>/dev/null"
        os.system(cmd_safari)


def handle_exit(sig, frame):
    """Signal handler for graceful shutdown."""
    close_browser()
    sys.exit(0)


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from config.settings import CSV_PATH
    print(f"  Main (Overview): http://127.0.0.1:8050/")
    print(f"  Positions:       http://127.0.0.1:8050/positions")
    print(f"  Analytics:       http://127.0.0.1:8050/analytics")
    print(f"  Intelligence:    http://127.0.0.1:8050/intelligence")
    print(f"  Dividends:       http://127.0.0.1:8050/dividends")
    print(f"  Watchlist:       http://127.0.0.1:8050/watchlist\n")

    # Register signals
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    # ── Background Snapshot Thread ─────────────────
    def background_refresh():
        """
        Independent thread that records snapshots every 60s.
        Ensures 'Today' chart has continuous data even if browser is closed.
        """
        while True:
            try:
                # We don't care about the UI period here; 
                # we just want fetch_live to run and record_snapshot to trigger.
                _perform_refresh("1d")
                logger.debug("Background snapshot recorded.")
            except Exception as e:
                logger.error(f"Background refresh failed: {e}")
            time.sleep(60)

    threading.Thread(target=background_refresh, daemon=True).start()

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