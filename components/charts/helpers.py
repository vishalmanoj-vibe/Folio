# components/charts/helpers.py
import logging

import pandas as pd
import plotly.graph_objects as go

from core.engine.utils import get_period_cutoff

logger = logging.getLogger(__name__)


def hex_to_rgba(hex_color: str, alpha: float) -> str:
    """
    Convert a hex color string (e.g. #378ADD) to an rgba string.

    Args:
        hex_color: The hex color string (with or without #).
        alpha: The opacity (0.0 to 1.0).
    """
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join([c * 2 for c in hex_color])
    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return f"rgba({r}, {g}, {b}, {alpha})"
    except Exception:
        return f"rgba(128, 128, 128, {alpha})"


# Plotly base margins
_LINE_MARGIN = dict(l=16, r=24, t=36, b=16)
_BAR_MARGIN = dict(l=110, r=60, t=16, b=16)


def create_empty_fig(
    msg: str = "Waiting for data…",
    height: int = 280,
    bar: bool = False,
    theme_tokens: dict | None = None,
) -> go.Figure:
    """
    Return a clean, annotated empty Plotly figure for loading/empty states.
    """
    if theme_tokens:
        base = theme_tokens["PLOTLY_BASE"].copy()
        t_sec = theme_tokens.get("T_SEC", base["font"]["color"])
    else:
        from config.constants import PLOTLY_BASE, T_SEC

        base = PLOTLY_BASE.copy()
        t_sec = T_SEC

    base["margin"] = _BAR_MARGIN if bar else _LINE_MARGIN
    base.pop("xaxis", None)
    base.pop("yaxis", None)

    f = go.Figure()
    f.update_layout(
        **base,
        height=height,
        annotations=[
            dict(
                text=msg,
                showarrow=False,
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                font=dict(color=t_sec, size=13),
            )
        ],
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
    )
    return f


def build_benchmark_traces(
    period: str,
    theme_tokens: dict | None = None,
    portfolio_start: pd.Timestamp | None = None,
    benchmarks: dict | None = None,
) -> list:
    """
    Return Plotly Scatter traces for benchmark indices normalised to
    % return from the start of the selected period window or portfolio start.
    The user-configured preferred benchmark is highlighted with a primary line style.
    """
    if benchmarks is None:
        try:
            from data.cache_manager import get_benchmarks_db

            benchmarks = get_benchmarks_db()
        except Exception as exc:
            logger.warning("Could not load benchmarks from DB: %s", exc)
            return []

    if not benchmarks:
        return []

    cutoff = get_period_cutoff(period)
    traces = []

    if theme_tokens is None:
        from config.constants import get_theme

        theme_tokens = get_theme("dark")

    b1_color = theme_tokens.get("BENCH_1")
    b2_color = theme_tokens.get("BENCH_2")
    t_sec = theme_tokens.get("T_SEC")

    # Load user's preferred benchmark to highlight it
    try:
        from data.settings_repository import get_setting

        preferred_benchmark = get_setting("portfolio_benchmark", "^AXJO") or "^AXJO"
        custom_benchmark = get_setting("custom_benchmark", "") or ""
        # Determine the label to highlight
        preset_labels = {
            "^AXJO": "ASX 200",
            "^GSPC": "S&P 500",
            "^NDX": "Nasdaq 100",
            "URTH": "MSCI World",
        }
        if preferred_benchmark == "__custom__" and custom_benchmark:
            preferred_label = custom_benchmark
        else:
            preferred_label = preset_labels.get(preferred_benchmark, preferred_benchmark)
    except Exception:
        preferred_label = "ASX 200"

    default_styles = {
        "S&P 500": {"color": b1_color, "dash": "dash"},
        "ASX 200": {"color": b2_color, "dash": "dot"},
    }

    for label, records in benchmarks.items():
        if not records:
            continue
        try:
            df = pd.DataFrame(records)
            df["Date"] = pd.to_datetime(df["Date"])
            df = df.set_index("Date").sort_index()

            start_dt = cutoff if cutoff is not None else portfolio_start
            if start_dt is not None:
                df = df[df.index >= start_dt]

            if df.empty or len(df) < 2:
                continue

            base = float(df["Close"].iloc[0])
            pct_s = ((df["Close"] - base) / base * 100).round(2)
            latest = float(pct_s.iloc[-1])
            sign = "+" if latest >= 0 else ""

            is_preferred = label == preferred_label

            if is_preferred:
                # Highlighted style for user's chosen benchmark
                style = default_styles.get(label, {"color": b1_color, "dash": "solid"})
                line_style = dict(color=style["color"], width=2.2, dash="solid")
                opacity = 1.0
            else:
                style = default_styles.get(label, {"color": t_sec, "dash": "dash"})
                line_style = dict(color=style["color"], width=1.2, dash=style["dash"])
                opacity = 0.55

            traces.append(
                go.Scatter(
                    x=pct_s.index.strftime("%Y-%m-%d").tolist(),
                    y=pct_s.tolist(),
                    name=f"{label} ({sign}{latest:.1f}%)" + (" ★" if is_preferred else ""),
                    mode="lines",
                    line=line_style,
                    opacity=opacity,
                    hovertemplate=f"%{{y:.2f}}%<extra>{label}</extra>",
                )
            )
        except Exception as exc:
            logger.warning("Benchmark trace failed for %s: %s", label, exc)

    return traces


def apply_standard_layout(
    fig: go.Figure,
    theme_tokens: dict,
    height: int = 280,
    show_legend: bool = False,
    chart_type: str = "line",
    title: str | None = None,
) -> go.Figure:
    """
    Applies the standardized layout to any go.Figure.

    Args:
        fig: The Plotly Figure to style.
        theme_tokens: The dictionary returned by get_theme().
        height: Height of the chart in pixels.
        show_legend: Whether to show the legend.
        chart_type: "line", "bar", or "other".
        title: Optional title string.
    """
    base = theme_tokens["PLOTLY_BASE"].copy()

    # Standard margins
    if chart_type == "bar":
        margin = dict(l=110, r=60, t=16, b=16)
    else:
        margin = base.get("margin", dict(l=50, r=20, t=30, b=30))

    layout_updates = {
        "height": height,
        "showlegend": show_legend,
        "margin": margin,
        "transition": dict(
            duration=400,
            easing="cubic-in-out",
            ordering="layout first",
        ),
        "uirevision": True,
    }

    if title:
        layout_updates["title"] = dict(
            text=title,
            font=dict(size=14, color=theme_tokens["T_PRI"]),
            x=0,
            y=0.98,
            xanchor="left",
            yanchor="top",
        )

    fig.update_layout(**base)
    fig.update_layout(**layout_updates)

    return fig
