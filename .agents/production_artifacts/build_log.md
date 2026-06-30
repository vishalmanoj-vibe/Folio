# Build Log — Detailed & Layman-Friendly README.md Overhaul

## Description of Changes
- Completely rewrote and expanded the root `README.md` to be lay-man readable, detailed, and clear.
- Added a "For Beginners: What is Folio?" introductory hook using a real-world analogy.
- Added a "Finance-to-English" terminology table defining common investment terms (Ticker, ETF, P&L, Tranches, Ex-Dividend, Sharpe Ratio, Volatility, Correlation Matrix, and Prophet Forecasting).
- Created a text-based ASCII flowchart demonstrating how the Browser UI, Dash Web App, Background Worker, and local SQLite Database coordinate.
- Expanded the macOS and Windows installation instructions, adding bulleted breakdowns of what the installers do behind the scenes.
- Added a clear "Troubleshooting Common Issues" section addressing common environment problems (macOS permissions/Gatekeeper, Windows PowerShell blocks, database locks from OneDrive/Dropbox/iCloud, and Port 8050 conflicts).
- Provided a detailed page-by-page tour guide of all six main dashboard views.
- Outlined the AI Assistant & Gemini Chatbot features, including how to configure a free Gemini API key and why key features still run offline without one.
- Added a comprehensive Developer Reference folder-tree map detailing page templates, callbacks, components, services, database queries, mathematical engines, assets, and tests.
- Summarized testing procedures and updated the technical stack reference table.

## Changed Files
- `README.md` (modified)

## Component IDs Added
- None

## Verification Results
- Verified that all paths in the documentation map correctly to existing workspace folders.
- Ran lints and formatting tools to ensure markdown is correct.
