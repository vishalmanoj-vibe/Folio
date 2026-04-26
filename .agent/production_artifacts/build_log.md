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

---

# Cross-Verification Audit — 2026-04-26

**Auditor**: @agent-qa

### Scope
Verified all fixes applied in Tiers 1, 2, and 3 to ensure root causes were addressed, no regressions were introduced, callback wiring remained intact, and the registry was updated. Ran stability audit checks.

### Tier 1 Checks
- **transaction_callbacks.py** (Line 117) - `allow_duplicate=True` added to `txn-msg`. **[PASS]**
- **pages/portfolio.py** (Line 20) - `layout = create_layout()` refactored to `def layout():`. **[PASS]**
- **services/market/data_fetcher.py** (Line 372) - Zero-price fallback implemented. **[PASS]**
- **callbacks/positions_callbacks.py** (Line 181) - Synchronous `yf.Ticker` replaced with `portfolio-store` history extraction. **[PASS]**
- **services/market/data_fetcher.py** (Line 20) - Share count signatures added to cache key. **[PASS]**
- **data/watchlist_repository.py** (Line 150) - Sequential looping replaced with bulk `yf.download`. **[PASS]**

### Tier 2 Checks
- **callbacks/chart_callbacks.py** - `period-store` converted to `State()`. **[PASS]**
- **app.py** - Circular initialization sync loops commented out. **[PASS]**
- **callbacks/positions_callbacks.py & app.py** - Ghost click protections added (`int(ctx.triggered[0]["value"]) < 1`). **[PASS]**
- **services/research_service.py** - Context injection truncated to top 20 holdings by weight. **[PASS]**
- **assets/view-pages.css** - `@media` query added for `.research-layout` mobile stacking. **[PASS]**
- **callbacks/portfolio_callbacks.py, intelligence_callbacks.py, dividend_callbacks.py, positions_callbacks.py** - Added pathname guards to prevent global recalculations. **[FAIL]**

### Tier 3 Checks
- **callbacks/transaction_callbacks.py** - Hex colors removed. **[PASS]**
- **callbacks/alert_callbacks.py** - Hex colors removed. **[PASS]**
- **callbacks/dividend_callbacks.py** - Hex colors removed. **[PASS]**
- **assets/base-reset.css** - Hex colors removed. **[PASS]**
- **pages/positions.py** - `chart_title()` helper implemented correctly. **[PASS]**
- **registry.md** - Pruned orphans and registered missing component IDs. **[PASS]**

### Failed Fixes Analysis
**Tier 2 Fix 2 (Pathname Guards): [FAIL]**
*Description of failure*: The implementation used `State("url", "pathname")` combined with `prevent_initial_call=True` on page-specific callbacks. In a Dash multi-page architecture, when a user navigates to a page, the components are dynamically mounted. Because `prevent_initial_call=True` is set, Dash suppresses the callback upon this initial mount. Since the `url` is a `State` rather than an `Input`, navigation does not trigger an update. The pages will render entirely blank until the background `live-interval` ticks and forces a `portfolio-store` update (which can take up to 30 seconds).

*Required Resolution*: To properly guard these callbacks without breaking navigation renders, `url` must be passed as an `Input("url", "pathname")` rather than a `State`, and `prevent_initial_call` should ideally be disabled (`False`) or evaluated carefully. This ensures that the act of navigating triggers the callback to populate the newly mounted layout, while the `url_pathname != "/page"` guard still successfully blocks background `portfolio-store` updates from firing when the user is on a different page.
