"""
callbacks/transaction_callbacks.py
====================================
Transaction management callbacks for the Portfolio Dashboard.

Handles:
- Adding new Buy/Sell transactions
- Input validation
- Saving to CSV (persistence)
- Updating the shared txn-store
- User feedback messages

This file preserves the original architecture and integrates with:
- data/csv_handler.py (save_csv)
- core/validators.py (validate_transaction)
- components/layout.py (transaction form UI)
"""

from dash import Input, Output, State, callback_context
import dash
from datetime import datetime

from core.validators import validate_transaction
from data.csv_handler import save_csv
from config.constants import GREEN, RED   # For success/error coloring

import logging
logger = logging.getLogger(__name__)


def register_callbacks(app):

    @app.callback(
        Output("txn-store", "data"),          # Update the shared transaction store
        Output("txn-msg", "children"),        # User feedback message
        Output("txn-msg", "style"),           # Color the message (green/red)
        Input("txn-submit", "n_clicks"),
        State("txn-type", "value"),
        State("txn-ticker", "value"),
        State("txn-shares", "value"),
        State("txn-price", "value"),
        State("txn-date", "value"),
        State("txn-store", "data"),           # Current transactions in memory
        prevent_initial_call=True,
    )
    def add_transaction(n_clicks, txn_type, ticker, shares, price, date_str, current_history):
        """
        Main callback to add a new transaction.
        
        Triggered when user clicks "Add transaction".
        Validates → Saves to CSV → Updates store → Shows feedback.
        """
        if n_clicks is None or n_clicks == 0:
            return dash.no_update, "", {}

        # Basic required field check
        if not all([txn_type, ticker, shares, price, date_str]):
            return (
                dash.no_update,
                "❌ Please fill in all fields (Type, Ticker, Shares, Price, Date)",
                {"color": RED, "fontSize": "13px"},
            )

        # Clean and prepare transaction dict
        new_txn = {
            "type": str(txn_type).strip().lower(),
            "ticker": str(ticker).strip().upper(),
            "shares": float(shares),
            "price": float(price),
            "date": str(date_str).strip(),
        }

        # Validate transaction using shared validator
        is_valid, error_msg = validate_transaction(new_txn)
        if not is_valid:
            logger.warning(f"Invalid transaction attempt: {error_msg}")
            return (
                dash.no_update,
                f"❌ Validation error: {error_msg}",
                {"color": RED, "fontSize": "13px"},
            )

        # Add creation timestamp for better tracking (optional but useful)
        new_txn["created_at"] = datetime.now().isoformat()

        # Append to current history
        updated_history = (current_history or []) + [new_txn]

        # Persist to CSV (this is the key for refresh persistence)
        try:
            save_csv(updated_history)
            logger.info(f"Transaction saved successfully: {new_txn['type']} {new_txn['shares']} {new_txn['ticker']} @ ${new_txn['price']}")
            
            success_msg = (
                f"✅ Added {new_txn['type'].upper()} "
                f"{new_txn['shares']:.2f} shares of {new_txn['ticker']} "
                f"at ${new_txn['price']:.4f} on {new_txn['date']}"
            )
            
            return (
                updated_history,                    # Update the store
                success_msg,
                {"color": GREEN, "fontSize": "13px", "marginTop": "8px"},
            )

        except Exception as e:
            logger.error(f"Failed to save transaction to CSV: {e}")
            return (
                dash.no_update,
                f"❌ Failed to save transaction: {str(e)}",
                {"color": RED, "fontSize": "13px"},
            )


    # Optional: Clear message after a few seconds (nice UX)
    @app.callback(
        Output("txn-msg", "children"),
        Input("live-interval", "n_intervals"),
        State("txn-msg", "children"),
        prevent_initial_call=True,
    )
    def clear_transaction_message(n_intervals, current_msg):
        """Auto-clear success/error message after ~60 seconds (one interval)."""
        if current_msg and ("✅" in current_msg or "❌" in current_msg):
            # Only clear success/error messages, keep empty string
            return ""
        return dash.no_update