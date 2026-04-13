from datetime import datetime
import pytz
from dash import html
from config import SURFACE, BORDER, GREEN, T_SEC


def is_market_open() -> bool:
    now_utc = datetime.now(pytz.utc)
    now_aet = now_utc.astimezone(pytz.timezone("Australia/Sydney"))
    return (
        now_aet.weekday() < 5
        and (now_aet.hour > 10 or (now_aet.hour == 10 and now_aet.minute >= 0))
        and now_aet.hour < 16
    )


def market_badge() -> html.Span:
    open_ = is_market_open()
    return html.Span(
        "ASX open" if open_ else "ASX closed",
        style={
            "fontSize":     "12px",
            "padding":      "3px 10px",
            "borderRadius": "20px",
            "background":   "#E1F5EE" if open_ else SURFACE,
            "color":        GREEN if open_ else T_SEC,
            "fontWeight":   "500",
            "border":       f"0.5px solid {'#1D9E75' if open_ else BORDER}",
        },
    )