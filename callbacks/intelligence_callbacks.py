"""
callbacks/intelligence_callbacks.py
===================================
Callbacks for the Portfolio Intelligence page.
"""
import math
from dash import Input, Output
from config.constants import COLORS, GREEN, RED
from services.intelligence_service import (
    compute_risk_metrics,
    sector_exposure,
    geo_exposure,
    compute_smart_alerts,
)

from components.charts.intel_helpers import create_empty_fig, _BAR_MIN_H
from components.charts.intel_equity import build_intel_equity_chart
from components.charts.intel_drawdown import build_intel_drawdown_chart
from components.charts.intel_volatility import build_intel_volatility_chart
from components.charts.intel_sector import build_intel_sector_chart
from components.charts.intel_geo import build_intel_geo_chart

def register_callbacks(app) -> None:
    @app.callback(
        Output("intel-risk-cards",     "children"),
        Output("intel-equity-chart",   "figure"),
        Output("intel-drawdown-chart", "figure"),
        Output("intel-vol-chart",      "figure"),
        Output("intel-sector-chart",   "figure"),
        Output("intel-geo-chart",      "figure"),
        Output("intel-alerts",         "children"),
        Output("intel-data-note",      "children"),
        Input("portfolio-store",       "data"),
        Input("intel-period-picker",   "value"),
        Input("theme-store",           "data"),
    )
    def update_intelligence(port_data, period, theme):
        from components.ui_helpers import stat_card, alert_card
        from config.constants import get_theme
        
        t_ = get_theme(theme or "dark")
        period = period or "3mo"

        # ── Empty / loading state ─────────────────────────────────────────────
        empty_bar = create_empty_fig(height=_BAR_MIN_H, bar=True, theme_tokens=t_)
        no_data = (
            [stat_card("—", "—")],
            create_empty_fig(height=300, theme_tokens=t_),
            create_empty_fig(height=260, theme_tokens=t_),
            empty_bar, empty_bar, empty_bar,
            [alert_card({
                "level": "info", "icon": "⏳",
                "title": "Waiting for data",
                "detail": "Portfolio data is loading — please wait.",
            })],
            "Waiting for portfolio data…",
        )

        if not port_data or not port_data.get("holdings"):
            return no_data

        holdings  = port_data["holdings"]
        tickers   = sorted({h["ticker"] for h in holdings})
        fetched_at = port_data.get("fetched_at", "")

        data_note = (
            f"Analysing {len(tickers)} ETF(s): {', '.join(tickers)}"
            + (f"  ·  Prices updated {fetched_at}" if fetched_at else "")
            + "  ·  Sector & geo: live from Yahoo Finance (cached 24 h)"
        )

        # ── A. Risk metrics ───────────────────────────────────────────────────
        metrics = compute_risk_metrics(port_data, period=period)
        vol     = metrics["vol"]
        sharpe  = metrics["sharpe"]
        max_dd  = metrics["max_dd"]
        cur_dd  = metrics["current_dd"]
        n_days  = metrics["n_days"]

        def _nan(v):
            return v is None or (isinstance(v, float) and math.isnan(v))

        vol_c  = (RED    if not _nan(vol)    and vol    > 20
                  else COLORS[2] if not _nan(vol)    and vol    > 12 else GREEN)
        shr_c  = (GREEN  if not _nan(sharpe) and sharpe > 1
                  else COLORS[2] if not _nan(sharpe) and sharpe > 0.5 else RED)
        dd_c   = (RED    if not _nan(max_dd) and max_dd < -15
                  else COLORS[2] if not _nan(max_dd) and max_dd < -8 else GREEN)
        cdd_c  = (RED    if not _nan(cur_dd) and cur_dd < -10
                  else COLORS[2] if not _nan(cur_dd) and cur_dd < -5 else GREEN)

        risk_cards = [
            stat_card(
                "Annualised volatility",
                f"{vol:.1f}%" if not _nan(vol) else "N/A",
                f"over {n_days} trading days", vol_c,
                tip="Standard deviation of daily returns, scaled to a year. Below 12% is low risk, 12–20% moderate, above 20% high.",
            ),
            stat_card(
                "Sharpe ratio",
                f"{sharpe:.2f}" if not _nan(sharpe) else "N/A",
                f"Rf = 4.35 %  ·  {n_days} d window", shr_c,
                tip="Return earned per unit of risk taken, above the RBA cash rate (4.35%). Above 1.0 is excellent, above 0.5 is acceptable.",
            ),
            stat_card(
                "Max drawdown",
                f"{max_dd:.1f}%" if not _nan(max_dd) else "N/A",
                "peak-to-trough", dd_c,
                tip="Worst loss from a portfolio peak to its lowest point in the loaded history window. The bigger the number, the deeper the fall.",
            ),
            stat_card(
                "Current drawdown",
                f"{cur_dd:.1f}%" if not _nan(cur_dd) else "N/A",
                "from recent high", cdd_c,
                tip="How far the portfolio is below its most recent all-time high right now. 0% means you are at a new peak.",
            ),
        ]

        # ── B. Equity curve ───────────────────────────────────────────────────
        eq_fig = build_intel_equity_chart(
            metrics.get("ret_dates", []),
            metrics.get("ret_values", []),
            t_
        )

        # ── C. Drawdown curve ─────────────────────────────────────────────────
        dd_fig = build_intel_drawdown_chart(
            metrics.get("dd_dates", []),
            metrics.get("dd_values", []),
            t_
        )

        # ── D. Per-ticker volatility (horizontal bar) ─────────────────────────
        vol_fig = build_intel_volatility_chart(metrics.get("ticker_vols", {}), t_)

        # ── E. Sector exposure (horizontal bar) ───────────────────────────────
        sec_exp = sector_exposure(port_data)
        sec_fig = build_intel_sector_chart(sec_exp, t_)

        # ── F. Geographic exposure (horizontal bar) ───────────────────────────
        geo_data = geo_exposure(port_data)
        geo_fig = build_intel_geo_chart(geo_data, t_)

        # ── G. Smart alerts ───────────────────────────────────────────────────
        alert_cards = [alert_card(a)
                       for a in compute_smart_alerts(metrics, port_data)]

        return (
            risk_cards,
            eq_fig, dd_fig,
            vol_fig, sec_fig, geo_fig,
            alert_cards,
            data_note,
        )
    @app.callback(
        Output("intel-detail-modal", "is_open"),
        Output("intel-modal-title",  "children"),
        Output("intel-modal-graph",  "figure"),
        Input("intel-sector-chart",  "clickData"),
        Input("intel-geo-chart",     "clickData"),
        Input("portfolio-store",     "data"),
        Input("theme-store",         "data"),
        prevent_initial_call=True
    )
    def open_allocation_modal(sec_click, geo_click, port_data, theme):
        import dash
        import plotly.graph_objects as go
        from services.intelligence_service import get_exposure_detail
        from config.constants import get_theme
        
        ctx = dash.callback_context
        if not ctx.triggered or not port_data:
            return dash.no_update, dash.no_update, dash.no_update

        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
        
        # If triggered by portfolio-store refresh, don't close the modal or change content
        if trigger_id == "portfolio-store":
            return dash.no_update, dash.no_update, dash.no_update

        # Determine which chart was clicked
        if trigger_id == "intel-sector-chart":
            click_data = sec_click
            exp_type = "sector"
        elif trigger_id == "intel-geo-chart":
            click_data = geo_click
            exp_type = "geo"
        else:
            # Fallback for unexpected triggers
            return dash.no_update, dash.no_update, dash.no_update

        if not click_data:
            return dash.no_update, dash.no_update, dash.no_update
            
        category = click_data["points"][0]["label"]
        detail = get_exposure_detail(port_data, exp_type, category)
        
        if not detail:
            # Only close if we explicitly have no data for a click
            return False, dash.no_update, go.Figure()

        # Build Sunburst Figure
        # Using branchvalues="remainder" is safer for precision: 
        # parents have value 0, leaves have the weights.
        ids = [category]
        labels = [category]
        parents = [""]
        values = [0] 
        
        if category == "Other":
            # Hierarchical: Other -> SubCategory -> Ticker
            sub_cats = sorted(list({d["sub_category"] for d in detail}))
            for sc in sub_cats:
                sc_weight = sum(d["weight"] for d in detail if d["sub_category"] == sc)
                if sc_weight < 0.05: continue # Filter out dust
                
                ids.append(f"other_{sc}")
                labels.append(sc)
                parents.append(category)
                values.append(0) # Let children define the weight
                
                for d in detail:
                    if d["sub_category"] == sc:
                        if d["weight"] < 0.05: continue
                        ids.append(f"other_{sc}_{d['ticker']}")
                        labels.append(d["ticker"])
                        parents.append(f"other_{sc}")
                        values.append(d["weight"])
        else:
            # Simple: Category -> Tickers
            for d in detail:
                if d["weight"] < 0.05: continue
                ids.append(f"cat_{d['ticker']}")
                labels.append(d["ticker"])
                parents.append(category)
                values.append(d["weight"])

        fig = go.Figure(go.Sunburst(
            ids=ids,
            labels=labels,
            parents=parents,
            values=values,
            branchvalues="remainder",
            hovertemplate="<b>%{label}</b><br>Portfolio Weight: %{value:.2f}%<extra></extra>",
            marker=dict(colors=COLORS * 3),
        ))
        
        t_ = get_theme(theme or "dark")
        fig.update_layout(
            margin=dict(t=20, l=20, r=20, b=20),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color=t_["T_PRI"], size=12),
            height=500,
            uirevision=True, # Preserve zoom/pan/drill-down state across auto-refreshes
        )
        
        title = f"{'Sector' if exp_type == 'sector' else 'Geographic'} Breakdown: {category}"
        return True, title, fig

    @app.callback(
        Output("intel-detail-modal", "is_open", allow_duplicate=True),
        Input("intel-modal-close-btn", "n_clicks"),
        prevent_initial_call=True
    )
    def close_modal(n):
        if n:
            return False
        return dash.no_update
