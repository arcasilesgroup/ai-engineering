# Handler: Design System

## Purpose

Design system intelligence and UX guidelines. Absorbed COMPLETE from UI/UX Pro Max skill. All rules, priority rankings, checklists, and product patterns preserved.

## Priority-Ranked Rule Categories (1-10)

| Priority | Category | Impact | Key Focus |
|----------|----------|--------|-----------|
| 1 | Accessibility | CRITICAL | Contrast 4.5:1, alt text, keyboard navigation |
| 2 | Touch & Interaction | CRITICAL | 44x44px minimum, 8px spacing, feedback |
| 3 | Performance | HIGH | WebP/AVIF, lazy loading, CLS <0.1 |
| 4 | Style Selection | HIGH | Match product type, SVG icons |
| 5 | Layout & Responsive | HIGH | Mobile-first, viewport meta, no horizontal scroll |
| 6 | Typography & Color | MEDIUM | 16px base, 1.5 line-height, semantic tokens |
| 7 | Animation | MEDIUM | 150-300ms duration, meaningful motion |
| 8 | Forms & Feedback | MEDIUM | Visible labels, error placement, validation |
| 9 | Navigation Patterns | HIGH | Predictable back, bottom nav <=5, deep linking |
| 10 | Charts & Data | LOW | Legends, tooltips, accessible colors |

### S1 Accessibility (CRITICAL)

- Color contrast minimum 4.5:1 for text
- Visible focus rings (2-4px)
- Aria-labels for icon-only buttons
- Full keyboard navigation support
- Respect reduced-motion preferences
- Meaningful screen reader labels
- Never use color as the sole indicator of state
- Semantic HTML before ARIA attributes

### S2 Touch & Interaction (CRITICAL)

- Minimum touch target: 44x44pt (Apple HIG) / 48x48dp (Material Design)
- 8px/8dp minimum gap between touch targets
- Click/tap for primary actions (avoid hover-only interactions)
- Loading state feedback on buttons
- Clear error messages near fields
- Visual feedback within 100ms of interaction
- No hover-only affordances -- everything must work with touch

### S3 Performance (HIGH)

- WebP/AVIF image formats with responsive srcset
- Lazy loading for non-critical assets (below the fold)
- Reserve space to avoid CLS (Cumulative Layout Shift <0.1)
- Font-display: swap to avoid invisible text during font loading
- Virtualize lists with 50+ items
- Keep main thread work under 16ms per frame
- Skeleton screens for operations taking >1s
- Preconnect to CDN/asset domains

### S4 Style Selection (HIGH)

- Match style to product type and audience
- SVG icons (never use emojis as structural icons)
- Consistent effects (shadows, blur, border-radius) across all components
- Platform-adaptive design (iOS HIG vs Material Design)
- Clear state distinctions (hover/pressed/disabled/focused)
- Unified dark/light mode design with semantic color tokens

### S5 Layout & Responsive (HIGH)

- Viewport meta: `width=device-width, initial-scale=1`
- Mobile-first design approach (styles cascade up)
- Systematic breakpoints: 375px / 768px / 1024px / 1440px
- Minimum 16px body text on mobile devices
- No horizontal scrolling on mobile (ever)
- 4pt/8dp spacing system for consistent rhythm
- Safe area awareness for notches and gesture bars
- Content not hidden behind fixed bars (nav, bottom sheet)

### S6 Typography & Color (MEDIUM)

- Line-height: 1.5-1.75 for body text
- Line length: 65-75 characters for readability
- Font scale consistency: 12, 14, 16, 18, 24, 32 (type scale)
- Semantic color tokens: primary, secondary, error, surface, on-primary, on-surface
- Dark mode using desaturated variants (not inverted)
- 4.5:1 contrast for all foreground/background pairs
- Tabular numbers for data columns (`font-variant-numeric: tabular-nums`)

### S7 Animation (MEDIUM)

- Duration: 150-300ms for micro-interactions
- Transform/opacity only (avoid animating width/height/margin)
- Exit animations 60-70% of enter duration
- Stagger sequences by 30-50ms per item
- Spring physics for natural feel (when appropriate)
- Respect prefers-reduced-motion media query
- State transitions should animate smoothly, not snap

### S8 Forms & Feedback (MEDIUM)

- Visible labels always (never placeholder-only)
- Error messages directly below the related field
- Loading, success, and error states on form submit
- Helper text for complex inputs (password requirements, format hints)
- Inline validation on blur (not on every keystroke)
- Disabled state: opacity 0.38-0.5 with cursor: not-allowed
- Progressive disclosure of advanced options
- Undo support for destructive actions

### S9 Navigation Patterns (HIGH)

- Bottom navigation maximum 5 items
- Current location always visually highlighted
- Predictable back behavior with state preservation
- Deep linking for all key screens
- Tab Bar (iOS) / Top App Bar + Nav Drawer (Android)
- Navigation items with both icon and text label
- Modal escape affordance always required (close button, swipe, ESC)

### S10 Charts & Data (LOW)

- Match chart type to data: trend=line, comparison=bar, proportion=pie/donut
- Accessible color palettes (avoid red/green only pairs)
- Always show legends for multi-series charts
- Tooltips on hover/tap showing exact values
- Responsive reflow on small screens
- Meaningful empty states when no data
- Skeleton placeholder while data loads

## Common Professional UI Issues

### Icons & Visual Elements

- No emojis as structural icons (use vector-based SVG)
- Consistent stroke width within icon layers
- One icon style per hierarchy level
- 44x44pt minimum with expanded hit areas
- Proper baseline alignment with text

### Interaction Quality

- 80-150ms tap feedback (visual response)
- Screen reader focus order matches visual layout
- Disabled state semantics enforced (aria-disabled)
- Platform-native gesture support where applicable
- No overlapping gesture conflicts

### Light/Dark Mode

- Body text >=4.5:1 contrast in both themes
- Secondary text >=3:1 on dark surfaces
- Separators/dividers visible in both themes
- State distinctions maintained per theme
- Token-driven theming approach (not hardcoded colors)
- 40-60% black modal scrim with blur backdrop

### Layout & Spacing

- Safe-area compliance for notches/gesture bars
- Status bar clearance maintained
- Predictable content width per device class
- 4/8dp spacing system applied consistently
- Readable text measure (line length) on large devices
- Section spacing hierarchy tiers: 16/24/32/48dp
- Adaptive gutters by breakpoint
