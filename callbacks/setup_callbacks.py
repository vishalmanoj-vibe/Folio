# callbacks/setup_callbacks.py
"""
callbacks/setup_callbacks.py
============================
Callbacks for first-run onboarding wizard and redirection guards.
"""

import json
import logging
import os
import sys
from datetime import datetime

import dash
from dash import ALL, Input, Output, State, dcc, html, no_update

from data.repository import PortfolioRepository

logger = logging.getLogger(__name__)
repo = PortfolioRepository()


def make_setup_row(i):
    return html.Tr(
        [
            html.Td(
                dcc.Input(
                    id={"type": "setup-ticker", "index": i},
                    type="text",
                    placeholder="e.g. VAS",
                    className="setup-row-input",
                    style={"textTransform": "uppercase"},
                )
            ),
            html.Td(
                dcc.Input(
                    id={"type": "setup-shares", "index": i},
                    type="number",
                    min=0.0001,
                    step="any",
                    placeholder="e.g. 10",
                    className="setup-row-input",
                )
            ),
            html.Td(
                dcc.Input(
                    id={"type": "setup-price", "index": i},
                    type="number",
                    min=0.0001,
                    step="any",
                    placeholder="e.g. 85.50",
                    className="setup-row-input",
                )
            ),
            html.Td(
                dcc.Input(
                    id={"type": "setup-date", "index": i},
                    type="date",
                    className="setup-row-input",
                    value=datetime.now().strftime("%Y-%m-%d"),
                )
            ),
            html.Td(
                html.Button(
                    "✕",
                    id={"type": "setup-delete-row-btn", "index": i},
                    className="setup-btn-secondary",
                    type="button",
                    style={
                        "padding": "4px 8px",
                        "fontSize": "11px",
                        "color": "var(--red)",
                        "border": "none",
                    },
                )
                if i > 0
                else ""
            ),
        ],
        id={"type": "setup-row", "index": i},
    )


def register_setup_callbacks(app):
    # ── Global Redirection Guard (Clientside to avoid Python circular dependencies) ──
    app.clientside_callback(
        """
        function(pathname, is_first_run) {
            if (is_first_run === null || is_first_run === undefined) {
                return window.dash_clientside.no_update;
            }

            // Use browser's actual URL to prevent Dash hydration bugs (where pathname is null)
            let actual_path = window.location.pathname;
            if (actual_path.length > 1 && actual_path.endsWith('/')) {
                actual_path = actual_path.slice(0, -1);
            }

            if (is_first_run) {
                // First-time user: force into onboarding wizard
                if (actual_path !== "/setup/portfolio" && actual_path !== "/setup/ai" && actual_path !== "/setup/ready") {
                    window.location.href = "/setup/portfolio";
                    return "Redirecting to portfolio setup...";
                }
            } else {
                // Active user: lock out of setup screens
                if (actual_path === "/setup" || actual_path === "/setup/portfolio" || actual_path === "/setup/ai" || actual_path === "/setup/ready") {
                    window.location.href = "/";
                    return "Redirecting to dashboard...";
                }
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output("dummy-redirect-output", "children"),
        Input("url", "pathname"),
        Input("setup-is-first-run-store", "data"),
    )

    # ── Page 1: Portfolio Setup Row Management ──
    @app.callback(
        Output("setup-portfolio-table-body", "children"),
        Input("setup-portfolio-rows-store", "data"),
    )
    def render_setup_rows(row_indices):
        if not row_indices:
            row_indices = [0]
        return [make_setup_row(i) for i in row_indices]

    @app.callback(
        Output("setup-portfolio-rows-store", "data"),
        Input("setup-add-row-btn", "n_clicks"),
        State("setup-portfolio-rows-store", "data"),
        prevent_initial_call=True,
    )
    def add_setup_row(n_clicks, current_rows):
        if not n_clicks:
            return current_rows
        if len(current_rows) >= 10:
            return current_rows  # 10 rows cap
        next_idx = max(current_rows) + 1 if current_rows else 0
        return current_rows + [next_idx]

    @app.callback(
        Output("setup-portfolio-rows-store", "data", allow_duplicate=True),
        Input({"type": "setup-delete-row-btn", "index": ALL}, "n_clicks"),
        State("setup-portfolio-rows-store", "data"),
        prevent_initial_call=True,
    )
    def delete_setup_row(n_clicks_list, current_rows):
        if not any(n_clicks_list):
            return current_rows

        ctx_triggered = dash.callback_context.triggered
        if not ctx_triggered:
            return current_rows

        prop_id = ctx_triggered[0]["prop_id"]
        try:
            dict_part = prop_id.split(".n_clicks")[0]
            trigger_dict = json.loads(dict_part)
            idx_to_remove = trigger_dict["index"]
            if idx_to_remove != 0:  # Ensure first row is safe
                new_rows = [r for r in current_rows if r != idx_to_remove]
                return new_rows
        except Exception as e:
            logger.error(f"Error deleting setup row: {e}")

        return current_rows

    # ── Page 1: Portfolio Validation and Continue ──
    @app.callback(
        Output("setup-portfolio-continue-btn", "disabled"),
        Input({"type": "setup-ticker", "index": ALL}, "value"),
        Input({"type": "setup-shares", "index": ALL}, "value"),
        Input({"type": "setup-price", "index": ALL}, "value"),
        Input({"type": "setup-date", "index": ALL}, "value"),
    )
    def validate_setup_portfolio(tickers, shares, prices, dates):
        for t, s, p, d in zip(tickers, shares, prices, dates):
            if t and s is not None and p is not None and d:
                t = str(t).strip()
                if len(t) >= 1:
                    try:
                        s_val = float(s)
                        p_val = float(p)
                        if s_val > 0 and p_val > 0:
                            return False  # Found at least one fully complete valid row
                    except (ValueError, TypeError):
                        pass
        return True

    @app.callback(
        Output("url", "pathname", allow_duplicate=True),
        Output("setup-portfolio-feedback", "children"),
        Output("txn-store", "data", allow_duplicate=True),
        Input("setup-portfolio-continue-btn", "n_clicks"),
        State({"type": "setup-ticker", "index": ALL}, "value"),
        State({"type": "setup-shares", "index": ALL}, "value"),
        State({"type": "setup-price", "index": ALL}, "value"),
        State({"type": "setup-date", "index": ALL}, "value"),
        prevent_initial_call=True,
    )
    def save_setup_portfolio(n_clicks, tickers, shares, prices, dates):
        if not n_clicks:
            return dash.no_update, dash.no_update, dash.no_update

        validated_txns = []
        for t, s, p, d in zip(tickers, shares, prices, dates):
            if t and s is not None and p is not None and d:
                t_clean = str(t).strip().upper()
                # Remove any .AX suffix to match relational specifications
                if t_clean.endswith(".AX"):
                    t_clean = t_clean[:-3]
                try:
                    s_val = float(s)
                    p_val = float(p)
                    if s_val > 0 and p_val > 0:
                        validated_txns.append(
                            {
                                "type": "buy",
                                "ticker": t_clean,
                                "shares": s_val,
                                "price": p_val,
                                "date": str(d),
                            }
                        )
                except (ValueError, TypeError):
                    pass

        if not validated_txns:
            return dash.no_update, "Please enter at least one valid transaction.", dash.no_update

        try:
            # Overwrite DB with onboarding transactions using PortfolioRepository
            repo.save_transactions(validated_txns)
            # Re-read to guarantee exact alignment
            saved_txns = repo.load_transactions()
            logger.info(f"Onboarding: saved {len(saved_txns)} transactions to database.")
            return (
                dash.no_update,
                dcc.Location(pathname="/setup/ai", id="setup-redir-ai", refresh=True),
                saved_txns,
            )
        except Exception as e:
            logger.error(f"Onboarding failed to save transactions: {e}")
            return dash.no_update, f"Database error: {e}", dash.no_update

    # ── Page 2: AI Key Setup ──
    @app.callback(
        Output("url", "pathname", allow_duplicate=True),
        Output("setup-ai-feedback", "children"),
        Input("setup-ai-save-btn", "n_clicks"),
        Input("setup-ai-skip-btn", "n_clicks"),
        Input("setup-ai-back-btn", "n_clicks"),
        State("setup-gemini-key", "value"),
        prevent_initial_call=True,
    )
    def handle_ai_setup(save_clicks, skip_clicks, back_clicks, api_key):
        ctx_triggered = dash.callback_context.triggered
        if not ctx_triggered:
            return dash.no_update, dash.no_update

        trigger_id = ctx_triggered[0]["prop_id"].split(".")[0]
        trigger_val = ctx_triggered[0].get("value")

        # Prevent ghost clicks on dynamic page loads
        if trigger_val is None:
            return dash.no_update, dash.no_update

        if trigger_id == "setup-ai-back-btn":
            return dash.no_update, dcc.Location(
                pathname="/setup/portfolio", id="setup-redir-back", refresh=True
            )

        if trigger_id == "setup-ai-skip-btn":
            logger.info("AI Onboarding: skipped by user.")
            return dash.no_update, dcc.Location(
                pathname="/setup/ready", id="setup-redir-skip", refresh=True
            )

        if trigger_id == "setup-ai-save-btn":
            if not api_key or not str(api_key).strip():
                return dash.no_update, "Please enter a valid Gemini API key or click Skip."

            api_key = str(api_key).strip()
            # Save to Database metadata as the primary persistent storage
            try:
                repo.set_gemini_api_key(api_key)
            except Exception as e:
                logger.error(f"AI Onboarding: Failed to save to database metadata: {e}")

            os.environ["GEMINI_API_KEY"] = api_key

            return dash.no_update, dcc.Location(
                pathname="/setup/ready", id="setup-redir-ready", refresh=True
            )

        return dash.no_update, dash.no_update

    # ── Page 3: Ready Summary and Launch ──
    @app.callback(
        Output("setup-ready-summary", "children"),
        Input("url", "pathname"),
        State("txn-store", "data"),
    )
    def render_ready_summary(pathname, txn_data):
        if pathname != "/setup/ready":
            return no_update

        # Read tickers count
        num_txns = len(txn_data) if txn_data else 0

        # Read AI key status
        ai_status = "Skipped (Not configured)"
        if os.environ.get("GEMINI_API_KEY"):
            ai_status = "Enabled (Database Storage)"

        return [
            html.Div("Onboarding Summary", className="setup-summary-title"),
            html.Div(
                [
                    html.Span("Transactions Imported:"),
                    html.Span(f"{num_txns}", className="setup-summary-value"),
                ],
                className="setup-summary-row",
            ),
            html.Div(
                [
                    html.Span("AI Analyst Engine:"),
                    html.Span(ai_status, className="setup-summary-value highlight"),
                ],
                className="setup-summary-row",
            ),
            html.Div(
                [
                    html.Span("Database Directory:"),
                    html.Span("Local Workspace", className="setup-summary-value"),
                ],
                className="setup-summary-row",
            ),
        ]

    @app.callback(
        Output("url", "pathname", allow_duplicate=True),
        Output("setup-is-first-run-store", "data", allow_duplicate=True),
        Output("setup-ready-feedback", "children"),
        Input("setup-ready-launch-btn", "n_clicks"),
        Input("setup-ready-back-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def handle_ready_launch(launch_clicks, back_clicks):
        ctx_triggered = dash.callback_context.triggered
        if not ctx_triggered:
            return dash.no_update, dash.no_update, dash.no_update

        trigger_id = ctx_triggered[0]["prop_id"].split(".")[0]
        trigger_val = ctx_triggered[0].get("value")

        # Prevent ghost clicks on dynamic page loads
        if trigger_val is None:
            return dash.no_update, dash.no_update, dash.no_update

        if trigger_id == "setup-ready-back-btn":
            return (
                dash.no_update,
                dash.no_update,
                dcc.Location(pathname="/setup/ai", id="setup-redir-ai-back", refresh=True),
            )

        if trigger_id == "setup-ready-launch-btn":
            logger.info("Onboarding wizard finished! Redirecting to home dashboard...")
            try:
                repo.set_onboarding_completed(True)
            except Exception as e:
                logger.error(f"Failed to save persistent onboarding state: {e}")

            # ── Trigger immediate data backfill ──────────────────────────────
            # The worker's startup fetch ran before any transactions existed.
            # Enqueue a high-priority portfolio refresh + per-ticker history fetch
            # so data populates immediately without waiting for the 5-min cooldown.
            try:
                from data.database import enqueue_task

                # Priority 1: Fetch live prices right away
                enqueue_task("refresh_portfolio", priority=1)
                # Priority 2: Backfill max history for each ticker (for charts/signals)
                txns = repo.load_transactions()
                tickers = {t["ticker"] for t in txns}
                for ticker in tickers:
                    enqueue_task("fetch_history", {"ticker": ticker, "period": "max"}, priority=2)
                # Priority 3: Maintenance (AI memory, watchlist histories)
                enqueue_task(
                    "maintenance", {"gemini_api_key": os.environ.get("GEMINI_API_KEY")}, priority=3
                )
                logger.info(f"Onboarding: Enqueued data backfill for {len(tickers)} ticker(s).")
            except Exception as e:
                logger.error(f"Failed to enqueue post-onboarding data backfill: {e}")

            # Turn off first run store to unlock main UI pages
            return (
                dash.no_update,
                False,
                dcc.Location(pathname="/", id="setup-redir-home", refresh=True),
            )

        return dash.no_update, dash.no_update, dash.no_update
