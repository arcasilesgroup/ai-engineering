# Handler: Sonner Principles -- Building Loved Components

## Purpose
Principles from building Sonner (13M+ weekly npm downloads) that apply to any component library. DX, defaults, naming, edge cases, cohesion, and asymmetric timing.

## The Sonner Principles

1. **Developer experience is key.** No hooks, no context, no complex setup. Insert `<Toaster />` once, call `toast()` from anywhere. The less friction to adopt, the more people will use it.

2. **Good defaults matter more than options.** Ship beautiful out of the box. Most users never customize. Default easing, timing, and visual design should be excellent.

3. **Naming creates identity.** "Sonner" (French for "to ring") feels more elegant than "react-toast". Sacrifice discoverability for memorability when appropriate.

4. **Handle edge cases invisibly.** Pause toast timers when tab is hidden. Fill gaps between stacked toasts with pseudo-elements to maintain hover state. Capture pointer events during drag. Users never notice these, and that's exactly right.

5. **Use transitions, not keyframes, for dynamic UI.** Toasts are added rapidly. Keyframes restart from zero on interruption. Transitions retarget smoothly.

6. **Build a great documentation site.** Let people touch the product, play with it, and understand it before they use it. Interactive examples with ready-to-use code snippets lower adoption barriers.

## Cohesion matters

Sonner's animation feels satisfying partly because the whole experience is cohesive. Easing and duration fit library vibe. It's slightly slower than typical UI animations and uses `ease` rather than `ease-out` to feel more elegant. Animation style matches toast design, page design, name--everything harmonizes.

When choosing animation values, consider component personality. Playful components can be bouncier. Professional dashboards should be crisp and fast. Match motion to mood.
