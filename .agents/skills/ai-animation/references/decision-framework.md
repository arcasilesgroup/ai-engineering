# Animation Decision Framework

Answer the four questions in order before writing animation code.

## 1. Should this animate at all?

| Frequency | Decision |
| --- | --- |
| 100+ times/day (keyboard shortcuts) | No animation. Ever. |
| Tens of times/day (hover, navigation) | Drastically reduce |
| Occasional (modals, drawers, toasts) | Standard animation |
| Rare (onboarding, celebrations) | Can add delight |

**Never animate keyboard-initiated actions.** Raycast has no open/close animation; that's optimal for something used hundreds of times daily.

## 2. What is the purpose?

Valid: spatial consistency, state indication, explanation, feedback, preventing jarring changes. If the purpose is just "looks cool" and users see it often, don't animate.

## 3. What easing should it use?

| Element behavior | Easing |
| --- | --- |
| Entering or exiting | `ease-out` (responsive) |
| Moving/morphing on screen | `ease-in-out` |
| Hover/color change | `ease` |
| Constant motion (marquee, progress) | `linear` |

Default: `ease-out`.

**Never use `ease-in` for UI animations.** It starts slow, making interfaces feel sluggish — a 300ms `ease-in` dropdown feels slower than a 300ms `ease-out` because users see immediate movement.

## 4. How fast should it be?

| Element | Duration |
| --- | --- |
| Button press feedback | 100-160ms |
| Tooltips, small popovers | 125-200ms |
| Dropdowns, selects | 150-250ms |
| Modals, drawers | 200-500ms |
| Marketing/explanatory | Can be longer |

**Rule:** UI animations should stay under 300ms. Perception of speed matters as much as actual speed.
