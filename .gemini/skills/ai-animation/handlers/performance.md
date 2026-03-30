# Handler: Animation Performance

## Purpose
Performance rules for smooth animations. GPU acceleration, CSS vs JS tradeoffs, and Web Animations API.

## Only animate transform and opacity

These properties skip layout and paint, running on GPU. Animating `padding`, `margin`, `height`, or `width` triggers all three rendering steps.

## CSS variables are inheritable

Changing CSS variable on parent recalculates styles for all children. In drawer with many items, updating `--swipe-amount` on container causes expensive style recalculation. Update `transform` directly on element instead.

```js
// Bad: triggers recalc on all children
element.style.setProperty('--swipe-amount', `${distance}px`);

// Good: only affects this element
element.style.transform = `translateY(${distance}px)`;
```

## Framer Motion hardware acceleration caveat

Framer Motion's shorthand properties (`x`, `y`, `scale`) are NOT hardware-accelerated. They use `requestAnimationFrame` on main thread. For hardware acceleration, use full `transform` string:

```jsx
// NOT hardware accelerated (convenient but drops frames under load)
<motion.div animate={{ x: 100 }} />

// Hardware accelerated (stays smooth even when main thread is busy)
<motion.div animate={{ transform: "translateX(100px)" }} />
```

This matters when browser simultaneously loads content, runs scripts, or paints. At Vercel, dashboard tab animation used Shared Layout Animations and dropped frames during page loads. Switching to CSS animations (off main thread) fixed it.

## CSS animations beat JS under load

CSS animations run off main thread. When browser is busy loading new page, Framer Motion animations (using `requestAnimationFrame`) drop frames. CSS animations remain smooth. Use CSS for predetermined animations; JS for dynamic, interruptible ones.

## Use WAAPI for programmatic CSS animations

Web Animations API gives JavaScript control with CSS performance. Hardware-accelerated, interruptible, and no library needed.

```js
element.animate(
  [
    { clipPath: 'inset(0 0 100% 0)' },
    { clipPath: 'inset(0 0 0 0)' }
  ],
  {
    duration: 1000,
    fill: 'forwards',
    easing: 'cubic-bezier(0.77, 0, 0.175, 1)',
  }
);
```
