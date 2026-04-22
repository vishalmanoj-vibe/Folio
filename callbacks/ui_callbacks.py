"""
UI Callbacks for Portfolio Dashboard.

Handles general UI interactions such as theme toggling and printing.
"""

from dash import Input, Output, State, ALL, ctx, html
import dash


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
            document.documentElement.style.backgroundColor = theme === 'dark' ? '#0a0a0a' : '#ffffff';
            
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
        Output("compact-toggle-btn", "className"),
        Input("compact-toggle-btn", "n_clicks"),
        State("compact-mode-store", "data"),
        prevent_initial_call=False
    )
    def toggle_compact_mode(n, is_compact):
        # Determine if we are in the initial load
        triggered = [t['prop_id'] for t in dash.callback_context.triggered]
        is_initial = not triggered or triggered == [''] or triggered == ['.']
        
        if is_initial:
            new_state = True # Always start collapsed
        else:
            new_state = not is_compact
        
        opened = not new_state
        label  = "Hide Form" if opened else "Add Transaction"
        icon   = "−" if opened else "+"
        
        children = [
            html.Span(icon, style={"fontSize": "16px", "fontWeight": "bold"}),
            label
        ]
        
        # Teal highlight when closed, standard when opened
        btn_class = "btn-primary btn-sm" if not opened else "btn-sm"
        
        return new_state, opened, children, btn_class


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


    # ── Active Nav Link Highlighting ──────────────────────────────────────────
    app.clientside_callback(
        """
        function(pathname) {
            const links = document.querySelectorAll('.nav-link');
            links.forEach(link => {
                const href = link.getAttribute('href');
                if (href === pathname) {
                    link.classList.add('active');
                } else {
                    link.classList.remove('active');
                }
            });
            return window.dash_clientside.no_update;
        }
        """,
        Output("nav-link-store", "data"),
        Input("url", "pathname"),
    )