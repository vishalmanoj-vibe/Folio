import plotly.graph_objects as go
from config.constants import COLORS

def build_dividend_figure(holdings: list[dict], theme_tokens: dict) -> go.Figure:
    T_SEC       = theme_tokens["T_SEC"]
    BORDER      = theme_tokens["BORDER"]
    PLOTLY_BASE = theme_tokens["PLOTLY_BASE"]
    
    fig = go.Figure()
    fig.update_layout(
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor=BORDER, tickprefix="$"),
        **PLOTLY_BASE,
    )
    
    h = [x for x in holdings if x["annual_div"] > 0]
    if not h:
        fig.add_annotation(text="No dividend data yet — holdings are recent",
                           showarrow=False, font=dict(color=T_SEC, size=13))
        return fig
        
    h_s = sorted(h, key=lambda x: x["annual_div"], reverse=True)
    
    fig.add_trace(go.Bar(
        x=[x["ticker"] for x in h_s],
        y=[x["annual_div"] for x in h_s],
        marker_color=COLORS[1],
        text=[f"${x['annual_div']:,.2f}  ({x['div_yield']:.1f}% yield)" for x in h_s],
        textposition="outside", textfont=dict(size=11),
    ))
    return fig
