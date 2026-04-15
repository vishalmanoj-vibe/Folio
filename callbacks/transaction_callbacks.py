"""
callbacks/transaction_callbacks.py
====================================
Transaction management callbacks.

Handles:
- Adding new Buy/Sell transactions
- Saving to CSV + updating txn-store
- Refreshing the transaction history table (txn-log)
- User feedback

Fully compatible with the current app.py refresh pattern.
"""

from dash import Input, Output, State, html
import dash
from datetime import datetime

from core.validators import validate_transaction
from data.csv_handler import save_csv
from components.ui_helpers import txn_table   # ← This renders the history table

import logging
logger = logging.getLogger(__name__)


def register_callbacks(app):

    # ── 1. Add new transaction ───────────────────────────────────────────────
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
            return (
                dash.no_update,
                "❌ Please fill in all fields",
                {"color": "#E24B4A", "fontSize": "13px"},
            )

        new_txn = {
            "type": str(txn_type).strip().lower(),
            "ticker": str(ticker).strip().upper(),
            "shares": float(shares),
            "price": float(price),
            "date": str(date_str).strip(),
            "created_at": datetime.now().isoformat(),
        }

        is_valid, error_msg = validate_transaction(new_txn)
        if not is_valid:
            logger.warning(f"Invalid transaction: {error_msg}")
            return dash.no_update, f"❌ {error_msg}", {"color": "#E24B4A", "fontSize": "13px"}

        updated_history = (current_history or []) + [new_txn]

        try:
            save_csv(updated_history)
            logger.info(f"Saved transaction: {new_txn['type']} {new_txn['ticker']}")

            success_msg = f"✅ Added {new_txn['type'].upper()} {new_txn['shares']:.2f} {new_txn['ticker']} @ ${new_txn['price']:.4f}"
            return updated_history, success_msg, {"color": "#1D9E75", "fontSize": "13px", "marginTop": "8px"}

        except Exception as e:
            logger.error(f"Save failed: {e}")
            return dash.no_update, f"❌ Save failed: {str(e)}", {"color": "#E24B4A", "fontSize": "13px"}


    # ── 2. Refresh transaction history table whenever txn-store changes ───────
    @app.callback(
        Output("txn-log", "children"),
        Input("txn-store", "data"),
        prevent_initial_call=False,   # Important: runs on initial load too
    )
    def update_transaction_log(history):
        """Render the full transaction history table from the store."""
        if not history:
            return html.P("No transactions yet.", 
                          style={"color": "var(--t-sec)", "fontSize": "13px"})
        
        return txn_table(history)


    # ── 3. Optional: Auto-clear success message after one interval ────────────
    @app.callback(
        Output("txn-msg", "children"),
        Input("live-interval", "n_intervals"),
        State("txn-msg", "children"),
        prevent_initial_call=True,
    )
    def clear_transaction_message(_, current_msg):
        if current_msg and ("✅" in current_msg or "❌" in current_msg):
            return ""
        return dash.no_update