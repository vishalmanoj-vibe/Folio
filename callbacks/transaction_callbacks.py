# callbacks/transaction_callbacks.py
"""
callbacks/transaction_callbacks.py
====================================
Clean transaction callbacks with reliable history refresh.
"""

import logging
import math
from datetime import datetime

import dash
from dash import Input, Output, State, html

from components.ui_helpers import txn_table
from core.validators import validate_transaction

logger = logging.getLogger(__name__)
from data.database import get_connection
from services.market.data_fetcher import get_etf_name, get_ticker_cached


def register_callbacks(app):
    """
    Register transaction-related callbacks with the Dash application.
    """

    # ── Ticker Discovery (Name & Price) ─────────────────
    @app.callback(
        Output("txn-ticker-hint", "children"),
        Output("txn-price", "value"),
        Input("txn-ticker", "value"),
        prevent_initial_call=True,
    )
    def discover_ticker(ticker):
        if not ticker or len(ticker.strip()) == 0:
            return "", dash.no_update

        ticker = ticker.strip().upper()
        if ticker.endswith(".AX"):
            ticker = ticker[:-3]
        if len(ticker) < 2:
            return "", dash.no_update

        try:
            # 1. Get Name (Uses multi-layer cache)
            name = get_etf_name(ticker)

            # 2. Get Price from SQLite (Read-only, zero network)
            conn = get_connection()
            price = None
            try:
                row = conn.execute(
                    "SELECT last_price FROM market_prices WHERE ticker = ?", (ticker,)
                ).fetchone()
                if row:
                    price = row["last_price"]
            finally:
                conn.close()

            # 3. If NOT in cache, perform a targeted live fetch
            if not price:
                try:
                    ticker_yf = f"{ticker}.AX" if "." not in ticker else ticker
                    tk = get_ticker_cached(ticker_yf)
                    # Try fast_info first, then full info
                    price = tk.fast_info.last_price
                    if not price or math.isnan(price) or price == 0:
                        price = tk.info.get("regularMarketPrice") or tk.info.get("previousClose")
                except Exception:
                    price = None

            return name, round(price, 2) if price else dash.no_update
        except Exception as e:
            # Only log if it's not a common 'not found' or network timeout
            if ticker and len(ticker) > 2:
                logger.debug(f"Discovery failed for {ticker}: {e}")
            return "", dash.no_update

    @app.callback(
        Output("txn-msg", "children"),
        Output("txn-msg", "style"),
        Output("compact-mode-store", "data", allow_duplicate=True),
        Input("txn-submit", "n_clicks"),
        State("txn-type", "value"),
        State("txn-ticker", "value"),
        State("txn-shares", "value"),
        State("txn-price", "value"),
        State("txn-date", "value"),
        prevent_initial_call=True,
    )
    def add_transaction(n_clicks, txn_type, ticker, shares, price, date_str):
        if n_clicks is None or n_clicks == 0:
            return "", {}, dash.no_update

        if not all([txn_type, ticker, shares is not None, price is not None, date_str]):
            # FIX: use CSS token instead of hardcoded hex
            return "❌ Please fill all fields", {"color": "var(--red)"}, dash.no_update

        # Handle both string and date object (DMC may return either)
        if hasattr(date_str, "strftime"):
            formatted_date = date_str.strftime("%Y-%m-%d")
        else:
            formatted_date = str(date_str).strip()

        ticker_clean = str(ticker).strip().upper()
        if ticker_clean.endswith(".AX"):
            ticker_clean = ticker_clean[:-3]
        new_txn = {
            "type": str(txn_type).strip().lower(),
            "ticker": ticker_clean,
            "shares": float(shares),
            "price": float(price),
            "date": formatted_date,
        }

        is_valid, error_msg = validate_transaction(new_txn)
        if not is_valid:
            # FIX: use CSS token instead of hardcoded hex
            return f"❌ {error_msg}", {"color": "var(--red)"}, dash.no_update

        success_msg = (
            f"✅ Added {new_txn['type'].upper()} {new_txn['shares']:.2f} {new_txn['ticker']}"
        )
        # FIX: use CSS token instead of hardcoded hex
        return success_msg, {"color": "var(--green)"}, True

    # Refresh transaction history table whenever txn-store changes
    @app.callback(
        Output("txn-log", "children"),
        Input("txn-store", "data"),
        prevent_initial_call=True,  # runs on load
    )
    def update_transaction_log(history):
        """Always show latest transactions"""
        return txn_table(history or [])

    # Auto-clear message after ~60 seconds
    @app.callback(
        Output("txn-msg", "children", allow_duplicate=True),
        Input("live-interval", "n_intervals"),
        State("txn-msg", "children"),
        prevent_initial_call=True,
    )
    def clear_message(_, msg):
        if msg and ("✅" in msg or "❌" in msg):
            return ""
        return dash.no_update
