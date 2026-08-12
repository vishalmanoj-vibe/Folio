# Multi-Provider AI Model Selection

Add support for Claude (Anthropic), ChatGPT (OpenAI), and Gemini (Google) as selectable AI providers in Folio. Users choose their provider and model in Settings, supply the corresponding API key, and all AI features (signals, chat, sentiment, reports) route through the selected provider.

## Proposed Changes

### Architecture: Provider Abstraction Layer

A single new file `services/ai_provider.py` will act as the unified AI gateway. All 4 AI consumers (`ai_engine.py`, `research_service.py`, `sentiment_service.py`, `report_service.py`) will call `ai_provider.py` instead of importing `google.genai` directly. This keeps changes surgical — each consumer only changes its ~5 lines of API call code.

---

### New Files

#### `services/ai_provider.py`
The unified AI provider gateway. Two public functions:
- `generate_content(prompt, system_prompt, model, temperature, max_tokens)` — Single-shot text generation (used by `ai_engine.py`, `sentiment_service.py`, `report_service.py`)
- `chat_completion(messages, system_prompt, model, temperature, max_tokens)` — Multi-turn chat (used by `research_service.py`)

Both functions read the active provider from user settings, get the corresponding API key from environment variables or database, and dispatch to the correct SDK.

#### `docs/guides/AI_PROVIDERS.md`
User-facing guide with step-by-step instructions to get API keys for Google Gemini, OpenAI, and Anthropic.

---

### Modified Files

#### `config/settings.py`
Add `AI_PROVIDER` settings default constant.

#### `data/settings_repository.py`
Add `ai_provider` default key to `DEFAULTS` dictionary.

#### `pages/settings.py`
Add provider dropdown, API key input, and Test Connection button to the layout.

#### `callbacks/settings_callbacks.py`
Add callbacks for loading/saving settings, updating model dropdown options dynamically, and verifying connection test.

#### `services/ai_engine.py`
Refactor `analyze_signals` to call `generate_content` from `ai_provider`.

#### `services/research_service.py`
Refactor `get_ai_response` to call `chat_completion` from `ai_provider`.

#### `services/sentiment_service.py`
Refactor `analyze_news_sentiment` to call `generate_content` from `ai_provider`.

#### `services/report_service.py`
Refactor PDF report AI commentary and summaries to call `generate_content` from `ai_provider`.

#### `callbacks/setup_callbacks.py`
Set default provider as `gemini` in onboarding.

#### `requirements.txt`
Add `openai` and `anthropic` as optional dependencies.
