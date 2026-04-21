"""
callbacks/transaction_callbacks.py
====================================
Clean transaction callbacks with reliable history refresh.
"""

from dash import Input, Output, State, html
import dash
from datetime import datetime

from core.validators import validate_transaction
from data.csv_handler import save_csv
from components.ui_helpers import txn_table

import logging
logger = logging.getLogger(__name__)


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
        if len(ticker) < 2:
            return "", dash.no_update
        
        try:
            name = get_etf_name(ticker)
            # Try to get live price for pre-fill
            ticker_yf = f"{ticker.upper()}.AX" if "." not in ticker else ticker.upper()
            tk = get_ticker_cached(ticker_yf)
            
            # Use fast_info if possible, else regular info
            try:
                price = tk.fast_info.last_price
                if price == 0 or math.isnan(price):
                    price = tk.info.get("regularMarketPrice") or tk.info.get("previousClose")
            except:
                price = tk.info.get("regularMarketPrice") or tk.info.get("previousClose")
                
            return name, round(price, 2) if price else dash.no_update
        except Exception as e:
            logger.debug(f"Discovery failed for {ticker}: {e}")
            return "", dash.no_update


    # Add new transaction
    @app.callback(
        Output("txn-store", "data"),
        Output("txn-msg", "children"),
        Output("txn-msg", "style"),
        Input("txn-submit", "n_clicks"),
        State("txn-type", "value"),
        State("txn-ticker", "value"),
        State("txn-shares", "value"),
        State("txn-price", "value"),
        State("txn-date", "value"),
        State("txn-store", "data"),
        prevent_initial_call=True,
    )
    def add_transaction(n_clicks, txn_type, ticker, shares, price, date_str, current_history):
        if n_clicks is None or n_clicks == 0:
            return dash.no_update, "", {}

        if not all([txn_type, ticker, shares is not None, price is not None, date_str]):
            return dash.no_update, "❌ Please fill all fields", {"color": "#E24B4A"}

        # Handle both string and date object (DMC may return either)
        if hasattr(date_str, 'strftime'):
            formatted_date = date_str.strftime("%Y-%m-%d")
        else:
            formatted_date = str(date_str).strip()

        new_txn = {
            "type": str(txn_type).strip().lower(),
            "ticker": str(ticker).strip().upper(),
            "shares": float(shares),
            "price": float(price),
            "date": formatted_date,
        }

        is_valid, error_msg = validate_transaction(new_txn)
        if not is_valid:
            return dash.no_update, f"❌ {error_msg}", {"color": "#E24B4A"}

        updated_history = (current_history or []) + [new_txn]

        try:
            save_csv(updated_history)
            success_msg = f"✅ Added {new_txn['type'].upper()} {new_txn['shares']:.2f} {new_txn['ticker']}"
            # Signal refresh is handled by app.py listening to txn-store change
            return updated_history, success_msg, {"color": "#1D9E75"}
        except Exception as e:
            logger.error(f"Save failed: {e}")
            return dash.no_update, f"❌ Save failed: {str(e)}", {"color": "#E24B4A"}


    # Refresh transaction history table whenever txn-store changes
    @app.callback(
        Output("txn-log", "children"),
        Input("txn-store", "data"),
        prevent_initial_call=False,   # runs on load
    )
    def update_transaction_log(history):
        """Always show latest transactions"""
        return txn_table(history or [])


    # Auto-clear message after ~60 seconds
    @app.callback(
        Output("txn-msg", "children"),
        Input("live-interval", "n_intervals"),
        State("txn-msg", "children"),
        prevent_initial_call=True,
    )
    def clear_message(_, msg):
        if msg and ("✅" in msg or "❌" in msg):
            return ""
        return dash.no_update