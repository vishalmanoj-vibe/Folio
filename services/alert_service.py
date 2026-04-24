# services/alert_service.py
"""
Alert service for Portfolio Dashboard.

Detects portfolio and position drawdown conditions.
"""

from config.settings import ALERT_THRESHOLDS


def check_alerts(holdings: list[dict], thresholds: dict | None = None) -> list[dict]:
    """
    Scan enriched holdings for alert conditions.

    Configuration:
      - individual_drawdown: Alert if any holding down X% all-time (default -20%)
      - portfolio_drawdown:  Alert if portfolio down X% all-time (default -15%)

    Thresholds can be overridden via config.ALERT_THRESHOLDS or environment variables:
      - ALERT_INDIVIDUAL_DRAWDOWN_PCT
      - ALERT_PORTFOLIO_DRAWDOWN_PCT

    Returns a list of alert dicts: {type, ticker?, message}
    """
    if thresholds is None:
        thresholds = ALERT_THRESHOLDS

    alerts: list[dict] = []
    individual_threshold = thresholds.get("individual_drawdown", -20.0)
    portfolio_threshold = thresholds.get("portfolio_drawdown", -15.0)

    # Individual position drawdowns
    for h in holdings:
        if h.get("pnl_pct", 0) <= individual_threshold:
            alerts.append({
                "type":    "drawdown",
                "ticker":  h["ticker"],
                "message": f"{h['ticker']} down {h['pnl_pct']:.2f}% since purchase",
            })

    # Portfolio total drawdown
    total_cost  = sum(h.get("total_cost", 0) for h in holdings)
    total_value = sum(h.get("mkt_value",  0) for h in holdings)

    if total_cost > 0:
        total_pct = (total_value - total_cost) / total_cost * 100
        if total_pct <= portfolio_threshold:
            alerts.append({
                "type":    "portfolio",
                "message": f"Portfolio down {total_pct:.2f}% overall",
            })

    return alerts
