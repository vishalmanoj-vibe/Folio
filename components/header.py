"""
components/header.py
====================
Shared header component for consistent navigation and UI controls.
"""

from dash import html, dcc

def create_header(
    title: str,
    subtitle: str = "",
    links_before: list[dict] | None = None,
    links_after: list[dict] | None = None,
    show_theme_toggle: bool = True,
    show_refresh: bool = True,
    show_pdf: bool = False,
    market_status: html.Div | None = None,
    last_updated: str | None = None,
) -> html.Div:
    """
    Standard header for all pages with static navigation support.
    """
    
    # ── Left side: Title & Nav ──────────────────────────────────────────────
    title_row = []
    
    # Links before title (e.g., Overview)
    if links_before:
        for link in links_before:
            title_row.append(
                html.A(link["label"], href=link["href"], className="nav-link", style={"marginRight": "12px"})
            )
            
    # Main Title
    title_row.append(
        html.H1(
            title,
            style={"margin": "0", "fontSize": "20px", "fontWeight": "500", "color": "var(--t-pri)"},
        )
    )
    
    # Links after title (e.g., Analytics, Intelligence)
    if links_after:
        for link in links_after:
            title_row.append(
                html.A(link["label"], href=link["href"], className="nav-link", style={"marginLeft": "12px"})
            )
            
    left_content = html.Div([
        html.Div(title_row, style={"display": "flex", "alignItems": "center", "flexWrap": "wrap"}),
        html.P(subtitle, style={"margin": "3px 0 0", "fontSize": "12px", "color": "var(--t-sec)"}) if subtitle else None,
    ])

    # ── Right side: Market Status & Settings ──────────────────────────────────
    right_items = []
    
    # Market Status (Badge)
    if market_status is not None:
        right_items.append(market_status)
        
    # Last updated
    if last_updated:
        right_items.append(
            html.Span(id="last-updated", children=last_updated, className="last-updated")
        )
    else:
        right_items.append(
            html.Span(id="last-updated", className="last-updated")
        )

    # Settings Menu
    controls = []
    if show_theme_toggle:
        controls.append(
            html.Button("☀ / ☾ Theme", id="theme-toggle", n_clicks=0, className="btn-sm")
        )
    if show_refresh:
        controls.append(
            html.Button("↻ Refresh Data", id="refresh-btn", n_clicks=0, className="btn-sm")
        )
    if show_pdf:
        controls.append(
            html.Button("⬇ Export PDF", id="pdf-btn", n_clicks=0, className="btn-sm")
        )
        
    settings_dropdown = html.Details([
        html.Summary(
            html.Span("☾", id="settings-icon-text"),
            className="settings-summary"
        ),
        html.Div(controls, className="settings-menu")
    ], className="settings-details")
    
    right_items.append(settings_dropdown)

    return html.Div(
        [
            left_content,
            html.Div(
                right_items,
                className="header-right",
                style={"display": "flex", "alignItems": "center", "gap": "16px"}
            ),
        ],
        className="page-header-row",
        style={
            "display": "flex", "justifyContent": "space-between",
            "alignItems": "center", "padding": "18px 24px 12px",
            "borderBottom": "0.5px solid var(--border)",
        },
    )
