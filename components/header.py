# components/header.py
"""
components/header.py
====================
Global navigation bar for the Sovereign Ledger dashboard.
"""

from dash import html, dcc
import dash_mantine_components as dmc

def create_header(
    market_status: html.Div | None = None,
    last_updated: str | None = None,
) -> html.Div:
    """
    Renders the global navigation bar.
    """
    
    # ── Left: Logo & Links ──────────────────────────────────────────────────
    nav_left = [
        html.Div(
            ["Portfolio"], 
            className="nav-logo"
        ),
        html.Div([
            html.A("Overview",     href="/",             className="nav-link"),
            html.A("Positions",    href="/positions",    className="nav-link"),
            html.A("Watchlist",    href="/watchlist",    className="nav-link"),
            html.Div([
                html.A("Intelligence", href="/intelligence", className="nav-link"),
                html.Span(id="intel-alert-count", className="nav-badge", style={"display": "none"})
            ], style={"display": "flex", "alignItems": "center", "position": "relative"}),
            html.A("Dividends",    href="/dividends",    className="nav-link"),
            html.A("Analytics",    href="/analytics",    className="nav-link"),
            html.A("AI Analyst",   href="/ai-analyst",   className="nav-link"),
        ], className="nav-links-container")
    ]

    # ── Right: Status & Settings ─────────────────────────────────────────────
    
    # Last updated chip
    last_updated_chip = html.Span(
        id="last-updated", 
        children=last_updated if last_updated else "", 
        className="last-updated"
    )

    # Settings Menu
    settings_dropdown = html.Details([
        html.Summary(
            html.Span("⚙", id="settings-icon-text"), # Settings gear
            className="settings-summary"
        ),
        html.Div([
            html.Div("Settings", style={"fontSize": "10px", "fontWeight": "700", "color": "var(--t-sec)", "marginBottom": "8px", "textTransform": "uppercase"}),
            html.Button([
                html.Span("☾", id="theme-icon-indicator", style={"marginRight": "8px"}),
                "Switch Theme"
            ], id="theme-toggle", n_clicks=0, className="btn-sm", style={"width": "100%", "justifyContent": "flex-start"}),
            html.Button("↻ Refresh Data", id="refresh-btn",  n_clicks=0, className="btn-sm", style={"width": "100%", "justifyContent": "flex-start"}),
            html.Button("⬇ Export PDF",   id="pdf-btn",      n_clicks=0, className="btn-sm", style={"width": "100%", "justifyContent": "flex-start"}),
        ], className="settings-menu")
    ], className="settings-details")

    nav_right = html.Div([
        html.Div(id="market-status", children=market_status) if market_status else html.Div(id="market-status"),
        last_updated_chip,
        settings_dropdown
    ], className="nav-right")

    return html.Div(
        [
            *nav_left,
            nav_right
        ],
        className="nav-bar"
    )
