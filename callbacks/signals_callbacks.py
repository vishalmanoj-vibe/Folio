import dash
from dash import Input, Output, State
import logging
from datetime import datetime

from services.market.data_fetcher import get_full_history_cache
from services.strategy_engine import generate_portfolio_signals
from services.ai_engine import analyze_signals

logger = logging.getLogger(__name__)

def register_callbacks(app):

    # ── Portfolio Signals ──────────────────────────────────────────────────────
    @app.callback(
        Output("signals-store", "data"),
        Output("signals-status-label", "children"),
        Input("generate-signals-btn", "n_clicks"),
        State("portfolio-store", "data"),
        State("signals-store", "data"),
        prevent_initial_call=True
    )
    def generate_signals_callback(n_clicks, portfolio_data, previous_signals_store):
        if not n_clicks or not portfolio_data or "holdings" not in portfolio_data:
            return dash.no_update, dash.no_update

        holdings = portfolio_data.get("holdings", [])
        if not holdings:
            return dash.no_update, "No holdings to analyse."

        previous_signals = previous_signals_store.get("raw", {}) if previous_signals_store else {}

        multi_full = get_full_history_cache(holdings)
        if multi_full.empty:
            logger.warning("Signals requested but full history cache is empty — user must load data first.")
            return (
                {"raw": {}, "ai": {}, "error": "No market data cached. Refresh the page and try again."},
                "⚠ No data — refresh first."
            )

        raw_signals = generate_portfolio_signals(multi_full, holdings, previous_signals)
        ai_insights = analyze_signals(raw_signals)

        timestamp = datetime.now().strftime("%H:%M")
        return (
            {"raw": raw_signals, "ai": ai_insights},
            f"Updated {timestamp}"
        )

    # ── Watchlist Signals ──────────────────────────────────────────────────────
    @app.callback(
        Output("watchlist-signals-store", "data"),
        Output("watchlist-signals-status-label", "children"),
        Input("watchlist-generate-signals-btn", "n_clicks"),
        State("watchlist-store", "data"),
        State("watchlist-signals-store", "data"),
        prevent_initial_call=True
    )
    def generate_watchlist_signals_callback(n_clicks, watchlist_data, previous_signals_store):
        if not n_clicks or not watchlist_data or "holdings" not in watchlist_data:
            return dash.no_update, dash.no_update

        holdings = watchlist_data.get("holdings", [])
        if not holdings:
            return dash.no_update, "No watchlist tickers to analyse."

        previous_signals = previous_signals_store.get("raw", {}) if previous_signals_store else {}

        # Use watchlist holdings to build the correct cache key
        multi_full = get_full_history_cache(holdings)
        if multi_full.empty:
            logger.warning("Watchlist signals requested but history cache is empty — user must visit Watchlist first.")
            return (
                {"raw": {}, "ai": {}, "error": "No market data cached. Visit the Watchlist page first."},
                "⚠ No data — visit Watchlist first."
            )

        raw_signals = generate_portfolio_signals(multi_full, holdings, previous_signals)
        ai_insights = analyze_signals(raw_signals)

        timestamp = datetime.now().strftime("%H:%M")
        return (
            {"raw": raw_signals, "ai": ai_insights},
            f"Updated {timestamp}"
        )

