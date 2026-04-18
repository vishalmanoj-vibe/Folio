import plotly.graph_objects as go
from config.constants import GREEN, RED

def build_pnl_bar_figure(holdings: list[dict], mode: str, theme_tokens: dict) -> go.Figure:
    BORDER      = theme_tokens["BORDER"]
    PLOTLY_BASE = theme_tokens["PLOTLY_BASE"]
    
    fig = go.Figure()
    fig.update_layout(
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor=BORDER,
                   ticksuffix="%" if mode == "pct" else "",
                   tickprefix="" if mode == "pct" else "$"),
        **PLOTLY_BASE,
    )
    
    key = "pnl_pct" if mode == "pct" else "pnl"
    h   = sorted(holdings, key=lambda x: x[key])
    
    fig.add_trace(go.Bar(
        x=[x["ticker"] for x in h],
        y=[x[key] for x in h],
        marker_color=[GREEN if x[key] >= 0 else RED for x in h],
        text=[
            f"{'+' if x[key]>=0 else ''}{'%' if mode=='pct' else '$'}{abs(x[key]):,.2f}"
            for x in h
        ],
        textposition="outside", textfont=dict(size=11),
    ))
    fig.add_hline(y=0, line_color=BORDER, line_width=1)
    return fig
