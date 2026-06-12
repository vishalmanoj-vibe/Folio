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
        if total_val <= 0:
            from components.charts.helpers import create_empty_fig

            return create_empty_fig(
                "Portfolio value is zero", height=600, theme_tokens=theme_tokens
            )

        for h in holdings:
            ticker = h["ticker"]
            etf_val = h.get("mkt_value", 0)
            if etf_val < 0.01:
                continue

            etf_holdings = holdings_data.get(ticker)
            if not etf_holdings:
                # ETF without holdings details: render as a leaf node under root
                ids.append(ticker)
                labels.append(ticker)
                parents.append("")
                values.append(etf_val)
                colors.append(-10.0)
                custom_data_list.append("100.00%")
                hover_texts.append(
                    f"<b>{ticker} (No holdings details)</b><br>"
                    f"Market Value: ${etf_val:,.2f}<br>"
                    f"Portfolio Weight: {(etf_val / total_val * 100):.2f}%"
                )
                font_colors.append(theme_tokens["T_PRI"])
                continue

            # Add parent node for the ETF
            ids.append(ticker)
            labels.append(ticker)
            parents.append("")
            values.append(etf_val)
            colors.append(-10.0)
            port_weight = etf_val / total_val * 100
            custom_data_list.append(f"{port_weight:.2f}%")
            hover_texts.append(
                f"<b>ETF: {ticker}</b><br>"
                f"Market Value: ${etf_val:,.2f}<br>"
                f"Portfolio Weight: {port_weight:.2f}%"
            )
            font_colors.append(theme_tokens["T_PRI"])

            # Sort holdings of this ETF descending
            sorted_holdings = sorted(etf_holdings.items(), key=lambda x: x[1], reverse=True)
            top_n = 20
            top_holdings = sorted_holdings[:top_n]
            other_holdings = sorted_holdings[top_n:]
            other_weight = sum(w for _, w in other_holdings)

            # Generate child nodes, ensuring exact mathematical sum matches etf_val
            children_specs = [(comp, w) for comp, w in top_holdings]
            if other_weight > 0.01:
                children_specs.append(("Other", other_weight))

            remaining_val = etf_val
            for idx, (label, weight) in enumerate(children_specs):
                if idx == len(children_specs) - 1:
                    val = max(0.0, round(remaining_val, 2))
                else:
                    val = round(etf_val * (weight / 100.0), 2)
                    remaining_val -= val

                node_id = f"{ticker}_{label}"
                ids.append(node_id)
                labels.append(label)
                parents.append(ticker)
                values.append(val)
                colors.append(weight)
                custom_data_list.append(f"{weight:.2f}%")

                if label == "Other":
                    hover_texts.append(
                        f"<b>Other Holdings ({ticker})</b><br>"
                        f"Exposure in {ticker}: {weight:.2f}%<br>"
                        f"Value in {ticker}: ${val:,.2f}"
                    )
                else:
                    hover_texts.append(
                        f"<b>{label} ({ticker})</b><br>"
                        f"Exposure in {ticker}: {weight:.2f}%<br>"
                        f"Value in {ticker}: ${val:,.2f}<br>"
                        f"Total ETF Value: ${etf_val:,.2f}"
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
