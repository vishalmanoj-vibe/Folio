# callbacks/settings_callbacks.py
"""
callbacks/settings_callbacks.py
==============================
Callbacks for the Settings page: loading/saving settings and rendering the weights preview.
"""

import logging
from datetime import datetime

import dash
from dash import Input, Output, State, html

from data.settings_repository import get_all_settings, save_setting
from services.strategy_engine import get_profile_weights

logger = logging.getLogger(__name__)


def make_weight_bar(name: str, val: float) -> html.Div:
    percentage = int(val * 100)
    return html.Div(
        [
            html.Div(
                [
                    html.Span(name, className="settings-weight-bar-name"),
                    html.Span(f"{percentage}%", className="settings-weight-bar-value"),
                ],
                className="settings-weight-bar-label-container",
            ),
            html.Div(
                html.Div(className="settings-weight-bar-fill", style={"width": f"{percentage}%"}),
                className="settings-weight-bar-bg",
            ),
        ],
        className="settings-weight-bar-row",
    )


def register_callbacks(app):
    # ── Callback 1: Load settings when Settings page is rendered ──
    @app.callback(
        Output("settings-investment-goal", "value"),
        Output("settings-risk-tolerance", "value"),
        Output("settings-tax-bracket", "value"),
        Input("url", "pathname"),
        prevent_initial_call=True,
    )
    def load_user_settings(pathname):
        if pathname != "/settings":
            return dash.no_update, dash.no_update, dash.no_update

        logger.debug("Loading user settings for Settings page.")
        settings = get_all_settings()
        return (
            settings.get("investment_goal", "Balanced"),
            settings.get("risk_tolerance", "Moderate"),
            settings.get("tax_bracket", "37%"),
        )

    # ── Callback 2: Dynamic weight preview ──
    @app.callback(
        Output("settings-weights-preview-container", "children"),
        Input("url", "pathname"),
        Input("settings-investment-goal", "value"),
        Input("settings-risk-tolerance", "value"),
        prevent_initial_call=True,
    )
    def update_weight_preview(pathname, goal, risk):
        if pathname != "/settings":
            return dash.no_update

        if not goal or not risk:
            return dash.no_update

        logger.debug(f"Calculating weight preview for Goal={goal}, Risk={risk}")
        weights = get_profile_weights(goal, risk)

        return [
            make_weight_bar("Trend following (50MA / 200MA)", weights.get("trend", 0.0)),
            make_weight_bar("Momentum (RSI oversold/overbought)", weights.get("momentum", 0.0)),
            make_weight_bar("Value discount (200MA distance)", weights.get("value", 0.0)),
            make_weight_bar("Cost basis alignment", weights.get("cost", 0.0)),
            make_weight_bar("Risk penalty (drawdowns)", weights.get("risk", 0.0)),
        ]

    # ── Callback 3: Save settings ──
    @app.callback(
        Output("settings-save-status", "children"),
        Input("settings-save-btn", "n_clicks"),
        State("url", "pathname"),
        State("settings-investment-goal", "value"),
        State("settings-risk-tolerance", "value"),
        State("settings-tax-bracket", "value"),
        prevent_initial_call=True,
    )
    def save_user_settings(n_clicks, pathname, goal, risk, tax):
        if pathname != "/settings" or not n_clicks:
            return dash.no_update

        logger.info(f"Saving user settings: Goal={goal}, Risk={risk}, Tax={tax}")
        save_setting("investment_goal", goal)
        save_setting("risk_tolerance", risk)
        save_setting("tax_bracket", tax)

        time_str = datetime.now().strftime("%H:%M:%S")
        return f"✓ Profile settings saved successfully at {time_str}"
