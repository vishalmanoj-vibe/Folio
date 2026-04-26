# pages/watchlist.py
"""
pages/watchlist.py
==================
Watchlist page entry.
Route: /watchlist
"""

import dash
from components.watchlist_layout import create_watchlist_layout

dash.register_page(__name__, path="/watchlist", title="Watchlist")

def layout():
    return create_watchlist_layout()
