# config/constants.py
"""
Constants for Folio.

Colors, theme definitions, ETF names, and chart information.
"""

# ── Dark theme tokens (defaults) ──────────────────────────────────────────────
BG      = "#0a0a0a"
SURFACE = "#111a1a"
BORDER  = "rgba(255,255,255,0.08)"
T_PRI   = "#f0ede8"
T_SEC   = "#8a8880"
GREEN   = "#1D9E75"
RED     = "#E24B4A"

COLORS = [
    "#378ADD", "#1D9E75", "#EF9F27", "#D85A30",
    "#7F77DD", "#D4537E", "#639922", "#5DCAA5",
    "#FAC775", "#85B7EB", "#F0997B", "#AFA9EC",
]

PLOTLY_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, -apple-system, BlinkMacSystemFont, sans-serif", color=T_PRI, size=13),
    margin=dict(l=16, r=16, t=40, b=16),
    legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0),
    uirevision=True,
)

# ── Theme-aware style resolver ────────────────────────────────────────────────
def get_theme(theme: str) -> dict:
    """
    Return a dict of colour tokens and a PLOTLY_BASE for the given theme.
    Usage:  t = get_theme(theme);  t["BG"], t["PLOTLY_BASE"], ...
    """
    if theme == "light":
        bg      = "#ffffff"
        surface = "#f4f4f2"
        border  = "rgba(0,0,0,0.09)"
        t_pri   = "#1a1a1a"
        t_sec   = "#6b6b67"
        # Light mode specific accents
        bench_1 = "#4A90E2" 
        bench_2 = "#D0021B"
        danger  = "#E24B4A"
        warning = "#EF9F27"
        info    = "#378ADD"
    else:  # dark (default)
        bg      = "#0a0a0a"
        surface = "#111a1a"
        border  = "rgba(255,255,255,0.08)"
        t_pri   = "#f0ede8"
        t_sec   = "#8a8880"
        # Dark mode specific accents
        bench_1 = "#6B8FCC"
        bench_2 = "#CC8F6B"
        danger  = "#E24B4A"
        warning = "#EF9F27"
        info    = "#378ADD"

    return {
        "BG":      bg,
        "SURFACE": surface,
        "BORDER":  border,
        "T_PRI":   t_pri,
        "T_SEC":   t_sec,
        "DANGER":  danger,
        "WARNING": warning,
        "GREEN":   "#1D9E75",
        "RED":     "#E24B4A",
        "CYAN":    "#009e80" if theme == "light" else "#00c9a7",
        "INFO":    info,
        "BENCH_1": bench_1,
        "BENCH_2": bench_2,
        "PLOTLY_BASE": dict(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter, -apple-system, BlinkMacSystemFont, sans-serif", color=t_pri, size=12),
            margin=dict(l=50, r=20, t=30, b=30),
            legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0, font=dict(color=t_sec, size=11)),
            xaxis=dict(
                showgrid=False,
                zeroline=False,
                tickfont=dict(size=10, color=t_sec),
                automargin=True,
                showline=False,
            ),
            yaxis=dict(
                gridcolor=border,
                zeroline=True,
                zerolinecolor=border,
                zerolinewidth=1,
                tickfont=dict(size=10, color=t_sec),
                automargin=True,
            ),
            hoverlabel=dict(
                bgcolor=surface,
                bordercolor=border,
                font=dict(color=t_pri, family="Inter", size=12),
                align="left",
            ),
            hovermode="x unified",
            uirevision=True,
        ),
    }

# ── ETF display names ─────────────────────────────────────────────────────────
# Full names are now fetched automatically from yfinance for any ticker.
# This dict is used only as a fast fallback or for very new/niche ETFs.
NAMES = {
    "VHY":  "Vanguard High Yield ETF",
    "AINF": "Betashares Global Infra ETF",
    "ASIA": "Betashares Asia Tech ETF",
    "SEMI": "Betashares Global Semis ETF",
    "IOO":  "iShares Global 100 ETF",
    "IOZ":  "iShares Core ASX 200 ETF",
    "XMET": "BetaShares Energy Transition Metals ETF",
    "QUAL": "VanEck MSCI World Quality ETF",
    "EMKT": "VanEck MSCI Emerging Markets ETF",
}

# ── Chart tooltip copy ────────────────────────────────────────────────────────
CHART_INFO = {
    "pnl-history": (
        "P&L from purchase date",
        "Shows your profit or loss since you bought each holding. The line starts "
        "at $0 on your purchase date and moves up (profit) or down (loss) as the "
        "price changes. Toggle between Portfolio (combined) or individual stocks. "
        "Switch between $ and % using the P&L view dropdown."
    ),
    "price-chart": (
        "Normalised price history",
        "All holdings are rescaled to start at 100 so you can compare performance "
        "side by side regardless of actual price. A line at 120 means that holding "
        "is up 20% over the selected period. The dotted line at 100 is the baseline."
    ),
    "portfolio-performance": (
        "Portfolio P&L Impact",
        "Each rectangle represents a holding. The size depends on the absolute Profit/Loss "
        "magnitude (Impact), and the color shows the direction: Green for gains, Red for losses. "
        "Largest boxes represent your biggest winners or losers."
    ),
    "dividend": (
        "Annual Dividend Detail",
        "A high-density breakdown of your annual dividend income for every holding. "
        "Lollipops are sorted with the highest income-producers at the top."
    ),
    "correlation": (
        "Return correlation matrix",
        "How similarly two holdings move together, from -1 to +1. Near +1 (red) "
        "= move together, higher concentration risk. Near 0 (yellow) = move independently. "
        "Near -1 (green) = move oppositely, high diversification."
    ),
}
