---
name: ai-slides
description: "Generates zero-dependency self-contained HTML presentations with keyboard/touch navigation and viewport-safe layout. Three modes: new (from scratch), convert (PPTX to HTML), enhance (improve existing). Trigger for 'create a talk deck', 'pitch deck', 'workshop slides', 'convert my PPTX', 'presentation for the all-hands'. Not for static visual art; use /ai-visual instead. Not for marketing collateral; use /ai-marketing instead."
effort: mid
argument-hint: "new|convert|enhance [topic]"
tags: [presentation, html, css]
---

# Slides

Generates zero-dependency, animation-rich HTML presentations that run entirely in the browser, with viewport fit as a hard gate. Non-designers discover their aesthetic through visual exploration rather than abstract choices.

## Workflow

Applies §10.1 KISS (zero dependencies; inline CSS/JS) and §10.7 Clean Code (commented, accessible, viewport-safe).

1. **Detect mode** — new (topic/notes/draft), convert (`.ppt`/`.pptx`), or enhance (existing HTML).
2. **Discover content** — ask only the minimum: purpose (pitch/teaching/talk/update), length (short 5–10 / medium 10–20 / long 20+), content state (finished copy / rough notes / topic only). If the user has content, have them paste it before styling.
3. **Discover style (preview-first)** — if a preset is named, skip previews. Else: ask the target feeling (impressed/energized/focused/inspired), generate 3 self-contained single-slide previews in `slide-previews/` (each < ~100 lines, showing typography/color/motion), ask which to keep or mix. Map mood → style via `STYLE_PRESETS.md`.
4. **Build** — output `presentation.html` (or `[name].html`); `assets/` only for extracted/user images. Required: semantic sections (`main`/`section`/`nav`), viewport-safe CSS base from `STYLE_PRESETS.md` (copy verbatim, theme on top), CSS custom properties, a presentation-controller class, Intersection Observer reveals, `prefers-reduced-motion`.
5. **Enforce viewport fit (hard gate)**:
   - every `.slide`: `height: 100vh; height: 100dvh; overflow: hidden;`
   - all type/spacing scales with `clamp()` — never `-clamp(...)` (browsers silently ignore negated CSS functions; use `calc(-1 * clamp(...))`)
   - overflow → split into more slides; never shrink text below readable; never allow in-slide scrollbars
   - use the density limits + mandatory CSS block in `STYLE_PRESETS.md`
6. **Validate at 8 sizes** — 1920x1080, 1440x900, 1280x720, 1024x768, 768x1024, 375x667, 414x896, 667x375. With browser automation: verify no overflow + keyboard nav. Without: review CSS against the density limits and flag un-verified sizes for manual QA.
7. **Deliver** — delete preview files unless the user keeps them; open with the platform opener (`open`/`xdg-open`/`start`); summarize file path, preset, slide count, theme customization points.

## Content Density

| Slide Type | Maximum Content |
|------------|-----------------|
| Title | 1 heading + 1 subtitle + optional tagline |
| Content | 1 heading + 4-6 bullets or 2 paragraphs |
| Feature grid | 6 cards maximum |
| Code | 8-10 lines maximum |
| Quote | 1 quote + attribution |
| Image | 1 image, ideally under 60vh |

## Requirements

- **Design**: distinctive — avoid purple-gradient, Inter-on-white, template decks. Production quality: commented, accessible, responsive, performant.
- **JS (every deck)**: keyboard nav (arrows, space, escape), touch/swipe, mouse wheel, progress/slide index, reveal-on-enter via Intersection Observer.
- **Aesthetics**: fonts from Google Fonts / Fontshare; atmospheric backgrounds, strong type hierarchy; abstract shapes/gradients/grids/noise/geometry over illustrations; inline CSS/JS unless a multi-file project is requested.

## PPT / PPTX Conversion

1. Prefer `python3` + `python-pptx` to extract text, images, notes.
2. If `python-pptx` is unavailable, ask whether to install it or fall back to a manual workflow.
3. Preserve slide order, speaker notes, extracted assets.
4. Run the same style-selection workflow as a new presentation.

## Common Mistakes

Generic startup gradients; system-font decks (unless intentionally editorial); bullet walls that break viewport fit; code blocks that scroll; fixed-height boxes that break on short screens.

## Integration

Called by: user directly, `/ai-build`. References: `STYLE_PRESETS.md`. See also: `/ai-prose` (prose content), `/ai-visual` (visual artifacts), `/ai-media` (generated insert visuals), `/ai-design` (aesthetic direction).

## Examples

User: "convert this PPTX to browser-native HTML"

```
/ai-slides convert /path/to/deck.pptx
```

Parses the PPTX, maps each slide to the HTML template, preserves images + notes, then validates viewport fit per slide at all 8 sizes.

$ARGUMENTS
