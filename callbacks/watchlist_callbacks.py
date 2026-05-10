# callbacks/watchlist_callbacks.py
import logging
import dash
from dash import Input, Output, State, html, dcc, ctx, ALL
import plotly.graph_objects as go
from data.watchlist_repository import WatchlistRepository
from services.market.data_fetcher import fetch_live, get_etf_name
from config.constants import GREEN, RED

import pandas as pd
logger = logging.getLogger(__name__)
from components.ui_helpers import tech_signal_badges
from components.charts.helpers import create_empty_fig
repo = WatchlistRepository()

def register_callbacks(app) -> None:
    """
    Register watchlist-specific callbacks.
    """

    # ── Watchlist Store Management ──────────────────────────────────────────
    @app.callback(
        Output("watchlist-store", "data"),
        Output("watchlist-input", "value"),
        Input("watchlist-add-btn", "n_clicks"),
        Input({"type": "watchlist-remove-btn", "index": ALL}, "n_clicks"),
        Input("watchlist-input", "n_submit"),
        Input("live-interval", "n_intervals"),
        Input("startup-interval", "n_intervals"),
        State("watchlist-input", "value"),
        State("watchlist-store", "data"),
        prevent_initial_call=True,
    )
    def update_watchlist_store(n_add, n_remove_list, n_submit, n_interval, n_startup, ticker_input, current_data):
        triggered_id = ctx.triggered_id

        # 1. Add Ticker
        if triggered_id in ("watchlist-add-btn", "watchlist-input"):
            if not ticker_input:
                return dash.no_update, dash.no_update
            repo.add_ticker(ticker_input.strip().upper())
            
        # 2. Remove Ticker (Pattern Matching)
        elif isinstance(triggered_id, dict) and triggered_id.get("type") == "watchlist-remove-btn":
            trigger_val = ctx.triggered[0]["value"]
            if not trigger_val or int(trigger_val) < 1:
                return dash.no_update, dash.no_update
            ticker_to_remove = triggered_id.get("index")
            repo.remove_ticker(ticker_to_remove)

        # 3. Fetch Live Data (Periodic or after mutation)
        watchlist_items = repo.load_watchlist()

        if not watchlist_items:
            return {"holdings": [], "histories": {}, "fetched_at": None}, dash.no_update

        # Create dummy holdings for fetch_live
        holdings = [
            {
                "ticker": item["ticker"],
                "ticker_yf": f"{item['ticker']}.AX" if "." not in item["ticker"] else item["ticker"],
                "total_shares": 0,
                "avg_cost": 0,
                "total_cost": 0,
                "buy_tranches": []
            }
            for item in watchlist_items
        ]
        
        try:
            live_data = fetch_live(holdings, "1y", record_snapshots=False, use_disk_history=True)
            triggered = ctx.triggered_id
            clear = "" if triggered in ("watchlist-add-btn", "watchlist-input") else dash.no_update
            return live_data, clear
        except Exception as e:
            logger.error(f"Watchlist live fetch failed: {e}")
            return dash.no_update, dash.no_update

    # ── Render Table ────────────────────────────────────────────────────────
    @app.callback(
        Output("watchlist-table-container", "children"),
        Output("watchlist-msg", "children"),
        Input("watchlist-store", "data"),
        Input("url", "pathname"),
        Input("watchlist-selected-ticker", "data"),
        Input("watchlist-signals-store", "data"),
        prevent_initial_call=False,
    )
    def render_watchlist_table(data, pathname, selected_ticker, signals_store):
        # Multi-page safety: only render if on the watchlist page
        if pathname.rstrip("/") != "/watchlist":
            return dash.no_update, dash.no_update

        if not data or "holdings" not in data or not data["holdings"]:
            return html.Div("Your watchlist is empty. Add a ticker above to get started.", 
                            className="c-muted", style={"padding": "40px", "textAlign": "center"}), ""

        holdings = data["holdings"]
        
        th_style = {
            "fontSize": "11px", "color": "var(--t-sec)", "fontWeight": "600",
            "padding": "12px", "textAlign": "left",
            "borderBottom": "1px solid var(--border)",
            "backgroundColor": "var(--surface)",
        }
        td_style = {
            "fontSize": "13px", "padding": "12px",
            "borderBottom": "0.5px solid var(--border)",
            "color": "var(--t-pri)",
        }

        rows = []
        for h in holdings:
            ticker = h["ticker"]
            name = h.get("name", ticker)
            price = h.get("last_price", 0)
            chg = h.get("day_chg", 0)
            chg_pct = h.get("day_chg_pct", 0)
            day_high = h.get("day_high", 0)
            day_low  = h.get("day_low", 0)
            div_yield = h.get("div_yield", 0)
            next_div  = h.get("next_div_date") or "—"
            
            color_cls = "c-pos" if chg >= 0 else "c-neg"
            sign = "+" if chg >= 0 else ""

            # Signal badge
            sig = (signals_store or {}).get("raw", {}).get(ticker)
            if sig:
                signal_val = sig.get("signal", "—")
                badge_color = GREEN if signal_val == "BUY" else (RED if signal_val == "SELL" else "var(--t-sec)")
                signal_cell = html.Span(
                    signal_val,
                    style={
                        "fontSize": "10px", "fontWeight": "bold",
                        "padding": "2px 6px", "borderRadius": "4px",
                        "backgroundColor": "var(--surface-2)",
                        "color": badge_color, "border": f"1px solid {badge_color}",
                    }
                )
            else:
                signal_cell = html.Span("—", style={"color": "var(--t-sec)", "fontSize": "12px"})
            
            # High-density click target
            is_active = (ticker == selected_ticker)

            row_style = {
                "backgroundColor": "var(--cyan-bg)" if is_active else "transparent",
                "transition": "background-color 0.15s",
            }
            rows.append(html.Tr([
                html.Td(
                    html.Div(ticker, 
                             id={"type": "watchlist-select-ticker", "index": ticker}, 
                             className="ticker-link", 
                             style={
                                 "cursor": "pointer",
                                 "display": "inline-block",
                                 "color": "var(--cyan)",
                                 "fontWeight": "600" if is_active else "400",
                             },
                             n_clicks=0),
                    style=td_style
                ),
                html.Td(name, style={**td_style, "color": "var(--t-sec)", "fontSize": "12px"}),
                html.Td(f"${price:,.3f}", style=td_style),
                html.Td([
                    html.Span(f"{sign}${abs(chg):,.3f}", className=color_cls, style={"fontWeight": "500"}),
                    html.Span(f" ({sign}{chg_pct:.2f}%)", className=color_cls, style={"fontSize": "11px", "marginLeft": "4px"})
                ], style=td_style),
                html.Td(
                    f"${day_high:,.3f} / ${day_low:,.3f}",
                    style={**td_style, "fontSize": "11px", "color": "var(--t-sec)"}
                ),
                html.Td(
                    html.Div(
                        f"{div_yield:.2f}%",
                        style={"fontWeight": "500",
                               "color": "var(--green)" if div_yield > 3 else "var(--t-pri)"}
                    ),
                    style=td_style),
                html.Td(signal_cell, style=td_style),
                html.Td(
                    html.Button("✕", id={"type": "watchlist-remove-btn", "index": ticker}, 
                                className="btn-sm", style={"color": "var(--red)", "padding": "2px 8px"}),
                    style={**td_style, "textAlign": "right"}
                )
            ], style=row_style))

        table = html.Table([
            html.Thead(html.Tr([
                html.Th("Ticker",     style=th_style),
                html.Th("Name",       style=th_style),
                html.Th("Price",      style=th_style),
                html.Th("Day Change", style=th_style),
                html.Th("High / Low", style=th_style),
                html.Th("Div Yield",  style=th_style),
                html.Th("Suggestion", style=th_style),
                html.Th("",           style={**th_style, "textAlign": "right"}),
            ])),
            html.Tbody(rows)
        ], style={"width": "100%", "borderCollapse": "collapse"})

        return table, ""

    # ── Handle Ticker Selection ─────────────────────────────────────────────
    @app.callback(
        Output("watchlist-selected-ticker", "data"),
        Input({"type": "watchlist-select-ticker", "index": ALL}, "n_clicks"),
        State("watchlist-store", "data"),
        State("watchlist-selected-ticker", "data"),
        prevent_initial_call=True,
    )
    def select_watchlist_ticker(n_clicks_list, data, current):
        # 1. Only act on a real user click (n_clicks > 0)
        if (
            ctx.triggered_id
            and isinstance(ctx.triggered_id, dict)
            and ctx.triggered_id.get("type") == "watchlist-select-ticker"
        ):
            click_val = ctx.triggered[0].get("value") or 0
            if int(click_val) > 0:
                return ctx.triggered_id["index"]
        return current

    @app.callback(
        Output("watchlist-selected-ticker", "data",
               allow_duplicate=True),
        Input("watchlist-store", "data"),
        State("watchlist-selected-ticker", "data"),
        prevent_initial_call='initial_duplicate',
    )
    def seed_default_ticker(data, current):
        if current is not None:
            return dash.no_update
        if data and "holdings" in data and data["holdings"]:
            return data["holdings"][0]["ticker"]
        return dash.no_update

    # ── Watchlist Chart ─────────────────────────────────────────────────────
    @app.callback(
        Output("watchlist-chart", "figure"),
        Output("watchlist-chart-title", "children"),
        Input("watchlist-selected-ticker", "data"),
        State("watchlist-store", "data"),
        Input("url", "pathname"),
        Input("theme-store", "data"),
        Input("watchlist-period-store", "data"),
        prevent_initial_call=False
    )
    def update_watchlist_chart(selected_ticker, data, pathname, theme, period):
        # Resolve theme tokens
        from config.constants import get_theme
        t_ = get_theme(theme or "dark")
        T_SEC = t_["T_SEC"]
        CYAN = t_["CYAN"]
        BORDER_COL = t_["BORDER"]

        # Multi-page safety
        if pathname.rstrip("/") != "/watchlist":
            return create_empty_fig("", height=300, theme_tokens=t_), "Price Performance"

        if not data or "histories" not in data or not data["histories"]:
            return create_empty_fig("Fetching price history...", height=300, theme_tokens=t_), "Price Performance"

        if not selected_ticker or selected_ticker not in data["histories"]:
            return create_empty_fig("Select a ticker to view history", height=300, theme_tokens=t_), "Price Performance"

        history = data["histories"][selected_ticker]
        
        if not history:
            return create_empty_fig(f"No historical data available for {selected_ticker}", height=300, theme_tokens=t_), "Price Performance"

        df = pd.DataFrame(history)
        df["Date"] = pd.to_datetime(df["Date"])

        # Filter by selected period
        period = period or "1y"
        from datetime import timedelta
        period_map = {
            "1mo": timedelta(days=30),
            "6mo": timedelta(days=182),
            "1y":  timedelta(days=365),
            "5y":  timedelta(days=1825),
        }
        if period in period_map:
            cutoff = pd.Timestamp.now() - period_map[period]
            df = df[df["Date"] >= cutoff]
        # "max" falls through with no filter — all records shown

        if df.empty:
            return create_empty_fig(f"No data for {selected_ticker} in this period", height=300, theme_tokens=t_), f"Price Performance: {selected_ticker}"
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df["Date"],
            y=df["Close"],
            mode="lines",
            line=dict(color=CYAN, width=2),
            fill="tozeroy",
            fillcolor=f"rgba(0, 201, 167, 0.05)", 
            name=selected_ticker
        ))

        layout_args = t_["PLOTLY_BASE"].copy()
        layout_args["margin"] = dict(t=10, b=10, l=10, r=10)
        layout_args["height"] = 300
        layout_args["xaxis"] = dict(
            showgrid=False,
            showline=False,
            zeroline=False,
            tickfont=dict(color=T_SEC, size=10),
        )
        y_min = df["Close"].min()
        y_max = df["Close"].max()
        
        layout_args["yaxis"] = dict(
            showgrid=True,
            gridcolor=BORDER_COL,
            showline=False,
            zeroline=False,
            tickfont=dict(color=T_SEC, size=10),
            side="right",
            range=[y_min * 0.98, y_max * 1.02]
        )
        layout_args["hovermode"] = "x unified"
        layout_args["showlegend"] = False
        
        fig.update_layout(**layout_args)

        return fig, f"Price Performance: {selected_ticker}"

    # ── Sync period button clicks to store ──────────────────────────────────
    @app.callback(
        Output("watchlist-period-store", "data"),
        Input({"type": "wl-period-btn", "index": ALL}, "n_clicks"),
        prevent_initial_call=True,
    )
    def sync_watchlist_period(n_clicks_list):
        if not ctx.triggered_id:
            return dash.no_update
        if not isinstance(ctx.triggered_id, dict):
            return dash.no_update
        return ctx.triggered_id["index"]

    # ── Update period button active styles ──────────────────────────────────
    @app.callback(
        Output({"type": "wl-period-btn", "index": ALL}, "className"),
        Input("watchlist-period-store", "data"),
    )
    def update_period_btn_styles(active_period):
        periods = ["1mo", "6mo", "1y", "5y", "max"]
        return [
            "btn-sm btn-primary" if p == (active_period or "1y") else "btn-sm"
            for p in periods
        ]

    @app.callback(
        [Output("watchlist-stat-cards", "children"), 
         Output("watchlist-tech-signals-container", "children"),
         Output("watchlist-ai-insight-container", "children")],
        Input("watchlist-selected-ticker", "data"),
        State("watchlist-store", "data"),
        Input("watchlist-signals-store", "data"),
        prevent_initial_call=False,
    )
    def render_watchlist_stat_cards(selected_ticker, data, signals_store):
        from components.ui_helpers import stat_card
        if not selected_ticker or not data or "holdings" not in data:
            return [], None, None

        h = next(
            (x for x in data["holdings"] if x["ticker"] == selected_ticker),
            None
        )
        if not h:
            return [], None, None

        price      = h.get("last_price", 0)
        day_chg    = h.get("day_chg", 0)
        day_chg_pct = h.get("day_chg_pct", 0)
        div_yield  = h.get("div_yield", 0)
        annual_div = h.get("annual_div", 0)
        day_high   = h.get("day_high", 0)
        day_low    = h.get("day_low", 0)
        freq       = h.get("div_frequency", "—")

        day_color = "var(--green)" if day_chg >= 0 else "var(--red)"
        day_sign  = "+" if day_chg >= 0 else ""

        cards = [
            stat_card(
                "Last Price",
                f"${price:,.3f}",
                f"High ${day_high:,.3f}  ·  Low ${day_low:,.3f}",
            ),
            stat_card(
                "Day Change",
                f"{day_sign}${abs(day_chg):,.3f}",
                f"{day_sign}{day_chg_pct:.2f}%",
                color=day_color,
                sub_color=day_color,
            ),
            stat_card(
                "Div Yield",
                f"{div_yield:.2f}%",
                f"${annual_div:,.2f} per share/yr",
                color="var(--green)" if div_yield > 0 else "var(--t-pri)",
            ),
            stat_card(
                "Frequency",
                freq,
                "distribution schedule",
            ),
        ]

        # Append AI Insight card if signals exist for this ticker
        ai_card = None
        if signals_store and "ai" in signals_store and selected_ticker in signals_store["ai"]:
            ai_data = signals_store["ai"][selected_ticker]
            raw_sig = signals_store.get("raw", {}).get(selected_ticker, {})
            verdict = ai_data.get("verdict", "Mixed")
            v_color = GREEN if verdict == "Confident" else (RED if verdict == "Risk flagged" else "var(--t-sec)")

            # Build children dynamically — never pass None into a children list
            ai_children = [
                html.Div([
                    html.Span("🤖", style={"marginRight": "8px"}),
                    "AI Analyst Insight"
                ], className="etf-detail-label", style={"display": "flex", "alignItems": "center"}),
                html.Div(verdict, className="etf-detail-value", style={"color": v_color, "fontSize": "16px"}),
                html.Div(ai_data.get("explanation", ""),
                         style={"marginTop": "8px", "whiteSpace": "normal", "fontSize": "13px", "color": "var(--t-sec)", "lineHeight": "1.5"}),
            ]
            if ai_data.get("risks"):
                ai_children.append(html.Div([
                    html.Div(f"• {r}", style={"color": "var(--red)", "marginTop": "4px", "fontSize": "12px"}) for r in ai_data["risks"]
                ]))
            if raw_sig:
                ai_children.append(html.Div([
                    html.Div(f"Technical Score: {raw_sig.get('score', 0.0):.2f}",
                             style={"marginTop": "8px", "fontWeight": "bold", "color": "var(--cyan)", "fontSize": "13px"}),
                    html.Div([html.Div(f"• {r}") for r in raw_sig.get("reasons", [])],
                             style={"marginTop": "4px", "color": "var(--t-sec)", "fontSize": "12px"})
                ]))

            ai_card = html.Div(ai_children, className="etf-detail-card", style={"marginTop": "10px", "marginBottom": "24px", "width": "100%"})

        # Generate Tech Signals
        tech_signals = None
        history = data.get("histories", {}).get(selected_ticker, [])
        if history:
            tech_signals = tech_signal_badges(selected_ticker, history)

        return cards, tech_signals, ai_card

    @app.callback(
        Output("watchlist-notes-input", "value"),
        Input("watchlist-selected-ticker", "data"),
    )
    def load_note_for_ticker(selected_ticker):
        if not selected_ticker:
            return ""
        notes = repo.load_notes()
        return notes.get(selected_ticker, "")

    @app.callback(
        Output("watchlist-notes-msg", "children"),
        Input("watchlist-notes-save-btn", "n_clicks"),
        State("watchlist-selected-ticker", "data"),
        State("watchlist-notes-input", "value"),
        prevent_initial_call=True,
    )
    def save_note_for_ticker(n_clicks, selected_ticker, note_text):
        if not selected_ticker:
            return "No ticker selected"
        repo.save_note(selected_ticker, note_text or "")
        return f"✓ Saved"

