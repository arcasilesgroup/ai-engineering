---
name: ai-canvas
description: "Use when creating visual design artifacts: posters, banners, flyers, branding pieces, marketing materials, cover art, identity compositions, or any static visual output (PDF/PNG). Trigger for 'create a poster', 'design a banner', 'visual composition for', 'branding piece', 'marketing visual', 'cover art for', 'promotional graphic', 'cartel para', 'material de comunicacion visual', 'diseño visual para'. Not for UI interfaces (use /ai-design), animation (use /ai-animation), presentation decks (use /ai-slides), or AI-generated images (use /ai-media)."
effort: high
argument-hint: "[visual artifact description or brief]"
mode: agent
tags: [visual-design, poster, banner, branding, artifact]
---


# Canvas

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

- **Called by**: user directly, `/ai-design` (visual artifacts), `/ai-media` (visual direction).
- **Consumed by**: ai-slides (aesthetic philosophy), ai-media (visual direction for generated assets).
- Does NOT call other skills — produces final artifacts.

## Common Mistakes

- Using generic stock photo aesthetics instead of creating a philosophy
- Lack of craftsmanship -- every spacing, color choice, and alignment must scream expertise
- Announcing the conceptual reference instead of embedding it subtly

$ARGUMENTS
