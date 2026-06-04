# callbacks/ui_callbacks.py
"""
UI Callbacks for Folio.

Handles general UI interactions such as theme toggling and printing.
"""

import dash
from dash import ALL, Input, Output, State, ctx, html


def register_callbacks(app) -> None:
    """
    Register UI-related callbacks with the Dash application.

    Args:
        app: The Dash application instance.
    """

    # ── 1. Dark / light theme store toggle ──
    @app.callback(
        Output("theme-store", "data"),
        Input("theme-toggle", "n_clicks"),
        Input("theme-toggle-hidden", "n_clicks"),
        State("theme-store", "data"),
        prevent_initial_call=True,
    )
    def toggle_theme_store(n, n_hidden, current):
        return "light" if current == "dark" else "dark"

    # ── 2. Sync UI attributes with theme store (Fires on load) ──
    app.clientside_callback(
        """
        function(theme) {
            const t = theme || 'dark';
            document.body.setAttribute('data-theme', t);
            document.documentElement.setAttribute('data-theme', t);
            return '';
        }
        """,
        Output("theme-toggle-hidden", "children"),
        Input("theme-store", "data"),
    )

    # ── PDF / print button ────────────────────────────────────────────────────
    app.clientside_callback(
        "function(n, n_hidden) { if(n || n_hidden) window.print(); return ''; }",
        Output("pdf-btn-hidden", "children"),
        Input("pdf-btn", "n_clicks"),
        Input("pdf-btn-hidden", "n_clicks"),
        prevent_initial_call=True,
    )

    # ── Compact Mode Toggle ──────────────────────────────────────────────────
    @app.callback(
        Output("compact-mode-store", "data"),
        Output("txn-collapse", "opened"),
        Output("compact-toggle-btn", "children"),
        Output("compact-toggle-btn", "className"),
        Input("compact-toggle-btn", "n_clicks"),
        State("compact-mode-store", "data"),
        prevent_initial_call=True,
    )
    def toggle_compact_mode(n, is_compact):
        # Explicitly handle initial load or reset
        if not n:
            return (
                True,
                False,
                [
                    html.Span("+", style={"fontSize": "16px", "fontWeight": "bold"}),
                    "Add Transaction",
                ],
                "btn-primary btn-sm",
            )

        new_state = not is_compact
        opened = not new_state
        label = "Hide Form" if opened else "Add Transaction"
        icon = "−" if opened else "+"

        children = [html.Span(icon, style={"fontSize": "16px", "fontWeight": "bold"}), label]

        # Teal highlight when closed, standard when opened
        btn_class = "btn-primary btn-sm" if not opened else "btn-sm"

        return new_state, opened, children, btn_class

    # ── Table Header Sorting ──────────────────────────────────────────────────
    @app.callback(
        Output("folio-table-state-v3", "data"),
        Input({"type": "table-th", "index": dash.ALL}, "n_clicks"),
        State("folio-table-state-v3", "data"),
        prevent_initial_call=True,
    )
    def update_table_sorting(n_clicks_list, current_state):
        # We need to find which specific column triggered the callback
        if not ctx.triggered_id:
            return dash.no_update

        # Pattern matching triggered_id is a dict
        triggered = ctx.triggered_id
        if not isinstance(triggered, dict) or triggered.get("type") != "table-th":
            return dash.no_update

        clicked_col = triggered.get("index")
        if not clicked_col:
            return dash.no_update

        # Ensure current_state is a valid dict
        if not current_state or not isinstance(current_state, dict):
            current_state = {"sort_col": "ticker", "sort_dir": "asc", "search": ""}

        new_state = current_state.copy()

        # Toggle logic
        if new_state.get("sort_col") == clicked_col:
            # Toggle direction on same column
            new_state["sort_dir"] = "asc" if new_state.get("sort_dir") == "desc" else "desc"
        else:
            # New column: default to Descending for metrics, Ascending for labels
            new_state["sort_col"] = clicked_col
            if clicked_col in ["ticker", "name", "div_frequency"]:
                new_state["sort_dir"] = "asc"
            else:
                new_state["sort_dir"] = "desc"

        return new_state

    # ── Active Nav Link Highlighting ──────────────────────────────────────────
    app.clientside_callback(
        """
        function(pathname) {
            const links = document.querySelectorAll('.nav-link');
            links.forEach(link => {
                const href = link.getAttribute('href');
                if (!href) return;

                let isActive = false;
                if (href === pathname) {
                    isActive = true;
                } else if (href !== '/' && pathname.startsWith(href + '/')) {
                    // Highlight parent for sub-pages like /positions/details
                    isActive = true;
                } else if (href === '/' && pathname.startsWith('/etf/')) {
                    // Highlight Overview for ETF-specific deep dives
                    isActive = true;
                }

                link.classList.toggle('active', isActive);
            });
            return window.dash_clientside.no_update;
        }
        """,
        Output("nav-link-store", "data"),
        Input("url", "pathname"),
    )

    # ── Manual Data Refresh ──────────────────────────────────────────────────
    @app.callback(
        Output("pending-tasks-store", "data", allow_duplicate=True),
        Input("refresh-btn", "n_clicks"),
        Input("refresh-btn-hidden", "n_clicks"),
        State("pending-tasks-store", "data"),
        prevent_initial_call=True,
    )
    def handle_refresh_click(n, n_hidden, pending):
        if not n and not n_hidden:
            return dash.no_update
        from data.database import enqueue_task

        task_id = enqueue_task("refresh_portfolio", priority=1)

        new_pending = pending or []
        new_pending.append({"id": task_id, "type": "refresh_portfolio"})
        return new_pending

    # ── Populate command palette ticker store ──
    app.clientside_callback(
        """
        function(portfolioData, watchlistData, signalsStore, watchlistSignalsStore) {
            const items = [];
            const seen = new Set();

            const rawSignals = (signalsStore && signalsStore.raw) ? signalsStore.raw : {};
            const watchSignals = (watchlistSignalsStore && watchlistSignalsStore.raw) ? watchlistSignalsStore.raw : {};

            if (portfolioData && portfolioData.holdings) {
                portfolioData.holdings.forEach(h => {
                    if (h.ticker && !seen.has(h.ticker + '_holdings')) {
                        seen.add(h.ticker + '_holdings');
                        const pnl = h.unrealised_pnl_pct || h.pnl_pct || 0;
                        const sig = rawSignals[h.ticker] ? rawSignals[h.ticker].signal : null;
                        items.push({
                            ticker: h.ticker.toUpperCase(),
                            group: 'holdings',
                            pnl_pct: pnl,
                            signal: sig
                        });
                    }
                });
            }
            if (watchlistData && watchlistData.holdings) {
                watchlistData.holdings.forEach(h => {
                    if (h.ticker && !seen.has(h.ticker + '_watchlist')) {
                        seen.add(h.ticker + '_watchlist');
                        const sig = watchSignals[h.ticker] ? watchSignals[h.ticker].signal : null;
                        items.push({
                            ticker: h.ticker.toUpperCase(),
                            group: 'watchlist',
                            pnl_pct: 0,
                            signal: sig
                        });
                    }
                });
            }
            window.paletteTickerData = items;
            return items;
        }
        """,
        Output("palette-ticker-store", "data"),
        Input("portfolio-store", "data"),
        Input("watchlist-store", "data"),
        Input("signals-store", "data"),
        Input("watchlist-signals-store", "data"),
    )
