# Skill: AI Persistence & Memory Management

## Objective
Implement persistent, long-term memory for AI agents without bloating storage or exceeding API token limits.

## The "Rolling Summary" Pattern
This project uses a rolling memory pattern to provide continuity while maintaining a lean data footprint.

### 1. Short-Term Log (High Fidelity)
- Store conversation turns in a simple JSON list (`conversation_log.json`).
- Include `role`, `content`, and `timestamp` (ISO 8601).
- **Cleanup Rule**: On every app startup, remove turns older than 7 days.

### 2. Long-Term Summary (Compressed Context)
- Turns removed from the short-term log are passed to the AI for summarization.
- **The Prompt**: "Summarise these investment research conversations in 3-5 bullet points. Focus on what tickers were discussed, what conclusions were reached, and what the user's investment preferences seem to be."
- Append the new summary chunk to `memory_summary.json`.

### 3. Context Injection
- When the AI assistant initialises, load both the summary and the recent log count.
- Inject this into the welcome message to provide a "memory" effect for the user.
- Prepend the full summary to the *last* user message before sending to the AI for reasoning, rather than storing it in the chat history.

## Storage Safeguards
- **Max File Size**: Set a hard limit (e.g., 50MB) for combined memory files.
- **UI Warning**: If `check_memory_size()` detects the limit is reached, display a warning in the UI.
- **Maintenance**: Perform heavy maintenance (summarization/cleanup) during app startup to avoid latency during active chat sessions.

## Implementation Checklist
- [ ] No Dash imports in the memory service (Service Layer Purity).
- [ ] maintenance called in `app.py` after market data is ready.
- [ ] `append_turn` called after both user and assistant messages.
- [ ] Timestamp parsing handles both ISO (new) and legacy formats.
