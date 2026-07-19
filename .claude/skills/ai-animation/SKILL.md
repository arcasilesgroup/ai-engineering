---
name: ai-animation
description: "Designs motion, transitions, and micro-interactions for UI components: spring animations, gestures, easing, staggers, scroll-triggered and loading/skeleton motion. Trigger for 'animate this', 'add transitions', 'micro-interactions for', 'gesture design', 'swipe to dismiss', 'easing for this', 'review this motion for polish'. Not for design systems; use /ai-design instead. Not for visual art; use /ai-visual instead. Not for testing animation code; use /ai-test instead."
effort: high
argument-hint: "[component or interaction to animate]"
tags: [animation, motion, transitions, micro-interactions, css]
---

# Animation

Motion design on Emil Kowalski's philosophy: animation is feel, not decoration. When functionality is table-stakes, taste is the differentiator.

## Workflow

Applies §10.1 KISS (motion serves function; restraint over decoration) and §10.7 Clean Code (named properties, not `transition: all`).

1. Load context: `.ai-engineering/manifest.yml` `providers.stacks`; per stack `.ai-engineering/overrides/<stack>/conventions.md` + `.ai-engineering/overrides/_shared/conventions.md`; `.ai-engineering/team/*.md`.
2. Run the Decision Framework (4 questions): should it animate? what purpose? what easing? how fast?
3. Load the handler for the work type (see Handler Map) and apply its rules.
4. Review against the checklist; test gestures on real devices (simulators miss touch latency).

Detail: [decision framework](references/decision-framework.md), [easing curves + review checklist](references/easing-curves.md), [reduced motion + touch hover](references/accessibility.md), [stagger + debugging](references/stagger-and-debug.md).

## Handler Map

| Concern | Handler |
| --- | --- |
| Springs, easing, durations | `handlers/motion-principles.md` |
| Buttons, popovers, tooltips, blur | `handlers/components.md` |
| Tabs, reveals, sliders | `handlers/clip-path.md` |
| Momentum, damping, pointer capture | `handlers/gestures.md` |
| GPU, WAAPI, CSS vs JS | `handlers/performance.md` |
| DX, defaults, cohesion | `handlers/sonner-principles.md` |

## Common Mistakes

- Animating keyboard-initiated actions (kills perceived speed).
- `transition: all` instead of named properties.
- `scale(0)` entry — nothing in the real world appears from nothing.
- `ease-in` on UI — feels sluggish.
- Skipping `prefers-reduced-motion` and the touch-hover media query.

## Integration

**Called by**: user, `/ai-design` (motion direction), `/ai-slides` (transitions), `/ai-code` (micro-interactions). **Hands off**: CSS/JSX specs to `/ai-code` or `/ai-build`. **See also**: `/ai-design`, `/ai-test` (animation code), `/ai-debug` (broken motion).

## Examples

```
/ai-animation swipe-to-dismiss for toast component
```

Spring config, threshold velocity, horizontal-only constraint, accessibility fallback, real-device test plan; hands off CSS/JSX with a `prefers-reduced-motion` gate.

$ARGUMENTS
