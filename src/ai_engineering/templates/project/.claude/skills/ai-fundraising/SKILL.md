---
name: ai-fundraising
description: "Drives fundraising and investor readiness: market sizing, competitive diligence, pitch decks, financial models, and investor outreach. Trigger for 'raise money', 'build a pitch deck', 'draft an investor cold email', 'market sizing', 'competitive research', 'financial model for the raise', 'warm intro to investors'. Not for growth/social content; use /ai-marketing instead. Not for sprint reviews or solution intent; use /ai-prose instead. Not for internal docs; use /ai-docs instead."
effort: mid
argument-hint: "[mode] [topic]"
tags: [fundraising, investor, market-research, pitch, outreach]
---

# Fundraising

Router for fundraising and investor-readiness work. Dispatches to handler files by mode.

## Workflow

Applies §10.4 DRY (one source-of-truth number set flows to deck, one-pager, model, and application) and §10.7 Clean Code (investor tone: numbers over narratives, no filler).

1. Detect mode (see Routing).
2. Load the relevant handler.
3. Anchor every material to a single set of confirmed metrics — traction, raise size, use of funds — before generating anything.
4. Run a consistency pass so no number disagrees across artifacts.

## Routing

| Sub-command | Handler | Purpose |
|-------------|---------|---------|
| `market-research` | `handlers/market-research.md` | Research-to-decision synthesis (diligence, competitive, sizing) |
| `investor-materials` | `handlers/investor-materials.md` | Pitch decks, one-pagers, financial models, applications |
| `investor-outreach` | `handlers/investor-outreach.md` | Cold emails, warm intros, follow-ups |

No sub-command → display the routing table and ask which mode to use.

## Examples

User: "build a seed pitch deck from our metrics"

```
/ai-fundraising investor-materials
```

Confirms the source-of-truth numbers (traction, raise size, use of funds), then generates a 12-slide deck and audits every claim for investor scrutiny.

## Integration

Calls the mode handlers (market-research, investor-materials, investor-outreach). See also `/ai-marketing` (growth + social content), `/ai-prose` (sprint review, solution intent), `/ai-slides` (deck rendering), and `/ai-docs` (boundaries).

$ARGUMENTS
