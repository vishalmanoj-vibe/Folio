import pandas as pd
import plotly.graph_objects as go

from config.constants import GREEN


def build_portfolio_dividend_chart(df_full: pd.DataFrame, theme_tokens: dict) -> go.Figure:
    if df_full.empty:
        from components.charts.helpers import create_empty_fig

        return create_empty_fig(
            "No dividend history available", height=200, theme_tokens=theme_tokens
        )

    # Filter past 1 year
    one_year_ago = pd.Timestamp.now() - pd.DateOffset(years=1)
    df = df_full[df_full["date"] >= one_year_ago].copy()

    if df.empty:
        from components.charts.helpers import create_empty_fig

        return create_empty_fig(
            "No dividends in the past year", height=200, theme_tokens=theme_tokens
        )

    df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()
    monthly = df.groupby("month")["total"].sum().reset_index()

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=monthly["month"],
            y=monthly["total"],
            marker_color=GREEN,
            name="Dividend Income",
            hovertemplate="%{x|%b %Y}<br>$%{y:,.2f}<extra></extra>",
        )
    )

    from components.charts.helpers import apply_standard_layout

    apply_standard_layout(fig, theme_tokens, height=200, chart_type="bar")

    fig.update_layout(
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis=dict(tickformat="%b %y"),
        title=dict(
            text="Portfolio Dividend Income (Past Year)",
            font=dict(size=12, color=theme_tokens["PLOTLY_BASE"]["font"]["color"]),
        ),
    )

    return fig
