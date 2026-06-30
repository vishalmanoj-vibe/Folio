# Spec: Detailed & Lay-Man Readable README.md Overhaul

## Feature Summary
This spec covers a complete documentation overhaul of the project's root `README.md`. The goal is to provide a comprehensive, easy-to-read guide explaining what Folio is, how it operates under a local double-process model, definitions of complex financial terms in plain English, and page-by-page instructions. It makes the application highly accessible to non-technical users while preserving structured codebase references for developers.

## Modified/New Files List
- `README.md` (modified)

## Component IDs
- None

## Data Strategy
- None (documentation only)

## Resolved Pain Points
- **Pain Point 1: Jargon Barriers.** Laymen often struggle with terms like "RSI", "Sharpe Ratio", "ex-dividend", or "Prophet". We translate each term to plain English.
- **Pain Point 2: Running Environment Mystery.** Users don't know why a launcher process restarts the worker. We explain the double-process design (Dash UI + background worker) and local SQLite database with WAL concurrency using a simple text diagram.
- **Pain Point 3: Installation Friction.** Onboarding issues (such as macOS Gatekeeper and Windows PowerShell execution policies) are addressed with clear, copy-pasteable commands and solutions.
