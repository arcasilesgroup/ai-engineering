# Accessibility — the honesty floor for designed surfaces (spec 038 / B-038-1/2)

Loaded only when a verify pass runs (context economy, spec 033). A design the framework
produces meets the accessibility floor or exits `not-covered: <reason>`; never a silent
pass.

## The four basics

1. **Contrast** — ≥ WCAG 2.2 AA over the real background (ai-design verify step 7 already
   measures it; never over declared CSS).
2. **Keyboard** — every interactive element is reachable and operable by keyboard alone.
3. **Visible focus** — focus is always visible during keyboard navigation.
4. **Reduced motion** — `prefers-reduced-motion` respected (delegated to ai-review's motion
   lens; the design adds no motion that ignores it).

## The rule

A verify pass that names the four basics passes. A verify pass that **deliberately cannot**
meet one or more exits `not-covered: <reason>` — the honest, recorded exit, never a silent
pass and never a stall. A verify pass that names neither the basics nor a `not-covered` is
refused by `contract._accessibility_problems` (silent pass refused).

## Same discipline, two surfaces

- `NOT COVERED` (cold verifier, spec 030): a lane that did not run.
- `not-covered` (design, spec 038): a surface that cannot meet the floor.
The same honesty, two places; the spelling stays linked in this reference and unifies into
one constant only when a second surface needs it.

## Landmarks and beyond (measured by need, not today)

Landmarks, screen-reader labels, tab order: added to the floor only when a surface needs
them; the current floor is the functional minimum (contrast, keyboard, focus,
reduced-motion).

## Design inputs (spec 037 roadmap rows 6/16)

The design skills (apple-design, hallmark, high-end-visual-design, emil-design-eng, and
the roadmap's) are inputs this design skill may load; never framework skills. This
reference is the floor any of them must respect.
