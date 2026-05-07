---
name: ai-market
description: "Use for marketing content and go-to-market execution: content strategy, blog posts for distribution, social media crossposting, market research, investor materials, investor outreach, and X/Twitter API automation. Trigger for 'write a blog post to publish', 'crosspost to socials', 'market research for X', 'investor deck', 'outreach campaign', 'content engine', 'post to Twitter/X'. NOT for internal documentation — use /ai-docs. NOT for reports or solution intent — use /ai-write."
effort: high
argument-hint: "[mode] [topic]"
mode: agent
tags: [marketing, content, social, investor, go-to-market]
mirror_family: copilot-skills
generated_by: ai-eng sync
canonical_source: .claude/skills/ai-market/SKILL.md
edit_policy: generated-do-not-edit
---



# Market

Router skill for marketing content and go-to-market execution. Dispatches to handler files based on content type.

## When to Use

- Platform-native social content and repurposing cascades.
- Multi-platform content distribution.
- Market research and competitive analysis.
- Investor pitch decks, one-pagers, financial models.
- Investor outreach (cold emails, warm intros, follow-ups).
- X/Twitter API automation.

## When NOT to Use

- Internal documentation (README, CHANGELOG, API docs) -- use `/ai-docs`
- Reports, solution intent, architecture board docs -- use `/ai-write`
- Code explanations -- use `/ai-explain`

## Routing

| Sub-command | Handler | Purpose |
|-------------|---------|---------|
| `content-engine` | `handlers/content-engine.md` | Platform-native social content with repurposing cascade |
| `crosspost` | `handlers/crosspost.md` | Multi-platform content distribution and adaptation |
| `market-research` | `handlers/market-research.md` | Research-to-decision synthesis (diligence, competitive, sizing) |
| `investor-materials` | `handlers/investor-materials.md` | Pitch decks, one-pagers, financial models, applications |
| `investor-outreach` | `handlers/investor-outreach.md` | Cold emails, warm intros, follow-ups |
| `x-api` | `handlers/x-api.md` | X API v2 posting, threads, media |

If no sub-command is provided, display the routing table above and ask the user which mode to use.

## Quick Reference

```
/ai-market content-engine                   # platform-native social content
/ai-market crosspost                        # multi-platform distribution
/ai-market market-research                  # research synthesis (diligence, competitive, sizing)
/ai-market investor-materials               # pitch deck, one-pager, financial model
/ai-market investor-outreach                # cold email, warm intro, follow-up
/ai-market x-api                            # post to X/Twitter via API
```

## Integration

See When NOT to Use for boundaries with `/ai-docs`, `/ai-write`, `/ai-explain`.

$ARGUMENTS
