---
name: ai-visual
description: Produces static visual design artifacts (posters, banners, flyers, branding pieces, cover art, identity compositions) by composing aesthetic philosophies into HTML/SVG and rendering to PDF/PNG. Trigger for 'create a poster', 'design a banner', 'branding visual', 'marketing graphic', 'cover art for', 'identity composition'. Not for UI interfaces; use /ai-design instead. Not for animation; use /ai-animation instead. Not for presentation decks; use /ai-slides instead. Not for AI-generated photographs; use /ai-media instead.
effort: high
argument-hint: "[visual artifact description or brief]"
tags: [visual-design, poster, banner, branding, artifact]
mirror_family: codex-skills
generated_by: ai-eng sync
canonical_source: .claude/skills/ai-visual/SKILL.md
edit_policy: generated-do-not-edit
---


# Visual

## Purpose

Visual design artifact creation. Generates custom design philosophies (aesthetic movements interpreted through form/space/color/composition + images/graphics/shapes/patterns) and expresses them visually with minimal text accent (90% visual, 10% essential text). User input is foundation, not constraint — the philosophy emphasizes visual expression and artistic interpretation.

## When to Use

- Creating posters, banners, flyers for events or campaigns
- Designing branding pieces and identity materials
- Building marketing and communication visuals
- Composing visual artifacts for presentations or reports
- Creating art-directed pieces with strong aesthetic philosophy
- Any static visual output (PDF, PNG) with high artistic direction

## Process

1. **Understand the brief** -- what is the artifact for? Who is the audience? What feeling should it evoke?
2. **Read handlers/philosophy.md** -- create a design philosophy (aesthetic movement) for this artifact
3. **Name the movement** (1-2 words) -- e.g., "Brutalist Joy", "Chromatic Silence", "Metabolist Dreams"
4. **Articulate the philosophy** (4-6 paragraphs covering: space/form, color/material, scale/rhythm, composition/balance, visual hierarchy)
5. **Read handlers/canvas-creation.md** -- apply the visual standards and craftsmanship rules
6. **Deduce the subtle reference** -- identify conceptual threads from the brief. Embed within the art -- sophisticated for those who know the subject, masterful abstract composition for others
7. **Create the canvas** -- express the philosophy visually. 90% visual design, 10% essential text
8. **Self-review** -- does this look like it belongs in a museum or magazine? If not, refine.
9. **Read handlers/examples.md** for inspiration if needed

## Rendering

Generate as self-contained HTML, then render to PDF via browser print or Puppeteer. For vector output, use SVG.

## Refinement Rules

When told work isn't perfect enough:

- Refine what exists rather than adding new graphics
- Make composition more cohesive with the art
- Ask: "How can I make what's already here more of a piece of art?"
- Avoid new functions or shapes -- polish existing elements

## Multi-Page Support

Additional pages should follow the same design philosophy but distinctly vary. Bundle in same PDF or multiple PNGs. Pages should almost tell a story in tasteful way while exercising full creative freedom.

## Integration

Called by: user directly, `/ai-design`, `/ai-media`. Consumed by: `/ai-slides` (aesthetic philosophy), `/ai-media` (visual direction). Calls: none — produces final artifacts. See also: `/ai-design` (UI), `/ai-animation` (motion).

## Examples

### Example 1 — event poster

User: "design a poster for a developer conference called 'Edge Runtime 2026'"

```
/ai-visual event poster for Edge Runtime 2026 developer conference
```

Defines a movement (e.g. "Brutalist Compute"), articulates philosophy across space/color/composition, and renders an HTML→PDF poster with 90% visual / 10% text emphasis.

### Example 2 — branding piece for product launch

User: "create cover art for the v1.0 release announcement"

```
/ai-visual cover art for product v1.0 release announcement
```

Generates a multi-page PDF where each page follows the same philosophy with distinct variation, suitable for press kit and social.

## Common Mistakes

- Using generic stock photo aesthetics instead of creating a philosophy
- Lack of craftsmanship -- every spacing, color choice, and alignment must scream expertise
- Announcing the conceptual reference instead of embedding it subtly

$ARGUMENTS
