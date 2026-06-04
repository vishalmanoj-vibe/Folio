# components/charts/treemap.py
import plotly.graph_objects as go


def build_portfolio_treemap(
    holdings: list[dict],
    theme_tokens: dict,
    mode: str = "flat",
    sector_data: dict[str, dict] | None = None,
    geo_data: dict[str, dict] | None = None,
    holdings_data: dict[str, dict] | None = None,
) -> go.Figure:
    """
    Build a unified portfolio treemap with optional hierarchical grouping.
    """
    if not holdings:
        from components.charts.helpers import create_empty_fig

        return create_empty_fig(
            "No holdings data available for treemap", height=600, theme_tokens=theme_tokens
        )

    if mode == "holdings" and not holdings_data:
        from components.charts.helpers import create_empty_fig

        return create_empty_fig(
            "No underlying holdings data — add a source URL in ⚙ Configure Sources",
            height=600,
            theme_tokens=theme_tokens,
        )

    ids = []
    labels = []
    parents = []
    values = []
    colors: list[float] = []
    hover_texts = []
    custom_data_list = []
    font_colors = []

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
                if val < 0.01:
                    continue
                child_nodes.append((s, t, val, h))
                parent_sums[s] = round(parent_sums.get(s, 0) + val, 2)

        for s in sorted(parent_sums.keys()):
            ids.append(s)
            labels.append(s)
            parents.append("")
            values.append(parent_sums[s])
            colors.append(-10.0)
            hover_texts.append(f"<b>Sector: {s}</b><br>Total Value: ${parent_sums[s]:,.2f}")
            custom_data_list.append("")
            font_colors.append(theme_tokens["T_PRI"])

        for s, t, val, h in child_nodes:
            node_id = f"{s}_{t}"
            ids.append(node_id)
            labels.append(t)
            parents.append(s)
            values.append(val)

            pct_of_parent = (val / parent_sums[s]) * 100
            colors.append(pct_of_parent)

            sign = "+" if h["pnl"] >= 0 else ""
            custom_data_list.append(f"{pct_of_parent:.1f}%")
            hover_texts.append(
                f"<b>{t} ({s})</b><br>"
                f"Value in Sector: ${val:,.2f}<br>"
                f"Weight in Sector: {pct_of_parent:.1f}%<br>"
                f"P&L: {sign}${h['pnl']:,.2f} ({h['pnl_pct']:+.2f}%)"
            )
            font_colors.append("white")

    elif mode == "geo" and geo_data:
        child_nodes = []
        parent_sums = {}

        for h in holdings:
            t = h["ticker"]
            weights = geo_data.get(t, {"Unclassified": 100.0})
            for r, pct in weights.items():
                val = round(h["mkt_value"] * (pct / 100.0), 2)
                if val < 0.01:
                    continue
                child_nodes.append((r, t, val, h))
                parent_sums[r] = round(parent_sums.get(r, 0) + val, 2)

        for r in sorted(parent_sums.keys()):
            ids.append(r)
            labels.append(r)
            parents.append("")
            values.append(parent_sums[r])
            colors.append(-10.0)
            hover_texts.append(f"<b>Region: {r}</b><br>Total Value: ${parent_sums[r]:,.2f}")
            custom_data_list.append("")
            font_colors.append(theme_tokens["T_PRI"])

        for r, t, val, h in child_nodes:
            node_id = f"{r}_{t}"
            ids.append(node_id)
            labels.append(t)
            parents.append(r)
            values.append(val)

            pct_of_parent = (val / parent_sums[r]) * 100
            colors.append(pct_of_parent)

            sign = "+" if h["pnl"] >= 0 else ""
            custom_data_list.append(f"{pct_of_parent:.1f}%")
            hover_texts.append(
                f"<b>{t} ({r})</b><br>"
                f"Value in Region: ${val:,.2f}<br>"
                f"Weight in Region: {pct_of_parent:.1f}%<br>"
                f"P&L: {sign}${h['pnl']:,.2f} ({h['pnl_pct']:+.2f}%)"
            )
            font_colors.append("white")

    elif mode == "holdings" and holdings_data:
        total_val = sum(h.get("mkt_value", 0) for h in holdings)

        # Take top 50 items and group the rest
        top_items = list(holdings_data.items())[:50]
        sum_top_weights = sum(d["weight"] for name, d in top_items)
        all_weights = sum(d["weight"] for name, d in holdings_data.items())
        other_weight = all_weights - sum_top_weights

        for comp_name, d in top_items:
            weight = d["weight"]
            val = round(total_val * (weight / 100.0), 2)
            ids.append(comp_name)
            labels.append(comp_name)
            parents.append("")
            values.append(val)
            colors.append(weight)
            custom_data_list.append(f"{weight:.2f}%")

            sources = d.get("sources", {})
            source_str = "<br>".join([f" • {k}: {v:.2f}%" for k, v in sources.items()])
            hover_texts.append(
                f"<b>{comp_name}</b><br>"
                f"Market Value: ${val:,.2f}<br>"
                f"Total Exposure: {weight:.2f}%<br>"
                f"Sources:<br>{source_str}"
            )
            font_colors.append("white")

        if other_weight > 0.01:
            val = round(total_val * (other_weight / 100.0), 2)
            ids.append("Other Underlying")
            labels.append("Other Underlying")
            parents.append("")
            values.append(val)
            colors.append(other_weight)
            custom_data_list.append(f"{other_weight:.2f}%")
            hover_texts.append(
                f"<b>Other Underlying Holdings</b><br>"
                f"Market Value: ${val:,.2f}<br>"
                f"Total Exposure: {other_weight:.2f}%"
            )
            font_colors.append("white")

    elif mode == "heatmap":
        # Day-change heatmap: diverging red/green color scale
        total_val = sum(h.get("mkt_value", 0) for h in holdings)
        for h in holdings:
            val = round(h.get("mkt_value", 0), 2)
            ids.append(h["ticker"])
            labels.append(h["ticker"])
            parents.append("")
            values.append(val)

            day_chg = h.get("day_chg_pct") or h.get("day_change_pct") or 0.0
            colors.append(float(day_chg))

            sign = "+" if day_chg >= 0 else ""
            weight = (val / total_val * 100) if total_val > 0 else 0.0
            custom_data_list.append(f"{sign}{day_chg:.1f}%")
            hover_texts.append(
                f"<b>{h['ticker']}</b><br>"
                f"Market Value: ${val:,.2f}<br>"
                f"Weight: {weight:.1f}%<br>"
                f"Day Change: {sign}{day_chg:.2f}%"
            )
            font_colors.append("white")

    else:
        total_val = sum(h["mkt_value"] for h in holdings)
        for h in holdings:
            val = round(h["mkt_value"], 2)
            ids.append(h["ticker"])
            labels.append(h["ticker"])
            parents.append("")
            values.append(val)

            weight = (val / total_val) * 100 if total_val > 0 else 0
            colors.append(weight)

            sign = "+" if h["pnl"] >= 0 else ""
            custom_data_list.append(f"{sign}${h['pnl']:,.2f}")
            hover_texts.append(
                f"<b>{h['ticker']}</b><br>"
                f"Market Value: ${val:,.2f}<br>"
                f"P&L: {sign}${h['pnl']:,.2f} ({h['pnl_pct']:+.2f}%)"
            )
            font_colors.append("white")

    # 2. Build Figure
    # ─────────────────────────────────────────────────────────────────────────
    if mode == "heatmap":
        marker_cfg = dict(
            colors=colors,
            colorscale="RdYlGn",
            cauto=False,
            cmid=0,
            cmin=-5,
            cmax=5,
            showscale=True,
            colorbar=dict(
                title=dict(text="Day %", font=dict(size=10, color=theme_tokens["T_SEC"])),
                thickness=10,
                len=0.5,
                tickfont=dict(size=9, color=theme_tokens["T_SEC"]),
                ticksuffix="%",
                outlinewidth=0,
                bgcolor="rgba(0,0,0,0)",
            ),
            line=dict(color=theme_tokens["BORDER"], width=1),
            pad=dict(b=8, l=8, r=8, t=20),
        )
    else:
        marker_cfg = dict(
            colors=colors,
            colorscale=[
                [0.0, theme_tokens["BG"]],
                [0.09, theme_tokens["BG"]],
                [0.091, theme_tokens["RED"]],
                [0.36, theme_tokens["WARNING"]],
                [0.63, theme_tokens["GREEN"]],
                [1.0, theme_tokens["CYAN"]],
            ],
            cauto=False,
            cmid=None,  # Disabled to allow the custom offset
            cmin=-10,
            cmax=100,
            line=dict(color=theme_tokens["BORDER"], width=1),
            pad=dict(b=8, l=8, r=8, t=20),
        )

    fig = go.Figure(
        go.Treemap(
            ids=ids,
            labels=labels,
            parents=parents,
            values=values,
            customdata=custom_data_list,
            branchvalues="total",
            maxdepth=2,
            marker=marker_cfg,
            textinfo="label+text",
            texttemplate="<b>%{label}</b><br>%{customdata}",
            textfont=dict(size=14, color=font_colors),
            hoverinfo="text",
            hovertext=hover_texts,
        )
    )

    fig.update_layout(
        template="none",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        treemapcolorway=None,
        margin=dict(t=0, b=0, l=0, r=0),
        height=600,
        uirevision=f"treemap_{mode}",
    )

    return fig
