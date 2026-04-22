"""
callbacks/dividend_callbacks.py
================================
Callbacks for the Dividends page.
"""

import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, html, dcc
from config.constants import COLORS, GREEN, BORDER, T_PRI, T_SEC
from components.ui_helpers import stat_card
from services.market.data_fetcher import _download_with_retry, _extract_col
from core.engine.utils import normalise_tz

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

    @app.callback(
        Output("dividend-stats-cards",   "children"),
        Output("dividend-calendar",      "children"),
        Output("dividend-income-chart",  "figure"),
        Output("dividend-yield-chart",   "figure"),
        Output("dividend-table",         "children"),
        Input("portfolio-store", "data"),
    )
    def update_dividends(port_data):
        if not port_data or "holdings" not in port_data:
            return [], [], go.Figure(), go.Figure(), "No data"

        holdings = port_data["holdings"]
        tickers_yf = [h["ticker_yf"] for h in holdings]
        
        # ── 1. Historical Data Fetch ──────────────────────────────────────────
        bulk_df = _download_with_retry(tickers_yf, period="max", actions=True)
        if bulk_df.empty:
            return [], [], go.Figure(), go.Figure(), "Could not load distribution data"

        all_divs = []
        for h in holdings:
            ticker = h["ticker"]; ticker_yf = h["ticker_yf"]
            tranches = h.get("buy_tranches", [])
            
            div_s = _extract_col(bulk_df, ticker_yf, "Dividends")
            if div_s.empty: continue
            
            div_s = div_s[div_s > 0]
            div_s.index = normalise_tz(div_s.index)
            
            for ex_date, amount in div_s.items():
                held_on_date = sum(t["shares"] for t in tranches if pd.to_datetime(t["date"]) < ex_date)
                if held_on_date > 0:
                    all_divs.append({
                        "date": ex_date, "ticker": ticker, "amount": amount,
                        "total": amount * held_on_date, "shares": held_on_date
                    })

        df = pd.DataFrame(all_divs).sort_values("date", ascending=False) if all_divs else pd.DataFrame()

        # ── 2. KPI Calculation ────────────────────────────────────────────────
        total_realized = df["total"].sum() if not df.empty else 0
        annual_est = sum(h.get("annual_div", 0) for h in holdings)
        port_yield = (annual_est / sum(h["mkt_value"] for h in holdings) * 100) if holdings else 0
        
        # Next Payment logic
        today = pd.Timestamp.now().floor("D")
        events = []
        f_map = {"Monthly": 1, "Quarterly": 3, "Biannual": 6, "Annual": 12, "Unknown": 3}
        
        for h in holdings:
            last_dt = h.get("last_div_date")
            if last_dt:
                next_ex = pd.to_datetime(last_dt) + pd.DateOffset(months=f_map.get(h.get("div_frequency"), 3))
                while next_ex < today:
                    next_ex += pd.DateOffset(months=f_map.get(h.get("div_frequency"), 3))
                
                events.append({
                    "ticker": h["ticker"],
                    "date": next_ex,
                    "amount": h.get("last_div_amount", 0),
                    "total": h.get("last_div_amount", 0) * h["total_shares"]
                })
        
        events = sorted(events, key=lambda x: x["date"])
        next_event = events[0] if events else None
        
        stats = [
            stat_card("Annual Income",   f"${annual_est:,.2f}",   "estimated next 12m"),
            stat_card("Portfolio Yield", f"{port_yield:.2f}%",    "weighted average"),
            stat_card("Total Realized",  f"${total_realized:,.2f}", "all-time received"),
            stat_card("Next Payment",    f"${next_event['total']:,.2f}" if next_event else "N/A", 
                      f"Est. {next_event['date'].strftime('%d %b')}" if next_event else "No upcoming dates"),
        ]

        # ── 3. Calendar Grid ──────────────────────────────────────────────────
        cal_cards = []
        for i, ev in enumerate(events[:4]): # Show next 4 as per mockup
            is_upcoming = i == 0
            cal_cards.append(html.Div([
                html.Div(ev["date"].strftime("%b %d"), className="div-event-date"),
                html.Div(ev["ticker"], className="div-event-ticker"),
                html.Div(f"${ev['total']:,.0f}", className="div-event-amount"),
            ], className=f"dividend-event {'upcoming' if is_upcoming else ''}"))
        
        # ── 4. Analysis Charts ────────────────────────────────────────────────
        def horizontal_bar_fig(labels, values, prefix="", suffix=""):
            if not values: return go.Figure()
            
            # Sort ascending for Plotly Y-axis (top will be largest)
            combined = sorted(zip(labels, values), key=lambda x: x[1])
            l_sorted, v_sorted = zip(*combined)
            
            fig = go.Figure(go.Bar(
                x=v_sorted,
                y=l_sorted,
                orientation='h',
                marker=dict(
                    color="rgba(0, 201, 167, 0.85)", # Teal highlight
                    line=dict(width=0),
                ),
                text=[f"{prefix}{v:,.2f}{suffix}" for v in v_sorted],
                textposition='outside',
                cliponaxis=False,
                width=0.4
            ))
            
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter, system-ui, sans-serif", color=T_PRI, size=12),
                margin=dict(l=0, r=50, t=10, b=10),
                xaxis=dict(visible=False, range=[0, max(v_sorted)*1.3 if v_sorted else 1]),
                yaxis=dict(showgrid=False, zeroline=False, tickfont=dict(size=12, color=T_SEC)),
                height=max(len(l_sorted)*38, 120),
                showlegend=False,
                hovermode=False,
            )
            return fig

        sorted_by_inc = sorted(holdings, key=lambda x: x.get("annual_div", 0), reverse=True)
        income_fig = horizontal_bar_fig(
            [h["ticker"] for h in sorted_by_inc if h.get("annual_div", 0) >= 0], 
            [h["annual_div"] for h in sorted_by_inc if h.get("annual_div", 0) >= 0], 
            prefix="$"
        )

        sorted_by_yld = sorted(holdings, key=lambda x: x.get("div_yield", 0), reverse=True)
        yield_fig = horizontal_bar_fig(
            [h["ticker"] for h in sorted_by_yld if h.get("div_yield", 0) >= 0], 
            [h["div_yield"] for h in sorted_by_yld if h.get("div_yield", 0) >= 0], 
            suffix="%"
        )

        # ── 5. History & Table ────────────────────────────────────────────────
        rows = [
            html.Tr([
                html.Td(row["date"].strftime("%Y-%m-%d"), style=_TD),
                html.Td(row["ticker"], style={**_TD, "fontWeight": "600"}),
                html.Td(f"${row['amount']:.4f}", style=_TD),
                html.Td(f"{row['shares']:,.2f}", style=_TD),
                html.Td(f"${row['total']:,.2f}", style={**_TD, "color": GREEN, "fontWeight": "600"}),
            ])
            for _, row in df.iterrows()
        ] if not df.empty else []
        
        table = html.Table([
            html.Thead(html.Tr([html.Th(c, style=_TH) for c in ["Ex-Date", "Ticker", "Per Share", "Shares Held", "Total Amount"]])),
            html.Tbody(rows)
        ], style={"width": "100%", "borderCollapse": "collapse"})

        return stats, cal_cards, income_fig, yield_fig, table
