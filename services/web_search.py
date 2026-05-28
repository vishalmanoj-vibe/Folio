import logging

from ddgs import DDGS

logger = logging.getLogger(__name__)


def search_financial_news(query: str, max_results: int = 3) -> list[dict]:
    """
    Search for recent financial news using DuckDuckGo.
    """
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, region="au-en", timelimit="m", max_results=max_results)

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
        "news",
        "announcement",
        "announced",
        "today",
        "latest",
        "recent",
        "asx",
        "dividend",
        "report",
        "results",
        "price",
        "forecast",
        "prediction",
        "analyst",
        "rating",
        "buy",
        "sell",
        "upgrade",
        "downgrade",
        "merge",
        "acquisition",
        "outlook",
    ]
    message_lower = message.lower()
    return any(kw in message_lower for kw in keywords)
