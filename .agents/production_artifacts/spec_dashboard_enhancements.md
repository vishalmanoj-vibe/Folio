# Feature Spec: New Dashboard Enhancements

## Goal
Implement a suite of new dashboard enhancements, adapting them to our Dash/Python/SQLite/Gemini stack:
1. **Dynamic Ticker-Aware Command Palette**: Upgrade the CMD+K search modal with dynamic holdings/watchlist ticker grouping and active technical/AI strategy signal indicators.
2. **Portfolio Day-Change Heatmap**: Add a "Day Change" option to the allocation treemap chart to color-code assets by daily percentage change.
3. **Investor Profile Settings Page**: Create a new `/settings` route allowing the user to select their goal, risk tolerance, and tax bracket, which dynamically adjusts weights in technical signal computations and AI assistant responses.
4. **News Sentiment Score Overlay**: Pull recent news via DDGS news search, score sentiment via Gemini, cache results in SQLite, and display sentiment metrics on the Portfolio and Watchlist grids.

## Stack & Technologies
- Dash/Plotly Python callbacks
- SQLite (`user_settings` and `sentiment_cache` tables)
- Google Gemini API (`models/gemini-3.1-flash-lite`)
- DuckDuckGo Search API (`services/web_search.py`)
- Clientside JavaScript (`assets/command_palette.js` and `callbacks/ui_callbacks.py`)

## Key Component/Store IDs
- `palette-ticker-store`: Clientside memory store containing tickers, groups (holdings/watchlist), P&L, and signals.
- `user_settings`: SQLite table for persisting keys: `investment_goal`, `risk_tolerance`, `tax_bracket`.
- `sentiment_cache`: SQLite cache table storing ticker sentiment, scores (-1.0 to 1.0), headlines, and timestamps.
- `settings-investment-goal`, `settings-risk-tolerance`, `settings-tax-bracket`: Dropdown inputs on `/settings` page.

## Proposed Changes

### [Database] [database.py](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/data/database.py)
- Create `user_settings` and `sentiment_cache` tables during database initialization.

### [Repository] [settings_repository.py](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/data/settings_repository.py) [NEW]
- Define `get_all_settings()`, `get_setting()`, `save_setting()`, `save_all_settings()`.

### [Services] [sentiment_service.py](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/services/sentiment_service.py) [NEW]
- DDGS news fetcher + Gemini analyzer + SQLite caching.

### [Strategy Engine] [strategy_engine.py](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/services/strategy_engine.py)
- Read profile goal/risk settings from database and adjust technical indicator strategy weights.

### [Settings Page] [settings.py](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/pages/settings.py) [NEW]
- Setup UI layout under `/settings` with profile selection dropdowns and strategy weight previews.

### [Settings Callbacks] [settings_callbacks.py](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/callbacks/settings_callbacks.py) [NEW]
- Handle settings loading, dynamic weights preview bar rendering, and settings saving.

### [UI Callbacks] [ui_callbacks.py](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/callbacks/ui_callbacks.py)
- Add clientside callback to populate `palette-ticker-store`.

### [Grids] [portfolio_callbacks.py](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/callbacks/portfolio_callbacks.py) & [watchlist_callbacks.py](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/callbacks/watchlist_callbacks.py)
- Add "Sentiment" column to both tables, displaying colored Positive/Neutral/Negative ratings and scores.

## Acceptance Criteria
- Run `ruff check` and `ruff format` on all updated/new files successfully.
- Pytest suite executes successfully with 61/61 passing tests.
- App starts up without errors and handles navigation, settings updates, and search seamlessly.
