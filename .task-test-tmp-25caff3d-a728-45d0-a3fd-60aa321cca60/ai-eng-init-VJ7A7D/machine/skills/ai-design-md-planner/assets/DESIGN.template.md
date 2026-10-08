<!--
DESIGN.md skeleton. Delete every comment before writing the file out.

Rules that decide whether this lints clean:
  - Sections must appear in the order below. Omit any you don't need; don't reorder.
  - `primary` color is required, or `missing-primary` fires.
  - Every COLOR token must be referenced by some component, or `orphaned-tokens` fires.
  - Component sub-tokens are limited to exactly these eight:
      backgroundColor, textColor, typography, rounded, padding, size, height, width
    borderColor / shadow / gap are NOT valid — put those in the prose.
  - Define backgroundColor and textColor together so contrast is actually checked (AA = 4.5:1).
  - Top-level YAML keys are only: version, name, description, omitted,
    colors, typography, rounded, spacing, components.

The prose carries the argument; the tokens carry the values. Write prose that explains
WHY, using descriptive color names ("weathered oxide"), and let the tokens carry the
systematic names (`tertiary`). Restating hex codes in prose wastes the section.
-->
---
version: alpha
name: <System name — a real name, not "Design System">
description: <One line: what this is for and who uses it>

# omitted:
#   - section: rounded
#     reason: "<why this genuinely doesn't apply>"

colors:
  # Semantic names. Derive ramps per color-craft.md — tinted neutrals, tapered
  # chroma, bent hue. Nothing straight out of a framework's default palette.
  primary: "#______"
  secondary: "#______"
  tertiary: "#______"       # the accent — one job, under 5% of the surface
  neutral: "#______"
  surface: "#______"
  on-surface: "#______"
  border: "#______"
  error: "#______"          # derived from the brand family, not stock red

typography:
  # 9–15 levels, named by role. Every level should differ in more than size —
  # tracking, line-height, and family all carry information.
  display:
    fontFamily: <Face>
    fontSize: __px
    fontWeight: ___
    lineHeight: 1.05        # tight at display sizes
    letterSpacing: -0.03em  # negative at display sizes
  headline-lg:
    fontFamily: <Face>
    fontSize: __px
    fontWeight: ___
    lineHeight: 1.15
    letterSpacing: -0.02em
  body-md:
    fontFamily: <Face>
    fontSize: 16px
    fontWeight: 400
    lineHeight: 1.6         # loose at body sizes
  label-caps:
    fontFamily: <Face>
    fontSize: 11px
    fontWeight: 500
    lineHeight: 1.3
    letterSpacing: 0.12em   # uppercase needs air

rounded:
  # Hierarchical, or deliberately uniform-zero. One radius on everything is a tell.
  none: 0px
  sm: __px
  md: __px
  full: 9999px

spacing:
  # Pick a 4px or 8px base and stay on it.
  xs: 4px
  sm: 8px
  md: 16px
  lg: 32px
  xl: 64px

components:
  # This is where tokens become usable and where the linter does its real work.
  # Use {references}, not literals. Cover real states.
  page:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.on-surface}"
    typography: "{typography.body-md}"
  button-primary:
    backgroundColor: "{colors.tertiary}"
    textColor: "{colors.surface}"
    typography: "{typography.label-caps}"
    rounded: "{rounded.sm}"
    padding: "{spacing.md}"
  button-primary-hover:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.surface}"
  button-secondary:
    backgroundColor: "{colors.neutral}"
    textColor: "{colors.primary}"
    rounded: "{rounded.sm}"
    padding: "{spacing.md}"
  card:
    backgroundColor: "{colors.neutral}"
    textColor: "{colors.on-surface}"
    rounded: "{rounded.md}"
    padding: "{spacing.lg}"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.on-surface}"
    rounded: "{rounded.sm}"
    padding: "{spacing.sm}"
  input-error:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.error}"
  # Add a component for any color token not yet referenced above,
  # or delete that token.
---

# <System name>

## Overview

<!-- The holistic description: brand personality, audience, usage conditions, and the
     emotional register. This is what an agent falls back on when a specific rule
     doesn't exist, so it has to carry a real point of view.
     State the named direction and — importantly — what it gives up. -->

## Colors

<!-- Lead with the palette's logic and its SOURCE. Name the referent; that's what
     makes the file feel authored rather than generated. Then one line per color
     saying what it is FOR, not what its hex value is. -->

- **Primary (#______):** <descriptive name> — <what it's for>
- **Tertiary (#______):** <descriptive name> — the sole driver for interaction
- **Neutral (#______):** <descriptive name> — <what it's for>

## Typography

<!-- Which faces, why these two, and what job each one has. Mention the fallback
     stack and licensing status here — the tokens only carry a single family name. -->

## Layout

<!-- Grid model, spacing base, density posture, symmetric vs asymmetric, measure
     for body text (60–75ch). Say what the layout does at breakpoints. -->

## Elevation & Depth

<!-- How hierarchy is conveyed. If flat, say what replaces shadow — borders, tonal
     layers, spacing. If shadows are used, give them a light direction and a
     palette-derived color, and specify them HERE since `shadow` isn't a valid token. -->

## Shapes

<!-- The shape language and why. Border treatment lives here too, since
     `borderColor` isn't a valid component sub-token. -->

## Components

<!-- Per-component guidance beyond what the tokens express: states, sizing rules,
     when to use which variant, what's forbidden. -->

## Do's and Don'ts

<!-- Specific and enforceable FOR THIS SYSTEM. This section is what survives contact
     with a future agent under time pressure, so make every line actionable.
     Generic advice ("maintain good contrast") wastes the slot. -->

- Do <specific rule>
- Don't <specific failure this system is prone to>
