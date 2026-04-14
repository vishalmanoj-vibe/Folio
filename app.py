"""
Portfolio Dashboard — modular entry point
==========================================
Run:   python app.py
Open:  http://127.0.0.1:8050

Pages
-----
  /             → pages/portfolio.py   (existing dashboard, unchanged)
  /etf/<ticker> → pages/etf_detail.py  (new ETF drill-down)

File layout:
  app.py                          ← this file
  config.py                       ← all constants / colours / paths
  data/
    csv_handler.py                ← load_csv / save_csv
    portfolio_builder.py          ← build_holdings
  services/
    cache.py                      ← simple TTL cache
    market_data.py                ← fetch_live (yfinance)
    alert_service.py              ← check_alerts
    market_status.py              ← is_market_open / market_badge
  components/
    layout.py                     ← portfolio page layout tree
    ui_helpers.py                 ← stat_card, chart_title, section, txn_table
  callbacks/
    core_callbacks.py             ← refresh, stat cards, live table  (+ ticker links)
    transaction_callbacks.py      ← add_transaction, txn log
    chart_callbacks.py            ← all 7 charts + ticker toggle buttons
    alert_callbacks.py            ← alerts banner
    ui_callbacks.py               ← theme toggle, PDF print (clientside)
  pages/
    portfolio.py                  ← Dash page wrapper: /
    etf_detail.py                 ← Dash page wrapper: /etf/<ticker>  ← NEW
"""

import dash
from dash import html, dcc

from components.layout import INDEX_STRING
from data.csv_handler import load_csv
from config import REFRESH_INTERVAL

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

# ── Dash app (Pages enabled) ──────────────────────────────────────────────────
app = dash.Dash(
    __name__,
    use_pages=True,
    pages_folder="pages",
    suppress_callback_exceptions=True,
)
app.title        = "Portfolio — Live"
app.index_string = INDEX_STRING

# pages/* imported HERE — after dash.Dash() — so register_page() succeeds
import pages.etf_detail as etf_detail  # noqa: E402

# ── Root layout ───────────────────────────────────────────────────────────────
# Shared stores + interval live here so they survive page navigation.
# Each page renders its own chrome inside dash.page_container.
app.layout = html.Div(
    [
        dcc.Store(id="txn-store",        data=INITIAL_HISTORY),
        dcc.Store(id="portfolio-store"),
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

# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from config import CSV_PATH
    print(f"\n  Portfolio Dashboard — Live P&L  (multi-page)")
    print(f"  CSV:        {CSV_PATH}")
    print(f"  Portfolio:  http://127.0.0.1:8050/")
    print(f"  ETF detail: http://127.0.0.1:8050/etf/VHY\n")
    app.run(debug=False, port=8050)