---
name: ai-prose
description: "Writes content (blog posts, pitch decks, sprint review summaries, architecture board reports, solution intent documents) with automatic audience targeting (developer/manager/executive). Trigger for 'write a blog post', 'pitch this', 'sprint review summary', 'architecture board doc', 'solution intent for'. Not for documentation artifacts like CHANGELOG or README; use /ai-docs instead. Not for marketing/social content; use /ai-marketing instead. Not for code-level explanations; use /ai-explain instead."
effort: mid
argument-hint: "content [type] [--audience developer|manager|executive]"
tags: [writing, content, communication]
---

# Prose

Content writing (blog, pitch, sprint-review, architecture-board, solution-intent) with automatic audience targeting. Edit, don't generate — start from what exists (notes, transcripts, data, real output); template language is a failure mode.

## Workflow

Applies §10.7 Clean Code (every sentence earns its place; cut filler) and §10.4 DRY (one source of truth — reuse real output, don't regenerate).

1. Detect content type: blog / pitch / sprint-review / architecture-board / solution-intent / presentation.
2. Gather source material — notes, transcripts, data, real output.
3. Pick audience (developer / manager / executive; default developer); apply the tone + jargon table.
4. Edit, don't generate — every sentence earns its place.
5. Apply shared rules (active voice, present tense, no filler).

Routing: single sub-command `content` (default) → `handlers/content.md`, which dispatches to sub-types internally by the content type in the prompt.

## Audience Targeting

| Audience | Tone | Detail Level | Jargon |
|----------|------|-------------|--------|
| `developer` | Technical, precise | Implementation details | Full technical vocabulary |
| `manager` | Results-oriented | Impact and timeline | Minimal, explained when used |
| `executive` | Strategic | Business value and risk | None |

## Commands

```
/ai-prose content blog                      # blog post
/ai-prose content pitch                     # elevator pitch
/ai-prose content sprint-review             # sprint review summary
/ai-prose content presentation             # presentation outline
/ai-prose content architecture-board       # architecture decision for review
/ai-prose content solution-intent          # solution intent document
/ai-prose content blog --audience manager  # manager-targeted variant
```

## Shared Rules

- Write what users can DO, not what you BUILT.
- Active voice. Present tense.
- No "basically", "simply", "just".
- Every section earns its place — cut anything that doesn't serve the reader.
- Audience determines vocabulary, not quality.

## Integration

Called by: user directly. Dispatches to: `handlers/content.md`. See also: `/ai-docs` (CHANGELOG/README), `/ai-marketing` (social/outreach), `/ai-explain` (code-level), `/ai-slides` (deck rendering).

## Examples

User: "write the sprint review summary for this week"

```
/ai-prose content sprint-review --audience manager
```

Reads recent commits + closed issues, produces a results-oriented summary with impact + timeline framing, omits implementation jargon.

$ARGUMENTS
