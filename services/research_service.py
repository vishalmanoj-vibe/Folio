import os
import logging
import copy
import google.genai as genai
from services.technical_indicators import (
    compute_signals
)
from services.web_search import (
    search_financial_news,
    format_search_results,
    should_search_web
)

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
    
    lines = [f"=== PORTFOLIO SNAPSHOT (Live as at {fetched_at}) ==="]
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
        
        lines.append(f"{t} — {name}  {weight:.1f}%  |  yield {div_yield:.1f}%  |  P&L {pnl_pct:+.1f}%")
        
    # Add technical signals for each holding
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
                f"  {ticker_h}: RSI={sig['rsi']:.0f} "
                f"({sig['rsi_label']}), "
                f"MACD={sig['macd_label']}, "
                f"Bollinger={sig['bb_label']}"
            )
    
    if sig_lines:
        lines.append("\nTechnical Signals (from price history):")
        lines.extend(sig_lines)
        lines.append("")
        
    if ticker:
        lines.append(f"=== TICKER USER IS CONSIDERING BUYING: {ticker.upper()} ===")
        lines.append("This ticker is NOT currently in the user's portfolio.")
        lines.append("The user wants to know if it would be a good addition to their existing holdings shown above.")
        lines.append("Evaluate fit based on: sector overlap, geographic overlap, yield impact, diversification benefit, and risk profile.")
        
    context = "\n".join(lines)
    logger.info(f"Generated portfolio context (length {len(context)}): {context[:200]}...")
    return context


def get_ai_response(history: list[dict], portfolio_data: dict,
                    ticker: str = "") -> str:
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
            if ticker:
                search_query = (
                    f"{ticker} ASX {search_query}"
                )
            
            results = search_financial_news(
                search_query, max_results=3
            )
            search_context = format_search_results(
                results
            )
            if search_context:
                logger.info(
                    f"Web search added: "
                    f"{len(results)} results"
                )
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
            full_context += (
                "\n\n" + search_context
            )
        full_message = full_context + "\n\n" + current_message

        # Convert past turns to google-genai Content objects
        # google-genai uses "model" not "assistant" for AI role
        chat_history = []
        for msg in past_turns:
            role = "model" if msg["role"] == "assistant" else "user"
            chat_history.append(
                genai.types.Content(
                    role=role,
                    parts=[genai.types.Part(text=msg["content"])]
                )
            )

        # Create chat session with history
        chat = client.chats.create(
            model="models/gemini-2.5-flash-lite",
            history=chat_history,
            config=genai.types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=2048,
            )
        )

        # Send the current message with context prepended
        response = chat.send_message(full_message)
        return response.text

    except Exception as e:
        logger.error(f"Error calling Gemini: {e}")
        return "I couldn't reach the AI service. Please check your API key and try again."
