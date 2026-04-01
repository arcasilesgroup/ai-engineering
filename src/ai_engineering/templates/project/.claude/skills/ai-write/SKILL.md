---
name: ai-write
description: "Use when writing content: blog posts, pitch decks, sprint review summaries, architecture board reports, or solution intent documents. Audience targeting (developer/manager/executive) adjusts tone automatically. Not for documentation artifacts like changelogs or READMEs — use /ai-docs. Not for marketing content — use /ai-market."
effort: high
argument-hint: "content <type> [--audience developer|manager|executive]"
tags: [writing, content, communication]
---


# Technical Writing

Router skill for content writing. Dispatches to handler files based on content type. Always: clear structure, audience-appropriate, no fluff.

## When to Use

- Creating pitch decks, sprint reviews, blog posts, architecture board presentations, solution intent documents.
- NOT for documentation artifacts (README, CHANGELOG, API docs) -- use `/ai-docs`.
- NOT for marketing content (social posts, investor materials, outreach) -- use `/ai-market`.
- NOT for code explanations -- use `/ai-explain`.

## Writing Philosophy

Edit, don't generate. Start from what exists: notes, transcripts, data, examples, real output. Every sentence must earn its place. Template language is a failure mode, not a starting point.

## Routing

| Sub-command | Handler | Purpose |
|-------------|---------|---------|
| `content` | `handlers/content.md` | Articles, pitches, presentations, sprint reviews, architecture board, solution intent |

Default (no sub-command): `content`.

The `content` handler handles all sub-type dispatch internally based on the content type specified in the user's prompt.

## Audience Targeting

| Audience | Tone | Detail Level | Jargon |
|----------|------|-------------|--------|
| `developer` | Technical, precise | Implementation details | Full technical vocabulary |
| `manager` | Results-oriented | Impact and timeline | Minimal, explained when used |
| `executive` | Strategic | Business value and risk | None |

Default: `developer`.

## Quick Reference

```
/ai-write content pitch                     # elevator pitch
/ai-write content sprint-review             # sprint review summary
/ai-write content blog                      # blog post
/ai-write content presentation              # presentation outline
/ai-write content architecture-board        # architecture decision for review
/ai-write content solution-intent           # solution intent document
/ai-write content blog --audience manager   # manager-targeted blog post
```

## Shared Rules

- Write what users can DO, not what you BUILT.
- Active voice. Present tense.
- No "basically", "simply", "just".
- Every section earns its place -- cut anything that does not serve the reader.
- Audience determines vocabulary, not quality.

## Integration

- Content mode adapts to audience tier.
- **NOT** `/ai-docs` -- for documentation artifacts use `/ai-docs`
- **NOT** `/ai-market` -- for marketing and go-to-market content use `/ai-market`

$ARGUMENTS
