from dash import Input, Output, State, ctx, html, no_update
import dash
import logging
from services.research_service import get_ai_response, build_portfolio_context

logger = logging.getLogger(__name__)

def register_callbacks(app):
    
    # --- CALLBACK 1: Welcome message on first navigation to /research ---
    @app.callback(
        Output("research-chat-store", "data"),
        Input("url", "pathname"),
        State("portfolio-store", "data"),
        State("research-chat-store", "data"),
        prevent_initial_call=True
    )
    def init_research_chat(pathname, portfolio_data, current_history):
        if pathname != "/research":
            return no_update

        # Conversation already exists — do not overwrite it
        if current_history is not None and len(current_history) > 0:
            return no_update

        if not portfolio_data or not portfolio_data.get("holdings"):
            return [{"role": "assistant", "content": "Loading your portfolio data, please wait..."}]

        holdings = portfolio_data["holdings"]
        n = len(holdings)
        total_val = sum(h.get("mkt_value", 0) for h in holdings)

        welcome_msg = (
            f"Hi! I've loaded your portfolio — {n} holdings worth "
            f"${total_val:,.0f}. Ask me about your positions, or type "
            "a ticker on the left to research it. Use the quick "
            "prompts below to get started."
        )

        return [{"role": "assistant", "content": welcome_msg}]

    # --- CALLBACK 2: Send message and get AI response ---
    @app.callback(
        Output("research-chat-store", "data", allow_duplicate=True),
        Output("research-input", "value"),
        Output("research-usage-store", "data", allow_duplicate=True),
        Output("research-typing-indicator", "style"),
        Output("research-send-btn", "disabled"),
        Input("research-send-btn", "n_clicks"),
        Input("qp-1", "n_clicks"),
        Input("qp-2", "n_clicks"),
        Input("qp-3", "n_clicks"),
        Input("qp-4", "n_clicks"),
        State("research-input", "value"),
        State("research-chat-store", "data"),
        State("portfolio-store", "data"),
        State("research-ticker-store", "data"),
        State("research-usage-store", "data"),
        prevent_initial_call=True
    )
    def send_research_message(n_send, n1, n2, n3, n4, input_val, current_history, portfolio_data, ticker, usage_data):
        from datetime import date
        DAILY_LIMIT = 20
        today_str = str(date.today())

        # Guard: if somehow triggered without a real user action, bail immediately
        if not ctx.triggered_id:
            return no_update, no_update, no_update, {"display": "none"}, False

        if not usage_data:
            usage_data = {"count": 0, "reset_date": ""}

        # Reset count if it's a new day
        if usage_data.get("reset_date") != today_str:
            usage_data = {"count": 0, "reset_date": today_str}

        current_count = usage_data.get("count", 0)

        if current_count >= DAILY_LIMIT:
            limit_msg = (
                f"You've reached your {DAILY_LIMIT} free messages "
                f"for today. Your limit resets tomorrow. "
                f"This keeps the service free for personal use."
            )
            limit_history = list(current_history or [])
            limit_history.append({"role": "assistant", "content": limit_msg})
            return limit_history, "", dash.no_update, {"display": "none"}, False

        message = None
        if ctx.triggered_id == "qp-1":
            message = "Does this ticker fit my portfolio?"
        elif ctx.triggered_id == "qp-2":
            message = "What are the main risks of this ticker?"
        elif ctx.triggered_id == "qp-3":
            message = "Compare this ticker to what I already own"
        elif ctx.triggered_id == "qp-4":
            message = "What sectors or regions am I missing in my portfolio?"
        elif ctx.triggered_id == "research-send-btn":
            message = input_val

        if not message or not str(message).strip():
            return no_update, no_update, no_update, {"display": "none"}, False

        history = list(current_history or [])
        history.append({"role": "user", "content": message})

        response = get_ai_response(history, portfolio_data, ticker or "")
        history.append({"role": "assistant", "content": response})

        new_usage = {"count": current_count + 1, "reset_date": today_str}
        return history, "", new_usage, {"display": "none"}, False

    # --- CLIENTSIDE: Show typing indicator immediately on send click ---
    app.clientside_callback(
        """
        function(n_clicks) {
            if (n_clicks && n_clicks > 0) {
                return [{"display": "flex", "padding": "4px 20px 8px"}, true];
            }
            return [{"display": "none"}, false];
        }
        """,
        Output("research-typing-indicator", "style", allow_duplicate=True),
        Output("research-send-btn", "disabled", allow_duplicate=True),
        Input("research-send-btn", "n_clicks"),
        prevent_initial_call=True,
    )

    # --- CALLBACK 3: Render chat messages ---
    @app.callback(
        Output("research-chat-display", "children"),
        Input("research-chat-store", "data"),
        prevent_initial_call=False
    )
    def render_chat(history):
        if not history:
            return html.Div("Your conversation will appear here.", className="research-chat-placeholder")
            
        bubbles = []
        for msg in history:
            cls_name = "chat-bubble-user" if msg.get("role") == "user" else "chat-bubble-assistant"
            bubbles.append(html.Div(msg.get("content", ""), className=cls_name))
            
        return html.Div(bubbles, style={"display": "flex", "flexDirection": "column", "gap": "12px"})

    # --- CALLBACK 4: Store researched ticker ---
    @app.callback(
        Output("research-ticker-store", "data"),
        Input("research-ticker-input", "value"),
        prevent_initial_call=True
    )
    def store_ticker(value):
        if not value or not str(value).strip():
            return ""
        return str(value).strip().upper()

    # --- CALLBACK 5: Render portfolio summary in left panel ---
    @app.callback(
        Output("research-portfolio-summary", "children"),
        Input("portfolio-store", "data"),
        prevent_initial_call=False
    )
    def render_portfolio_summary(portfolio_data):
        if not portfolio_data or not portfolio_data.get("holdings"):
            return html.P("Loading...", style={"color": "var(--t-sec)", "fontSize": "12px"})
            
        holdings = portfolio_data["holdings"]
        total_val = sum(h.get("mkt_value", 0) for h in holdings)
        
        sorted_holdings = sorted(holdings, key=lambda x: x.get("mkt_value", 0), reverse=True)
        
        children = [
            html.P(f"${total_val:,.0f}", style={"fontSize": "18px", "fontWeight": "500", "color": "var(--t-pri)", "margin": "0 0 12px"})
        ]
        
        for h in sorted_holdings:
            mkt_value = h.get("mkt_value", 0)
            weight = (mkt_value / total_val * 100) if total_val > 0 else 0
            pnl_pct = h.get("pnl_pct", 0)
            
            pnl_color = "var(--green)" if pnl_pct >= 0 else "var(--red)"
            pnl_sign = "+" if pnl_pct >= 0 else ""
            
            row = html.Div([
                html.Span(h.get("ticker", ""), className="research-portfolio-ticker"),
                html.Span(f"{weight:.1f}%", className="research-portfolio-weight"),
                html.Span(f"{pnl_sign}{pnl_pct:.1f}%", className="research-portfolio-pnl", style={"color": pnl_color}),
            ], className="research-portfolio-row")
            
            children.append(row)
            
        return children

    # --- CALLBACK 6: Render usage counter display ---
    @app.callback(
        Output("research-usage-display", "children"),
        Input("research-usage-store", "data"),
        Input("url", "pathname"),
    )
    def render_usage_display(usage_data, pathname):
        if pathname != "/research":
            return dash.no_update

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
            "var(--green)" if remaining > 10
            else "var(--warning)" if remaining > 3
            else "var(--red)"
        )

        return html.Div([
            html.Span(
                f"{remaining} of {DAILY_LIMIT} messages remaining today",
                style={
                    "fontSize": "10px",
                    "color": color,
                    "fontWeight": "500",
                }
            ),
            html.Span(
                " · Resets at midnight",
                style={"fontSize": "10px", "color": "var(--t-sec)"}
            ),
        ], style={
            "padding": "6px 20px",
            "borderBottom": "0.5px solid var(--border)",
            "display": "flex",
            "alignItems": "center",
            "gap": "4px",
            "flexShrink": "0",
        })
