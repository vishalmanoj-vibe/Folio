"""
Portfolio Dashboard — modular entry point
==========================================
Run:   python app.py
Open:  http://127.0.0.1:8050

Pages
-----
  /             → pages/portfolio.py      (main dashboard)
  /etf/<ticker> → pages/etf_detail.py     (ETF drill-down)
  /intelligence → pages/intelligence.py  (risk & allocation)  ← NEW
"""

from config.logging import setup_logging
setup_logging()

import dash
from dash import html, dcc

from components.layout import INDEX_STRING
from data.csv_handler import load_csv
from config.settings import REFRESH_INTERVAL

import callbacks.core_callbacks         as core
import callbacks.transaction_callbacks  as txn
import callbacks.chart_callbacks        as charts
import callbacks.alert_callbacks        as alerts
import callbacks.ui_callbacks           as ui

# ── Load initial CSV data ─────────────────────────────────────────────────────
INITIAL_HISTORY: list[dict] = []
try:
    INITIAL_HISTORY = load_csv()
except Exception as e:
    print(f"\nERROR loading CSV:\n{e}")
    print("Dashboard will start with an empty portfolio.\n")

# ── Compute initial portfolio data ────────────────────────────────────────────
from data.portfolio_builder import build_holdings
from services.market.fetcher import fetch_live

INITIAL_HOLDINGS = build_holdings(INITIAL_HISTORY)
INITIAL_PORTFOLIO_DATA = {}
if INITIAL_HOLDINGS:
    try:
        INITIAL_PORTFOLIO_DATA = fetch_live(INITIAL_HOLDINGS, "1Y")
        print("✅ Initial portfolio data loaded")
    except Exception as e:
        print(f"⚠️  Could not fetch initial market data: {e}")
        INITIAL_PORTFOLIO_DATA = {"holdings": INITIAL_HOLDINGS, "histories": {}}

# ── Dash app (Pages enabled) ──────────────────────────────────────────────────
app = dash.Dash(
    __name__,
    use_pages=True,
    pages_folder="pages",
    suppress_callback_exceptions=True,
)
app.title        = "Portfolio — Live"
app.index_string = INDEX_STRING

# ── pages/* imported AFTER dash.Dash() so register_page() succeeds ───────────
import pages.etf_detail    as etf_detail     # noqa: E402
import pages.intelligence  as intelligence   # noqa: E402

# ── Root layout ───────────────────────────────────────────────────────────────
app.layout = html.Div(
    [
        dcc.Store(id="txn-store",        data=INITIAL_HISTORY),
        dcc.Store(id="portfolio-store",  data=INITIAL_PORTFOLIO_DATA),
        dcc.Store(id="alerts-store"),
        dcc.Store(id="theme-store",      data="dark"),
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

# ── Register callbacks ────────────────────────────────────────────────────────
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
    print(f"\n  Portfolio Dashboard — Live P&L  (multi-page)")
    print(f"  CSV:           {CSV_PATH}")
    print(f"  Portfolio:     http://127.0.0.1:8050/")
    print(f"  ETF detail:    http://127.0.0.1:8050/etf/VHY")
    print(f"  Intelligence:  http://127.0.0.1:8050/intelligence\n")
    app.run(debug=False, port=8050)