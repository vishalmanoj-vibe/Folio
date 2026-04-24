# components/charts/treemap.py
import plotly.graph_objects as go

def build_portfolio_treemap(
    holdings: list[dict], 
    theme_tokens: dict, 
    mode: str = "flat",
    sector_data: dict[str, dict] = None,
    geo_data: dict[str, dict] = None
) -> go.Figure:
    """
    Build a unified portfolio treemap with optional hierarchical grouping.
    """
    if not holdings:
        return go.Figure()

    ids = []
    labels = []
    parents = []
    values = []
    colors = []
    hover_texts = []
    custom_data_list = []

    # 1. Prepare hierarchy mapping
    # ─────────────────────────────────────────────────────────────────────────
    if mode == "sector" and sector_data:
        child_nodes = []
        parent_sums = {}
        
        for h in holdings:
            t = h["ticker"]
            weights = sector_data.get(t, {"Unclassified": 100.0})
            for s, pct in weights.items():
                val = round(h["mkt_value"] * (pct / 100.0), 2)
                if val < 0.01: continue
                child_nodes.append((s, t, val, h))
                parent_sums[s] = round(parent_sums.get(s, 0) + val, 2)

        for s in sorted(parent_sums.keys()):
            ids.append(s)
            labels.append(s)
            parents.append("")
            values.append(parent_sums[s])
            colors.append(0) 
            hover_texts.append(f"<b>Sector: {s}</b><br>Total Value: ${parent_sums[s]:,.2f}")
            custom_data_list.append("")

        for s, t, val, h in child_nodes:
            node_id = f"{s}_{t}"
            ids.append(node_id)
            labels.append(t)
            parents.append(s)
            values.append(val)
            colors.append(h["pnl_pct"])
            
            sign = "+" if h["pnl"] >= 0 else ""
            pct_of_parent = (val / parent_sums[s]) * 100
            custom_data_list.append(f"{pct_of_parent:.1f}%")
            hover_texts.append(
                f"<b>{t} ({s})</b><br>"
                f"Value in Sector: ${val:,.2f}<br>"
                f"Weight in Sector: {pct_of_parent:.1f}%<br>"
                f"P&L: {sign}${h['pnl']:,.2f} ({h['pnl_pct']:+.2f}%)"
            )

    elif mode == "geo" and geo_data:
        child_nodes = []
        parent_sums = {}

        for h in holdings:
            t = h["ticker"]
            weights = geo_data.get(t, {"Unclassified": 100.0})
            for r, pct in weights.items():
                val = round(h["mkt_value"] * (pct / 100.0), 2)
                if val < 0.01: continue
                child_nodes.append((r, t, val, h))
                parent_sums[r] = round(parent_sums.get(r, 0) + val, 2)

        for r in sorted(parent_sums.keys()):
            ids.append(r)
            labels.append(r)
            parents.append("")
            values.append(parent_sums[r])
            colors.append(0)
            hover_texts.append(f"<b>Region: {r}</b><br>Total Value: ${parent_sums[r]:,.2f}")
            custom_data_list.append("")

        for r, t, val, h in child_nodes:
            node_id = f"{r}_{t}"
            ids.append(node_id)
            labels.append(t)
            parents.append(r)
            values.append(val)
            colors.append(h["pnl_pct"])
            
            sign = "+" if h["pnl"] >= 0 else ""
            pct_of_parent = (val / parent_sums[r]) * 100
            custom_data_list.append(f"{pct_of_parent:.1f}%")
            hover_texts.append(
                f"<b>{t} ({r})</b><br>"
                f"Value in Region: ${val:,.2f}<br>"
                f"Weight in Region: {pct_of_parent:.1f}%<br>"
                f"P&L: {sign}${h['pnl']:,.2f} ({h['pnl_pct']:+.2f}%)"
            )

    else:
        for h in holdings:
            val = round(h["mkt_value"], 2)
            ids.append(h["ticker"])
            labels.append(h["ticker"])
            parents.append("")
            values.append(val)
            colors.append(h["pnl_pct"])
            
            sign = "+" if h["pnl"] >= 0 else ""
            custom_data_list.append(f"{sign}${h['pnl']:,.2f}")
            hover_texts.append(
                f"<b>{h['ticker']}</b><br>"
                f"Market Value: ${val:,.2f}<br>"
                f"P&L: {sign}${h['pnl']:,.2f} ({h['pnl_pct']:+.2f}%)"
            )

    # 2. Build Figure
    # ─────────────────────────────────────────────────────────────────────────
    valid_colors = [c for c in colors if c is not None and c != 0]
    max_perf = max([abs(c) for c in valid_colors] + [10]) if valid_colors else 10
    
    fig = go.Figure(go.Treemap(
        ids=ids,
        labels=labels,
        parents=parents,
        values=values,
        customdata=custom_data_list,
        branchvalues="total",
        marker=dict(
            colors=colors,
            colorscale=[
                [0.0, "#E24B4A"], 
                [0.48, "#662222"],
                [0.5, "#2D2D2D"],  # Slightly lighter grey for neutral
                [0.52, "#226622"],
                [1.0, "#1D9E75"]  
            ],
            cmid=0,
            cmin=-max_perf,
            cmax=max_perf,
            line=dict(color="rgba(255,255,255,0.1)", width=2), # Visible borders
            pad=dict(b=5, l=5, r=5, t=5),
        ),
        textinfo="label+text",
        texttemplate="<b>%{label}</b><br>%{customdata}",
        textfont=dict(size=14, color="white"),
        hoverinfo="text",
        hovertext=hover_texts,
    ))

    fig.update_layout(
        paper_bgcolor=theme_tokens["BG"],
        plot_bgcolor=theme_tokens["BG"],
        margin=dict(t=0, b=0, l=0, r=0),
        height=600,
        uirevision=True,
    )
    
    return fig
