# pages/settings.py
"""
pages/settings.py
=================
Investor Profile Settings Page.
Route: /settings
"""

import dash
from dash import dcc, html

from components.ui_helpers import section

dash.register_page(__name__, path="/settings", title="Folio — Settings")


def layout() -> html.Div:
    return html.Div(
        [
            # Page Header
            html.Div(
                [
                    html.Div(
                        [
                            html.H1("Settings", className="header-title"),
                            html.P(
                                "Investor Profile & Strategy Customization",
                                className="header-subtitle",
                            ),
                        ],
                        className="header-title-row",
                    ),
                ],
                className="page-header-row",
            ),
            # Form and Weight Preview side-by-side
            html.Div(
                [
                    # Left Column: Form
                    html.Div(
                        [
                            section(
                                html.H3("Investor Profile", className="settings-section-title"),
                                html.Div(
                                    [
                                        # Investment Goal
                                        html.Div(
                                            [
                                                html.Label(
                                                    "Investment Goal", className="settings-label"
                                                ),
                                                html.P(
                                                    "Configures the technical engine weights (e.g. Growth prioritizes trend/momentum; Income focuses on cost basis & yield).",
                                                    className="settings-preview-description",
                                                    style={"marginBottom": "6px"},
                                                ),
                                                dcc.Dropdown(
                                                    id="settings-investment-goal",
                                                    options=[
                                                        {
                                                            "label": "Balanced (Default)",
                                                            "value": "Balanced",
                                                        },
                                                        {
                                                            "label": "Growth (Focus Trend & Momentum)",
                                                            "value": "Growth",
                                                        },
                                                        {
                                                            "label": "Income (Focus Cost Basis & Value)",
                                                            "value": "Income",
                                                        },
                                                        {
                                                            "label": "Capital Preservation (Focus Risk & Value)",
                                                            "value": "Capital Preservation",
                                                        },
                                                    ],
                                                    value="Balanced",
                                                    clearable=False,
                                                    className="settings-dropdown",
                                                ),
                                            ],
                                            className="settings-form-row",
                                        ),
                                        # Risk Tolerance
                                        html.Div(
                                            [
                                                html.Label(
                                                    "Risk Tolerance", className="settings-label"
                                                ),
                                                html.P(
                                                    "Adjusts strategy score penalties; Low risk tolerance applies strict penalties to assets with large drawdowns.",
                                                    className="settings-preview-description",
                                                    style={"marginBottom": "6px"},
                                                ),
                                                dcc.Dropdown(
                                                    id="settings-risk-tolerance",
                                                    options=[
                                                        {
                                                            "label": "Low (Higher Risk Penalties)",
                                                            "value": "Low",
                                                        },
                                                        {
                                                            "label": "Moderate (Default)",
                                                            "value": "Moderate",
                                                        },
                                                        {
                                                            "label": "High (Muted Risk Penalties)",
                                                            "value": "High",
                                                        },
                                                    ],
                                                    value="Moderate",
                                                    clearable=False,
                                                    className="settings-dropdown",
                                                ),
                                            ],
                                            className="settings-form-row",
                                        ),
                                        # Tax Bracket
                                        html.Div(
                                            [
                                                html.Label(
                                                    "Tax Bracket (For CGT Warnings)",
                                                    className="settings-label",
                                                ),
                                                html.P(
                                                    "Determines your marginal tax rate to calculate tax implications and display Capital Gains Tax (CGT) alerts.",
                                                    className="settings-preview-description",
                                                    style={"marginBottom": "6px"},
                                                ),
                                                dcc.Dropdown(
                                                    id="settings-tax-bracket",
                                                    options=[
                                                        {"label": "0% (No Tax)", "value": "0%"},
                                                        {
                                                            "label": "15% (Super Fund)",
                                                            "value": "15%",
                                                        },
                                                        {"label": "19%", "value": "19%"},
                                                        {"label": "30%", "value": "30%"},
                                                        {"label": "32.5%", "value": "32.5%"},
                                                        {"label": "37% (Default)", "value": "37%"},
                                                        {"label": "45%", "value": "45%"},
                                                    ],
                                                    value="37%",
                                                    clearable=False,
                                                    className="settings-dropdown",
                                                ),
                                            ],
                                            className="settings-form-row",
                                        ),
                                        # ── AI Provider ──────────────────────
                                        html.Div(
                                            [
                                                html.Label(
                                                    "AI Provider",
                                                    className="settings-label",
                                                ),
                                                html.P(
                                                    "Select the AI service provider to power insights, sentiment, and chat.",
                                                    className="settings-preview-description",
                                                    style={"marginBottom": "6px"},
                                                ),
                                                dcc.Dropdown(
                                                    id="settings-ai-provider",
                                                    options=[
                                                        {
                                                            "label": "Google Gemini (Default)",
                                                            "value": "gemini",
                                                        },
                                                        {
                                                            "label": "OpenAI (ChatGPT)",
                                                            "value": "openai",
                                                        },
                                                        {
                                                            "label": "Anthropic (Claude)",
                                                            "value": "anthropic",
                                                        },
                                                    ],
                                                    value="gemini",
                                                    clearable=False,
                                                    className="settings-dropdown",
                                                ),
                                            ],
                                            className="settings-form-row",
                                        ),
                                        # API Key
                                        html.Div(
                                            [
                                                html.Label(
                                                    "AI Provider API Key",
                                                    className="settings-label",
                                                ),
                                                html.P(
                                                    "Enter your API key for the selected provider. Key is saved securely locally.",
                                                    className="settings-preview-description",
                                                    style={"marginBottom": "6px"},
                                                ),
                                                dcc.Input(
                                                    id="settings-ai-api-key-input",
                                                    type="password",
                                                    placeholder="Enter API key",
                                                    className="txn-input",
                                                    style={"width": "100%"},
                                                ),
                                                html.Div(
                                                    [
                                                        html.Button(
                                                            "Test Connection",
                                                            id="settings-ai-test-btn",
                                                            className="setup-btn-primary",
                                                            type="button",
                                                            style={
                                                                "marginTop": "8px",
                                                                "marginRight": "12px",
                                                                "padding": "6px 12px",
                                                                "fontSize": "12px",
                                                            },
                                                        ),
                                                        html.Span(
                                                            id="settings-ai-test-status",
                                                            className="settings-status-message",
                                                            style={
                                                                "display": "inline-block",
                                                                "verticalAlign": "middle",
                                                                "marginTop": "8px",
                                                            },
                                                        ),
                                                    ],
                                                    style={"marginTop": "8px"},
                                                ),
                                            ],
                                            className="settings-form-row",
                                        ),
                                        # ── AI Model Selection ──────────────
                                        html.Div(
                                            [
                                                html.Label(
                                                    "AI Chat Model",
                                                    className="settings-label",
                                                ),
                                                html.P(
                                                    "Used by the AI Research Assistant chatbot.",
                                                    className="settings-preview-description",
                                                    style={"marginBottom": "6px"},
                                                ),
                                                dcc.Dropdown(
                                                    id="settings-chat-model",
                                                    options=[
                                                        {
                                                            "label": "Standard (2.5 Flash) — Fast, low cost",
                                                            "value": "gemini-2.5-flash",
                                                        },
                                                        {
                                                            "label": "Enhanced (3.1 Flash) — Higher quality",
                                                            "value": "gemini-3.1-flash-lite",
                                                        },
                                                    ],
                                                    value="gemini-2.5-flash",
                                                    clearable=False,
                                                    className="settings-dropdown",
                                                ),
                                            ],
                                            className="settings-form-row",
                                        ),
                                        # Report Model
                                        html.Div(
                                            [
                                                html.Label(
                                                    "AI Report Model",
                                                    className="settings-label",
                                                ),
                                                html.P(
                                                    "Used when generating the weekly PDF commentary.",
                                                    className="settings-preview-description",
                                                    style={"marginBottom": "6px"},
                                                ),
                                                dcc.Dropdown(
                                                    id="settings-report-model",
                                                    options=[
                                                        {
                                                            "label": "Standard (2.5 Flash) — Fast, low cost",
                                                            "value": "gemini-2.5-flash",
                                                        },
                                                        {
                                                            "label": "Enhanced (3.1 Flash) — Higher quality",
                                                            "value": "gemini-3.1-flash-lite",
                                                        },
                                                    ],
                                                    value="gemini-3.1-flash-lite",
                                                    clearable=False,
                                                    className="settings-dropdown",
                                                ),
                                            ],
                                            className="settings-form-row",
                                        ),
                                        # ── Portfolio Benchmark ─────────────
                                        html.Div(
                                            [
                                                html.Label(
                                                    "Portfolio Benchmark",
                                                    className="settings-label",
                                                ),
                                                html.P(
                                                    "Index to compare your portfolio returns against on charts.",
                                                    className="settings-preview-description",
                                                    style={"marginBottom": "6px"},
                                                ),
                                                dcc.Dropdown(
                                                    id="settings-portfolio-benchmark",
                                                    options=[
                                                        {
                                                            "label": "ASX 200 (Default)",
                                                            "value": "^AXJO",
                                                        },
                                                        {"label": "S&P 500", "value": "^GSPC"},
                                                        {"label": "Nasdaq 100", "value": "^NDX"},
                                                        {
                                                            "label": "MSCI World (URTH ETF)",
                                                            "value": "URTH",
                                                        },
                                                        {
                                                            "label": "Custom Ticker...",
                                                            "value": "__custom__",
                                                        },
                                                    ],
                                                    value="^AXJO",
                                                    clearable=False,
                                                    className="settings-dropdown",
                                                ),
                                                # Hidden row shown dynamically when custom is selected
                                                html.Div(
                                                    [
                                                        dcc.Input(
                                                            id="settings-custom-benchmark",
                                                            type="text",
                                                            placeholder="e.g. SPY, ACWI, VGS.AX",
                                                            className="txn-input",
                                                            debounce=True,
                                                            style={
                                                                "marginTop": "8px",
                                                                "width": "100%",
                                                            },
                                                        ),
                                                    ],
                                                    id="settings-custom-benchmark-row",
                                                    style={"display": "none"},
                                                ),
                                            ],
                                            className="settings-form-row",
                                        ),
                                        # ── AI Persona ──────────────────────
                                        html.Div(
                                            [
                                                html.Label(
                                                    "AI Analysis Persona",
                                                    className="settings-label",
                                                ),
                                                html.P(
                                                    "Sets the tone and style of AI signal explanations and the Research Assistant.",
                                                    className="settings-preview-description",
                                                    style={"marginBottom": "6px"},
                                                ),
                                                dcc.Dropdown(
                                                    id="settings-ai-persona",
                                                    options=[
                                                        {
                                                            "label": "Conservative Wealth Manager (Default)",
                                                            "value": "Conservative",
                                                        },
                                                        {
                                                            "label": "Skeptical Short-Seller — Devil's Advocate",
                                                            "value": "Skeptical",
                                                        },
                                                        {
                                                            "label": "Growth Optimist — Momentum & Tailwinds",
                                                            "value": "Growth",
                                                        },
                                                        {
                                                            "label": "Concise Executive — Bullets & Key Figures Only",
                                                            "value": "Concise",
                                                        },
                                                    ],
                                                    value="Conservative",
                                                    clearable=False,
                                                    className="settings-dropdown",
                                                ),
                                                # Dynamic description displayed below the selected persona
                                                html.P(
                                                    id="settings-ai-persona-description",
                                                    className="settings-preview-description",
                                                    style={
                                                        "marginTop": "8px",
                                                        "color": "var(--t-sec)",
                                                        "fontStyle": "italic",
                                                    },
                                                ),
                                            ],
                                            className="settings-form-row",
                                        ),
                                        # ── Data Refresh Policy ─────────────
                                        html.Div(
                                            [
                                                html.Label(
                                                    "Data Refresh Frequency",
                                                    className="settings-label",
                                                ),
                                                html.P(
                                                    "How often the app polls for live price updates during market hours.",
                                                    className="settings-preview-description",
                                                    style={"marginBottom": "6px"},
                                                ),
                                                dcc.Dropdown(
                                                    id="settings-refresh-policy",
                                                    options=[
                                                        {
                                                            "label": "1 Minute — High frequency",
                                                            "value": "1m",
                                                        },
                                                        {
                                                            "label": "5 Minutes (Default)",
                                                            "value": "5m",
                                                        },
                                                        {
                                                            "label": "15 Minutes — Standard",
                                                            "value": "15m",
                                                        },
                                                        {
                                                            "label": "30 Minutes — Low frequency",
                                                            "value": "30m",
                                                        },
                                                        {
                                                            "label": "End of Day — Data saver mode",
                                                            "value": "EOD",
                                                        },
                                                    ],
                                                    value="5m",
                                                    clearable=False,
                                                    className="settings-dropdown",
                                                ),
                                            ],
                                            className="settings-form-row",
                                        ),
                                        # Save Button & Success notification
                                        html.Div(
                                            [
                                                html.Button(
                                                    "Save Profile Settings",
                                                    id="settings-save-btn",
                                                    className="setup-btn-primary",
                                                    type="button",
                                                    style={"marginTop": "16px"},
                                                ),
                                                html.Div(
                                                    id="settings-save-status",
                                                    className="settings-status-message",
                                                ),
                                            ],
                                            className="settings-action-row",
                                        ),
                                    ],
                                    className="settings-form-container",
                                ),
                            ),
                        ],
                        className="grid-item-2",
                    ),
                    # Right Column: Strategy Weight Preview
                    html.Div(
                        [
                            section(
                                html.H3(
                                    "Active Strategy Weight Profile",
                                    className="settings-section-title",
                                ),
                                html.Div(
                                    [
                                        html.P(
                                            "These weights are applied dynamically to compute technical indicator signal scores. "
                                            "Scores sum to 1.0. Signals: BUY >= 0.5, SELL <= -0.5.",
                                            className="settings-preview-description",
                                        ),
                                        html.Div(id="settings-weights-preview-container"),
                                    ],
                                    className="settings-preview-container",
                                ),
                            ),
                        ],
                        className="grid-item-2",
                    ),
                ],
                className="charts-grid-row",
            ),
        ],
        className="page-root",
    )
