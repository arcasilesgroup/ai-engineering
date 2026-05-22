# Easing Curves

Built-in CSS easings lack punch. Use custom cubic-bezier curves; source stronger variants from easing.dev or easings.co — never invent from scratch.

```css
/* Strong ease-out for UI interactions */
--ease-out: cubic-bezier(0.23, 1, 0.32, 1);

/* Strong ease-in-out for on-screen movement */
--ease-in-out: cubic-bezier(0.77, 0, 0.175, 1);

/* iOS-like drawer curve (from Ionic Framework) */
--ease-drawer: cubic-bezier(0.32, 0.72, 0, 1);
```

## Review Format

Use a markdown table with Before/After/Why columns (never separate "Before:" / "After:" lines):

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
