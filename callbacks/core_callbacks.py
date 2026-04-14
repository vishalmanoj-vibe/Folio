"""
callbacks/core_callbacks.py
============================
Main data refresh, stat cards, live positions table.

Colour tokens use CSS variables (var(--surface) etc.) so the table
renders correctly in both dark and light themes.
"""

from dash import Input, Output, html

from config.constants import GREEN, RED, T_PRI, T_SEC
from config.settings import REFRESH_INTERVAL
from data.portfolio_builder import build_holdings
from services.market.fetcher import fetch_live
from services.market.status import market_badge
from components.ui_helpers import stat_card


def register_callbacks(app) -> None:

    # ── Main data refresh ─────────────────────────────────────────────────────
    @app.callback(
        Output("portfolio-store", "data"),
        Output("last-updated",    "children"),
        Output("market-status",   "children"),
        Input("live-interval",    "n_intervals"),
        Input("refresh-btn",      "n_clicks"),
        Input("period-picker",    "value"),
        Input("txn-store",        "data"),
    )
    def refresh(_, __, period, history):
        holdings = build_holdings(history or [])
        if not holdings:
            return {}, "No holdings — check your CSV.", market_badge()
        data = fetch_live(holdings, period)
        return data, f"Updated {data.get('fetched_at', '')}", market_badge()

    # ── Stat cards ────────────────────────────────────────────────────────────
    @app.callback(
        Output("stat-cards", "children"),
        Input("portfolio-store", "data"),
    )
    def update_stats(data):
        if not data or "holdings" not in data:
            return []

        h          = data["holdings"]
        total_val  = sum(x["mkt_value"]  for x in h)
        total_cost = sum(x["total_cost"] for x in h)
        total_pnl  = total_val - total_cost
        pnl_pct    = (total_pnl / total_cost * 100) if total_cost else 0
        total_day  = sum(x["day_pnl"]    for x in h)
        annual_div = sum(x["annual_div"] for x in h)
        port_yield = (annual_div / total_val * 100) if total_val else 0

        ps = "+" if total_pnl >= 0 else ""
        ds = "+" if total_day >= 0 else ""
        pc = GREEN if total_pnl >= 0 else RED
        dc = GREEN if total_day >= 0 else RED

        return [
            stat_card("Total value",      f"${total_val:,.2f}"),
            stat_card("Cost basis",       f"${total_cost:,.2f}"),
            stat_card("Unrealised P&L",   f"{ps}${total_pnl:,.2f}",
                      f"{ps}{pnl_pct:.2f}% all time", pc, pc),
            stat_card("Today's P&L",      f"{ds}${total_day:,.2f}",
                      "across all positions", dc, dc),
            stat_card("Annual dividends", f"${annual_div:,.2f}",
                      f"{port_yield:.2f}% yield",
                      GREEN if port_yield > 0 else "var(--t-pri)",
                      "var(--t-sec)"),
            stat_card("Holdings", str(len(h))),
        ]

    # ── Live positions table ──────────────────────────────────────────────────
    @app.callback(
        Output("live-table", "children"),
        Input("portfolio-store", "data"),
    )
    def update_live_table(data):
        if not data or "holdings" not in data:
            return html.P("Loading...",
                          style={"color": "var(--t-sec)", "fontSize": "13px"})

        h  = data["holdings"]
        th = {
            "fontSize":        "11px",
            "color":           "var(--t-sec)",
            "fontWeight":      "500",
            "padding":         "7px 12px",
            "textAlign":       "left",
            "borderBottom":    "1px solid var(--border)",
            "backgroundColor": "var(--surface)",
            "whiteSpace":      "nowrap",
        }
        td = {
            "fontSize":     "13px",
            "padding":      "8px 12px",
            "borderBottom": "0.5px solid var(--border)",
            "whiteSpace":   "nowrap",
            "color":        "var(--t-pri)",
        }

        def pnl_td(val, pct):
            c = GREEN if val >= 0 else RED
            s = "+" if val >= 0 else ""
            return html.Td(
                [
                    html.Div(f"{s}${val:,.2f}",
                             style={"color": c, "fontWeight": "500",
                                    "fontSize": "13px"}),
                    html.Div(f"{s}{pct:.2f}%",
                             style={"color": c, "fontSize": "11px"}),
                ],
                style=td,
            )

        rows = []
        for x in sorted(h, key=lambda v: v["mkt_value"], reverse=True):
            dc = GREEN if x["day_chg"] >= 0 else RED
            ds = "+" if x["day_chg"] >= 0 else ""
            rows.append(html.Tr([
                # Ticker links to ETF detail page
                html.Td(
                    html.A(x["ticker"], href=f"/etf/{x['ticker']}",
                           className="ticker-link"),
                    style=td,
                ),
                html.Td(x.get("name", ""),
                        style={**td, "color": "var(--t-sec)",
                               "fontSize": "12px"}),
                html.Td(str(x["total_shares"]), style=td),
                html.Td(f"${x['avg_cost']:,.4f}",  style=td),
                html.Td(f"${x['last_price']:,.3f}", style=td),
                html.Td(
                    [
                        html.Div(f"{ds}${x['day_chg']:,.3f}",
                                 style={"color": dc, "fontWeight": "500",
                                        "fontSize": "13px"}),
                        html.Div(f"{ds}{x['day_chg_pct']:.2f}%",
                                 style={"color": dc, "fontSize": "11px"}),
                    ],
                    style=td,
                ),
                html.Td(f"${x['day_high']:,.3f} / ${x['day_low']:,.3f}",
                        style={**td, "fontSize": "12px",
                               "color": "var(--t-sec)"}),
                html.Td(f"${x['mkt_value']:,.2f}", style=td),
                html.Td(f"${x['total_cost']:,.2f}", style=td),
                pnl_td(x["pnl"],     x["pnl_pct"]),
                pnl_td(x["day_pnl"], x["day_chg_pct"]),
                html.Td(f"{x['div_yield']:.2f}%", style=td),
            ]))

        return html.Div(
            html.Table(
                [
                    html.Thead(html.Tr([
                        html.Th(c, style=th)
                        for c in [
                            "Ticker", "Name", "Shares", "Avg cost",
                            "Last price", "Day change", "High / Low",
                            "Market value", "Cost basis",
                            "Unrealised P&L", "Today's P&L", "Div yield",
                        ]
                    ])),
                    html.Tbody(rows),
                ],
                style={"width": "100%", "borderCollapse": "collapse",
                       "overflowX": "auto", "display": "block"},
            ),
            style={
                "overflowX":    "auto",
                "borderRadius": "8px",
                "border":       "0.5px solid var(--border)",
            },
        )