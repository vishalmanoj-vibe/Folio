import logging
import pandas as pd
from config.constants import NAMES

logger = logging.getLogger(__name__)


def validate_transaction(txn: dict) -> tuple[bool, str]:
    """
    Validate transaction structure before aggregation.
    
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


def build_holdings(history: list[dict]) -> list[dict]:
    """
    Aggregate buy/sell transactions into one consolidated row per ticker.

    Returns a list of dicts, one per held ticker, with:
      - ticker, ticker_yf, name, market
      - total_shares (net after sells)
      - total_cost   (remaining cost at avg price)
      - avg_cost     (weighted avg of all buys)
      - first_purchase (earliest buy date string)
      - buy_tranches  (list of individual buy rows — needed for P&L history chart)
    """
    if not history:
        return []

    # Validate all transactions before processing
    invalid_txns = []
    for i, txn in enumerate(history):
        is_valid, error_msg = validate_transaction(txn)
        if not is_valid:
            invalid_txns.append((i, error_msg))
            logger.warning("Invalid transaction at index %d: %s", i, error_msg)
    
    if invalid_txns:
        logger.error("Found %d invalid transactions — skipping them", len(invalid_txns))

    # Filter out invalid transactions
    valid_history = [
        txn for i, txn in enumerate(history)
        if not any(idx == i for idx, _ in invalid_txns)
    ]

    if not valid_history:
        logger.warning("No valid transactions after validation")
        return []

    df = pd.DataFrame(valid_history)
    results = []

    for ticker, grp in df.groupby("ticker"):
        buys  = grp[grp["type"] == "buy"].copy()
        sells = (
            grp[grp["type"] == "sell"].copy()
            if "sell" in grp["type"].values
            else pd.DataFrame()
        )

        if buys.empty:
            continue

        total_bought = float(buys["shares"].sum())
        total_cost   = float((buys["shares"] * buys["price"]).sum())
        total_sold   = float(sells["shares"].sum()) if not sells.empty else 0.0
        net_shares   = total_bought - total_sold

        if net_shares <= 0:
            continue   # fully sold out — exclude from holdings

        avg_cost       = round(total_cost / total_bought, 4)
        # Proportional cost: preserves correct cost basis when shares are sold
        remaining_cost = round(total_cost * (net_shares / total_bought), 2)

        # Per-buy-tranche list — used by the P&L history chart
        buy_tranches = [
            {
                "ticker":    ticker,
                "shares":    float(r["shares"]),
                "price":     float(r["price"]),
                "date":      str(r["date"]),
                "buy_price": float(r["price"]),   # alias kept for chart compat
                "buy_date":  str(r["date"]),       # alias kept for chart compat
            }
            for _, r in buys.iterrows()
        ]

        results.append({
            "ticker":         ticker,
            "ticker_yf":      ticker + ".AX",
            "name":           NAMES.get(ticker, ticker),
            "market":         "ETF/ASX",
            "total_shares":   net_shares,
            "total_cost":     remaining_cost,
            "avg_cost":       avg_cost,
            "first_purchase": buys["date"].min(),
            "buy_tranches":   buy_tranches,
        })

    logger.info("Built %d holdings from %d transactions", len(results), len(history))
    return results