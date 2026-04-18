"""
callbacks/portfolio_callbacks.py
================================
Thin orchestration layer — no business logic, no math, no pandas.

Every non-trivial computation is delegated:
  stats + table rows  →  core/engine/stats_engine.py
  html rendering      →  components/ui_helpers.py
  market badge        →  services/market/market_status.py
"""

from dash import Input, Output, html

from config.constants import GREEN, RED
from core.engine.stats_engine import compute_portfolio_stats, build_live_table_rows
from services.market.market_status import market_badge
from components.ui_helpers import stat_card


def register_callbacks(app) -> None:
    """
    Register core dashboard callbacks with the Dash application.

    Handles top-level UI components like the market status badge, stat cards,
    and the live positions data table. Orchestrates data flow without business logic.

    Args:
        app: The Dash application instance.
    """

    # ── Market status badge ───────────────────────────────────────────────────
    @app.callback(
        Output("market-status", "children"),
        Input("live-interval",  "n_intervals"),
    )
    def update_market_status(_):
        return market_badge()

    # ── Last updated timestamp ────────────────────────────────────────────────
    @app.callback(
        Output("last-updated",   "children"),
        Input("portfolio-store", "data"),
    )
    def update_last_refreshed(portfolio_data):
        if not portfolio_data or "fetched_at" not in portfolio_data:
            return "Last refreshed: just now"
        return f"Last refreshed: {portfolio_data['fetched_at']}"

    # ── Stat cards ────────────────────────────────────────────────────────────
    @app.callback(
        Output("stat-cards",     "children"),
        Input("portfolio-store", "data"),
    )
    def update_stats(data):
        if not data or "holdings" not in data:
            return []

        s  = compute_portfolio_stats(data["holdings"])
        ps = "+" if s["total_pnl"] >= 0 else ""
        ds = "+" if s["total_day"] >= 0 else ""
        pc = GREEN if s["total_pnl"] >= 0 else RED
        dc = GREEN if s["total_day"] >= 0 else RED

        return [
            stat_card("Total value",      f"${s['total_val']:,.2f}",
                      tip="Current market value of all holdings combined."),
            stat_card("Cost basis",       f"${s['total_cost']:,.2f}",
                      tip="Total amount spent buying all current holdings, excluding brokerage."),
            stat_card("Unrealised P&L",   f"{ps}${s['total_pnl']:,.2f}",
                      f"{ps}{s['pnl_pct']:.2f}% all time", pc, pc,
                      tip="Paper profit or loss since purchase. Not realised until you sell."),
            stat_card("Today's P&L",      f"{ds}${s['total_day']:,.2f}",
                      "across all positions", dc, dc,
                      tip="Estimated change in portfolio value since yesterday's close."),
            stat_card("Annual dividends", f"${s['annual_div']:,.2f}",
                      f"{s['port_yield']:.2f}% yield",
                      GREEN if s["port_yield"] > 0 else "var(--t-pri)",
                      "var(--t-sec)",
                      tip="Projected annual dividend income based on each ETF's trailing 12-month distributions."),
            stat_card("Holdings", str(len(data["holdings"])),
                      tip="Number of distinct ETFs currently held in the portfolio."),
        ]

    # ── Live positions table ──────────────────────────────────────────────────
    @app.callback(
        Output("live-table",     "children"),
        Input("portfolio-store", "data"),
    )
    def update_live_table(data):
        if not data or "holdings" not in data:
            return html.P("Loading...",
                          style={"color": "var(--t-sec)", "fontSize": "13px"})

        th = {
            "fontSize": "11px", "color": "var(--t-sec)", "fontWeight": "500",
            "padding": "7px 12px", "textAlign": "left",
            "borderBottom": "1px solid var(--border)",
            "backgroundColor": "var(--surface)", "whiteSpace": "nowrap",
        }
        td = {
            "fontSize": "13px", "padding": "8px 12px",
            "borderBottom": "0.5px solid var(--border)",
            "whiteSpace": "nowrap", "color": "var(--t-pri)",
        }

        def pnl_td(val, pct, color, sign):
            return html.Td([
                html.Div(f"{sign}${val:,.2f}",
                         style={"color": color, "fontWeight": "500", "fontSize": "13px"}),
                html.Div(f"{sign}{pct:.2f}%",
                         style={"color": color, "fontSize": "11px"}),
            ], style=td)

        rows = []
        for x in build_live_table_rows(data["holdings"]):
            rows.append(html.Tr([
                html.Td(
                    html.A(x["ticker"], href=f"/etf/{x['ticker']}",
                           className="ticker-link"),
                    style=td,
                ),
                html.Td(x["name"],
                        style={**td, "color": "var(--t-sec)", "fontSize": "12px"}),
                html.Td(str(x["total_shares"]), style=td),
                html.Td(f"${x['avg_cost']:,.4f}",  style=td),
                html.Td(f"${x['last_price']:,.3f}", style=td),
                html.Td([
                    html.Div(f"{x['day_chg_sign']}${x['day_chg']:,.3f}",
                             style={"color": x["day_chg_color"], "fontWeight": "500",
                                    "fontSize": "13px"}),
                    html.Div(f"{x['day_chg_sign']}{x['day_chg_pct']:.2f}%",
                             style={"color": x["day_chg_color"], "fontSize": "11px"}),
                ], style=td),
                html.Td(f"${x['day_high']:,.3f} / ${x['day_low']:,.3f}",
                        style={**td, "fontSize": "12px", "color": "var(--t-sec)"}),
                html.Td(f"${x['mkt_value']:,.2f}",  style=td),
                html.Td(f"${x['total_cost']:,.2f}", style=td),
                pnl_td(x["pnl"],     x["pnl_pct"],    x["pnl_color"],     x["pnl_sign"]),
                pnl_td(x["day_pnl"], x["day_chg_pct"], x["day_pnl_color"], x["day_pnl_sign"]),
                html.Td(f"{x['div_yield']:.2f}%", style=td),
            ]))

        return html.Div(
            html.Table(
                [
                    html.Thead(html.Tr([
                        html.Th(c, style=th) for c in [
                            "Ticker", "Name", "Shares", "Avg cost",
                            "Last price", "Day change", "High / Low",
                            "Market value", "Cost basis",
                            "Unrealised P&L", "Today's P&L", "Div yield",
                        ]
                    ])),
                    html.Tbody(rows),
                ],
                style={"width": "100%", "borderCollapse": "collapse"},
            ),
            style={"overflowX": "auto", "borderRadius": "8px",
                   "border": "0.5px solid var(--border)"},
        )