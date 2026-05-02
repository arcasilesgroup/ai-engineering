---
name: ai-animation
description: Use when adding motion, transitions, or micro-interactions to UI components. Trigger for 'animate this', 'add transitions', 'micro-interactions for', 'spring animation', 'gesture design', 'swipe to dismiss', 'review the motion', 'easing for this', 'stagger animation', 'stagger the', 'animar esto', 'transicion para'. Not for design systems or aesthetic direction (use /ai-design), visual art (use /ai-canvas), testing animation code (use /ai-test), or debugging broken animations (use /ai-debug).
effort: high
argument-hint: "[component or interaction to animate]"
mode: agent
tags: [animation, motion, transitions, micro-interactions, css]
mirror_family: copilot-skills
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

Ask: How often will users see this animation?

| Frequency | Decision |
| --- | --- |
| 100+ times/day (keyboard shortcuts, command palette) | No animation. Ever. |
| Tens of times/day (hover effects, navigation) | Remove or drastically reduce |
| Occasional (modals, drawers, toasts) | Standard animation |
| Rare/first-time (onboarding, feedback, celebrations) | Can add delight |

**Never animate keyboard-initiated actions.** These repeat hundreds of times daily. Animation makes them feel slow, delayed, and disconnected from user intent.

Raycast has no open/close animation. That's optimal for something used hundreds of times daily.

### 2. What is the purpose?

Every animation needs a clear answer: "Why does this animate?"

Valid purposes:
- **Spatial consistency:** toast enters/exits from same direction; swipe-to-dismiss feels intuitive
- **State indication:** morphing feedback button shows state change
- **Explanation:** marketing animation demonstrates feature function
- **Feedback:** button scales down on press, confirming the interface heard the user
- **Preventing jarring changes:** elements appearing/disappearing without transition feel broken

If the purpose is just "it looks cool" and users see it often, don't animate.

### 3. What easing should it use?

Decision tree:

Is the element entering or exiting?
- **Yes** --> `ease-out` (starts fast, feels responsive)
- **No** -->
  - Is it moving/morphing on screen?
    - **Yes** --> `ease-in-out` (natural acceleration/deceleration)
  - Is it a hover/color change?
    - **Yes** --> `ease`
  - Is it constant motion (marquee, progress bar)?
    - **Yes** --> `linear`
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

When reviewing animation code, use a markdown table with Before/After/Why columns. Never use separate "Before:" and "After:" lines:

| Before | After | Why |
| --- | --- | --- |
| `transition: all 300ms` | `transition: transform 200ms ease-out` | Specify exact properties; avoid `all` |
| `transform: scale(0)` | `transform: scale(0.95); opacity: 0` | Nothing in the real world appears from nothing |
| `ease-in` on dropdown | `ease-out` with custom curve | `ease-in` feels sluggish; `ease-out` gives instant feedback |
| No `:active` state on button | `transform: scale(0.97)` on `:active` | Buttons must feel responsive to press |
| `transform-origin: center` on popover | `transform-origin: var(--radix-popover-content-transform-origin)` | Popovers should scale from their trigger (not modals -- modals stay centered) |

Never use this format:
```
Before: transition: all 300ms
After: transition: transform 200ms ease-out
```

## Review Checklist

| Issue | Fix |
| --- | --- |
| `transition: all` | Specify exact properties: `transition: transform 200ms ease-out` |
| `scale(0)` entry animation | Start from `scale(0.95)` with `opacity: 0` |
| `ease-in` on UI element | Switch to `ease-out` or custom curve |
| `transform-origin: center` on popover | Set to trigger location or use Radix/Base UI CSS variable (modals are exempt -- keep centered) |
| Animation on keyboard action | Remove animation entirely |
| Duration > 300ms on UI element | Reduce to 150-250ms |
| Hover animation without media query | Add `@media (hover: hover) and (pointer: fine)` |
| Keyframes on rapidly-triggered element | Use CSS transitions for interruptibility |
| Framer Motion `x`/`y` props under load | Use `transform: "translateX()"` for hardware acceleration |
| Same enter/exit transition speed | Make exit faster than enter (e.g., enter 2s, exit 200ms) |
| Elements all appear at once | Add stagger delay (30-80ms between items) |

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

When multiple elements enter together, stagger their appearance. Each element animates in with small delay after previous one.

```css
.item {
  opacity: 0;
  transform: translateY(8px);
  animation: fadeIn 300ms ease-out forwards;
}

.item:nth-child(1) { animation-delay: 0ms; }
.item:nth-child(2) { animation-delay: 50ms; }
.item:nth-child(3) { animation-delay: 100ms; }
.item:nth-child(4) { animation-delay: 150ms; }

@keyframes fadeIn {
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
```

Keep stagger delays short (30-80ms between items). Long delays make interface feel slow. Stagger is decorative--never block interaction while stagger animations are playing.

## Debugging Animations

### Slow motion testing
Play animations at reduced speed to spot issues invisible at full speed. Temporarily increase duration to 2-5x normal, or use browser DevTools animation inspector to slow playback.

Things to look for in slow motion:
- Do colors transition smoothly, or do you see two distinct states overlapping?
- Does easing feel right, or does it start/stop abruptly?
- Is transform-origin correct, or does element scale from wrong point?
- Are multiple animated properties (opacity, transform, color) in sync?

### Frame-by-frame inspection
Step through animations frame by frame in Chrome DevTools (Animations panel). This reveals timing issues between coordinated properties you cannot see at full speed.

### Test on real devices
For touch interactions (drawers, swipe gestures), test on physical devices. Connect phone via USB, visit local dev server by IP address, and use Safari's remote devtools. Xcode Simulator is alternative but real hardware is better for gesture testing.

## Integration

- **Called by**: user directly, `/ai-design` (when motion is needed).
- **Consumed by**: ai-slides (transitions), ai-code (frontend micro-interactions).
- **Transitions to**: implementation via `/ai-code` or `/ai-dispatch` — hand off animation specifications (easing curves, durations, CSS/JS code).

$ARGUMENTS
