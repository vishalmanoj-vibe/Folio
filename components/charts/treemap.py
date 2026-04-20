"""
components/charts/treemap.py
============================
Scalable Portfolio Treemap.
Size = Market Value (Allocation)
Color = P&L % (Performance)
"""

import plotly.graph_objects as go

def build_portfolio_treemap(holdings: list[dict], theme_tokens: dict) -> go.Figure:
    """
    Build a unified portfolio treemap.
    
    Args:
        holdings: List of enriched holding dictionaries.
        theme_tokens: Dictionary of UI theme colors and base layouts.
    """
    if not holdings:
        return go.Figure()

    # Use absolute P&L for size to show impact (Gain or Loss)
    tickers = [h["ticker"] for h in holdings]
    values = [max(abs(h["pnl"]), 0.01) for h in holdings]
    pnl_vals = [h["pnl"] for h in holdings]
    
    # Custom labels to show signed P&L
    display_vals = []
    for h in holdings:
        sign = "+" if h["pnl"] >= 0 else ""
        display_vals.append(f"{sign}${h['pnl']:,.2f}")

    # Custom hover labels
    hover_texts = []
    for h in holdings:
        sign = "+" if h["pnl"] >= 0 else ""
        txt = (
            f"<b>{h['ticker']}</b><br>"
            f"P&L (Excl. Div): {sign}${h['pnl']:,.2f} ({h['pnl_pct']:+.2f}%)<br>"
            f"Market Value: ${h['mkt_value']:,.2f}"
        )
        hover_texts.append(txt)

    # Color scale: Red -> Grey -> Green
    # Dynamically scale intensity based on the biggest mover
    max_pnl_abs = max(values) if values else 1
    
    fig = go.Figure(go.Treemap(
        labels=tickers,
        parents=[""] * len(tickers),
        values=values,
        customdata=display_vals,
        branchvalues="total",
        marker=dict(
            colors=pnl_vals,
            colorscale=[
                [0.0, "#E24B4A"], # Vibrant Red for max loss
                [0.48, "#662222"], # Darker Red for small losses
                [0.5, "#444444"],  # Neutral Grey for zero
                [0.52, "#226622"], # Darker Green for small gains
                [1.0, "#1D9E75"]  # Vibrant Green for max gain
            ],
            cmid=0,
            cmin=-max_pnl_abs,
            cmax=max_pnl_abs,
            line=dict(color="#111110", width=2),
            pad=dict(b=5, l=5, r=5, t=5),
        ),
        textinfo="label+text",
        texttemplate="<b>%{label}</b><br>%{customdata}",
        textfont=dict(size=14, color="white"),
        hoverinfo="text",
        hovertext=hover_texts,
    ))

    fig.update_layout(
        paper_bgcolor="#111110",
        plot_bgcolor="#111110",
        margin=dict(t=10, b=10, l=10, r=10),
        height=450,
        uirevision=True,
    )
    
    return fig
