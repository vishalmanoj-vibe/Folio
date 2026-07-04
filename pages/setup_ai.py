# pages/setup_ai.py
"""
pages/setup_ai.py
=================
Onboarding Wizard: Page 2 — AI Assistant Configuration
Route: /setup/ai
"""

import dash
import dash_mantine_components as dmc
from dash import dcc, html

dash.register_page(__name__, path="/setup/ai", title="Folio — AI Setup")


def layout() -> html.Div:
    return html.Div(
        [
            dcc.Store(id="setup-ai-redirect-store", data=None, storage_type="session"),
            html.Div(
                [
                    # Step indicators
                    html.Div(
                        [
                            html.Div(
                                [html.Span("✓", className="setup-step-num"), "Portfolio"],
                                className="setup-step completed",
                            ),
                            html.Div(
                                [html.Span("2", className="setup-step-num"), "Strategy & AI"],
                                className="setup-step active",
                            ),
                            html.Div(
                                [html.Span("3", className="setup-step-num"), "Ready"],
                                className="setup-step",
                            ),
                        ],
                        className="setup-steps-header",
                    ),
                    # Title & Description
                    html.H1("Configure Strategy & AI", className="setup-title"),
                    html.P(
                        "Customize your investment strategy preferences and optionally enable Gemini AI for deep market insights.",
                        className="setup-subtitle",
                    ),
                    # AI Key configuration container
                    html.Div(
                        [
                            # Strategy Settings
                            html.Div(
                                [
                                    html.H3(
                                        "Strategy Settings",
                                        className="txn-label",
                                        style={
                                            "borderBottom": "0.5px solid var(--border)",
                                            "paddingBottom": "6px",
                                            "marginBottom": "16px",
                                            "fontSize": "14px",
                                            "fontWeight": "600",
                                        },
                                    ),
                                    # Investment Goal
                                    html.Div(
                                        [
                                            html.Label("Investment Goal", className="txn-label"),
                                            dcc.Dropdown(
                                                id="setup-investment-goal",
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
                                        style={"marginBottom": "16px"},
                                    ),
                                    # Risk Tolerance
                                    html.Div(
                                        [
                                            html.Label("Risk Tolerance", className="txn-label"),
                                            dcc.Dropdown(
                                                id="setup-risk-tolerance",
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
                                        style={"marginBottom": "16px"},
                                    ),
                                    # Tax Bracket
                                    html.Div(
                                        [
                                            html.Label(
                                                "Tax Bracket (For CGT Warnings)",
                                                className="txn-label",
                                            ),
                                            dcc.Dropdown(
                                                id="setup-tax-bracket",
                                                options=[
                                                    {"label": "0% (No Tax)", "value": "0%"},
                                                    {"label": "15% (Super Fund)", "value": "15%"},
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
                                        style={"marginBottom": "12px"},
                                    ),
                                    html.P(
                                        "Note: These settings can be modified anytime in the settings section (gear icon in the top header) once the application is loaded.",
                                        className="setup-subtitle",
                                        style={
                                            "fontSize": "11px",
                                            "marginTop": "4px",
                                            "marginBottom": "24px",
                                            "fontStyle": "italic",
                                        },
                                    ),
                                ]
                            ),
                            # Features summary box
                            html.H3(
                                "AI Analyst (Optional)",
                                className="txn-label",
                                style={
                                    "borderBottom": "0.5px solid var(--border)",
                                    "paddingBottom": "6px",
                                    "marginBottom": "16px",
                                    "fontSize": "14px",
                                    "fontWeight": "600",
                                    "marginTop": "24px",
                                },
                            ),
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.Span("🔍", className="setup-ai-feature-icon"),
                                            html.Div(
                                                "<strong>Portfolio Insights:</strong> Explains complex technical indicators (RSI, MACD) and highlights key buy/sell/hold thresholds.",
                                                className="setup-ai-feature-text",
                                            ),
                                        ],
                                        className="setup-ai-feature-item",
                                    ),
                                    html.Div(
                                        [
                                            html.Span("💬", className="setup-ai-feature-icon"),
                                            html.Div(
                                                "<strong>Interactive Analyst Chat:</strong> Ask questions, run scenario tests, and research historical ETF metrics using live data.",
                                                className="setup-ai-feature-text",
                                            ),
                                        ],
                                        className="setup-ai-feature-item",
                                    ),
                                    html.Div(
                                        [
                                            html.Span("🛡️", className="setup-ai-feature-icon"),
                                            html.Div(
                                                "<strong>Secure Storage:</strong> Credentials are stored directly in your native macOS Keychain using hardware-level security.",
                                                className="setup-ai-feature-text",
                                            ),
                                        ],
                                        className="setup-ai-feature-item",
                                    ),
                                ],
                                className="setup-ai-features-list",
                            ),
                            # AI Provider
                            html.Div(
                                [
                                    html.Label("AI Provider", className="txn-label"),
                                    dcc.Dropdown(
                                        id="setup-ai-provider",
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
                                style={"marginBottom": "16px"},
                            ),
                            # AI Provider API Key
                            html.Div(
                                [
                                    html.Label("AI Provider API Key", className="txn-label"),
                                    dcc.Input(
                                        id="setup-ai-api-key",
                                        type="password",
                                        placeholder="Enter API key",
                                        className="setup-row-input",
                                        style={"width": "100%"},
                                    ),
                                    html.Div(
                                        [
                                            html.Button(
                                                "Test Connection",
                                                id="setup-ai-test-btn",
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
                                                id="setup-ai-test-status",
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
                                style={"marginBottom": "16px"},
                            ),
                            # AI Chat Model
                            html.Div(
                                [
                                    html.Label("AI Chat Model", className="txn-label"),
                                    dcc.Dropdown(
                                        id="setup-chat-model",
                                        options=[
                                            {
                                                "label": "Standard (2.5 Flash)",
                                                "value": "gemini-2.5-flash",
                                            },
                                            {
                                                "label": "Enhanced (3.1 Flash)",
                                                "value": "gemini-3.1-flash-lite",
                                            },
                                            {
                                                "label": "Gemini 2.5 Pro (Advanced)",
                                                "value": "gemini-2.5-pro",
                                            },
                                        ],
                                        value="gemini-2.5-flash",
                                        clearable=False,
                                        className="settings-dropdown",
                                    ),
                                ],
                                style={"marginBottom": "16px"},
                            ),
                            # AI Report Model
                            html.Div(
                                [
                                    html.Label("AI Report Model", className="txn-label"),
                                    dcc.Dropdown(
                                        id="setup-report-model",
                                        options=[
                                            {
                                                "label": "Standard (2.5 Flash)",
                                                "value": "gemini-2.5-flash",
                                            },
                                            {
                                                "label": "Enhanced (3.1 Flash)",
                                                "value": "gemini-3.1-flash-lite",
                                            },
                                        ],
                                        value="gemini-3.1-flash-lite",
                                        clearable=False,
                                        className="settings-dropdown",
                                    ),
                                ],
                                style={"marginBottom": "24px"},
                            ),
                            # Action buttons row
                            html.Div(
                                [
                                    html.Button(
                                        "Back",
                                        id="setup-ai-back-btn",
                                        className="setup-btn-secondary",
                                        type="button",
                                    ),
                                    html.Div(
                                        [
                                            html.Button(
                                                "Skip for now",
                                                id="setup-ai-skip-btn",
                                                className="setup-btn-secondary",
                                                type="button",
                                                style={"marginRight": "8px"},
                                            ),
                                            html.Button(
                                                "Save & Continue",
                                                id="setup-ai-save-btn",
                                                className="setup-btn-primary",
                                                type="button",
                                            ),
                                        ],
                                        style={"display": "flex"},
                                    ),
                                ],
                                className="setup-actions-row",
                            ),
                            # Feedback / Errors
                            html.Div(id="setup-ai-feedback", className="setup-feedback"),
                        ],
                        id="setup-ai-container",
                    ),
                ],
                className="setup-card",
            ),
        ],
        className="setup-root",
    )
