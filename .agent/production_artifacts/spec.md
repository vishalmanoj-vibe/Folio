# Spec: Watchlist Feature

## Summary
Add a new 'Watchlist' page to the portfolio dashboard. Users can add tickers they are interested in, view live pricing, and track performance before committing to a purchase. The data will be persisted in a `watchlist.csv` file.

## Components & IDs
All new IDs will follow the `watchlist-` namespace pattern.

### Global Store
- `watchlist-store`: Holds the list of tickers in the watchlist and their live data.

### Page Components (pages/watchlist.py)
- `watchlist-input`: Text input for adding a new ticker.
- `watchlist-add-btn`: Button to add the ticker.
- `watchlist-table`: Table showing watchlist tickers, current price, day change, and a remove button.
- `watchlist-msg`: Status message for add/remove actions.
- `watchlist-chart`: Price history chart for the selected watchlist ticker.

## Data Strategy
1. **Storage**: `data/raw/watchlist.csv` with columns: `ticker`, `added_date`.
2. **Persistence**: `WatchlistRepository` in `data/watchlist_repository.py`.
3. **Live Data**: Fetch live data using `services/market/data_fetcher.py`.
4. **State Management**: `watchlist-store` in `app.py` to keep data synchronized across navigation.

## Modified Files
- `config/settings.py`: Define `WATCHLIST_CSV_PATH`.
- `app.py`: Seed `watchlist-store`, register `watchlist_callbacks`.
- `components/header.py`: Add "Watchlist" link to navigation.
- `.agents/skills/registry.md`: Register new IDs.

## New Files
- `pages/watchlist.py`: Page definition.
- `components/watchlist_layout.py`: Layout components.
- `callbacks/watchlist_callbacks.py`: Callback logic.
- `data/watchlist_repository.py`: CSV interaction layer.
- `data/raw/watchlist.csv`: Initial empty CSV.

## Design
- Follow **Aura Design System** (high-density, dark mode, glassmorphism).
- Use `create_header` for consistency.
- Use `var(--t-pri)`, `var(--t-sec)`, etc., for styling.
