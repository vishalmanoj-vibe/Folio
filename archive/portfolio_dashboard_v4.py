"""
Financial Portfolio Dashboard — Live P&L
==========================================
Run:   python portfolio_dashboard.py
Open:  http://127.0.0.1:8050

Transactions are read from and saved to stock_portfolio_transactions.csv
in the SAME folder as this script file.

CSV format (it will tell you if something is wrong on startup):
  type,ticker,shares,price,date
  buy,VHY,7,81.87,2026-03-30
  buy,AINF,30,16.88,2026-03-06

Accepted date formats: YYYY-MM-DD or DD.MM.YYYY
Ticker should NOT include .AX — the script adds it automatically.
"""

import os
import dash
from dash import dcc, html, Input, Output, State, ALL
import plotly.graph_objects as go
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import pytz
import warnings
warnings.filterwarnings("ignore")

# ── Paths — always relative to this script, never the shell cwd ───────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH   = os.path.join(SCRIPT_DIR, "stock_portfolio_transactions.csv")

# ── App ───────────────────────────────────────────────────────────────────────
app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "Portfolio — Live"

# ── Theme ─────────────────────────────────────────────────────────────────────
BG      = "#ffffff"
SURFACE = "#f8f8f6"
BORDER  = "rgba(0,0,0,0.09)"
T_PRI   = "#1a1a1a"
T_SEC   = "#6b6b67"
GREEN   = "#1D9E75"
RED     = "#E24B4A"

COLORS = [
    "#378ADD","#1D9E75","#EF9F27","#D85A30",
    "#7F77DD","#D4537E","#639922","#5DCAA5",
    "#FAC775","#85B7EB","#F0997B","#AFA9EC",
]

PLOTLY_BASE = dict(
    paper_bgcolor=BG, plot_bgcolor=SURFACE,
    font=dict(family="system-ui,sans-serif", color=T_PRI, size=13),
    margin=dict(l=16, r=16, t=40, b=16),
    legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0),
)

# ── Chart tooltips ────────────────────────────────────────────────────────────
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

NAMES = {
    "VHY":  "Vanguard High Yield ETF",
    "AINF": "Betashares Global Infra ETF",
    "ASIA": "Betashares Asia Tech ETF",
    "SEMI": "Betashares Global Semis ETF",
    "IOO":  "iShares Global 100 ETF",
    "IOZ":  "iShares Core ASX 200 ETF",
}

# ── CSV helpers ───────────────────────────────────────────────────────────────
def load_csv() -> list[dict]:
    """
    Load transactions from CSV. Returns list of dicts with keys:
    type, ticker, shares, price, date (YYYY-MM-DD).
    Raises a clear RuntimeError if the file is missing or malformed
    so the error prints to terminal instead of silently giving an empty list.
    """
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(
            f"\n\nCSV file not found at:\n  {CSV_PATH}\n\n"
            "Please create it with columns: type,ticker,shares,price,date\n"
            "Example row:  buy,VHY,7,81.87,2026-03-30\n"
        )

    df = pd.read_csv(CSV_PATH)

    # Normalise column names — handle both Title Case and lowercase
    df.columns = [c.strip().lower() for c in df.columns]

    missing = [c for c in ["ticker","shares","price","date"] if c not in df.columns]
    if missing:
        raise ValueError(
            f"\n\nCSV is missing required columns: {missing}\n"
            f"Found columns: {list(df.columns)}\n"
            "Required: type, ticker, shares, price, date\n"
        )

    # 'type' column optional — default to 'buy' if absent
    if "type" not in df.columns:
        df["type"] = "buy"

    # Normalise values
    df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()
    df["type"]   = df["type"].astype(str).str.strip().str.lower()
    df["shares"] = pd.to_numeric(df["shares"], errors="coerce")
    df["price"]  = pd.to_numeric(df["price"],  errors="coerce")

    # Parse dates — accept YYYY-MM-DD and DD.MM.YYYY
    df["date"] = pd.to_datetime(df["date"], dayfirst=False, errors="coerce")
    mask_failed = df["date"].isna()
    if mask_failed.any():
        # Try again with dayfirst for DD.MM.YYYY format
        retry = pd.to_datetime(
            pd.read_csv(CSV_PATH).iloc[:, df.columns.tolist().index("date")],
            dayfirst=True, errors="coerce"
        )
        df.loc[mask_failed, "date"] = retry[mask_failed]

    still_bad = df["date"].isna().any() or df["shares"].isna().any() or df["price"].isna().any()
    if still_bad:
        bad_rows = df[df[["date","shares","price"]].isna().any(axis=1)]
        raise ValueError(
            f"\n\nCSV has rows with invalid date, shares, or price:\n"
            f"{bad_rows.to_string()}\n\n"
            "Date format should be YYYY-MM-DD (e.g. 2026-03-30)\n"
        )

    df["date"] = df["date"].dt.strftime("%Y-%m-%d")

    records = df[["type","ticker","shares","price","date"]].to_dict("records")
    print(f"  Loaded {len(records)} transactions from {CSV_PATH}")
    return records


def save_csv(history: list[dict]):
    """Write full transaction list back to CSV."""
    df = pd.DataFrame(history)[["type","ticker","shares","price","date"]]
    df.columns = ["Type","Ticker","Shares","Price","Date"]
    df.to_csv(CSV_PATH, index=False)
    print(f"  Saved {len(history)} transactions to {CSV_PATH}")


# ── Load on startup — fail loudly so you see the error in terminal ────────────
try:
    INITIAL_HISTORY = load_csv()
except Exception as e:
    print(f"\nERROR loading CSV:\n{e}")
    # Set a placeholder so the app at least starts; dashboard will show empty state
    INITIAL_HISTORY = []

# ── Build holdings from transactions ──────────────────────────────────────────
def build_holdings(history: list[dict]) -> list[dict]:
    """Aggregate buy/sell transactions → one row per ticker with weighted avg cost."""
    if not history:
        return []
    df = pd.DataFrame(history)
    results = []
    for ticker, grp in df.groupby("ticker"):
        buys  = grp[grp["type"] == "buy"].copy()
        sells = grp[grp["type"] == "sell"].copy() if "sell" in grp["type"].values else pd.DataFrame()
        if buys.empty:
            continue
        total_bought = float(buys["shares"].sum())
        total_cost   = float((buys["shares"] * buys["price"]).sum())
        total_sold   = float(sells["shares"].sum()) if not sells.empty else 0.0
        net_shares   = total_bought - total_sold
        if net_shares <= 0:
            continue
        avg_cost       = round(total_cost / total_bought, 4)
        remaining_cost = round(avg_cost * net_shares, 2)
        buy_tranches   = [
            {"ticker": ticker, "shares": float(r["shares"]), "price": float(r["price"]),
             "date": str(r["date"]), "buy_price": float(r["price"]), "buy_date": str(r["date"])}
            for _, r in buys.iterrows()
        ]
        results.append({
            "ticker":         ticker,
            "ticker_yf":      ticker + ".AX",
            "name":           NAMES.get(ticker, ticker),
            "market":         "ETF/ASX",
            "total_shares":   net_shares,
            "total_cost":     remaining_cost,
            "avg_cost":       avg_cost,
            "first_purchase": buys["date"].min(),
            "buy_tranches":   buy_tranches,
        })
    return results


# ── Market status ─────────────────────────────────────────────────────────────
def is_market_open() -> bool:
    now_utc = datetime.now(pytz.utc)
    now_aet = now_utc.astimezone(pytz.timezone("Australia/Sydney"))
    return now_utc.weekday() < 5 and 10 <= now_aet.hour < 16


def market_badge():
    open_ = is_market_open()
    return html.Span(
        "ASX open" if open_ else "ASX closed",
        style={
            "fontSize":"12px","padding":"3px 10px","borderRadius":"20px",
            "background":"#E1F5EE" if open_ else SURFACE,
            "color": GREEN if open_ else T_SEC, "fontWeight":"500",
            "border":f"0.5px solid {'#1D9E75' if open_ else BORDER}",
        }
    )


# ── Data fetch ────────────────────────────────────────────────────────────────
def fetch_live(holdings: list[dict], hist_period: str = "3mo") -> dict:
    if not holdings:
        return {}
    enriched, histories = [], {}

    for h in holdings:
        try:
            tk   = yf.Ticker(h["ticker_yf"])
            info = tk.info
            fi   = tk.fast_info

            last_price = float(fi.get("last_price") or info.get("regularMarketPrice") or h["avg_cost"])
            prev_close = float(fi.get("previous_close") or info.get("previousClose") or last_price)
            day_high   = float(fi.get("day_high") or info.get("dayHigh") or last_price)
            day_low    = float(fi.get("day_low")  or info.get("dayLow")  or last_price)

            day_chg     = round(last_price - prev_close, 4)
            day_chg_pct = round((day_chg / prev_close * 100) if prev_close else 0, 2)
            mkt_value   = round(h["total_shares"] * last_price, 2)
            pnl         = round(mkt_value - h["total_cost"], 2)
            pnl_pct     = round((pnl / h["total_cost"] * 100) if h["total_cost"] else 0, 2)
            day_pnl     = round(day_chg * h["total_shares"], 2)

            hist_full      = tk.history(period="max")
            hist_period_df = tk.history(period=hist_period)

            div_s      = hist_full["Dividends"] if "Dividends" in hist_full.columns else pd.Series(dtype=float)
            cutoff     = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
            annual_div = round(float(div_s[div_s.index >= cutoff].sum()) * h["total_shares"], 2)
            total_div  = round(float(div_s.sum()) * h["total_shares"], 2)
            div_yield  = round((annual_div / mkt_value * 100) if mkt_value else 0, 2)

            if not hist_period_df.empty:
                df_p = hist_period_df["Close"].reset_index()
                df_p.columns = ["Date","Close"]
                df_p["Date"] = pd.to_datetime(df_p["Date"]).dt.tz_localize(None)
                histories[h["ticker"]] = df_p.to_dict("records")

            tranche_data = []
            if not hist_full.empty:
                close_all = hist_full["Close"].copy()
                close_all.index = pd.to_datetime(close_all.index).tz_localize(None)
                for tr in h.get("buy_tranches", []):
                    buy_date = pd.to_datetime(tr["date"])
                    mask = close_all.index >= buy_date
                    if not mask.any():
                        continue
                    sub   = close_all[mask].copy()
                    pnl_s = (sub - tr["price"]) * tr["shares"]
                    pct_s = (sub - tr["price"]) / tr["price"] * 100
                    tranche_data.append({
                        "dates":     [d.strftime("%Y-%m-%d") for d in sub.index],
                        "pnl":       [round(v,2) for v in pnl_s.tolist()],
                        "pct":       [round(v,2) for v in pct_s.tolist()],
                        "shares":    float(tr["shares"]),
                        "buy_price": float(tr["price"]),
                        "buy_date":  tr["date"],
                    })

            enriched.append({
                **h,
                "last_price":  round(last_price,3), "prev_close": round(prev_close,3),
                "day_high":    round(day_high,3),   "day_low":    round(day_low,3),
                "day_chg":     day_chg,    "day_chg_pct": day_chg_pct,
                "day_pnl":     day_pnl,   "mkt_value":   mkt_value,
                "pnl":         pnl,        "pnl_pct":     pnl_pct,
                "total_div":   total_div,  "annual_div":  annual_div,
                "div_yield":   div_yield,  "tranches":    tranche_data,
            })
        except Exception:
            enriched.append({
                **h,
                "last_price": h["avg_cost"], "prev_close": h["avg_cost"],
                "day_high": h["avg_cost"],   "day_low":    h["avg_cost"],
                "day_chg": 0, "day_chg_pct": 0, "day_pnl": 0,
                "mkt_value": round(h["total_shares"]*h["avg_cost"],2),
                "pnl": 0, "pnl_pct": 0,
                "total_div": 0, "annual_div": 0, "div_yield": 0, "tranches": [],
            })

    return {"holdings": enriched, "histories": histories,
            "fetched_at": datetime.now().strftime("%H:%M:%S")}


# ── UI helpers ────────────────────────────────────────────────────────────────
def stat_card(label, value, sub=None, color=T_PRI, sub_color=T_SEC):
    return html.Div([
        html.P(label, style={"fontSize":"12px","color":T_SEC,"margin":"0 0 4px"}),
        html.P(value, style={"fontSize":"20px","fontWeight":"500","margin":"0","color":color}),
        html.P(sub,   style={"fontSize":"11px","color":sub_color,"margin":"3px 0 0"}) if sub else None,
    ], style={"background":SURFACE,"borderRadius":"10px",
              "padding":"14px 18px","flex":"1","minWidth":"130px"})


def chart_title(label: str, info_key: str = ""):
    """Render chart title with a hoverable (i) badge."""
    # CHART_INFO values are (title, description) tuples — get description safely
    tip = CHART_INFO.get(info_key, ("",""))[1] if info_key else ""
    children = [html.Span(label, style={"fontSize":"13px","fontWeight":"500","color":T_PRI})]
    if tip:
        children.append(html.Span("i", title=tip, style={
            "display":"inline-flex","alignItems":"center","justifyContent":"center",
            "width":"16px","height":"16px","borderRadius":"50%",
            "background":SURFACE,"border":f"1px solid {BORDER}",
            "fontSize":"10px","color":T_SEC,"cursor":"help",
            "marginLeft":"6px","fontWeight":"500",
        }))
    return html.Div(children,
                    style={"display":"inline-flex","alignItems":"center","marginBottom":"6px"})


def section(title_node, children):
    return html.Div([title_node, children],
                    style={"padding":"16px 24px",
                           "borderBottom":f"0.5px solid {BORDER}"})


def txn_table(history: list[dict]):
    if not history:
        return html.P("No transactions yet.", style={"color":T_SEC,"fontSize":"13px"})
    th_s = {"fontSize":"11px","color":T_SEC,"fontWeight":"500","padding":"6px 10px",
             "borderBottom":f"1px solid {BORDER}","backgroundColor":SURFACE,
             "textAlign":"left","whiteSpace":"nowrap"}
    td_s = {"fontSize":"12px","padding":"6px 10px",
             "borderBottom":f"0.5px solid {BORDER}","whiteSpace":"nowrap"}
    rows = [
        html.Tr([
            html.Td(t["date"],  style=td_s),
            html.Td(t["ticker"],style={**td_s,"fontWeight":"500"}),
            html.Td(t["type"].upper(),
                    style={**td_s,"color": GREEN if t["type"]=="buy" else RED,
                           "fontWeight":"500"}),
            html.Td(str(t["shares"]), style=td_s),
            html.Td(f"${float(t['price']):,.4f}", style=td_s),
            html.Td(f"${float(t['shares'])*float(t['price']):,.2f}", style=td_s),
        ])
        for t in reversed(history)
    ]
    return html.Table([
        html.Thead(html.Tr([html.Th(c,style=th_s)
                            for c in ["Date","Ticker","Type","Shares","Price","Total"]])),
        html.Tbody(rows),
    ], style={"width":"100%","borderCollapse":"collapse"})


# ── Layout ────────────────────────────────────────────────────────────────────
app.layout = html.Div([

    dcc.Store(id="portfolio-store"),
    dcc.Store(id="txn-store", data=INITIAL_HISTORY),
    dcc.Interval(id="live-interval", interval=60_000, n_intervals=0),

    # Header
    html.Div([
        html.Div([
            html.H1("Portfolio — Live P&L",
                    style={"margin":"0","fontSize":"20px","fontWeight":"500"}),
            html.P("Auto-refreshes every 60 s · Yahoo Finance · ASX ETFs",
                   style={"margin":"3px 0 0","fontSize":"12px","color":T_SEC}),
        ]),
        html.Div([
            html.Div(id="market-status"),
            html.Span(id="last-updated", style={"fontSize":"12px","color":T_SEC}),
        ], style={"display":"flex","flexDirection":"column",
                  "alignItems":"flex-end","gap":"6px"}),
    ], style={"display":"flex","justifyContent":"space-between",
              "alignItems":"flex-start","padding":"18px 24px 12px",
              "borderBottom":f"0.5px solid {BORDER}"}),

    # Controls
    html.Div([
        html.Div([
            html.P("Chart period",style={"fontSize":"12px","color":T_SEC,"margin":"0 0 4px"}),
            dcc.Dropdown(id="period-picker",
                options=[{"label":"Since purchase","value":"max"},
                         {"label":"1 month","value":"1mo"},
                         {"label":"3 months","value":"3mo"},
                         {"label":"6 months","value":"6mo"},
                         {"label":"1 year","value":"1y"},
                         {"label":"2 years","value":"2y"}],
                value="3mo", clearable=False,
                style={"width":"155px","fontSize":"13px"}),
        ]),
        html.Div([
            html.P("P&L view",style={"fontSize":"12px","color":T_SEC,"margin":"0 0 4px"}),
            dcc.Dropdown(id="pnl-mode",
                options=[{"label":"Dollar ($)","value":"dollar"},
                         {"label":"Percentage (%)","value":"pct"}],
                value="dollar", clearable=False,
                style={"width":"155px","fontSize":"13px"}),
        ]),
        html.Button("Refresh now", id="refresh-btn", n_clicks=0,
                    style={"fontWeight":"500","alignSelf":"flex-end"}),
    ], style={"display":"flex","gap":"16px","alignItems":"flex-end",
              "padding":"14px 24px","borderBottom":f"0.5px solid {BORDER}",
              "flexWrap":"wrap"}),

    # Stat cards
    html.Div(id="stat-cards",
             style={"display":"flex","gap":"10px","padding":"16px 24px",
                    "flexWrap":"wrap","borderBottom":f"0.5px solid {BORDER}"}),

    # ── Transaction panel ─────────────────────────────────────────────────────
    html.Div([
        html.P("Add transaction",
               style={"fontSize":"13px","fontWeight":"500","margin":"0 0 4px"}),
        html.P(f"Saved to: {CSV_PATH}",
               style={"fontSize":"11px","color":T_SEC,"margin":"0 0 12px",
                      "fontFamily":"monospace"}),
        html.Div([
            html.Div([
                html.P("Type",style={"fontSize":"11px","color":T_SEC,"margin":"0 0 4px"}),
                dcc.Dropdown(id="txn-type",
                    options=[{"label":"Buy","value":"buy"},
                             {"label":"Sell","value":"sell"}],
                    value="buy", clearable=False,
                    style={"width":"100px","fontSize":"13px"}),
            ]),
            html.Div([
                html.P("Ticker",style={"fontSize":"11px","color":T_SEC,"margin":"0 0 4px"}),
                dcc.Input(id="txn-ticker", type="text", placeholder="e.g. VHY",
                          style={"width":"90px","fontSize":"13px","padding":"6px 8px",
                                 "border":f"0.5px solid {BORDER}","borderRadius":"6px"}),
            ]),
            html.Div([
                html.P("Shares",style={"fontSize":"11px","color":T_SEC,"margin":"0 0 4px"}),
                dcc.Input(id="txn-shares", type="number", placeholder="0",
                          style={"width":"90px","fontSize":"13px","padding":"6px 8px",
                                 "border":f"0.5px solid {BORDER}","borderRadius":"6px"}),
            ]),
            html.Div([
                html.P("Price ($)",style={"fontSize":"11px","color":T_SEC,"margin":"0 0 4px"}),
                dcc.Input(id="txn-price", type="number", placeholder="0.00",
                          style={"width":"100px","fontSize":"13px","padding":"6px 8px",
                                 "border":f"0.5px solid {BORDER}","borderRadius":"6px"}),
            ]),
            html.Div([
                html.P("Date (YYYY-MM-DD)",
                       style={"fontSize":"11px","color":T_SEC,"margin":"0 0 4px"}),
                dcc.Input(id="txn-date", type="text",
                          value=datetime.now().strftime("%Y-%m-%d"),
                          style={"width":"130px","fontSize":"13px","padding":"6px 8px",
                                 "border":f"0.5px solid {BORDER}","borderRadius":"6px"}),
            ]),
            html.Div([
                html.P("\u00a0",style={"fontSize":"11px","margin":"0 0 4px"}),
                html.Button("Add transaction", id="txn-submit", n_clicks=0,
                            style={"fontWeight":"500","fontSize":"13px","padding":"7px 16px"}),
            ]),
        ], style={"display":"flex","gap":"12px","flexWrap":"wrap","alignItems":"flex-end"}),
        html.P(id="txn-msg",
               style={"fontSize":"12px","marginTop":"8px","minHeight":"18px","color":GREEN}),
        html.Details([
            html.Summary("Transaction history",
                         style={"fontSize":"12px","color":T_SEC,
                                "cursor":"pointer","marginTop":"8px"}),
            html.Div(id="txn-log", style={"marginTop":"10px","overflowX":"auto"}),
        ]),
    ], style={"padding":"16px 24px","background":SURFACE,
              "borderBottom":f"0.5px solid {BORDER}"}),

    # Live positions
    section(chart_title("Live positions"),
            html.Div(id="live-table")),

    # P&L history
    section(
        chart_title("P&L from purchase date","pnl-history"),
        html.Div([
            html.Div([
                html.P("View:", style={"fontSize":"12px","color":T_SEC,
                                       "margin":"0 8px 0 0","alignSelf":"center"}),
                html.Div(id="ticker-toggle-btns",
                         style={"display":"flex","gap":"6px","flexWrap":"wrap"}),
            ], style={"display":"flex","alignItems":"center",
                      "marginBottom":"12px","flexWrap":"wrap"}),
            dcc.Graph(id="pnl-history-chart", config={"displayModeBar":False}),
        ]),
    ),

    # Charts grid
    html.Div([
        html.Div([
            html.Div([chart_title("Price history — normalised to 100","price-chart"),
                      dcc.Graph(id="price-chart",config={"displayModeBar":False})],
                     style={"flex":"2","minWidth":"280px"}),
            html.Div([chart_title("Portfolio allocation","allocation"),
                      dcc.Graph(id="allocation-chart",config={"displayModeBar":False})],
                     style={"flex":"1","minWidth":"220px"}),
        ], style={"display":"flex","gap":"14px","flexWrap":"wrap","marginBottom":"14px"}),
        html.Div([
            html.Div([chart_title("Unrealised P&L — all time","pnl-bar"),
                      dcc.Graph(id="pnl-bar-chart",config={"displayModeBar":False})],
                     style={"flex":"1","minWidth":"260px"}),
            html.Div([chart_title("Today's P&L","day-pnl"),
                      dcc.Graph(id="day-pnl-chart",config={"displayModeBar":False})],
                     style={"flex":"1","minWidth":"260px"}),
        ], style={"display":"flex","gap":"14px","flexWrap":"wrap","marginBottom":"14px"}),
        html.Div([
            html.Div([chart_title("Annual dividend income","dividend"),
                      dcc.Graph(id="dividend-chart",config={"displayModeBar":False})],
                     style={"flex":"1","minWidth":"260px"}),
            html.Div([chart_title("Return correlation matrix","correlation"),
                      dcc.Graph(id="corr-chart",config={"displayModeBar":False})],
                     style={"flex":"1","minWidth":"260px"}),
        ], style={"display":"flex","gap":"14px","flexWrap":"wrap"}),
    ], style={"padding":"16px 24px"}),

], style={"fontFamily":"system-ui,-apple-system,sans-serif",
          "color":T_PRI,"maxWidth":"1300px","margin":"0 auto","backgroundColor":BG})


# ── Callbacks ─────────────────────────────────────────────────────────────────

@app.callback(
    Output("txn-store","data"),
    Output("txn-msg","children"),
    Output("txn-msg","style"),
    Input("txn-submit","n_clicks"),
    State("txn-type","value"),
    State("txn-ticker","value"),
    State("txn-shares","value"),
    State("txn-price","value"),
    State("txn-date","value"),
    State("txn-store","data"),
    prevent_initial_call=True,
)
def add_transaction(_, txn_type, ticker, shares, price, date, history):
    base = {"fontSize":"12px","marginTop":"8px","minHeight":"18px"}
    # Validate inputs
    if not ticker or shares is None or price is None:
        return history, "Please fill in ticker, shares and price.", {**base,"color":RED}
    ticker = ticker.strip().upper()
    try:
        shares = float(shares)
        price  = float(price)
    except (TypeError, ValueError):
        return history, "Shares and price must be numbers.", {**base,"color":RED}
    if shares <= 0 or price <= 0:
        return history, "Shares and price must be positive.", {**base,"color":RED}
    # Validate date
    try:
        datetime.strptime(date.strip(), "%Y-%m-%d")
    except (ValueError, AttributeError):
        return history, "Date must be YYYY-MM-DD (e.g. 2026-03-30).", {**base,"color":RED}

    # Sell validation
    if txn_type == "sell":
        df = pd.DataFrame(history)
        if df.empty or ticker not in df["ticker"].values:
            return history, f"No holdings found for {ticker}.", {**base,"color":RED}
        grp  = df[df["ticker"]==ticker]
        held = (grp[grp["type"]=="buy"]["shares"].sum()
                - grp[grp["type"]=="sell"]["shares"].sum()
                if "sell" in grp["type"].values
                else grp[grp["type"]=="buy"]["shares"].sum())
        if shares > held:
            return history, f"Cannot sell {shares} — only holding {held}.", {**base,"color":RED}

    new_txn  = {"type":txn_type,"ticker":ticker,"shares":shares,
                "price":price,"date":date.strip()}
    updated  = history + [new_txn]

    # Save to CSV
    try:
        save_csv(updated)
        msg = f"{txn_type.capitalize()} {shares} {ticker} @ ${price:.4f} saved to CSV."
    except Exception as e:
        msg = f"Added to dashboard but CSV save failed: {e}"

    color = GREEN if txn_type == "buy" else RED
    return updated, msg, {**base,"color":color}


@app.callback(
    Output("txn-log","children"),
    Input("txn-store","data"),
)
def update_txn_log(history):
    return txn_table(history)


@app.callback(
    Output("portfolio-store","data"),
    Output("last-updated","children"),
    Output("market-status","children"),
    Input("live-interval","n_intervals"),
    Input("refresh-btn","n_clicks"),
    Input("period-picker","value"),
    Input("txn-store","data"),
)
def refresh(_, __, period, history):
    holdings = build_holdings(history or [])
    if not holdings:
        return {}, "No holdings — check your CSV.", market_badge()
    data = fetch_live(holdings, period)
    return data, f"Updated {data.get('fetched_at','')}", market_badge()


@app.callback(
    Output("stat-cards","children"),
    Input("portfolio-store","data"),
)
def update_stats(data):
    if not data or "holdings" not in data:
        return []
    h = data["holdings"]
    total_val  = sum(x["mkt_value"]  for x in h)
    total_cost = sum(x["total_cost"] for x in h)
    total_pnl  = total_val - total_cost
    pnl_pct    = (total_pnl / total_cost * 100) if total_cost else 0
    total_day  = sum(x["day_pnl"]    for x in h)
    annual_div = sum(x["annual_div"] for x in h)
    port_yield = (annual_div / total_val * 100) if total_val else 0
    ps = "+" if total_pnl >= 0 else ""
    ds = "+" if total_day >= 0 else ""
    pc = GREEN if total_pnl >= 0 else RED
    dc = GREEN if total_day >= 0 else RED
    return [
        stat_card("Total value",      f"${total_val:,.2f}"),
        stat_card("Cost basis",       f"${total_cost:,.2f}"),
        stat_card("Unrealised P&L",   f"{ps}${total_pnl:,.2f}",
                  f"{ps}{pnl_pct:.2f}% all time", pc, pc),
        stat_card("Today's P&L",      f"{ds}${total_day:,.2f}",
                  "across all positions", dc, dc),
        stat_card("Annual dividends", f"${annual_div:,.2f}",
                  f"{port_yield:.2f}% yield",
                  GREEN if port_yield > 0 else T_PRI, T_SEC),
        stat_card("Holdings", str(len(h))),
    ]


@app.callback(
    Output("live-table","children"),
    Input("portfolio-store","data"),
)
def update_live_table(data):
    if not data or "holdings" not in data:
        return html.P("Loading...", style={"color":T_SEC,"fontSize":"13px"})
    h = data["holdings"]
    th = {"fontSize":"11px","color":T_SEC,"fontWeight":"500","padding":"7px 12px",
          "textAlign":"left","borderBottom":f"1px solid {BORDER}",
          "backgroundColor":SURFACE,"whiteSpace":"nowrap"}
    td = {"fontSize":"13px","padding":"8px 12px",
          "borderBottom":f"0.5px solid {BORDER}","whiteSpace":"nowrap"}

    def pnl_td(val, pct):
        c = GREEN if val >= 0 else RED
        s = "+" if val >= 0 else ""
        return html.Td([
            html.Div(f"{s}${val:,.2f}", style={"color":c,"fontWeight":"500","fontSize":"13px"}),
            html.Div(f"{s}{pct:.2f}%",  style={"color":c,"fontSize":"11px"}),
        ], style=td)

    rows = []
    for x in sorted(h, key=lambda v: v["mkt_value"], reverse=True):
        dc = GREEN if x["day_chg"] >= 0 else RED
        ds = "+" if x["day_chg"] >= 0 else ""
        rows.append(html.Tr([
            html.Td(html.Span(x["ticker"],style={"fontWeight":"500"}),style=td),
            html.Td(x.get("name",""),style={**td,"color":T_SEC,"fontSize":"12px"}),
            html.Td(str(x["total_shares"]),style=td),
            html.Td(f"${x['avg_cost']:,.4f}",style=td),
            html.Td(f"${x['last_price']:,.3f}",style=td),
            html.Td([
                html.Div(f"{ds}${x['day_chg']:,.3f}",
                         style={"color":dc,"fontWeight":"500","fontSize":"13px"}),
                html.Div(f"{ds}{x['day_chg_pct']:.2f}%",
                         style={"color":dc,"fontSize":"11px"}),
            ],style=td),
            html.Td(f"${x['day_high']:,.3f} / ${x['day_low']:,.3f}",
                    style={**td,"fontSize":"12px","color":T_SEC}),
            html.Td(f"${x['mkt_value']:,.2f}",style=td),
            html.Td(f"${x['total_cost']:,.2f}",style=td),
            pnl_td(x["pnl"],x["pnl_pct"]),
            pnl_td(x["day_pnl"],x["day_chg_pct"]),
            html.Td(f"{x['div_yield']:.2f}%",style=td),
        ]))

    return html.Div([
        html.Table([
            html.Thead(html.Tr([html.Th(c,style=th) for c in [
                "Ticker","Name","Shares","Avg cost","Last price","Day change",
                "High / Low","Market value","Cost basis",
                "Unrealised P&L","Today's P&L","Div yield",
            ]])),
            html.Tbody(rows),
        ],style={"width":"100%","borderCollapse":"collapse",
                 "overflowX":"auto","display":"block"}),
    ],style={"overflowX":"auto","borderRadius":"8px","border":f"0.5px solid {BORDER}"})


@app.callback(
    Output("ticker-toggle-btns","children"),
    Input("portfolio-store","data"),
)
def build_toggle_btns(data):
    if not data or "holdings" not in data:
        return []
    tickers = ["Portfolio"] + [h["ticker"] for h in data["holdings"]]
    return [
        html.Button(
            t,
            id={"type":"ticker-btn","index":t},
            n_clicks=0,
            style={
                "fontSize":"12px","padding":"4px 12px","borderRadius":"20px",
                "cursor":"pointer","fontWeight":"500","background":"transparent",
                "border":f"1.5px solid {T_PRI if t=='Portfolio' else COLORS[(i-1)%len(COLORS)]}",
                "color": T_PRI if t=="Portfolio" else COLORS[(i-1)%len(COLORS)],
            }
        )
        for i,t in enumerate(tickers)
    ]


@app.callback(
    Output("pnl-history-chart","figure"),
    Input("portfolio-store","data"),
    Input("pnl-mode","value"),
    Input({"type":"ticker-btn","index":ALL},"n_clicks"),
    State({"type":"ticker-btn","index":ALL},"id"),
)
def pnl_history_chart(data, mode, n_clicks_list, btn_ids):
    fig = go.Figure()
    fig.update_layout(
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor=BORDER,
                   ticksuffix="%" if mode=="pct" else "",
                   tickprefix="" if mode=="pct" else "$",
                   zeroline=True, zerolinecolor=BORDER, zerolinewidth=1),
        hovermode="x unified", height=380, **PLOTLY_BASE,
    )
    if not data or "holdings" not in data:
        return fig

    selected = "Portfolio"
    if n_clicks_list and any(n and n > 0 for n in n_clicks_list):
        last_idx = max(range(len(n_clicks_list)), key=lambda i: n_clicks_list[i] or 0)
        selected = btn_ids[last_idx]["index"]

    holdings  = data["holdings"]
    color_map = {h["ticker"]: COLORS[i % len(COLORS)] for i,h in enumerate(holdings)}

    if selected == "Portfolio":
        series = {}
        for h in holdings:
            for tr in h.get("tranches",[]):
                idx   = pd.to_datetime(tr["dates"])
                key   = f"{h['ticker']}_{tr['buy_date']}"
                series[key] = {
                    "pnl":  pd.Series(tr["pnl"],  index=idx),
                    "cost": pd.Series([tr["shares"]*tr["buy_price"]]*len(idx), index=idx),
                }
        if series:
            cpnl  = pd.concat([v["pnl"]  for v in series.values()],axis=1).ffill().sum(axis=1).sort_index()
            ccost = pd.concat([v["cost"] for v in series.values()],axis=1).ffill().sum(axis=1).sort_index()
            y  = (cpnl/ccost*100).round(2) if mode=="pct" else cpnl.round(2)
            lv = y.iloc[-1] if len(y) else 0
            lc = GREEN if lv >= 0 else RED
            fc = "rgba(29,158,117,0.12)" if lv >= 0 else "rgba(226,75,74,0.10)"
            fig.add_trace(go.Scatter(
                x=cpnl.index.strftime("%Y-%m-%d").tolist(), y=y.tolist(),
                name="Portfolio", mode="lines", fill="tozeroy", fillcolor=fc,
                line=dict(color=lc, width=2.5),
                hovertemplate=("%{y:.2f}%<extra>Portfolio</extra>" if mode=="pct"
                               else "$%{y:,.2f}<extra>Portfolio</extra>"),
            ))
    else:
        hm = next((h for h in holdings if h["ticker"]==selected), None)
        if hm:
            tranches = hm.get("tranches",[])
            bc = color_map.get(selected, COLORS[0])
            if len(tranches) == 1:
                tr = tranches[0]
                fig.add_trace(go.Scatter(
                    x=tr["dates"], y=tr["pct"] if mode=="pct" else tr["pnl"],
                    name=selected, mode="lines", fill="tozeroy",
                    fillcolor="rgba(55,138,221,0.10)",
                    line=dict(color=bc, width=2.5),
                ))
            else:
                pnl_p, cost_p = [], []
                for tr in tranches:
                    idx   = pd.to_datetime(tr["dates"])
                    pnl_s = pd.Series(tr["pnl"], index=idx)
                    cst_s = pd.Series([tr["shares"]*tr["buy_price"]]*len(idx), index=idx)
                    pnl_p.append(pnl_s); cost_p.append(cst_s)
                    fig.add_trace(go.Scatter(
                        x=tr["dates"], y=tr["pct"] if mode=="pct" else tr["pnl"],
                        name=f"  {tr['buy_date']} ({int(tr['shares'])} shares)",
                        mode="lines", line=dict(color=bc,width=1,dash="dot"), opacity=0.45,
                    ))
                cpnl  = pd.concat(pnl_p, axis=1).ffill().sum(axis=1).sort_index()
                ccost = pd.concat(cost_p,axis=1).ffill().sum(axis=1).sort_index()
                yc = (cpnl/ccost*100).round(2) if mode=="pct" else cpnl.round(2)
                fig.add_trace(go.Scatter(
                    x=cpnl.index.strftime("%Y-%m-%d").tolist(), y=yc.tolist(),
                    name=f"{selected} (combined)", mode="lines",
                    fill="tozeroy", fillcolor="rgba(55,138,221,0.10)",
                    line=dict(color=bc, width=2.5),
                ))
    fig.add_hline(y=0, line_color=BORDER, line_width=0.8)
    return fig


@app.callback(Output("price-chart","figure"), Input("portfolio-store","data"))
def price_chart(data):
    fig = go.Figure()
    fig.update_layout(xaxis=dict(showgrid=False),yaxis=dict(gridcolor=BORDER),**PLOTLY_BASE)
    if not data or "histories" not in data: return fig
    for i,(t,recs) in enumerate(data["histories"].items()):
        df = pd.DataFrame(recs)
        if df.empty or not df["Close"].iloc[0]: continue
        fig.add_trace(go.Scatter(
            x=df["Date"], y=(df["Close"]/df["Close"].iloc[0]*100).round(2),
            name=t, mode="lines", line=dict(color=COLORS[i%len(COLORS)],width=1.8),
        ))
    fig.add_hline(y=100, line_dash="dot", line_color=BORDER)
    return fig


@app.callback(Output("allocation-chart","figure"), Input("portfolio-store","data"))
def allocation_chart(data):
    fig = go.Figure()
    fig.update_layout(**PLOTLY_BASE)
    if not data or "holdings" not in data: return fig
    h = data["holdings"]
    fig.add_trace(go.Pie(
        labels=[x["ticker"] for x in h], values=[x["mkt_value"] for x in h],
        hole=0.45, marker=dict(colors=COLORS[:len(h)],line=dict(color=BG,width=2)),
        textinfo="label+percent", textfont=dict(size=12),
    ))
    return fig


@app.callback(
    Output("pnl-bar-chart","figure"),
    Input("portfolio-store","data"),
    Input("pnl-mode","value"),
)
def pnl_bar(data, mode):
    fig = go.Figure()
    fig.update_layout(
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor=BORDER,
                   ticksuffix="%" if mode=="pct" else "",
                   tickprefix="" if mode=="pct" else "$"),
        **PLOTLY_BASE,
    )
    if not data or "holdings" not in data: return fig
    key = "pnl_pct" if mode=="pct" else "pnl"
    h   = sorted(data["holdings"],key=lambda x: x[key])
    fig.add_trace(go.Bar(
        x=[x["ticker"] for x in h], y=[x[key] for x in h],
        marker_color=[GREEN if x[key]>=0 else RED for x in h],
        text=[f"{'+' if x[key]>=0 else ''}{'%' if mode=='pct' else '$'}{abs(x[key]):,.2f}"
              for x in h],
        textposition="outside", textfont=dict(size=11),
    ))
    fig.add_hline(y=0,line_color=BORDER,line_width=1)
    return fig


@app.callback(Output("day-pnl-chart","figure"), Input("portfolio-store","data"))
def day_pnl_chart(data):
    fig = go.Figure()
    fig.update_layout(xaxis=dict(showgrid=False),
                      yaxis=dict(gridcolor=BORDER,tickprefix="$"),**PLOTLY_BASE)
    if not data or "holdings" not in data: return fig
    h = sorted(data["holdings"],key=lambda x: x["day_pnl"])
    fig.add_trace(go.Bar(
        x=[x["ticker"] for x in h], y=[x["day_pnl"] for x in h],
        marker_color=[GREEN if x["day_pnl"]>=0 else RED for x in h],
        text=[f"${x['day_pnl']:,.2f}  {'+' if x['day_chg_pct']>=0 else ''}{x['day_chg_pct']:.2f}%"
              for x in h],
        textposition="outside", textfont=dict(size=11),
    ))
    fig.add_hline(y=0,line_color=BORDER,line_width=1)
    return fig


@app.callback(Output("dividend-chart","figure"), Input("portfolio-store","data"))
def dividend_chart(data):
    fig = go.Figure()
    fig.update_layout(xaxis=dict(showgrid=False),
                      yaxis=dict(gridcolor=BORDER,tickprefix="$"),**PLOTLY_BASE)
    if not data or "holdings" not in data: return fig
    h = [x for x in data["holdings"] if x["annual_div"] > 0]
    if not h:
        fig.add_annotation(text="No dividend data yet — holdings are recent",
                           showarrow=False,font=dict(color=T_SEC,size=13))
        return fig
    h_s = sorted(h,key=lambda x: x["annual_div"],reverse=True)
    fig.add_trace(go.Bar(
        x=[x["ticker"] for x in h_s], y=[x["annual_div"] for x in h_s],
        marker_color=COLORS[1],
        text=[f"${x['annual_div']:,.2f}  ({x['div_yield']:.1f}% yield)" for x in h_s],
        textposition="outside", textfont=dict(size=11),
    ))
    return fig


@app.callback(Output("corr-chart","figure"), Input("portfolio-store","data"))
def corr_chart(data):
    fig = go.Figure()
    fig.update_layout(**PLOTLY_BASE)
    if not data or "histories" not in data or len(data["histories"]) < 2:
        fig.add_annotation(text="Need 2+ holdings with history",
                           showarrow=False,font=dict(color=T_SEC,size=13))
        return fig
    dfs = {t: pd.DataFrame(r).set_index("Date")["Close"].pct_change().dropna()
           for t,r in data["histories"].items()
           if len(pd.DataFrame(r)) > 5}
    if len(dfs) < 2: return fig
    corr  = pd.DataFrame(dfs).dropna().corr().round(2)
    ticks = list(corr.columns)
    fig.add_trace(go.Heatmap(
        z=corr.values.tolist(), x=ticks, y=ticks,
        colorscale=[[0,"#E24B4A"],[0.5,"#f8f8f6"],[1,"#1D9E75"]],
        zmin=-1, zmax=1,
        text=[[f"{v:.2f}" for v in row] for row in corr.values.tolist()],
        texttemplate="%{text}", textfont=dict(size=11),
        showscale=True, colorbar=dict(thickness=12,len=0.8),
    ))
    fig.update_layout(
        xaxis=dict(showgrid=False,tickfont=dict(size=11)),
        yaxis=dict(showgrid=False,tickfont=dict(size=11),autorange="reversed"),
    )
    return fig


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"\n  Portfolio Dashboard — Live P&L")
    print(f"  CSV: {CSV_PATH}")
    print(f"  Open http://127.0.0.1:8050\n")
    app.run(debug=False, port=8050)
