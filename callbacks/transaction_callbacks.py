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


def register_callbacks(app):

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

        new_txn = {
            "type": str(txn_type).strip().lower(),
            "ticker": str(ticker).strip().upper(),
            "shares": float(shares),
            "price": float(price),
            "date": str(date_str).strip(),
        }

        is_valid, error_msg = validate_transaction(new_txn)
        if not is_valid:
            return dash.no_update, f"❌ {error_msg}", {"color": "#E24B4A"}

        updated_history = (current_history or []) + [new_txn]

        try:
            save_csv(updated_history)
            success_msg = f"✅ Added {new_txn['type'].upper()} {new_txn['shares']:.2f} {new_txn['ticker']}"
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