import logging
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, ALL, html

from config import GREEN, RED, COLORS, get_theme

logger = logging.getLogger(__name__)


def register_callbacks(app) -> None:

    # ── Ticker toggle buttons ─────────────────────────────────────────────────
    @app.callback(
        Output("ticker-toggle-btns", "children"),
        Input("portfolio-store",     "data"),
        Input("theme-store",         "data"),
    )
    def build_toggle_btns(data, theme):
        t_ = get_theme(theme or "dark")
        T_PRI = t_["T_PRI"]
        if not data or "holdings" not in data:
            return []
        tickers = ["Portfolio"] + [h["ticker"] for h in data["holdings"]]
        return [
            html.Button(
                t,
                id={"type": "ticker-btn", "index": t},
                n_clicks=0,
                style={
                    "fontSize":     "12px",
                    "padding":      "4px 12px",
                    "borderRadius": "20px",
                    "cursor":       "pointer",
                    "fontWeight":   "500",
                    "background":   "transparent",
                    "border":       f"1.5px solid {T_PRI if t == 'Portfolio' else COLORS[(i - 1) % len(COLORS)]}",
                    "color":        T_PRI if t == "Portfolio" else COLORS[(i - 1) % len(COLORS)],
                },
            )
            for i, t in enumerate(tickers)
        ]

    # ── P&L history ───────────────────────────────────────────────────────────
    @app.callback(
        Output("pnl-history-chart", "figure"),
        Input("portfolio-store",    "data"),
        Input("pnl-mode",           "value"),
        Input("theme-store",        "data"),
        Input({"type": "ticker-btn", "index": ALL}, "n_clicks"),
        State({"type": "ticker-btn", "index": ALL}, "id"),
    )
    def pnl_history_chart(data, mode, theme, n_clicks_list, btn_ids):
        t_ = get_theme(theme or "dark")
        BORDER = t_["BORDER"]
        PLOTLY_BASE = t_["PLOTLY_BASE"]

        fig = go.Figure()
        fig.update_layout(
            xaxis=dict(showgrid=False),
            yaxis=dict(
                gridcolor=BORDER,
                ticksuffix="%" if mode == "pct" else "",
                tickprefix="" if mode == "pct" else "$",
                zeroline=True, zerolinecolor=BORDER, zerolinewidth=1,
            ),
            hovermode="x unified",
            height=380,
            **PLOTLY_BASE,
        )

        if not data or "holdings" not in data:
            return fig

        selected = "Portfolio"
        if n_clicks_list and any(n and n > 0 for n in n_clicks_list):
            last_idx = max(range(len(n_clicks_list)), key=lambda i: n_clicks_list[i] or 0)
            selected = btn_ids[last_idx]["index"]

        holdings  = data["holdings"]
        color_map = {h["ticker"]: COLORS[i % len(COLORS)] for i, h in enumerate(holdings)}

        if selected == "Portfolio":
            series = {}
            for h in holdings:
                for tr in h.get("tranches", []):
                    idx = pd.to_datetime(tr["dates"])
                    key = f"{h['ticker']}_{tr['buy_date']}"
                    series[key] = {
                        "pnl":  pd.Series(tr["pnl"], index=idx),
                        "cost": pd.Series([tr["shares"] * tr["buy_price"]] * len(idx), index=idx),
                    }
            if series:
                cpnl  = pd.concat([v["pnl"]  for v in series.values()], axis=1).ffill().sum(axis=1).sort_index()
                ccost = pd.concat([v["cost"] for v in series.values()], axis=1).ffill().sum(axis=1).sort_index()
                y  = (cpnl / ccost * 100).round(2) if mode == "pct" else cpnl.round(2)
                lv = y.iloc[-1] if len(y) else 0
                lc = GREEN if lv >= 0 else RED
                fc = "rgba(29,158,117,0.12)" if lv >= 0 else "rgba(226,75,74,0.10)"
                fig.add_trace(go.Scatter(
                    x=cpnl.index.strftime("%Y-%m-%d").tolist(), y=y.tolist(),
                    name="Portfolio", mode="lines", fill="tozeroy", fillcolor=fc,
                    line=dict(color=lc, width=2.5),
                    hovertemplate=("%{y:.2f}%<extra>Portfolio</extra>" if mode == "pct"
                                   else "$%{y:,.2f}<extra>Portfolio</extra>"),
                ))
        else:
            hm = next((h for h in holdings if h["ticker"] == selected), None)
            if hm:
                tranches = hm.get("tranches", [])
                bc = color_map.get(selected, COLORS[0])
                if len(tranches) == 1:
                    tr = tranches[0]
                    fig.add_trace(go.Scatter(
                        x=tr["dates"], y=tr["pct"] if mode == "pct" else tr["pnl"],
                        name=selected, mode="lines", fill="tozeroy",
                        fillcolor="rgba(55,138,221,0.10)",
                        line=dict(color=bc, width=2.5),
                    ))
                else:
                    pnl_p, cost_p = [], []
                    for tr in tranches:
                        idx   = pd.to_datetime(tr["dates"])
                        pnl_s = pd.Series(tr["pnl"], index=idx)
                        cst_s = pd.Series([tr["shares"] * tr["buy_price"]] * len(idx), index=idx)
                        pnl_p.append(pnl_s)
                        cost_p.append(cst_s)
                        fig.add_trace(go.Scatter(
                            x=tr["dates"], y=tr["pct"] if mode == "pct" else tr["pnl"],
                            name=f"  {tr['buy_date']} ({int(tr['shares'])} shares)",
                            mode="lines", line=dict(color=bc, width=1, dash="dot"), opacity=0.45,
                        ))
                    cpnl  = pd.concat(pnl_p,  axis=1).ffill().sum(axis=1).sort_index()
                    ccost = pd.concat(cost_p, axis=1).ffill().sum(axis=1).sort_index()
                    yc    = (cpnl / ccost * 100).round(2) if mode == "pct" else cpnl.round(2)
                    fig.add_trace(go.Scatter(
                        x=cpnl.index.strftime("%Y-%m-%d").tolist(), y=yc.tolist(),
                        name=f"{selected} (combined)", mode="lines",
                        fill="tozeroy", fillcolor="rgba(55,138,221,0.10)",
                        line=dict(color=bc, width=2.5),
                    ))

        fig.add_hline(y=0, line_color=BORDER, line_width=0.8)
        return fig

    # ── Normalised price history ──────────────────────────────────────────────
    @app.callback(
        Output("price-chart",    "figure"),
        Input("portfolio-store", "data"),
        Input("theme-store",     "data"),
    )
    def price_chart(data, theme):
        t_ = get_theme(theme or "dark")
        BORDER = t_["BORDER"]
        PLOTLY_BASE = t_["PLOTLY_BASE"]

        fig = go.Figure()
        fig.update_layout(xaxis=dict(showgrid=False), yaxis=dict(gridcolor=BORDER), **PLOTLY_BASE)
        if not data or "histories" not in data:
            return fig
        for i, (t, recs) in enumerate(data["histories"].items()):
            df = pd.DataFrame(recs)
            if df.empty or not df["Close"].iloc[0]:
                continue
            fig.add_trace(go.Scatter(
                x=df["Date"], y=(df["Close"] / df["Close"].iloc[0] * 100).round(2),
                name=t, mode="lines",
                line=dict(color=COLORS[i % len(COLORS)], width=1.8),
            ))
        fig.add_hline(y=100, line_dash="dot", line_color=BORDER)
        return fig

    # ── Allocation donut ──────────────────────────────────────────────────────
    @app.callback(
        Output("allocation-chart", "figure"),
        Input("portfolio-store",   "data"),
        Input("theme-store",       "data"),
    )
    def allocation_chart(data, theme):
        t_ = get_theme(theme or "dark")
        BG = t_["BG"]
        PLOTLY_BASE = t_["PLOTLY_BASE"]

        fig = go.Figure()
        fig.update_layout(**PLOTLY_BASE)
        if not data or "holdings" not in data:
            return fig
        h = data["holdings"]
        fig.add_trace(go.Pie(
            labels=[x["ticker"] for x in h],
            values=[x["mkt_value"] for x in h],
            hole=0.45,
            marker=dict(colors=COLORS[:len(h)], line=dict(color=BG, width=2)),
            textinfo="label+percent",
            textfont=dict(size=12),
        ))
        return fig

    # ── Unrealised P&L bar ────────────────────────────────────────────────────
    @app.callback(
        Output("pnl-bar-chart",  "figure"),
        Input("portfolio-store", "data"),
        Input("pnl-mode",        "value"),
        Input("theme-store",     "data"),
    )
    def pnl_bar(data, mode, theme):
        t_ = get_theme(theme or "dark")
        BORDER = t_["BORDER"]
        PLOTLY_BASE = t_["PLOTLY_BASE"]

        fig = go.Figure()
        fig.update_layout(
            xaxis=dict(showgrid=False),
            yaxis=dict(gridcolor=BORDER,
                       ticksuffix="%" if mode == "pct" else "",
                       tickprefix="" if mode == "pct" else "$"),
            **PLOTLY_BASE,
        )
        if not data or "holdings" not in data:
            return fig
        key = "pnl_pct" if mode == "pct" else "pnl"
        h   = sorted(data["holdings"], key=lambda x: x[key])
        fig.add_trace(go.Bar(
            x=[x["ticker"] for x in h],
            y=[x[key] for x in h],
            marker_color=[GREEN if x[key] >= 0 else RED for x in h],
            text=[f"{'+' if x[key] >= 0 else ''}{'%' if mode == 'pct' else '$'}{abs(x[key]):,.2f}" for x in h],
            textposition="outside", textfont=dict(size=11),
        ))
        fig.add_hline(y=0, line_color=BORDER, line_width=1)
        return fig

    # ── Day P&L bar ───────────────────────────────────────────────────────────
    @app.callback(
        Output("day-pnl-chart",  "figure"),
        Input("portfolio-store", "data"),
        Input("theme-store",     "data"),
    )
    def day_pnl_chart(data, theme):
        t_ = get_theme(theme or "dark")
        BORDER = t_["BORDER"]
        PLOTLY_BASE = t_["PLOTLY_BASE"]

        fig = go.Figure()
        fig.update_layout(
            xaxis=dict(showgrid=False),
            yaxis=dict(gridcolor=BORDER, tickprefix="$"),
            **PLOTLY_BASE,
        )
        if not data or "holdings" not in data:
            return fig
        h = sorted(data["holdings"], key=lambda x: x["day_pnl"])
        fig.add_trace(go.Bar(
            x=[x["ticker"] for x in h],
            y=[x["day_pnl"] for x in h],
            marker_color=[GREEN if x["day_pnl"] >= 0 else RED for x in h],
            text=[f"${x['day_pnl']:,.2f}  {'+' if x['day_chg_pct'] >= 0 else ''}{x['day_chg_pct']:.2f}%" for x in h],
            textposition="outside", textfont=dict(size=11),
        ))
        fig.add_hline(y=0, line_color=BORDER, line_width=1)
        return fig

    # ── Annual dividend income ────────────────────────────────────────────────
    @app.callback(
        Output("dividend-chart", "figure"),
        Input("portfolio-store", "data"),
        Input("theme-store",     "data"),
    )
    def dividend_chart(data, theme):
        t_ = get_theme(theme or "dark")
        T_SEC = t_["T_SEC"]
        BORDER = t_["BORDER"]
        PLOTLY_BASE = t_["PLOTLY_BASE"]

        fig = go.Figure()
        fig.update_layout(
            xaxis=dict(showgrid=False),
            yaxis=dict(gridcolor=BORDER, tickprefix="$"),
            **PLOTLY_BASE,
        )
        if not data or "holdings" not in data:
            return fig
        h = [x for x in data["holdings"] if x["annual_div"] > 0]
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

    # ── Correlation heatmap ───────────────────────────────────────────────────
    @app.callback(
        Output("corr-chart",     "figure"),
        Input("portfolio-store", "data"),
        Input("theme-store",     "data"),
    )
    def corr_chart(data, theme):
        t_ = get_theme(theme or "dark")
        T_SEC = t_["T_SEC"]
        PLOTLY_BASE = t_["PLOTLY_BASE"]

        fig = go.Figure()
        fig.update_layout(**PLOTLY_BASE)
        if not data or "histories" not in data or len(data["histories"]) < 2:
            fig.add_annotation(text="Need 2+ holdings with history",
                               showarrow=False, font=dict(color=T_SEC, size=13))
            return fig

        dfs = {}
        for t, r in data["histories"].items():
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