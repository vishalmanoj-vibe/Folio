import logging
from dash import Input, Output, html

from config import GREEN, RED, T_PRI, T_SEC, SURFACE, BORDER, get_theme
from data.portfolio_builder import build_holdings
from services.market_data import fetch_live
from services.market_status import market_badge
from components.ui_helpers import stat_card

logger = logging.getLogger(__name__)


def register_callbacks(app) -> None:

    # ── Main data refresh ─────────────────────────────────────────────────────
    @app.callback(
        Output("portfolio-store", "data"),
        Output("last-updated",    "children"),
        Output("market-status",   "children"),
        Input("live-interval",    "n_intervals"),
        Input("refresh-btn",      "n_clicks"),
        Input("period-picker",    "value"),
        Input("txn-store",        "data"),   # re-fetch when user adds/edits a transaction
    )
    def refresh(_, __, period, history):
        holdings = build_holdings(history or [])
        if not holdings:
            logger.info("No holdings found — returning empty state")
            return {}, "No holdings — check your CSV.", market_badge()
        data = fetch_live(holdings, period)
        logger.info("Dashboard refreshed at %s", data.get("fetched_at", ""))
        return data, f"Updated {data.get('fetched_at', '')}", market_badge()

    # ── Stat cards ────────────────────────────────────────────────────────────
    @app.callback(
        Output("stat-cards",            "children"),
        Output("stat-cards-performers", "children"),
        Input("portfolio-store", "data"),
    )
    def update_stats(data):
        if not data or "holdings" not in data:
            return [], []

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

        max_h = max(h, key=lambda x: x["pnl"])
        min_h = min(h, key=lambda x: x["pnl"])
        bp_sign = "+" if max_h["pnl"] >= 0 else ""
        wp_sign = "+" if min_h["pnl"] >= 0 else ""

        summary_cards = [
            stat_card("Total value",      f"${total_val:,.2f}"),
            stat_card("Cost basis",       f"${total_cost:,.2f}"),
            stat_card("Unrealised P&L",   f"{ps}${total_pnl:,.2f}",
                      f"{ps}{pnl_pct:.2f}% all time", pc, pc),
            stat_card("Today's P&L",      f"{ds}${total_day:,.2f}",
                      "across all positions", dc, dc),
            stat_card("Annual dividends", f"${annual_div:,.2f}",
                      f"{port_yield:.2f}% yield",
                      GREEN if port_yield > 0 else T_PRI, T_SEC),
            stat_card("Holdings",         str(len(h))),
        ]

        performer_cards = [
            stat_card(
                "Best performer",
                f"{max_h['ticker']}  {bp_sign}${max_h['pnl']:,.2f}",
                f"{bp_sign}{max_h['pnl_pct']:.2f}% all time",
                GREEN, GREEN,
            ),
            stat_card(
                "Worst performer",
                f"{min_h['ticker']}  {wp_sign}${min_h['pnl']:,.2f}",
                f"{wp_sign}{min_h['pnl_pct']:.2f}% all time",
                RED, RED,
            ),
        ]

        return summary_cards, performer_cards

    # ── Live positions table ──────────────────────────────────────────────────
    @app.callback(
        Output("live-table",     "children"),
        Input("portfolio-store", "data"),
        Input("theme-store",     "data"),
    )
    def update_live_table(data, theme):
        t_ = get_theme(theme or "dark")
        SURFACE = t_["SURFACE"]
        BORDER  = t_["BORDER"]
        T_SEC   = t_["T_SEC"]

        if not data or "holdings" not in data:
            return html.P("Loading...", style={"color": T_SEC, "fontSize": "13px"})

        h = data["holdings"]

        # Identify best / worst for row highlighting
        max_pnl = max(h, key=lambda x: x["pnl"])
        min_pnl = min(h, key=lambda x: x["pnl"])

        th = {
            "fontSize": "11px", "color": T_SEC, "fontWeight": "500",
            "padding": "7px 12px", "textAlign": "left",
            "borderBottom": f"1px solid {BORDER}",
            "backgroundColor": SURFACE, "whiteSpace": "nowrap",
        }
        td = {
            "fontSize": "13px", "padding": "8px 12px",
            "borderBottom": f"0.5px solid {BORDER}", "whiteSpace": "nowrap",
        }

        def pnl_td(val, pct):
            c = GREEN if val >= 0 else RED
            s = "+" if val >= 0 else ""
            return html.Td(
                [
                    html.Div(f"{s}${val:,.2f}", style={"color": c, "fontWeight": "500", "fontSize": "13px"}),
                    html.Div(f"{s}{pct:.2f}%",  style={"color": c, "fontSize": "11px"}),
                ],
                style=td,
            )

        rows = []
        for x in sorted(h, key=lambda v: v["mkt_value"], reverse=True):
            dc = GREEN if x["day_chg"] >= 0 else RED
            ds = "+" if x["day_chg"] >= 0 else ""

            # Subtle left-border highlight for best / worst
            is_best  = x["ticker"] == max_pnl["ticker"]
            is_worst = x["ticker"] == min_pnl["ticker"]
            row_style = {}
            if is_best:
                row_style = {"borderLeft": f"3px solid {GREEN}", "backgroundColor": "rgba(29,158,117,0.06)"}
            elif is_worst:
                row_style = {"borderLeft": f"3px solid {RED}",   "backgroundColor": "rgba(226,75,74,0.06)"}

            # Ticker cell — badge for best/worst
            ticker_content = [html.Span(x["ticker"], style={"fontWeight": "500"})]
            if is_best:
                ticker_content.append(html.Span(
                    " ▲ best",
                    style={"fontSize": "10px", "color": GREEN, "marginLeft": "4px"},
                ))
            elif is_worst:
                ticker_content.append(html.Span(
                    " ▼ worst",
                    style={"fontSize": "10px", "color": RED, "marginLeft": "4px"},
                ))

            rows.append(html.Tr(
                [
                    html.Td(ticker_content, style=td),
                    html.Td(x.get("name", ""),  style={**td, "color": T_SEC, "fontSize": "12px"}),
                    html.Td(str(x["total_shares"]), style=td),
                    html.Td(f"${x['avg_cost']:,.4f}",  style=td),
                    html.Td(f"${x['last_price']:,.3f}", style=td),
                    html.Td(
                        [
                            html.Div(f"{ds}${x['day_chg']:,.3f}",
                                     style={"color": dc, "fontWeight": "500", "fontSize": "13px"}),
                            html.Div(f"{ds}{x['day_chg_pct']:.2f}%",
                                     style={"color": dc, "fontSize": "11px"}),
                        ],
                        style=td,
                    ),
                    html.Td(f"${x['day_high']:,.3f} / ${x['day_low']:,.3f}",
                            style={**td, "fontSize": "12px", "color": T_SEC}),
                    html.Td(f"${x['mkt_value']:,.2f}", style=td),
                    html.Td(f"${x['total_cost']:,.2f}", style=td),
                    # Unrealised P&L $ + % (all-time)
                    pnl_td(x["pnl"], x["pnl_pct"]),
                    # Today's P&L $ + %
                    pnl_td(x["day_pnl"], x["day_chg_pct"]),
                    html.Td(f"{x['div_yield']:.2f}%", style=td),
                ],
                style=row_style,
            ))

        return html.Div(
            [
                html.Table(
                    [
                        html.Thead(html.Tr([
                            html.Th(c, style=th)
                            for c in [
                                "Ticker", "Name", "Shares", "Avg cost", "Last price",
                                "Day change", "High / Low", "Market value", "Cost basis",
                                "Unrealised P&L (all time)", "Today's P&L", "Div yield",
                            ]
                        ])),
                        html.Tbody(rows),
                    ],
                    style={"width": "100%", "borderCollapse": "collapse",
                           "overflowX": "auto", "display": "block"},
                ),
            ],
            style={"overflowX": "auto", "borderRadius": "8px",
                   "border": f"0.5px solid {BORDER}"},
        )