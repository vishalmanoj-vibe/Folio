"""
Financial Portfolio Dashboard — Live P&L
==========================================
Run:   python portfolio_dashboard.py
Open:  http://127.0.0.1:8050
"""

import json
import dash
from dash import dcc, html, dash_table, Input, Output, State, ALL, ctx
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import pytz
import warnings
warnings.filterwarnings("ignore")

# ── App ───────────────────────────────────────────────────────────────────────
app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "Portfolio — Live"

app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
        [title]:hover::after {
            content: attr(title);
            position: absolute;
            background: #2c2c2a;
            color: #f0efe8;
            font-size: 12px;
            line-height: 1.5;
            padding: 8px 12px;
            border-radius: 8px;
            max-width: 280px;
            white-space: normal;
            z-index: 9999;
            margin-top: 4px;
            margin-left: -8px;
            pointer-events: none;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        [title] { position: relative; }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

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

# ── Chart tooltip descriptions ─────────────────────────────────────────────────
CHART_INFO = {
    "pnl-history":   ("P&L from purchase date",
                      "Shows your profit or loss since you bought each holding. "
                      "The line starts at $0 on your purchase date and moves up (profit) "
                      "or down (loss) as the price changes. Toggle between Portfolio "
                      "(combined total) or individual stocks using the buttons above. "
                      "Switch between $ and % using the P&L view dropdown."),
    "price-chart":   ("Normalised price history",
                      "All holdings are rescaled to start at 100 on the left edge of "
                      "the chart so you can compare performance side by side regardless "
                      "of their actual price. A line at 120 means that stock is up 20% "
                      "over the selected period. The dotted line at 100 is the baseline."),
    "allocation":    ("Portfolio allocation",
                      "Shows what percentage of your total portfolio value each holding "
                      "represents today. Larger slices = bigger positions. Use this to "
                      "check if you are over-concentrated in any single ETF."),
    "pnl-bar":       ("Unrealised P&L — all time",
                      "The dollar (or percentage) gain or loss on each holding since you "
                      "first bought it, based on your weighted average purchase price. "
                      "Green bars = currently profitable. Red bars = currently at a loss. "
                      "This is unrealised — it only becomes real when you sell."),
    "day-pnl":       ("Today's P&L",
                      "How much each holding has gained or lost today compared to "
                      "yesterday's closing price. This resets every trading day. "
                      "Green = up today, red = down today. Useful for tracking "
                      "short-term market movements on your specific positions."),
    "dividend":      ("Annual dividend income",
                      "The estimated annual dividend income from each holding based on "
                      "dividends paid over the last 12 months, scaled to your share count. "
                      "The yield percentage shown is annual dividends divided by current "
                      "market value. Higher yield = more income relative to what you hold."),
    "correlation":   ("Return correlation matrix",
                      "Shows how similarly two holdings move together on a scale of "
                      "-1 to +1. A score near +1 (dark green) means they tend to rise "
                      "and fall together — less diversification. Near 0 means they move "
                      "independently. Near -1 (dark red) means they move in opposite "
                      "directions — good diversification. Ideally you want a mix of low "
                      "or negative correlations across your portfolio."),
}

# ── Purchase history ───────────────────────────────────────────────────────────
INITIAL_HISTORY = [
    {"ticker":"VHY",  "type":"buy","shares":7,  "price":81.87,         "date":"2026-03-30"},
    {"ticker":"AINF", "type":"buy","shares":30, "price":16.8763333333,  "date":"2026-03-06"},
    {"ticker":"AINF", "type":"buy","shares":20, "price":16.0295,        "date":"2026-03-09"},
    {"ticker":"ASIA", "type":"buy","shares":35, "price":15.03257142857, "date":"2026-03-16"},
    {"ticker":"ASIA", "type":"buy","shares":15, "price":14.9426666667,  "date":"2026-03-23"},
    {"ticker":"ASIA", "type":"buy","shares":15, "price":14.6326666667,  "date":"2026-03-30"},
    {"ticker":"SEMI", "type":"buy","shares":25, "price":23.7896,        "date":"2026-03-09"},
    {"ticker":"SEMI", "type":"buy","shares":15, "price":25.8026666667,  "date":"2026-03-11"},
    {"ticker":"SEMI", "type":"buy","shares":10, "price":25.209,         "date":"2026-03-23"},
    {"ticker":"IOO",  "type":"buy","shares":2,  "price":177.4,          "date":"2026-03-05"},
    {"ticker":"IOZ",  "type":"buy","shares":5,  "price":36.55,          "date":"2026-03-05"},
]

NAMES = {
    "VHY":  "Vanguard High Yield ETF",
    "AINF": "Betashares Global Infra ETF",
    "ASIA": "Betashares Asia Tech ETF",
    "SEMI": "Betashares Global Semis ETF",
    "IOO":  "iShares Global 100 ETF",
    "IOZ":  "iShares Core ASX 200 ETF",
}

# ── Build holdings from transaction history ────────────────────────────────────
def build_holdings(history):
    """
    Aggregate buy/sell transactions into one row per ticker.
    Sells reduce share count and are excluded from cost basis calc (FIFO not needed here —
    we simply reduce total shares and adjust cost proportionally).
    """
    df = pd.DataFrame(history)
    if df.empty:
        return []

    results = []
    for ticker, grp in df.groupby("ticker"):
        buys  = grp[grp["type"] == "buy"].copy()
        sells = grp[grp["type"] == "sell"].copy() if "sell" in grp["type"].values else pd.DataFrame()

        total_bought = buys["shares"].sum()
        total_cost   = (buys["shares"] * buys["price"]).sum()
        total_sold   = sells["shares"].sum() if not sells.empty else 0
        net_shares   = total_bought - total_sold

        if net_shares <= 0:
            continue  # fully sold out

        avg_cost     = round(total_cost / total_bought, 4) if total_bought else 0
        remaining_cost = avg_cost * net_shares

        # Build per-buy-tranche data (buys only)
        buy_tranches = []
        for _, row in buys.iterrows():
            buy_tranches.append({
                "ticker":    ticker,
                "shares":    float(row["shares"]),
                "price":     float(row["price"]),
                "date":      str(row["date"]),
                "buy_price": float(row["price"]),
                "buy_date":  str(row["date"]),
            })

        results.append({
            "ticker":       ticker,
            "ticker_yf":    ticker + ".AX",
            "name":         NAMES.get(ticker, ticker),
            "market":       "ETF/ASX",
            "total_shares": float(net_shares),
            "total_cost":   round(remaining_cost, 2),
            "avg_cost":     avg_cost,
            "first_purchase": buys["date"].min(),
            "buy_tranches": buy_tranches,
        })

    return results


# ── Market status ──────────────────────────────────────────────────────────────
def is_market_open():
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


# ── Data fetch ─────────────────────────────────────────────────────────────────
def fetch_live(holdings, hist_period="3mo"):
    if not holdings:
        return {}
    enriched  = []
    histories = {}

    for h in holdings:
        ticker_yf = h["ticker_yf"]
        try:
            tk   = yf.Ticker(ticker_yf)
            info = tk.info
            fi   = tk.fast_info

            last_price = float(fi.get("last_price") or info.get("regularMarketPrice") or h["avg_cost"])
            prev_close = float(fi.get("previous_close") or info.get("previousClose") or last_price)
            day_high   = float(fi.get("day_high") or info.get("dayHigh") or last_price)
            day_low    = float(fi.get("day_low") or info.get("dayLow") or last_price)

            day_chg     = round(last_price - prev_close, 4)
            day_chg_pct = round((day_chg / prev_close * 100) if prev_close else 0, 2)
            mkt_value   = round(h["total_shares"] * last_price, 2)
            pnl         = round(mkt_value - h["total_cost"], 2)
            pnl_pct     = round((pnl / h["total_cost"] * 100) if h["total_cost"] else 0, 2)
            day_pnl     = round(day_chg * h["total_shares"], 2)

            hist_full   = tk.history(period="max")
            hist_period_df = tk.history(period=hist_period)

            div_s      = hist_full["Dividends"] if "Dividends" in hist_full.columns else pd.Series(dtype=float)
            cutoff     = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
            annual_div = round(float(div_s[div_s.index >= cutoff].sum()) * h["total_shares"], 2)
            total_div  = round(float(div_s.sum()) * h["total_shares"], 2)
            div_yield  = round((annual_div / mkt_value * 100) if mkt_value else 0, 2)

            # Period history for normalised price chart
            if not hist_period_df.empty:
                df_p = hist_period_df["Close"].reset_index()
                df_p.columns = ["Date","Close"]
                df_p["Date"] = pd.to_datetime(df_p["Date"]).dt.tz_localize(None)
                histories[h["ticker"]] = df_p.to_dict("records")

            # Per-tranche P&L from purchase date
            tranche_data = []
            if not hist_full.empty:
                close_all = hist_full["Close"].copy()
                close_all.index = pd.to_datetime(close_all.index).tz_localize(None)
                for tr in h.get("buy_tranches", []):
                    buy_date = pd.to_datetime(tr["date"])
                    mask = close_all.index >= buy_date
                    if not mask.any():
                        continue
                    sub       = close_all[mask].copy()
                    pnl_s     = (sub - tr["price"]) * tr["shares"]
                    pct_s     = (sub - tr["price"]) / tr["price"] * 100
                    tranche_data.append({
                        "label":     f"{h['ticker']} @ ${tr['price']:.2f} ({tr['date']})",
                        "dates":     [d.strftime("%Y-%m-%d") for d in sub.index],
                        "pnl":       [round(v, 2) for v in pnl_s.tolist()],
                        "pct":       [round(v, 2) for v in pct_s.tolist()],
                        "shares":    float(tr["shares"]),
                        "buy_price": float(tr["price"]),
                        "buy_date":  tr["date"],
                    })

            enriched.append({
                **h,
                "last_price":   round(last_price, 3),
                "prev_close":   round(prev_close, 3),
                "day_high":     round(day_high, 3),
                "day_low":      round(day_low, 3),
                "day_chg":      day_chg,
                "day_chg_pct":  day_chg_pct,
                "day_pnl":      day_pnl,
                "mkt_value":    mkt_value,
                "pnl":          pnl,
                "pnl_pct":      pnl_pct,
                "total_div":    total_div,
                "annual_div":   annual_div,
                "div_yield":    div_yield,
                "tranches":     tranche_data,
            })
        except Exception as e:
            enriched.append({
                **h,
                "last_price": h["avg_cost"], "prev_close": h["avg_cost"],
                "day_high": h["avg_cost"], "day_low": h["avg_cost"],
                "day_chg": 0, "day_chg_pct": 0, "day_pnl": 0,
                "mkt_value": round(h["total_shares"]*h["avg_cost"],2),
                "pnl": 0, "pnl_pct": 0,
                "total_div": 0, "annual_div": 0, "div_yield": 0,
                "tranches": [],
            })

    return {"holdings": enriched, "histories": histories,
            "fetched_at": datetime.now().strftime("%H:%M:%S")}


# ── UI helpers ─────────────────────────────────────────────────────────────────
def stat_card(label, value, sub=None, color=T_PRI, sub_color=T_SEC):
    return html.Div([
        html.P(label, style={"fontSize":"12px","color":T_SEC,"margin":"0 0 4px"}),
        html.P(value, style={"fontSize":"20px","fontWeight":"500","margin":"0","color":color}),
        html.P(sub,   style={"fontSize":"11px","color":sub_color,"margin":"3px 0 0"}) if sub else None,
    ], style={"background":SURFACE,"borderRadius":"10px",
              "padding":"14px 18px","flex":"1","minWidth":"130px"})


def chart_title(label, info_key):
    """Chart title with hoverable (i) info button."""
    tip = CHART_INFO.get(info_key, ("",""))[1]
    return html.Div([
        html.Span(label, style={"fontSize":"13px","fontWeight":"500","color":T_PRI}),
        html.Span("i", title=tip, style={
            "display":"inline-flex","alignItems":"center","justifyContent":"center",
            "width":"16px","height":"16px","borderRadius":"50%",
            "background":SURFACE,"border":f"1px solid {BORDER}",
            "fontSize":"10px","color":T_SEC,"cursor":"help",
            "marginLeft":"6px","fontWeight":"500","flexShrink":"0",
            "verticalAlign":"middle",
        }),
    ], style={"display":"inline-flex","alignItems":"center","marginBottom":"6px"})


def section(title_node, children, border=True):
    return html.Div([
        title_node,
        children,
    ], style={
        "padding":"16px 24px",
        "borderBottom": f"0.5px solid {BORDER}" if border else "none",
    })


# ── Transaction log display ────────────────────────────────────────────────────
def txn_table(history):
    if not history:
        return html.P("No transactions yet.", style={"color":T_SEC,"fontSize":"13px"})
    th = {"fontSize":"11px","color":T_SEC,"fontWeight":"500","padding":"6px 10px",
          "borderBottom":f"1px solid {BORDER}","backgroundColor":SURFACE,
          "textAlign":"left","whiteSpace":"nowrap"}
    td_s = {"fontSize":"12px","padding":"6px 10px",
             "borderBottom":f"0.5px solid {BORDER}","whiteSpace":"nowrap"}
    rows = []
    for i, t in enumerate(reversed(history)):
        c = GREEN if t["type"] == "buy" else RED
        rows.append(html.Tr([
            html.Td(t["date"],                        style=td_s),
            html.Td(t["ticker"],                      style={**td_s,"fontWeight":"500"}),
            html.Td(t["type"].upper(),
                    style={**td_s,"color":c,"fontWeight":"500"}),
            html.Td(str(t["shares"]),                 style=td_s),
            html.Td(f"${float(t['price']):,.4f}",     style=td_s),
            html.Td(f"${float(t['shares'])*float(t['price']):,.2f}", style=td_s),
        ]))
    return html.Table([
        html.Thead(html.Tr([html.Th(c,style=th) for c in
                            ["Date","Ticker","Type","Shares","Price","Total"]])),
        html.Tbody(rows),
    ], style={"width":"100%","borderCollapse":"collapse","fontSize":"12px"})


# ── Layout ─────────────────────────────────────────────────────────────────────
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
    ], style={
        "display":"flex","justifyContent":"space-between","alignItems":"flex-start",
        "padding":"18px 24px 12px","borderBottom":f"0.5px solid {BORDER}",
    }),

    # Controls bar
    html.Div([
        html.Div([
            html.P("Chart period", style={"fontSize":"12px","color":T_SEC,"margin":"0 0 4px"}),
            dcc.Dropdown(id="period-picker",
                options=[
                    {"label":"Since purchase","value":"max"},
                    {"label":"1 month",       "value":"1mo"},
                    {"label":"3 months",      "value":"3mo"},
                    {"label":"6 months",      "value":"6mo"},
                    {"label":"1 year",        "value":"1y"},
                    {"label":"2 years",       "value":"2y"},
                ],
                value="3mo", clearable=False,
                style={"width":"155px","fontSize":"13px"}),
        ]),
        html.Div([
            html.P("P&L view", style={"fontSize":"12px","color":T_SEC,"margin":"0 0 4px"}),
            dcc.Dropdown(id="pnl-mode",
                options=[
                    {"label":"Dollar ($)",    "value":"dollar"},
                    {"label":"Percentage (%)","value":"pct"},
                ],
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

    # ── Buy / Sell panel ──────────────────────────────────────────────────────
    html.Div([
        html.Div([
            chart_title("Add transaction", ""),
            html.P("Enter a buy or sell to instantly update your portfolio.",
                   style={"fontSize":"12px","color":T_SEC,"margin":"2px 0 12px"}),
        ]),
        html.Div([
            # Type
            html.Div([
                html.P("Type", style={"fontSize":"11px","color":T_SEC,"margin":"0 0 4px"}),
                dcc.Dropdown(id="txn-type",
                    options=[{"label":"Buy","value":"buy"},{"label":"Sell","value":"sell"}],
                    value="buy", clearable=False,
                    style={"width":"100px","fontSize":"13px"}),
            ]),
            # Ticker
            html.Div([
                html.P("Ticker", style={"fontSize":"11px","color":T_SEC,"margin":"0 0 4px"}),
                dcc.Input(id="txn-ticker", type="text", placeholder="e.g. VHY",
                          style={"width":"90px","fontSize":"13px","padding":"6px 8px",
                                 "border":f"0.5px solid {BORDER}","borderRadius":"6px"}),
            ]),
            # Shares
            html.Div([
                html.P("Shares", style={"fontSize":"11px","color":T_SEC,"margin":"0 0 4px"}),
                dcc.Input(id="txn-shares", type="number", placeholder="0",
                          style={"width":"90px","fontSize":"13px","padding":"6px 8px",
                                 "border":f"0.5px solid {BORDER}","borderRadius":"6px"}),
            ]),
            # Price
            html.Div([
                html.P("Price ($)", style={"fontSize":"11px","color":T_SEC,"margin":"0 0 4px"}),
                dcc.Input(id="txn-price", type="number", placeholder="0.00",
                          style={"width":"100px","fontSize":"13px","padding":"6px 8px",
                                 "border":f"0.5px solid {BORDER}","borderRadius":"6px"}),
            ]),
            # Date
            html.Div([
                html.P("Date", style={"fontSize":"11px","color":T_SEC,"margin":"0 0 4px"}),
                dcc.Input(id="txn-date", type="text",
                          placeholder=datetime.now().strftime("%Y-%m-%d"),
                          value=datetime.now().strftime("%Y-%m-%d"),
                          style={"width":"120px","fontSize":"13px","padding":"6px 8px",
                                 "border":f"0.5px solid {BORDER}","borderRadius":"6px"}),
            ]),
            # Submit
            html.Div([
                html.P(" ", style={"fontSize":"11px","margin":"0 0 4px"}),
                html.Button("Add transaction", id="txn-submit", n_clicks=0,
                            style={"fontWeight":"500","fontSize":"13px",
                                   "padding":"7px 16px"}),
            ]),
        ], style={"display":"flex","gap":"12px","flexWrap":"wrap","alignItems":"flex-end"}),

        # Feedback message
        html.P(id="txn-msg", style={"fontSize":"12px","marginTop":"8px",
                                    "color":GREEN,"minHeight":"16px"}),

        # Transaction log
        html.Details([
            html.Summary("Transaction history",
                         style={"fontSize":"12px","color":T_SEC,"cursor":"pointer",
                                "marginTop":"10px","userSelect":"none"}),
            html.Div(id="txn-log", style={"marginTop":"10px","overflowX":"auto"}),
        ]),
    ], style={"padding":"16px 24px","borderBottom":f"0.5px solid {BORDER}",
              "background":SURFACE}),

    # Live positions table
    section(
        chart_title("Live positions",""),
        html.Div(id="live-table"),
    ),

    # P&L from purchase date
    section(
        chart_title("P&L from purchase date","pnl-history"),
        html.Div([
            html.Div([
                html.P("View:", style={"fontSize":"12px","color":T_SEC,
                                       "margin":"0 8px 0 0","alignSelf":"center"}),
                html.Div(id="ticker-toggle-btns",
                         style={"display":"flex","gap":"6px","flexWrap":"wrap"}),
            ], style={"display":"flex","alignItems":"center",
                      "marginBottom":"12px","flexWrap":"wrap","gap":"8px"}),
            dcc.Graph(id="pnl-history-chart", config={"displayModeBar":False}),
        ]),
    ),

    # Charts grid
    html.Div([
        html.Div([
            html.Div([
                chart_title("Price history — normalised to 100","price-chart"),
                dcc.Graph(id="price-chart", config={"displayModeBar":False}),
            ], style={"flex":"2","minWidth":"280px"}),
            html.Div([
                chart_title("Portfolio allocation","allocation"),
                dcc.Graph(id="allocation-chart", config={"displayModeBar":False}),
            ], style={"flex":"1","minWidth":"220px"}),
        ], style={"display":"flex","gap":"14px","flexWrap":"wrap","marginBottom":"14px"}),

        html.Div([
            html.Div([
                chart_title("Unrealised P&L — all time","pnl-bar"),
                dcc.Graph(id="pnl-bar-chart", config={"displayModeBar":False}),
            ], style={"flex":"1","minWidth":"260px"}),
            html.Div([
                chart_title("Today's P&L","day-pnl"),
                dcc.Graph(id="day-pnl-chart", config={"displayModeBar":False}),
            ], style={"flex":"1","minWidth":"260px"}),
        ], style={"display":"flex","gap":"14px","flexWrap":"wrap","marginBottom":"14px"}),

        html.Div([
            html.Div([
                chart_title("Annual dividend income","dividend"),
                dcc.Graph(id="dividend-chart", config={"displayModeBar":False}),
            ], style={"flex":"1","minWidth":"260px"}),
            html.Div([
                chart_title("Return correlation matrix","correlation"),
                dcc.Graph(id="corr-chart", config={"displayModeBar":False}),
            ], style={"flex":"1","minWidth":"260px"}),
        ], style={"display":"flex","gap":"14px","flexWrap":"wrap"}),

    ], style={"padding":"16px 24px"}),

], style={"fontFamily":"system-ui,-apple-system,sans-serif",
          "color":T_PRI,"maxWidth":"1300px","margin":"0 auto","backgroundColor":BG})


# ── Callbacks ──────────────────────────────────────────────────────────────────

# 1. Add transaction → update store + feedback
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
def add_transaction(n, txn_type, ticker, shares, price, date, history):
    base_style = {"fontSize":"12px","marginTop":"8px","minHeight":"16px"}
    if not ticker or not shares or not price:
        return history, "Please fill in ticker, shares and price.", {**base_style,"color":RED}
    ticker = ticker.strip().upper()
    try:
        shares = float(shares)
        price  = float(price)
    except ValueError:
        return history, "Shares and price must be numbers.", {**base_style,"color":RED}
    if shares <= 0 or price <= 0:
        return history, "Shares and price must be positive.", {**base_style,"color":RED}

    # Validate sell doesn't exceed holdings
    if txn_type == "sell":
        df = pd.DataFrame(history)
        if not df.empty and ticker in df["ticker"].values:
            tk_df = df[df["ticker"] == ticker]
            held  = tk_df[tk_df["type"]=="buy"]["shares"].sum() - \
                    tk_df[tk_df["type"]=="sell"]["shares"].sum() if "sell" in tk_df["type"].values else tk_df[tk_df["type"]=="buy"]["shares"].sum()
            if shares > held:
                return history, f"Cannot sell {shares} shares — you only hold {held}.", {**base_style,"color":RED}
        else:
            return history, f"No holdings found for {ticker}.", {**base_style,"color":RED}

    new_txn = {"ticker":ticker,"type":txn_type,"shares":shares,"price":price,"date":date}
    updated  = history + [new_txn]
    sign     = "+" if txn_type=="buy" else "-"
    msg      = f"{txn_type.capitalize()} {shares} {ticker} @ ${price:.4f} added."
    return updated, msg, {**base_style,"color": GREEN if txn_type=="buy" else RED}


# 2. Transaction log display
@app.callback(
    Output("txn-log","children"),
    Input("txn-store","data"),
)
def update_txn_log(history):
    return txn_table(history)


# 3. Portfolio data fetch — triggered by interval, refresh, period, OR txn change
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
    holdings = build_holdings(history or INITIAL_HISTORY)
    if not holdings:
        return {}, "No holdings", market_badge()
    data = fetch_live(holdings, period)
    return data, f"Updated {data.get('fetched_at','')}", market_badge()


# 4. Stat cards
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
        stat_card("Total value",    f"${total_val:,.2f}"),
        stat_card("Cost basis",     f"${total_cost:,.2f}"),
        stat_card("Unrealised P&L", f"{ps}${total_pnl:,.2f}",
                  f"{ps}{pnl_pct:.2f}% all time", pc, pc),
        stat_card("Today's P&L",   f"{ds}${total_day:,.2f}",
                  "across all positions", dc, dc),
        stat_card("Annual dividends",f"${annual_div:,.2f}",
                  f"{port_yield:.2f}% yield",
                  GREEN if port_yield > 0 else T_PRI, T_SEC),
        stat_card("Holdings", str(len(h))),
    ]


# 5. Live table
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
            html.Td(html.Span(x["ticker"], style={"fontWeight":"500"}), style=td),
            html.Td(x.get("name",""),      style={**td,"color":T_SEC,"fontSize":"12px"}),
            html.Td(str(x["total_shares"]),style=td),
            html.Td(f"${x['avg_cost']:,.4f}",  style=td),
            html.Td(f"${x['last_price']:,.3f}", style=td),
            html.Td([
                html.Div(f"{ds}${x['day_chg']:,.3f}",
                         style={"color":dc,"fontWeight":"500","fontSize":"13px"}),
                html.Div(f"{ds}{x['day_chg_pct']:.2f}%",
                         style={"color":dc,"fontSize":"11px"}),
            ], style=td),
            html.Td(f"${x['day_high']:,.3f} / ${x['day_low']:,.3f}",
                    style={**td,"fontSize":"12px","color":T_SEC}),
            html.Td(f"${x['mkt_value']:,.2f}", style=td),
            html.Td(f"${x['total_cost']:,.2f}", style=td),
            pnl_td(x["pnl"], x["pnl_pct"]),
            pnl_td(x["day_pnl"], x["day_chg_pct"]),
            html.Td(f"{x['div_yield']:.2f}%", style=td),
        ]))

    return html.Div([
        html.Table([
            html.Thead(html.Tr([html.Th(c,style=th) for c in [
                "Ticker","Name","Shares","Avg cost","Last price",
                "Day change","High / Low","Market value","Cost basis",
                "Unrealised P&L","Today's P&L","Div yield",
            ]])),
            html.Tbody(rows),
        ], style={"width":"100%","borderCollapse":"collapse",
                  "overflowX":"auto","display":"block"}),
    ], style={"overflowX":"auto","borderRadius":"8px","border":f"0.5px solid {BORDER}"})


# 6. Ticker toggle buttons
@app.callback(
    Output("ticker-toggle-btns","children"),
    Input("portfolio-store","data"),
)
def build_toggle_btns(data):
    if not data or "holdings" not in data:
        return []
    tickers = ["Portfolio"] + [h["ticker"] for h in data["holdings"]]
    btns = []
    for i, t in enumerate(tickers):
        color = T_PRI if t == "Portfolio" else COLORS[(i-1) % len(COLORS)]
        btns.append(html.Button(
            t, id={"type":"ticker-btn","index":t}, n_clicks=0,
            style={"fontSize":"12px","padding":"4px 12px","borderRadius":"20px",
                   "cursor":"pointer","border":f"1.5px solid {color}",
                   "background":"transparent","color":color,"fontWeight":"500"},
        ))
    return btns


# 7. P&L history chart
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
        all_series = {}
        for h in holdings:
            for tr in h.get("tranches", []):
                dates  = pd.to_datetime(tr["dates"])
                pnl_s  = pd.Series(tr["pnl"], index=dates)
                cost_s = pd.Series([tr["shares"]*tr["buy_price"]]*len(dates), index=dates)
                all_series[f"{h['ticker']}_{tr['buy_date']}"] = {"pnl":pnl_s,"cost":cost_s}

        if all_series:
            comb_pnl  = pd.concat([v["pnl"]  for v in all_series.values()],axis=1).ffill().sum(axis=1).sort_index()
            comb_cost = pd.concat([v["cost"] for v in all_series.values()],axis=1).ffill().sum(axis=1).sort_index()
            y = (comb_pnl/comb_cost*100).round(2) if mode=="pct" else comb_pnl.round(2)
            last_val  = y.iloc[-1] if len(y) else 0
            lc = GREEN if last_val >= 0 else RED
            fc = "rgba(29,158,117,0.12)" if last_val >= 0 else "rgba(226,75,74,0.10)"
            fig.add_trace(go.Scatter(
                x=comb_pnl.index.strftime("%Y-%m-%d").tolist(), y=y.tolist(),
                name="Portfolio", mode="lines", fill="tozeroy", fillcolor=fc,
                line=dict(color=lc, width=2.5),
                hovertemplate=("%{y:.2f}%<extra>Portfolio</extra>" if mode=="pct"
                               else "$%{y:,.2f}<extra>Portfolio</extra>"),
            ))
    else:
        h_match = next((h for h in holdings if h["ticker"]==selected), None)
        if h_match:
            tranches   = h_match.get("tranches", [])
            base_color = color_map.get(selected, COLORS[0])
            if len(tranches) == 1:
                tr = tranches[0]
                y  = tr["pct"] if mode=="pct" else tr["pnl"]
                fig.add_trace(go.Scatter(
                    x=tr["dates"], y=y, name=selected, mode="lines",
                    fill="tozeroy", fillcolor="rgba(55,138,221,0.10)",
                    line=dict(color=base_color, width=2.5),
                ))
            else:
                pnl_p, cost_p = [], []
                for tr in tranches:
                    dates  = pd.to_datetime(tr["dates"])
                    pnl_s  = pd.Series(tr["pnl"], index=dates)
                    cost_s = pd.Series([tr["shares"]*tr["buy_price"]]*len(dates), index=dates)
                    pnl_p.append(pnl_s); cost_p.append(cost_s)
                    y = tr["pct"] if mode=="pct" else tr["pnl"]
                    fig.add_trace(go.Scatter(
                        x=tr["dates"], y=y,
                        name=f"  {tr['buy_date']} ({int(tr['shares'])} shares)",
                        mode="lines",
                        line=dict(color=base_color, width=1, dash="dot"),
                        opacity=0.45,
                    ))
                comb_pnl  = pd.concat(pnl_p, axis=1).ffill().sum(axis=1).sort_index()
                comb_cost = pd.concat(cost_p, axis=1).ffill().sum(axis=1).sort_index()
                y_c = (comb_pnl/comb_cost*100).round(2) if mode=="pct" else comb_pnl.round(2)
                fig.add_trace(go.Scatter(
                    x=comb_pnl.index.strftime("%Y-%m-%d").tolist(), y=y_c.tolist(),
                    name=f"{selected} (combined)", mode="lines",
                    fill="tozeroy", fillcolor="rgba(55,138,221,0.10)",
                    line=dict(color=base_color, width=2.5),
                ))

    fig.add_hline(y=0, line_color=BORDER, line_width=0.8)
    return fig


# 8. Price chart
@app.callback(
    Output("price-chart","figure"),
    Input("portfolio-store","data"),
)
def price_chart(data):
    fig = go.Figure()
    fig.update_layout(xaxis=dict(showgrid=False), yaxis=dict(gridcolor=BORDER), **PLOTLY_BASE)
    if not data or "histories" not in data: return fig
    for i,(ticker, recs) in enumerate(data["histories"].items()):
        df = pd.DataFrame(recs)
        if df.empty: continue
        base = df["Close"].iloc[0]
        if not base: continue
        fig.add_trace(go.Scatter(
            x=df["Date"], y=(df["Close"]/base*100).round(2),
            name=ticker, mode="lines",
            line=dict(color=COLORS[i % len(COLORS)], width=1.8),
        ))
    fig.add_hline(y=100, line_dash="dot", line_color=BORDER)
    return fig


# 9. Allocation donut
@app.callback(
    Output("allocation-chart","figure"),
    Input("portfolio-store","data"),
)
def allocation_chart(data):
    fig = go.Figure()
    fig.update_layout(**PLOTLY_BASE)
    if not data or "holdings" not in data: return fig
    h = data["holdings"]
    fig.add_trace(go.Pie(
        labels=[x["ticker"] for x in h], values=[x["mkt_value"] for x in h],
        hole=0.45, marker=dict(colors=COLORS[:len(h)], line=dict(color=BG, width=2)),
        textinfo="label+percent", textfont=dict(size=12),
    ))
    return fig


# 10. P&L bar
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
    h   = sorted(data["holdings"], key=lambda x: x[key])
    fig.add_trace(go.Bar(
        x=[x["ticker"] for x in h], y=[x[key] for x in h],
        marker_color=[GREEN if x[key]>=0 else RED for x in h],
        text=[f"{'+' if x[key]>=0 else ''}{'%' if mode=='pct' else '$'}{abs(x[key]):,.2f}" for x in h],
        textposition="outside", textfont=dict(size=11),
    ))
    fig.add_hline(y=0, line_color=BORDER, line_width=1)
    return fig


# 11. Day P&L bar
@app.callback(
    Output("day-pnl-chart","figure"),
    Input("portfolio-store","data"),
)
def day_pnl_chart(data):
    fig = go.Figure()
    fig.update_layout(xaxis=dict(showgrid=False),
                      yaxis=dict(gridcolor=BORDER, tickprefix="$"), **PLOTLY_BASE)
    if not data or "holdings" not in data: return fig
    h = sorted(data["holdings"], key=lambda x: x["day_pnl"])
    fig.add_trace(go.Bar(
        x=[x["ticker"] for x in h], y=[x["day_pnl"] for x in h],
        marker_color=[GREEN if x["day_pnl"]>=0 else RED for x in h],
        text=[f"${x['day_pnl']:,.2f}  {'+' if x['day_chg_pct']>=0 else ''}{x['day_chg_pct']:.2f}%" for x in h],
        textposition="outside", textfont=dict(size=11),
    ))
    fig.add_hline(y=0, line_color=BORDER, line_width=1)
    return fig


# 12. Dividends
@app.callback(
    Output("dividend-chart","figure"),
    Input("portfolio-store","data"),
)
def dividend_chart(data):
    fig = go.Figure()
    fig.update_layout(xaxis=dict(showgrid=False),
                      yaxis=dict(gridcolor=BORDER, tickprefix="$"), **PLOTLY_BASE)
    if not data or "holdings" not in data: return fig
    h = [x for x in data["holdings"] if x["annual_div"] > 0]
    if not h:
        fig.add_annotation(text="No dividend data yet — holdings are recent",
                           showarrow=False, font=dict(color=T_SEC, size=13))
        return fig
    h_s = sorted(h, key=lambda x: x["annual_div"], reverse=True)
    fig.add_trace(go.Bar(
        x=[x["ticker"] for x in h_s], y=[x["annual_div"] for x in h_s],
        marker_color=COLORS[1],
        text=[f"${x['annual_div']:,.2f}  ({x['div_yield']:.1f}% yield)" for x in h_s],
        textposition="outside", textfont=dict(size=11),
    ))
    return fig


# 13. Correlation heatmap
@app.callback(
    Output("corr-chart","figure"),
    Input("portfolio-store","data"),
)
def corr_chart(data):
    fig = go.Figure()
    fig.update_layout(**PLOTLY_BASE)
    if not data or "histories" not in data or len(data["histories"]) < 2:
        fig.add_annotation(text="Need 2+ holdings with history",
                           showarrow=False, font=dict(color=T_SEC, size=13))
        return fig
    dfs = {}
    for ticker, recs in data["histories"].items():
        df = pd.DataFrame(recs)
        if len(df) > 5:
            dfs[ticker] = df.set_index("Date")["Close"].pct_change().dropna()
    if len(dfs) < 2: return fig
    corr  = pd.DataFrame(dfs).dropna().corr().round(2)
    ticks = list(corr.columns)
    fig.add_trace(go.Heatmap(
        z=corr.values.tolist(), x=ticks, y=ticks,
        colorscale=[[0,"#E24B4A"],[0.5,"#f8f8f6"],[1,"#1D9E75"]],
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


# ── Run ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n  Portfolio Dashboard — Live P&L")
    print("  Open http://127.0.0.1:8050\n")
    app.run(debug=False, port=8050)