import dash
from dash import html, dcc
import dash_mantine_components as dmc

dash.register_page(
    __name__,
    path="/reports",
    title="Reports"
)

def layout():
    return html.Div([
        
        # Page header
        html.Div([
            html.Div([
                html.H1(
                    "Weekly Reports",
                    className="header-title"
                ),
                html.P(
                    "AI-generated portfolio summary with market news",
                    className="header-subtitle"
                ),
            ], className="header-title-row"),
        ], className="page-header-row"),
        
        # Main content
        html.Div([
            
            # Report controls card
            html.Div([
                html.Div([
                    html.Div([
                        html.H3(
                            "Generate Report",
                            style={
                                "fontSize": "14px",
                                "fontWeight": "500",
                                "color": "var(--t-pri)",
                                "margin": "0 0 4px"
                            }
                        ),
                        html.P(
                            "Generates a PDF with your "
                            "portfolio summary, technical "
                            "signals, dividend calendar, "
                            "AI market commentary, and "
                            "recent ASX news.",
                            style={
                                "fontSize": "12px",
                                "color": "var(--t-sec)",
                                "margin": "0"
                            }
                        ),
                    ]),
                    html.Button(
                        "Generate Weekly Report",
                        id="generate-report-btn",
                        n_clicks=0,
                        className="btn-primary",
                        style={
                            "height": "38px",
                            "padding": "0 20px",
                            "fontSize": "13px",
                            "flexShrink": "0",
                        }
                    ),
                ], style={
                    "display": "flex",
                    "justifyContent": "space-between",
                    "alignItems": "center",
                    "gap": "20px",
                }),
                
                # Status message
                dcc.Loading(
                    html.Div(
                        id="report-status-msg",
                        style={
                            "marginTop": "12px",
                            "fontSize": "12px",
                            "color": "var(--t-sec)",
                            "minHeight": "20px",
                        }
                    ),
                    type="circle",
                    color="var(--cyan)",
                ),
                
                # Auto-generation note
                html.Div([
                    html.Span(
                        "Auto-generates every Monday",
                        style={
                            "fontSize": "10px",
                            "color": "var(--t-muted)",
                        }
                    ),
                    html.Span(
                        id="last-report-date",
                        style={
                            "fontSize": "10px",
                            "color": "var(--t-muted)",
                            "marginLeft": "12px",
                        }
                    ),
                ], style={"marginTop": "8px"}),
                
            ], className="card",
               style={"marginBottom": "16px"}),
            
            # Download area
            html.Div(
                id="report-download-area",
                style={"display": "none"},
                children=[
                    html.Div([
                        html.Span(
                            "✓ Report ready",
                            style={
                                "color": "var(--green)",
                                "fontWeight": "500",
                                "fontSize": "13px",
                            }
                        ),
                        html.Button(
                            "Download PDF Report →",
                            id="report-pdf-link",
                            style={
                                "color": "var(--cyan)",
                                "fontSize": "13px",
                                "marginLeft": "16px",
                                "background": "none",
                                "border": "none",
                                "padding": "0",
                                "cursor": "pointer",
                                "textDecoration": "underline",
                            }
                        ),
                    ], style={
                        "display": "flex",
                        "alignItems": "center",
                        "padding": "12px 16px",
                        "background": "var(--surface-2)",
                        "border": "0.5px solid var(--green)",
                        "borderRadius": "8px",
                    }),
                ]
            ),
            
            # Report preview info
            html.Div([
                html.P(
                    "Report Contents",
                    style={
                        "fontSize": "11px",
                        "fontWeight": "600",
                        "color": "var(--t-sec)",
                        "textTransform": "uppercase",
                        "letterSpacing": "0.5px",
                        "margin": "0 0 10px"
                    }
                ),
                html.Div([
                    html.Div(
                        label,
                        style={
                            "fontSize": "12px",
                            "color": "var(--t-sec)",
                            "padding": "6px 0",
                            "borderBottom":
                                "0.5px solid var(--border)",
                        }
                    )
                    for label in [
                        "📊  Portfolio summary — "
                        "total value, P&L, top/worst performer",
                        "📈  Holdings breakdown — "
                        "weight, RSI, MACD, dividend yield",
                        "💰  Dividend calendar — "
                        "upcoming payments in next 30 days",
                        "🤖  AI market commentary — "
                        "written by Gemini based on your data",
                        "📰  Recent ASX news — "
                        "per holding from web search",
                        "⚠️   Disclaimer footer",
                    ]
                ]),
            ], className="card",
               style={"marginTop": "16px"}),
            
            # Hidden download component
            dcc.Download(id="report-download"),
            
            # Store for report cache
            dcc.Store(
                id="report-cache-store",
                storage_type="session"
            ),
            
        ], className="page-container"),
        
    ], className="page-root")
