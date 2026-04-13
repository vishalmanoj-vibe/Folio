import logging
import pandas as pd
from config import NAMES

logger = logging.getLogger(__name__)


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

    df = pd.DataFrame(history)
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