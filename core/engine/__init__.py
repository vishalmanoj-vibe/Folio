# core/engine/__init__.py
"""
core/engine
===========
Portfolio computation engine — pure Python, no Dash, no network calls.
"""

from core.engine.portfolio_engine import (
    aggregate_shares,
    build_holdings,
    build_tranches,
    compute_holding_pnl,
    compute_tranche_pnl,
)

__all__ = [
    "build_holdings",
    "compute_tranche_pnl",
    "compute_holding_pnl",
    "aggregate_shares",
    "build_tranches",
]
