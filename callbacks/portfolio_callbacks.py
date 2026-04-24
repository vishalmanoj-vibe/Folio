# callbacks/portfolio_callbacks.py
"""
callbacks/portfolio_callbacks.py
================================
Thin orchestration layer — no business logic, no math, no pandas.

Every non-trivial computation is delegated:
  stats + table rows  →  core/engine/stats_engine.py
  html rendering      →  components/ui_helpers.py
  market badge        →  services/market/market_status.py
"""

import logging
from dash import Input, Output, State, html

logger = logging.getLogger(__name__)

from config.constants import GREEN, RED
from core.engine.stats_engine import compute_portfolio_stats, build_live_table_rows
from services.market.market_status import market_badge
from components.ui_helpers import stat_card, stat_card_skeleton, table_skeleton


def register_callbacks(app) -> None:
    """
    Register core dashboard callbacks with the Dash application.
    """

    # ── Market status badge ───────────────────────────────────────────────────
    @app.callback(
        Output("market-status", "children"),
        Input("live-interval",  "n_intervals"),
        Input("url",            "pathname"),  # Ensure refresh on page change
    )
    def update_market_status(_, __):
        return market_badge()

    # ── Last updated timestamp ────────────────────────────────────────────────
    @app.callback(
        Output("last-updated",   "children"),
        Input("portfolio-store", "data"),
        Input("url",             "pathname"),  # Ensure refresh on page change
    )
    def update_last_refreshed(portfolio_data, _):
        if not portfolio_data or "fetched_at" not in portfolio_data:
            return "Last refreshed: just now"
        return f"Last refreshed: {portfolio_data['fetched_at']}"

    # ── Stat cards ────────────────────────────────────────────────────────────
    @app.callback(
        Output("stat-cards",     "children"),
        Input("portfolio-store", "data"),
    )
    def update_stats(data):
        if not data or "holdings" not in data or not data["holdings"]:
            return [stat_card_skeleton() for _ in range(6)]

        s  = compute_portfolio_stats(data["holdings"])
        ps = "+" if s["total_pnl"] >= 0 else ""
        ds = "+" if s["total_day"] >= 0 else ""
        pc = GREEN if s["total_pnl"] >= 0 else RED
        dc = GREEN if s["total_day"] >= 0 else RED

        # Extract timestamp for "Today's P&L" card
        fetched_at = data.get("fetched_at", "")
        as_at = f" as at {fetched_at[:5]}" if fetched_at else ""

        return [
            stat_card("Total value",      f"${s['total_val']:,.2f}",
                      f"{ds}${abs(s['total_day']):,.2f} ({ds}{s['day_pct']:.2f}%) today", 
                      "var(--t-pri)", dc,
                      tip="Current market value of all holdings combined."),
            stat_card("Cost basis",       f"${s['total_cost']:,.2f}",
                      tip="Total amount spent buying all current holdings, excluding brokerage."),
            stat_card("Unrealised P&L",   f"{ps}${s['total_pnl']:,.2f}",
                      f"{ps}{s['pnl_pct']:.2f}% all time", pc, pc,
                      tip="Paper profit or loss since purchase. Not realised until you sell."),
            stat_card("Today's P&L",      f"{ds}${s['total_day']:,.2f}",
                      f"{ds}{s['day_pct']:.2f}%{as_at}", dc, dc,
                      tip="Estimated change in portfolio value since yesterday's close."),
            stat_card("Realized dividends", f"${s['realized_div']:,.2f}",
                      "total cash received",
                      GREEN if s["realized_div"] > 0 else "var(--t-pri)",
                      "var(--t-sec)",
                      tip="Actual cash dividends received based on your holding history and ex-dividend dates."),
            stat_card("Annual dividends", f"${s['annual_div']:,.2f}",
                      f"{s['port_yield']:.2f}% yield",
                      GREEN if s["port_yield"] > 0 else "var(--t-pri)",
                      "var(--t-sec)",
                      tip="Projected annual dividend income based on each ETF's trailing 12-month distributions."),
        ]

    # ── Live positions table ──────────────────────────────────────────────────
    @app.callback(
        Output("live-table",        "children"),
        Input("portfolio-store",    "data"),
        State("table-filter",       "value"),
        Input("table-state-store",  "data"),
    )
    def update_live_table(data, filter_query, table_state):
        # Extremely defensive checks for arguments
        if not isinstance(data, dict):
            logger.debug(f"live_table: data is not a dict: {type(data)}")
            return table_skeleton(rows=5)

        holdings = data.get("holdings", [])
        if not holdings:
            return table_skeleton(rows=5)

        # ── Filtering ─────────────────────────────────────────────────────────
        if isinstance(filter_query, str) and filter_query:
            q = filter_query.lower()
            holdings = [
                h for h in holdings 
                if q in h["ticker"].lower() or q in h.get("name", "").lower()
            ]
        elif filter_query:
            logger.warning(f"live_table: filter_query is not a string: {type(filter_query)}")

        if not holdings:
            return html.Div(
                "No positions match your filter",
                style={
                    "textAlign": "center", "padding": "60px 20px",
                    "color": "var(--t-sec)", "fontSize": "13px",
                    "border": "0.5px dashed var(--border)", "borderRadius": "8px",
                    "backgroundColor": "var(--surface-2)", "margin": "10px 0"
                }
            )

        # ── Sorting ───────────────────────────────────────────────────────────
        if not isinstance(table_state, dict) or not table_state:
            table_state = {"sort_col": "mkt_value", "sort_dir": "desc"}
            
        sort_col = table_state.get("sort_col", "mkt_value")
        sort_dir = table_state.get("sort_dir", "desc")
        
        rows_data = build_live_table_rows(holdings, sort_col, sort_dir)

        th_style = {
            "fontSize": "11px", "color": "var(--t-sec)", "fontWeight": "600",
            "padding": "10px 12px", "textAlign": "left",
            "borderBottom": "1px solid var(--border)",
            "backgroundColor": "var(--surface)", "whiteSpace": "nowrap",
        }
        td_style = {
            "fontSize": "13px", "padding": "10px 12px",
            "borderBottom": "0.5px solid var(--border)",
            "whiteSpace": "nowrap", "color": "var(--t-pri)",
        }

        def pnl_td(val, pct, color, sign):
            return html.Td([
                html.Div(f"{sign}${val:,.2f}",
                         style={"color": color, "fontWeight": "500", "fontSize": "13px"}),
                html.Div(f"{sign}{pct:.2f}%",
                         style={"color": color, "fontSize": "11px"}),
            ], style=td_style)

        # Helper to render sortable header
        def sortable_th(label, col_id):
            is_active = sort_col == col_id
            icon = " ↓" if sort_dir == "desc" else " ↑"
            return html.Th(
                [
                    html.Span(label),
                    html.Span(icon if is_active else "", className="sort-icon")
                ],
                id={"type": "table-th", "index": col_id},
                style=th_style,
                className="table-th-sortable"
            )

        rows = []
        for x in rows_data:
            rows.append(html.Tr([
                html.Td(
                    html.A(x["ticker"], href="/positions",
                           className="ticker-link"),
                    style=td_style,
                ),
                html.Td(x["name"],
                        style={**td_style, "color": "var(--t-sec)", "fontSize": "12px",
                               "maxWidth": "160px", "overflow": "hidden",
                               "textOverflow": "ellipsis"},
                        title=x["name"]),
                html.Td(f"{x['total_shares']:,.2f}", style=td_style),
                html.Td(f"${x['avg_cost']:,.4f}",  style=td_style),
                html.Td(f"${x['last_price']:,.3f}", style=td_style),
                html.Td([
                    html.Div(f"{x['day_chg_sign']}${x['day_chg']:,.3f}",
                             style={"color": x["day_chg_color"], "fontWeight": "500",
                                    "fontSize": "13px"}),
                    html.Div(f"{x['day_chg_sign']}{x['day_chg_pct']:.2f}%",
                             style={"color": x["day_chg_color"], "fontSize": "11px"}),
                ], style=td_style),
                html.Td(f"${x['day_high']:,.3f} / ${x['day_low']:,.3f}",
                        style={**td_style, "fontSize": "12px", "color": "var(--t-sec)"}),
                html.Td(f"${x['mkt_value']:,.2f}",  style=td_style),
                html.Td(f"${x['total_cost']:,.2f}", style=td_style),
                pnl_td(x["pnl"],     x["pnl_pct"],    x["pnl_color"],     x["pnl_sign"]),
                pnl_td(x["day_pnl"], x["day_chg_pct"], x["day_pnl_color"], x["day_pnl_sign"]),
                html.Td(f"{x['div_yield']:.2f}%", style=td_style),
                html.Td(f"${x['realized_div']:,.2f}", style=td_style),
                html.Td(x["div_frequency"], style={**td_style, "fontSize": "11px", "color": "var(--t-sec)"}),
            ]))

        headers = [
            ("Ticker", "ticker"), ("Name", "name"), ("Shares", "total_shares"), 
            ("Avg cost", "avg_cost"), ("Last price", "last_price"), 
            ("Day change", "day_chg"), ("High / Low", "day_high"), 
            ("Market value", "mkt_value"), ("Cost basis", "total_cost"),
            ("Unrealised P&L", "pnl"), ("Today's P&L", "day_pnl"), 
            ("Div yield", "div_yield"), ("Realized div", "realized_div"), ("Freq", "div_frequency")
        ]

        return html.Div(
            html.Table(
                [
                    html.Thead(html.Tr([sortable_th(label, col_id) for label, col_id in headers])),
                    html.Tbody(rows),
                ],
                style={"width": "100%", "borderCollapse": "collapse"},
            ),
            style={"overflowX": "auto", "borderRadius": "8px",
                   "border": "0.5px solid var(--border)"},
        )