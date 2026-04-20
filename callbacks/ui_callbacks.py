"""
UI Callbacks for Portfolio Dashboard.

Handles general UI interactions such as theme toggling and printing.
"""

from dash import Input, Output, State


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