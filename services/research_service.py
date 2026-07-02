import copy
import logging
import os

import google.genai as genai
import pandas as pd

from config.settings import GEMINI_FLASH_MODEL
from services.technical_indicators import compute_signals
from services.web_search import format_search_results, search_financial_news, should_search_web

logger = logging.getLogger(__name__)

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    logger.warning("GEMINI_API_KEY is missing from environment variables.")

SYSTEM_PROMPT = """You are an Australian ASX ETF investment research assistant.
Always reason from the portfolio data provided in each message.
Never fabricate price data, yields, or returns.
Keep responses to 3-4 paragraphs unless asked for more.
End every response with: "Note: This is not financial advice."
Be specific to the user's portfolio, not generic.
When a ticker is listed under "TICKER USER IS CONSIDERING BUYING", treat it as a prospective purchase the user wants evaluated against their existing portfolio — not as a current holding."""


def build_portfolio_context(portfolio_data: dict, ticker: str = "") -> str:
    if not portfolio_data or "holdings" not in portfolio_data or not portfolio_data["holdings"]:
        return "Portfolio data is not yet loaded."

    holdings = portfolio_data["holdings"]
    fetched_at = portfolio_data.get("fetched_at", "Unknown")

    total_val = sum(float(h.get("mkt_value", 0)) for h in holdings)

    lines = []
    active_page = portfolio_data.get("active_page")
    active_ticker = portfolio_data.get("active_ticker")
    if active_page:
        lines.append("=== USER CURRENT VIEWPORT CONTEXT ===")
        lines.append(f"Current Dashboard Page: {active_page}")
        if active_ticker:
            lines.append(f"Currently Selected/Researched Ticker: {active_ticker}")
        lines.append("")

    lines.append(f"=== PORTFOLIO SNAPSHOT (Live as at {fetched_at}) ===")
    lines.append(f"Total value: ${total_val:,.0f}")

    # FIX: limit context to top 20 holdings by weight to prevent context window overflow
    sorted_holdings = sorted(holdings, key=lambda x: float(x.get("mkt_value", 0)), reverse=True)
    for h in sorted_holdings[:20]:
        t = h.get("ticker", "Unknown")
        name = h.get("name", "Unknown")
        mkt_value = float(h.get("mkt_value", 0))
        div_yield = float(h.get("div_yield", 0)) if h.get("div_yield") is not None else 0.0
        pnl_pct = float(h.get("pnl_pct", 0)) if h.get("pnl_pct") is not None else 0.0

        weight = (mkt_value / total_val * 100) if total_val > 0 else 0.0

        lines.append(
            f"{t} — {name}  {weight:.1f}%  |  yield {div_yield:.1f}%  |  P&L {pnl_pct:+.1f}%"
        )

    # Add technical signals for each holding (enriched with numerics)
    sig_lines = []
    histories = portfolio_data.get("histories", {})
    for h in sorted_holdings[:10]:
        ticker_h = h["ticker"]
        history = histories.get(ticker_h, [])
        if not history:
            continue
        sig = compute_signals(ticker_h, history)
        if "error" not in sig:
            sig_lines.append(
                f"  {ticker_h}: RSI={sig['rsi']:.0f} ({sig['rsi_label']}), "
                f"MACD={sig['macd']:.3f} vs Signal={sig['macd_signal']:.3f} ({sig['macd_label']}), "
                f"BB={sig['bb_label']} [upper={sig['bb_upper']:.2f} lower={sig['bb_lower']:.2f}], "
                f"last=${sig['last_price']:.2f}"
            )

    # ── Performance Context (7-Day) ──
    perf_lines = []
    total_7d_chg = 0.0
    valid_count = 0

    for h in sorted_holdings:
        ticker_h = h["ticker"]
        history = histories.get(ticker_h, [])
        if len(history) < 2:
            continue

        # Get price from ~7 days ago
        target_date = (pd.Timestamp.now() - pd.Timedelta(days=7)).strftime("%Y-%m-%d")
        start_price = None
        for entry in reversed(history):
            if entry["Date"] <= target_date:
                start_price = float(entry["Close"])
                break

        if not start_price:
            # Fallback to the oldest available in our 14d window
            start_price = float(history[0]["Close"])

        curr_price = float(h.get("last_price", 0))
        if start_price > 0:
            chg_pct = (curr_price - start_price) / start_price * 100
            weight = (float(h.get("mkt_value", 0)) / total_val) if total_val > 0 else 0
            total_7d_chg += chg_pct * weight
            valid_count += 1
            if weight > 0.02:  # Only list holdings > 2% weight in perf summary
                perf_lines.append(f"  {ticker_h}: {chg_pct:+.1f}%")

    if valid_count > 0:
        lines.append("\nRECENT PERFORMANCE (Estimated 7-Day Trend):")
        lines.append(f"Portfolio Total: {total_7d_chg:+.2f}%")
        if perf_lines:
            lines.extend(perf_lines[:10])  # Top 10 movers/weights
        lines.append("")

    if sig_lines:
        lines.append("Technical Signals (from price history):")
        lines.extend(sig_lines)
        lines.append("")

    # ── 52-Week Range Context ──────────────────────────────────────────────────
    range_lines = []
    for h in sorted_holdings[:10]:
        hi = h.get("week_52_high")
        lo = h.get("week_52_low")
        price = h.get("last_price")
        if hi and lo and price and float(hi) > 0:
            pct_from_high = (float(price) - float(hi)) / float(hi) * 100
            range_lines.append(
                f"  {h['ticker']}: ${float(price):.2f}  "
                f"52w High=${float(hi):.2f} ({pct_from_high:+.1f}% from high)  "
                f"52w Low=${float(lo):.2f}"
            )
    if range_lines:
        lines.append("52-Week Price Ranges:")
        lines.extend(range_lines)
        lines.append("")

    # ── News Sentiment (reads SQLite cache — zero extra API calls) ─────────────
    try:
        from services.sentiment_service import get_cached_sentiment

        sentiment_lines = []
        for h in sorted_holdings[:10]:
            cached = get_cached_sentiment(h["ticker"])
            if cached:
                sentiment_lines.append(
                    f"  {h['ticker']}: {cached['sentiment']} (score {cached['score']:+.2f}) — {cached.get('rationale', '')[:80]}"
                )
        if sentiment_lines:
            lines.append("News Sentiment (cached):")
            lines.extend(sentiment_lines)
            lines.append("")
    except Exception:
        pass  # Sentiment is best-effort — never block the context builder

    if ticker and ticker.upper() != "GENERAL":
        lines.append(f"=== TICKER USER IS CONSIDERING BUYING: {ticker.upper()} ===")
        lines.append("This ticker is NOT currently in the user's portfolio.")
        lines.append(
            "The user wants to know if it would be a good addition to their existing holdings shown above."
        )
        lines.append(
            "Evaluate fit based on: sector overlap, geographic overlap, yield impact, diversification benefit, and risk profile."
        )

    context = "\n".join(lines)
    logger.info(f"Generated portfolio context (length {len(context)}): {context[:200]}...")
    return context


def get_ai_response(history: list[dict], portfolio_data: dict, ticker: str = "") -> str:
    logger.info(
        f"get_ai_response called — "
        f"holdings: {len(portfolio_data.get('holdings', []))}, "
        f"history_len: {len(history)}"
    )
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return "API key is not configured. Please add GEMINI_API_KEY to your .env file."

        client = genai.Client(api_key=api_key)

        # Build context and inject into a copy of the last user message
        context = build_portfolio_context(portfolio_data, ticker)

        # Auto web search if message needs live data
        current_message_search = history[-1]["content"] if history else ""

        search_context = ""
        if should_search_web(current_message_search):
            # Build smart query from message + ticker
            search_query = current_message_search[:100]
            if ticker and ticker.upper() != "GENERAL":
                search_query = f"{ticker} ASX {search_query}"

            results = search_financial_news(search_query, max_results=3)
            search_context = format_search_results(results)
            if search_context:
                logger.info(f"Web search added: {len(results)} results")
        logger.info(
            f"Context length: {len(context)} chars, "
            f"History turns: {len(history)}, "
            f"Ticker: '{ticker}'"
        )

        # Separate history into past turns and current message
        if not history:
            return "No message to respond to."

        past_turns = history[:-1]
        current_message = history[-1]["content"]

        # Prepend the full portfolio context (including TA signals) to the
        # last user message. This ensures the AI reasons with fresh data
        # while keeping the actual chat history (past_turns) clean and lean.
        full_context = context
        if search_context:
            full_context += "\n\n" + search_context
        full_message = full_context + "\n\n" + current_message

        # Convert past turns to google-genai Content objects
        # google-genai uses "model" not "assistant" for AI role
        chat_history: list[genai.types.ContentOrDict] = []
        for msg in past_turns:
            role = "model" if msg["role"] == "assistant" else "user"
            chat_history.append(
                genai.types.Content(role=role, parts=[genai.types.Part(text=msg["content"])])
            )

        # Load user profile settings for customized AI context
        from data.settings_repository import get_all_settings

        settings = get_all_settings()
        goal = settings.get("investment_goal", "Balanced")
        risk = settings.get("risk_tolerance", "Moderate")
        tax = settings.get("tax_bracket", "37%")
        persona = settings.get("ai_persona", "Conservative")

        # Build persona tone instruction
        from services.ai_engine import PERSONA_PROMPTS

        persona_instruction = PERSONA_PROMPTS.get(persona, PERSONA_PROMPTS["Conservative"])

        profile_instruction = (
            f"\n\nUSER'S INVESTOR PROFILE:\n"
            f"- Investment Goal: {goal}\n"
            f"- Risk Tolerance: {risk}\n"
            f"- Tax Bracket: {tax}\n"
            f"Please customize your advice, risk evaluation, and portfolio suggestions to align with this investor profile."
        )
        system_prompt_dynamic = persona_instruction + "\n\n" + SYSTEM_PROMPT + profile_instruction

        # Resolve chat model from user settings (fallback to Flash).
        # The `or` guard narrows the type from `str | None` → `str` to satisfy the SDK.
        from data.settings_repository import get_setting

        ai_chat_model = get_setting("ai_chat_model", GEMINI_FLASH_MODEL) or GEMINI_FLASH_MODEL

        # Create chat session with history
        chat = client.chats.create(
            model=ai_chat_model,
            history=chat_history,
            config=genai.types.GenerateContentConfig(
                system_instruction=system_prompt_dynamic,
                max_output_tokens=2048,
            ),
        )

        # Send the current message with context prepended
        response = chat.send_message(full_message)
        return response.text

    except Exception as e:
        logger.error(f"Error calling Gemini: {e}")
        return "I couldn't reach the AI service. Please check your API key and try again."
