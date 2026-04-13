"""
Portfolio Dashboard — modular entry point
==========================================
Run:   python app.py
Open:  http://127.0.0.1:8050

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
    layout.py                     ← full Dash layout tree
    ui_helpers.py                 ← stat_card, chart_title, section, txn_table
  callbacks/
    core_callbacks.py             ← refresh, stat cards, live table
    transaction.py                ← add_transaction, txn log
    chart_callbacks.py            ← all 7 charts + ticker toggle buttons
    alert_callbacks.py            ← alerts banner
    ui_callbacks.py               ← theme toggle, PDF print (clientside)
"""

import logging
import dash

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)-30s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)

from components.layout import create_layout, INDEX_STRING
from data.csv_handler import load_csv

import callbacks.core_callbacks  as core
import callbacks.transaction     as txn
import callbacks.chart_callbacks as charts
import callbacks.alert_callbacks as alerts
import callbacks.ui_callbacks    as ui

# ── Load initial CSV data ─────────────────────────────────────────────────────
INITIAL_HISTORY: list[dict] = []
try:
    INITIAL_HISTORY = load_csv()
except Exception as e:
    print(f"\nERROR loading CSV:\n{e}")
    print("Dashboard will start with an empty portfolio.\n")

# ── Dash app ──────────────────────────────────────────────────────────────────
app = dash.Dash(
    __name__,
    suppress_callback_exceptions=True,   # required for dynamic ticker buttons
)
app.title        = "Portfolio — Live"
app.index_string = INDEX_STRING
app.layout       = create_layout(INITIAL_HISTORY)

# ── Register all callbacks ────────────────────────────────────────────────────
core.register_callbacks(app)
txn.register_callbacks(app)
charts.register_callbacks(app)
alerts.register_callbacks(app)
ui.register_callbacks(app)

# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from config import CSV_PATH
    print(f"\n  Portfolio Dashboard — Live P&L")
    print(f"  CSV:  {CSV_PATH}")
    print(f"  Open  http://127.0.0.1:8050\n")
    app.run(debug=False, port=8050)