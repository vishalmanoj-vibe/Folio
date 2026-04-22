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
    compute_smart_alerts,
    portfolio_returns,
)
from services.prediction_service import get_forecast

from components.charts.intel_helpers import create_empty_fig, _BAR_MIN_H
from components.charts.intel_equity import build_intel_equity_chart
from components.charts.intel_drawdown import build_intel_drawdown_chart

import plotly.graph_objects as go
from components.ui_helpers import stat_card, alert_card
from config.constants import get_theme

def register_callbacks(app) -> None:
    @app.callback(
        Output("intel-risk-cards",     "children"),
        Output("intel-equity-chart",   "figure"),
        Output("intel-drawdown-chart", "figure"),
        Output("intel-alerts",         "children"),
        Output("intel-data-note",      "children"),
        Input("portfolio-store",       "data"),
        Input("intel-period-picker",   "value"),
        Input("theme-store",           "data"),
        Input("intel-pred-toggle",     "value"),
    )
    def update_intelligence(port_data, period, theme, pred_on):
        t_ = get_theme(theme or "dark")
        period = period or "3mo"

        # ── Empty / loading state ─────────────────────────────────────────────
        no_data = (
            [stat_card("—", "—")],
            create_empty_fig(height=300, theme_tokens=t_),
            create_empty_fig(height=300, theme_tokens=t_),
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
        # Pre-compute full returns once to avoid double processing in B2
        histories = port_data.get("histories", {})
        holdings_list = port_data.get("holdings", [])
        full_returns = portfolio_returns(histories, holdings_list)

        metrics = compute_risk_metrics(port_data, period=period, returns=full_returns)
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
                f"{vol:.2f}%" if not _nan(vol) else "N/A",
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
                f"{max_dd:.2f}%" if not _nan(max_dd) else "N/A",
                "peak-to-trough", dd_c,
                tip="Worst loss from a portfolio peak to its lowest point in the loaded history window. The bigger the number, the deeper the fall.",
            ),
            stat_card(
                "Current drawdown",
                f"{cur_dd:.2f}%" if not _nan(cur_dd) else "N/A",
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

        # ── B2. Prediction Trace (Optional) ───────────────────────────────────
        if pred_on:
            full_metrics = compute_risk_metrics(port_data, period="max", returns=full_returns)
            pred_data = get_forecast(
                full_metrics.get("ret_dates", []),
                full_metrics.get("ret_values", []),
                period or "3mo"
            )
            if pred_data:
                p_dates = pred_data["dates"]
                yhat = pred_data["yhat"]
                yhat_l = pred_data["yhat_lower"]
                yhat_u = pred_data["yhat_upper"]
                
                chart_last_v = metrics.get("ret_values", [])[-1] if metrics.get("ret_values") else 0
                full_last_v = full_metrics.get("ret_values", [])[-1] if full_metrics.get("ret_values") else 0
                offset = chart_last_v - full_last_v
                
                yhat = [v + offset for v in yhat]
                yhat_l = [v + offset for v in yhat_l]
                yhat_u = [v + offset for v in yhat_u]
                
                ci_color = "rgba(55, 138, 221, 0.12)"
                eq_fig.add_trace(go.Scatter(
                    x=p_dates + p_dates[::-1],
                    y=yhat_u + yhat_l[::-1],
                    fill='toself', fillcolor=ci_color,
                    line=dict(color='rgba(255,255,255,0)'),
                    hoverinfo="skip", showlegend=True, name="Confidence Interval"
                ))
                
                last_d = metrics.get("ret_dates", [])[-1] if metrics.get("ret_dates") else None
                eq_fig.add_trace(go.Scatter(
                    x=[last_d] + p_dates if last_d else p_dates,
                    y=[chart_last_v] + yhat,
                    mode="lines", name="Forecast",
                    line=dict(color=COLORS[0], width=2, dash="dash"),
                    hovertemplate="Predicted: %{y:.2f}%<extra></extra>",
                ))
                eq_fig.update_layout(xaxis=dict(autorange=True))

        # ── C. Drawdown curve ─────────────────────────────────────────────────
        dd_fig = build_intel_drawdown_chart(
            metrics.get("dd_dates", []),
            metrics.get("dd_values", []),
            t_
        )

        # ── G. Smart alerts ───────────────────────────────────────────────────
        alert_cards = [alert_card(a)
                       for a in compute_smart_alerts(metrics, port_data)]

        return (
            risk_cards,
            eq_fig, dd_fig,
            alert_cards,
            data_note,
        )
