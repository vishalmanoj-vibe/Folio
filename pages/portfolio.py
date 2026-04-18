"""
pages/portfolio.py
==================
Dash Pages wrapper for the existing portfolio dashboard.
Route: /

Layout is delegated entirely to components/portfolio_layout.py — nothing new here.
Stores, Interval, and all callbacks are registered in app.py.
"""

import dash
from components.portfolio_layout import create_layout

dash.register_page(__name__, path="/", title="Portfolio — Live P&L")

# Dash Pages calls `layout` (or `layout()`) when the page is rendered.
# We call create_layout() without initial_history because txn-store is
# already seeded from app.layout.
layout = create_layout()