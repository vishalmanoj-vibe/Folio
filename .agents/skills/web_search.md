# Skill: Live Web Search Integration

## Objective
Supplement AI research with real-time financial news and announcements using DuckDuckGo.

## Core Components
- **`services/web_search.py`**: The engine layer.
  - `search_financial_news(query)`: Uses `ddgs` package to fetch recent AU financial news.
  - `should_search_web(message)`: Keyword-based classifier (e.g., "latest", "dividend", "announcement").
  - `format_search_results(results)`: Converts result dicts into context-ready strings.
- **`services/research_service.py`**: The orchestration layer.
  - Injects search context into the Gemini prompt alongside portfolio data.
- **`callbacks/research_callbacks.py`**: The presentation layer.
  - Displays the `🔍 Web search used` indicator in the chat bubble.

## Maintenance & Patterns
1. **Keyword Accuracy**: If the AI fails to trigger search for a specific term (e.g., "earnings"), add it to the `keywords` list in `should_search_web()`.
2. **Query Refinement**: Ensure the search query includes the ticker context if available (e.g., `f"{ticker} ASX {user_message}"`) to avoid generic results.
3. **Region Pinning**: Always use `region="au-en"` and `timelimit="m"` for ASX relevance and freshness.
4. **Error Handling**: `DDGS` calls must be wrapped in `try/except`. If search fails, the assistant should gracefully fall back to portfolio data only.
5. **Positional Arguments**: In the `ddgs` library, the `text()` method requires the search string as a positional argument (`query`), not a keyword argument (`keywords=...`).

## Verification
- Test with queries like: "What are the latest dividend announcements for VHY?" or "Any recent news for VAS?".
- Confirm the 🔍 indicator appears in the UI.
