# Contributing to Folio

This guide covers local setup, development conventions, and how to extend the app.

## Setup Instructions

1. **Clone the Repository**:
   ```bash
   git clone <repo-url>
   cd folio
   ```

2. **Environment Setup**:
   - Python 3.11+ is recommended.
   - Create a virtual environment:
     ```bash
     python -m venv venv
     source venv/bin/activate  # macOS/Linux
     .\venv\Scripts\activate   # Windows
     ```
   - Install dependencies:
     ```bash
     pip install -r requirements.txt
     ```
   - Install Playwright (required for ETF holdings scraping):
     ```bash
     playwright install webkit
     ```

3. **Configuration**:
   - Create a `.env` file in the root directory (see `.env.example` for all available variables).
   - `GEMINI_API_KEY` is required for Assistant features.

4. **Run the App**:
   ```bash
   python app.py
   ```

## Development Workflow

### Adding a New Feature

To add a new feature (e.g., a new chart or a new data service), follow these steps:

1. **Data Layer**: Add any necessary table schemas to `data/database.py` and access methods to `data/repository.py`.
2. **Service Layer**: Implement the business logic in `services/`.
3. **Engine Layer**: If the feature involves math or aggregation, add pure logic to `core/engine/`.
4. **UI Component**: Create the component in `components/` or add to an existing page in `pages/`.
5. **Callbacks**: Register new interactivity in `callbacks/` and ensure it's imported and registered in `app.py`.

### Code Standards

- **Aesthetics**: Use the CSS Token System (`assets/base-tokens.css`). Never hardcode hex values in Python.
- **Performance**: Use bulk `yf.download()` instead of per-ticker loops.
- **Safety**: Always use `prevent_initial_call=True` for page-specific callbacks.

## Related Documentation

- **[DEVELOPER_GUIDE.md](docs/guides/DEVELOPER_GUIDE.md)**: Deep dive into architecture, algorithms, and data flow.
- **[TESTING.md](improvements/TESTING.md)**: Testing procedures and manual verification.
- **[GEMINI.md](../GEMINI.md)**: Coding rules, architecture constraints, and AI agent boundaries.
- **[IMPROVEMENTS.md](improvements/IMPROVEMENTS.md)**: Historical log of project milestones and architectural changes.
