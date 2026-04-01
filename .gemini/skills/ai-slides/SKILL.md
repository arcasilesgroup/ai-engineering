---
name: ai-slides
description: Use when creating a presentation deck from scratch, converting PowerPoint to browser-native HTML, or improving layout and motion in existing HTML slides. Trigger for 'create a talk deck', 'pitch deck', 'workshop slides', 'convert my PPTX', 'presentation for the all-hands'. Generates zero-dependency self-contained HTML with keyboard/touch navigation and viewport-safe layout.
effort: high
argument-hint: "new|convert|enhance [topic]"
tags: [presentation, html, css]
---



# Slides

## Purpose

Create zero-dependency, animation-rich HTML presentations that run entirely in the browser. Helps non-designers discover their aesthetic through visual exploration rather than abstract choices. Converts PowerPoint decks to web. Enforces viewport fit as a hard gate.

## When to Use

- `new`: creating a talk deck, pitch deck, workshop deck, or internal presentation from scratch
- `convert`: converting `.ppt` or `.pptx` slides into an HTML presentation
- `enhance`: improving an existing HTML presentation's layout, motion, or typography

## Process

### Step 1 -- Detect Mode

Choose one path based on user input:
- **New presentation**: user has a topic, notes, or full draft
- **PPT conversion**: user has `.ppt` or `.pptx`
- **Enhancement**: user already has HTML slides and wants improvements

### Step 2 -- Discover Content

Ask only the minimum needed:
- purpose: pitch, teaching, conference talk, internal update
- length: short (5-10 slides), medium (10-20), long (20+)
- content state: finished copy, rough notes, topic only

If the user has content, ask them to paste it before styling.

### Step 3 -- Discover Style (Preview-First)

Default to visual exploration. If the user already knows the desired preset, skip previews and use it directly.

Otherwise:
1. Ask what feeling the deck should create: impressed, energized, focused, inspired
2. Generate **3 single-slide preview files** in a `slide-previews/` directory
3. Each preview must be self-contained, show typography/color/motion clearly, and stay under roughly 100 lines of slide content
4. Ask the user which preview to keep or what elements to mix

Use the preset guide in `STYLE_PRESETS.md` when mapping mood to style.

### Step 4 -- Build the Presentation

Output either `presentation.html` or `[presentation-name].html`. Use an `assets/` folder only when the deck contains extracted or user-supplied images.

Required structure:
- semantic slide sections (`main`, `section`, `nav`)
- viewport-safe CSS base from `STYLE_PRESETS.md` (copy verbatim, then theme on top)
- CSS custom properties for theme values
- presentation controller class (see JS requirements below)
- Intersection Observer for reveal animations
- `prefers-reduced-motion` support

### Step 5 -- Enforce Viewport Fit (Hard Gate)

Rules (non-negotiable):
- every `.slide` must use `height: 100vh; height: 100dvh; overflow: hidden;`
- all type and spacing must scale with `clamp()` (**Warning:** never use `-clamp(...)` -- browsers ignore negated CSS functions silently. Use `calc(-1 * clamp(...))` instead.)
- when content does not fit, split into multiple slides
- never solve overflow by shrinking text below readable sizes
- never allow scrollbars inside a slide

Use the density limits and mandatory CSS block in `STYLE_PRESETS.md`.

### Step 6 -- Validate at 8 Viewport Sizes

Check the finished deck at these sizes:
- Desktop: 1920x1080, 1440x900, 1280x720
- Tablet: 1024x768, 768x1024
- Mobile: 375x667, 414x896
- Landscape phone: 667x375

If browser automation is available, verify no slide overflows and that keyboard navigation works.

If no browser automation is available: manually review CSS for viewport fit using the density limits in STYLE_PRESETS.md. Document which sizes were NOT verified and flag for manual QA.

### Step 7 -- Deliver

At handoff:
- delete temporary preview files unless the user wants to keep them
- open the deck with the platform-appropriate opener (`open` on macOS, `xdg-open` on Linux, `start` on Windows)
- summarize file path, preset used, slide count, and easy theme customization points

## Quick Reference

| Slide Type | Maximum Content |
|------------|-----------------|
| Title | 1 heading + 1 subtitle + optional tagline |
| Content | 1 heading + 4-6 bullets or 2 paragraphs |
| Feature grid | 6 cards maximum |
| Code | 8-10 lines maximum |
| Quote | 1 quote + attribution |
| Image | 1 image, ideally under 60vh |

## Non-Negotiables

1. **Zero dependencies**: one self-contained HTML file with inline CSS and JS
2. **Viewport fit is mandatory**: every slide fits inside one viewport with no internal scrolling
3. **Show, don't tell**: use visual previews instead of abstract style questionnaires
4. **Distinctive design**: avoid generic purple-gradient, Inter-on-white, template-looking decks
5. **Production quality**: code commented, accessible, responsive, performant

## JavaScript Requirements

Every presentation must include:
- keyboard navigation (arrow keys, space, escape)
- touch / swipe navigation
- mouse wheel navigation
- progress indicator or slide index
- reveal-on-enter animation triggers via Intersection Observer

## PPT / PPTX Conversion

1. Prefer `python3` with `python-pptx` to extract text, images, and notes
2. If `python-pptx` is unavailable, ask whether to install it or fall back to manual workflow
3. Preserve slide order, speaker notes, and extracted assets
4. After extraction, run the same style-selection workflow as a new presentation

## Implementation Details

- Fonts from Google Fonts or Fontshare
- Prefer atmospheric backgrounds, strong type hierarchy, clear visual direction
- Use abstract shapes, gradients, grids, noise, and geometry rather than illustrations
- Use inline CSS and JS unless the user explicitly wants a multi-file project

## Integration

- **Called by**: user directly, `/ai-dispatch`
- **References**: `STYLE_PRESETS.md` (same directory) for CSS base, presets, and validation rules
- **Related**: `ai-media` (generated visuals for insert shots)
- **See also**: `/ai-write` (prose content); `/ai-slides` handles presentation format, `/ai-write` handles narrative

## Common Mistakes

- Generic startup gradients with no visual identity
- System-font decks unless intentionally editorial
- Long bullet walls that break viewport fit
- Code blocks that need scrolling
- Fixed-height content boxes that break on short screens
- Skipping the viewport validation step
- Generating previews when the user already named a preset

$ARGUMENTS
