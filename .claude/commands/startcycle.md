---
description: Run the Folio idea-to-production pipeline (PM → Engineer → QA → Docs)
argument-hint: [idea]
---
Run the workflow defined in .agents/workflows/startcycle.md for this idea: $ARGUMENTS

Use the subagents in order: agent-ideator (feasibility review) → agent-pm (spec) → PAUSE for my approval of the spec → agent-engineer → agent-qa → agent-docs. Report progress briefly after each stage, and don't pause again after approval.
