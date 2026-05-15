# callbacks/chart_callbacks.py
"""
callbacks/chart_callbacks.py
=============================
Chart callbacks.
"""

import logging
import plotly.graph_objects as go
from dash import Input, Output, State, ALL, html
import dash_mantine_components as dmc

from config.constants import COLORS, get_theme
from services.history_cache import get_latest_histories
from components.charts import (
    build_pnl_history_figure,
    build_price_chart_figure,
    build_corr_figure,
    build_portfolio_treemap,
    build_performance_lollipops,
)
from components.charts.intel_holdings import build_holdings_bubble_chart
from components.ui_helpers import chart_skeleton, progress_row, interpolate_color
from components.charts.helpers import create_empty_fig
from services.intelligence_service import (
    compute_risk_metrics,
    fetch_etf_sector_weights,
    fetch_etf_geo_weights,
    holdings_blended_data,
)

logger = logging.getLogger(__name__)

def register_callbacks(app) -> None:
    """
    Register chart-related callbacks with the Dash application.
    """

    # ── Ticker selector options ───────────────────────────────────────────────
    @app.callback(
        Output("ticker-selector", "data"),
        Input("portfolio-store",  "data"),
        Input("url","pathname"),
    )
    def update_ticker_options(data, pathname):
        import dash
        if pathname != "/": return dash.no_update
        if not data or "holdings" not in data or not data["holdings"]:
            return ["Portfolio"]
        
        tickers = ["Portfolio"] + sorted([h["ticker"] for h in data["holdings"]])
        return [{"label": t, "value": t} for t in tickers]


    # ── P&L history ───────────────────────────────────────────────────────────
    @app.callback(
        Output("pnl-history-chart", "figure"),
        Output("benchmark-pending-store", "data", allow_duplicate=True),
        Input("portfolio-store",    "data"),
        Input("theme-store",        "data"),
        # FIX: change to State to prevent double-rendering when portfolio-store updates
        State("period-store",       "data"),
        Input("pnl-mode-store",     "data"),
        Input("ticker-store",       "data"),
        Input("url",                "pathname"),
        Input("task-poll-interval", "n_intervals"),
        State("benchmark-pending-store", "data"),
        prevent_initial_call=True,
    )
    def pnl_history_chart(data, theme, period, mode, selected, pathname, n_tasks, bench_pending):
        import dash
        if pathname != "/": return dash.no_update, dash.no_update
        t_       = get_theme(theme or "dark")
        period   = period or "max"
        mode     = mode or "pct"
        selected = selected or "Portfolio"

        if not data or "holdings" not in data or not data["holdings"]:
            return create_empty_fig("No holdings data available", height=450, theme_tokens=t_), dash.no_update

        # ── Lazy Fetch & P&L Injection ──
        from data.repository import PortfolioRepository
        txn_data = PortfolioRepository().load_transactions()
        
        from services.market.data_fetcher import fetch_portfolio_history
        from core.engine.portfolio_engine import build_holdings, compute_tranche_pnl
        import pandas as pd
        # We need tranches for the P&L history calculation
        holdings = build_holdings(txn_data, include_tranches=True)
        # Re-merge with current live metrics (last_price, mkt_value) from portfolio-store
        price_map = {h["ticker"]: h for h in data.get("holdings", [])}
        for h in holdings:
            if h["ticker"] in price_map:
                h.update(price_map[h["ticker"]])
        
        # ── Start Date Optimization ──
        # If 'max' is selected, truncate to the date of the first purchase 
        # to prevent processing irrelevant historical data.
        fetch_period = period
        if period == "max":
            all_buy_dates = []
            for h in holdings:
                all_buy_dates.extend([pd.to_datetime(t["date"]) for t in h.get("buy_tranches", [])])
            if all_buy_dates:
                fetch_period = min(all_buy_dates)

        # Fetch histories for all tickers needed
        histories = fetch_portfolio_history(holdings, fetch_period)
        
        # Populate tranches with P&L series for the chart builder
        for h in holdings:
            ticker = h["ticker"]
            history_list = histories.get(ticker, [])
            if history_list:
                df_h = pd.DataFrame(history_list)
                if not df_h.empty:
                    df_h["Date"] = pd.to_datetime(df_h["Date"])
                    close_s = df_h.set_index("Date")["Close"]
                    # compute_tranche_pnl expects a Series with DatetimeIndex
                    h["tranches"] = compute_tranche_pnl(close_s, h.get("buy_tranches", []))

        # ── Benchmark Check ──
        from data.cache_manager import get_benchmarks_db
        from data.database import enqueue_task, get_connection
        
        bench_data = get_benchmarks_db()
        new_bench_pending = bench_pending
        
        if bench_data is None:
            # Queue task if not already pending
            conn = get_connection()
            try:
                row = conn.execute("SELECT task_id FROM worker_tasks WHERE task_type = 'fetch_benchmarks' AND status IN ('pending', 'running')").fetchone()
                if row:
                    new_bench_pending = row["task_id"]
                else:
                    new_bench_pending = enqueue_task("fetch_benchmarks", {"period": "max"}, priority=8)
            finally:
                conn.close()
        else:
            new_bench_pending = None

        fig = build_pnl_history_figure(holdings, mode, period, t_, selected)
        
        # ── Memory Hygiene ──
        import gc
        gc.collect()
        
        return fig, new_bench_pending

    # ── Normalised price history ──────────────────────────────────────────────
    @app.callback(
        Output("price-chart",    "figure"),
        Input("portfolio-store", "data"),
        Input("theme-store",     "data"),
        # FIX: change to State to prevent double-rendering
        State("analytics-period-store", "data"),
        Input("url",             "pathname"),
    )
    def price_chart(data, theme, period, pathname):
        import dash
        if pathname.rstrip("/") != "/analytics": return dash.no_update
        t_ = get_theme(theme or "dark")
        period = period or "max"
        if not data or "holdings" not in data:
            return create_empty_fig("No portfolio data available", height=400, theme_tokens=t_)
            
        from services.market.data_fetcher import fetch_portfolio_history
        histories = fetch_portfolio_history(data["holdings"], period)
        if not histories:
            return create_empty_fig("No price history available", height=400, theme_tokens=t_)
            
        holdings = data.get("holdings", [])
        return build_price_chart_figure(histories, period, t_, holdings)

    # ── Portfolio Treemap ─────────────────────────────────────────────────────
    @app.callback(
        Output("portfolio-treemap", "figure"),
        Input("portfolio-store",    "data"),
        Input("theme-store",        "data"),
        Input("treemap-mode-store", "data"),
        Input("url",                "pathname"),
    )
    def portfolio_treemap(data, theme, mode, pathname):
        import dash
        if pathname.rstrip("/") != "/analytics": return dash.no_update
        t_ = get_theme(theme or "dark")
        mode = mode or "sector"
        if not data or "holdings" not in data or not data["holdings"]:
            return create_empty_fig("No holdings data available", height=450, theme_tokens=t_)
        
        mode = mode or "sector"
        sector_map = {}
        geo_map = {}
        
        if mode == "sector":
            for h in data["holdings"]:
                ticker_yf = h.get("ticker_yf", h["ticker"] + ".AX")
                sector_map[h["ticker"]] = fetch_etf_sector_weights(ticker_yf)
        elif mode == "geo":
            for h in data["holdings"]:
                ticker_yf = h.get("ticker_yf", h["ticker"] + ".AX")
                geo_map[h["ticker"]] = fetch_etf_geo_weights(ticker_yf)
            
        return build_portfolio_treemap(
            data["holdings"], t_, 
            mode=mode, 
            sector_data=sector_map, 
            geo_data=geo_map
        )


    # ── Analytics Risk ────────────────────────────────────────────────────────
    @app.callback(
        Output("analytics-vol-chart",    "children"),
        Input("portfolio-store",         "data"),
        Input("theme-store",             "data"),
        # FIX: change to State to prevent double-rendering
        State("analytics-period-store", "data"),
        Input("url",                     "pathname"),
    )
    def update_analytics_volatility(data, theme, period, pathname):
        import dash
        if pathname.rstrip("/") != "/analytics": return dash.no_update
        if not data or "holdings" not in data or not data["holdings"]:
            return html.P("No holdings data available", style={"color": "var(--t-sec)", "fontSize": "13px"})

        from services.market.data_fetcher import fetch_portfolio_history
        histories = fetch_portfolio_history(data["holdings"], period or "max")
        metrics = compute_risk_metrics(data, period=(period or "max"), histories=histories)
        ticker_vols = metrics.get("ticker_vols", {})
        
        if not ticker_vols:
            return html.P("Insufficient data for this period", style={"color": "var(--t-sec)", "fontSize": "13px"})

        # Sort descending (Highest volatility first)
        tv = sorted(
            [(t, v) for t, v in ticker_vols.items() if v is not None],
            key=lambda x: x[1],
            reverse=True
        )
        
        if not tv:
            return html.P("No volatility metrics available", style={"color": "var(--t-sec)", "fontSize": "13px"})

        max_vol = max([v for _, v in tv]) if tv else 0
        n_vols = len(tv)
        
        # Red (High) -> Yellow (Mid) -> Green (Low)
        C_RED    = "#E24B4A"
        C_YELLOW = "#EF9F27"
        C_GREEN  = "#1D9E75"

        rows = []
        for i, (ticker, val) in enumerate(tv):
            if n_vols > 1:
                fraction = i / (n_vols - 1)
                if fraction < 0.5:
                    # Interpolate Red to Yellow (0.0 to 0.5)
                    local_frac = fraction / 0.5
                    color = interpolate_color(C_RED, C_YELLOW, local_frac)
                else:
                    # Interpolate Yellow to Green (0.5 to 1.0)
                    local_frac = (fraction - 0.5) / 0.5
                    color = interpolate_color(C_YELLOW, C_GREEN, local_frac)
            else:
                color = C_RED

            rows.append(
                progress_row(ticker, val, max_vol, suffix="%", color=color)
            )
        return rows

    # ── Correlation heatmap ───────────────────────────────────────────────────
    @app.callback(
        Output("corr-chart",     "figure"),
        Input("portfolio-store", "data"),
        Input("theme-store",     "data"),
        # FIX: change to State to prevent double-rendering
        State("analytics-period-store", "data"),
        Input("url",             "pathname"),
    )
    def update_corr_chart(data, theme, period, pathname):
        import dash
        if pathname.rstrip("/") != "/analytics": return dash.no_update
        t_ = get_theme(theme or "dark")
        period = period or "max"
        
        if not data or "holdings" not in data:
            return create_empty_fig("No holdings found", height=380, theme_tokens=t_)

        from services.market.data_fetcher import fetch_portfolio_history
        histories = fetch_portfolio_history(data["holdings"], period)
        if not histories:
            return create_empty_fig("No shared history found", height=380, theme_tokens=t_)
        return build_corr_figure(histories, period, t_)

    # ── ETF Holdings Bubble Chart ─────────────────────────────────────────────
    @app.callback(
        Output("holdings-bubble-chart", "figure"),
        Output("holdings-freshness-note", "children"),
        Output("holdings-url-collapse", "opened", allow_duplicate=True),
        Input("portfolio-store", "data"),
        Input("theme-store", "data"),
        Input("url", "pathname"),
        Input("holdings-url-save-status", "children"),  # re-trigger after URL save
        State("holdings-url-collapse", "opened"),
        prevent_initial_call=True
    )
    def update_holdings_bubble_chart(data, theme, pathname, _save_status, collapse_open):
        import dash
        if pathname.rstrip("/") != "/analytics":
            return dash.no_update, dash.no_update, dash.no_update

        t_ = get_theme(theme or "dark")

        if not data or "holdings" not in data or not data["holdings"]:
            return create_empty_fig("No portfolio data", height=600, theme_tokens=t_), "", dash.no_update

        blended_data = holdings_blended_data(data)

        if not blended_data:
            # Determine which tickers still have no holdings data after the scrape
            from services.market.holdings_fetcher import get_user_url, PROVIDER_SEED_URLS
            from services.intelligence_service import _get_cached_metadata
            missing = []
            for h in data["holdings"]:
                ticker = h["ticker"]
                cached = _get_cached_metadata(ticker + ".AX", "holdings", ttl_days=30)
                if not cached:
                    has_seed = ticker in PROVIDER_SEED_URLS
                    has_user = bool(get_user_url(ticker))
                    if not has_seed and not has_user:
                        missing.append(ticker)

            if missing:
                note = (
                    f"⚠ No holdings data for: {', '.join(missing)}. "
                    "Please expand ⚙ Configure Sources and add a fund page URL."
                )
            else:
                note = "⚠ Holdings data unavailable — scrape may be in progress or throttled (retries every 24 h)."

            empty_fig = create_empty_fig(
                "No holdings data — add a source URL in ⚙ Configure Sources",
                height=600, theme_tokens=t_
            )
            # Auto-open the configure panel only when tickers are genuinely missing a URL
            should_open = bool(missing) or collapse_open
            return empty_fig, note, should_open

        fig = build_holdings_bubble_chart(blended_data, t_)
        return fig, "Holdings data loaded successfully.", dash.no_update


    # ── Holdings URL Config — Toggle collapse ─────────────────────────────────
    @app.callback(
        Output("holdings-url-collapse", "opened", allow_duplicate=True),
        Input("holdings-url-toggle", "n_clicks"),
        State("holdings-url-collapse", "opened"),
        prevent_initial_call=True
    )
    def toggle_url_collapse(n_clicks, is_open):
        return not is_open

    # ── Holdings URL Config — Load existing URLs table ────────────────────────
    @app.callback(
        Output("holdings-url-table", "children"),
        Input("holdings-url-collapse", "opened"),
        Input("holdings-url-save-btn", "n_clicks"),
        Input("url", "pathname"),
        prevent_initial_call=True
    )
    def load_url_table(is_open, _save, pathname):
        import dash
        if pathname.rstrip("/") != "/analytics":
            return dash.no_update
        if not is_open:
            return dash.no_update


        from services.market.holdings_fetcher import get_all_user_urls, PROVIDER_SEED_URLS

        user_urls = get_all_user_urls()
        # Merge with defaults, user URLs override
        all_tickers = sorted(set(list(PROVIDER_SEED_URLS.keys()) + list(user_urls.keys())))

        if not all_tickers:
            return html.P("No tickers configured.", style={"color": "var(--t-muted)", "fontSize": "13px"})

        rows = [
            html.Tr([
                html.Th("Ticker", style={"width": "80px", "paddingRight": "16px", "textAlign": "left", "fontSize": "12px", "color": "var(--t-muted)"}),
                html.Th("Source URL", style={"textAlign": "left", "fontSize": "12px", "color": "var(--t-muted)"}),
                html.Th("Type", style={"width": "90px", "textAlign": "center", "fontSize": "12px", "color": "var(--t-muted)"}),
            ], style={"borderBottom": "1px solid var(--border)"})
        ]
        for t in all_tickers:
            is_user = t in user_urls
            display_url = user_urls.get(t) or PROVIDER_SEED_URLS.get(t, "—")
            badge_style = {
                "fontSize": "10px", "padding": "2px 8px", "borderRadius": "10px",
                "background": "var(--cyan)" if is_user else "var(--surface)",
                "color": "var(--bg)" if is_user else "var(--t-muted)",
                "fontWeight": "600",
            }
            rows.append(html.Tr([
                html.Td(t, style={"fontWeight": "600", "fontSize": "13px", "paddingRight": "16px", "paddingBottom": "8px"}),
                html.Td(
                    html.A(
                        display_url[:60] + ("…" if len(display_url) > 60 else ""),
                        href=display_url, target="_blank",
                        style={"fontSize": "12px", "color": "var(--cyan)", "textDecoration": "none"}
                    ),
                    style={"paddingBottom": "8px"}
                ),
                html.Td(
                    html.Span("Custom" if is_user else "Default", style=badge_style),
                    style={"textAlign": "center", "paddingBottom": "8px"}
                ),
            ]))

        return html.Table(rows, style={"width": "100%", "borderCollapse": "collapse"})

    # ── Holdings URL Config — Save URL ────────────────────────────────────────
    @app.callback(
        Output("holdings-url-save-status", "children"),
        Output("holdings-url-ticker-input", "value"),
        Output("holdings-url-input", "value"),
        Input("holdings-url-save-btn", "n_clicks"),
        State("holdings-url-ticker-input", "value"),
        State("holdings-url-input", "value"),
        prevent_initial_call=True
    )
    def save_holdings_url(n_clicks, ticker_val, url_val):
        import dash
        if not ticker_val or not url_val:
            return "⚠ Please enter both a ticker and a URL.", dash.no_update, dash.no_update

        ticker_clean = ticker_val.strip().upper().replace(".AX", "")
        url_clean = url_val.strip()

        if not url_clean.startswith("http"):
            return "⚠ URL must start with http:// or https://", dash.no_update, dash.no_update

        try:
            from services.market.holdings_fetcher import save_user_url
            save_user_url(ticker_clean, url_clean)
            return f"✅ Saved URL for {ticker_clean}. Holdings will refresh on next load.", "", ""
        except Exception as e:
            return f"❌ Failed to save: {e}", dash.no_update, dash.no_update