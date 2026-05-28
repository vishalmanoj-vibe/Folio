# History Cache — DEPRECATED (Moved to SQLite for memory hygiene)
_LATEST_SIG = None


def set_histories(sig: str, histories: dict) -> None:
    # We no longer store histories in RAM. SQLite is fast enough.
    global _LATEST_SIG
    _LATEST_SIG = sig


def get_histories(sig: str) -> dict | None:
    # Always return None to force a fetch from SQLite
    return None


def get_latest_histories() -> dict:
    # Return empty dict; downstream will fetch from SQLite
    return {}
