# Handler: Component Animation Principles

## Purpose
Animation rules for specific UI components. Every component has unique motion requirements.

## Buttons must feel responsive

Add `transform: scale(0.97)` on `:active`. This gives instant feedback, making the UI feel like it truly listens.

```css
.button {
  transition: transform 160ms ease-out;
}

.button:active {
  transform: scale(0.97);
}
```

This applies to any pressable element. Scale should be subtle (0.95-0.98).

## Never animate from scale(0)

Nothing in the real world disappears and reappears completely. Elements animating from `scale(0)` look like they materialize from nowhere.

Start from `scale(0.9)` or higher, combined with opacity. Even barely-visible initial scale makes entrance feel natural, like a deflated balloon with visible shape.

```css
/* Bad */
.entering {
  transform: scale(0);
}

/* Good */
.entering {
  transform: scale(0.95);
  opacity: 0;
}
```

## Make popovers origin-aware

Popovers should scale in from their trigger, not center. Default `transform-origin: center` is wrong for almost every popover. **Exception: modals.** Modals should keep `transform-origin: center` because they're not anchored to specific triggers--they appear centered in viewport.

```css
/* Radix UI */
.popover {
  transform-origin: var(--radix-popover-content-transform-origin);
}

/* Base UI */
.popover {
  transform-origin: var(--transform-origin);
}
```

Whether users notice individually doesn't matter. In aggregate, unseen details become visible. They compound.

## Tooltips: skip delay on subsequent hovers

Tooltips should delay before appearing to prevent accidental activation. Once one tooltip is open, hovering over adjacent tooltips should open them instantly with no animation. This feels faster without defeating the initial delay's purpose.

```css
.tooltip {
  transition: transform 125ms ease-out, opacity 125ms ease-out;
  transform-origin: var(--transform-origin);
}

.tooltip[data-starting-style],
.tooltip[data-ending-style] {
  opacity: 0;
  transform: scale(0.97);
}

/* Skip animation on subsequent tooltips */
.tooltip[data-instant] {
  transition-duration: 0ms;
}
```

## Use CSS transitions over keyframes for interruptible UI

CSS transitions can be interrupted and retargeted mid-animation. Keyframes restart from zero. For rapidly-triggered interactions (adding toasts, toggling states), transitions produce smoother results.

```css
/* Interruptible - good for UI */
.toast {
  transition: transform 400ms ease;
}

/* Not interruptible - avoid for dynamic UI */
@keyframes slideIn {
  from { transform: translateY(100%); }
  to { transform: translateY(0); }
}
```

## Use blur to mask imperfect transitions

When crossfade between two states feels off despite trying different easings and durations, add subtle `filter: blur(2px)` during transition.

**Why blur works:** Without blur, you see two distinct objects during crossfade--old and new states overlapping. This looks unnatural. Blur bridges the visual gap by blending states together, tricking the eye into perceiving single smooth transformation instead of two objects swapping.

Combine blur with scale-on-press (`scale(0.97)`) for polished button state transition:

```css
.button {
  transition: transform 160ms ease-out;
}

.button:active {
  transform: scale(0.97);
}

.button-content {
  transition: filter 200ms ease, opacity 200ms ease;
}

.button-content.transitioning {
  filter: blur(2px);
  opacity: 0.7;
}
```

Keep blur under 20px. Heavy blur is expensive, especially in Safari.

## Animate enter states with @starting-style

Modern CSS way to animate element entry without JavaScript:

```css
.toast {
  opacity: 1;
  transform: translateY(0);
  transition: opacity 400ms ease, transform 400ms ease;

  @starting-style {
    opacity: 0;
    transform: translateY(100%);
  }
}
```

This replaces common React pattern of using `useEffect` to set `mounted: true` after initial render. Use `@starting-style` when browser support allows; fall back to `data-mounted` attribute pattern otherwise.

```jsx
// Legacy pattern (still works everywhere)
useEffect(() => {
  setMounted(true);
}, []);
// <div data-mounted={mounted}>
```

## The Opacity + Height Combination

When items enter and exit lists (like Family's drawer), opacity change must work well with height animation. This is often trial and error. There's no formula--you adjust until it feels right.
