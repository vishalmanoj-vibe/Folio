# components/header.py
"""
components/header.py
====================
Global navigation bar for the Folio dashboard.
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
            ["Folio"], 
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
    settings_dropdown = dmc.Menu(
        [
            dmc.MenuTarget(
                html.Div(
                    html.Span("⚙", id="settings-icon-text"), 
                    className="settings-summary"
                )
            ),
            dmc.MenuDropdown(
                [
                    dmc.MenuLabel("Settings", style={"fontSize": "10px", "fontWeight": "700", "color": "var(--t-sec)", "textTransform": "uppercase"}),
                    dmc.MenuItem(
                        "Switch Theme",
                        id="theme-toggle",
                        leftSection=html.Span("☾", id="theme-icon-indicator"),
                        style={"fontSize": "11px"}
                    ),
                    dmc.MenuItem(
                        "Refresh Data",
                        id="refresh-btn",
                        leftSection=html.Span("↻"),
                        style={"fontSize": "11px"}
                    ),
                    dmc.MenuItem(
                        "Export PDF",
                        id="pdf-btn",
                        leftSection=html.Span("⬇"),
                        style={"fontSize": "11px"}
                    ),
                ],
                style={
                    "background": "var(--surface)",
                    "border": "0.5px solid var(--border)",
                    "borderRadius": "10px",
                    "boxShadow": "0 12px 32px rgba(0,0,0,0.45)",
                    "padding": "10px",
                    "minWidth": "175px"
                }
            ),
        ],
        trigger="click",
        position="bottom-end",
        offset=8,
        transitionProps={"transition": "fade", "duration": 150}
    )

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
