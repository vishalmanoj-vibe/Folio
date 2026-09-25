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
from dash_iconify import DashIconify

logger = logging.getLogger(__name__)

from components.market_badge import market_badge
from components.ui_helpers import stat_card, stat_card_skeleton, table_skeleton
from config.constants import GREEN, RED
from core.engine.stats_engine import build_live_table_rows, compute_portfolio_stats
from services.market.market_status import is_market_open

# Columns right-aligned as numbers in the live positions table
_NUM_COLS = {
    "total_shares",
    "avg_cost",
    "last_price",
    "day_chg",
    "day_high",
    "mkt_value",
    "total_cost",
    "pnl",
    "day_pnl",
    "div_yield",
    "realized_div",
}


def _signed_money(val: float, dp: int = 2) -> str:
    """Format a signed dollar amount as +$1.23 / -$1.23 (never $-1.23)."""
    return f"{'+' if val >= 0 else '-'}${abs(val):,.{dp}f}"


def _trend_line(text: str, is_up: bool, color: str) -> html.Div:
    """Tabler-style trend line: arrow icon + text, coloured by direction."""
    return html.Div(
        [
            DashIconify(
                icon="tabler:trending-up" if is_up else "tabler:trending-down",
                width=12,
                className="trend-icon",
            ),
            html.Span(text),
        ],
        className="trend table-td-sub",
        style={"color": color},
    )


def register_callbacks(app) -> None:
    """
    Register core dashboard callbacks with the Dash application.
    """

    # ── Market status badge ───────────────────────────────────────────────────
    @app.callback(
        Output("market-status", "children"),
        Input("live-interval", "n_intervals"),
        Input("url", "pathname"),  # Ensure refresh on page change
    )
    def update_market_status(_, __):
        return market_badge()

    @app.callback(
        Output("status-indicator-dot", "className"),
        Output("last-updated-text", "children"),
        Input("portfolio-store", "data"),
        Input("url", "pathname"),  # Ensure refresh on page change
    )
    def update_last_refreshed(portfolio_data, _):
        # Pulse dot class
        is_open = is_market_open(include_auction=False)
        dot_class = "pulse-dot active" if is_open else "pulse-dot"

        if not portfolio_data or "fetched_at" not in portfolio_data:
            return dot_class, "Last refreshed: just now"

        fetched_at = portfolio_data.get("fetched_at", "Unknown")
        # Fail-safe formatting for UI badge
        try:
            if "T" in str(fetched_at):
                from datetime import datetime

                dt = datetime.fromisoformat(str(fetched_at))
                fetched_at = dt.strftime("%H:%M:%S")
            else:
                fetched_at = str(fetched_at)[:8]
        except:
            pass

        return dot_class, f"Last refreshed: {fetched_at}"

    # ── Stat cards ────────────────────────────────────────────────────────────
    @app.callback(
        Output("stat-cards", "children"),
        Input("portfolio-store", "data"),
        Input("url", "pathname"),
        prevent_initial_call=False,
    )
    def update_stats(data, url_pathname):
        import dash

        # FIX: prevent background recalculation when not on Portfolio page
        if url_pathname != "/":
            return dash.no_update
        if not data or "holdings" not in data or not data["holdings"]:
            return [stat_card_skeleton() for _ in range(8)]

        s = compute_portfolio_stats(data["holdings"])
        ps = "+" if s["total_pnl"] >= 0 else ""
        ds = "+" if s["total_day"] >= 0 else ""
        pc = GREEN if s["total_pnl"] >= 0 else RED
        dc = GREEN if s["total_day"] >= 0 else RED

        # Total Return sign/color
        ts = "+" if s["total_return_pct"] >= 0 else ""
        tc = GREEN if s["total_return_pct"] >= 0 else RED

        # Top Performer sign/color
        tps = "+" if s["top_perf_pct"] >= 0 else ""
        tpc = GREEN if s["top_perf_pct"] >= 0 else RED

        # Extract timestamp for "Today's P&L" card
        fetched_at = data.get("fetched_at", "")
        as_at = f" as at {fetched_at[:5]}" if fetched_at else ""

        return [
            stat_card(
                "Total value",
                f"${s['total_val']:,.2f}",
                f"{_signed_money(s['total_day'])} ({ds}{s['day_pct']:.2f}%) today",
                "var(--t-pri)",
                dc,
                tip="Current market value of all holdings combined.",
                trend="up" if s["total_day"] >= 0 else "down",
            ),
            stat_card(
                "Cost basis",
                f"${s['total_cost']:,.2f}",
                tip="Total amount spent buying all current holdings, excluding brokerage.",
            ),
            stat_card(
                "Unrealised P&L",
                _signed_money(s["total_pnl"]),
                f"{ps}{s['pnl_pct']:.2f}% all time",
                pc,
                pc,
                tip="Paper profit or loss since purchase. Not realised until you sell.",
                trend="up" if s["total_pnl"] >= 0 else "down",
            ),
            stat_card(
                "Today's P&L",
                _signed_money(s["total_day"]),
                f"{ds}{s['day_pct']:.2f}%{as_at}",
                dc,
                dc,
                tip="Estimated change in portfolio value since yesterday's close.",
                trend="up" if s["total_day"] >= 0 else "down",
            ),
            stat_card(
                "Total return",
                f"{ts}{s['total_return_pct']:.2f}%",
                "growth + dividends",
                tc,
                "var(--t-sec)",
                tip="The complete performance of your portfolio, combining price growth and all cash dividends received.",
            ),
            stat_card(
                "Top performer",
                s["top_perf_ticker"],
                f"{tps}{s['top_perf_pct']:.2f}% today",
                "var(--cyan)",
                tpc,
                tip="The holding with the highest percentage gain in your portfolio during today's trading session.",
                trend="up" if s["top_perf_pct"] >= 0 else "down",
            ),
            stat_card(
                "Realized dividends",
                f"${s['realized_div']:,.2f}",
                "total cash received",
                GREEN if s["realized_div"] > 0 else "var(--t-pri)",
                "var(--t-sec)",
                tip="Actual cash dividends received based on your holding history and ex-dividend dates.",
            ),
            stat_card(
                "Annual dividends",
                f"${s['annual_div']:,.2f}",
                f"{s['port_yield']:.2f}% yield",
                GREEN if s["port_yield"] > 0 else "var(--t-pri)",
                "var(--t-sec)",
                tip="Projected annual dividend income based on each ETF's trailing 12-month distributions.",
            ),
        ]

    # ── Live positions table ──────────────────────────────────────────────────
    @app.callback(
        Output("live-table", "children"),
        Input("portfolio-store", "data"),
        Input("folio-table-state-v3", "data"),
        Input("url", "pathname"),
        State("table-filter", "value"),
        State("signals-store", "data"),
        prevent_initial_call=False,
    )
    def update_live_table(data, table_state, url_pathname, filter_query, signals_store):
        import dash

        # FIX: prevent background recalculation when not on Portfolio page
        if url_pathname != "/":
            return dash.no_update
        # Extremely defensive checks for arguments
        if not isinstance(data, dict):
            logger.debug(f"live_table: data is not a dict: {type(data)}")
            return table_skeleton(rows=5)

        holdings = data.get("holdings", [])
        if not holdings:
            return table_skeleton(rows=5)

        # Load all cached sentiments from DB to avoid N+1 queries
        from data.database import get_connection

        conn = get_connection()
        sentiment_dict = {}
        try:
            rows = conn.execute("SELECT ticker, sentiment, score FROM sentiment_cache").fetchall()
            for r in rows:
                sentiment_dict[r["ticker"]] = {"sentiment": r["sentiment"], "score": r["score"]}
        except Exception as e:
            logger.warning(f"Failed to load sentiment cache for portfolio table: {e}")
        finally:
            conn.close()

        # ── Filtering ─────────────────────────────────────────────────────────
        if isinstance(filter_query, str) and filter_query:
            q = filter_query.lower()
            holdings = [
                h for h in holdings if q in h["ticker"].lower() or q in h.get("name", "").lower()
            ]
        elif filter_query:
            logger.warning(f"live_table: filter_query is not a string: {type(filter_query)}")

        if not holdings:
            return html.Div(
                "No positions match your filter",
                style={
                    "textAlign": "center",
                    "padding": "60px 20px",
                    "color": "var(--t-sec)",
                    "fontSize": "13px",
                    "border": "0.5px dashed var(--border)",
                    "borderRadius": "8px",
                    "backgroundColor": "var(--surface-2)",
                    "margin": "10px 0",
                },
            )

        # ── Sorting ───────────────────────────────────────────────────────────
        if not isinstance(table_state, dict) or not table_state:
            table_state = {"sort_col": "ticker", "sort_dir": "asc"}

        sort_col = table_state.get("sort_col", "ticker")
        sort_dir = table_state.get("sort_dir", "asc")

        # ── HARD-LOCK ──
        # If the column is 'ticker', we FORCE ascending. This prevents any
        # stale or ghost updates from flipping it to descending on load.
        if sort_col == "ticker":
            sort_dir = "asc"

        logger.debug(f"FINAL RENDER: sort_col={sort_col}, sort_dir={sort_dir}")

        rows_data = build_live_table_rows(holdings, sort_col, sort_dir)

        def pnl_td(val, pct, color, sign):
            return html.Td(
                [
                    html.Div(_signed_money(val), style={"color": color, "fontWeight": "500"}),
                    _trend_line(f"{sign}{pct:.2f}%", val >= 0, color),
                ],
                className="table-td num",
            )

        # Helper to render sortable header
        def sortable_th(label, col_id):
            is_active = sort_col == col_id
            icon = DashIconify(
                icon="tabler:arrow-down" if sort_dir == "desc" else "tabler:arrow-up", width=11
            )
            cls = "table-th table-th-sortable"
            if col_id in _NUM_COLS:
                cls += " num"
            if col_id == "ticker":
                cls += " table-sticky-col"
            return html.Th(
                [html.Span(label), html.Span(icon if is_active else "", className="sort-icon")],
                id={"type": "table-th", "index": col_id},
                className=cls,
            )

        def _sentiment_badge_td(ticker):
            sent_data = sentiment_dict.get(ticker)
            if not sent_data:
                return html.Td(
                    html.Span("—", style={"color": "var(--t-sec)"}), className="table-td"
                )
            sent_val = sent_data["sentiment"]
            sent_score = sent_data["score"]
            sent_color = (
                "var(--green)"
                if sent_val == "Positive"
                else ("var(--red)" if sent_val == "Negative" else "var(--t-sec)")
            )
            return html.Td(
                html.Span(
                    f"{sent_val} ({sent_score:+.2f})",
                    style={"color": sent_color, "fontWeight": "500", "fontSize": "12px"},
                ),
                className="table-td",
            )

        def _signal_badge_td(ticker, signals_store):
            sig = (signals_store or {}).get("raw", {}).get(ticker)
            if not sig:
                return html.Td(
                    html.Span("—", style={"color": "var(--t-sec)"}), className="table-td"
                )
            signal_val = sig.get("signal", "—")
            badge_color = (
                GREEN if signal_val == "BUY" else (RED if signal_val == "SELL" else "var(--t-sec)")
            )
            return html.Td(
                html.Span(
                    signal_val,
                    style={
                        "fontSize": "10px",
                        "fontWeight": "bold",
                        "padding": "2px 6px",
                        "borderRadius": "4px",
                        "backgroundColor": "var(--surface-2)",
                        "color": badge_color,
                        "border": f"1px solid {badge_color}",
                    },
                ),
                className="table-td",
            )

        rows = []
        for x in rows_data:
            rows.append(
                html.Tr(
                    [
                        html.Td(
                            html.A(
                                x["ticker"],
                                href=f"/positions?ticker={x['ticker']}",
                                className="ticker-link",
                            ),
                            className="table-td table-sticky-col",
                        ),
                        html.Td(
                            x["name"],
                            className="table-td",
                            style={
                                "color": "var(--t-sec)",
                                "fontSize": "12px",
                                "maxWidth": "160px",
                                "overflow": "hidden",
                                "textOverflow": "ellipsis",
                            },
                            title=x["name"],
                        ),
                        html.Td(f"{x['total_shares']:,.2f}", className="table-td num"),
                        html.Td(f"${x['avg_cost']:,.4f}", className="table-td num"),
                        html.Td(f"${x['last_price']:,.3f}", className="table-td num"),
                        html.Td(
                            [
                                html.Div(
                                    _signed_money(x["day_chg"], 3),
                                    style={"color": x["day_chg_color"], "fontWeight": "500"},
                                ),
                                _trend_line(
                                    f"{x['day_chg_sign']}{x['day_chg_pct']:.2f}%",
                                    x["day_chg"] >= 0,
                                    x["day_chg_color"],
                                ),
                            ],
                            className="table-td num",
                        ),
                        html.Td(
                            f"${x['day_high']:,.3f} / ${x['day_low']:,.3f}",
                            className="table-td num",
                            style={"color": "var(--t-sec)"},
                        ),
                        html.Td(f"${x['mkt_value']:,.2f}", className="table-td num"),
                        html.Td(f"${x['total_cost']:,.2f}", className="table-td num"),
                        pnl_td(x["pnl"], x["pnl_pct"], x["pnl_color"], x["pnl_sign"]),
                        pnl_td(
                            x["day_pnl"], x["day_chg_pct"], x["day_pnl_color"], x["day_pnl_sign"]
                        ),
                        _sentiment_badge_td(x["ticker"]),
                        _signal_badge_td(x["ticker"], signals_store),
                        html.Td(f"{x['div_yield']:.2f}%", className="table-td num"),
                        html.Td(f"${x['realized_div']:,.2f}", className="table-td num"),
                        html.Td(
                            html.Span(x["div_frequency"], className="tag"),
                            className="table-td",
                        ),
                    ]
                )
            )

        headers = [
            ("Ticker", "ticker"),
            ("Name", "name"),
            ("Shares", "total_shares"),
            ("Avg cost", "avg_cost"),
            ("Last price", "last_price"),
            ("Day change", "day_chg"),
            ("High / Low", "day_high"),
            ("Market value", "mkt_value"),
            ("Cost basis", "total_cost"),
            ("Unrealised P&L", "pnl"),
            ("Today's P&L", "day_pnl"),
            ("Div yield", "div_yield"),
            ("Realized div", "realized_div"),
            ("Freq", "div_frequency"),
        ]
        sentiment_th = html.Th("Sentiment", className="table-th")
        suggestion_th = html.Th("Suggestion", className="table-th")

        return html.Div(
            html.Table(
                [
                    html.Thead(
                        html.Tr(
                            [sortable_th(label, col_id) for label, col_id in headers[:11]]
                            + [sentiment_th, suggestion_th]
                            + [sortable_th(label, col_id) for label, col_id in headers[11:]]
                        )
                    ),
                    html.Tbody(rows),
                ],
                className="table-container",
            ),
            className="overflow-table",
        )
