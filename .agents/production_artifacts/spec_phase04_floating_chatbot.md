# Spec: Floating AI Chatbot Widget (Global)

## Feature Summary
Replaces the standalone AI Assistant page (`/ai-analyst`) with a globally-accessible floating chatbot widget positioned in the bottom-right corner of the dashboard viewport. The chatbot automatically extracts viewport context (active page and active selected ticker) to enrich the background AI task payload context, personalizing the chat conversation dynamically.

## Modified/New Files List
- `services/research_service.py` [MODIFY]
- `app.py` [MODIFY]
- `components/header.py` [MODIFY]
- `components/chatbot.py` [NEW]
- `callbacks/research_callbacks.py` [MODIFY]
- `assets/ui-components.css` [MODIFY]
- `pages/ai_analyst.py` [DELETE]
- `docs/guides/DEVELOPER_GUIDE.md` [MODIFY]

## Component IDs
- `chatbot-widget-root`: Container for the entire widget.
- `chatbot-trigger`: Floating button to expand/collapse the chatbot.
- `chatbot-window`: Floating chat card container.
- `chatbot-close`: Minimize/close icon.
- `chatbot-context-bar`: HTML Div displaying active page/ticker context.
- `chatbot-quick-prompts`: Quick prompts container.

## Data Strategy
- Chat conversation state is persisted in `research-chat-store` (memory, cleared on reload).
- Ticker search state is persisted in `research-ticker-store` (memory).
- Usage limits are persisted in `research-usage-store` (local storage).
- The widget reads pathname from `url` and selection states from `positions-selected-ticker`, `watchlist-selected-ticker`, and `ticker-store` to build the active context.
- Passes `active_page` and `active_ticker` within the context payload to the SQLite background task queue (`worker_tasks`).

## Resolved Pain Points
- **Preserve Conversation State**: Keeping the widget in the global layout prevents conversation state loss when changing pages (which would happen if the chat component was inside page-specific layouts).
- **Zero Latency Toggling**: A clientside callback handles toggling between expanded and collapsed states, avoiding server-side delays.
- **Dynamic Chip Hiding**: Chips specific to tickers are hidden automatically when no active ticker is selected, preserving vertical space.
- **Compact Quick Prompts**: Configured the chips with horizontal scrolling and hidden scrollbars to prevent them from taking up multiple rows in the compact layout.

## Fallback States
- If no ticker is selected, the chatbot displays a general context badge (e.g. "Overview" or "Insights") and hides ticker-specific quick prompts, showing only generic prompts like "What am I missing?".
- Displays an animated typing indicator while background tasks are running.
- Returns clean warning messages if the 20-message daily cap is hit.

## External Dependencies
None.

## External URLs
None.

## Related Files
- **Skills:** [Component ID Registry](../skills/registry.md), [AI Memory & Caching](../skills/ai_memory.md)
- **Reference:** [Store Contracts](../../docs/reference/store_contracts.md), [Callback Ownership](../../docs/reference/callback_ownership.md)
- **Code:** [chatbot.py](../../components/chatbot.py), [research_callbacks.py](../../callbacks/research_callbacks.py), [research_service.py](../../services/research_service.py)
