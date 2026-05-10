# callbacks/positions_callbacks.py
import logging
import plotly.graph_objects as go
from dash import Input, Output, State, ALL, html, dcc, ctx

logger = logging.getLogger(__name__)

from config.constants import (
    COLORS, BORDER, GREEN, RED, T_PRI, T_SEC, BG, SURFACE, NAMES, get_theme
)
from components.ui_helpers import stat_card, tech_signal_badges, progress_row, interpolate_color
from components.charts.helpers import create_empty_fig
from services.market.dividend_service import calculate_portfolio_dividend_stats, get_ticker_dividend_data
import pandas as pd

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
        Input("signals-store", "data"),
        prevent_initial_call=False,
    )
    def render_card_grid(port_data, selected_ticker, url_pathname, signals_store):
        import dash
        # FIX: prevent background recalculation when not on Positions page
        if url_pathname.rstrip("/") != "/positions": return dash.no_update
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
                
                signal_badge = None
                if signals_store and "raw" in signals_store:
                    sig_data = signals_store["raw"].get(ticker)
                    if sig_data:
                        signal_val = sig_data.get("signal", "HOLD")
                        color_map = {"BUY": GREEN, "SELL": RED, "HOLD": "var(--t-sec)"}
                        badge_color = color_map.get(signal_val, "var(--t-sec)")
                        signal_badge = html.Div(
                            signal_val,
                            style={
                                "fontSize": "10px", "fontWeight": "bold", 
                                "padding": "2px 6px", "borderRadius": "4px",
                                "backgroundColor": "var(--surface-2)",
                                "color": badge_color, "border": f"1px solid {badge_color}",
                                "display": "inline-block", "marginTop": "4px"
                            }
                        )
                
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

                card_children = [
                    html.Div(ticker, className="holding-card-ticker"),
                    html.Div(name,   className="holding-card-name"),
                    html.Div(f"${h['mkt_value']:,.2f}", className="holding-card-value"),
                    html.Div(f"{pnl:+.2f}%", className=f"holding-card-pnl {pnl_cls}"),
                    html.Div(f"Yield: {h.get('div_yield', 0):.2f}%", className="holding-card-name", style={"marginTop": "4px"}),
                ]
                
                if signal_badge:
                    card_children.append(signal_badge)
                    
                card_children.append(dcc.Graph(figure=spark_fig, config={"displayModeBar": False}, className="holding-card-sparkline"))

                cards.append(
                    html.Div(
                        card_children, 
                        id={"type": "pos-card", "index": ticker},
                        className=f"holding-card {'selected' if is_selected else ''}",
                        n_clicks=0
                    )
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
        [Output("etf-detail-cards", "children"), 
         Output("positions-tech-signals-container", "children")],
        Input("positions-selected-ticker", "data"),
        Input("portfolio-store", "data"),
        Input("url", "pathname"),
        prevent_initial_call=False,
    )
    def render_detail_metrics(ticker, port_data, url_pathname):
        import dash
        if url_pathname.rstrip("/") != "/positions": return dash.no_update, dash.no_update
        if not ticker or not port_data or "holdings" not in port_data:
            return [], None

        h = next((x for x in port_data["holdings"] if x["ticker"] == ticker), None)
        if not h:
            return html.Div(f"Metrics for {ticker} are currently unavailable", className="c-muted"), None

        pnl = h["pnl"]; pc = GREEN if pnl >= 0 else RED
        day_pnl = h["day_pnl"]; dc = GREEN if day_pnl >= 0 else RED

        # Calculate ticker-specific next payment
        _, _, events = calculate_portfolio_dividend_stats([h])
        today = pd.Timestamp.now().floor("D")
        next_e = next((e for e in events if e["date"] >= today), None)
        
        next_div_val = "None"
        next_div_sub = "No upcoming events"
        if next_e:
            next_div_val = f"${next_e['total']:,.2f}"
            next_div_sub = f"{next_e['date'].strftime('%d %b')} ({next_e['type']})"

        metrics = [
            ("Total Invested", f"${h['total_cost']:,.2f}", f"{h['total_shares']:,.2f} units"),
            ("Market Value", f"${h['mkt_value']:,.2f}", f"@ ${h['last_price']:,.3f}"),
            ("Unrealised P&L", f"{'+$' if pnl >= 0 else '-$'}{abs(pnl):,.2f}", f"{h['pnl_pct']:+.2f}%", pc),
            ("Today's P&L", f"{'+$' if day_pnl >= 0 else '-$'}{abs(day_pnl):,.2f}", f"{h['day_chg_pct']:+.2f}%", dc),
            ("Avg Cost", f"${h['avg_cost']:,.4f}", "VWAP"),
            ("Div Yield", f"{h.get('div_yield', 0):.2f}%", f"Annual: ${h.get('annual_div', 0):,.2f}"),
            ("Next Div", next_div_val, next_div_sub, GREEN if next_e else None),
        ]

        cards_layout = [
            html.Div([
                html.Div(label, className="etf-detail-label"),
                html.Div(val,   className="etf-detail-value", style={"color": color} if color else {}),
                html.Div(sub,   className="etf-detail-sub"),
            ], className="etf-detail-card")
            for label, val, sub, color in [(m[0], m[1], m[2], m[3] if len(m)>3 else None) for m in metrics]
        ]
        
        # Generate Tech Signals
        tech_signals = None
        history = port_data.get("histories", {}).get(ticker, [])
        if history:
            tech_signals = tech_signal_badges(ticker, history)

        return cards_layout, tech_signals

    @app.callback(
        Output("ai-insight-container", "children"),
        Input("positions-selected-ticker", "data"),
        Input("signals-store", "data"),
        Input("url", "pathname"),
        prevent_initial_call=False,
    )
    def render_ai_insight(ticker, signals_store, url_pathname):
        import dash
        if url_pathname.rstrip("/") != "/positions": return dash.no_update
        if not ticker or not signals_store or "ai" not in signals_store:
            return None

        if ticker not in signals_store["ai"]:
            return None

        ai_data = signals_store["ai"][ticker]
        raw_sig = signals_store["raw"].get(ticker, {}) if "raw" in signals_store else {}
        verdict = ai_data.get("verdict", "Mixed")
        
        # Map verdict to color
        v_color = GREEN if verdict == "Confident" else (RED if verdict == "Risk flagged" else "var(--t-sec)")
        
        # Build children dynamically
        ai_children = [
            html.Div([
                html.Span("🤖", style={"marginRight": "8px"}),
                "AI Analyst Insight"
            ], className="etf-detail-label", style={"display": "flex", "alignItems": "center"}),
            html.Div(verdict, className="etf-detail-value", style={"color": v_color, "fontSize": "16px"}),
            html.Div(ai_data.get("explanation", ""), style={"marginTop": "8px", "whiteSpace": "normal", "fontSize": "13px", "color": "var(--t-sec)", "lineHeight": "1.5"}),
        ]
        if ai_data.get("risks"):
            ai_children.append(html.Div([
                html.Div(f"• {r}", style={"color": "var(--red)", "marginTop": "4px", "fontSize": "12px"}) for r in ai_data["risks"]
            ]))
        if raw_sig:
            ai_children.append(html.Div([
                html.Div(f"Technical Score: {raw_sig.get('score', 0.0):.2f}", style={"marginTop": "8px", "fontWeight": "bold", "color": "var(--cyan)", "fontSize": "13px"}),
                html.Div([html.Div(f"• {r}") for r in raw_sig.get("reasons", [])], style={"marginTop": "4px", "color": "var(--t-sec)", "fontSize": "12px"})
            ]))

        return html.Div(ai_children, className="etf-detail-card", style={"marginTop": "10px", "marginBottom": "24px", "width": "100%"})

    # ── 4. Detail Panel — Price Chart ─────────────────────────────────────────
    @app.callback(
        Output("positions-price-chart-container", "children"),
        Input("positions-selected-ticker", "data"),
        Input("positions-period-store", "data"),
        Input("portfolio-store", "data"),
        Input("theme-store", "data"),
        Input("url", "pathname"),
    )
    def render_price_chart(ticker, period, port_data, theme, url_pathname):
        import dash
        if url_pathname.rstrip("/") != "/positions": return dash.no_update
        t_ = get_theme(theme or "dark")
        if not ticker: 
            return None

        holding = next((h for h in port_data.get("holdings", []) if h["ticker"] == ticker), None)
        if not holding: 
            return None

        fig = go.Figure()
        
        # Merge theme base with local overrides
        layout = _CHART_LAYOUT.copy()
        layout.update(dict(
            xaxis=dict(showgrid=False, rangeslider_visible=False),
            yaxis=dict(gridcolor="rgba(255,255,255,0.05)", tickprefix="$"),
            hovermode="x unified", height=350,
            uirevision=ticker,
            hoverlabel=t_["PLOTLY_BASE"].get("hoverlabel")
        ))
        fig.update_layout(layout)

        try:
            # FIX: use pre-fetched histories from portfolio-store
            history_records = port_data.get("histories", {}).get(ticker, [])
            if not history_records:
                fig = create_empty_fig(f"No price history for {ticker}", height=350, theme_tokens=t_)
            else:
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
                    
                    if all(col in df.columns for col in ["Open", "High", "Low", "Close"]):
                        fig.add_trace(go.Candlestick(
                            x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
                            increasing_line_color=GREEN, decreasing_line_color=RED,
                            increasing_fillcolor=GREEN, decreasing_fillcolor=RED, 
                            name=ticker,
                            opacity=0.9
                        ))
                    else:
                        # Fallback to line chart if OHLC is missing (e.g. for intraday 1d)
                        fig.add_trace(go.Scatter(
                            x=df.index, y=df["Close"], mode="lines",
                            line=dict(color=GREEN if df["Close"].iloc[-1] >= df["Close"].iloc[0] else RED, width=2),
                            name=ticker,
                            hovertemplate="$%{y:,.3f}<extra></extra>"
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
                    fig = create_empty_fig(f"No price history available for {ticker}", height=350, theme_tokens=t_)
        except Exception as e:
            logger.error(f"Failed to fetch history for {ticker}: {e}")
            fig = create_empty_fig("Error loading chart data", height=350, theme_tokens=t_)

        from components.ui_helpers import chart_title
        return html.Div([
            html.Div([
                chart_title("Price history", "positions-price"),
                html.Div(id="positions-period-btns", className="flex-row-gap", style={"marginLeft": "auto"})
            ], className="flex-row flex-center", style={"marginBottom": "12px"}),
            dcc.Graph(id="positions-price-chart", figure=fig, config={"displayModeBar": False}),
        ], style={"marginTop": "24px"})

    # ── 5. Detail Panel — Transaction Table ──────────────────────────────────
    @app.callback(
        Output("positions-txn-table-container", "children"),
        Input("positions-selected-ticker", "data"),
        Input("txn-store", "data"),
        Input("url", "pathname"),
    )
    def render_txn_table(ticker, history, url_pathname):
        import dash
        if url_pathname.rstrip("/") != "/positions": return dash.no_update
        if not ticker or not history: return None
        txns = sorted([t for t in history if t["ticker"].upper() == ticker], key=lambda x: x["date"], reverse=True)
        if not txns:
            return None
        
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

        from components.ui_helpers import chart_title
        return html.Div([
            chart_title("Transaction history", "positions-txns"),
            html.Table([
                html.Thead(html.Tr([html.Th(c, style=_TH) for c in ["Date", "Type", "Shares", "Price", "Total"]])),
                html.Tbody(rows)
            ], className="overflow-table", style={"width": "100%", "borderCollapse": "collapse", "marginTop": "10px"})
        ], style={"marginTop": "24px"})

    # ── 6. Period Selection Buttons ──────────────────────────────────────────
    @app.callback(
        Output("positions-period-btns", "children"),
        Input("positions-period-store", "data"),
        Input("url", "pathname"),
    )
    def render_period_btns(current_period, url_pathname):
        import dash
        if url_pathname.rstrip("/") != "/positions": return dash.no_update
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
        Input("positions-selected-ticker", "data"),
        Input("url", "pathname"),
    )
    def update_detail_title(ticker, url_pathname):
        import dash
        if url_pathname.rstrip("/") != "/positions": return dash.no_update
        if not ticker:
            return "Select a position to view details"
        return f"Details for {ticker}"

    # ── 9. Ticker-Specific Dividend Details ───────────────────────────────────
    @app.callback(
        Output("positions-ticker-dividend-container", "children"),
        Input("positions-selected-ticker", "data"),
        Input("portfolio-store", "data"),
        Input("url", "pathname"),
        prevent_initial_call=False
    )
    def render_ticker_dividends(ticker, port_data, url_pathname):
        import dash
        if url_pathname.rstrip("/") != "/positions": return dash.no_update
        if not ticker or not port_data or "holdings" not in port_data:
            return None
            
        h = next((x for x in port_data["holdings"] if x["ticker"] == ticker), None)
        if not h: return None
        
        df = get_ticker_dividend_data(ticker, h["ticker_yf"])
        if df.empty:
            return html.Div("No dividend history found for this position.", className="c-muted", style={"fontSize": "13px", "padding": "20px", "border": "0.5px dashed var(--border)", "borderRadius": "8px", "textAlign": "center"})
            
        # 1. Mini Bar Chart (Trend)
        plot_df = df.head(8).iloc[::-1] # Last 8, chronological
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=plot_df["date"],
            y=plot_df["amount"],
            marker_color=GREEN,
            name="Distribution",
            hovertemplate="$%{y:.4f}<extra></extra>"
        ))
        fig.update_layout(
            height=140,
            margin=dict(l=0, r=0, t=20, b=0),
            xaxis=dict(visible=True, showgrid=False, tickformat="%b %y", tickfont=dict(size=9, color=T_SEC)),
            yaxis=dict(visible=False),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        
        # 2. Last 5 Payments Table
        rows = []
        for _, row in df.head(5).iterrows():
            rows.append(html.Tr([
                html.Td(row["date"].strftime("%d %b %Y"), style=_TD),
                html.Td(row["pay_date"] if row["pay_date"] else "—", style={**_TD, "color": T_SEC}),
                html.Td(f"${row['amount']:.4f}", style={**_TD, "fontWeight": "600", "color": GREEN}),
            ]))
            
        table = html.Table([
            html.Thead(html.Tr([html.Th(c, style=_TH) for c in ["Ex-Date", "Pay-Date", "Amount"]])),
            html.Tbody(rows)
        ], style={"width": "100%", "borderCollapse": "collapse"})
        
        from components.ui_helpers import chart_title
        return html.Div([
            chart_title(f"Dividend trend & history"),
            html.Div([
                html.Div([
                    dcc.Graph(figure=fig, config={"displayModeBar": False})
                ], style={"flex": "1", "minWidth": "200px"}),
                html.Div([
                    table
                ], style={"flex": "1.2", "minWidth": "250px"}),
            ], style={"display": "flex", "flexWrap": "wrap", "gap": "24px", "marginTop": "12px"})
        ], style={"padding": "16px", "backgroundColor": "var(--surface-2)", "borderRadius": "8px", "border": "1px solid var(--border)"})

    # ── 10. Portfolio Dividend Insights ───────────────────────────────────────
    @app.callback(
        [Output("positions-dividend-income-chart", "children"),
         Output("positions-dividend-yield-chart", "children"),
         Output("positions-dividend-table", "children")],
        Input("portfolio-store", "data"),
        Input("url", "pathname"),
        prevent_initial_call=False
    )
    def render_portfolio_dividend_insights(port_data, url_pathname):
        import dash
        if url_pathname.rstrip("/") != "/positions": return [dash.no_update]*3
        if not port_data or "holdings" not in port_data:
            return [None]*3
            
        holdings = port_data["holdings"]
        df_full, stats, _ = calculate_portfolio_dividend_stats(holdings)
        
        # 1. Comparison Charts (Progress Rows)
        C_START = "#1D9E75" 
        C_END   = "#EF9F27" 

        income_data = sorted([{"ticker": h["ticker"], "val": h.get("annual_div", 0)} for h in holdings], key=lambda x: x["val"], reverse=True)
        income_data = [x for x in income_data if x["val"] > 0]
        max_income = max([x["val"] for x in income_data]) if income_data else 0
        n_income = len(income_data)
        income_rows = [
            progress_row(x["ticker"], x["val"], max_income, prefix="$", color=interpolate_color(C_START, C_END, i / (n_income - 1)) if n_income > 1 else C_START)
            for i, x in enumerate(income_data)
        ]

        yield_data = sorted([{"ticker": h["ticker"], "val": h.get("div_yield", 0)} for h in holdings], key=lambda x: x["val"], reverse=True)
        yield_data = [x for x in yield_data if x["val"] > 0]
        max_yield = max([x["val"] for x in yield_data]) if yield_data else 0
        n_yield = len(yield_data)
        yield_rows = [
            progress_row(x["ticker"], x["val"], max_yield, suffix="%", color=interpolate_color(C_START, C_END, i / (n_yield - 1)) if n_yield > 1 else C_START)
            for i, x in enumerate(yield_data)
        ]

        # 2. Recent Distributions Table (Max 20)
        if df_full.empty:
            table = html.Div("No dividend history found.", className="c-muted", style={"padding": "40px", "textAlign": "center"})
        else:
            rows = []
            for _, row in df_full.head(20).iterrows():
                rows.append(html.Tr([
                    html.Td(row["date"].strftime("%Y-%m-%d"), style=_TD),
                    html.Td(row["pay_date"] if row["pay_date"] else "—", style={**_TD, "color": T_SEC}),
                    html.Td(row["ticker"], style={**_TD, "fontWeight": "600"}),
                    html.Td(f"${row['amount']:.4f}", style=_TD),
                    html.Td(f"{row['shares']:g}", style=_TD),
                    html.Td(f"${row['total']:,.2f}", style={**_TD, "color": GREEN, "fontWeight": "600"}),
                ]))
            table = html.Table([
                html.Thead(html.Tr([html.Th(c, style=_TH) for c in ["Ex-Date", "Pay-Date", "Ticker", "Per Share", "Shares Held", "Total Amount"]])),
                html.Tbody(rows)
            ], style={"width": "100%", "borderCollapse": "collapse"})
            
        return income_rows, yield_rows, table

