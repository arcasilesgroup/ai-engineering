---
name: ai-gtm
description: "Drives go-to-market execution and marketing content: blog posts for distribution, social crossposts, investor materials, market research, outreach campaigns, X/Twitter automation. Trigger for 'go to market', 'gtm plan', 'write a blog post to publish', 'crosspost to socials', 'market research for', 'investor deck', 'outreach campaign', 'content engine'. Not for internal docs; use /ai-docs instead. Not for sprint reviews or solution intent; use /ai-write instead."
effort: high
argument-hint: "[mode] [topic]"
mode: agent
tags: [gtm, marketing, content, social, investor, go-to-market]
mirror_family: copilot-skills
generated_by: ai-eng sync
canonical_source: .claude/skills/ai-gtm/SKILL.md
edit_policy: generated-do-not-edit
---



# GTM

## Quick start

```
/ai-gtm blog "topic"               # public-facing blog post
/ai-gtm crosspost                  # syndicate latest post across platforms
/ai-gtm research "competitor"      # market research
/ai-gtm investor-deck              # investor pitch
/ai-gtm x-api                      # post to X/Twitter
```

## Workflow

Router skill for marketing content and go-to-market execution. Dispatches to handler files based on content type.

1. Detect mode (blog / crosspost / research / investor / outreach / x-api).
2. Load relevant handler.
3. Apply audience tone (public, never internal).
4. For social: schedule + monitor.

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
/ai-gtm content-engine                   # platform-native social content
/ai-gtm crosspost                        # multi-platform distribution
/ai-gtm market-research                  # research synthesis (diligence, competitive, sizing)
/ai-gtm investor-materials               # pitch deck, one-pager, financial model
/ai-gtm investor-outreach                # cold email, warm intro, follow-up
/ai-gtm x-api                            # post to X/Twitter via API
```

## Examples

### Example 1 — public blog post for distribution

User: "write a blog post about how we shipped our DAG planner"

```
/ai-gtm content-engine "DAG-based parallel agent planning"
```

Picks public-facing tone, structures for SEO, includes social hooks for crosspost.

### Example 2 — crosspost to socials

User: "syndicate the latest blog post"

```
/ai-gtm crosspost
```

Reads the latest published blog post, generates platform-specific variants (X thread, LinkedIn long-form, Mastodon), schedules.

## Integration

Calls: x-api handler (X/Twitter), platform-specific handlers. See When NOT to Use for boundaries with `/ai-docs`, `/ai-write`, `/ai-explain`. See also: `/ai-write` (sprint review, solution intent), `/ai-visual` (visual collateral).

$ARGUMENTS
