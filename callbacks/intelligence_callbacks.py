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
    )
    def update_intelligence(port_data):
        from components.ui_helpers import stat_card, alert_card

        # ── Empty / loading state ─────────────────────────────────────────────
        empty_bar = create_empty_fig(height=_BAR_MIN_H, bar=True)
        no_data = (
            [stat_card("—", "—")],
            create_empty_fig(height=300),
            create_empty_fig(height=260),
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
        metrics = compute_risk_metrics(port_data)
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
            ),
            stat_card(
                "Sharpe ratio",
                f"{sharpe:.2f}" if not _nan(sharpe) else "N/A",
                f"Rf = 4.35 %  ·  {n_days} d window", shr_c,
            ),
            stat_card(
                "Max drawdown",
                f"{max_dd:.1f}%" if not _nan(max_dd) else "N/A",
                "peak-to-trough", dd_c,
            ),
            stat_card(
                "Current drawdown",
                f"{cur_dd:.1f}%" if not _nan(cur_dd) else "N/A",
                "from recent high", cdd_c,
            ),
        ]

        # ── B. Equity curve ───────────────────────────────────────────────────
        eq_fig = build_intel_equity_chart(
            metrics.get("ret_dates", []),
            metrics.get("ret_values", [])
        )

        # ── C. Drawdown curve ─────────────────────────────────────────────────
        dd_fig = build_intel_drawdown_chart(
            metrics.get("dd_dates", []),
            metrics.get("dd_values", [])
        )

        # ── D. Per-ticker volatility (horizontal bar) ─────────────────────────
        vol_fig = build_intel_volatility_chart(metrics.get("ticker_vols", {}))

        # ── E. Sector exposure (horizontal bar) ───────────────────────────────
        sec_exp = sector_exposure(port_data)
        sec_fig = build_intel_sector_chart(sec_exp)

        # ── F. Geographic exposure (horizontal bar) ───────────────────────────
        geo_data = geo_exposure(port_data)
        geo_fig = build_intel_geo_chart(geo_data)

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
