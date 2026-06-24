# components/chatbot.py
"""
components/chatbot.py
=====================
Layout structure for the floating AI Assistant chatbot widget.
"""

import dash_mantine_components as dmc
from dash import dcc, html


def create_chatbot_widget() -> html.Div:
    """
    Renders the persistent floating chatbot widget.
    Includes the toggle button and the main glassmorphic chat container.
    """
    return html.Div(
        [
            # 1. Floating Action Button (Trigger)
            html.Button(
                [
                    html.Span("✨", className="chatbot-icon"),
                    html.Span("Ask Folio AI", className="chatbot-trigger-text"),
                ],
                id="chatbot-trigger",
                className="chatbot-trigger-btn",
                n_clicks=0,
                style={"display": "flex"},  # Starts visible
            ),
            # 2. Chat Window Container
            html.Div(
                [
                    # Header
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Span(
                                        "✨", style={"fontSize": "16px", "marginRight": "4px"}
                                    ),
                                    html.Span("Folio AI Assistant", className="chatbot-title"),
                                ],
                                className="chatbot-header-left",
                                style={"display": "flex", "alignItems": "center"},
                            ),
                            # Close button
                            html.Button(
                                "✕", id="chatbot-close", className="chatbot-close-btn", n_clicks=0
                            ),
                        ],
                        className="chatbot-header",
                    ),
                    # Context Status Bar
                    html.Div(
                        id="chatbot-context-bar",
                        className="chatbot-context-bar",
                    ),
                    # Ticker Research Input row
                    html.Div(
                        [
                            dmc.TextInput(
                                id="research-ticker-input",
                                placeholder="Research ticker (e.g. VAS, NDQ)...",
                                size="xs",
                                style={"width": "100%"},
                                debounce=True,
                            ),
                        ],
                        className="chatbot-ticker-row",
                    ),
                    # Chat Display Area
                    html.Div(id="research-chat-display", className="research-chat-display"),
                    # Typing Indicator
                    html.Div(
                        id="research-typing-indicator",
                        className="research-typing-indicator",
                        style={"display": "none"},
                        children=[
                            html.Span("●", style={"animationDelay": "0s"}),
                            html.Span("●", style={"animationDelay": "0.2s"}),
                            html.Span("●", style={"animationDelay": "0.4s"}),
                        ],
                    ),
                    # Usage display
                    html.Div(
                        id="research-usage-display",
                        className="research-usage-display",
                    ),
                    # Quick Prompt Chips
                    html.Div(
                        [
                            html.Button(
                                "Does this fit my portfolio?",
                                id="qp-1",
                                className="quick-prompt-chip btn-sm",
                                n_clicks=0,
                            ),
                            html.Button(
                                "What are the risks?",
                                id="qp-2",
                                className="quick-prompt-chip btn-sm",
                                n_clicks=0,
                            ),
                            html.Button(
                                "Compare to what I own",
                                id="qp-3",
                                className="quick-prompt-chip btn-sm",
                                n_clicks=0,
                            ),
                            html.Button(
                                "What am I missing?",
                                id="qp-4",
                                className="quick-prompt-chip btn-sm",
                                n_clicks=0,
                            ),
                            html.Button(
                                "Generate Weekly Report",
                                id="qp-report",
                                className="quick-prompt-chip btn-sm",
                                n_clicks=0,
                                style={
                                    "borderColor": "var(--cyan)",
                                    "color": "var(--cyan)",
                                },
                            ),
                        ],
                        id="chatbot-quick-prompts",
                        className="quick-prompt-chips",
                    ),
                    # Input Row
                    html.Div(
                        [
                            dcc.Input(
                                id="research-input",
                                type="text",
                                placeholder="Ask anything about your portfolio or a ticker...",
                                className="mantine-TextInput-input",
                                style={"flex": "1", "height": "34px"},
                                autoComplete="off",
                            ),
                            html.Div(
                                id="research-send-btn-wrapper",
                                style={"display": "flex"},
                                children=[
                                    html.Button(
                                        "Send",
                                        id="research-send-btn",
                                        className="btn-primary btn-sm",
                                        n_clicks=0,
                                    )
                                ],
                            ),
                        ],
                        className="research-input-row",
                    ),
                    # Hidden download/store infrastructure
                    dcc.Download(id="report-download"),
                    dcc.Store(id="report-cache-store", storage_type="session"),
                ],
                id="chatbot-window",
                className="chatbot-window-container",
                style={"display": "none"},  # Collapsed by default
            ),
        ],
        id="chatbot-widget-root",
        className="chatbot-widget-root",
    )
