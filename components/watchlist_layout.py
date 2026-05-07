# components/watchlist_layout.py
"""
components/watchlist_layout.py
==============================
Layout for the Watchlist page.
"""

from dash import dcc, html
import dash_mantine_components as dmc
from components.ui_helpers import chart_title, section

def create_watchlist_layout() -> html.Div:
    """
    Construct the watchlist page layout.
    """
    return html.Div(
        [
            # ── Page Header Row ───────────────────────────────────────────────
            html.Div(
                [
                    html.Div([
                        html.H1("Market Watchlist", className="header-title"),
                        html.P("Track potential purchases · Live pricing · Real-time metrics", className="header-subtitle"),
                    ], className="header-title-row"),
                    html.Div([
                        dmc.Button(
                            "Generate Signals",
                            id="watchlist-generate-signals-btn",
                            variant="light",
                            color="teal",
                            size="sm",
                            leftSection="🤖"
                        ),
                        dcc.Loading(
                            id="watchlist-loading-signals",
                            type="dot",
                            color="var(--t-pri)",
                            children=html.Span(
                                id="watchlist-signals-status-label",
                                style={"marginLeft": "10px", "fontSize": "11px", "color": "var(--t-sec)"}
                            )
                        )
                    ], style={"marginLeft": "auto", "display": "flex", "alignItems": "center", "gap": "8px"})
                ],
                className="page-header-row",
                style={"display": "flex"}
            ),

            # ── Add Ticker Row ────────────────────────────────────────────────
            html.Div(
                [
                    html.Div([
                        dmc.TextInput(
                            id="watchlist-input",
                            placeholder="Enter ticker (e.g. VAS, MQG)",
                            size="sm",
                            className="txn-input-text",
                            style={"width": "260px", "marginRight": "12px"}
                        ),
                        html.Button(
                            "Add to Watchlist",
                            id="watchlist-add-btn",
                            n_clicks=0,
                            className="btn-primary"
                        ),
                    ], style={"display": "flex", "alignItems": "center", "marginBottom": "16px"}),
                    html.P(id="watchlist-msg", className="txn-status-msg"),
                ],
                className="card-inset",
                style={"padding": "20px", "marginBottom": "24px"}
            ),

            # ── Main Content: Table & Chart ───────────────────────────────────
            html.Div(
                [
                    # Left: Table
                    html.Div(
                        [
                            chart_title("Watched Assets"),
                            html.Div(id="watchlist-table-container"),
                        ],
                        className="card-inset",
                        style={"flex": "1.5", "padding": "20px", "marginRight": "24px"}
                    ),

                    # Right: Chart
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Div(
                                        "Price Performance",
                                        id="watchlist-chart-title",
                                        className="chart-title-text",
                                    ),
                                    html.Div(
                                        [
                                            html.Button("1M", id={"type": "wl-period-btn", "index": "1mo"},
                                                        className="btn-sm", n_clicks=0),
                                            html.Button("6M", id={"type": "wl-period-btn", "index": "6mo"},
                                                        className="btn-sm", n_clicks=0),
                                            html.Button("1Y", id={"type": "wl-period-btn", "index": "1y"},
                                                        className="btn-sm", n_clicks=0),
                                            html.Button("5Y", id={"type": "wl-period-btn", "index": "5y"},
                                                        className="btn-sm", n_clicks=0),
                                            html.Button("Max", id={"type": "wl-period-btn", "index": "max"},
                                                        className="btn-sm", n_clicks=0),
                                        ],
                                        id="wl-period-btn-row",
                                        style={"display": "flex", "gap": "6px", "marginLeft": "auto"},
                                    ),
                                ],
                                style={"display": "flex", "alignItems": "center", 
                                       "marginBottom": "12px"},
                            ),
                            dcc.Graph(id="watchlist-chart", config={"displayModeBar": False}),
                            html.Div(
                                id="watchlist-stat-cards",
                                style={
                                    "display": "grid",
                                    "gridTemplateColumns": "repeat(4, 1fr)",
                                    "gap": "8px",
                                    "marginTop": "14px",
                                }
                            ),
                            html.Div([
                                html.P(
                                    "Research notes",
                                    style={"fontSize": "10px", "fontWeight": "600",
                                           "color": "var(--t-sec)", "textTransform": "uppercase",
                                           "letterSpacing": "0.5px", "margin": "14px 0 6px"}
                                ),
                                dmc.Textarea(
                                    id="watchlist-notes-input",
                                    placeholder="Add your research notes for this ticker...",
                                    minRows=3,
                                    style={"width": "100%", "fontSize": "12px"},
                                ),
                                html.Div([
                                    html.Button(
                                        "Save Note",
                                        id="watchlist-notes-save-btn",
                                        n_clicks=0,
                                        className="btn-sm btn-primary",
                                        style={"marginTop": "8px"}
                                    ),
                                    html.Span(
                                        id="watchlist-notes-msg",
                                        style={"fontSize": "11px", "color": "var(--t-sec)",
                                               "marginLeft": "10px"}
                                    ),
                                ], style={"display": "flex", "alignItems": "center"}),
                            ], style={"marginTop": "4px"}),
                        ],
                        className="card-inset",
                        style={"flex": "1", "padding": "20px"}
                    ),
                ],
                style={"display": "flex", "width": "100%"}
            ),
        ],
        className="page-root"
    )
