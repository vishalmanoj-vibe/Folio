"""
callbacks/positions_callbacks.py
==================================
Callbacks for the Positions page.
"""

import yfinance as yf
import plotly.graph_objects as go
from dash import Input, Output, State, ALL, html, dcc, ctx
from config.constants import (
    COLORS, BORDER, GREEN, RED, T_PRI, T_SEC, BG, SURFACE, NAMES
)
from components.ui_helpers import stat_card

# ── Plotly layout base ────────────────────────────────────────────────────────
_CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="system-ui,sans-serif", color=T_PRI, size=11),
    margin=dict(l=10, r=10, t=10, b=10),
    legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0),
    uirevision=True,
)

_TH = {
    "fontSize": "10px", "color": "var(--t-sec)", "fontWeight": "600",
    "padding": "9px 12px", "borderBottom": "0.5px solid var(--border)",
    "backgroundColor": "var(--surface-2)", "textAlign": "left",
    "whiteSpace": "nowrap", "textTransform": "uppercase", "letterSpacing": "0.4px",
}
_TD = {
    "fontSize": "12px", "padding": "9px 12px",
    "borderBottom": "0.5px solid var(--border)", "whiteSpace": "nowrap",
    "color": "var(--t-pri)",
}

def register_callbacks(app) -> None:

    # ── 1. Card Grid Population ───────────────────────────────────────────────
    @app.callback(
        Output("positions-card-grid", "children"),
        Input("portfolio-store", "data"),
        State("positions-selected-ticker", "data")
    )
    def render_card_grid(port_data, selected_ticker):
        if not port_data or "holdings" not in port_data:
            return []

        cards = []
        for h in port_data["holdings"]:
            ticker = h["ticker"]
            name = NAMES.get(ticker, ticker)
            pnl = h["pnl_pct"]
            pnl_cls = "c-pos" if pnl >= 0 else "c-neg"
            is_selected = ticker == selected_ticker
            
            # Sparkline
            spark_fig = go.Figure()
            history = port_data.get("histories", {}).get(ticker, [])
            if history:
                prices = [x["Close"] for x in history[-20:]]
                is_pos = pnl >= 0
                line_color = GREEN if is_pos else RED
                fill_color = "rgba(29,158,117,0.08)" if is_pos else "rgba(226,75,74,0.08)"
                
                spark_fig.add_trace(go.Scatter(
                    y=prices, mode="lines", 
                    line=dict(color=line_color, width=1.5),
                    fill='tozeroy', 
                    fillcolor=fill_color
                ))
            spark_fig.update_layout(
                xaxis=dict(visible=False), yaxis=dict(visible=False),
                margin=dict(l=0, r=0, t=0, b=0), height=30,
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                showlegend=False
            )

            cards.append(
                html.Div([
                    html.Div(ticker, className="holding-card-ticker"),
                    html.Div(name,   className="holding-card-name"),
                    html.Div(f"${h['mkt_value']:,.2f}", className="holding-card-value"),
                    html.Div(f"{pnl:+.2f}%", className=f"holding-card-pnl {pnl_cls}"),
                    html.Div(f"Yield: {h.get('div_yield', 0):.2f}%", className="holding-card-name", style={"marginTop": "4px"}),
                    dcc.Graph(figure=spark_fig, config={"displayModeBar": False}, className="holding-card-sparkline")
                ], 
                id={"type": "pos-card", "index": ticker},
                className=f"holding-card {'selected' if is_selected else ''}",
                n_clicks=0)
            )
        return cards

    # ── 2. Handle Card Clicks ──────────────────────────────────────────────────
    @app.callback(
        Output("positions-selected-ticker", "data"),
        Input({"type": "pos-card", "index": ALL}, "n_clicks"),
        State("positions-selected-ticker", "data"),
        prevent_initial_call=True
    )
    def select_ticker(n_clicks_list, current):
        if not ctx.triggered_id:
            return current
        return ctx.triggered_id["index"]

    # ── 3. Detail Panel — Metrics Cards ──────────────────────────────────────
    @app.callback(
        Output("etf-detail-cards", "children"),
        Input("positions-selected-ticker", "data"),
        Input("portfolio-store", "data"),
    )
    def render_detail_metrics(ticker, port_data):
        if not ticker or not port_data or "holdings" not in port_data:
            return html.Div("Select a position to view details", className="c-muted")

        h = next((x for x in port_data["holdings"] if x["ticker"] == ticker), None)
        if not h: return html.Div("Position not found")

        pnl = h["pnl"]; pc = GREEN if pnl >= 0 else RED
        day_pnl = h["day_pnl"]; dc = GREEN if day_pnl >= 0 else RED

        metrics = [
            ("Total Invested", f"${h['total_cost']:,.2f}", f"{h['total_shares']:,.2f} units"),
            ("Market Value", f"${h['mkt_value']:,.2f}", f"@ ${h['last_price']:,.3f}"),
            ("Unrealised P&L", f"{'+$' if pnl >= 0 else '-$'}{abs(pnl):,.2f}", f"{h['pnl_pct']:+.2f}%", pc),
            ("Today's P&L", f"{'+$' if day_pnl >= 0 else '-$'}{abs(day_pnl):,.2f}", f"{h['day_chg_pct']:+.2f}%", dc),
            ("Avg Cost", f"${h['avg_cost']:,.4f}", "VWAP"),
            ("Div Yield", f"{h.get('div_yield', 0):.2f}%", f"Annual: ${h.get('annual_div', 0):,.2f}"),
        ]

        return [
            html.Div([
                html.Div(label, className="etf-detail-label"),
                html.Div(val,   className="etf-detail-value", style={"color": color} if color else {}),
                html.Div(sub,   className="etf-detail-sub"),
            ], className="etf-detail-card")
            for label, val, sub, *extra in [(m[0], m[1], m[2], m[3] if len(m)>3 else None) for m in metrics]
        ]

    # ── 4. Detail Panel — Price Chart ─────────────────────────────────────────
    @app.callback(
        Output("positions-price-chart", "figure"),
        Input("positions-selected-ticker", "data"),
        Input("positions-period-store", "data"),
        Input("portfolio-store", "data"),
    )
    def render_price_chart(ticker, period, port_data):
        fig = go.Figure()
        fig.update_layout(
            xaxis=dict(showgrid=False, rangeslider_visible=False),
            yaxis=dict(gridcolor="rgba(255,255,255,0.05)", tickprefix="$"),
            hovermode="x unified", height=350, **_CHART_LAYOUT
        )
        if not ticker: return fig

        holding = next((h for h in port_data.get("holdings", []) if h["ticker"] == ticker), None)
        try:
            tk = yf.Ticker(ticker + ".AX")
            df = tk.history(start=holding["first_purchase"] if period == "purchase" else None, period=period if period != "purchase" else None)
            if not df.empty:
                if df.index.tz is not None: df.index = df.index.tz_convert(None)
                fig.add_trace(go.Candlestick(
                    x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
                    increasing_line_color=GREEN, decreasing_line_color=RED,
                    increasing_fillcolor=GREEN, decreasing_fillcolor=RED, name=ticker
                ))
                if holding and holding.get("avg_cost"):
                    fig.add_hline(y=holding["avg_cost"], line_dash="dot", line_color="rgba(255,255,255,0.3)",
                                  annotation_text=f"Avg cost ${holding['avg_cost']:,.3f}", annotation_position="top left")
        except: pass
        return fig

    # ── 5. Detail Panel — Transaction Table ──────────────────────────────────
    @app.callback(
        Output("positions-txn-table", "children"),
        Input("positions-selected-ticker", "data"),
        Input("txn-store", "data"),
    )
    def render_txn_table(ticker, history):
        if not ticker or not history: return "No data"
        txns = sorted([t for t in history if t["ticker"].upper() == ticker], key=lambda x: x["date"], reverse=True)
        
        rows = []
        for t in txns:
            is_buy = t["type"] == "buy"
            rows.append(html.Tr([
                html.Td(t["date"], style=_TD),
                html.Td(t["type"].upper(), style={**_TD, "color": GREEN if is_buy else RED, "fontWeight": "600"}),
                html.Td(f"{float(t['shares']):g}", style=_TD),
                html.Td(f"${float(t['price']):,.3f}", style=_TD),
                html.Td(f"${(float(t['shares']) * float(t['price'])):,.2f}", style=_TD),
            ]))

        return html.Table([
            html.Thead(html.Tr([html.Th(c, style=_TH) for c in ["Date", "Type", "Shares", "Price", "Total"]])),
            html.Tbody(rows)
        ], style={"width": "100%", "borderCollapse": "collapse"})

