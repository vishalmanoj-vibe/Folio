"""
pages/etf_detail.py
====================
ETF detail drill-down page.
Route: /etf/<ticker>   e.g. /etf/VHY

Bug fixes in this version
--------------------------
1. LIGHT MODE  — All background/surface/border/text colours now use CSS
                 variables (var(--bg), var(--surface), etc.) instead of
                 hardcoded dark hex values, so the theme toggle works.

2. PERIOD FILTER — Selected period is stored in `dcc.Store` ("etf-period-store")
                   and written by a separate clientside callback.  The chart
                   callback reads from that store, not from button n_clicks
                   (which all start at 0 and can't be disambiguated on first
                   render or after a page reload).

3. DIVIDENDS    — `hist.get("Dividends")` fails on a DataFrame (no .get()).
                 Fixed to `hist["Dividends"] if "Dividends" in hist.columns`.
                 Also uses the tranche data already in portfolio-store instead
                 of re-fetching, so the cards always have data.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import yfinance as yf
from dash import ALL, ClientsideFunction, Input, Output, State, dcc, html, register_page

from config.constants import (
    BG, SURFACE, BORDER, GREEN, RED, T_PRI, T_SEC, COLORS, PLOTLY_BASE, NAMES
)
from services.market.status import market_badge

# ── Register page ─────────────────────────────────────────────────────────────
register_page(__name__, path_template="/etf/<ticker>", title="ETF Detail")

# ── Period filter options ─────────────────────────────────────────────────────
PERIOD_OPTIONS = [
    {"label": "Since purchase", "value": "purchase"},
    {"label": "1M",  "value": "1mo"},
    {"label": "3M",  "value": "3mo"},
    {"label": "6M",  "value": "6mo"},
    {"label": "1Y",  "value": "1y"},
    {"label": "MAX", "value": "max"},
]
DEFAULT_PERIOD = "3mo"

# ── CSS-variable style tokens (theme-aware) ───────────────────────────────────
# Use CSS vars everywhere so dark/light toggle works without Python re-render.
_SECTION = {
    "padding":      "20px 24px",
    "borderBottom": "0.5px solid var(--border)",
}
_CARD = {
    "background":   "var(--surface)",
    "borderRadius": "10px",
    "padding":      "16px 20px",
    "flex":         "1",
    "minWidth":     "140px",
}
_TH = {
    "fontSize": "11px", "color": "var(--t-sec)", "fontWeight": "500",
    "padding": "7px 12px", "borderBottom": "1px solid var(--border)",
    "backgroundColor": "var(--surface)", "textAlign": "left",
    "whiteSpace": "nowrap",
}
_TD = {
    "fontSize": "13px", "padding": "8px 12px",
    "borderBottom": "0.5px solid var(--border)", "whiteSpace": "nowrap",
    "color": "var(--t-pri)",
}


# ── Small stat card ────────────────────────────────────────────────────────────
def _card(label: str, value: str, sub: str | None = None,
          color: str = "var(--t-pri)", sub_color: str = "var(--t-sec)") -> html.Div:
    children: list = [
        html.P(label, style={"fontSize": "11px", "color": "var(--t-sec)",
                              "margin": "0 0 4px"}),
        html.P(value, style={"fontSize": "20px", "fontWeight": "500",
                              "margin": "0", "color": color}),
    ]
    if sub:
        children.append(
            html.P(sub, style={"fontSize": "11px", "color": sub_color,
                                "margin": "3px 0 0"})
        )
    return html.Div(children, style=_CARD)


# ── Layout factory ────────────────────────────────────────────────────────────
def layout(ticker: str = "") -> html.Div:
    ticker = ticker.upper()
    name   = NAMES.get(ticker, ticker)

    return html.Div(
        [
            # Hidden stores
            dcc.Store(id="etf-ticker-store", data=ticker),
            dcc.Store(id="etf-period-store", data=DEFAULT_PERIOD, storage_type="session"),

            # ── A. Header ─────────────────────────────────────────────────────
            html.Div(
                [
                    html.Div([
                        html.A(
                            "← Portfolio",
                            href="/",
                            style={
                                "fontSize": "12px",
                                "color": "var(--t-sec)",
                                "textDecoration": "none",
                                "display": "inline-block",
                                "marginBottom": "8px",
                                "letterSpacing": "0.02em",
                            },
                        ),
                        html.Div(
                            [
                                html.Span(
                                    ticker,
                                    style={
                                        "fontSize":      "22px",
                                        "fontWeight":    "600",
                                        "background":    "var(--surface)",
                                        "border":        "1px solid var(--border)",
                                        "borderRadius":  "6px",
                                        "padding":       "2px 10px",
                                        "marginRight":   "12px",
                                        "letterSpacing": "0.04em",
                                        "color":         "var(--t-pri)",
                                    },
                                ),
                                html.Span(
                                    name,
                                    style={
                                        "fontSize":   "18px",
                                        "fontWeight": "400",
                                        "color":      "var(--t-sec)",
                                    },
                                ),
                            ],
                            style={"display": "flex", "alignItems": "center",
                                   "flexWrap": "wrap", "gap": "4px"},
                        ),
                    ]),
                    html.Div([
                        html.Div(id="etf-market-status", style={"marginBottom": "8px", "textAlign": "right"}),
                        html.Button(
                            "Refresh now", id="refresh-btn", n_clicks=0,
                            style={"fontWeight": "500", "fontSize": "12px", "padding": "4px 10px", "float": "right"},
                        ),
                    ]),
                ],
                style={
                    "display": "flex", "justifyContent": "space-between",
                    "alignItems": "flex-start",
                    "padding": "18px 24px 14px",
                    "borderBottom": "0.5px solid var(--border)",
                },
            ),

            # ── B. Price chart ────────────────────────────────────────────────
            html.Div(
                [
                    html.Div(
                        [
                            html.Span("Price chart",
                                      style={"fontSize": "13px", "fontWeight": "500",
                                             "color": "var(--t-pri)"}),
                            # Period filter buttons
                            html.Div(
                                id="etf-period-btns",
                                children=_period_buttons(DEFAULT_PERIOD),
                                style={"display": "flex", "gap": "6px",
                                       "flexWrap": "wrap"},
                            ),
                        ],
                        style={
                            "display": "flex", "justifyContent": "space-between",
                            "alignItems": "center", "marginBottom": "10px",
                            "flexWrap": "wrap", "gap": "10px",
                        },
                    ),
                    dcc.Loading(
                        dcc.Graph(id="etf-price-chart",
                                  config={"displayModeBar": False}),
                        type="circle",
                        color=COLORS[0],
                    ),
                ],
                style=_SECTION,
            ),

            # ── C. Position summary ───────────────────────────────────────────
            html.Div(
                [
                    html.Span("Position summary",
                              style={"fontSize": "13px", "fontWeight": "500",
                                     "display": "block", "marginBottom": "12px",
                                     "color": "var(--t-pri)"}),
                    html.Div(id="etf-position-cards",
                             style={"display": "flex", "gap": "10px",
                                    "flexWrap": "wrap"}),
                ],
                style=_SECTION,
            ),

            # ── D. Transaction table ──────────────────────────────────────────
            html.Div(
                [
                    html.Span("Transactions",
                              style={"fontSize": "13px", "fontWeight": "500",
                                     "display": "block", "marginBottom": "12px",
                                     "color": "var(--t-pri)"}),
                    html.Div(id="etf-txn-table", style={"overflowX": "auto"}),
                ],
                style=_SECTION,
            ),

            # ── E. Dividend section ───────────────────────────────────────────
            html.Div(
                [
                    html.Span("Dividends",
                              style={"fontSize": "13px", "fontWeight": "500",
                                     "display": "block", "marginBottom": "12px",
                                     "color": "var(--t-pri)"}),
                    html.Div(id="etf-dividend-cards",
                             style={"display": "flex", "gap": "10px",
                                    "flexWrap": "wrap", "marginBottom": "16px"}),
                    dcc.Loading(
                        dcc.Graph(id="etf-dividend-chart",
                                  config={"displayModeBar": False},
                                  style={"height": "260px"}),
                        type="circle",
                        color=COLORS[1],
                    ),
                ],
                style={**_SECTION, "borderBottom": "none"},
            ),
        ],
        # Use CSS vars for the outer wrapper too
        style={
            "backgroundColor": "var(--bg)",
            "color":           "var(--t-pri)",
            "minHeight":       "100vh",
        },
    )


# ── Period button renderer (also called from callback to update active state) ─
def _period_buttons(active: str) -> list:
    buttons = []
    for opt in PERIOD_OPTIONS:
        is_active = opt["value"] == active
        buttons.append(
            html.Button(
                opt["label"],
                id={"type": "etf-period-btn", "index": opt["value"]},
                n_clicks=0,
                style={
                    "fontSize":       "12px",
                    "padding":        "3px 12px",
                    "borderRadius":   "20px",
                    "cursor":         "pointer",
                    "fontWeight":     "500",
                    # Active button gets a solid accent border; inactive is muted
                    "background":     COLORS[0] if is_active else "var(--surface)",
                    "border":         f"1px solid {COLORS[0]}" if is_active
                                      else "1px solid var(--border)",
                    "color":          "#ffffff" if is_active else "var(--t-pri)",
                },
            )
        )
    return buttons


# ── Plotly layout base using CSS-var-aware colours ────────────────────────────
# Charts use the dark constants from config for paper/plot bg (Plotly doesn't
# read CSS vars). We keep the dark values here — charts look fine in both
# themes since they're canvas-rendered. Only the surrounding HTML needs vars.
_CHART_LAYOUT = dict(
    paper_bgcolor=BG,
    plot_bgcolor=SURFACE,
    font=dict(family="system-ui,sans-serif", color=T_PRI, size=13),
    margin=dict(l=16, r=16, t=40, b=16),
    legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0),
    uirevision=True,  # Preserve state across auto-refreshes
)


# ── Callbacks ─────────────────────────────────────────────────────────────────
def register_callbacks(app) -> None:

    # ── Market badge ──────────────────────────────────────────────────────────
    @app.callback(
        Output("etf-market-status", "children"),
        Input("live-interval",      "n_intervals"),
    )
    def etf_market_badge(_):
        return market_badge()

    # ── Period store + button highlight ──────────────────────────────────────
    # One callback: clicking any period button writes to the store AND
    # re-renders the buttons so the active one is highlighted.
    @app.callback(
        Output("etf-period-store", "data"),
        Output("etf-period-btns",  "children"),
        Input({"type": "etf-period-btn", "index": ALL}, "n_clicks"),
        State({"type": "etf-period-btn", "index": ALL}, "id"),
        State("etf-period-store", "data"),
        prevent_initial_call=True,
    )
    def update_period(n_clicks_list, btn_ids, current_period):
        # Find which button was actually clicked (n_clicks just incremented)
        from dash import ctx
        if not ctx.triggered_id:
            return current_period, _period_buttons(current_period)
        clicked = ctx.triggered_id["index"]
        return clicked, _period_buttons(clicked)

    # ── Price chart ───────────────────────────────────────────────────────────
    @app.callback(
        Output("etf-price-chart", "figure"),
        Input("etf-ticker-store", "data"),
        Input("etf-period-store", "data"),
        Input("portfolio-store",  "data"),
    )
    def etf_price_chart(ticker, selected_period, port_data):
        fig = go.Figure()
        fig.update_layout(
            xaxis=dict(showgrid=False, rangeslider_visible=False),
            yaxis=dict(gridcolor=BORDER, tickprefix="$"),
            hovermode="x unified",
            height=380,
            **_CHART_LAYOUT,
        )

        if not ticker:
            return fig

        # Resolve first-purchase date and holding details from store
        first_purchase = None
        holding        = None
        if port_data and "holdings" in port_data:
            holding = next(
                (h for h in port_data["holdings"] if h["ticker"] == ticker), None
            )
            if holding:
                first_purchase = holding.get("first_purchase")

        ticker_yf = ticker + ".AX"
        try:
            tk = yf.Ticker(ticker_yf)
            if selected_period == "purchase" and first_purchase:
                df = tk.history(start=first_purchase)
            else:
                df = tk.history(period=selected_period)
        except Exception as exc:
            fig.add_annotation(
                text=f"Could not load price data: {exc}",
                showarrow=False, font=dict(color=T_SEC, size=12),
            )
            return fig

        if df.empty:
            fig.add_annotation(
                text="No price history for this period",
                showarrow=False, font=dict(color=T_SEC, size=13),
            )
            return fig

        # Normalise timezone
        if df.index.tz is not None:
            df.index = df.index.tz_convert(None)
        dates = df.index.strftime("%Y-%m-%d").tolist()

        # Candlestick
        fig.add_trace(go.Candlestick(
            x=dates,
            open=df["Open"].round(3).tolist(),
            high=df["High"].round(3).tolist(),
            low=df["Low"].round(3).tolist(),
            close=df["Close"].round(3).tolist(),
            name=ticker,
            increasing_line_color=GREEN,
            decreasing_line_color=RED,
            increasing_fillcolor=GREEN,
            decreasing_fillcolor=RED,
            line=dict(width=1),
        ))

        # Dotted avg-cost reference line
        if holding and holding.get("avg_cost"):
            fig.add_hline(
                y=holding["avg_cost"],
                line_dash="dot",
                line_color="rgba(255,255,255,0.30)",
                annotation_text=f"Avg cost  ${holding['avg_cost']:,.4f}",
                annotation_font_size=10,
                annotation_font_color=T_SEC,
                annotation_position="top left",
            )

        return fig

    # ── Position summary cards ────────────────────────────────────────────────
    @app.callback(
        Output("etf-position-cards", "children"),
        Input("etf-ticker-store",    "data"),
        Input("portfolio-store",     "data"),
    )
    def etf_position_cards(ticker, port_data):
        if not ticker or not port_data or "holdings" not in port_data:
            return html.P("Loading…",
                          style={"color": "var(--t-sec)", "fontSize": "13px"})

        h = next((x for x in port_data["holdings"] if x["ticker"] == ticker), None)
        if not h:
            return html.P(f"No active position for {ticker}.",
                          style={"color": "var(--t-sec)", "fontSize": "13px"})

        pnl     = h["pnl"];   psgn = "+" if pnl     >= 0 else ""; pc = GREEN if pnl     >= 0 else RED
        day_pnl = h["day_pnl"]; dsgn = "+" if day_pnl >= 0 else ""; dc = GREEN if day_pnl >= 0 else RED

        return [
            _card("Total invested",  f"${h['total_cost']:,.2f}"),
            _card("Current value",   f"${h['mkt_value']:,.2f}",
                  f"{h['total_shares']} shares @ ${h['last_price']:,.3f}"),
            _card("Unrealised P&L",
                  f"{psgn}${pnl:,.2f}",
                  f"{psgn}{h['pnl_pct']:.2f}%  all time", pc, pc),
            _card("Today's P&L",
                  f"{dsgn}${day_pnl:,.2f}",
                  f"{dsgn}{h['day_chg_pct']:.2f}%  today", dc, dc),
            _card("Avg cost",    f"${h['avg_cost']:,.4f}"),
            _card("Last price",  f"${h['last_price']:,.3f}",
                  f"H ${h['day_high']:,.3f}  /  L ${h['day_low']:,.3f}"),
        ]

    # ── Transaction table ─────────────────────────────────────────────────────
    @app.callback(
        Output("etf-txn-table",   "children"),
        Input("etf-ticker-store", "data"),
        Input("txn-store",        "data"),
    )
    def etf_txn_table(ticker, history):
        if not ticker or not history:
            return html.P("No transactions.",
                          style={"color": "var(--t-sec)", "fontSize": "13px"})

        rows_data = [t for t in history if t.get("ticker", "").upper() == ticker]
        if not rows_data:
            return html.P(f"No transactions found for {ticker}.",
                          style={"color": "var(--t-sec)", "fontSize": "13px"})

        rows          = []
        running_shares = 0.0
        running_cost   = 0.0

        for t in sorted(rows_data, key=lambda r: r["date"]):
            shares = float(t["shares"])
            price  = float(t["price"])
            total  = shares * price
            is_buy = t["type"] == "buy"
            tc     = GREEN if is_buy else RED

            if is_buy:
                running_shares += shares
                running_cost   += total
            else:
                if running_shares > 0:
                    running_cost -= shares * (running_cost / running_shares)
                running_shares -= shares

            rows.append(html.Tr([
                html.Td(t["date"],         style=_TD),
                html.Td(t["type"].upper(), style={**_TD, "color": tc,
                                                  "fontWeight": "600"}),
                html.Td(f"{shares:g}",     style=_TD),
                html.Td(f"${price:,.4f}",  style=_TD),
                html.Td(f"${total:,.2f}",  style=_TD),
                html.Td(f"{max(running_shares, 0):g}",
                        style={**_TD, "color": "var(--t-sec)"}),
                html.Td(f"${max(running_cost, 0):,.2f}",
                        style={**_TD, "color": "var(--t-sec)"}),
            ]))

        return html.Div(
            html.Table(
                [
                    html.Thead(html.Tr([
                        html.Th(c, style=_TH)
                        for c in ["Date", "Type", "Shares", "Price",
                                  "Total value", "Running shares",
                                  "Running cost basis"]
                    ])),
                    html.Tbody(rows),
                ],
                style={"width": "100%", "borderCollapse": "collapse"},
            ),
            style={
                "borderRadius": "8px",
                "border":       "0.5px solid var(--border)",
                "overflowX":    "auto",
            },
        )

    # ── Dividend cards + per-year bar chart ───────────────────────────────────
    @app.callback(
        Output("etf-dividend-cards", "children"),
        Output("etf-dividend-chart", "figure"),
        Input("etf-ticker-store",    "data"),
        Input("portfolio-store",     "data"),
    )
    def etf_dividends(ticker, port_data):
        empty_fig = go.Figure()
        empty_fig.update_layout(
            **_CHART_LAYOUT, height=240,
            annotations=[dict(
                text="No dividend history available",
                showarrow=False, font=dict(color=T_SEC, size=13),
            )],
        )

        if not ticker or not port_data or "holdings" not in port_data:
            return [], empty_fig

        h = next((x for x in port_data["holdings"] if x["ticker"] == ticker), None)
        if not h:
            return [], empty_fig

        annual_div = h.get("annual_div", 0)
        div_yield  = h.get("div_yield",  0)
        total_div  = h.get("total_div",  0)

        cards = [
            _card("Annual income",
                  f"${annual_div:,.2f}",
                  "estimated · last 12 months",
                  GREEN if annual_div > 0 else "var(--t-pri)", "var(--t-sec)"),
            _card("Dividend yield",
                  f"{div_yield:.2f}%",
                  "annual income ÷ current value",
                  GREEN if div_yield > 0 else "var(--t-pri)", "var(--t-sec)"),
            _card("Total received",
                  f"${total_div:,.2f}",
                  "all time since first purchase"),
        ]

        # Per-year bar chart — fetch dividend history from yfinance
        try:
            tk   = yf.Ticker(ticker + ".AX")
            hist = tk.history(period="max")

            # FIX: DataFrame has no .get() — use column existence check
            if hist.empty or "Dividends" not in hist.columns:
                return cards, empty_fig

            div_s = hist["Dividends"]
            div_s = div_s[div_s > 0]

            if div_s.empty:
                return cards, empty_fig

            # Normalise timezone
            if div_s.index.tz is not None:
                div_s.index = div_s.index.tz_convert(None)

            # Scale per-share dividend to our share count
            div_s   = div_s * float(h.get("total_shares", 1))
            by_year = div_s.groupby(div_s.index.year).sum().round(2)
            years   = [str(y) for y in by_year.index]
            amounts = by_year.tolist()

            fig = go.Figure()
            fig.update_layout(
                xaxis=dict(showgrid=False),
                yaxis=dict(gridcolor=BORDER, tickprefix="$"),
                height=240,
                **_CHART_LAYOUT,
            )
            fig.add_trace(go.Bar(
                x=years,
                y=amounts,
                marker_color=COLORS[1],
                text=[f"${v:,.2f}" for v in amounts],
                textposition="outside",
                textfont=dict(size=11, color=T_PRI),
                name="Annual dividends",
            ))
            return cards, fig

        except Exception:
            return cards, empty_fig