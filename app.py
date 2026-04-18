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

Responsiveness fix
------------------
portfolio-store and txn-store are seeded with data= at startup using the
values already computed before the app starts (INITIAL_HISTORY,
INITIAL_PORTFOLIO_DATA). This means all charts render on the very first
paint instead of waiting for the interval callback to fire and complete
a yfinance round-trip.
"""

# Setup logging first
from config.logging import setup_logging
setup_logging()

import logging
logger = logging.getLogger(__name__)

import dash
from dash import html, dcc, Input, Output

from components.layout import INDEX_STRING
from data.csv_handler import load_csv
from config.settings import REFRESH_INTERVAL

# Callback modules
import callbacks.core_callbacks         as core
import callbacks.transaction_callbacks  as txn
import callbacks.chart_callbacks        as charts
import callbacks.alert_callbacks        as alerts
import callbacks.ui_callbacks           as ui

# ── Initial data load ─────────────────────────────────────────────────────────
# This runs once at startup. The results seed the stores so the first render
# is instant — callbacks then keep data fresh on subsequent interval ticks.
try:
    INITIAL_HISTORY: list[dict] = load_csv()
    logger.info(f"Loaded {len(INITIAL_HISTORY)} transactions from CSV")
except Exception as e:
    logger.error(f"Failed to load initial CSV: {e}")
    INITIAL_HISTORY = []
    print(f"\nERROR loading CSV:\n{e}\n")

from data.portfolio_builder import build_holdings
from services.market.fetcher import fetch_live

INITIAL_HOLDINGS = build_holdings(INITIAL_HISTORY)
INITIAL_PORTFOLIO_DATA: dict = {}

if INITIAL_HOLDINGS:
    try:
        INITIAL_PORTFOLIO_DATA = fetch_live(INITIAL_HOLDINGS, "1Y")
        print("✅ Initial portfolio data loaded")
    except Exception as e:
        logger.warning(f"Initial market fetch failed: {e}")
        INITIAL_PORTFOLIO_DATA = {"holdings": INITIAL_HOLDINGS, "histories": {}}

# ── Dash App ──────────────────────────────────────────────────────────────────
app = dash.Dash(
    __name__,
    use_pages=True,
    pages_folder="pages",
    suppress_callback_exceptions=True,
)

app.title = "Portfolio — Live"
app.index_string = INDEX_STRING

# Import pages after app creation
import pages.etf_detail as etf_detail      # noqa: E402
import pages.intelligence as intelligence  # noqa: E402

# ── Root Layout ───────────────────────────────────────────────────────────────
app.layout = html.Div(
    [
        # Seed both stores with startup data so every chart renders on first paint.
        # The interval callback overwrites these with fresh data every 60 s.
        dcc.Store(id="txn-store",       data=INITIAL_HISTORY),
        dcc.Store(id="portfolio-store", data=INITIAL_PORTFOLIO_DATA),
        dcc.Store(id="alerts-store"),
        dcc.Store(id="theme-store",          data="dark"),
        dcc.Store(id="selected-ticker-store", data="Portfolio"),
        dcc.Interval(id="live-interval", interval=REFRESH_INTERVAL, n_intervals=0),

        dash.page_container,
    ],
    style={
        "fontFamily":      "system-ui,-apple-system,sans-serif",
        "color":           "var(--t-pri)",
        "maxWidth":        "1300px",
        "margin":          "0 auto",
        "backgroundColor": "var(--bg)",
    },
)

# ── Refresh callback — keeps stores fresh every interval tick ─────────────────
@app.callback(
    Output("txn-store",       "data"),
    Output("portfolio-store", "data"),
    Input("live-interval",    "n_intervals"),
    Input("refresh-btn",      "n_clicks"),
    prevent_initial_call=True,   # ← don't fire on load; stores are pre-seeded above
)
def refresh_portfolio_data(n_intervals, n_clicks):
    """
    Periodic callback to refresh market data.

    Fires on the 'live-interval' timer, re-loads CSV history, builds holdings,
    and fetches live market prices.

    Args:
        n: The interval count.

    Returns:
        Updated portfolio dictionary for the dcc.Store.
    """
    try:
        history  = load_csv()
        holdings = build_holdings(history)
        portfolio_data = fetch_live(holdings, "1Y") if holdings else {"holdings": [], "histories": {}}
        logger.debug(f"Refreshed portfolio: {len(holdings)} holdings")
        return history, portfolio_data
    except Exception as e:
        logger.error(f"Portfolio refresh failed: {e}")
        return [], {"holdings": [], "histories": {}}


# ── Register Callbacks ────────────────────────────────────────────────────────
core.register_callbacks(app)
txn.register_callbacks(app)
charts.register_callbacks(app)
alerts.register_callbacks(app)
ui.register_callbacks(app)
etf_detail.register_callbacks(app)
intelligence.register_callbacks(app)

# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from config.settings import CSV_PATH
    print(f"\n  Portfolio Dashboard — Live P&L (multi-page)")
    print(f"  CSV:          {CSV_PATH}")
    print(f"  Main:         http://127.0.0.1:8050/")
    print(f"  Intelligence: http://127.0.0.1:8050/intelligence\n")

    app.run(debug=False, port=8050)