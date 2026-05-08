---
name: ai-animation
description: "Designs motion, transitions, and micro-interactions for UI components: spring animations, gestures, easing, staggers — taste-driven detail compounding. Trigger for 'animate this', 'add transitions', 'micro-interactions for', 'gesture design', 'swipe to dismiss', 'easing for this', 'stagger the'. Not for design systems; use /ai-design instead. Not for visual art; use /ai-visual instead. Not for testing animation code; use /ai-test instead."
effort: high
argument-hint: "[component or interaction to animate]"
tags: [animation, motion, transitions, micro-interactions, css]
---

# Animation

## Quick start

```
/ai-animation save button                       # micro-interaction
/ai-animation swipe-to-dismiss for toast        # gesture design
/ai-animation review the modal entry            # review existing motion
```

## Workflow

Motion design based on Emil Kowalski's design-engineering philosophy: animation is about feel, not decoration. In competitive markets where functionality is table-stakes, taste becomes the differentiator.

1. **Run the Decision Framework** (4 questions): should it animate, what purpose, what easing, how fast?
2. **Load the relevant handler** for the work type (motion principles, components, clip-path, gestures, performance, sonner-principles).
3. **Apply the rules** from the loaded handler.
4. **Review** with the checklist; **test on real devices** for gestures (simulator misses touch latency).

> Detail: see [decision framework](references/decision-framework.md), [easing curves and review checklist](references/easing-curves.md), [accessibility (reduced motion + touch hover)](references/accessibility.md), [stagger + debugging](references/stagger-and-debug.md).

## When to Use

- Adding animations or transitions to components
- Designing micro-interactions (button press, hover, focus)
- Building gesture-based interactions (swipe, drag, pinch)
- Reviewing existing animations for polish and performance
- Choosing easing curves, durations, spring configurations
- Implementing scroll-triggered animations
- Building loading/skeleton animations

## Handler Map

| Concern | Handler |
| --- | --- |
| Springs, easing, durations | `handlers/motion-principles.md` |
| Buttons, popovers, tooltips, blur | `handlers/components.md` |
| Tabs, reveals, sliders | `handlers/clip-path.md` |
| Momentum, damping, pointer capture | `handlers/gestures.md` |
| GPU, WAAPI, CSS vs JS | `handlers/performance.md` |
| DX, defaults, cohesion | `handlers/sonner-principles.md` |

Step 0 (load contexts): per `.ai-engineering/contexts/stack-context.md`.

## Common Mistakes

- Animating keyboard-initiated actions (kills perceived speed).
- `transition: all` instead of named properties.
- `scale(0)` entry — nothing in the real world appears from nothing.
- `ease-in` on UI — feels sluggish.
- Skipping `prefers-reduced-motion` and the touch-hover media query.

## Examples

### Example 1 — micro-interaction for a save button

User: "animate the save button to feel responsive"

```
/ai-animation save button
```

Picks easing (cubic-bezier), duration (150-200ms), state choreography (idle → loading → success), hands off CSS/JSX with `prefers-reduced-motion` gate.

### Example 2 — swipe-to-dismiss gesture

User: "design the swipe-to-dismiss interaction for the toast component"

```
/ai-animation swipe-to-dismiss for toast component
```

Spring config, threshold velocity, horizontal-only constraint, accessibility fallback, real-device test plan.

## Integration

Called by: user directly, `/ai-design` (motion direction), `/ai-slides` (transitions), `/ai-code` (frontend micro-interactions). Hands off: CSS/JSX specs to `/ai-code` or `/ai-build`. See also: `/ai-design`, `/ai-test` (animation code), `/ai-debug` (broken motion).

$ARGUMENTS
