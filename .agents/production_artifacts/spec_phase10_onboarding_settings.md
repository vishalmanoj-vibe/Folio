# Spec: Investor Profile Settings in Onboarding Wizard

## Summary
Add Investor Profile settings (Investment Goal, Risk Tolerance, and Tax Bracket) to the onboarding setup wizard. This allows users to configure both strategy settings and AI credentials in one place right after cloning the repo.

---

## Proposed Changes

### 1. Page Updates

#### [MODIFY] [setup_portfolio.py](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/pages/setup_portfolio.py)
- Rename Step 2 indicator from "AI Analyst" to "Strategy & AI" for terminology consistency.

#### [MODIFY] [setup_ai.py](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/pages/setup_ai.py)
- Rename Step 2 indicator from "AI Analyst" to "Strategy & AI".
- Change page header title to "Configure Strategy & AI" and subtitle to "Customize your investment strategy preferences and optionally enable Gemini AI."
- Add a new section "Strategy Settings" above the Gemini key field with three styled dropdowns:
  - **Investment Goal**: Balanced (default), Growth, Income, Capital Preservation.
  - **Risk Tolerance**: Low, Moderate (default), High.
  - **Tax Bracket**: 0%, 15%, 19%, 30%, 32.5%, 37% (default), 45%.
- Apply the `.settings-dropdown` and `.settings-form-row` classes to the dropdown inputs for dark mode compatibility and premium UX.

#### [MODIFY] [setup_ready.py](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/pages/setup_ready.py)
- Rename Step 2 indicator from "AI Analyst" to "Strategy & AI" for consistency.

---

### 2. Callback & Logic Updates

#### [MODIFY] [setup_callbacks.py](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/callbacks/setup_callbacks.py)
- Add a load callback to retrieve existing settings from SQLite via `get_all_settings()` when navigating to `/setup/ai`, and populate the dropdowns.
- Update `handle_ai_setup` to accept the three strategy settings dropdown values as `State` inputs.
- When saving (`setup-ai-save-btn` click) or skipping (`setup-ai-skip-btn` click), save the selected dropdown values to the SQLite database via `save_setting()`.

---

## Component IDs
We will register the following new IDs in [registry.md](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/.agents/skills/registry.md):
- `setup-investment-goal`: Dropdown selector for goal in wizard.
- `setup-risk-tolerance`: Dropdown selector for risk in wizard.
- `setup-tax-bracket`: Dropdown selector for tax in wizard.

---

## Fallback States
- Dropdowns will fall back to their system defaults (Balanced, Moderate, 37%) if the database table `user_settings` is empty.
- If loading fails, it defaults gracefully using `data.settings_repository.DEFAULTS`.

---

## External Dependencies / URLs
None. No new pip packages or external HTTP URLs are introduced in this phase.
