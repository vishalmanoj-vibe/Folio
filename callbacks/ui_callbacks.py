"""
UI Callbacks for Portfolio Dashboard.

Handles general UI interactions such as theme toggling and printing.
"""

from dash import Input, Output, State, ALL, ctx


def register_callbacks(app) -> None:
    """
    Register UI-related callbacks with the Dash application.

    Args:
        app: The Dash application instance.
    """

    # ── Dark / light theme toggle ─────────────────────────────────────────────
    app.clientside_callback(
        """
        function(n, current) {
            const shouldToggle = n > 0;
            const theme = shouldToggle ? (current === 'dark' ? 'light' : 'dark') : current;
            
            document.body.setAttribute('data-theme', theme);
            document.documentElement.style.backgroundColor = theme === 'dark' ? '#111110' : '#ffffff';
            
            // Return theme for store and icon text
            return [theme, theme === 'dark' ? '☾' : '☀'];
        }
        """,
        [Output("theme-store", "data"), Output("settings-icon-text", "children")],
        Input("theme-toggle",    "n_clicks"),
        State("theme-store",     "data"),
    )

    # ── PDF / print button ────────────────────────────────────────────────────
    app.clientside_callback(
        "function(n) { if(n) window.print(); return ''; }",
        Output("pdf-btn", "children"),   # dummy output — just needs somewhere to write
        Input("pdf-btn",  "n_clicks"),
        prevent_initial_call=True,
    )

    # ── Compact Mode Toggle ──────────────────────────────────────────────────
    @app.callback(
        Output("compact-mode-store", "data"),
        Output("txn-collapse", "opened"),
        Output("compact-toggle-btn", "children"),
        Input("compact-toggle-btn", "n_clicks"),
        State("compact-mode-store", "data"),
        prevent_initial_call=False
    )
    def toggle_compact_mode(n, is_compact):
        import dash
        from dash import html
        
        # On first load (n=None/0), use the stored state
        new_state = not is_compact if n else is_compact
        
        opened = not new_state
        label  = "Hide Form" if opened else "Add Transaction"
        icon   = "−" if opened else "+"
        
        children = [
            html.Span(icon, style={"fontSize": "16px", "fontWeight": "bold", "marginRight": "6px"}),
            label
        ]
        
        return new_state, opened, children


    # ── Table Header Sorting ──────────────────────────────────────────────────
    @app.callback(
        Output("table-state-store", "data"),
        Input({"type": "table-th", "index": ALL}, "n_clicks"),
        State("table-state-store", "data"),
        prevent_initial_call=True
    )
    def update_table_sorting(n_clicks_list, current_state):
        if not ctx.triggered:
            return current_state
        
        # Find which header was clicked
        triggered_id = ctx.triggered_id
        if not triggered_id or not isinstance(triggered_id, dict):
            return current_state
            
        clicked_col = triggered_id["index"]
        
        new_state = current_state.copy()
        if new_state["sort_col"] == clicked_col:
            # Toggle direction
            new_state["sort_dir"] = "asc" if new_state["sort_dir"] == "desc" else "desc"
        else:
            # New column, default to desc for everything except ticker/name
            new_state["sort_col"] = clicked_col
            new_state["sort_dir"] = "asc" if clicked_col in ["ticker", "name"] else "desc"
            
        return new_state