---
name: ai-design
description: "Designs user interfaces and design systems: aesthetic direction, color palettes, typography, spatial composition, information architecture for web, mobile, CLI, and docs-heavy experiences. Trigger for 'design this page', 'create a design system', 'color palette for', 'typography for', 'UI for this feature'. Not for animation; use /ai-animation instead. Not for static visual art (posters, banners); use /ai-visual instead. Not for slide decks; use /ai-slides instead."
effort: high
argument-hint: "[UI or design task description]"
tags: [design, ui, ux, design-system, aesthetics]
---

# Design

Aesthetic direction, design systems, component/UI/UX, and information architecture. Every output declares a conceptual direction and executes it with named tokens — never vague suggestions.

## Workflow

Applies §10.1 KISS (fewest moving parts; no decorative complexity) and §10.7 Clean Code (specific named tokens, not vague advice).

1. Load `handlers/aesthetics.md` (design-thinking framework) and `handlers/design-system.md` (priority-ranked UX rules). If unavailable, apply steps 2-5 directly.
2. Frame the request:
   - **Purpose** — what problem, which user?
   - **Tone** — pick ONE extreme with character (minimalist, maximalist, organic, luxury, playful, editorial, brutalist).
   - **Constraints** — framework, performance budget, accessibility level.
   - **Differentiation** — what makes it UNFORGETTABLE?
3. Apply UX guidelines by priority — gate P1-P2, treat P3-P9 as considerations, P10 for data-viz only:

| Priority | Category            | Gate                   |
| -------- | ------------------- | ---------------------- |
| 1        | Accessibility       | CRITICAL -- never skip |
| 2        | Touch & Interaction | CRITICAL -- never skip |
| 3        | Performance         | HIGH                   |
| 4        | Style Selection     | HIGH                   |
| 5        | Layout & Responsive | HIGH                   |
| 6        | Typography & Color  | MEDIUM                 |
| 7        | Animation           | MEDIUM                 |
| 8        | Forms & Feedback    | MEDIUM                 |
| 9        | Navigation Patterns | HIGH                   |
| 10       | Charts & Data       | LOW                    |

4. Produce specific choices, not guidance:
   - Named fonts (display + body pairing).
   - Color system (primary, secondary, accent, surface, background, text hierarchy, state colors).
   - Spacing scale (4pt/8dp).
   - Spatial composition + layout strategy.
   - Motion approach (duration, easing, what animates).
   - Conceptual direction in one sentence.
5. Design light + dark themes together, never dark mode as an afterthought.
6. Delegate: motion beyond micro-interactions -> `/ai-animation`; posters/banners/illustration -> `/ai-visual`; decks -> `/ai-slides`.
7. Run `handlers/checklist.md` pre-delivery; do not ship with unchecked items.

## Common Mistakes

- Generic AI aesthetics (purple gradients, Inter font, centered hero, 3-column features).
- Vague advice ("use a clean design") instead of specific tokens.
- Accessibility not treated as a hard gate (contrast, touch targets, keyboard nav).

## Integration

Called by: user, `/ai-slides`, `/ai-media`, `/ai-build`. Calls: `handlers/aesthetics.md`, `handlers/design-system.md`, `handlers/checklist.md`, `/ai-animation`, `/ai-visual`. Consumed by: `/ai-slides` (presentation aesthetics), `/ai-media` (visual asset direction).

## Examples

```
/ai-design empty state for search results page
```

Picks an opinionated direction, then specifies layout, micro-copy, illustration-vs-icon, accessibility checks, and light + dark simultaneously; runs `handlers/checklist.md` before handoff.

$ARGUMENTS
