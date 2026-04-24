# callbacks/alert_callbacks.py
"""
Alert Callbacks for Portfolio Dashboard.

Handles the rendering of the alert banner based on portfolio logic.
"""

from dash import Input, Output, html
from config.constants import RED
from services.alert_service import check_alerts


def register_callbacks(app) -> None:
    """
    Register alert-related callbacks with the Dash application.

    Args:
        app: The Dash application instance.
    """

    @app.callback(
        Output("alerts-banner", "children"),
        Output("intel-alert-count", "children"),
        Output("intel-alert-count", "style"),
        Input("portfolio-store", "data"),
    )
    def show_alerts(data):
        if not data or "holdings" not in data:
            return "", "", {"display": "none"}

        alerts = check_alerts(data["holdings"])
        count = len(alerts)
        
        # Badge logic
        badge_style = {"display": "inline-block"} if count > 0 else {"display": "none"}
        badge_text = str(count) if count > 0 else ""

        if not alerts:
            return "", badge_text, badge_style

        return html.Div(
            [html.Div(a["message"]) for a in alerts],
            style={
                "background":    "rgba(226, 75, 74, 0.1)", # Subtle red background
                "color":         "var(--red, #E24B4A)",
                "padding":       "10px 24px",
                "borderRadius":  "0",
                "fontSize":      "13px",
                "borderBottom":  "0.5px solid var(--red, #E24B4A)",
            },
        ), badge_text, badge_style
