# Skill: UI/UX Changes

## Objective
Make visual and layout changes to the dashboard while preserving
all existing functionality, component IDs, and callback wiring.

## Rules of Engagement
- **The "Aura Ledger" Aesthetic**: Maintain the dark-themed, high-density professional SaaS look.
  - Use subtle glow effects (`box-shadow: 0 0 15px var(--glow)`) for active cards.
  - Ensure high-density layouts (minimize whitespace without sacrificing readability).
- **Modular CSS Hierarchy**: NEVER use a monolithic `styles.css`.
  - `base.css`: CSS Variables and resets (must load first).
  - `ui-components.css`: Reusable component styles (cards, inputs).
  - `pages/*.css`: Page-specific overrides.
- **Color Variables**: Never hardcode hex. Use `var(--t-pri)`, `var(--bg)`, `var(--surface)`, `var(--border)`, `var(--green)`, `var(--red)`.
- **Iconography**: Use `dash-iconify` for all icons to ensure visual consistency.
- **Component IDs**: Never change an ID — only style properties.
- **Layout Consistency**: All pages MUST use `create_header()` for navigation.

## Where things live
- Global theme tokens  → components/layout.py (INDEX_STRING <style> block)
- Static CSS           → assets/styles.css
- Per-component style  → inline style= dicts in layout.py or ui_helpers.py
- Chart colors/theme   → config/constants.py get_theme()
- Stat cards           → components/ui_helpers.py stat_card()
- Chart titles         → components/ui_helpers.py chart_title()
- Section wrappers     → components/ui_helpers.py section()
- Live table rows      → callbacks/core_callbacks.py update_live_table()

## Steps

### 1. Classify the change
Identify which category it falls into:
  A) Spacing / padding / margins     → inline style= or styles.css
  B) Typography (size, weight)       → inline style= or styles.css
  C) Colors / theme tokens           → INDEX_STRING or get_theme()
  D) Component layout / arrangement  → layout.py structure
  E) Chart appearance                → figure builder in components/charts/
  F) Card / table styling            → ui_helpers.py

### 2. Read before touching
Open the specific file for that category.
Do not edit by memory — read the current state first.

### 3. Make the change
- For spacing/typography: edit the style= dict on the exact element
- For new CSS classes: add to assets/styles.css, apply className= in layout
- For chart tweaks: edit only the fig.update_layout() call in the builder
- For theme-aware colors: add/edit in get_theme() in config/constants.py
  and reference via theme_tokens dict in the figure builder

### 4. Dark + light check
After every change mentally verify:
- Does it use var(--t-pri), var(--bg), var(--surface), var(--border)?
- If a hex color was used, is it in get_theme() so it switches with theme?
- Would the layout break if the surface color were near-white?

### 5. Verify
Run: python app.py
Toggle the theme. Confirm the change looks correct in both modes.