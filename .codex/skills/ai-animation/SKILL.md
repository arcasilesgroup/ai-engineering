---
name: ai-animation
description: "Designs motion, transitions, and micro-interactions for UI components: spring animations, gestures, easing, staggers — taste-driven detail compounding. Trigger for 'animate this', 'add transitions', 'micro-interactions for', 'gesture design', 'swipe to dismiss', 'easing for this', 'stagger the'. Not for design systems; use /ai-design instead. Not for visual art; use /ai-canvas instead. Not for testing animation code; use /ai-test instead."
effort: high
argument-hint: "[component or interaction to animate]"
tags: [animation, motion, transitions, micro-interactions, css]
mirror_family: codex-skills
generated_by: ai-eng sync
canonical_source: .claude/skills/ai-animation/SKILL.md
edit_policy: generated-do-not-edit
---



# Animation

## Purpose

Motion design skill based on Emil Kowalski's design engineering philosophy. Builds interfaces where every animation detail compounds into something that feels right. In competitive markets where functionality is table-stakes, taste becomes the differentiator.

Core philosophy: animation is about feel, not decoration. Full design philosophy in `handlers/motion-principles.md`.

## When to Use

- Adding animations or transitions to components
- Designing micro-interactions (button press, hover, focus)
- Building gesture-based interactions (swipe, drag, pinch)
- Reviewing existing animations for polish and performance
- Choosing easing curves, durations, spring configurations
- Implementing scroll-triggered animations
- Building loading/skeleton animations

## Process

1. **Read the Animation Decision Framework** (below) -- answer the 4 questions in order before writing any animation code
2. **Load relevant handler** based on the type of work:
   - Motion principles --> `handlers/motion-principles.md` (springs, easing, durations)
   - Component interactions --> `handlers/components.md` (buttons, popovers, tooltips, blur)
   - Clip-path animations --> `handlers/clip-path.md` (tabs, reveals, sliders)
   - Gesture/drag --> `handlers/gestures.md` (momentum, damping, pointer capture)
   - Performance concerns --> `handlers/performance.md` (GPU, WAAPI, CSS vs JS)
   - Building loved components --> `handlers/sonner-principles.md` (DX, defaults, cohesion)
3. **Apply the rules** from the loaded handler
4. **Review using the checklist** at the bottom of this file
5. **Test on real devices** for gesture interactions -- simulator is not enough

## The Animation Decision Framework

### 1. Should this animate at all?

| Frequency | Decision |
| --- | --- |
| 100+ times/day (keyboard shortcuts) | No animation. Ever. |
| Tens of times/day (hover, navigation) | Drastically reduce |
| Occasional (modals, drawers, toasts) | Standard animation |
| Rare (onboarding, celebrations) | Can add delight |

**Never animate keyboard-initiated actions.** Raycast has no open/close animation; that's optimal for something used hundreds of times daily.

### 2. What is the purpose?

Valid: spatial consistency, state indication, explanation, feedback, preventing jarring changes. If the purpose is just "looks cool" and users see it often, don't animate.

### 3. What easing should it use?

| Element behavior | Easing |
| --- | --- |
| Entering or exiting | `ease-out` (responsive) |
| Moving/morphing on screen | `ease-in-out` |
| Hover/color change | `ease` |
| Constant motion (marquee, progress) | `linear` |
  - Default --> `ease-out`

**Critical:** Use custom easing curves. Built-in CSS easings lack punch and feel weak.

```css
/* Strong ease-out for UI interactions */
--ease-out: cubic-bezier(0.23, 1, 0.32, 1);

/* Strong ease-in-out for on-screen movement */
--ease-in-out: cubic-bezier(0.77, 0, 0.175, 1);

/* iOS-like drawer curve (from Ionic Framework) */
--ease-drawer: cubic-bezier(0.32, 0.72, 0, 1);
```

**Never use `ease-in` for UI animations.** It starts slow, making interfaces feel sluggish and unresponsive. A dropdown with `ease-in` at 300ms feels slower than `ease-out` at the same duration because `ease-in` delays initial movement--precisely when users watch most closely.

**Easing resources:** Don't create curves from scratch. Use easing.dev or easings.co to find stronger custom variants.

### 4. How fast should it be?

| Element | Duration |
| --- | --- |
| Button press feedback | 100-160ms |
| Tooltips, small popovers | 125-200ms |
| Dropdowns, selects | 150-250ms |
| Modals, drawers | 200-500ms |
| Marketing/explanatory | Can be longer |

**Rule:** UI animations should stay under 300ms. A 180ms dropdown feels more responsive than a 400ms one. Perception of speed matters as much as actual speed: `ease-out` at 200ms feels faster than `ease-in` at 200ms because users see immediate movement. Instant tooltips after the first one (skip delay + animation) make toolbars feel faster.

## Review Format (Required)

When reviewing animation code, use a markdown table with Before/After/Why columns (never separate "Before:" / "After:" lines):

| Before | After | Why |
| --- | --- | --- |
| `transition: all 300ms` | `transition: transform 200ms ease-out` | Specify properties; avoid `all` |
| `scale(0)` | `scale(0.95); opacity: 0` | Nothing in the real world appears from nothing |
| `ease-in` on dropdown | `ease-out` w/ custom curve | `ease-in` feels sluggish |
| No `:active` on button | `transform: scale(0.97)` on `:active` | Buttons must feel responsive |
| `transform-origin: center` on popover | Bind to trigger CSS var | Popovers scale from trigger (modals stay centered) |

## Review Checklist

| Issue | Fix |
| --- | --- |
| `transition: all` / `scale(0)` entry / `ease-in` on UI | Specify properties; start `scale(0.95)`; switch to `ease-out` |
| `transform-origin: center` on popover | Set to trigger location (modals exempt) |
| Animation on keyboard action / duration > 300ms | Remove; or reduce to 150-250ms |
| Hover without media query / keyframes on rapid element | `@media (hover: hover)`; switch to CSS transitions |
| Framer Motion `x`/`y` under load / same enter+exit speed | Use `transform: "translateX()"`; exit faster than enter |
| Elements appear at once | Stagger 30-80ms between items |

## Accessibility

### prefers-reduced-motion
Animations can cause motion sickness. Reduced motion means fewer and gentler animations, not zero. Keep opacity and color transitions that aid comprehension. Remove movement and position animations.

```css
@media (prefers-reduced-motion: reduce) {
  .element {
    animation: fade 0.2s ease;
    /* No transform-based motion */
  }
}
```

```jsx
const shouldReduceMotion = useReducedMotion();
const closedX = shouldReduceMotion ? 0 : '-100%';
```

### Touch device hover states
```css
@media (hover: hover) and (pointer: fine) {
  .element:hover {
    transform: scale(1.05);
  }
}
```
Touch devices trigger hover on tap, causing false positives. Gate hover animations behind this media query.

## Stagger Animations

When multiple elements enter together, stagger 30-80ms between items. Long delays make interface feel slow. Decorative — never block interaction.

```css
.item { opacity: 0; transform: translateY(8px); animation: fadeIn 300ms ease-out forwards; }
.item:nth-child(1) { animation-delay: 0ms; }
.item:nth-child(2) { animation-delay: 50ms; }
.item:nth-child(3) { animation-delay: 100ms; }
@keyframes fadeIn { to { opacity: 1; transform: translateY(0); } }
```

## Debugging Animations

- **Slow motion**: temporarily 2-5x duration, watch for color overlap, abrupt easing, wrong transform-origin, out-of-sync properties.
- **Frame-by-frame**: Chrome DevTools Animations panel for timing between coordinated properties.
- **Real devices**: gesture testing requires physical hardware (USB + Safari remote devtools); simulators miss touch latency.

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

Called by: user directly, `/ai-design` (motion direction), `/ai-slides` (transitions), `/ai-code` (frontend micro-interactions). Hands off: CSS/JSX specs to `/ai-code` or `/ai-dispatch`. See also: `/ai-design`, `/ai-test` (animation code), `/ai-debug` (broken motion).

$ARGUMENTS
