import logging

logger = logging.getLogger(__name__)

# Module-level cache for price histories
_CACHE = {}
_LATEST = None

def set_histories(sig: str, histories: dict) -> None:
    """
    Stores the price histories dict in the server-side cache.
    
    Args:
        sig: A unique signature string for the holdings (tickers + shares).
        histories: The dictionary of price histories keyed by ticker.
    """
    global _LATEST
    if not histories:
        logger.debug("Skipping empty histories cache update")
        return
        
    _CACHE[sig] = histories
    _LATEST = histories
    logger.debug(f"Histories cached for signature: {sig[:20]}...")

def get_histories(sig: str) -> dict | None:
    """
    Retrieves histories for a specific holdings signature.
    """
    return _CACHE.get(sig)

def get_latest_histories() -> dict:
    """
    Returns the most recently stored histories dict.
    Returns an empty dict if no histories are cached.
    """
    return _LATEST if _LATEST is not None else {}
