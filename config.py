import os

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(SCRIPT_DIR, "data", "raw", "stock_portfolio_transactions.csv")

# ── Intervals ─────────────────────────────────────────────────────────────────
REFRESH_INTERVAL = 60_000   # milliseconds

# ── Dark theme tokens (defaults) ──────────────────────────────────────────────
BG      = "#111110"
SURFACE = "#1c1c1a"
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
    paper_bgcolor=BG,
    plot_bgcolor=SURFACE,
    font=dict(family="system-ui,sans-serif", color=T_PRI, size=13),
    margin=dict(l=16, r=16, t=40, b=16),
    legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0),
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
    else:  # dark (default)
        bg      = "#111110"
        surface = "#1c1c1a"
        border  = "rgba(255,255,255,0.08)"
        t_pri   = "#f0ede8"
        t_sec   = "#8a8880"

    return {
        "BG":      bg,
        "SURFACE": surface,
        "BORDER":  border,
        "T_PRI":   t_pri,
        "T_SEC":   t_sec,
        "PLOTLY_BASE": dict(
            paper_bgcolor=bg,
            plot_bgcolor=surface,
            font=dict(family="system-ui,sans-serif", color=t_pri, size=13),
            margin=dict(l=16, r=16, t=40, b=16),
            legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0),
        ),
    }

# ── ETF display names ─────────────────────────────────────────────────────────
NAMES = {
    "VHY":  "Vanguard High Yield ETF",
    "AINF": "Betashares Global Infra ETF",
    "ASIA": "Betashares Asia Tech ETF",
    "SEMI": "Betashares Global Semis ETF",
    "IOO":  "iShares Global 100 ETF",
    "IOZ":  "iShares Core ASX 200 ETF",
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
    "allocation": (
        "Portfolio allocation",
        "Shows what % of your total portfolio value each holding represents today. "
        "Larger slices = bigger positions. Use this to check if you are "
        "over-concentrated in any single ETF."
    ),
    "pnl-bar": (
        "Unrealised P&L — all time",
        "The dollar (or %) gain or loss on each holding since you first bought it, "
        "based on your weighted average purchase price. Green = profitable, "
        "Red = at a loss. Unrealised — only becomes real when you sell."
    ),
    "day-pnl": (
        "Today's P&L",
        "How much each holding gained or lost today vs yesterday's closing price. "
        "Resets every trading day. Green = up today, red = down today."
    ),
    "dividend": (
        "Annual dividend income",
        "Estimated annual dividend income from each holding based on dividends paid "
        "over the last 12 months, scaled to your share count. "
        "Yield % = annual dividends divided by current market value."
    ),
    "correlation": (
        "Return correlation matrix",
        "How similarly two holdings move together, from -1 to +1. Near +1 (green) "
        "= move together, less diversification. Near 0 = move independently. "
        "Near -1 (red) = move oppositely, good diversification."
    ),
}