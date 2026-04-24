"""
callbacks/dividend_callbacks.py
================================
Callbacks for the Dividends page.
"""

import logging
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, html, dcc
from config.constants import COLORS, GREEN, BORDER, T_PRI, T_SEC
from components.ui_helpers import stat_card, progress_row, interpolate_color
from services.market.data_fetcher import _download_with_retry, _extract_col
from core.engine.utils import normalise_tz

logger = logging.getLogger(__name__)

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
        Output("dividend-income-chart",  "children"),
        Output("dividend-yield-chart",   "children"),
        Output("dividend-table",         "children"),
        Input("portfolio-store", "data"),
    )
    def update_dividends(port_data):
        try:
            if not port_data or "holdings" not in port_data:
                return [], [], [], [], "No data"

            holdings = port_data["holdings"]
            tickers_yf = [h["ticker_yf"] for h in holdings]
            
            # ── 1. Historical Data Fetch ──────────────────────────────────────────
            bulk_df = _download_with_retry(tickers_yf, period="max", actions=True)
            if bulk_df.empty:
                return [], [], [], [], "Could not load distribution data"

            all_divs = []
            for h in holdings:
                ticker = h["ticker"]; ticker_yf = h["ticker_yf"]
                tranches = h.get("buy_tranches", [])
                
                div_s = _extract_col(bulk_df, ticker_yf, "Dividends")
                if div_s.empty: continue
                
                div_s = div_s[div_s > 0]
                div_s.index = normalise_tz(div_s.index)
                
                # Matching ex-dividend dates against purchase tranches
                for ex_date, amount in div_s.items():
                    # A tranche is eligible only if it was bought BEFORE the ex-dividend date
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
            port_total_val = sum(h["mkt_value"] for h in holdings)
            port_yield = (annual_est / port_total_val * 100) if port_total_val else 0
            
            # Next Payment logic
            today = pd.Timestamp.now().floor("D")
            events = []
            f_map = {"Monthly": 1, "Quarterly": 3, "Biannual": 6, "Annual": 12, "Unknown": 3}
            
            for h in holdings:
                # Prioritize real data from ticker.info if available
                payout_dt = h.get("payout_date")
                next_ex_dt = h.get("next_div_date")
                
                if payout_dt:
                    events.append({
                        "ticker": h["ticker"], "date": pd.to_datetime(payout_dt),
                        "amount": h.get("last_div_amount", 0),
                        "total": h.get("last_div_amount", 0) * h["total_shares"],
                        "type": "PAYMENT"
                    })
                elif next_ex_dt:
                    events.append({
                        "ticker": h["ticker"], "date": pd.to_datetime(next_ex_dt),
                        "amount": h.get("last_div_amount", 0),
                        "total": h.get("last_div_amount", 0) * h["total_shares"],
                        "type": "EX-DATE"
                    })
                else:
                    # Fallback to frequency-based estimation if yfinance metadata is missing
                    last_dt = h.get("last_div_date")
                    if last_dt:
                        # Project forward based on historical frequency (Monthly/Quarterly/etc.)
                        next_ex = pd.to_datetime(last_dt) + pd.DateOffset(months=f_map.get(h.get("div_frequency"), 3))
                        # Skip past dates to find the next upcoming distribution
                        while next_ex < today:
                            next_ex += pd.DateOffset(months=f_map.get(h.get("div_frequency"), 3))
                        
                        events.append({
                            "ticker": h["ticker"], "date": next_ex,
                            "amount": h.get("last_div_amount", 0),
                            "total": h.get("last_div_amount", 0) * h["total_shares"],
                            "type": "ESTIMATED"
                        })
            
            events = sorted(events, key=lambda x: x["date"])
            
            stats = [
                stat_card("Annual Income",   f"${annual_est:,.2f}",   "estimated next 12m"),
                stat_card("Portfolio Yield", f"{port_yield:.2f}%",    "weighted average"),
                stat_card("Total Realized",  f"${total_realized:,.2f}", "all-time received"),
            ]

            # ── 3. Calendar Grid ──────────────────────────────────────────────────
            cal_cards = []
            for e in events[:8]:
                days_left = (e["date"] - today).days
                type_color = "var(--green)" if e["type"] == "PAYMENT" else "var(--cyan)" if e["type"] == "EX-DATE" else "var(--t-sec)"
                cal_cards.append(html.Div([
                    html.Div([
                        html.Span(e["ticker"], className="cal-ticker"),
                        html.Span(e["type"], style={"fontSize": "8px", "color": type_color, "marginLeft": "8px", "fontWeight": "700", "border": f"0.5px solid {type_color}", "padding": "1px 4px", "borderRadius": "3px"})
                    ], style={"display": "flex", "alignItems": "center", "justifyContent": "center"}),
                    html.Div(f"{e['date'].strftime('%d %b')}", className="cal-date"),
                    html.Div(f"${e['total']:,.2f}", className="cal-amount"),
                    html.Div(f"In {days_left} days" if days_left > 0 else "Today", className="cal-days"),
                ], className="cal-card"))


            # ── 4. Analysis Rows ──────────────────────────────────────────────────
            # Colors for gradient
            C_START = "#1D9E75" # Theme Green
            C_END   = "#EF9F27" # Theme Orange

            # Income Rows
            income_data = sorted([{"ticker": h["ticker"], "val": h.get("annual_div", 0)} for h in holdings], key=lambda x: x["val"], reverse=True)
            income_data = [x for x in income_data if x["val"] > 0]
            max_income = max([x["val"] for x in income_data]) if income_data else 0
            n_income = len(income_data)
            
            income_rows = [
                progress_row(
                    x["ticker"], x["val"], max_income, 
                    prefix="$", 
                    color=interpolate_color(C_START, C_END, i / (n_income - 1)) if n_income > 1 else C_START
                )
                for i, x in enumerate(income_data)
            ]

            # Yield Rows
            yield_data = sorted([{"ticker": h["ticker"], "val": h.get("div_yield", 0)} for h in holdings], key=lambda x: x["val"], reverse=True)
            yield_data = [x for x in yield_data if x["val"] > 0]
            max_yield = max([x["val"] for x in yield_data]) if yield_data else 0
            n_yield = len(yield_data)
            
            yield_rows = [
                progress_row(
                    x["ticker"], x["val"], max_yield, 
                    suffix="%", 
                    color=interpolate_color(C_START, C_END, i / (n_yield - 1)) if n_yield > 1 else C_START
                )
                for i, x in enumerate(yield_data)
            ]

            # ── 5. Table ──────────────────────────────────────────────────────────
            rows = [
                html.Tr([
                    html.Td(row["date"].strftime("%Y-%m-%d"), style=_TD),
                    html.Td(row["ticker"], style={**_TD, "fontWeight": "600"}),
                    html.Td(f"${row['amount']:.4f}", style=_TD),
                    html.Td(f"{row['shares']:g}", style=_TD),
                    html.Td(f"${row['total']:,.2f}", style={**_TD, "color": GREEN, "fontWeight": "600"}),
                ])
                for _, row in df.iterrows()
            ] if not df.empty else []
            
            table = html.Table([
                html.Thead(html.Tr([html.Th(c, style=_TH) for c in ["Ex-Date", "Ticker", "Per Share", "Shares Held", "Total Amount"]])),
                html.Tbody(rows)
            ], style={"width": "100%", "borderCollapse": "collapse"})

            return stats, cal_cards, income_rows, yield_rows, table
        except Exception as e:
            logger.error(f"Failed to update dividends page: {e}")
            return [], [], [], [], "An error occurred while loading dividend data"
