"""
core/engine
===========
Portfolio computation engine — pure Python, no Dash, no network calls.
"""

from core.engine.portfolio_engine import (
    build_holdings,
    compute_tranche_pnl,
    compute_holding_pnl,
    aggregate_shares,
    build_tranches,
)

__all__ = [
    "build_holdings",
    "compute_tranche_pnl",
    "compute_holding_pnl",
    "aggregate_shares",
    "build_tranches",
]