import logging

logger = logging.getLogger(__name__)

# Module-level cache for price histories
# We only keep the latest version to prevent memory leaks from signature churn.
_LATEST_HISTORIES = {}
_LATEST_SIG = None

def set_histories(sig: str, histories: dict) -> None:
    """
    Stores the price histories dict in the server-side cache.
    Replaces the previous entry to prevent memory growth.
    """
    global _LATEST_HISTORIES, _LATEST_SIG
    if not histories:
        logger.debug("Skipping empty histories cache update")
        return
        
    _LATEST_HISTORIES = histories
    _LATEST_SIG = sig
    logger.debug(f"Histories cached for signature: {sig[:20]}...")

def get_histories(sig: str) -> dict | None:
    """
    Retrieves histories if the signature matches the latest cached one.
    """
    if sig == _LATEST_SIG:
        return _LATEST_HISTORIES
    return None

def get_latest_histories() -> dict:
    """
    Returns the most recently stored histories dict.
    """
    return _LATEST_HISTORIES
