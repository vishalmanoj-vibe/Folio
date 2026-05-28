# core/validators.py
"""
Validators for Folio.

Transaction validation and data checking utilities.
"""

import pandas as pd


def validate_transaction(txn: dict) -> tuple[bool, str]:
    """
    Validate transaction structure before aggregation.

    Args:
        txn: Transaction dictionary with keys: type, ticker, shares, price, date

    Returns:
        (is_valid, error_message)
    """
    required_keys = ["type", "ticker", "shares", "price", "date"]
    missing = [k for k in required_keys if k not in txn]
    if missing:
        return False, f"Transaction missing keys: {missing}"

    # Validate types
    try:
        shares = float(txn["shares"])
        price = float(txn["price"])
    except (TypeError, ValueError):
        return False, "Shares and price must be numeric"

    if shares <= 0 or price <= 0:
        return False, "Shares and price must be positive"

    txn_type = str(txn.get("type", "buy")).lower().strip()
    if txn_type not in ["buy", "sell"]:
        return False, f"Type must be 'buy' or 'sell', got '{txn_type}'"

    # Validate date format
    try:
        pd.to_datetime(str(txn["date"]), format="%Y-%m-%d")
    except (ValueError, TypeError):
        return False, f"Date must be YYYY-MM-DD, got '{txn['date']}'"

    return True, ""
