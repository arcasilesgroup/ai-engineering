---
name: ai-visual
description: "Produces static visual design artifacts (posters, banners, flyers, branding, cover art, identity compositions) by composing named aesthetic philosophies into HTML/SVG, rendered to PDF/PNG. Trigger for 'create a poster', 'design a banner', 'branding visual', 'cover art for', 'identity composition'. Not for UI interfaces; use /ai-design instead. Not for animation; use /ai-animation instead. Not for presentation decks; use /ai-slides instead. Not for AI-generated photographs; use /ai-media instead."
effort: mid
argument-hint: "[visual artifact description or brief]"
tags: [visual-design, poster, banner, branding, artifact]
---

# Visual

Static visual artifacts: generate a custom, named design philosophy, then express it as 90% visual / 10% essential text. User input is foundation, not constraint.

## Workflow

Applies §10.1 KISS (restraint; polish what exists over adding graphics) and §10.7 Clean Code (every spacing, color, alignment is deliberate craft).

1. Understand the brief — purpose, audience, feeling to evoke.
2. Load `handlers/philosophy.md`; create + name a design movement (1-2 words, e.g. "Brutalist Joy", "Chromatic Silence").
3. Articulate the philosophy (4-6 paragraphs): space/form, color/material, scale/rhythm, composition/balance, visual hierarchy.
4. Load `handlers/canvas-creation.md`; apply visual standards + craftsmanship rules.
5. Deduce the subtle reference — embed conceptual threads within the art (sophisticated for those who know the subject, masterful abstract composition for others). Never announce it.
6. Create the canvas — 90% visual, 10% essential text.
7. Self-review — museum/magazine bar? If not, refine. Consult `handlers/examples.md` for inspiration.

Output rules:

| Mode | Rule |
| --- | --- |
| Render | Self-contained HTML -> PDF (browser print / Puppeteer); SVG for vector output. |
| Refine | Polish existing elements only — no new graphics/functions/shapes; make composition more cohesive. |
| Multi-page | One philosophy, distinct variation per page; bundle as one PDF or multiple PNGs; pages tell a story. |

## Common Mistakes

- Generic stock-photo aesthetics instead of a named philosophy.
- Announcing the conceptual reference instead of embedding it subtly.

## Integration

Called by: user directly, `/ai-design`, `/ai-media`. Consumed by: `/ai-slides` (aesthetic philosophy), `/ai-media` (visual direction). Calls: none — produces final artifacts. See also: `/ai-design` (UI), `/ai-animation` (motion).

## Examples

```
/ai-visual event poster for Edge Runtime 2026 developer conference
```

Names a movement (e.g. "Brutalist Compute"), articulates philosophy across space/color/composition, and renders an HTML->PDF poster at 90% visual / 10% text.

$ARGUMENTS
