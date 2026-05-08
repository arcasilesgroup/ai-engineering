---
name: ai-write
description: Writes content (blog posts, pitch decks, sprint review summaries, architecture board reports, solution intent documents) with automatic audience targeting (developer/manager/executive). Trigger for 'write a blog post', 'pitch this', 'sprint review summary', 'architecture board doc', 'solution intent for'. Not for documentation artifacts like CHANGELOG or README; use /ai-docs instead. Not for marketing/social content; use /ai-market instead. Not for code-level explanations; use /ai-explain instead.
effort: high
argument-hint: "content [type] [--audience developer|manager|executive]"
tags: [writing, content, communication]
mirror_family: codex-skills
generated_by: ai-eng sync
canonical_source: .claude/skills/ai-write/SKILL.md
edit_policy: generated-do-not-edit
---



# Technical Writing

## Quick start

```
/ai-write content blog
/ai-write content sprint-review --audience manager
/ai-write content architecture-board
```

## Workflow

1. Detect content type from prompt (blog / pitch / sprint-review / architecture-board / solution-intent / presentation).
2. Read existing source material — notes, transcripts, data, real output.
3. Pick audience (developer / manager / executive); apply tone + jargon table.
4. Edit, do not generate. Every sentence earns its place.
5. Apply shared rules: active voice, present tense, no filler ("basically", "simply", "just").

Router skill for content writing. Dispatches to handler files based on content type. Always: clear structure, audience-appropriate, no fluff.

## When to Use

- Creating pitch decks, sprint reviews, blog posts, architecture board presentations, solution intent documents.
- NOT for documentation artifacts (README, CHANGELOG, API docs) -- use `/ai-docs`.
- NOT for marketing content (social posts, investor materials, outreach) -- use `/ai-market`.
- NOT for code explanations -- use `/ai-explain`.

## Writing Philosophy

Edit, don't generate. Start from what exists: notes, transcripts, data, examples, real output. Every sentence must earn its place. Template language is a failure mode, not a starting point.

## Routing

Single sub-command `content` (default) — handler `handlers/content.md` covers articles, pitches, presentations, sprint reviews, architecture board, solution intent. The handler dispatches to sub-types internally based on the content type in the user's prompt.

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

## Examples

### Example 1 — sprint review for a manager audience

User: "write the sprint review summary for this week"

```
/ai-write content sprint-review --audience manager
```

Reads recent commits + closed issues, generates a results-oriented summary with impact + timeline framing, omits implementation jargon.

### Example 2 — pitch deck for executive review

User: "draft an elevator pitch for the new auth product"

```
/ai-write content pitch --audience executive
```

Strategic framing, business value first, no technical vocabulary, ≤90 words.

## Integration

Called by: user directly. Dispatches to: `handlers/content.md`. See also: `/ai-docs` (CHANGELOG/README), `/ai-market` (social/outreach), `/ai-explain` (code-level), `/ai-slides` (deck rendering).

$ARGUMENTS
