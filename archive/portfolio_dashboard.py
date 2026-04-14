"""
Financial Portfolio Dashboard — Live P&L with Purchase History
================================================================
Run:   python portfolio_dashboard.py
Open:  http://127.0.0.1:8050

Features:
- Tracks P&L from exact purchase dates with multiple tranches
- Weighted average cost per holding
- Period dropdown drives all charts
- Auto-refreshes every 60 seconds
- ASX ETFs (.AX suffix applied automatically)
"""

import dash
from dash import dcc, html, dash_table, Input, Output, State, ALL
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

# ── Purchase history (multiple tranches) ──────────────────────────────────────
# Each row = one buy. Ticker WITHOUT .AX — added automatically below.
PURCHASE_HISTORY = [
    {"ticker": "VHY",  "shares": 7,  "price": 81.87,          "date": "2026-03-30"},
    {"ticker": "AINF", "shares": 30, "price": 16.8763333333,   "date": "2026-03-06"},
    {"ticker": "AINF", "shares": 20, "price": 16.0295,         "date": "2026-03-09"},
    {"ticker": "ASIA", "shares": 35, "price": 15.03257142857,  "date": "2026-03-16"},
    {"ticker": "ASIA", "shares": 15, "price": 14.9426666667,   "date": "2026-03-23"},
    {"ticker": "ASIA", "shares": 15, "price": 14.6326666667,   "date": "2026-03-30"},
    {"ticker": "SEMI", "shares": 25, "price": 23.7896,         "date": "2026-03-09"},
    {"ticker": "SEMI", "shares": 15, "price": 25.8026666667,   "date": "2026-03-11"},
    {"ticker": "SEMI", "shares": 10, "price": 25.209,          "date": "2026-03-23"},
    {"ticker": "IOO",  "shares": 2,  "price": 177.4,           "date": "2026-03-05"},
    {"ticker": "IOZ",  "shares": 5,  "price": 36.55,           "date": "2026-03-05"},
]

NAMES = {
    "VHY":  "Vanguard High Yield ETF",
    "AINF": "Betashares Global Infra ETF",
    "ASIA": "Betashares Asia Tech ETF",
    "SEMI": "Betashares Global Semis ETF",
    "IOO":  "iShares Global 100 ETF",
    "IOZ":  "iShares Core ASX 200 ETF",
}

# ── Build consolidated holdings from purchase history ─────────────────────────
def build_holdings(history):
    """Aggregate tranches into one row per ticker with weighted avg cost."""
    df = pd.DataFrame(history)
    df["cost"] = df["shares"] * df["price"]
    grouped = df.groupby("ticker").agg(
        total_shares=("shares", "sum"),
        total_cost=("cost", "sum"),
        first_purchase=("date", "min"),
    ).reset_index()
    grouped["avg_cost"] = (grouped["total_cost"] / grouped["total_shares"]).round(4)
    grouped["ticker_yf"] = grouped["ticker"] + ".AX"
    grouped["name"] = grouped["ticker"].map(NAMES)
    grouped["market"] = "ETF/ASX"
    return grouped.to_dict("records")


HOLDINGS_BASE = build_holdings(PURCHASE_HISTORY)

# ── Market status ─────────────────────────────────────────────────────────────
def is_market_open():
    now_utc = datetime.now(pytz.utc)
    now_aet = now_utc.astimezone(pytz.timezone("Australia/Sydney"))
    if now_utc.weekday() >= 5:
        return False
    return 10 <= now_aet.hour < 16


def market_badge():
    open_ = is_market_open()
    return html.Span(
        "ASX open" if open_ else "ASX closed",
        style={
            "fontSize":"12px","padding":"3px 10px","borderRadius":"20px",
            "background":"#E1F5EE" if open_ else SURFACE,
            "color": GREEN if open_ else T_SEC,
            "fontWeight":"500",
            "border":f"0.5px solid {'#1D9E75' if open_ else BORDER}",
        }
    )


# ── Data fetch ────────────────────────────────────────────────────────────────
def fetch_live(holdings, hist_period="1y"):
    """
    Fetch live prices and full history for each holding.
    hist_period controls how far back the chart history goes.
    P&L is always calculated from the actual purchase date regardless of period.
    """
    enriched  = []
    histories = {}
    tranches  = pd.DataFrame(PURCHASE_HISTORY)

    for h in holdings:
        ticker_base = h["ticker"]
        ticker_yf   = h["ticker_yf"]
        try:
            tk   = yf.Ticker(ticker_yf)
            info = tk.info
            fi   = tk.fast_info

            last_price = float(
                fi.get("last_price") or
                info.get("regularMarketPrice") or
                h["avg_cost"]
            )
            prev_close = float(fi.get("previous_close") or info.get("previousClose") or last_price)
            day_high   = float(fi.get("day_high") or info.get("dayHigh") or last_price)
            day_low    = float(fi.get("day_low") or info.get("dayLow") or last_price)

            day_chg     = round(last_price - prev_close, 4)
            day_chg_pct = round((day_chg / prev_close * 100) if prev_close else 0, 2)

            total_shares = h["total_shares"]
            avg_cost     = h["avg_cost"]
            total_cost   = h["total_cost"]
            mkt_value    = round(total_shares * last_price, 2)
            pnl          = round(mkt_value - total_cost, 2)
            pnl_pct      = round((pnl / total_cost * 100) if total_cost else 0, 2)
            day_pnl      = round(day_chg * total_shares, 2)

            # Full history (as far back as possible for P&L-from-purchase chart)
            hist_full = tk.history(period="max")
            hist_period_df = tk.history(period=hist_period)

            # Dividends
            div_s      = hist_full["Dividends"] if "Dividends" in hist_full.columns else pd.Series(dtype=float)
            cutoff     = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
            annual_div = round(float(div_s[div_s.index >= cutoff].sum()) * total_shares, 2)
            total_div  = round(float(div_s.sum()) * total_shares, 2)
            div_yield  = round((annual_div / mkt_value * 100) if mkt_value else 0, 2)

            # History for the selected period (for normalised price chart)
            if not hist_period_df.empty:
                df_p = hist_period_df["Close"].reset_index()
                df_p.columns = ["Date","Close"]
                df_p["Date"] = pd.to_datetime(df_p["Date"]).dt.tz_localize(None)
                histories[ticker_base] = df_p.to_dict("records")

            # Per-tranche P&L history (value of each tranche over time from purchase date)
            tranche_rows = tranches[tranches["ticker"] == ticker_base].copy()
            tranche_data = []
            if not hist_full.empty:
                close_all = hist_full["Close"].copy()
                close_all.index = pd.to_datetime(close_all.index).tz_localize(None)
                for _, tr in tranche_rows.iterrows():
                    buy_date = pd.to_datetime(tr["date"])
                    mask     = close_all.index >= buy_date
                    if not mask.any():
                        continue
                    sub = close_all[mask].copy()
                    cost_at_buy = tr["price"]
                    pnl_series  = (sub - cost_at_buy) * tr["shares"]
                    pct_series  = ((sub - cost_at_buy) / cost_at_buy * 100)
                    tranche_data.append({
                        "label":    f"{ticker_base} @ ${cost_at_buy:.2f} ({tr['date']})",
                        "dates":    [d.strftime("%Y-%m-%d") for d in sub.index],
                        "pnl":      [round(v,2) for v in pnl_series.tolist()],
                        "pct":      [round(v,2) for v in pct_series.tolist()],
                        "shares":   int(tr["shares"]),
                        "buy_price":float(cost_at_buy),
                        "buy_date": tr["date"],
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
                "error": str(e),
            })

    return {
        "holdings": enriched,
        "histories": histories,
        "fetched_at": datetime.now().strftime("%H:%M:%S"),
    }


# ── UI helpers ────────────────────────────────────────────────────────────────
def stat_card(label, value, sub=None, color=T_PRI, sub_color=T_SEC):
    return html.Div([
        html.P(label, style={"fontSize":"12px","color":T_SEC,"margin":"0 0 4px"}),
        html.P(value, style={"fontSize":"20px","fontWeight":"500","margin":"0","color":color}),
        html.P(sub,   style={"fontSize":"11px","color":sub_color,"margin":"3px 0 0"}) if sub else None,
    ], style={"background":SURFACE,"borderRadius":"10px",
              "padding":"14px 18px","flex":"1","minWidth":"130px"})


def section(title, children):
    return html.Div([
        html.P(title, style={"fontSize":"13px","fontWeight":"500","margin":"0 0 10px"}),
        children,
    ], style={"padding":"16px 24px","borderBottom":f"0.5px solid {BORDER}"})


# ── Layout ────────────────────────────────────────────────────────────────────
app.layout = html.Div([

    dcc.Store(id="portfolio-store"),
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

    # Controls
    html.Div([
        html.Div([
            html.P("Chart period", style={"fontSize":"12px","color":T_SEC,"margin":"0 0 4px"}),
            dcc.Dropdown(
                id="period-picker",
                options=[
                    {"label":"Since purchase", "value":"max"},
                    {"label":"1 month",        "value":"1mo"},
                    {"label":"3 months",       "value":"3mo"},
                    {"label":"6 months",       "value":"6mo"},
                    {"label":"1 year",         "value":"1y"},
                    {"label":"2 years",        "value":"2y"},
                ],
                value="3mo", clearable=False,
                style={"width":"160px","fontSize":"13px"},
            ),
        ]),
        html.Div([
            html.P("P&L view", style={"fontSize":"12px","color":T_SEC,"margin":"0 0 4px"}),
            dcc.Dropdown(
                id="pnl-mode",
                options=[
                    {"label":"Dollar ($)",    "value":"dollar"},
                    {"label":"Percentage (%)", "value":"pct"},
                ],
                value="dollar", clearable=False,
                style={"width":"160px","fontSize":"13px"},
            ),
        ]),
        html.Button("Refresh now", id="refresh-btn", n_clicks=0,
                    style={"fontWeight":"500","alignSelf":"flex-end"}),
    ], style={
        "display":"flex","gap":"16px","alignItems":"flex-end",
        "padding":"14px 24px","borderBottom":f"0.5px solid {BORDER}","flexWrap":"wrap",
    }),

    # Stat cards
    html.Div(id="stat-cards",
             style={"display":"flex","gap":"10px","padding":"16px 24px",
                    "flexWrap":"wrap","borderBottom":f"0.5px solid {BORDER}"}),

    # Live positions table
    section("Live positions", html.Div(id="live-table")),

    # P&L from purchase date chart
    section("P&L from purchase date",
        html.Div([
            html.Div([
                html.P("View:", style={"fontSize":"12px","color":T_SEC,
                                       "margin":"0 8px 0 0","alignSelf":"center"}),
                html.Div(id="ticker-toggle-btns",
                         style={"display":"flex","gap":"6px","flexWrap":"wrap"}),
            ], style={"display":"flex","alignItems":"center",
                      "marginBottom":"12px","flexWrap":"wrap","gap":"8px"}),
            dcc.Graph(id="pnl-history-chart", config={"displayModeBar":False}),
        ])
    ),

    # Charts row 1
    html.Div([
        html.Div([
            html.Div(dcc.Graph(id="price-chart",     config={"displayModeBar":False}),
                     style={"flex":"2","minWidth":"280px"}),
            html.Div(dcc.Graph(id="allocation-chart", config={"displayModeBar":False}),
                     style={"flex":"1","minWidth":"220px"}),
        ], style={"display":"flex","gap":"14px","flexWrap":"wrap","marginBottom":"14px"}),

        html.Div([
            html.Div(dcc.Graph(id="pnl-bar-chart",  config={"displayModeBar":False}),
                     style={"flex":"1","minWidth":"260px"}),
            html.Div(dcc.Graph(id="day-pnl-chart",  config={"displayModeBar":False}),
                     style={"flex":"1","minWidth":"260px"}),
        ], style={"display":"flex","gap":"14px","flexWrap":"wrap","marginBottom":"14px"}),

        html.Div([
            html.Div(dcc.Graph(id="dividend-chart", config={"displayModeBar":False}),
                     style={"flex":"1","minWidth":"260px"}),
            html.Div(dcc.Graph(id="corr-chart",     config={"displayModeBar":False}),
                     style={"flex":"1","minWidth":"260px"}),
        ], style={"display":"flex","gap":"14px","flexWrap":"wrap"}),

    ], style={"padding":"16px 24px"}),

], style={
    "fontFamily":"system-ui,-apple-system,sans-serif",
    "color":T_PRI,"maxWidth":"1300px","margin":"0 auto","backgroundColor":BG,
})


# ── Callbacks ─────────────────────────────────────────────────────────────────

@app.callback(
    Output("portfolio-store","data"),
    Output("last-updated","children"),
    Output("market-status","children"),
    Input("live-interval","n_intervals"),
    Input("refresh-btn","n_clicks"),
    Input("period-picker","value"),       # period change also triggers refetch
)
def refresh(_, __, period):
    data = fetch_live(HOLDINGS_BASE, period)
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
        stat_card("Total value",     f"${total_val:,.2f}"),
        stat_card("Cost basis",      f"${total_cost:,.2f}"),
        stat_card("Unrealised P&L",
                  f"{ps}${total_pnl:,.2f}",
                  f"{ps}{pnl_pct:.2f}% all time", pc, pc),
        stat_card("Today's P&L",
                  f"{ds}${total_day:,.2f}",
                  "across all positions", dc, dc),
        stat_card("Annual dividends",
                  f"${annual_div:,.2f}",
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

    th = {"fontSize":"11px","color":T_SEC,"fontWeight":"500",
          "padding":"7px 12px","textAlign":"left",
          "borderBottom":f"1px solid {BORDER}",
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
            html.Td(x.get("name",""), style={**td,"color":T_SEC,"fontSize":"12px"}),
            html.Td(str(x["total_shares"]), style=td),
            html.Td(f"${x['avg_cost']:,.4f}", style=td),
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
            html.Thead(html.Tr([
                html.Th(c, style=th) for c in [
                    "Ticker","Name","Shares","Avg cost","Last price",
                    "Day change","High / Low","Market value","Cost basis",
                    "Unrealised P&L","Today's P&L","Div yield",
                ]
            ])),
            html.Tbody(rows),
        ], style={"width":"100%","borderCollapse":"collapse",
                  "overflowX":"auto","display":"block"}),
    ], style={"overflowX":"auto","borderRadius":"8px",
              "border":f"0.5px solid {BORDER}"})


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
        color = "#1a1a1a" if t == "Portfolio" else COLORS[i-1 if i > 0 else 0 % len(COLORS)]
        btns.append(html.Button(
            t, id={"type":"ticker-btn","index":t},
            n_clicks=0,
            style={
                "fontSize":"12px","padding":"4px 12px",
                "borderRadius":"20px","cursor":"pointer",
                "border":f"1.5px solid {color}",
                "background":"transparent","color":color,
                "fontWeight":"500",
            }
        ))
    return btns


@app.callback(
    Output("pnl-history-chart","figure"),
    Input("portfolio-store","data"),
    Input("pnl-mode","value"),
    Input({"type":"ticker-btn","index":ALL},"n_clicks"),
    State({"type":"ticker-btn","index":ALL},"id"),
)
def pnl_history_chart(data, mode, n_clicks_list, btn_ids):
    fig = go.Figure()
    ylabel = "P&L (%)" if mode == "pct" else "P&L ($)"
    fig.update_layout(
        xaxis=dict(showgrid=False, showline=False),
        yaxis=dict(gridcolor=BORDER,
                   ticksuffix="%" if mode=="pct" else "",
                   tickprefix="" if mode=="pct" else "$",
                   zeroline=True, zerolinecolor=BORDER, zerolinewidth=1),
        hovermode="x unified",
        height=380,
        **PLOTLY_BASE,
    )
    if not data or "holdings" not in data:
        return fig

    # Determine which ticker is selected (last clicked button)
    selected = "Portfolio"
    if n_clicks_list and any(n > 0 for n in n_clicks_list):
        last_click_idx = max(range(len(n_clicks_list)),
                             key=lambda i: n_clicks_list[i] or 0)
        selected = btn_ids[last_click_idx]["index"]

    holdings   = data["holdings"]
    color_map  = {h["ticker"]: COLORS[i % len(COLORS)]
                  for i, h in enumerate(holdings)}

    if selected == "Portfolio":
        # ── Combined portfolio P&L line ───────────────────────────────────
        # Align all holdings to a common date index, sum daily values
        all_series = {}
        for h in holdings:
            for tr in h.get("tranches", []):
                dates = pd.to_datetime(tr["dates"])
                vals  = tr["pnl"] if mode == "dollar" else None
                costs = tr["shares"] * tr["buy_price"]
                # For pct mode we track $ value and convert at the end
                pnl_s = pd.Series(tr["pnl"], index=dates)
                cost_s = pd.Series([costs]*len(dates), index=dates)
                key = f"{h['ticker']}_{tr['buy_date']}"
                all_series[key] = {"pnl": pnl_s, "cost": cost_s}

        if all_series:
            combined_pnl  = pd.concat([v["pnl"]  for v in all_series.values()], axis=1).ffill().sum(axis=1)
            combined_cost = pd.concat([v["cost"] for v in all_series.values()], axis=1).ffill().sum(axis=1)
            combined_pnl  = combined_pnl.sort_index()
            combined_cost = combined_cost.sort_index()

            if mode == "pct":
                y = (combined_pnl / combined_cost * 100).round(2)
                hover = "%{y:.2f}%"
            else:
                y = combined_pnl.round(2)
                hover = "$%{y:,.2f}"

            fill_color = "rgba(29,158,117,0.12)" if y.iloc[-1] >= 0 else "rgba(226,75,74,0.10)"
            line_color = GREEN if y.iloc[-1] >= 0 else RED

            fig.add_trace(go.Scatter(
                x=combined_pnl.index.strftime("%Y-%m-%d").tolist(),
                y=y.tolist(),
                name="Portfolio",
                mode="lines",
                fill="tozeroy",
                fillcolor=fill_color,
                line=dict(color=line_color, width=2.5),
                hovertemplate=hover + "<extra>Portfolio</extra>",
            ))

    else:
        # ── Single ticker — one solid line per tranche, averaged ──────────
        h_match = next((h for h in holdings if h["ticker"] == selected), None)
        if h_match:
            tranches   = h_match.get("tranches", [])
            base_color = color_map[selected]

            if len(tranches) == 1:
                tr = tranches[0]
                y  = tr["pct"] if mode == "pct" else tr["pnl"]
                fig.add_trace(go.Scatter(
                    x=tr["dates"], y=y,
                    name=selected, mode="lines",
                    fill="tozeroy",
                    fillcolor=f"rgba(55,138,221,0.10)",
                    line=dict(color=base_color, width=2.5),
                    hovertemplate=("%{y:.2f}%<extra>" if mode=="pct" else "$%{y:,.2f}<extra>") + selected + "</extra>",
                ))
            else:
                # Multiple tranches — show each dotted + weighted avg solid
                pnl_parts  = []
                cost_parts = []
                for tr in tranches:
                    dates  = pd.to_datetime(tr["dates"])
                    pnl_s  = pd.Series(tr["pnl"], index=dates)
                    cost_s = pd.Series([tr["shares"]*tr["buy_price"]]*len(dates), index=dates)
                    pnl_parts.append(pnl_s)
                    cost_parts.append(cost_s)
                    # Dotted individual tranche
                    y = tr["pct"] if mode=="pct" else tr["pnl"]
                    fig.add_trace(go.Scatter(
                        x=tr["dates"], y=y,
                        name=f"  {tr['buy_date']} ({tr['shares']} shares)",
                        mode="lines",
                        line=dict(color=base_color, width=1, dash="dot"),
                        opacity=0.45,
                        hovertemplate=("%{y:.2f}%<extra>" if mode=="pct" else "$%{y:,.2f}<extra>") + tr["buy_date"] + "</extra>",
                    ))

                # Weighted combined line
                combined_pnl  = pd.concat(pnl_parts,  axis=1).ffill().sum(axis=1).sort_index()
                combined_cost = pd.concat(cost_parts, axis=1).ffill().sum(axis=1).sort_index()
                if mode == "pct":
                    y_comb = (combined_pnl / combined_cost * 100).round(2)
                else:
                    y_comb = combined_pnl.round(2)

                fig.add_trace(go.Scatter(
                    x=combined_pnl.index.strftime("%Y-%m-%d").tolist(),
                    y=y_comb.tolist(),
                    name=f"{selected} (combined)",
                    mode="lines",
                    fill="tozeroy",
                    fillcolor="rgba(55,138,221,0.10)",
                    line=dict(color=base_color, width=2.5),
                    hovertemplate=("%{y:.2f}%<extra>" if mode=="pct" else "$%{y:,.2f}<extra>") + selected + " combined</extra>",
                ))

    fig.add_hline(y=0, line_color=BORDER, line_width=0.8)
    return fig


@app.callback(
    Output("price-chart","figure"),
    Input("portfolio-store","data"),
    Input("period-picker","value"),
)
def price_chart(data, period):
    fig = go.Figure()
    fig.update_layout(
        title=f"Price history — normalised to 100",
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor=BORDER),
        **PLOTLY_BASE,
    )
    if not data or "histories" not in data:
        return fig
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


@app.callback(
    Output("allocation-chart","figure"),
    Input("portfolio-store","data"),
)
def allocation_chart(data):
    fig = go.Figure()
    fig.update_layout(title="Portfolio allocation", **PLOTLY_BASE)
    if not data or "holdings" not in data: return fig
    h = data["holdings"]
    fig.add_trace(go.Pie(
        labels=[x["ticker"] for x in h],
        values=[x["mkt_value"] for x in h],
        hole=0.45,
        marker=dict(colors=COLORS[:len(h)], line=dict(color=BG, width=2)),
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
        title="Unrealised P&L — all time",
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor=BORDER,
                   ticksuffix="%" if mode=="pct" else "",
                   tickprefix="" if mode=="pct" else "$"),
        **PLOTLY_BASE,
    )
    if not data or "holdings" not in data: return fig
    key = "pnl_pct" if mode == "pct" else "pnl"
    h   = sorted(data["holdings"], key=lambda x: x[key])
    fig.add_trace(go.Bar(
        x=[x["ticker"] for x in h],
        y=[x[key] for x in h],
        marker_color=[GREEN if x[key] >= 0 else RED for x in h],
        text=[f"{'+' if x[key]>=0 else ''}"
              f"{'%' if mode=='pct' else '$'}{abs(x[key]):,.2f}"
              for x in h],
        textposition="outside", textfont=dict(size=11),
    ))
    fig.add_hline(y=0, line_color=BORDER, line_width=1)
    return fig


@app.callback(
    Output("day-pnl-chart","figure"),
    Input("portfolio-store","data"),
)
def day_pnl_chart(data):
    fig = go.Figure()
    fig.update_layout(
        title="Today's P&L",
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor=BORDER, tickprefix="$"),
        **PLOTLY_BASE,
    )
    if not data or "holdings" not in data: return fig
    h = sorted(data["holdings"], key=lambda x: x["day_pnl"])
    fig.add_trace(go.Bar(
        x=[x["ticker"] for x in h],
        y=[x["day_pnl"] for x in h],
        marker_color=[GREEN if x["day_pnl"] >= 0 else RED for x in h],
        text=[f"${x['day_pnl']:,.2f}  {'+' if x['day_chg_pct']>=0 else ''}{x['day_chg_pct']:.2f}%"
              for x in h],
        textposition="outside", textfont=dict(size=11),
    ))
    fig.add_hline(y=0, line_color=BORDER, line_width=1)
    return fig


@app.callback(
    Output("dividend-chart","figure"),
    Input("portfolio-store","data"),
)
def dividend_chart(data):
    fig = go.Figure()
    fig.update_layout(
        title="Annual dividend income",
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor=BORDER, tickprefix="$"),
        **PLOTLY_BASE,
    )
    if not data or "holdings" not in data: return fig
    h = [x for x in data["holdings"] if x["annual_div"] > 0]
    if not h:
        fig.add_annotation(text="No dividend data yet — these are recent purchases",
                           showarrow=False, font=dict(color=T_SEC, size=13))
        return fig
    h_s = sorted(h, key=lambda x: x["annual_div"], reverse=True)
    fig.add_trace(go.Bar(
        x=[x["ticker"] for x in h_s],
        y=[x["annual_div"] for x in h_s],
        marker_color=COLORS[1],
        text=[f"${x['annual_div']:,.2f}  ({x['div_yield']:.1f}% yield)" for x in h_s],
        textposition="outside", textfont=dict(size=11),
    ))
    return fig


@app.callback(
    Output("corr-chart","figure"),
    Input("portfolio-store","data"),
)
def corr_chart(data):
    fig = go.Figure()
    fig.update_layout(title="Return correlation matrix", **PLOTLY_BASE)
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
    combined = pd.DataFrame(dfs).dropna()
    corr     = combined.corr().round(2)
    ticks    = list(corr.columns)
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


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n  Portfolio Dashboard — Live P&L")
    print("  Open http://127.0.0.1:8050\n")
    app.run(debug=False, port=8050)