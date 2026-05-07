# Skill: Add Chart

## Objective
Add a new Plotly chart to the portfolio dashboard following the
exact modular architecture — no shortcuts, no inline figures.

## Rules of Engagement
- Read the relevant callback file before touching it
- Never modify existing component IDs
- Always use CSS variables — never hardcode colors
- Figure builder must be a standalone function returning go.Figure
- theme_tokens dict must be passed in — never access config directly

## Steps

### 1. Read first
Open and read:
- components/charts/ (see what already exists)
- callbacks/chart_callbacks.py (find register_callbacks pattern)
- config/constants.py (check COLORS, GREEN, RED, CHART_INFO)
- config/settings.py (check PLOTLY_BASE and theme token structure)

### 2. Create the figure builder
Save to: components/charts/{chart_name}.py

Required signature:
  def build_{chart_name}_figure(
      holdings: list[dict],   # or histories: dict — match what you need
      theme_tokens: dict,
      [mode: str]             # only if the chart has abs/pct toggle
  ) -> go.Figure:

Figure layout must use:
  fig.update_layout(**PLOTLY_BASE)
  yaxis gridcolor=BORDER from theme_tokens
  No hardcoded colors — use COLORS, GREEN, RED from config.constants

### 3. Wire the callback
In callbacks/chart_callbacks.py, inside register_callbacks(app):

  @app.callback(
      Output("{chart-id}", "figure"),
      Input("portfolio-store", "data"),
      Input("theme-store", "data"),
      [Input("pnl-mode", "value")]   # only if mode-dependent
  )
  def update_{chart_name}(portfolio_data, theme, [mode]):
      holdings = portfolio_data.get("holdings", [])
      if not holdings:
          return go.Figure()
      tokens = get_theme(theme)
      return build_{chart_name}_figure(holdings, tokens)

### 4. Add the layout slot
In components/layout.py, add inside the charts grid section:
  html.Div([
      chart_title("{Chart Label}", "{chart-key}"),
      dcc.Graph(id="{chart-id}", config={"displayModeBar": False})
  ], style={"flex": "1", "minWidth": "260px"})

Add tooltip to CHART_INFO in config/constants.py if needed.

### 5. Verify
Run: python app.py
Confirm the chart renders on first paint with no errors.