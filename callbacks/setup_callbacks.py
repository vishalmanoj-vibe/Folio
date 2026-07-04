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
from typing import Any, cast

import dash
from dash import ALL, Input, Output, State, dcc, html, no_update

from data.repository import PortfolioRepository

logger = logging.getLogger(__name__)
repo = PortfolioRepository()


PROVIDER_MODELS = {
    "gemini": {
        "chat": [
            {"label": "Standard (2.5 Flash)", "value": "gemini-2.5-flash"},
            {"label": "Enhanced (3.1 Flash)", "value": "gemini-3.1-flash-lite"},
            {"label": "Gemini 2.5 Pro (Advanced)", "value": "gemini-2.5-pro"},
        ],
        "report": [
            {"label": "Standard (2.5 Flash)", "value": "gemini-2.5-flash"},
            {"label": "Enhanced (3.1 Flash)", "value": "gemini-3.1-flash-lite"},
        ],
    },
    "openai": {
        "chat": [
            {"label": "GPT-4o Mini (Default)", "value": "gpt-4o-mini"},
            {"label": "GPT-4o (High quality)", "value": "gpt-4o"},
        ],
        "report": [
            {"label": "GPT-4o Mini (Default)", "value": "gpt-4o-mini"},
            {"label": "GPT-4o (High quality)", "value": "gpt-4o"},
        ],
    },
    "anthropic": {
        "chat": [
            {"label": "Claude 3.5 Haiku (Default)", "value": "claude-3-5-haiku-latest"},
            {"label": "Claude 3.5 Sonnet (High quality)", "value": "claude-3-5-sonnet-latest"},
        ],
        "report": [
            {"label": "Claude 3.5 Haiku (Default)", "value": "claude-3-5-haiku-latest"},
            {"label": "Claude 3.5 Sonnet (High quality)", "value": "claude-3-5-sonnet-latest"},
        ],
    },
}


# ── Private Helpers ──────────────────────────────────────────────────────────


def _get_task_statuses(task_ids: list) -> dict:
    """Query worker_tasks for a list of task IDs.
    Returns {task_id: {status, type, result}}.
    """
    if not task_ids:
        return {}
    from data.database import get_connection

    conn = get_connection()
    try:
        placeholders = ",".join("?" * len(task_ids))
        rows = conn.execute(
            f"SELECT task_id, task_type, status, result FROM worker_tasks"
            f" WHERE task_id IN ({placeholders})",
            task_ids,
        ).fetchall()
        return {
            r["task_id"]: {
                "status": r["status"],
                "type": r["task_type"],
                "result": r["result"],
            }
            for r in rows
        }
    except Exception as e:
        logger.error(f"Failed to query task statuses: {e}")
        return {}
    finally:
        conn.close()


def _render_step_row(label: str, status: str) -> html.Div:
    """Render a single task step row with icon, label, and coloured status badge."""
    ICONS = {
        "pending": "○",
        "running": "◐",
        "complete": "✓",
        "failed": "!",
    }
    BADGE_CLASSES = {
        "pending": "badge-pending",
        "running": "badge-running",
        "complete": "badge-done",
        "failed": "badge-failed",
    }
    STATUS_LABELS = {
        "pending": "Queued",
        "running": "Running…",
        "complete": "Done",
        "failed": "Error",
    }
    icon = ICONS.get(status, "○")
    badge_cls = BADGE_CLASSES.get(status, "badge-pending")
    status_text = STATUS_LABELS.get(status, "Queued")

    return html.Div(
        [
            html.Span(icon, className=f"setup-step-icon step-icon-{status}"),
            html.Span(label, className="setup-step-label"),
            html.Span(status_text, className=f"setup-step-badge {badge_cls}"),
        ],
        className="setup-step-row",
    )


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
                    type=cast(Any, "date"),
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

    # ── Page 2: Strategy Settings Loader ──
    @app.callback(
        Output("setup-investment-goal", "value"),
        Output("setup-risk-tolerance", "value"),
        Output("setup-tax-bracket", "value"),
        Output("setup-ai-provider", "value"),
        Input("url", "pathname"),
        prevent_initial_call=False,
    )
    def load_setup_settings(pathname):
        if pathname != "/setup/ai":
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update

        logger.debug("Onboarding: Loading existing strategy settings.")
        from data.settings_repository import get_all_settings

        settings = get_all_settings()
        return (
            settings.get("investment_goal", "Balanced"),
            settings.get("risk_tolerance", "Moderate"),
            settings.get("tax_bracket", "37%"),
            settings.get("ai_provider", "gemini"),
        )

    # ── Onboarding AI Provider dynamic models options and API key masking ──
    @app.callback(
        Output("setup-chat-model", "options"),
        Output("setup-chat-model", "value"),
        Output("setup-report-model", "options"),
        Output("setup-report-model", "value"),
        Output("setup-ai-api-key", "placeholder"),
        Output("setup-ai-api-key", "value"),
        Input("setup-ai-provider", "value"),
        State("url", "pathname"),
        prevent_initial_call=False,
    )
    def update_setup_provider_models_and_key(provider, pathname):
        if pathname != "/setup/ai" or not provider:
            return (
                dash.no_update,
                dash.no_update,
                dash.no_update,
                dash.no_update,
                dash.no_update,
                dash.no_update,
            )

        models = PROVIDER_MODELS.get(provider, PROVIDER_MODELS["gemini"])
        chat_options = models["chat"]
        report_options = models["report"]

        default_chat = chat_options[0]["value"]
        default_report = report_options[0]["value"]

        placeholders = {
            "gemini": "Enter Gemini API Key (e.g. AIzaSy...)",
            "openai": "Enter OpenAI API Key (e.g. sk-proj-...)",
            "anthropic": "Enter Anthropic API Key (e.g. sk-ant-...)",
        }
        placeholder = placeholders.get(provider, "Enter API key")

        env_key_name = f"{provider.upper()}_API_KEY"
        api_key_val = os.getenv(env_key_name)
        if not api_key_val:
            try:
                api_key_val = repo.get_api_key(provider)
            except Exception:
                pass

        key_value = "••••••••••••••••" if api_key_val else ""

        from data.settings_repository import get_all_settings

        settings = get_all_settings()
        stored_provider = settings.get("ai_provider", "gemini")

        if provider == stored_provider:
            chat_val = settings.get("ai_chat_model", default_chat)
            report_val = settings.get("ai_report_model", default_report)
            if not any(opt["value"] == chat_val for opt in chat_options):
                chat_val = default_chat
            if not any(opt["value"] == report_val for opt in report_options):
                report_val = default_report
        else:
            chat_val = default_chat
            report_val = default_report

        return chat_options, chat_val, report_options, report_val, placeholder, key_value

    # ── Onboarding AI Provider connection testing ──
    @app.callback(
        Output("setup-ai-test-status", "children"),
        Output("setup-ai-test-status", "style"),
        Input("setup-ai-test-btn", "n_clicks"),
        State("setup-ai-provider", "value"),
        State("setup-ai-api-key", "value"),
        prevent_initial_call=True,
    )
    def test_setup_ai_connection(n_clicks, provider, api_key_input):
        if not n_clicks or not provider:
            return dash.no_update, dash.no_update

        # Resolve the actual API key to test
        api_key_val = str(api_key_input).strip() if api_key_input else ""
        if api_key_val == "••••••••••••••••":
            env_key_name = f"{provider.upper()}_API_KEY"
            api_key_val = os.getenv(env_key_name)
            if not api_key_val:
                try:
                    api_key_val = repo.get_api_key(provider)
                except Exception:
                    pass

        if not api_key_val:
            return "❌ API key is empty", {"color": "var(--red)"}

        test_prompt = "Say only 'OK'"
        env_key_name = f"{provider.upper()}_API_KEY"
        old_env_val = os.environ.get(env_key_name)
        os.environ[env_key_name] = api_key_val

        from unittest.mock import patch

        try:
            with patch("services.ai_provider.get_setting", return_value=provider):
                from services.ai_provider import generate_content

                test_model = (
                    "gemini-2.5-flash"
                    if provider == "gemini"
                    else ("gpt-4o-mini" if provider == "openai" else "claude-3-5-haiku-latest")
                )
                response = generate_content(test_prompt, model=test_model, max_tokens=10)

            if (
                "error" in response.lower()
                or "fail" in response.lower()
                or "api key" in response.lower()
            ):
                return f"❌ Connection failed: {response}", {"color": "var(--red)"}
            return f"✓ Connection successful! ({response})", {"color": "var(--green)"}
        except Exception as e:
            return f"❌ Connection failed: {e}", {"color": "var(--red)"}
        finally:
            if old_env_val is not None:
                os.environ[env_key_name] = old_env_val
            elif env_key_name in os.environ:
                del os.environ[env_key_name]

    # ── Page 2: AI Key & Strategy Setup ──
    @app.callback(
        Output("url", "pathname", allow_duplicate=True),
        Output("setup-ai-feedback", "children"),
        Input("setup-ai-save-btn", "n_clicks"),
        Input("setup-ai-skip-btn", "n_clicks"),
        Input("setup-ai-back-btn", "n_clicks"),
        State("setup-ai-provider", "value"),
        State("setup-chat-model", "value"),
        State("setup-report-model", "value"),
        State("setup-ai-api-key", "value"),
        State("setup-investment-goal", "value"),
        State("setup-risk-tolerance", "value"),
        State("setup-tax-bracket", "value"),
        prevent_initial_call=True,
    )
    def handle_ai_setup(
        save_clicks,
        skip_clicks,
        back_clicks,
        ai_provider,
        chat_model,
        report_model,
        api_key,
        goal,
        risk,
        tax,
    ):
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

        from data.settings_repository import save_setting

        if trigger_id == "setup-ai-skip-btn":
            logger.info("AI Onboarding: skipped by user. Resetting to default strategy settings.")
            # Default all to normal/balanced if skipped
            save_setting("investment_goal", "Balanced")
            save_setting("risk_tolerance", "Moderate")
            save_setting("tax_bracket", "37%")
            save_setting("ai_provider", "gemini")
            save_setting("ai_chat_model", "gemini-2.5-flash")
            save_setting("ai_report_model", "gemini-3.1-flash-lite")

            # Clear active provider API keys from database/env if skipped
            for p in ["gemini", "openai", "anthropic"]:
                try:
                    repo.set_api_key(p, "")
                except Exception:
                    pass
                env_var_name = f"{p.upper()}_API_KEY"
                if env_var_name in os.environ:
                    del os.environ[env_var_name]

            return dash.no_update, dcc.Location(
                pathname="/setup/ready", id="setup-redir-skip", refresh=True
            )

        if trigger_id == "setup-ai-save-btn":
            provider = ai_provider or "gemini"
            # Save selected strategy settings
            save_setting("investment_goal", goal or "Balanced")
            save_setting("risk_tolerance", risk or "Moderate")
            save_setting("tax_bracket", tax or "37%")
            save_setting("ai_provider", provider)
            save_setting("ai_chat_model", chat_model or "gemini-2.5-flash")
            save_setting("ai_report_model", report_model or "gemini-3.1-flash-lite")

            # Optionally save AI API Key if entered and not masked
            api_key_str = str(api_key).strip() if api_key else ""
            if api_key_str and api_key_str != "••••••••••••••••":
                try:
                    repo.set_api_key(provider, api_key_str)
                except Exception as e:
                    logger.error(f"AI Onboarding: Failed to save key for {provider}: {e}")
                os.environ[f"{provider.upper()}_API_KEY"] = api_key_str
            elif api_key_str == "":
                try:
                    repo.set_api_key(provider, "")
                except Exception:
                    pass
                env_var_name = f"{provider.upper()}_API_KEY"
                if env_var_name in os.environ:
                    del os.environ[env_var_name]

            return dash.no_update, dcc.Location(
                pathname="/setup/ready", id="setup-redir-ready", refresh=True
            )

        return dash.no_update, dash.no_update

    # ── Page 3: Auto Data Fetch (fires once on page load via startup interval) ──
    @app.callback(
        Output("setup-init-tasks-store", "data"),
        Output("setup-poll-interval", "disabled"),
        Input("setup-startup-interval", "n_intervals"),
        State("url", "pathname"),
        State("setup-init-tasks-store", "data"),
        prevent_initial_call=True,
    )
    def auto_start_fetch(n_intervals, pathname, store_data):
        """Enqueue all data-fetch tasks and start the progress poll interval."""
        if pathname != "/setup/ready":
            return no_update, no_update

        # If store already has tasks (page refresh), just re-enable polling
        if store_data and store_data.get("tasks"):
            logger.info("Onboarding: store already has tasks, re-enabling poll on refresh.")
            return no_update, False

        # Fresh start: enqueue all required tasks
        try:
            from data.database import enqueue_task

            tasks = []

            # 1. Critical — live prices (gates the Launch button)
            task_id = enqueue_task("refresh_portfolio", priority=1)
            critical_id = task_id
            tasks.append(
                {
                    "id": task_id,
                    "type": "refresh_portfolio",
                    "label": "Fetching live prices",
                    "is_critical": True,
                }
            )

            # 2. Per-ticker price history (needed for charts, signals, intelligence)
            txns = repo.load_transactions()
            tickers = list({t["ticker"] for t in txns})
            for ticker in sorted(tickers):
                task_id = enqueue_task(
                    "fetch_history", {"ticker": ticker, "period": "max"}, priority=2
                )
                tasks.append(
                    {
                        "id": task_id,
                        "type": "fetch_history",
                        "label": f"Fetching history: {ticker}",
                        "is_critical": False,
                    }
                )

            # 2.5 ETF constituent holdings (needed for Analytics page treemap / allocation charts)
            for ticker in sorted(tickers):
                task_id = enqueue_task("scrape_holdings", {"ticker": ticker}, priority=3)
                tasks.append(
                    {
                        "id": task_id,
                        "type": "scrape_holdings",
                        "label": f"Scraping holdings: {ticker}",
                        "is_critical": False,
                    }
                )

            # 3. Benchmark data (Intelligence page)
            task_id = enqueue_task("fetch_benchmarks", {"period": "max"}, priority=2)
            tasks.append(
                {
                    "id": task_id,
                    "type": "fetch_benchmarks",
                    "label": "Fetching benchmark data",
                    "is_critical": False,
                }
            )

            # 4. Maintenance (AI memory, watchlist histories)
            task_id = enqueue_task(
                "maintenance",
                {"gemini_api_key": os.environ.get("GEMINI_API_KEY")},
                priority=3,
            )
            tasks.append(
                {
                    "id": task_id,
                    "type": "maintenance",
                    "label": "Running maintenance tasks",
                    "is_critical": False,
                }
            )

            store = {
                "tasks": tasks,
                "phase": "fetching",
                "started_at": datetime.now().isoformat(),
                "critical_task_id": critical_id,
            }
            logger.info(f"Onboarding: enqueued {len(tasks)} data fetch tasks.")
            return store, False  # Enable poll interval

        except Exception as e:
            logger.error(f"Onboarding: failed to enqueue data fetch tasks: {e}")
            return no_update, True  # Keep interval disabled

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

            # Data fetch tasks were already enqueued by auto_start_fetch on page load.
            # Turn off first-run flag and redirect to the main dashboard.
            return (
                dash.no_update,
                False,
                dcc.Location(pathname="/", id="setup-redir-home", refresh=True),
            )

        return dash.no_update, dash.no_update, dash.no_update

    # ── Page 3: Progress Tracker Poll (fires every 2s via setup-poll-interval) ──
    @app.callback(
        Output("setup-init-step-list", "children"),
        Output("setup-init-progress-label", "children"),
        Output("setup-init-progress-bar", "style"),
        Output("setup-init-status-msg", "children"),
        Output("setup-ready-launch-btn", "disabled"),
        Output("setup-poll-interval", "disabled", allow_duplicate=True),
        Output("setup-init-tasks-store", "data", allow_duplicate=True),
        Output("setup-ready-summary", "children"),
        Output("setup-ready-summary", "style"),
        Output("setup-init-progress-container", "style"),
        Output("setup-init-title", "children"),
        Output("setup-init-subtitle", "children"),
        Input("setup-poll-interval", "n_intervals"),
        State("setup-init-tasks-store", "data"),
        State("url", "pathname"),
        prevent_initial_call=True,
    )
    def poll_init_progress(n_intervals, store_data, pathname):
        """Poll worker_tasks every 2s and update the progress tracker UI."""
        _NOOP = tuple([no_update] * 12)

        if pathname != "/setup/ready":
            return _NOOP
        if not store_data or not store_data.get("tasks"):
            return _NOOP

        tasks = store_data.get("tasks", [])
        started_at_str = store_data.get("started_at", "")
        phase = store_data.get("phase", "fetching")

        # Already in ready phase — stop further processing
        if phase == "ready":
            return _NOOP

        # ── Timeout check ────────────────────────────────────────────────────
        timed_out = False
        if started_at_str:
            try:
                elapsed = (datetime.now() - datetime.fromisoformat(started_at_str)).total_seconds()
                timed_out = elapsed > 240
            except Exception:
                pass

        # ── Query task statuses from SQLite ──────────────────────────────────
        task_ids = [t["id"] for t in tasks]
        statuses = _get_task_statuses(task_ids)

        total = len(tasks)
        completed = sum(
            1 for t in tasks if statuses.get(t["id"], {}).get("status") in ("complete", "failed")
        )
        all_done = total > 0 and completed >= total

        pct = int(completed / total * 100) if total > 0 else 0

        # ── Render per-task step rows ────────────────────────────────────────
        step_rows = []
        for task in tasks:
            tid = task["id"]
            status = statuses.get(tid, {}).get("status", "pending")
            step_rows.append(_render_step_row(task["label"], status))

        bar_style = {"width": f"{pct}%", "transition": "width 0.6s ease"}
        progress_label = f"{completed} of {total} tasks complete"
        launch_disabled = not (all_done or timed_out)

        # ── Status warning message ───────────────────────────────────────────
        status_msg: Any = ""
        if timed_out and not all_done:
            status_msg = html.Div(
                "⚠ Some tasks are taking longer than expected. "
                "You can launch now — data will continue loading in the background.",
                className="setup-init-status-warning",
            )

        # ── Phase B transition: all done or timeout ──────────────────────────
        if all_done or timed_out:
            new_store = {**store_data, "phase": "ready"}

            # Build ready summary
            try:
                num_txns = len(repo.load_transactions())
            except Exception:
                num_txns = 0
            ai_status = "Enabled ✓" if os.environ.get("GEMINI_API_KEY") else "Not configured"

            summary_children = [
                html.Div("Setup Complete", className="setup-summary-title"),
                html.Div(
                    [
                        html.Span("Transactions loaded:"),
                        html.Span(str(num_txns), className="setup-summary-value"),
                    ],
                    className="setup-summary-row",
                ),
                html.Div(
                    [
                        html.Span("Market data:"),
                        html.Span("Fetched ✓", className="setup-summary-value"),
                    ],
                    className="setup-summary-row",
                ),
                html.Div(
                    [
                        html.Span("AI Analyst:"),
                        html.Span(ai_status, className="setup-summary-value highlight"),
                    ],
                    className="setup-summary-row",
                ),
            ]

            if all_done:
                new_title = "Dashboard Ready!"
                new_subtitle = (
                    "All market data has been loaded. "
                    "Click 'Launch Dashboard' to open your portfolio."
                )
                bar_style = {"width": "100%", "transition": "width 0.6s ease"}
                progress_label = f"{total} of {total} tasks complete"
            else:
                new_title = "Dashboard Ready"
                new_subtitle = (
                    "Live prices are loaded. Some background tasks are still running "
                    "and will complete automatically."
                )

            return (
                step_rows,  # 1. step-list children
                progress_label,  # 2. progress-label children
                bar_style,  # 3. progress-bar style
                status_msg,  # 4. status-msg children
                False,  # 5. launch-btn disabled → ENABLED
                True,  # 6. poll-interval disabled → STOP
                new_store,  # 7. tasks-store data
                summary_children,  # 8. ready-summary children
                {},  # 9. ready-summary style → SHOW
                {"display": "none"},  # 10. progress-container → HIDE
                new_title,  # 11. title children
                new_subtitle,  # 12. subtitle children
            )

        # ── Phase A: still fetching — update progress indicators only ─────────
        return (
            step_rows,
            progress_label,
            bar_style,
            status_msg,
            launch_disabled,
            no_update,  # keep interval running
            no_update,  # keep store as-is
            no_update,  # summary still hidden
            no_update,  # summary style unchanged
            no_update,  # progress container still visible
            no_update,  # title unchanged
            no_update,  # subtitle unchanged
        )
