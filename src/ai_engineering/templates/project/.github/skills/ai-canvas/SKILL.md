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

Visual design artifact creation skill. Creates design philosophies (aesthetic movements articulated through form, space, color, and composition) and expresses them visually through high-quality compositions with minimal integrated text.

## Core Understanding

This skill generates custom design philosophies and expresses them visually. A design philosophy is NOT a layout -- it's a visual philosophy interpreted through:
- Form, space, color, composition
- Images, graphics, shapes, patterns
- Minimal text as visual accent (90% visual, 10% essential text)

**Critical:** User input provides foundation but should not constrain creative freedom. The philosophy emphasizes visual expression, spatial communication, artistic interpretation, and minimal words.

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
8. **Self-review** -- Check: (1) clear focal point, (2) consistent spacing, (3) color harmony within palette, (4) type hierarchy with max 2-3 font sizes, (5) grid-based composition. If any criterion fails, refine.
9. **Read handlers/examples.md** for inspiration if needed

## Quick Reference

| Step | Gate | Output |
|------|------|--------|
| Brief | Audience + purpose clear | Creative direction |
| Philosophy | Movement named + articulated | .md philosophy doc |
| Canvas | Visual standards met | .pdf or .png artifact |
| Review | 5-point criteria check | Refined output |

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

- **Called by**: user directly, `/ai-design` (when visual artifacts are needed), `/ai-media` (for visual direction)
- **Consumed by**: ai-slides (aesthetic philosophy), ai-media (visual direction for generated assets)
- **Does NOT call**: other skills -- this skill produces final artifacts

## Common Mistakes

- Using generic stock photo aesthetics instead of creating a philosophy
- Too much text -- remember: 90% visual, 10% text
- Lack of craftsmanship -- every spacing, color choice, and alignment must scream expertise
- Not creating a named movement -- the philosophy gives the piece coherence
- Announcing the conceptual reference instead of embedding it subtly

$ARGUMENTS
