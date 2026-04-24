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
from data.csv_handler import load_csv
from config.settings import REFRESH_INTERVAL

# Callback modules
import callbacks.portfolio_callbacks      as portfolio
import callbacks.transaction_callbacks    as txn
import callbacks.chart_callbacks          as charts
import callbacks.alert_callbacks          as alerts
import callbacks.ui_callbacks             as ui
import callbacks.intelligence_callbacks   as intell_cb
import callbacks.positions_callbacks      as positions_cb
import callbacks.dividend_callbacks       as dividends_cb

# ── Initial data load ─────────────────────────────────────────────────────────
try:
    INITIAL_HISTORY: list[dict] = load_csv()
    logger.info(f"Loaded {len(INITIAL_HISTORY)} transactions from CSV")
except Exception as e:
    logger.error(f"Failed to load initial CSV: {e}")
    INITIAL_HISTORY = []
    print(f"\nERROR loading CSV:\n{e}\n")

from data.portfolio_builder import build_holdings
from services.market.data_fetcher import fetch_live

INITIAL_HOLDINGS = build_holdings(INITIAL_HISTORY)
INITIAL_PORTFOLIO_DATA: dict = {}

if INITIAL_HOLDINGS:
    try:
        INITIAL_PORTFOLIO_DATA = fetch_live(INITIAL_HOLDINGS, "max")
        print("✅ Initial portfolio data loaded")
    except Exception as e:
        logger.warning(f"Initial market fetch failed: {e}")
        INITIAL_PORTFOLIO_DATA = {"holdings": INITIAL_HOLDINGS, "histories": {}}

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
            dcc.Store(id="analytics-period-store", data="max",    storage_type='session'),
            dcc.Store(id="intel-period-store",     data="3mo",    storage_type='session'),
            dcc.Store(id="intel-pred-store",       data=False,    storage_type='session'),
            dcc.Store(id="positions-selected-ticker", data=None, storage_type='session'),
            dcc.Store(id="positions-period-store", data="3mo", storage_type='session'),
            
            # Global Navigation
            create_header(),
            
            # Page Content with Loading Indicator
            dcc.Loading(
                dash.page_container,
                type="dot",
                color="var(--cyan)",
            ),
        ],
        className="app-container",
    )
)

# ── Refresh logic helpers ─────────────────
def _perform_refresh(period):
    history  = load_csv()
    holdings = build_holdings(history)
    portfolio_data = fetch_live(holdings, period) if holdings else {"holdings": [], "histories": {}}
    return history, portfolio_data

# ── Primary Refresh (Interval / Button) ─────────────────
@app.callback(
    Output("txn-store",       "data", allow_duplicate=True),
    Output("portfolio-store", "data", allow_duplicate=True),
    Input("live-interval",    "n_intervals"),
    Input("refresh-btn",      "n_clicks"),
    State("period-store",     "data"),
    State("analytics-period-store", "data"),
    prevent_initial_call='initial_duplicate',
)
def refresh_periodic(n_intervals, n_clicks, p1, p2):
    """
    Periodic refresh triggered by browser timer.
    Note: Snapshot recording also happens in a background thread for reliability.
    """
    try:
        # Use whatever period store is populated
        period = p1 or p2 or "max"
        return _perform_refresh(period)
    except Exception as e:
        logger.error(f"Periodic refresh failed: {e}")
        return dash.no_update, dash.no_update

# ── Immediate Refresh on Transaction Change ──────────────
@app.callback(
    Output("portfolio-store", "data", allow_duplicate=True),
    Input("txn-store", "data"),
    State("period-store", "data"),
    State("analytics-period-store", "data"),
    prevent_initial_call=True,
)
def refresh_on_txn(txn_data, p1, p2):
    """
    Triggered when a transaction is added via the UI.
    Forces a portfolio-store refresh so charts/stats update immediately.
    """
    try:
        logger.info("Transaction update detected; triggering portfolio refresh.")
        period = p1 or p2 or "max"
        _, data = _perform_refresh(period)
        return data
    except Exception as e:
        logger.error(f"Transaction-triggered refresh failed: {e}")
        return dash.no_update

# ── Store-Triggered Portfolio Refresh ─────────────────
@app.callback(
    Output("portfolio-store", "data", allow_duplicate=True),
    Input("period-store", "data"),
    Input("analytics-period-store", "data"),
    prevent_initial_call=True,
)
def refresh_on_period_change(p1, p2):
    try:
        # Determine which one changed or use a priority
        period = p1 or p2 or "max"
        _, data = _perform_refresh(period)
        return data
    except Exception as e:
        logger.error(f"Store-triggered refresh failed: {e}")
        return dash.no_update

# ── Global Picker Syncing (Session Persistence) ──────────────────────────────
@app.callback(Output("period-store", "data"), Input("period-picker", "value"), prevent_initial_call=True)
def sync_p1(v): return v if v else dash.no_update

@app.callback(Output("pnl-mode-store", "data"), Input("pnl-mode", "value"), prevent_initial_call=True)
def sync_mode(v): return v if v else dash.no_update

@app.callback(Output("ticker-store", "data"), Input("ticker-selector", "value"), prevent_initial_call=True)
def sync_tk(v): return v if v else dash.no_update

@app.callback(Output("treemap-mode-store", "data"), Input("treemap-mode", "value"), prevent_initial_call=True)
def sync_tree(v): return v if v else dash.no_update

@app.callback(Output("analytics-period-store", "data"), Input("analytics-period-picker", "value"), prevent_initial_call=True)
def sync_p2(v): return v if v else dash.no_update

@app.callback(Output("intel-period-store", "data"), Input("intel-period-picker", "value"), prevent_initial_call=True)
def sync_p3(v): return v if v else dash.no_update

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
    print(f"  Dividends:       http://127.0.0.1:8050/dividends\n")

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