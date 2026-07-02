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

# Map refresh policy value → interval milliseconds
REFRESH_POLICY_MS: dict[str, int] = {
    "1m": 60_000,
    "5m": 300_000,
    "15m": 900_000,
    "30m": 1_800_000,
    "EOD": 86_400_000,
}


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
        Output("settings-chat-model", "value"),
        Output("settings-report-model", "value"),
        Output("settings-portfolio-benchmark", "value"),
        Output("settings-custom-benchmark", "value"),
        Output("settings-ai-persona", "value"),
        Output("settings-refresh-policy", "value"),
        Input("url", "pathname"),
        prevent_initial_call=False,
    )
    def load_user_settings(pathname):
        if pathname != "/settings":
            return (
                dash.no_update,
                dash.no_update,
                dash.no_update,
                dash.no_update,
                dash.no_update,
                dash.no_update,
                dash.no_update,
                dash.no_update,
                dash.no_update,
            )

        logger.debug("Loading user settings for Settings page.")
        settings = get_all_settings()
        return (
            settings.get("investment_goal", "Balanced"),
            settings.get("risk_tolerance", "Moderate"),
            settings.get("tax_bracket", "37%"),
            settings.get("ai_chat_model", "gemini-2.5-flash"),
            settings.get("ai_report_model", "gemini-3.1-flash-lite"),
            settings.get("portfolio_benchmark", "^AXJO"),
            settings.get("custom_benchmark", ""),
            settings.get("ai_persona", "Conservative"),
            settings.get("data_refresh_policy", "5m"),
        )

    # ── Callback 2: Dynamic weight preview ──
    @app.callback(
        Output("settings-weights-preview-container", "children"),
        Input("url", "pathname"),
        Input("settings-investment-goal", "value"),
        Input("settings-risk-tolerance", "value"),
        prevent_initial_call=False,
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

    # ── Callback 3: Toggle custom benchmark input visibility ──
    @app.callback(
        Output("settings-custom-benchmark-row", "style"),
        Input("settings-portfolio-benchmark", "value"),
        prevent_initial_call=False,
    )
    def toggle_custom_benchmark(benchmark_val):
        if benchmark_val == "__custom__":
            return {"display": "block"}
        return {"display": "none"}

    # ── Callback 4: Save settings ──
    @app.callback(
        Output("settings-save-status", "children"),
        Input("settings-save-btn", "n_clicks"),
        State("url", "pathname"),
        State("settings-investment-goal", "value"),
        State("settings-risk-tolerance", "value"),
        State("settings-tax-bracket", "value"),
        State("settings-chat-model", "value"),
        State("settings-report-model", "value"),
        State("settings-portfolio-benchmark", "value"),
        State("settings-custom-benchmark", "value"),
        State("settings-ai-persona", "value"),
        State("settings-refresh-policy", "value"),
        prevent_initial_call=True,
    )
    def save_user_settings(
        n_clicks,
        pathname,
        goal,
        risk,
        tax,
        chat_model,
        report_model,
        benchmark,
        custom_benchmark,
        ai_persona,
        refresh_policy,
    ):
        if pathname != "/settings" or not n_clicks:
            return dash.no_update

        logger.info(
            f"Saving user settings: Goal={goal}, Risk={risk}, Tax={tax}, "
            f"ChatModel={chat_model}, ReportModel={report_model}, "
            f"Benchmark={benchmark}, Persona={ai_persona}, Refresh={refresh_policy}"
        )
        save_setting("investment_goal", goal)
        save_setting("risk_tolerance", risk)
        save_setting("tax_bracket", tax)
        save_setting("ai_chat_model", chat_model or "gemini-2.5-flash")
        save_setting("ai_report_model", report_model or "gemini-3.1-flash-lite")
        save_setting("portfolio_benchmark", benchmark or "^AXJO")
        save_setting("custom_benchmark", custom_benchmark or "")
        save_setting("ai_persona", ai_persona or "Conservative")
        save_setting("data_refresh_policy", refresh_policy or "5m")

        time_str = datetime.now().strftime("%H:%M:%S")
        return f"✓ Profile settings saved successfully at {time_str}"

    # ── Callback 5: Dynamically update price-interval based on saved refresh policy ──
    @app.callback(
        Output("price-interval", "interval"),
        Input("settings-save-status", "children"),
        Input("url", "pathname"),
        prevent_initial_call=False,
    )
    def update_price_interval(save_status, pathname):
        """Reads the persisted data_refresh_policy and updates the Dash interval in the browser."""
        settings = get_all_settings()
        policy = settings.get("data_refresh_policy", "5m")
        ms = REFRESH_POLICY_MS.get(policy, 300_000)
        logger.debug(f"Setting price-interval to {ms}ms (policy={policy})")
        return ms

    # ── Callback 6: Dynamically update AI Persona description text ──
    @app.callback(
        Output("settings-ai-persona-description", "children"),
        Input("settings-ai-persona", "value"),
        prevent_initial_call=False,
    )
    def update_persona_description(persona_val):
        descriptions = {
            "Conservative": (
                "Conservative Wealth Manager: Prioritizes capital preservation, historic drawdowns, and structural "
                "200-day moving average metrics. Appends CGT tax evaluations (favoring >12 months holding period) on sales."
            ),
            "Skeptical": (
                "Skeptical Short-Seller / Devil's Advocate: Critically evaluates all technical signals. "
                "Highlights divergences (e.g. price vs. RSI), volume decay, and potential bull traps."
            ),
            "Growth": (
                "Growth Optimist: Momentum & trend-following focus. Emphasizes strong tailwinds, moving average "
                "crossovers (50MA/200MA), sector leadership, and new 52-week highs."
            ),
            "Concise": (
                "Concise Executive: Short, bulleted, data-dense briefs. Grounded purely in hard metrics "
                "(RSI values, moving average percentages, support/resistance levels) with zero filler."
            ),
        }
        return descriptions.get(persona_val, "")
