# Build Log: Watchlist Feature

## New IDs Registered
- `watchlist-store`: Global data store.
- `watchlist-input`: Ticker search.
- `watchlist-add-btn`: Addition trigger.
- `watchlist-table`: Main data view.
- `watchlist-msg`: Feedback.
- `watchlist-chart`: Visual analysis.

## Files Changed
- `app.py`: Global state and callback registration.
- `config/settings.py`: Path definitions.
- `components/header.py`: Navigation update.
- `.agents/skills/registry.md`: ID documentation.

## New Files Created
- `pages/watchlist.py`: Page entry.
- `components/watchlist_layout.py`: Aura UI layout.
- `callbacks/watchlist_callbacks.py`: Interactivity logic.
- `data/watchlist_repository.py`: CSV data layer.
- `data/raw/watchlist.csv`: Persistent storage.

## Stability Check
- `prevent_initial_call=True` implemented in `watchlist_callbacks.py`.
- Seeding `watchlist-store` in `app.py` for instant load.

---

# Build Log: Research Assistant Feature

## New IDs Registered
- `research-chat-store`: Conversation history.
- `research-ticker-store`: Ticker being researched.
- `research-portfolio-summary`: Live holdings display.
- `research-chat-display`: Chat message area.
- `research-ticker-input`: Free-text ticker input.
- `research-input`: Chat message text input.
- `research-send-btn`: Message send button.
- `research-disclaimer`: Static disclaimer text.
- `qp-1` through `qp-4`: Quick prompt chips.

## Files Changed
- `app.py`: Added research stores and callback registration.
- `components/header.py`: Added Research nav link.
- `assets/view-pages.css`: Added Research Assistant CSS classes.
- `.agents/skills/registry.md`: Added Research Assistant ID documentation.

## New Files Created
- `pages/research.py`: Research page layout.
- `callbacks/research_callbacks.py`: Interactivity logic and chat state management.
- `services/research_service.py`: Gemini API integration and prompt context building.

## Stability Check
- `prevent_initial_call=True` implemented in `research_callbacks.py`.
- No ID namespace collisions with existing pages.
- Fallback logic integrated for Gemini API errors.
