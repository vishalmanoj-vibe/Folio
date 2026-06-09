import logging

from ddgs import DDGS

logger = logging.getLogger(__name__)


def search_financial_news(query: str, max_results: int = 3, timelimit: str = "w") -> list[dict]:
    """
    Search for recent financial news using DuckDuckGo.
    Uses progressive timelimit fallbacks to ensure fresh results first, with guarantee of returning data.
    """
    try:
        with DDGS() as ddgs:
            # 1. Try with the requested timelimit (default 'w' / weekly)
            results = list(
                ddgs.text(query, region="au-en", timelimit=timelimit, max_results=max_results)
            )

            # 2. If no results, try fallback timelimit (weekly or monthly)
            if not results and timelimit in ["d", "w"]:
                next_limit = "w" if timelimit == "d" else "m"
                results = list(
                    ddgs.text(query, region="au-en", timelimit=next_limit, max_results=max_results)
                )

            # 3. Final absolute fallback without time restriction
            if not results:
                results = list(ddgs.text(query, region="au-en", max_results=max_results))

            # Ensure each dict has the required keys and return as a list
            search_data = []
            for r in results:
                search_data.append(
                    {
                        "title": r.get("title", ""),
                        "href": r.get("href", ""),
                        "body": r.get("body", ""),
                    }
                )
            return search_data

    except Exception as e:
        logger.error(f"Error searching DuckDuckGo for '{query}': {e}")
        return []


def format_search_results(results: list[dict]) -> str:
    """
    Format search results into a readable string.
    """
    if not results:
        return ""

    output = "Recent web results:\n"
    for result in results:
        output += f"- {result['title']}: {result['body'][:200]}\n"

    return output


def should_search_web(message: str) -> bool:
    """
    Checks if the user message is asking about something that needs live web data.
    """
    keywords = [
        # Live market events
        "news",
        "announcement",
        "announced",
        "today",
        "latest",
        "recent",
        # ASX-specific
        "asx",
        "asx 200",
        # Corporate actions
        "dividend",
        "report",
        "results",
        "earnings",
        "guidance",
        "merger",
        "acquisition",
        "merge",
        "ipo",
        "listing",
        # Price & analyst
        "price",
        "forecast",
        "prediction",
        "analyst",
        "rating",
        "buy",
        "sell",
        "upgrade",
        "downgrade",
        "target",
        # Macro / policy
        "rba",
        "interest rate",
        "rate cut",
        "rate hike",
        "cpi",
        "inflation",
        "gdp",
        "unemployment",
        "recession",
        "macro",
        "federal reserve",
        "fed",
        # Funds & sectors
        "etf",
        "sector",
        "watchlist",
        "outlook",
    ]
    message_lower = message.lower()
    return any(kw in message_lower for kw in keywords)
