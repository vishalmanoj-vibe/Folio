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
                                [html.Span("2", className="setup-step-num"), "AI Analyst"],
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
                    html.H1("Enable AI features (optional)", className="setup-title"),
                    html.P(
                        "Supercharge your portfolio strategy with an integrated AI investment analyst powered by Gemini. "
                        "This enables deep market explanations and custom risk evaluations.",
                        className="setup-subtitle",
                    ),
                    # AI Key configuration container
                    html.Div(
                        [
                            # Features summary box
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
                            # Gemini Key Input field
                            html.Div(
                                [
                                    html.Label("Gemini API Key", className="txn-label"),
                                    dcc.Input(
                                        id="setup-gemini-key",
                                        type="password",
                                        placeholder="Enter your Gemini API Key (AI_...) or Google AI Studio key",
                                        className="setup-row-input",
                                        style={"width": "100%"},
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
