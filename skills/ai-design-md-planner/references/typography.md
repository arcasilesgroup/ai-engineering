# Typography

Choosing faces, pairing them, and building a scale that reads as designed. Read alongside `anti-slop.md`.

**Contents**
- [The typeface library](#the-typeface-library)
- [Pairing](#pairing)
- [Building the scale](#building-the-scale)
- [Optical adjustments](#optical-adjustments)
- [Weight discipline](#weight-discipline)
- [Measure and rhythm](#measure-and-rhythm)
- [Numerals and features](#numerals-and-features)
- [Variable fonts](#variable-fonts)
- [Delivery and fallbacks](#delivery-and-fallbacks)
- [Writing typography tokens](#writing-typography-tokens)

---

## The typeface library

Organized by register. **(F)** = free/open-source, **(C)** = commercial license required. There are strong open options in every category, so a good typographic system never requires a licensing budget.

### Neo-grotesque sans — neutral, structural, Swiss

The workhorse category. Neutral but not characterless.

- **Söhne** (C) — Klim's Helvetica reinterpretation; the current standard for considered neutral. Excellent Buch/Kräftig weights.
- **Neue Haas Grotesk** (C) — Helvetica as originally drawn, before the 1980s digitization damaged it.
- **Untitled Sans** (C) — Klim; slightly warmer and more workmanlike than Söhne.
- **Basis Grotesque** (C) — Colophon; subtle quirks that survive at small sizes.
- **Archivo** (F) — Omnibus-Type. Genuinely good, variable, with a real condensed family. Strongly underused.
- **Public Sans** (F) — USWDS; neutral, legible, institutionally credible. Used in the DESIGN.md spec's own examples.
- **Geist** (F) — Vercel; clean, modern, with a matching mono.
- **Inter** (F) — excellent, and everywhere. Usable *deliberately* — set optical sizing, enable `cv05`/`cv11` for the single-storey alternates, use the variable axes. Reflexive use is the problem, not the face.
- **Helvetica Now** (C) — the good modern Helvetica, with a genuine Micro optical size.

### Humanist sans — warmer, calligraphic skeleton

- **Ideal Sans** (C) — H&Co; unusually warm, subtle irregularity.
- **Freight Sans** (C) — large family, wide range.
- **IBM Plex Sans** (F) — engineered warmth; superb mono and serif companions in the same family. Excellent for clinical/technical registers.
- **Source Sans 3** (F) — Adobe; quiet, legible, dependable.
- **Work Sans** (F) — optimized for screen at middle sizes.

### Geometric sans — constructed, Bauhaus-descended

- **Futura** (C) / **Neue Haas Unica** (C) — the originals.
- **Jost** (F) — a well-made Futura interpretation, variable.
- **Space Grotesk** (F) — geometric with mono-derived quirks; distinctive without being loud.
- Avoid **Poppins**, **Montserrat**, **Century Gothic** as defaults — technically fine, but so overused they now signal absence of choice.

### Serif — text

For body copy, long-form, and anything wanting gravity.

- **Tiempos Text** (C) — Klim; the modern standard for screen serif body.
- **Lyon** (C) — Commercial Type; editorial authority.
- **Freight Text** (C) — warm, wide range of optical sizes.
- **Source Serif 4** (F) — Adobe; variable, excellent on screen, genuinely good.
- **Literata** (F) — Google Books; engineered for extended reading.
- **Newsreader** (F) — variable with an optical size axis; editorial character.
- **EB Garamond** (F) — a proper Garamond revival; classical register.
- **IBM Plex Serif** (F) — pairs natively with Plex Sans and Mono.

### Serif — display

High contrast, meant for large sizes.

- **Canela** (C) — Commercial Type; the serif-sans hybrid that defined a decade of luxury branding.
- **GT Sectra** (C) — Grilli Type; calligraphic and sharp, brilliant editorial display.
- **Ogg** (C) — Sharp Type; calligraphic, distinctive.
- **Tiempos Headline** (C) — tighter, more dramatic cut of Tiempos.
- **Fraunces** (F) — variable with `SOFT`, `WONK`, and optical size axes. Genuinely characterful and the strongest free display serif available.
- **Instrument Serif** (F) — high contrast, elegant, free.
- **Playfair Display** (F) — competent, but now the default "elegant" choice; treat it the way you'd treat Inter.

### Slab serif

- **Zilla Slab** (F) — Mozilla; geometric slab with personality.
- **Bitter** (F) — contemporary slab for screen.
- **Roboto Slab** (F) — neutral; the Inter of slabs.

### Monospace

For code, numerics, identifiers, timestamps, and anything tabular.

- **Berkeley Mono** (C) — the current enthusiast standard; genuine technical character.
- **Commit Mono** (F) — neutral, highly legible, customizable at download.
- **JetBrains Mono** (F) — tall x-height, designed for long code sessions.
- **IBM Plex Mono** (F) — pairs with the Plex family.
- **Geist Mono** (F) — pairs with Geist.
- **Departure Mono** (F) — pixel/bitmap; perfect for Retro-Futurist HUD, wrong for almost everything else.
- **SF Mono** / **Menlo** — available on Apple platforms; fine as a fallback.

### Condensed & display

- **Archivo Narrow** / **Archivo Condensed** (F) — the reliable condensed workhorse.
- **Anton** (F) — heavy condensed display; strong poster presence.
- **Roboto Condensed** (F) — neutral, map-and-label register.
- Avoid **Oswald** and **Bebas Neue** as defaults — heavily overused.

---

## Pairing

**The core rule: pair across classifications, not within them.** Two grotesques together (Inter + Helvetica) isn't a pairing, it's an accident nobody will read as intentional. The eye needs a clear reason for two faces to coexist.

Reliable pairing structures:

| Structure | Example | Register |
|---|---|---|
| Display serif + neutral sans | Fraunces + Archivo | Editorial, brand |
| Neutral sans + mono | Public Sans + JetBrains Mono | Technical, product |
| Serif body + condensed sans labels | Source Serif 4 + Archivo Narrow | Field guide, cartographic |
| Geometric display + humanist body | Jost + Source Sans 3 | Cultural, event |
| One superfamily | IBM Plex Sans + Serif + Mono | Systematic, engineered |

**Divide by job, not by size.** The strongest pairings assign each face a role: one carries the *voice* (display, headings, body prose), the other carries the *apparatus* (labels, metadata, numerics, UI chrome). Reader-facing vs. machine-facing is a legible distinction that survives at every size.

**Check the vertical proportions.** Two faces with wildly different x-heights look mismatched at the same nominal size. Either choose faces with compatible proportions, or compensate in the scale (set the smaller-x-height face a step larger).

**Two is the target. Three needs a reason** — usually a superfamily, or a genuinely distinct third job (e.g. a pixel mono used only for a single status readout).

**One is legitimate** if the face has enough range — a large family with real optical sizes and a variable axis can carry an entire system. But then the range must be *used*: a single face at three sizes and two weights is not a typographic system.

---

## Building the scale

Generate with a modular ratio, then hand-tune. The generation gives you coherence; the tuning gives you drama.

| Ratio | Value | Use |
|---|---|---|
| Minor third | 1.200 | Dense UI, dashboards, many levels |
| Major third | 1.250 | General product |
| Perfect fourth | 1.333 | Editorial, marketing |
| Golden | 1.618 | Very few levels, high drama |

From a 16px base at 1.25:

```
16 → 20 → 25 → 31 → 39 → 49 → 61
```

Round to sensible values and add the small end:

```
12, 14, 16, 20, 25, 31, 39, 48, 64
```

**Then break it at the display end.** Pure geometric scales are always too timid where you most need impact. If the top of the generated scale is 61px and the design wants a hero, take it to 88 or 120. The gap between body and display should feel like a *jump*, not a progression — that gap is what creates hierarchy.

The spec notes most design systems have **9–15 typography levels**, named semantically: `display`, `headline-lg/md/sm`, `body-lg/md/sm`, `label-lg/md/sm`, `caption`, `code`. Name by role, not by size, so an agent knows which to reach for.

---

## Optical adjustments

This is where a system stops looking like defaults. Every one of these is invisible individually and unmistakable in aggregate.

**Tracking varies with size.** Type is drawn to be spaced correctly at text sizes; at other sizes it needs help.

| Size | Tracking |
|---|---|
| Display (48px+) | −0.02 to −0.04em |
| Headline (24–48px) | −0.01 to −0.02em |
| Body (14–20px) | 0 |
| Small (11–13px) | +0.005 to +0.01em |
| Uppercase labels | +0.06 to +0.12em |

Uppercase set at default tracking looks broken rather than emphatic — uppercase letterforms were designed with more space around them than lowercase.

**Line-height moves inversely to size.**

| Size | Line-height |
|---|---|
| Display | 1.0–1.15 |
| Headline | 1.2–1.35 |
| Body | 1.5–1.7 |
| Small / labels | 1.3–1.45 |

Use unitless multipliers, which the spec explicitly recommends — they inherit correctly. A single line-height across the whole scale is a reliable tell.

**Optical sizing.** Faces with an `opsz` axis (Fraunces, Newsreader, Source Serif 4, Inter) adjust their contrast and spacing for the size they're set at. Use it — it's the difference between a display size that looks drawn for the job and one that looks scaled up.

---

## Weight discipline

**Two weights, far apart.** 400 and 700 reads as a decision. 400/500/600 reads as indecision — the steps are too close to distinguish, so they create visual noise without creating hierarchy.

If you need a third, make it a genuine extreme (300, 800, 900) with a specific job, not an intermediate.

Two related points:

- **Never synthesize.** Faux-bold and faux-italic (browser-generated when a real cut isn't loaded) look distinctly wrong. Load the real weights or don't use them.
- **Prefer size and space to weight for hierarchy.** Weight is the loudest tool and the first one overused. A system where hierarchy comes primarily from size, spacing, and color, with weight as the accent, is almost always more refined.

---

## Measure and rhythm

**Measure: 60–75 characters** for body text. This is the most-ignored typographic rule on the web and the one with the largest readability impact. Set it explicitly (`max-width: 65ch`) rather than letting the container decide.

Narrower (45–55ch) works for short-form and sidebars. Wider than 80ch and the eye loses the line return.

**Vertical rhythm.** Set spacing between text blocks as a function of the line height, not as arbitrary pixel values. Space *above* a heading should be noticeably larger than space below it — a heading belongs to the content that follows it, and getting this backwards is a common and very visible error.

---

## Numerals and features

Worth setting explicitly; the spec supports `fontFeature` and `fontVariation` on typography tokens.

- **`tnum` (tabular figures)** — mandatory for tables, prices, timers, any column of numbers. Proportional figures make columns jitter.
- **`onum` (oldstyle figures)** — figures with ascenders and descenders; excellent in editorial body text, wrong in UI.
- **`ss01`–`ss20` (stylistic sets)** — face-specific alternates. Inter's `cv05`/`cv11` give a single-storey `a` and `g`; Fraunces' `WONK` axis switches to more idiosyncratic forms.
- **`calt`, `liga`** — contextual alternates and ligatures; on by default, but disable `liga` in code contexts where `!=` shouldn't fuse.
- **`case`** — adjusts punctuation position for all-caps settings; use it on uppercase labels.

```yaml
typography:
  data-md:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: 400
    lineHeight: 1.45
    fontFeature: "'tnum' 1, 'liga' 0"
```

---

## Variable fonts

A single variable file replaces many static weights, and gives access to axes that static cuts can't express.

Standard axes: `wght` (weight), `wdth` (width), `slnt`/`ital`, `opsz` (optical size). Custom axes are common — Fraunces has `SOFT` and `WONK`.

Two cautions:

- **Constrain yourself anyway.** Variable fonts make it trivial to use eleven weights. Don't. Pick two or three instances and treat them as if they were the only cuts available.
- **Watch the payload.** A full variable font with many axes can be larger than the two static cuts you'd actually use. Subset it.

```yaml
typography:
  display-lg:
    fontFamily: Fraunces
    fontSize: 72px
    lineHeight: 1.05
    letterSpacing: -0.03em
    fontVariation: "'wght' 600, 'SOFT' 40, 'WONK' 1, 'opsz' 72"
```

---

## Delivery and fallbacks

- **Self-host** where possible — faster, no third-party dependency, and required by some privacy regimes.
- **`font-display: swap`** so text is readable during load, with a metrics-matched fallback (`size-adjust`, `ascent-override`) to prevent layout shift.
- **Subset aggressively** — Latin-only subsets are a fraction of the full file.
- **Specify a real fallback stack**, not just `sans-serif`. If the brand face fails to load, the fallback should still be a defensible choice.
- **Commercial licensing is per-use** — web, app, and desktop are typically separate. If the user's product ships a native app, flag it; a face licensed for web only is a real problem later.

Note the fallback stack in the DESIGN.md prose. The tokens carry `fontFamily` as a single name; the prose is where the full stack and licensing status belong.

---

## Writing typography tokens

Name by role, cover the full range, and set every property that carries a decision:

```yaml
typography:
  display:
    fontFamily: Fraunces
    fontSize: 72px
    fontWeight: 600
    lineHeight: 1.05
    letterSpacing: -0.03em
  headline-lg:
    fontFamily: Fraunces
    fontSize: 40px
    fontWeight: 600
    lineHeight: 1.15
    letterSpacing: -0.02em
  body-md:
    fontFamily: Archivo
    fontSize: 16px
    fontWeight: 400
    lineHeight: 1.6
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
```

Every level here differs in more than size — tracking, line-height, and family all carry information. That's what distinguishes a typographic system from a list of font sizes.
