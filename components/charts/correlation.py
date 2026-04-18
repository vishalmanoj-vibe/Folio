import pandas as pd
import plotly.graph_objects as go

def build_corr_figure(histories: dict, theme_tokens: dict) -> go.Figure:
    T_SEC       = theme_tokens["T_SEC"]
    PLOTLY_BASE = theme_tokens["PLOTLY_BASE"]
    
    fig = go.Figure()
    fig.update_layout(**PLOTLY_BASE)
    
    if not histories or len(histories) < 2:
        fig.add_annotation(text="Need 2+ holdings with history",
                           showarrow=False, font=dict(color=T_SEC, size=13))
        return fig
        
    dfs = {}
    for t, r in histories.items():
        s = pd.DataFrame(r).set_index("Date")["Close"].pct_change().dropna()
        if len(s) >= 10:
            dfs[t] = s
            
    if len(dfs) < 2:
        fig.add_annotation(text="Need 2+ holdings with at least 10 days of history",
                           showarrow=False, font=dict(color=T_SEC, size=13))
        return fig
        
    corr  = pd.DataFrame(dfs).corr(min_periods=10).round(2)
    ticks = list(corr.columns)
    
    fig.add_trace(go.Heatmap(
        z=corr.values.tolist(), x=ticks, y=ticks,
        colorscale=[[0, "#1D9E75"], [0.5, "#EF9F27"], [1, "#E24B4A"]],
        zmin=-1, zmax=1,
        text=[[f"{v:.2f}" for v in row] for row in corr.values.tolist()],
        texttemplate="%{text}", textfont=dict(size=11),
        showscale=True, colorbar=dict(thickness=12, len=0.8),
    ))
    
    fig.update_layout(
        xaxis=dict(showgrid=False, tickfont=dict(size=11)),
        yaxis=dict(showgrid=False, tickfont=dict(size=11), autorange="reversed"),
    )
    return fig
