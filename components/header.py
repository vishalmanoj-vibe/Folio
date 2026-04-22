"""
components/header.py
====================
Global navigation bar for the Sovereign Ledger dashboard.
"""

from dash import html, dcc

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
        html.A("Overview",     href="/",             className="nav-link"),
        html.A("Positions",    href="/positions",    className="nav-link"),
        html.A("Analytics",    href="/analytics",    className="nav-link"),
        html.A("Intelligence", href="/intelligence", className="nav-link"),
        html.A("Dividends",    href="/dividends",    className="nav-link"),
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
            html.Span("☾", id="settings-icon-text"),
            className="settings-summary"
        ),
        html.Div([
            html.Button("☀ / ☾ Theme",   id="theme-toggle", n_clicks=0, className="btn-sm"),
            html.Button("↻ Refresh Data", id="refresh-btn",  n_clicks=0, className="btn-sm"),
            html.Button("⬇ Export PDF",   id="pdf-btn",      n_clicks=0, className="btn-sm"),
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
