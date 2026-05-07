# Skill: Testing & Verification

## Objective
Ensure every change is verified across all device types and theme states without crashing the production environment.

## 1. The Stability Audit (DevTools)
Before submitting a change:
- Open the dashboard in a browser.
- Open **Chrome DevTools (F12) → Console**.
- **Check for Red Errors**: Look for `ID not found` or `Callback error`.
- **Navigation Test**: Click through every page in the sidebar. If an error appears during navigation, you missed a `prevent_initial_call=True`.

## 2. Visual Quality Check
- **Theme Toggle**: Switch between Light and Dark mode. 
  - Ensure all text remains readable (no white-on-white).
  - Check that chart background/grid colors updated.
- **Responsiveness**: Resize the browser to 375px (iPhone width).
  - Ensure stat cards stack vertically.
  - Ensure tables don't cause horizontal page overflow (should be scrollable).

## 3. Data Integrity Check
- Check the **Last Updated** timestamp.
- If a transaction was added, verify the `portfolio-store` updated immediately.
- Hover over chart data points to ensure Tooltips are formatted correctly (e.g., `$1,234.56` not `1234.5678`).

## 4. Final Review Checklist
- [ ] No `print()` statements left in the code (use `logging` if needed).
- [ ] All new variables are in `base.css`.
- [ ] No hardcoded hex colors in Python files.
- [ ] Tickers are stored without `.AX` suffix.
