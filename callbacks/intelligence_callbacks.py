"""
callbacks/intelligence_callbacks.py
===================================
Callbacks for the Portfolio Intelligence page.
"""
import math
import logging
from dash import Input, Output
from config.constants import COLORS, GREEN, RED

logger = logging.getLogger(__name__)

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

import dash
import plotly.graph_objects as go
from services.intelligence_service import get_exposure_detail
from components.ui_helpers import stat_card, alert_card
from config.constants import get_theme

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
        ctx = dash.callback_context
        if not ctx.triggered or not port_data:
            return dash.no_update, dash.no_update, dash.no_update

        try:
            trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
            logger.debug(f"Allocation modal triggered by: {trigger_id}")
            
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
                return dash.no_update, dash.no_update, dash.no_update

            logger.debug(f"Allocation modal click data: {click_data}")

            if not click_data or "points" not in click_data or not click_data["points"]:
                logger.debug("Allocation modal: click data empty or malformed, ignoring.")
                return dash.no_update, dash.no_update, dash.no_update
                
            point = click_data["points"][0]
            category = point.get("label") or point.get("y") or point.get("x") or point.get("customdata")
            
            logger.debug(f"Allocation modal category: {category}")

            if not category or not isinstance(category, str):
                logger.debug("Allocation modal: category missing or not a string, ignoring.")
                return dash.no_update, dash.no_update, dash.no_update

            category = category.strip()
            logger.info(f"Allocation modal requested: type={exp_type}, cat='{category}'")

            detail = get_exposure_detail(port_data, exp_type, category)
            
            if not detail:
                logger.info(f"No exposure detail found for {exp_type}='{category}'")
                return False, dash.no_update, go.Figure()

            # Build Sunburst Figure
            detail = [d for d in detail if d["weight"] >= 0.01]
            if not detail:
                return False, dash.no_update, go.Figure()

            ids = [category]
            labels = [category]
            parents = [""]
            
            root_value = sum(d["weight"] for d in detail)
            values = [root_value] 
            
            if category == "Other":
                sub_cats = sorted(list({d["sub_category"] for d in detail}))
                for sc in sub_cats:
                    sc_weight = sum(d["weight"] for d in detail if d["sub_category"] == sc)
                    ids.append(f"other_{sc}")
                    labels.append(sc)
                    parents.append(category)
                    values.append(sc_weight) 
                    for d in detail:
                        if d["sub_category"] == sc:
                            ids.append(f"other_{sc}_{d['ticker']}")
                            labels.append(d["ticker"])
                            parents.append(f"other_{sc}")
                            values.append(d["weight"])
            else:
                for d in detail:
                    ids.append(f"cat_{d['ticker']}")
                    labels.append(d["ticker"])
                    parents.append(category)
                    values.append(d["weight"])

            values = [round(v, 6) for v in values]

            fig = go.Figure(go.Sunburst(
                ids=ids, labels=labels, parents=parents, values=values,
                branchvalues="total",
                hovertemplate="<b>%{label}</b><br>Portfolio Weight: %{value:.2f}%<extra></extra>",
                marker=dict(colors=COLORS * 3),
            ))
            
            t_ = get_theme(theme or "dark")
            layout_override = t_["PLOTLY_BASE"].copy()
            layout_override.update(dict(
                paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(t=20, l=20, r=20, b=20),
                height=500,
                uirevision=True,
            ))
            fig.update_layout(layout_override)
            
            title = f"{'Sector' if exp_type == 'sector' else 'Geographic'} Breakdown: {category}"
            return True, title, fig

        except Exception as e:
            logger.error(f"Allocation modal error: {e}", exc_info=True)
            return dash.no_update, dash.no_update, dash.no_update

    @app.callback(
        Output("intel-detail-modal", "is_open", allow_duplicate=True),
        Input("intel-modal-close-btn", "n_clicks"),
        prevent_initial_call=True
    )
    def close_modal(n):
        if n:
            return False
        return dash.no_update