"""
data/portfolio_builder.py
=========================
Thin shim — all portfolio computation has moved to core/engine/portfolio_engine.py.

This file is kept so that all existing import paths continue to work unchanged:
    from data.portfolio_builder import build_holdings, validate_transaction

The name-resolution improvement (get_etf_name) lives in services/market/data_fetcher.py
and is still applied at enrich-time in fetch_live(), not here, to keep this
module free of network calls.
"""

from core.engine.portfolio_engine import build_holdings  # noqa: F401  (re-export)
from core.validators import validate_transaction          # noqa: F401  (re-export)

__all__ = ["build_holdings", "validate_transaction"]