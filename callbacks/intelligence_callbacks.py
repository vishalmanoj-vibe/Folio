# callbacks/intelligence_callbacks.py
"""
callbacks/intelligence_callbacks.py
===================================
Callbacks for the Portfolio Intelligence page.
"""
import math
import logging
from dash import Input, Output, State, html
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
        Input("intel-period-store",    "data"),
        Input("theme-store",           "data"),
        Input("intel-pred-store",      "data"),
        Input("url", "pathname"),
        State("intel-pred-toggle",     "checked"),
        State("intel-period-picker",   "value"),
        prevent_initial_call=False,
    )
    def update_intelligence(port_data, period_st, theme, pred_st, url_pathname, pred_ui, period_ui):
        import dash
        # FIX: prevent background recalculation when not on Intelligence page
        if url_pathname != "/intelligence": return tuple([dash.no_update] * 5)
        t_ = get_theme(theme or "dark")
        period = period_st or period_ui or "3mo"
        
        # UI toggle takes precedence during interaction; store provides session persistence
        pred_on = pred_ui if pred_ui is not None else pred_st

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

        try:
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
                    tip="Return earned per unit of risk taken, above the RBA cash rate (4.35%). Above 1.0 is considered good.",
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
            eq_fig.update_layout(uirevision=f"pred_{pred_on}")

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

                    from datetime import datetime, timedelta
                    p_dates_dt = [datetime.strptime(d, "%Y-%m-%d") for d in p_dates]
                    last_d = metrics.get("ret_dates", [])[-1] if metrics.get("ret_dates") else None
                    last_d_dt = datetime.strptime(last_d, "%Y-%m-%d") if last_d else None
                    
                    ci_color = "rgba(0, 201, 167, 0.1)" # Teal CI
                    eq_fig.add_trace(go.Scatter(
                        x=p_dates_dt + p_dates_dt[::-1],
                        y=yhat_u + yhat_l[::-1],
                        fill='toself', fillcolor=ci_color,
                        line=dict(color='rgba(255,255,255,0)'),
                        hoverinfo="skip", showlegend=True, name="Confidence Interval"
                    ))
                    
                    eq_fig.add_trace(go.Scatter(
                        x=[last_d_dt] + p_dates_dt if last_d_dt else p_dates_dt,
                        y=[chart_last_v] + yhat,
                        mode="lines+markers", name="Forecast",
                        line=dict(color=t_["CYAN"], width=3, dash="dash"),
                        marker=dict(size=4, color=t_["CYAN"]),
                        hovertemplate="Predicted: %{y:.2f}%<extra></extra>",
                    ))
                    
                    # Force X-axis to frame both history and forecast perfectly
                    if p_dates_dt and metrics.get("ret_dates"):
                        start_d = datetime.strptime(metrics["ret_dates"][0], "%Y-%m-%d")
                        eq_fig.update_layout(xaxis=dict(range=[start_d, p_dates_dt[-1]]))

            # ── C. Drawdown curve ─────────────────────────────────────────────────
            dd_fig = build_intel_drawdown_chart(
                metrics.get("dd_dates", []),
                metrics.get("dd_values", []),
                t_
            )

            # ── G. Smart alerts ───────────────────────────────────────────────────
            alert_cards = [alert_card(a)
                           for a in compute_smart_alerts(metrics, port_data)]

            # ── 5. Final Output ───────────────────────────────────────────────────
            # Return signature must match the 5 Outputs defined in the callback:
            # 1. intel-risk-cards
            # 2. intel-equity-chart
            # 3. intel-drawdown-chart
            # 4. intel-alerts
            # 5. intel-data-note
            return (
                risk_cards,
                eq_fig, dd_fig,
                alert_cards,
                data_note
            )
        except Exception:
            logger.exception("Failed to update intelligence page")
            return no_data
