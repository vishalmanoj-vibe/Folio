"""
Portfolio Dashboard — modular entry point
==========================================
Run:   python app.py
Open:  http://127.0.0.1:8050

Pages
-----
  /               → pages/portfolio.py
  /etf/<ticker>   → pages/etf_detail.py
  /intelligence   → pages/intelligence.py

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
from dash import html, dcc, Input, Output
import webbrowser
import threading
import os
import sys
import signal

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
import callbacks.etf_detail_callbacks     as etf_detail_cb

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
        INITIAL_PORTFOLIO_DATA = fetch_live(INITIAL_HOLDINGS, "1Y")
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

# Import pages after app creation
import pages.etf_detail as etf_detail      # noqa: E402
import pages.intelligence as intelligence  # noqa: E402
import pages.analytics as analytics        # noqa: E402
import pages.portfolio as portfolio_page    # noqa: E402

import dash_mantine_components as dmc

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
            dcc.Store(id="portfolio-store", data=INITIAL_PORTFOLIO_DATA),
            dcc.Store(id="alerts-store"),
            dcc.Store(id="theme-store",          data="dark"),
            dcc.Store(id="compact-mode-store",   data=True, storage_type='local'),
            dcc.Store(id="table-state-store",     data={"search": "", "sort_col": "mkt_value", "sort_dir": "desc"}, storage_type='local'),
            dcc.Store(id="selected-ticker-store", data="Portfolio"),
            dcc.Interval(id="live-interval", interval=REFRESH_INTERVAL, n_intervals=0),
            dash.page_container,
        ],
        className="app-container",
    )
)

# ── Refresh callback ─────────────────
@app.callback(
    Output("txn-store",       "data"),
    Output("portfolio-store", "data"),
    Input("live-interval",    "n_intervals"),
    Input("refresh-btn",      "n_clicks"),
    prevent_initial_call=True,
)
def refresh_portfolio_data(n_intervals, n_clicks):
    try:
        history  = load_csv()
        holdings = build_holdings(history)
        portfolio_data = fetch_live(holdings, "1Y") if holdings else {"holdings": [], "histories": {}}
        return history, portfolio_data
    except Exception as e:
        logger.error(f"Portfolio refresh failed: {e}")
        return [], {"holdings": [], "histories": {}}


# ── Register Callbacks ────────────────────────────────────────────────────────
portfolio.register_callbacks(app)
txn.register_callbacks(app)
charts.register_callbacks(app)
alerts.register_callbacks(app)
ui.register_callbacks(app)
etf_detail_cb.register_callbacks(app)
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
    print(f"\n  Portfolio Dashboard — Live P&L (multi-page)")
    print(f"  CSV:          {CSV_PATH}")
    print(f"  Main:         http://127.0.0.1:8050/")
    print(f"  Analytics:    http://127.0.0.1:8050/analytics")
    print(f"  Intelligence: http://127.0.0.1:8050/intelligence\n")

    # Register signals
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

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