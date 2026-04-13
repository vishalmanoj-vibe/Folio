from dash import Input, Output, State


def register_callbacks(app) -> None:

    # ── Dark / light theme toggle ─────────────────────────────────────────────
    app.clientside_callback(
        """
        function(n, current) {
            const theme = current === 'dark' ? 'light' : 'dark';
            document.body.setAttribute('data-theme', theme);
            return theme;
        }
        """,
        Output("theme-store",    "data"),
        Input("theme-toggle",    "n_clicks"),
        State("theme-store",     "data"),
        prevent_initial_call=True,
    )

    # ── PDF / print button ────────────────────────────────────────────────────
    app.clientside_callback(
        "function(n) { if(n) window.print(); return ''; }",
        Output("pdf-btn", "children"),   # dummy output — just needs somewhere to write
        Input("pdf-btn",  "n_clicks"),
        prevent_initial_call=True,
    )
