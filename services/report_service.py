import io
import os
import logging
from datetime import datetime, timedelta

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    Table, TableStyle, HRFlowable, Image,
    KeepTogether,
)

from services.technical_indicators import compute_signals
from services.web_search import search_financial_news

logger = logging.getLogger(__name__)

# ── Design tokens ─────────────────────────────────────────────────────────────
_TEAL        = colors.HexColor("#00c9a7")
_DARK        = colors.HexColor("#1c1c1a")
_SURFACE     = colors.HexColor("#f4f4f2")
_GREEN_HEX   = "#1D9E75"
_RED_HEX     = "#E24B4A"
_TEAL_HEX    = "#00c9a7"
_GREY        = colors.HexColor("#8a8880")
_WHITE       = colors.white
_LIGHT_ROW   = colors.HexColor("#fafafa")


# ── 1. Data assembly ──────────────────────────────────────────────────────────

def gather_report_data(portfolio_data: dict) -> dict:
    """
    Assembles all portfolio metrics needed for the report.
    Returns a flat dict of scalars + lists.
    """
    try:
        holdings = portfolio_data.get("holdings", [])
        histories = portfolio_data.get("histories", {})
        if not holdings:
            return {}

        total_val   = sum(h["mkt_value"]  for h in holdings)
        total_cost  = sum(h["total_cost"] for h in holdings)
        total_pnl   = total_val - total_cost
        pnl_pct     = (total_pnl / total_cost * 100) if total_cost else 0
        annual_div  = sum(h.get("annual_div", 0) for h in holdings)
        port_yield  = (annual_div / total_val * 100) if total_val else 0

        holdings_data = []
        for h in holdings:
            ticker  = h["ticker"]
            history = histories.get(ticker, [])
            sig     = compute_signals(ticker, history)
            holdings_data.append({
                "ticker":     ticker,
                "name":       h.get("name", ticker),
                "weight":     (h["mkt_value"] / total_val * 100) if total_val else 0,
                "mkt_value":  h["mkt_value"],
                "pnl_pct":    h["pnl_pct"],
                "day_chg_pct": h.get("day_chg_pct", 0),
                "div_yield":  h.get("div_yield", 0),
                "rsi":        sig.get("rsi", 0),
                "rsi_label":  sig.get("rsi_label", "N/A"),
                "macd_label": sig.get("macd_label", "N/A"),
                "bb_label":   sig.get("bb_label", "N/A"),
            })

        holdings_data.sort(key=lambda x: x["weight"], reverse=True)

        top_performer   = max(holdings_data, key=lambda x: x["pnl_pct"])
        worst_performer = min(holdings_data, key=lambda x: x["pnl_pct"])

        # Upcoming dividends (next 30 days)
        upcoming_dividends = []
        now = pd.Timestamp.now()
        for h in holdings:
            ndd = h.get("next_div_date")
            if ndd:
                try:
                    dt = pd.to_datetime(ndd)
                    if now <= dt <= now + timedelta(days=30):
                        upcoming_dividends.append({
                            "ticker":   h["ticker"],
                            "ex_date":  ndd,
                            "pay_date": h.get("payout_date", "TBC"),
                            "amount":   h.get("last_div_amount", 0),
                        })
                except Exception:
                    continue
        upcoming_dividends.sort(key=lambda x: x["ex_date"])

        # Build weekly portfolio P&L series from histories
        pnl_series = _build_pnl_series(holdings, histories)

        return {
            "generated_at":      datetime.now().strftime("%d %B %Y, %I:%M %p"),
            "total_val":         total_val,
            "total_cost":        total_cost,
            "total_pnl":         total_pnl,
            "pnl_pct":           pnl_pct,
            "annual_div":        annual_div,
            "port_yield":        port_yield,
            "holdings_data":     holdings_data,
            "top_performer":     top_performer,
            "worst_performer":   worst_performer,
            "upcoming_dividends": upcoming_dividends,
            "pnl_series":        pnl_series,
        }

    except Exception as e:
        logger.error(f"gather_report_data failed: {e}")
        return {}


def _build_pnl_series(
    holdings: list[dict],
    histories: dict,
) -> list[dict]:
    """
    Builds a daily portfolio P&L % series for the last 7 trading days.
    Returns list of {"date": str, "pnl_pct": float}.
    """
    try:
        frames = {}
        for h in holdings:
            ticker  = h["ticker"]
            history = histories.get(ticker, [])
            if not history:
                continue
            df = pd.DataFrame(history)
            df["Date"]  = pd.to_datetime(df["Date"])
            df          = df.set_index("Date").sort_index()
            frames[ticker] = df["Close"]

        if not frames:
            return []

        prices = pd.DataFrame(frames).dropna(how="all")
        # Tail last 7 trading days for a weekly view
        prices = prices.tail(7)

        if prices.empty:
            return []

        # Weight by current market value
        total_val = sum(h["mkt_value"] for h in holdings)
        weights   = {}
        for h in holdings:
            if h["ticker"] in prices.columns and total_val:
                weights[h["ticker"]] = h["mkt_value"] / total_val

        # Normalised return from period start (7 days ago)
        normed = prices / prices.iloc[0]
        weighted = sum(
            normed[t] * w
            for t, w in weights.items()
            if t in normed.columns
        )
        pnl_pct = (weighted - 1) * 100

        return [
            {"date": d.strftime("%Y-%m-%d"), "pnl_pct": round(float(v), 3)}
            for d, v in pnl_pct.items()
            if not pd.isna(v)
        ]

    except Exception as e:
        logger.warning(f"_build_pnl_series failed: {e}")
        return []


# ── 2. News fetching ──────────────────────────────────────────────────────────

def fetch_news_for_holdings(
    holdings: list[dict],
) -> dict[str, list[dict]]:
    """
    Returns {ticker: [{"title": str, "url": str, "body": str}]}
    """
    news_map: dict[str, list[dict]] = {}
    for h in holdings[:8]:
        ticker = h["ticker"]
        try:
            results = search_financial_news(
                f"{ticker} ASX ETF",
                max_results=2,
            )
            if not results:
                results = search_financial_news(
                    f"{ticker} ASX ETF news announcement",
                    max_results=2,
                )
            news_map[ticker] = [
                {
                    "title": r.get("title", ""),
                    "url":   r.get("href", ""),
                    "body":  r.get("body", "")[:300],
                }
                for r in (results or [])
            ]
        except Exception as e:
            logger.warning(f"News fetch failed for {ticker}: {e}")
            news_map[ticker] = []

    return news_map


def fetch_market_news() -> list[dict]:
    """
    Fetches general ASX market news, IPOs, and stocks to watch.
    Returns list of {"title": str, "url": str, "body": str}.
    """
    try:
        queries = [
            "ASX market news today Australia stocks",
            "ASX IPO upcoming 2026 new listing",
            "ASX stocks to watch this week Australia",
        ]
        combined = []
        for q in queries:
            results = search_financial_news(q, max_results=2)
            for r in results or []:
                combined.append({
                    "title": r.get("title", ""),
                    "url":   r.get("href", ""),
                    "body":  r.get("body", "")[:250],
                })
        return combined[:6]
    except Exception as e:
        logger.warning(f"Market news fetch failed: {e}")
        return []


# ── 3. AI commentary ──────────────────────────────────────────────────────────

def get_ai_commentary(
    report_data: dict,
    news_map: dict[str, list[dict]],
    market_news: list[dict],
    api_key: str,
) -> str:
    """
    Calls Gemini to write the weekly portfolio commentary.
    """
    try:
        import google.genai as genai

        prompt = (
            "Write a concise 3-paragraph weekly portfolio commentary "
            "for an Australian retail ETF investor. Plain text only, "
            "no markdown, no bullet points, no asterisks.\n\n"
            f"Total Portfolio Value: ${report_data['total_val']:,.0f}\n"
            f"Unrealised P&L: {report_data['pnl_pct']:+.1f}%\n"
            f"Portfolio Yield: {report_data['port_yield']:.2f}%\n"
            f"Top performer: {report_data['top_performer']['ticker']} "
            f"({report_data['top_performer']['pnl_pct']:+.1f}%)\n"
            f"Worst performer: {report_data['worst_performer']['ticker']} "
            f"({report_data['worst_performer']['pnl_pct']:+.1f}%)\n\n"
            "Holdings:\n"
        )
        for h in report_data.get("holdings_data", []):
            prompt += (
                f"- {h['ticker']}: {h['weight']:.1f}% of portfolio, "
                f"P&L {h['pnl_pct']:+.1f}%, RSI {h['rsi']:.0f} "
                f"({h['rsi_label']}), MACD {h['macd_label']}\n"
            )

        prompt += "\nRecent holding news:\n"
        for ticker, articles in list(news_map.items())[:5]:
            for a in articles[:1]:
                prompt += f"- {ticker}: {a['body'][:150]}\n"

        prompt += "\nGeneral ASX market news this week:\n"
        for item in market_news[:3]:
            prompt += f"- {item['body'][:150]}\n"

        prompt += (
            "\nParagraph 1: Overall portfolio performance this week. "
            "Paragraph 2: Key movers and technical signals (RSI/MACD). "
            "Paragraph 3: Week ahead — what to watch, any risks or opportunities. "
            "Be specific and direct. Do not repeat the raw numbers — interpret them."
        )

        client   = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="models/gemini-2.5-flash-lite",
            contents=prompt,
        )
        return response.text.strip()

    except Exception as e:
        logger.error(f"get_ai_commentary failed: {e}")
        return (
            "Market commentary is temporarily unavailable. "
            "Please try regenerating the report."
        )


# ── 4. Chart builder ──────────────────────────────────────────────────────────

def _build_pnl_chart_image(
    pnl_series: list[dict],
) -> bytes | None:
    """
    Renders a P&L % line chart using matplotlib.
    Returns PNG bytes or None on failure.
    """
    try:
        if not pnl_series or len(pnl_series) < 2:
            return None

        dates  = [datetime.strptime(p["date"], "%Y-%m-%d") for p in pnl_series]
        values = [p["pnl_pct"] for p in pnl_series]

        fig, ax = plt.subplots(figsize=(6.8, 2.4))
        fig.patch.set_facecolor("white")
        ax.set_facecolor("#fafafa")

        # Fill positive / negative areas
        ax.fill_between(
            dates, values, 0,
            where=[v >= 0 for v in values],
            alpha=0.25, color=_GREEN_HEX, interpolate=True,
        )
        ax.fill_between(
            dates, values, 0,
            where=[v < 0 for v in values],
            alpha=0.25, color=_RED_HEX, interpolate=True,
        )

        # Main line
        line_color = _GREEN_HEX if values[-1] >= 0 else _RED_HEX
        ax.plot(dates, values, color=line_color, linewidth=1.8, zorder=3)

        # Zero baseline
        ax.axhline(0, color="#bbbbbb", linewidth=0.6, linestyle="--")

        # Final value label
        ax.annotate(
            f"{values[-1]:+.2f}%",
            xy=(dates[-1], values[-1]),
            fontsize=8,
            color=line_color,
            fontweight="bold",
            ha="right",
            va="bottom" if values[-1] >= 0 else "top",
        )

        # Formatting
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
        ax.tick_params(axis="x", labelsize=7, rotation=0)
        ax.tick_params(axis="y", labelsize=7)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:+.1f}%"))
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color("#dddddd")
        ax.spines["bottom"].set_color("#dddddd")
        ax.set_title(
            "Weekly Portfolio P&L", fontsize=9,
            color="#555", pad=6, loc="left",
        )

        plt.tight_layout(pad=0.5)
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=150, bbox_inches="tight")
        plt.close(fig)
        return buf.getvalue()

    except Exception as e:
        logger.warning(f"Chart build failed: {e}")
        return None


# ── 5. PDF builder ────────────────────────────────────────────────────────────

def build_pdf(
    report_data: dict,
    news_map: dict[str, list[dict]],
    market_news: list[dict],
    ai_commentary: str,
) -> bytes:
    """
    Assembles all sections into a PDF and returns raw bytes.
    """
    buffer = io.BytesIO()
    doc    = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=18*mm, leftMargin=18*mm,
        topMargin=18*mm, bottomMargin=18*mm,
    )
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontSize=20,
        textColor=_DARK,
        spaceAfter=2,
    )
    h2_style = ParagraphStyle(
        "H2Custom",
        parent=styles["Heading2"],
        fontSize=12,
        textColor=_DARK,
        spaceBefore=8,
        spaceAfter=4,
        borderPad=0,
    )
    h3_style = ParagraphStyle(
        "H3Custom",
        parent=styles["Heading3"],
        fontSize=10,
        textColor=colors.HexColor("#333333"),
        spaceBefore=5,
        spaceAfter=2,
    )
    body_style = ParagraphStyle(
        "BodyCustom",
        parent=styles["Normal"],
        fontSize=9,
        leading=14,
        textColor=colors.HexColor("#333333"),
    )
    muted_style = ParagraphStyle(
        "Muted",
        parent=body_style,
        textColor=_GREY,
        fontSize=8,
    )
    link_style = ParagraphStyle(
        "LinkStyle",
        parent=body_style,
        fontSize=8,
        textColor=colors.HexColor(_TEAL_HEX),
    )
    disclaimer_style = ParagraphStyle(
        "Disclaimer",
        parent=styles["Italic"],
        fontSize=7.5,
        textColor=_GREY,
        leading=11,
    )

    story = []

    # ── SECTION 1: Header ─────────────────────────────────────────────────────
    story.append(Paragraph("Portfolio Weekly Report", title_style))
    story.append(Paragraph(
        f"Generated: {report_data['generated_at']}",
        muted_style,
    ))
    story.append(Spacer(1, 2*mm))
    story.append(HRFlowable(
        width="100%", thickness=1.5,
        color=_TEAL, spaceAfter=3*mm,
    ))

    # ── SECTION 2: Portfolio Summary ─────────────────────────────────────────
    story.append(Paragraph("Portfolio Summary", h2_style))

    pnl_sign  = "+" if report_data["total_pnl"] >= 0 else ""
    pnl_color = _GREEN_HEX if report_data["total_pnl"] >= 0 else _RED_HEX

    summary_data = [
        ["Total Value",  f"${report_data['total_val']:,.2f}"],
        ["Cost Basis",   f"${report_data['total_cost']:,.2f}"],
        ["Unrealised P&L",
         f'<font color="{pnl_color}">'
         f'{pnl_sign}${abs(report_data["total_pnl"]):,.2f} '
         f'({pnl_sign}{report_data["pnl_pct"]:.2f}%)'
         f'</font>'],
        ["Annual Dividends",
         f"${report_data['annual_div']:,.2f} "
         f"({report_data['port_yield']:.2f}% yield)"],
        ["Top Performer",
         f"{report_data['top_performer']['ticker']} "
         f'<font color="{_GREEN_HEX}">'
         f"({report_data['top_performer']['pnl_pct']:+.2f}%)"
         f"</font>"],
        ["Worst Performer",
         f"{report_data['worst_performer']['ticker']} "
         f'<font color="{_RED_HEX}">'
         f"({report_data['worst_performer']['pnl_pct']:+.2f}%)"
         f"</font>"],
    ]

    summary_rows = []
    label_style = ParagraphStyle("SL", parent=body_style,
                                 fontName="Helvetica-Bold", fontSize=8)
    value_style = ParagraphStyle("SV", parent=body_style, fontSize=8)

    for label, value in summary_data:
        summary_rows.append([
            Paragraph(label, label_style),
            Paragraph(value, value_style),
        ])

    summary_table = Table(
        summary_rows,
        colWidths=[55*mm, 100*mm],
    )
    summary_table.setStyle(TableStyle([
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",  (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1),
         [_WHITE, _LIGHT_ROW]),
        ("LINEBELOW",   (0, 0), (-1, -2),
         0.25, colors.HexColor("#e0e0e0")),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 4*mm))

    # ── SECTION 3: P&L Chart ─────────────────────────────────────────────────
    pnl_series = report_data.get("pnl_series", [])
    chart_bytes = _build_pnl_chart_image(pnl_series)
    if chart_bytes:
        story.append(Paragraph("Weekly P&L Performance", h2_style))
        chart_buf = io.BytesIO(chart_bytes)
        chart_img = Image(chart_buf, width=168*mm, height=58*mm)
        story.append(chart_img)
        story.append(Spacer(1, 4*mm))

    # ── SECTION 4: Holdings Table ─────────────────────────────────────────────
    story.append(Paragraph("Holdings Breakdown", h2_style))

    col_w = [18*mm, 17*mm, 22*mm, 17*mm, 30*mm, 20*mm, 18*mm, 12*mm]
    headers = ["Ticker", "Weight", "Value", "P&L",
               "RSI", "MACD", "Div Yield", "Day Chg"]

    cell_style = ParagraphStyle("Cell", parent=body_style,
                                fontSize=7.5, leading=10)
    hdr_style  = ParagraphStyle("Hdr",  parent=cell_style,
                                fontName="Helvetica-Bold",
                                textColor=_WHITE)

    table_data = [[Paragraph(h, hdr_style) for h in headers]]

    for h in report_data.get("holdings_data", []):
        pnl_s   = "+" if h["pnl_pct"] >= 0 else ""
        pnl_c   = _GREEN_HEX if h["pnl_pct"] >= 0 else _RED_HEX
        day_s   = "+" if h["day_chg_pct"] >= 0 else ""
        day_c   = _GREEN_HEX if h["day_chg_pct"] >= 0 else _RED_HEX
        rsi_c   = (
            _GREEN_HEX if h["rsi_label"] == "Oversold"
            else _RED_HEX if h["rsi_label"] == "Overbought"
            else "#333333"
        )
        macd_c  = _GREEN_HEX if h["macd_label"] == "Bullish" else _RED_HEX

        table_data.append([
            Paragraph(h["ticker"], cell_style),
            Paragraph(f"{h['weight']:.1f}%", cell_style),
            Paragraph(f"${h['mkt_value']:,.0f}", cell_style),
            Paragraph(
                f'<font color="{pnl_c}">{pnl_s}{h["pnl_pct"]:.1f}%</font>',
                cell_style,
            ),
            Paragraph(
                f'<font color="{rsi_c}">{h["rsi"]:.0f} ({h["rsi_label"]})</font>',
                cell_style,
            ),
            Paragraph(
                f'<font color="{macd_c}">{h["macd_label"]}</font>',
                cell_style,
            ),
            Paragraph(f"{h['div_yield']:.2f}%", cell_style),
            Paragraph(
                f'<font color="{day_c}">{day_s}{h["day_chg_pct"]:.1f}%</font>',
                cell_style,
            ),
        ])

    holdings_table = Table(table_data, colWidths=col_w, repeatRows=1)
    holdings_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  _DARK),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  _WHITE),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 7.5),
        ("GRID",          (0, 0), (-1, -1), 0.25, colors.HexColor("#dddddd")),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [_WHITE, _LIGHT_ROW]),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",         (1, 0), (-1, -1), "CENTER"),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW",     (0, 0), (-1, 0),  1, _TEAL),
    ]))
    story.append(holdings_table)
    story.append(Spacer(1, 4*mm))

    # ── SECTION 5: Dividend Calendar ─────────────────────────────────────────
    story.append(Paragraph("Upcoming Dividends (Next 30 Days)", h2_style))
    upcoming = report_data.get("upcoming_dividends", [])
    if upcoming:
        div_headers = ["Ticker", "Ex-Date", "Pay Date", "Per Share"]
        div_col_w   = [35*mm, 45*mm, 45*mm, 35*mm]
        div_data    = [[Paragraph(h, hdr_style) for h in div_headers]]
        for d in upcoming:
            div_data.append([
                Paragraph(d["ticker"], cell_style),
                Paragraph(d["ex_date"], cell_style),
                Paragraph(d.get("pay_date", "TBC"), cell_style),
                Paragraph(f"${d['amount']:.4f}", cell_style),
            ])
        div_table = Table(div_data, colWidths=div_col_w, repeatRows=1)
        div_table.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0), _DARK),
            ("GRID",          (0, 0), (-1, -1), 0.25, colors.HexColor("#dddddd")),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [_WHITE, _LIGHT_ROW]),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN",         (1, 0), (-1, -1), "CENTER"),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LINEBELOW",     (0, 0), (-1, 0), 1, _TEAL),
        ]))
        story.append(div_table)
    else:
        story.append(Paragraph(
            "No dividend payments expected in the next 30 days.",
            muted_style,
        ))
    story.append(Spacer(1, 4*mm))

    # ── SECTION 6: AI Commentary ──────────────────────────────────────────────
    story.append(KeepTogether([
        Paragraph("Weekly Market Commentary", h2_style),
        Paragraph(ai_commentary, body_style),
    ]))
    story.append(Spacer(1, 4*mm))

    # ── SECTION 7: News Per Holding ───────────────────────────────────────────
    story.append(Paragraph("Recent News by Holding", h2_style))
    for ticker, articles in news_map.items():
        if not articles:
            continue
        story.append(Paragraph(ticker, h3_style))
        for a in articles:
            title = a.get("title", "")
            url   = a.get("url", "")
            body  = a.get("body", "")
            if title and url:
                story.append(Paragraph(
                    f'<link href="{url}" color="{_TEAL_HEX}">'
                    f'<b>{title}</b></link>',
                    link_style,
                ))
            if body:
                story.append(Paragraph(body, muted_style))
            story.append(Spacer(1, 1.5*mm))
    story.append(Spacer(1, 4*mm))

    # ── SECTION 8: General Market News & Stocks to Watch ─────────────────────
    if market_news:
        story.append(Paragraph(
            "ASX Market News & Stocks to Watch", h2_style,
        ))
        for item in market_news:
            title = item.get("title", "")
            url   = item.get("url", "")
            body  = item.get("body", "")
            if title and url:
                story.append(Paragraph(
                    f'<link href="{url}" color="{_TEAL_HEX}">'
                    f'<b>{title}</b></link>',
                    link_style,
                ))
            if body:
                story.append(Paragraph(body, muted_style))
            story.append(Spacer(1, 2*mm))
        story.append(Spacer(1, 2*mm))

    # ── SECTION 9: Disclaimer ─────────────────────────────────────────────────
    story.append(HRFlowable(
        width="100%", thickness=0.5,
        color=_GREY, spaceBefore=4*mm, spaceAfter=2*mm,
    ))
    story.append(Paragraph(
        "Disclaimer: This report is automatically generated for personal "
        "use only and does not constitute financial advice. Data is sourced "
        "from Yahoo Finance and public web sources. Always verify with a "
        "licensed financial adviser before making investment decisions. "
        "Past performance is not indicative of future results.",
        disclaimer_style,
    ))

    doc.build(story)
    return buffer.getvalue()


# ── 6. Orchestrator ───────────────────────────────────────────────────────────

def generate_weekly_report(
    portfolio_data: dict,
    api_key: str,
) -> bytes:
    """
    Orchestrates all steps and returns PDF bytes.
    """
    logger.info("Starting weekly report generation")

    report_data = gather_report_data(portfolio_data)
    if not report_data:
        raise ValueError("Could not gather portfolio data for report")

    holdings   = report_data.get("holdings_data", [])
    news_map   = fetch_news_for_holdings(holdings)
    logger.info(f"Fetched news for {len(news_map)} holdings")

    market_news = fetch_market_news()
    logger.info(f"Fetched {len(market_news)} general market news items")

    ai_commentary = get_ai_commentary(
        report_data, news_map, market_news, api_key,
    )
    logger.info("AI commentary generated")

    pdf_bytes = build_pdf(
        report_data, news_map, market_news, ai_commentary,
    )
    logger.info(f"PDF built: {len(pdf_bytes):,} bytes")

    return pdf_bytes
