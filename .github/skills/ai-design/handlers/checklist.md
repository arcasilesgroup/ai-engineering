# Handler: Pre-Delivery Checklist

## Purpose

Quality gate before delivering any design work. Merged from Frontend Design and UI/UX Pro Max pre-delivery checks.

## Visual Quality

- [ ] No emoji icons (use SVG)
- [ ] Consistent icon family/style across the design
- [ ] Official brand assets with correct proportions
- [ ] No layout-shifting pressed states
- [ ] Semantic theme tokens used throughout (no hardcoded colors)
- [ ] Distinctive aesthetic direction (not generic AI look)
- [ ] Typography is intentional -- display + body fonts paired
- [ ] Color palette is cohesive with clear hierarchy

## Interaction Quality

- [ ] Clear pressed/active feedback on all tappable elements
- [ ] Touch targets >=44x44pt / 48x48dp
- [ ] 150-300ms micro-interaction timing
- [ ] Disabled states visually distinct (opacity 0.38-0.5)
- [ ] Screen reader labels are descriptive
- [ ] No gesture region conflicts
- [ ] Hover states gated with `@media (hover: hover) and (pointer: fine)`

## Accessibility

- [ ] Primary text >=4.5:1 contrast in both light and dark modes
- [ ] Secondary text >=3:1 on dark surfaces
- [ ] Meaningful accessibility labels on images/icons
- [ ] Form fields have labels, hints, and error messages
- [ ] Color is never the sole indicator of state
- [ ] Reduced motion and dynamic text size supported
- [ ] Keyboard navigation works for all interactive elements
- [ ] Focus indicators visible (2-4px ring)

## Layout & Responsive

- [ ] Safe areas respected (notches, gesture bars)
- [ ] Scroll content not hidden behind fixed bars
- [ ] Tested at: 375px, 768px, 1024px, 1440px
- [ ] Gutters adapt by device/orientation
- [ ] 4/8dp spacing rhythm maintained
- [ ] Text readable on large devices (line length <=75 chars)
- [ ] No horizontal scrolling on mobile

## Performance

- [ ] Images use WebP/AVIF with responsive srcset
- [ ] Below-fold images have loading="lazy"
- [ ] CLS <0.1 (space reserved for all dynamic content)
- [ ] Font-display: swap on all web fonts
- [ ] Lists with 50+ items virtualized
- [ ] Animations use transform/opacity only

## Both Themes

- [ ] Dividers distinguishable in both light and dark
- [ ] Interaction states consistent per theme
- [ ] Both themes tested before delivery
- [ ] Semantic color tokens work correctly in both modes
