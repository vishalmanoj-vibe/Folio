from dash import Input, Output, State


def register_callbacks(app) -> None:

    # ── Dark / light theme toggle ─────────────────────────────────────────────
    app.clientside_callback(
        """
        function(n, current) {
            // If this is initial call (n is null/undefined), use current theme
            // If button was clicked (n > 0), toggle the theme
            const shouldToggle = n > 0;
            const theme = shouldToggle ? (current === 'dark' ? 'light' : 'dark') : current;
            
            document.body.setAttribute('data-theme', theme);
            document.documentElement.style.backgroundColor = theme === 'dark' ? '#111110' : '#ffffff';
            return theme;
        }
        """,
        Output("theme-store",    "data"),
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