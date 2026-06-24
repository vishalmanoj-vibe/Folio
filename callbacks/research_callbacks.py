import base64
import json
import logging
import os
from datetime import datetime

import dash
from dash import Input, Output, State, ctx, html, no_update

from data.database import enqueue_task, get_connection
from services.research_memory import (
    append_turn,
    check_memory_size,
    load_conversation_log,
    load_memory_summary,
)
from services.research_service import build_portfolio_context, get_ai_response

logger = logging.getLogger(__name__)


def get_quick_prompt_questions(page_name, active_ticker):
    # Default fallback questions
    qp1 = "Does this fit my portfolio?"
    qp2 = "What are the main risks?"
    qp3 = "Compare to what I own"
    qp4 = "What sectors or regions am I missing in my portfolio?"

    if page_name == "Positions" and active_ticker:
        t = active_ticker.upper()
        qp1 = f"Does {t} fit my portfolio?"
        qp2 = f"What are the main risks of {t}?"
        qp3 = f"Compare {t} to what I own"
        qp4 = "What am I missing in my portfolio?"
    elif page_name == "Watchlist" and active_ticker:
        t = active_ticker.upper()
        qp1 = f"Does {t} fit my portfolio?"
        qp2 = f"What are the main risks of {t}?"
        qp3 = f"Compare {t} to my holdings"
        qp4 = "What am I missing in my portfolio?"
    elif page_name == "Deep Dive":
        qp1 = "Which of my holdings is the most volatile?"
        qp2 = "Which of my tickers have the highest correlation?"
        qp3 = "How can I improve my asset allocation?"
        qp4 = "Is my portfolio diversified enough?"
    elif page_name == "Insights":
        qp1 = "What alerts are active right now?"
        qp2 = "Are any of my holdings overbought?"
        qp3 = "Explain the current technical signals"
        qp4 = "Show me the highest technical signal score"
    elif page_name == "Settings":
        qp1 = "How does my investor profile affect signals?"
        qp2 = "Explain my custom strategy weights"
        qp3 = "How can I optimize my tax settings?"
        qp4 = "What am I missing in my portfolio?"
    elif page_name == "Overview":
        if active_ticker:
            t = active_ticker.upper()
            qp1 = f"Does {t} fit my portfolio?"
            qp2 = f"What are the risks of {t}?"
            qp3 = f"Compare {t} to what I own"
            qp4 = "What am I missing in my portfolio?"
        else:
            qp1 = "What is my total portfolio value and P&L?"
            qp2 = "Compare my top holdings by market value"
            qp3 = "Suggest rebalancing actions for my holdings"
            qp4 = "What am I missing in my portfolio?"

    return qp1, qp2, qp3, qp4


def register_callbacks(app):
    # --- CALLBACK 1: Welcome message on chatbot mount/load ---
    @app.callback(
        Output("research-chat-store", "data"),
        Input("url", "pathname"),
        State("portfolio-store", "data"),
        State("research-chat-store", "data"),
        prevent_initial_call=True,
    )
    def init_research_chat(pathname, portfolio_data, current_history):
        # Conversation already exists — do not overwrite it
        if current_history is not None and len(current_history) > 0:
            return no_update

        if not portfolio_data or not portfolio_data.get("holdings"):
            return [{"role": "assistant", "content": "Loading your portfolio data, please wait..."}]

        holdings = portfolio_data["holdings"]
        n = len(holdings)
        total_val = sum(h.get("mkt_value", 0) for h in holdings)

        summary = load_memory_summary()
        recent_log = load_conversation_log()

        memory_note = ""
        if summary:
            memory_note = f"\n\nFrom our previous conversations: {summary}"

        recent_count = len(recent_log)
        if recent_count > 0:
            memory_note += (
                f"\n\nI also have {recent_count} recent message(s) from the last 7 days in memory."
            )

        welcome_msg = (
            f"Hi! I've loaded your portfolio — {n} holdings worth "
            f"${total_val:,.0f}. Ask me about your positions, or type "
            f"a ticker in the input box above to research it. You can also click "
            f"**Generate Weekly Report** below to create a PDF summary." + memory_note
        )

        return [{"role": "assistant", "content": welcome_msg}]

    # --- CALLBACK 2: Send message OR trigger report generation ---
    @app.callback(
        Output("research-chat-store", "data", allow_duplicate=True),
        Output("research-input", "value"),
        Output("research-usage-store", "data", allow_duplicate=True),
        Output("research-typing-indicator", "style"),
        Output("research-send-btn", "disabled"),
        Output("report-cache-store", "data", allow_duplicate=True),
        Output("ai-pending-tasks-store", "data", allow_duplicate=True),
        Input("research-send-btn", "n_clicks"),
        Input("research-input", "n_submit"),
        Input("qp-1", "n_clicks"),
        Input("qp-2", "n_clicks"),
        Input("qp-3", "n_clicks"),
        Input("qp-4", "n_clicks"),
        Input("qp-report", "n_clicks"),
        State("research-input", "value"),
        State("research-chat-store", "data"),
        State("portfolio-store", "data"),
        State("research-ticker-store", "data"),
        State("research-usage-store", "data"),
        State("ai-pending-tasks-store", "data"),
        State("url", "pathname"),
        State("positions-selected-ticker", "data"),
        State("watchlist-selected-ticker", "data"),
        State("ticker-store", "data"),
        prevent_initial_call=True,
    )
    def send_research_message(
        n_send,
        n_submit,
        n1,
        n2,
        n3,
        n4,
        n_report,
        input_val,
        current_history,
        portfolio_data,
        ticker,
        usage_data,
        ai_pending,
        pathname,
        pos_ticker,
        wl_ticker,
        overview_ticker,
    ):
        from datetime import date

        DAILY_LIMIT = 20
        today_str = str(date.today())

        if not ctx.triggered_id:
            return (
                no_update,
                no_update,
                no_update,
                {"display": "none"},
                False,
                no_update,
                no_update,
            )

        # Guard against mount-time ghost fires for quick-prompt buttons
        triggered_val = ctx.triggered[0].get("value") or 0
        if str(ctx.triggered_id) in ("qp-1", "qp-2", "qp-3", "qp-4", "qp-report"):
            if not triggered_val or int(triggered_val) < 1:
                return (
                    no_update,
                    no_update,
                    no_update,
                    {"display": "none"},
                    False,
                    no_update,
                    no_update,
                )

        # Guard for send button / enter key
        if str(ctx.triggered_id) in ("research-send-btn", "research-input"):
            if not triggered_val or int(triggered_val) < 1:
                return (
                    no_update,
                    no_update,
                    no_update,
                    {"display": "none"},
                    False,
                    no_update,
                    no_update,
                )

        history = list(current_history or [])

        # ── Report generation branch ─────────────────────────────────────────
        if ctx.triggered_id == "qp-report":
            history.append({"role": "user", "content": "Generate Weekly Report"})
            history.append(
                {
                    "role": "assistant",
                    "content": "⌛ Preparing your report, please wait...",
                    "type": "thinking",
                }
            )
            placeholder_idx = len(history) - 1

            # Enqueue report task
            task_id = enqueue_task(
                "generate_report",
                {"tickers": [h["ticker"] for h in portfolio_data.get("holdings", [])]},
                priority=2,
            )

            new_ai_pending = (ai_pending or {}).copy()
            new_ai_pending[task_id] = placeholder_idx

            return (history, "", no_update, {"display": "none"}, False, no_update, new_ai_pending)

        # ── Standard chat branch ─────────────────────────────────────────────
        if not usage_data:
            usage_data = {"count": 0, "reset_date": ""}

        if usage_data.get("reset_date") != today_str:
            usage_data = {"count": 0, "reset_date": today_str}

        current_count = usage_data.get("count", 0)

        if current_count >= DAILY_LIMIT:
            limit_msg = (
                f"You've reached your {DAILY_LIMIT} free messages "
                f"for today. Your limit resets tomorrow."
            )
            history.append({"role": "assistant", "content": limit_msg})
            return (history, "", no_update, {"display": "none"}, False, no_update, no_update)

        # Resolve active viewport context
        page_name = "Overview"
        active_ticker = None

        if pathname == "/positions":
            page_name = "Positions"
            active_ticker = pos_ticker
        elif pathname == "/watchlist":
            page_name = "Watchlist"
            active_ticker = wl_ticker
        elif pathname == "/analytics":
            page_name = "Deep Dive"
        elif pathname == "/intelligence":
            page_name = "Insights"
        elif pathname == "/settings":
            page_name = "Settings"
        elif pathname == "/":
            page_name = "Overview"
            if overview_ticker and overview_ticker != "Portfolio":
                active_ticker = overview_ticker

        # Fallback to research search bar ticker if no page-specific ticker is active
        if not active_ticker and ticker:
            active_ticker = ticker

        # Resolve quick prompt texts for the active context
        qp1, qp2, qp3, qp4 = get_quick_prompt_questions(page_name, active_ticker)

        message = None
        target_ticker = None

        if ctx.triggered_id == "qp-1":
            message = qp1
            if active_ticker and page_name in ("Positions", "Watchlist", "Overview"):
                target_ticker = active_ticker
        elif ctx.triggered_id == "qp-2":
            message = qp2
            if active_ticker and page_name in ("Positions", "Watchlist", "Overview"):
                target_ticker = active_ticker
        elif ctx.triggered_id == "qp-3":
            message = qp3
            if active_ticker and page_name in ("Positions", "Watchlist", "Overview"):
                target_ticker = active_ticker
        elif ctx.triggered_id == "qp-4":
            message = qp4
        elif ctx.triggered_id in ("research-send-btn", "research-input"):
            message = input_val
            # For typed/free-text questions, only target the active ticker if it is explicitly mentioned
            if active_ticker and message:
                import re

                pattern = r"\b" + re.escape(active_ticker.upper()) + r"\b"
                if re.search(pattern, message.upper()):
                    target_ticker = active_ticker

        if not message or not str(message).strip():
            return (
                no_update,
                no_update,
                no_update,
                {"display": "none"},
                False,
                no_update,
                no_update,
            )

        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": "Thinking...", "type": "thinking"})
        placeholder_idx = len(history) - 1

        append_turn("user", message)

        # ── Build Compact Context ──
        holdings = portfolio_data.get("holdings", []) if portfolio_data else []
        top_holdings = sorted(holdings, key=lambda x: x.get("mkt_value", 0), reverse=True)[:20]
        context = {
            "holdings": top_holdings,
            "active_page": page_name,
            "active_ticker": active_ticker,
        }

        # Enqueue AI task
        task_id = enqueue_task(
            "generate_ai_response",
            {
                "messages": history[:-1],  # History excluding placeholder
                "context": context,
                "ticker": target_ticker or "General",
            },
            priority=1,
        )  # Highest priority

        new_ai_pending = (ai_pending or {}).copy()
        new_ai_pending[task_id] = placeholder_idx

        new_usage = {"count": current_count + 1, "reset_date": today_str}
        return (history, "", new_usage, {"display": "none"}, False, no_update, new_ai_pending)

    # --- CLIENTSIDE: Show typing indicator immediately on send or quick prompt click ---
    app.clientside_callback(
        """
        function() {
            const anyClicked = Array.from(arguments).some(n => n && n > 0);
            if (anyClicked) {
                return [{"display": "flex", "padding": "4px 20px 8px"}, true];
            }
            return [{"display": "none"}, false];
        }
        """,
        Output("research-typing-indicator", "style", allow_duplicate=True),
        Output("research-send-btn", "disabled", allow_duplicate=True),
        Input("research-send-btn", "n_clicks"),
        Input("research-input", "n_submit"),
        Input("qp-1", "n_clicks"),
        Input("qp-2", "n_clicks"),
        Input("qp-3", "n_clicks"),
        Input("qp-4", "n_clicks"),
        Input("qp-report", "n_clicks"),
        prevent_initial_call=True,
    )

    # --- CALLBACK 3: Poll AI tasks ---
    @app.callback(
        Output("research-chat-store", "data", allow_duplicate=True),
        Output("ai-pending-tasks-store", "data", allow_duplicate=True),
        Output("report-cache-store", "data", allow_duplicate=True),
        Input("task-poll-interval", "n_intervals"),
        State("ai-pending-tasks-store", "data"),
        State("research-chat-store", "data"),
        prevent_initial_call=True,
    )
    def poll_ai_research_callback(n, pending, history):
        if not pending:
            return no_update, {}, no_update

        history = list(history or [])
        conn = get_connection()
        try:
            still_pending = {}
            new_report = no_update

            for task_id, placeholder_idx in pending.items():
                row = conn.execute(
                    "SELECT status, result FROM worker_tasks WHERE task_id = ?", (task_id,)
                ).fetchone()

                if row:
                    status = row["status"]
                    if status == "complete":
                        res = json.loads(row["result"]) if row["result"] else {}

                        # Replace placeholder in history
                        if placeholder_idx < len(history):
                            if "response" in res:
                                # AI Chat response
                                history[placeholder_idx] = {
                                    "role": "assistant",
                                    "content": res["response"],
                                }
                                append_turn("assistant", res["response"])
                            elif "pdf_b64" in res:
                                # Report response
                                history[placeholder_idx] = {
                                    "role": "assistant",
                                    "content": "✓ Your **Weekly Portfolio Report** is ready!",
                                    "type": "report-ready",
                                }
                                new_report = res["pdf_b64"]

                    elif status == "failed":
                        res = json.loads(row["result"]) if row["result"] else {}
                        err = res.get("error", "AI failed.")
                        if placeholder_idx < len(history):
                            history[placeholder_idx] = {"role": "assistant", "content": f"❌ {err}"}
                    else:
                        still_pending[task_id] = placeholder_idx
                else:
                    # Task not found
                    if placeholder_idx < len(history):
                        history[placeholder_idx] = {
                            "role": "assistant",
                            "content": "❌ Assistant is temporarily unavailable (Task not found).",
                        }

            return history, still_pending, new_report
        finally:
            conn.close()

    # --- CALLBACK 4: Render chat messages ---
    @app.callback(
        Output("research-chat-display", "children"),
        Input("research-chat-store", "data"),
        prevent_initial_call=True,
    )
    def render_chat(history):
        if not history:
            return html.Div(
                "Your conversation will appear here.", className="research-chat-placeholder"
            )

        bubbles = []
        for msg in history:
            role = msg.get("role", "")
            msg_type = msg.get("type", "")
            content = msg.get("content", "")

            if msg_type == "report-ready":
                # Special "report ready" bubble with a download button
                bubbles.append(
                    html.Div(
                        [
                            html.P(content, style={"margin": "0 0 10px", "color": "var(--green)"}),
                            html.Button(
                                "⬇ Download PDF Report",
                                id="report-pdf-link",
                                n_clicks=0,
                                style={
                                    "background": "none",
                                    "border": "1px solid var(--cyan)",
                                    "color": "var(--cyan)",
                                    "borderRadius": "6px",
                                    "padding": "6px 14px",
                                    "fontSize": "12px",
                                    "cursor": "pointer",
                                },
                            ),
                        ],
                        className="chat-bubble-assistant",
                    )
                )
            elif role == "user":
                bubbles.append(html.Div(content, className="chat-bubble-user"))
            else:
                bubbles.append(html.Div(content, className="chat-bubble-assistant"))

        return html.Div(
            bubbles, style={"display": "flex", "flexDirection": "column", "gap": "12px"}
        )

    # --- CALLBACK 4: Store researched ticker ---
    @app.callback(
        Output("research-ticker-store", "data"),
        Input("research-ticker-input", "value"),
        prevent_initial_call=True,
    )
    def store_ticker(value):
        if not value or not str(value).strip():
            return ""
        return str(value).strip().upper()

    # --- CALLBACK 5: Render usage counter display ---
    @app.callback(
        Output("research-usage-display", "children"),
        Input("research-usage-store", "data"),
    )
    def render_usage_display(usage_data):
        memory = check_memory_size()

        from datetime import date

        DAILY_LIMIT = 20
        today_str = str(date.today())

        if not usage_data:
            usage_data = {"count": 0, "reset_date": ""}

        if usage_data.get("reset_date") != today_str:
            count = 0
        else:
            count = usage_data.get("count", 0)

        remaining = DAILY_LIMIT - count
        color = (
            "var(--green)"
            if remaining > 10
            else "var(--warning)"
            if remaining > 3
            else "var(--red)"
        )

        if memory.get("is_full"):
            return html.Div(
                [
                    html.Span(
                        "⚠ Research memory is full (50MB). ",
                        style={"color": "var(--red)", "fontSize": "11px", "fontWeight": "600"},
                    ),
                    html.Span(
                        "Old conversations are being auto-summarised. "
                        "If this persists, restart the app.",
                        style={"color": "var(--t-sec)", "fontSize": "10px"},
                    ),
                ],
                style={"padding": "6px 20px", "flexShrink": "0"},
            )

        return html.Div(
            [
                html.Span(
                    f"{remaining} of {DAILY_LIMIT} messages remaining today",
                    style={"fontSize": "10px", "color": color, "fontWeight": "500"},
                ),
                html.Span(
                    " · Resets at midnight", style={"fontSize": "10px", "color": "var(--t-sec)"}
                ),
            ],
            style={
                "padding": "6px 20px",
                "borderBottom": "0.5px solid var(--border)",
                "display": "flex",
                "alignItems": "center",
                "gap": "4px",
                "flexShrink": "0",
            },
        )

    # --- CALLBACK 7: Trigger PDF download from chat bubble button ---
    @app.callback(
        Output("report-download", "data"),
        Input("report-pdf-link", "n_clicks"),
        State("report-cache-store", "data"),
        prevent_initial_call=True,
    )
    def trigger_download(n_clicks, b64_data):
        if not n_clicks or not b64_data:
            return dash.no_update

        pdf_bytes = base64.b64decode(b64_data)
        filename = f"Portfolio_Report_{datetime.now().strftime('%Y%m%d')}.pdf"
        return dash.dcc.send_bytes(pdf_bytes, filename=filename)

    # --- CLIENTSIDE: Auto-scroll chat to bottom when children change ---
    app.clientside_callback(
        """
        function(children) {
            const el = document.getElementById('research-chat-display');
            if (el) {
                setTimeout(() => {
                    el.scrollTop = el.scrollHeight;
                }, 100);
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output("research-chat-display", "id"),  # Dummy output
        Input("research-chat-display", "children"),
        prevent_initial_call=True,
    )

    # --- CLIENTSIDE CALLBACK: Toggle Chatbot Window ---
    app.clientside_callback(
        """
        function(trigger_clicks, close_clicks) {
            const triggered = window.dash_clientside.callback_context.triggered;
            if (!triggered || triggered.length === 0) {
                return [{"display": "none"}, {"display": "flex"}];
            }
            const trigId = triggered[0].prop_id.split('.')[0];
            if (trigId === 'chatbot-trigger') {
                return [{"display": "flex"}, {"display": "none"}];
            }
            if (trigId === 'chatbot-close') {
                return [{"display": "none"}, {"display": "flex"}];
            }
            return [{"display": "none"}, {"display": "flex"}];
        }
        """,
        Output("chatbot-window", "style"),
        Output("chatbot-trigger", "style"),
        Input("chatbot-trigger", "n_clicks"),
        Input("chatbot-close", "n_clicks"),
        prevent_initial_call=True,
    )

    # --- CALLBACK: Update Chatbot Context & Quick Prompts ---
    @app.callback(
        Output("chatbot-context-bar", "children"),
        Output("qp-1", "children"),
        Output("qp-1", "style"),
        Output("qp-2", "children"),
        Output("qp-2", "style"),
        Output("qp-3", "children"),
        Output("qp-3", "style"),
        Output("qp-4", "children"),
        Output("qp-4", "style"),
        Input("url", "pathname"),
        Input("positions-selected-ticker", "data"),
        Input("watchlist-selected-ticker", "data"),
        Input("ticker-store", "data"),
        Input("research-ticker-store", "data"),
    )
    def update_chatbot_context(pathname, pos_ticker, wl_ticker, overview_ticker, chatbot_ticker):
        page_name = "Overview"
        active_ticker = None

        if pathname == "/positions":
            page_name = "Positions"
            active_ticker = pos_ticker
        elif pathname == "/watchlist":
            page_name = "Watchlist"
            active_ticker = wl_ticker
        elif pathname == "/analytics":
            page_name = "Deep Dive"
        elif pathname == "/intelligence":
            page_name = "Insights"
        elif pathname == "/settings":
            page_name = "Settings"
        elif pathname == "/":
            page_name = "Overview"
            if overview_ticker and overview_ticker != "Portfolio":
                active_ticker = overview_ticker

        # Fallback to research search bar ticker if no page-specific ticker is active
        if not active_ticker and chatbot_ticker:
            active_ticker = chatbot_ticker

        # 1. Context display
        context_children = [
            html.Span("Context:", style={"fontWeight": "600"}),
            html.Span(page_name, className="chatbot-context-badge"),
        ]
        if active_ticker:
            context_children.append(
                html.Span(
                    active_ticker.upper(),
                    className="chatbot-context-badge",
                    style={"borderColor": "var(--cyan)", "color": "var(--cyan)"},
                )
            )

        # 2. Quick Prompts visibility and labeling
        qp1, qp2, qp3, qp4 = get_quick_prompt_questions(page_name, active_ticker)
        show_style = {"display": "inline-flex"}

        return (
            context_children,
            qp1,
            show_style,
            qp2,
            show_style,
            qp3,
            show_style,
            qp4,
            show_style,
        )
