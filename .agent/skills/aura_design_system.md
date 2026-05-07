# Skill: Aura Design System

## Objective
Maintain the "Aura Ledger" aesthetic: a premium, high-density, dark-themed financial SaaS look.

## Core Visual Tokens
- **Surface**: `var(--surface)` — use for card backgrounds.
- **Border**: `var(--border)` — use for card outlines (1px solid).
- **Glow**: `box-shadow: 0 0 15px var(--glow)` — use ONLY for active/selected items.
- **Typography**: 
  - Main titles: Semibold, 1.1rem.
  - Stat values: Bold, 1.4rem, mono font if possible.

## Chart Aesthetic
- **Background**: `rgba(0,0,0,0)` (transparent) so it sits on the surface.
- **Gridlines**: `var(--border)` (low opacity).
- **Traces**: 
  - Positive: `var(--green)` with 0.2 opacity fill.
  - Negative: `var(--red)` with 0.2 opacity fill.
- **Smoothing**: Always use `line_shape='spline'` for time-series equity curves.

## Layout Density Rules
- **Margins**: Use `0.5rem` to `1rem` — keep things tight.
- **Card Spacing**: Use CSS Grid `gap: 1rem`.
- **Vertical Alignment**: Ensure stat cards in a row have identical heights regardless of content.

## Animation
- **Hover**: Subtle scale up (`transform: translateY(-2px)`) for interactive cards.
- **Transition**: `transition: all 0.3s ease` for theme switching.
