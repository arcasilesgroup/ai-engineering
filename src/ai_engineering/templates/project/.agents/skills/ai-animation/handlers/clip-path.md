# Handler: Clip-Path Animations

## Purpose
clip-path is not just for shapes. It's one of the most powerful animation tools in CSS.

## The inset shape

`clip-path: inset(top right bottom left)` defines rectangular clipping region. Each value "eats" into the element from that side.

```css
/* Fully hidden from right */
.hidden {
  clip-path: inset(0 100% 0 0);
}

/* Fully visible */
.visible {
  clip-path: inset(0 0 0 0);
}

/* Reveal from left to right */
.overlay {
  clip-path: inset(0 100% 0 0);
  transition: clip-path 200ms ease-out;
}
.button:active .overlay {
  clip-path: inset(0 0 0 0);
  transition: clip-path 2s linear;
}
```

## Tabs with perfect color transitions

Duplicate tab list. Style the copy as "active" (different background, different text color). Clip the copy so only active tab is visible. Animate clip on tab change. This creates seamless color transition that timing individual color transitions can never achieve.

## Hold-to-delete pattern

Use `clip-path: inset(0 100% 0 0)` on colored overlay. On `:active`, transition to `inset(0 0 0 0)` over 2s with linear timing. On release, snap back with 200ms ease-out. Add `scale(0.97)` on button for press feedback.

## Image reveals on scroll

Start with `clip-path: inset(0 0 100% 0)` (hidden from bottom). Animate to `inset(0 0 0 0)` when element enters viewport. Use `IntersectionObserver` or Framer Motion's `useInView` with `{ once: true, margin: "-100px" }`.

## Comparison sliders

Overlay two images. Clip the top one with `clip-path: inset(0 50% 0 0)`. Adjust right inset value based on drag position. No extra DOM elements needed, fully hardware-accelerated.

## CSS Transform Mastery

### translateY with percentages

Percentage values in `translate()` are relative to element's own size. Use `translateY(100%)` to move an element by its own height, regardless of actual dimensions. This is how Sonner positions toasts and how Vaul hides drawers before animating in.

```css
/* Works regardless of drawer height */
.drawer-hidden {
  transform: translateY(100%);
}

/* Works regardless of toast height */
.toast-enter {
  transform: translateY(-100%);
}
```

Prefer percentages over hardcoded pixel values. They're less error-prone and adapt to content.

### scale() scales children too

Unlike `width`/`height`, `scale()` also scales element children. When scaling a button on press, font size, icons, and content scale proportionally. This is a feature, not a bug.

### 3D transforms for depth

`rotateX()`, `rotateY()` with `transform-style: preserve-3d` create real 3D effects in CSS. Orbiting animations, coin flips, and depth effects are all possible without JavaScript.

```css
.wrapper {
  transform-style: preserve-3d;
}

@keyframes orbit {
  from {
    transform: translate(-50%, -50%) rotateY(0deg) translateZ(72px) rotateY(360deg);
  }
  to {
    transform: translate(-50%, -50%) rotateY(360deg) translateZ(72px) rotateY(0deg);
  }
}
```

### transform-origin

Every element has an anchor point from which transforms execute. Default is center. Set it to match trigger location for origin-aware interactions.
