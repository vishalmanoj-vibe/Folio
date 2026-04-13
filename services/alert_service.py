def check_alerts(holdings: list[dict]) -> list[dict]:
    """
    Scan enriched holdings for alert conditions.

    Current rules:
      - Individual holding down ≥ 20% all-time → drawdown alert
      - Whole portfolio down ≥ 20% all-time → portfolio alert

    Returns a list of alert dicts: {type, ticker?, message}
    """
    alerts: list[dict] = []

    for h in holdings:
        if h.get("pnl_pct", 0) <= -20:
            alerts.append({
                "type":    "drawdown",
                "ticker":  h["ticker"],
                "message": f"{h['ticker']} down {h['pnl_pct']:.2f}% since purchase",
            })

    total_cost  = sum(h.get("total_cost", 0) for h in holdings)
    total_value = sum(h.get("mkt_value",  0) for h in holdings)

    if total_cost > 0:
        total_pct = (total_value - total_cost) / total_cost * 100
        if total_pct <= -20:
            alerts.append({
                "type":    "portfolio",
                "message": f"Portfolio down {total_pct:.2f}% overall",
            })

    return alerts
