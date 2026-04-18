---
description: /addfeature [description of what you want to add]
---

## Purpose
Guide a new dashboard feature from idea → spec → build → verify,
using the correct modular architecture every step.

### Stage 1 — @pm: Spec the feature
1. Read GEMINI.md to understand the current architecture
2. Read components/layout.py and callbacks/chart_callbacks.py
   to understand what already exists
3. Write a short spec to production_artifacts/feature_spec.md:
   - What the feature does (2–3 sentences)
   - Which files will be created or modified
   - Component IDs for any new Dash elements
   - Data source: holdings, histories, or new store?
4. PAUSE — ask the user:
   "Here's the plan. Does this look right before I start coding?"
   Wait for explicit approval. Do not proceed until confirmed.

### Stage 2 — @engineer: Build it
1. Read production_artifacts/feature_spec.md
2. Follow the relevant skill file:
   - New chart    → use .agents/skills/add_chart.md
   - Bug fix      → use .agents/skills/debug_dash.md
3. Make only the changes listed in the spec
4. Do not touch files not listed in the spec
5. Save a summary to production_artifacts/build_log.md:
   - Files created
   - Files modified
   - New component IDs introduced

### Stage 3 — @qa: Verify
1. Read production_artifacts/build_log.md
2. Check each modified file against GEMINI.md rules:
   - No hardcoded colors?
   - CSS variables used correctly?
   - No new per-ticker yfinance loops?
   - Existing component IDs untouched?
3. Run a mental trace of the callback chain:
   store → callback → figure builder → dcc.Graph
4. Flag any issues. Fix minor ones directly.
   For bigger issues, report back before changing.

### Stage 4 — Report to user
Summarise:
  - What was built (one sentence)
  - Files changed
  - How to test it: "Run python app.py and look for X at [location]"
  - Anything to watch out for