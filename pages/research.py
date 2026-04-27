import dash
from dash import html, dcc
import dash_mantine_components as dmc
from components.ui_helpers import section, chart_title

dash.register_page(__name__, path="/research", title="Research")

def layout():
    return html.Div([
        # 1. Page header row
        html.Div([
            html.H1("Research Assistant", className="header-title"),
            html.P("AI-powered portfolio analysis · Not financial advice", className="header-subtitle"),
        ], className="page-header-row"),
        
        # 2. Research layout
        html.Div([
            
            # LEFT PANEL
            html.Div([
                html.P("Your Portfolio", className="research-context-heading"),
                html.Div(id="research-portfolio-summary"),
                html.Hr(style={"borderColor": "var(--border)", "margin": "14px 0"}),
                html.P("Research a Ticker", className="research-context-heading"),
                dmc.TextInput(
                    id="research-ticker-input",
                    placeholder="e.g. XMET, VAS, NDQ",
                    debounce=True,
                    size="sm",
                    style={"width": "100%"}
                ),
                html.P(
                    "Responses are AI-generated and not financial advice. Always verify with a licensed adviser.",
                    id="research-disclaimer",
                    className="research-disclaimer"
                )
            ], className="research-context-panel"),
            
            # RIGHT PANEL
            html.Div([
                html.Div(id="research-chat-display", className="research-chat-display"),
                html.Div(
                    id="research-typing-indicator",
                    className="research-typing-indicator",
                    style={"display": "none"},
                    children=[
                        html.Span("●", style={"animationDelay": "0s"}),
                        html.Span("●", style={"animationDelay": "0.2s"}),
                        html.Span("●", style={"animationDelay": "0.4s"}),
                    ]
                ),

                html.Div(
                    id="research-usage-display",
                    className="research-usage-display",
                ),

                html.Div([
                    html.Button("Does this fit my portfolio?", id="qp-1", className="quick-prompt-chip btn-sm", n_clicks=0),
                    html.Button("What are the risks?", id="qp-2", className="quick-prompt-chip btn-sm", n_clicks=0),
                    html.Button("Compare to what I own", id="qp-3", className="quick-prompt-chip btn-sm", n_clicks=0),
                    html.Button("What am I missing?", id="qp-4", className="quick-prompt-chip btn-sm", n_clicks=0),
                ], className="quick-prompt-chips"),

                html.Div([
                    dcc.Input(
                        id="research-input",
                        type="text",
                        placeholder="Ask anything about your portfolio or a ticker...",
                        className="mantine-TextInput-input",
                        style={"flex": "1", "height": "34px"},
                        debounce=False,
                        autoComplete="off"
                    ),
                    html.Div(
                        id="research-send-btn-wrapper",
                        style={"display": "flex"},
                        children=[
                            html.Button(
                                "Send",
                                id="research-send-btn",
                                className="btn-primary btn-sm",
                                n_clicks=0
                            )
                        ]
                    )
                ], className="research-input-row")

            ], className="research-chat-panel")
            
        ], className="research-layout")
        
    ], className="page-root")
