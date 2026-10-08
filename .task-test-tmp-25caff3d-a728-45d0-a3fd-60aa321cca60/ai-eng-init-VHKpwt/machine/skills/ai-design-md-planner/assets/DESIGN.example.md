---
version: alpha
name: Kiln
description: Studio management for working ceramicists — kiln schedules, glaze recipes, and inventory for small production potteries.

colors:
  primary: "#8B4E34"
  secondary: "#5F594F"
  tertiary: "#2F6B62"
  neutral: "#F4F2EE"
  surface: "#FBFAF8"
  on-surface: "#23201B"
  subtle: "#EBCBB8"
  border: "#E8E4DD"
  error: "#9B3A2E"

typography:
  display:
    fontFamily: Fraunces
    fontSize: 56px
    fontWeight: 600
    lineHeight: 1.05
    letterSpacing: -0.025em
  headline-lg:
    fontFamily: Fraunces
    fontSize: 32px
    fontWeight: 600
    lineHeight: 1.18
    letterSpacing: -0.015em
  headline-sm:
    fontFamily: Fraunces
    fontSize: 21px
    fontWeight: 600
    lineHeight: 1.28
  body-lg:
    fontFamily: Archivo
    fontSize: 18px
    fontWeight: 400
    lineHeight: 1.65
  body-md:
    fontFamily: Archivo
    fontSize: 16px
    fontWeight: 400
    lineHeight: 1.6
  body-sm:
    fontFamily: Archivo
    fontSize: 14px
    fontWeight: 400
    lineHeight: 1.5
  label-caps:
    fontFamily: Archivo
    fontSize: 11px
    fontWeight: 500
    lineHeight: 1.3
    letterSpacing: 0.12em
  data-md:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: 400
    lineHeight: 1.45
    fontFeature: "'tnum' 1"
  data-sm:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: 400
    lineHeight: 1.4
    letterSpacing: 0.02em
    fontFeature: "'tnum' 1"

rounded:
  none: 0px
  sm: 2px
  md: 4px
  full: 9999px

spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 48px
  gutter: 24px
  margin: 48px

components:
  page:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.on-surface}"
    typography: "{typography.body-md}"
  divider:
    backgroundColor: "{colors.border}"
    height: 1px
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.surface}"
    typography: "{typography.label-caps}"
    rounded: "{rounded.sm}"
    padding: "{spacing.md}"
  button-primary-hover:
    backgroundColor: "#693A26"
    textColor: "{colors.surface}"
  button-secondary:
    backgroundColor: "{colors.neutral}"
    textColor: "{colors.primary}"
    typography: "{typography.label-caps}"
    rounded: "{rounded.sm}"
    padding: "{spacing.md}"
  card:
    backgroundColor: "{colors.neutral}"
    textColor: "{colors.on-surface}"
    rounded: "{rounded.md}"
    padding: "{spacing.lg}"
  text-meta:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.secondary}"
    typography: "{typography.body-sm}"
  chip-firing:
    backgroundColor: "{colors.subtle}"
    textColor: "#693A26"
    typography: "{typography.data-sm}"
    rounded: "{rounded.full}"
    padding: "{spacing.xs}"
  status-live:
    backgroundColor: "{colors.tertiary}"
    textColor: "{colors.surface}"
    typography: "{typography.data-sm}"
    rounded: "{rounded.sm}"
    padding: "{spacing.xs}"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.on-surface}"
    typography: "{typography.body-md}"
    rounded: "{rounded.sm}"
    padding: "{spacing.sm}"
  input-error:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.error}"
    typography: "{typography.body-sm}"
  tooltip:
    backgroundColor: "{colors.on-surface}"
    textColor: "{colors.surface}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.sm}"
    padding: "{spacing.sm}"
---

# Kiln

## Overview

Kiln is used by people whose hands are dirty. A potter checks it between pulls, on a tablet propped against a shelf in a workshop with north light and clay dust on everything. It holds things that matter and cannot be re-derived: firing schedules, glaze recipes worked out over years, what went into kiln load #418 and what came out of it.

The register is **Warm Analog crossed with Archival Institutional** — the visual language of a well-kept studio notebook rather than of software. It should feel like a record, not a dashboard. Permanent, legible at arm's length, unhurried.

What this direction gives up, deliberately: **density and speed**. Kiln will never show as much on one screen as a spreadsheet would, and it does not try to feel fast. The trade buys legibility in bad light and the sense that entered data is being kept rather than processed. For a tool where a lost glaze recipe is unrecoverable, that felt like the right side of the trade.

The system commits to warmth throughout. There is no pure white and no pure black anywhere in it.

## Colors

The palette is taken from the materials themselves. Every color in Kiln is sampled from something in a working pottery, and that constraint — rather than any preference — is what set the values.

- **Primary (#8B4E34):** *Fired clay.* The color of earthenware after oxidation firing. Carries all primary interaction: buttons, links, active states. It is a text-safe value (5.8:1 on card, 6.2:1 reversed) precisely so interaction never needs a second, lighter variant.
- **Secondary (#5F594F):** *Kiln ash.* The warm grey of wood-ash deposit. Reserved for metadata — timestamps, authorship, counts. It reads as recessive without disappearing.
- **Tertiary (#2F6B62):** *Copper oxide, reduction-fired.* The blue-green copper turns in a reduction atmosphere. This is the only cool color in the system and it has exactly one job: marking something **live** — a kiln currently firing. Nothing else may use it, and that scarcity is what makes a firing state readable at a glance across the room.
- **Neutral (#F4F2EE) and Surface (#FBFAF8):** *Unfired porcelain and bisque.* Two paper values a half-step apart. Nearly the entire interface is built from the gap between these two.
- **Subtle (#EBCBB8):** *Raw terracotta slip.* A tint of the primary ramp, used only as a chip fill for firing-cycle labels.
- **On-surface (#23201B):** *Iron-rich stoneware body.* The near-black. It carries a trace of the clay hue, which is why body text on this paper looks settled rather than printed on top.
- **Error (#9B3A2E):** *Overfired iron.* Derived from the same ramp as the primary, not imported from a stock alert palette. A failure in Kiln is a firing that went wrong, and it should look like one.

All neutrals are warm-tinted (OKLCH hue ≈ 55–60, chroma 0.004–0.010). No value in this system has R = G = B. The ramps were built in OKLCH with chroma peaking mid-range and the hue bending from 42° in the tints to 20° in the shades, so the clay colors behave like pigment rather than like a gradient.

## Typography

Two families, split by job, plus a mono for anything a kiln reports.

**Fraunces** carries the voice — display and headings. It is a variable serif with genuine optical-size and `SOFT`/`WONK` axes, which is why it holds up at 56px without the thin-stroke fragility that most display serifs show on screen. Its slight oddness is the point: it reads as drawn rather than specified, which is the register a studio notebook wants. Fallback: `Fraunces, "Source Serif 4", Georgia, serif`. SIL Open Font License.

**Archivo** carries the apparatus — body copy, labels, controls. A grotesque with enough neutrality to disappear behind Fraunces and enough width and weight range to handle small labels. It is deliberately not Inter: Inter would work, but its ubiquity would make the pairing read as a default rather than a choice. Fallback: `Archivo, "Helvetica Neue", Arial, sans-serif`. SIL Open Font License.

**JetBrains Mono** carries measured data — cone numbers, temperatures, kiln IDs, timestamps, glaze percentages. Tabular figures are enabled (`'tnum' 1`) so numeric columns align, which matters constantly in recipe tables. Fallback: `"JetBrains Mono", ui-monospace, SFMono-Regular, monospace`.

The scale runs 11 → 56px on a ≈1.25 ratio, hand-broken at the top so display sits well clear of headline. Tracking is optical: −0.025em at display, neutral through body, +0.12em on uppercase labels. Line height moves inversely with size, 1.05 at display to 1.65 at body-lg. Only two weights are used — 400 and 600 — and no third is permitted, because hierarchy here comes from family and size, not from weight.

All faces are open-licensed and self-hosted; no third-party font CDN is used.

## Layout

A **12-column grid** with 24px gutters and 48px outer margins on desktop, collapsing to a single column below 768px. Body measure is capped at **68 characters** — recipe notes are read, not scanned, and an uncapped paragraph is the fastest way to make a studio notebook feel like a form.

Spacing runs on a strict **8px base** with a 4px half-step for micro-adjustment inside chips and data cells. Nothing sits off the scale.

Density is intentionally uneven. Record views — a glaze recipe, a kiln log entry — get generous vertical rhythm and wide margins. Index views (the kiln list, the inventory table) tighten to 8px row padding and `data-md`. This contrast is the primary hierarchy device in the app: the shift in density tells you which kind of screen you are on before you read a word.

Layout is asymmetric by default. Content sits flush-left against the grid with the right margin left open for marginal annotations — firing notes, revision dates, who changed what. Centered text appears nowhere in this system.

## Elevation & Depth

Kiln is flat. There are **no drop shadows anywhere** in the interface, including on modals.

Depth is carried by three devices instead:

1. **Tonal layering** — the half-step between Surface (`#FBFAF8`) and Neutral (`#F4F2EE`). A card is not a floating object; it is a slightly different paper stock laid on the page.
2. **Hairline rules** — 1px in `border` (`#E8E4DD`), used to divide rather than to enclose. Rules run between rows and sections; they do not wrap around content to make boxes.
3. **Space** — the primary grouping tool. Related items sit 8px apart, unrelated groups 48px. Most apparent depth problems in this system are grouping problems and should be solved here first.

Overlays (dropdowns, the recipe editor) sit on Surface with a full-strength 1px rule and no scrim blur. Because there is no shadow language, an overlay is distinguished by having a border where nothing else does.

## Shapes

The shape language is **near-square**. Radii are deliberately small and hierarchical rather than uniform: inputs and buttons at `2px`, cards at `4px`, and `9999px` reserved exclusively for firing-cycle chips, where the pill shape marks them as a distinct class of object rather than as a container.

Nothing in the system uses a radius above 4px except those chips. The near-square language comes from kiln shelves and stacked greenware; it also keeps the interface reading as a record rather than as a consumer app.

Borders are 1px solid `border` (`#E8E4DD`) at rest and 1px solid `primary` on focus. Focus rings are 2px offset in `primary`, which clears 3:1 against both Surface and Neutral. Border radius and border color are specified here rather than as tokens because the DESIGN.md component schema has no `borderColor` sub-token — these values are normative regardless.

## Components

**Buttons.** Primary is a solid fill in `primary` with Surface text and `label-caps` — uppercase, tracked, small. Secondary is a `neutral` fill with `primary` text. There is no tertiary or ghost button; if a third level of action is needed on a screen, the screen has too many actions. Hover darkens the fill to `#693A26`; there is no lift, scale, or shadow change.

**Chips (`chip-firing`).** Pill-shaped, `subtle` fill, `data-sm` type. Used only for firing cycles — bisque, glaze, reduction. Never used as a generic tag.

**Status (`status-live`).** The only element permitted to use `tertiary`. Marks a kiln currently firing. Because it is the sole cool color in an otherwise warm interface, it is findable peripherally, which is the entire design requirement.

**Cards.** `neutral` fill, 4px radius, 24px padding, no border and no shadow — the tonal step alone separates them. Cards are for genuinely discrete records (one kiln load, one recipe). Lists of properties inside a card are plain rows with hairline rules, not nested cards.

**Inputs.** Surface fill with a 1px `border` rule, 2px radius, `body-md` at full size — inputs use body type rather than a smaller UI size because they are often filled in with a stylus, standing up, in poor light. Error state switches text to `error` and the rule to `error`; an inline message and an icon always accompany it, never color alone.

**Data tables.** `data-md` with tabular figures, 8px row padding, hairline rules between rows, no zebra striping, no vertical rules. Numeric columns right-align; identifier columns left-align.

**Tooltips.** `on-surface` fill with Surface text — the one inversion in the system. 150ms delay in, no delay out.

## Do's and Don'ts

- **Do** keep `tertiary` (#2F6B62) exclusively on live-firing indicators. It is the only cool color in the interface and its findability depends entirely on scarcity — a second use anywhere destroys the signal.
- **Don't** introduce a shadow. If something needs to feel raised, use the Surface→Neutral tonal step or a hairline rule. The absence of shadow is a system-level commitment, not an oversight.
- **Do** use `data-md`/`data-sm` for every cone number, temperature, kiln ID, percentage, and timestamp. Numbers set in Archivo will not align in columns and will look wrong next to numbers that do.
- **Don't** add a third font weight. Hierarchy comes from family and size. If a heading isn't reading as a heading, it needs more space above it, not more weight.
- **Do** cap body text at 68 characters. Recipe and firing notes are read at length.
- **Don't** center text. The system is flush-left throughout, including headings, empty states, and modals.
- **Do** pair every error state with an icon and a written message. Studio lighting is bad and roughly 8% of the audience cannot rely on a red/green distinction.
- **Don't** use pure `#FFFFFF` or `#000000`, including for imagery backgrounds and PDF exports. Every neutral in this system is warm-tinted, and an untinted value next to them reads as a defect.
- **Do** let index views be denser than record views. The density difference is the primary wayfinding cue in the app.
- **Don't** wrap content in a card by default. Cards mean "this is one discrete record." A list of fields is a list, with rules between it.
