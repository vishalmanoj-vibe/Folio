# components/header.py
"""
components/header.py
====================
Global navigation bar for the Folio dashboard.
"""

import dash_mantine_components as dmc
from dash import dcc, html


def create_header(
    market_status: html.Div | None = None,
    last_updated: str | None = None,
) -> html.Div:
    """
    Renders the global navigation bar.
    """

    # ── Left: Logo & Links ──────────────────────────────────────────────────
    nav_left = [
        html.Div(["Folio"], className="nav-logo"),
        html.Div(
            [
                html.A("Holdings", href="/", className="nav-link"),
                html.A("Positions", href="/positions", className="nav-link"),
                html.A("Watchlist", href="/watchlist", className="nav-link"),
                html.Div(
                    [
                        html.A("Insights", href="/intelligence", className="nav-link"),
                        html.Span(
                            id="intel-alert-count", className="nav-badge", style={"display": "none"}
                        ),
                    ],
                    style={"display": "flex", "alignItems": "center", "position": "relative"},
                ),
                html.A("Deep Dive", href="/analytics", className="nav-link"),
                html.A("Assistant", href="/ai-analyst", className="nav-link"),
            ],
            className="nav-links-container",
        ),
    ]

    # ── Right: Status & Settings ─────────────────────────────────────────────

    # Last updated chip
    last_updated_chip = html.Span(
        id="last-updated",
        children=[
            html.Div(id="status-indicator-dot", className="pulse-dot"),
            html.Span(last_updated if last_updated else "", id="last-updated-text"),
        ],
        className="last-updated",
    )

    # Settings Menu
    settings_dropdown = dmc.Menu(
        [
            dmc.MenuTarget(
                html.Div(html.Span("⚙", id="settings-icon-text"), className="settings-summary")
            ),
            dmc.MenuDropdown(
                [
                    dmc.MenuLabel(
                        "Settings",
                        style={
                            "fontSize": "10px",
                            "fontWeight": "700",
                            "color": "var(--t-sec)",
                            "textTransform": "uppercase",
                        },
                    ),
                    dmc.MenuItem(
                        "Switch Theme",
                        id="theme-toggle",
                        leftSection=html.Span("☾", id="theme-icon-indicator"),
                        style={"fontSize": "11px"},
                    ),
                    dmc.MenuItem(
                        "Refresh Data",
                        id="refresh-btn",
                        leftSection=html.Span("↻"),
                        style={"fontSize": "11px"},
                    ),
                    dmc.MenuItem(
                        "Export PDF",
                        id="pdf-btn",
                        leftSection=html.Span("⬇"),
                        style={"fontSize": "11px"},
                    ),
                ],
                style={
                    "background": "var(--surface)",
                    "border": "0.5px solid var(--border)",
                    "borderRadius": "10px",
                    "boxShadow": "0 12px 32px rgba(0,0,0,0.45)",
                    "padding": "10px",
                    "minWidth": "175px",
                },
            ),
        ],
        trigger="click",
        position="bottom-end",
        offset=8,
        transitionProps={"transition": "fade", "duration": 150},
    )

    # Intelligence Action (Consolidated Button + Status Box)
    intelligence_action = html.Div(
        id="signals-updated-chip",
        children=[
            dmc.Tooltip(
                label="Refresh All Signals (Portfolio & Watchlist)",
                position="bottom",
                withArrow=True,
                children=dmc.ActionIcon(
                    "🤖",
                    id="global-generate-signals-btn",
                    variant="subtle",
                    color="cyan",
                    size="md",
                    radius="md",
                    style={"height": "20px", "width": "20px", "fontSize": "14px"},
                ),
            ),
            dcc.Loading(
                id="global-loading-signals",
                type="dot",
                color="var(--cyan)",
                children=html.Span(
                    id="global-signals-status-label",
                    style={
                        "fontSize": "10px",
                        "color": "var(--t-sec)",
                        "whiteSpace": "nowrap",
                        "marginLeft": "2px",
                    },
                ),
            ),
        ],
        className="last-updated",
        style={
            "marginLeft": "4px",
            "padding": "2px 8px",
            "border": "0.5px solid rgba(0, 255, 255, 0.15)",
            "gap": "6px",
        },
    )

    nav_right = html.Div(
        [
            html.Div(id="market-status", children=market_status)
            if market_status
            else html.Div(id="market-status"),
            last_updated_chip,
            intelligence_action,
            settings_dropdown,
        ],
        className="nav-right",
    )

    return html.Div([*nav_left, nav_right], className="nav-bar")
