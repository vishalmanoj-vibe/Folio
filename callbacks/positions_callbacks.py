# callbacks/positions_callbacks.py
import logging
import plotly.graph_objects as go
from dash import Input, Output, State, ALL, html, dcc, ctx

logger = logging.getLogger(__name__)

from config.constants import (
    COLORS, BORDER, GREEN, RED, T_PRI, T_SEC, BG, SURFACE, NAMES, get_theme
)
from components.ui_helpers import stat_card
from components.charts.intel_helpers import create_empty_fig

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
        Input("positions-selected-ticker", "data"),
        Input("url", "pathname"),
        prevent_initial_call=False,
    )
    def render_card_grid(port_data, selected_ticker, url_pathname):
        import dash
        # FIX: prevent background recalculation when not on Positions page
        if url_pathname != "/positions": return dash.no_update
        if not port_data or "holdings" not in port_data:
            return []

        cards = []
        for h in port_data["holdings"]:
            try:
                ticker = h["ticker"]
                name = NAMES.get(ticker, ticker)
                pnl = h["pnl_pct"]
                pnl_cls = "c-pos" if pnl >= 0 else "c-neg"
                is_selected = ticker == selected_ticker
                
                # ── Mini Sparkline Generator ──
                # Renders a high-density area chart of the last 20 price points 
                # to provide quick visual context for each holding.
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
            except Exception as e:
                logger.error(f"Failed to render card for {h.get('ticker', '?')}: {e}")
                continue
        return cards

    # ── 2. Handle Card Clicks ──────────────────────────────────────────────────
    @app.callback(
        Output("positions-selected-ticker", "data"),
        Input({"type": "pos-card", "index": ALL}, "n_clicks"),
        Input("portfolio-store", "data"),
        State("positions-selected-ticker", "data"),
    )
    def select_ticker(n_clicks_list, port_data, current):
        """
        Handles ticker selection with auto-default to first holding.
        """
        # If triggered by a card click
        if ctx.triggered_id and isinstance(ctx.triggered_id, dict) and ctx.triggered_id.get("type") == "pos-card":
            # FIX: ignore ghost clicks on dynamically generated components
            if not ctx.triggered[0]["value"] or int(ctx.triggered[0]["value"]) < 1:
                import dash
                return dash.no_update
            return ctx.triggered_id["index"]

        # Default selection logic (on load or when store updates)
        if current is None and port_data and "holdings" in port_data and port_data["holdings"]:
            return port_data["holdings"][0]["ticker"]

        return current

    # ── 3. Detail Panel — Metrics Cards ──────────────────────────────────────
    @app.callback(
        Output("etf-detail-cards", "children"),
        Input("positions-selected-ticker", "data"),
        Input("portfolio-store", "data"),
    )
    def render_detail_metrics(ticker, port_data):
        if not ticker or not port_data or "holdings" not in port_data:
            return []

        h = next((x for x in port_data["holdings"] if x["ticker"] == ticker), None)
        if not h:
            return html.Div(f"Metrics for {ticker} are currently unavailable", className="c-muted")

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
        Input("theme-store", "data"),
    )
    def render_price_chart(ticker, period, port_data, theme):
        t_ = get_theme(theme or "dark")
        if not ticker: 
            return create_empty_fig("Select a position to view history", height=350, theme_tokens=t_)

        holding = next((h for h in port_data.get("holdings", []) if h["ticker"] == ticker), None)
        if not holding: 
            return create_empty_fig(f"No data for {ticker}", height=350, theme_tokens=t_)

        fig = go.Figure()
        fig.update_layout(
            xaxis=dict(showgrid=False, rangeslider_visible=False),
            yaxis=dict(gridcolor="rgba(255,255,255,0.05)", tickprefix="$"),
            hovermode="x unified", height=350, **_CHART_LAYOUT
        )

        try:
            # FIX: use pre-fetched histories from portfolio-store
            history_records = port_data.get("histories", {}).get(ticker, [])
            if not history_records:
                return create_empty_fig(
                    f"No price history for {ticker}", 
                    height=350, theme_tokens=t_
                )
            
            import pandas as pd
            df = pd.DataFrame(history_records)
            df["Date"] = pd.to_datetime(df["Date"])
            df = df.set_index("Date").sort_index()
            
            # Apply period filter
            from datetime import timedelta
            period_map = {
                "1mo": timedelta(days=30),
                "3mo": timedelta(days=90),
                "1y":  timedelta(days=365),
                "ytd": None,
                "max": None,
            }
            if period in period_map and period_map[period]:
                cutoff = pd.Timestamp.now() - period_map[period]
                df = df[df.index >= cutoff]
            elif period == "ytd":
                df = df[df.index >= pd.Timestamp(pd.Timestamp.now().year, 1, 1)]
            
            if not df.empty:
                if df.index.tz is not None: 
                    df.index = df.index.tz_convert(None)
                
                fig.add_trace(go.Candlestick(
                    x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
                    increasing_line_color=GREEN, decreasing_line_color=RED,
                    increasing_fillcolor=GREEN, decreasing_fillcolor=RED, 
                    name=ticker,
                    opacity=0.9
                ))
                
                if holding and holding.get("avg_cost"):
                    fig.add_hline(
                        y=holding["avg_cost"], 
                        line_dash="dot", 
                        line_color="rgba(255,255,255,0.4)",
                        annotation_text=f"Avg cost ${holding['avg_cost']:,.3f}", 
                        annotation_position="top left"
                    )
            else:
                fig.add_annotation(text=f"No price history available for {ticker}", 
                                  showarrow=False, font=dict(size=14, color="var(--t-sec)"))
        except Exception as e:
            logger.error(f"Failed to fetch history for {ticker}: {e}")
            fig.add_annotation(text="Error loading chart data", showarrow=False)
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

    # ── 6. Period Selection Buttons ──────────────────────────────────────────
    @app.callback(
        Output("positions-period-btns", "children"),
        Input("positions-period-store", "data")
    )
    def render_period_btns(current_period):
        periods = [
            ("1M", "1mo"),
            ("3M", "3mo"),
            ("1Y", "1y"),
            ("YTD", "ytd"),
            ("MAX", "max")
        ]
        
        btns = []
        for label, val in periods:
            is_active = (current_period == val)
            # Use btn-primary for the active selection, otherwise standard styling
            btn_class = f"period-btn btn-sm {'btn-primary' if is_active else ''}"
            
            btns.append(
                html.Button(
                    label,
                    id={"type": "pos-period-btn", "index": val},
                    className=btn_class,
                    n_clicks=0
                )
            )
        return btns

    # ── 7. Detail Title ──────────────────────────────────────────────────────
    @app.callback(
        Output("positions-detail-title", "children"),
        Input("positions-selected-ticker", "data")
    )
    def update_detail_title(ticker):
        if not ticker:
            return "Select a position to view details"
        return f"Details for {ticker}"

