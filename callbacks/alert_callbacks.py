from dash import Input, Output, html
from config.constants import RED
from services.alerts import check_alerts


def register_callbacks(app) -> None:

    @app.callback(
        Output("alerts-banner", "children"),
        Input("portfolio-store", "data"),
    )
    def show_alerts(data):
        if not data or "holdings" not in data:
            return ""

        alerts = check_alerts(data["holdings"])
        if not alerts:
            return ""

        return html.Div(
            [html.Div(a["message"]) for a in alerts],
            style={
                "background":    "#2a0f0f",
                "color":         RED,
                "padding":       "10px 24px",
                "borderRadius":  "0",
                "marginBottom":  "0",
                "fontSize":      "13px",
                "borderBottom":  f"0.5px solid {RED}",
            },
        )
