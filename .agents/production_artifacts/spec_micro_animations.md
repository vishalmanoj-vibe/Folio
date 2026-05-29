# Feature Spec: Premium Micro-Animations and Spotlight Glows

## Goal
Elevate the dashboard from a standard web utility to a highly premium, native-app-like experience by introducing hardware-accelerated transitions and responsive user interactions. Specifically:
1. **Plotly Gliding Transitions**: Smooth interpolation of chart data and axes when changing periods/tickers.
2. **Glassmorphic Spotlight Glow**: Responsive, hardware-accelerated cursor lighting tracking over cards.
3. **Generic Clientside Countup**: High-performance character animation for key numerical data on updates without backend modifications.

## Stack & Technologies
- Plotly transition engine inside Dash
- Vanilla CSS Custom Properties (`--mouse-x`, `--mouse-y`)
- Lightweight Clientside JavaScript utilizing standard `MutationObserver`

## Key Component IDs
This enhancement does not add any new Dash Component IDs. It automatically styles and animations all existing card widgets and charts using their generic CSS class signatures (`.stat-card-container`, `.card`, `.stat-card-value`).

## Proposed Changes

### [MODIFY] [helpers.py](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/components/charts/helpers.py)
- Inject a transition configuration and set `uirevision = True` in `apply_standard_layout()` to enable built-in Plotly morphing and interpolation.

### [NEW] [spotlight.js](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/assets/spotlight.js)
- Implement cursor coordinate tracking over elements with `.stat-card-container` or `.card`, binding computed values to CSS variables `--mouse-x` and `--mouse-y`.

### [MODIFY] [ui-components.css](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/assets/ui-components.css)
- Implement standard CSS tokens for card hovering utilizing a radial glow styled in `var(--cyan)` opacity mapping.

### [NEW] [countup.js](file:///Users/vishal/Library/CloudStorage/OneDrive-Personal/Projects/portfolio_dashboard/assets/countup.js)
- Implement a generic `MutationObserver`-driven animator that monitors text-changes inside any element containing the `.stat-card-value` class, interpolating values client-side in the browser.

## Fallback States
- **Plotly Transitions**: If transitions are not supported or if data is absent, the fallback `create_empty_fig` is automatically rendered.
- **Spotlight Hover**: If javascript or CSS variables are unavailable, card backgrounds fallback perfectly to the default static `var(--surface-2)` style.
- **Countup**: If interpolation fails or returns NaN, the element immediately falls back to the exact parsed text value.

## Verification
- Period/ticker changes on all charts are beautifully interpolated instead of snapping.
- Cards react in real-time to cursor hover with a soft glassmorphic glow.
- Summary value changes visually tick up/down smoothly when loaded.
