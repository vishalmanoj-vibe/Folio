"""
callbacks/etf_detail_callbacks.py
==================================
Callbacks for the ETF detail page.
"""

import yfinance as yf
import plotly.graph_objects as go
from dash import Input, Output, State, ALL, html
from config.constants import (
    COLORS, BORDER, GREEN, RED, T_PRI, T_SEC, BG, SURFACE
)
from services.market.market_status import market_badge
from components.ui_helpers import stat_card

# ── Plotly layout base using CSS-var-aware colours ────────────────────────────
_CHART_LAYOUT = dict(
    paper_bgcolor=BG,
    plot_bgcolor=SURFACE,
    font=dict(family="system-ui,sans-serif", color=T_PRI, size=13),
    margin=dict(l=16, r=16, t=40, b=16),
    legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0),
    uirevision=True,  # Preserve state across auto-refreshes
)

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

def register_callbacks(app) -> None:
    from pages.etf_detail import _period_buttons


    # ── Period store + button highlight ──────────────────────────────────────
    @app.callback(
        Output("etf-period-store", "data"),
        Output("etf-period-btns",  "children"),
        Input({"type": "etf-period-btn", "index": ALL}, "n_clicks"),
        State({"type": "etf-period-btn", "index": ALL}, "id"),
        State("etf-period-store", "data"),
        prevent_initial_call=True,
    )
    def update_period(n_clicks_list, btn_ids, current_period):
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

        if df.index.tz is not None:
            df.index = df.index.tz_convert(None)
        dates = df.index.strftime("%Y-%m-%d").tolist()

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
            stat_card("Total invested",  f"${h['total_cost']:,.2f}",
                      tip="Total capital deployed into this ETF across all buy transactions."),
            stat_card("Current value",   f"${h['mkt_value']:,.2f}",
                  f"{h['total_shares']} shares @ ${h['last_price']:,.3f}",
                  tip="Today's market value based on the latest available price."),
            stat_card("Unrealised P&L",
                  f"{psgn}${pnl:,.2f}",
                  f"{psgn}{h['pnl_pct']:.2f}%  all time", pc, pc,
                  tip="Paper gain or loss on this position since your first purchase. Not locked in until sold."),
            stat_card("Today's P&L",
                  f"{dsgn}${day_pnl:,.2f}",
                  f"{dsgn}{h['day_chg_pct']:.2f}%  today", dc, dc,
                  tip="Estimated value change since yesterday's closing price, based on units held."),
            stat_card("Avg cost",    f"${h['avg_cost']:,.4f}",
                  tip="Average price paid per share across all buy transactions (VWAP)."),
            stat_card("Last price",  f"${h['last_price']:,.3f}",
                  f"H ${h['day_high']:,.3f}  /  L ${h['day_low']:,.3f}",
                  tip="Most recent trade price. During ASX off-hours this is the previous session's close."),
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
            stat_card("Annual income",
                  f"${annual_div:,.2f}",
                  "estimated · last 12 months",
                  GREEN if annual_div > 0 else "var(--t-pri)", "var(--t-sec)"),
            stat_card("Dividend yield",
                  f"{div_yield:.2f}%",
                  "annual income ÷ current value",
                  GREEN if div_yield > 0 else "var(--t-pri)", "var(--t-sec)"),
            stat_card("Total received",
                  f"${total_div:,.2f}",
                  "all time since first purchase"),
        ]

        try:
            tk   = yf.Ticker(ticker + ".AX")
            hist = tk.history(period="max")

            if hist.empty or "Dividends" not in hist.columns:
                return cards, empty_fig

            div_s = hist["Dividends"]
            div_s = div_s[div_s > 0]

            if div_s.empty:
                return cards, empty_fig

            if div_s.index.tz is not None:
                div_s.index = div_s.index.tz_convert(None)

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
