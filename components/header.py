"""
components/header.py
====================
Shared header component for consistent navigation and UI controls.
"""

from dash import html, dcc

def create_header(
    title: str,
    subtitle: str = "",
    nav_links: list[dict] | None = None,
    show_theme_toggle: bool = True,
    show_refresh: bool = True,
    show_pdf: bool = False,
    market_status: html.Div | None = None,
    last_updated: str | None = None,
    back_link: dict | None = None,
) -> html.Div:
    """
    Standard header for all pages.
    """
    
    # ── Left side: Title & Nav ──────────────────────────────────────────────
    left_children = []
    
    if back_link:
        left_children.append(
            html.A(back_link["label"], href=back_link["href"], className="back-link", style={"marginRight": "12px"})
        )
        
    title_row = [
        html.H1(
            title,
            style={"margin": "0", "fontSize": "20px", "fontWeight": "500", "color": "var(--t-pri)"},
        )
    ]
    
    if nav_links:
        for link in nav_links:
            title_row.append(
                html.A(link["label"], href=link["href"], className="nav-link", style={"marginLeft": "12px"})
            )
            
    left_children.append(
        html.Div([
            html.Div(title_row, style={"display": "flex", "alignItems": "center", "flexWrap": "wrap"}),
            html.P(subtitle, style={"margin": "3px 0 0", "fontSize": "12px", "color": "var(--t-sec)"}) if subtitle else None,
        ])
    )

    # ── Right side: Controls ──────────────────────────────────────────────
    right_children = []
    
    if market_status is not None:
        right_children.append(market_status)
        
    if last_updated:
        right_children.append(
            html.Span(id="last-updated", children=last_updated, style={"fontSize": "12px", "color": "var(--t-sec)"})
        )
    else:
        # Placeholder for callback-driven updates
        right_children.append(
            html.Span(id="last-updated", style={"fontSize": "12px", "color": "var(--t-sec)"})
        )

    controls = []
    if show_theme_toggle:
        controls.append(
            html.Button("☀ / ☾", id="theme-toggle", n_clicks=0, className="btn-sm")
        )
    if show_refresh:
        controls.append(
            html.Button("Refresh now", id="refresh-btn", n_clicks=0, className="btn-sm")
        )
    if show_pdf:
        controls.append(
            html.Button("⬇ PDF", id="pdf-btn", n_clicks=0, className="btn-sm")
        )
        
    right_children.append(
        html.Div(controls, style={"display": "flex", "gap": "8px", "marginTop": "8px"})
    )

    return html.Div(
        [
            html.Div(left_children, style={"display": "flex", "alignItems": "center"}),
            html.Div(
                right_children,
                style={"display": "flex", "flexDirection": "column", "alignItems": "flex-end", "gap": "6px"}
            ),
        ],
        className="page-header-row",
        style={
            "display": "flex", "justifyContent": "space-between",
            "alignItems": "flex-start", "padding": "18px 24px 12px",
            "borderBottom": "0.5px solid var(--border)",
        },
    )
