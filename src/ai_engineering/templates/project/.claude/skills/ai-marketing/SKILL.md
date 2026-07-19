---
name: ai-marketing
description: "Drives go-to-market execution and marketing content: blog posts for distribution, social crossposts, X/Twitter automation, platform-native content engines. Trigger for 'go to market', 'marketing plan', 'write a blog post to publish', 'crosspost to socials', 'content engine', 'post a thread on X'. Not for fundraising/investor materials; use /ai-fundraising instead. Not for internal docs; use /ai-docs instead. Not for sprint reviews or solution intent; use /ai-prose instead. Not for code explanations; use /ai-explain instead."
effort: mid
argument-hint: "[mode] [topic]"
tags: [gtm, marketing, content, social, go-to-market]
---

# Marketing

Router for marketing content + go-to-market execution. Dispatches to handler files by mode.

## Workflow

Applies §10.4 DRY (write once, adapt across platforms — the repurposing cascade) and §10.7 Clean Code (public tone, no filler).

1. Detect mode (see Routing).
2. Load the relevant handler.
3. Apply audience tone — public, never internal.
4. For social: schedule + monitor.

## Routing

| Sub-command | Handler | Purpose |
|-------------|---------|---------|
| `content-engine` | `handlers/content-engine.md` | Platform-native social content with repurposing cascade |
| `crosspost` | `handlers/crosspost.md` | Multi-platform content distribution and adaptation |
| `x-api` | `handlers/x-api.md` | X API v2 posting, threads, media |

No sub-command → display the routing table and ask which mode to use.

## Integration

Calls the mode handlers (x-api → X/Twitter; per-platform handlers). See also `/ai-fundraising` (investor materials, market research, outreach), `/ai-prose` (sprint review, solution intent), `/ai-visual` (visual collateral), `/ai-docs` and `/ai-explain` (boundaries).

## Examples

User: "syndicate the latest blog post"

```
/ai-marketing crosspost
```

Reads the latest published blog post, generates platform-specific variants (X thread, LinkedIn long-form, Mastodon), and schedules them.

$ARGUMENTS
