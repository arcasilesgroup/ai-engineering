---
name: ai-design-audit
description: Use when a web interface needs its visual defects found and fixed with measurements rather than opinions — misaligned rows, ragged card interiors, touch targets, rendered contrast over gradients and images, text printing over text, Gestalt proximity, divider lines that should be space, and type-scale drift — measured in a real browser across widths, and proved unchanged afterwards.
---

# AI Design Audit

A stylesheet is a claim. A painted pixel is the evidence. Everything here measures the second, because the defects that survive review are exactly the ones no declaration predicts: contrast against a gradient with grain over it, a row whose two cards start reading 68px apart, a label printing over another label at 320px, a card grid that groups the wrong things.

Serve the **built** output and point the audit at it. A dev server with hot reload measures a page nobody visits.

```bash
node scripts/audit.mjs --base http://127.0.0.1:4399 \
  --routes / /about /projects --widths 320 390 820 1440
```

`--checks` selects passes (`geometry contrast collision proximity type interior`); `--aa` relaxes the contrast target from AAA to AA; `--json out.json` writes findings and text anchors. Run it before touching anything.

## What each pass is asking

**geometry** — does the page fit, can a thumb hit it, does a heading follow the one above it. Sub-pixel borders on a pill radius, images shipping more resolution than their box can use, missing dimensions.

**contrast** — the ink is read from the element's own `color`; only the *ground* is sampled, because that is the part no token knows. Text over a photograph is where this earns its keep.

**collision** — glyph rects, not element boxes. Boxes overlap constantly and mean nothing.

**proximity** — for a set of like siblings, the gap between them against the largest gap inside one. Below 1.0 the space is grouping the wrong things and something else — usually a border — is arguing against it. Also inventories every stroke that is not a container edge.

**type** — one role, one answer. Two roles at the same size, face, weight and case whose leading differs by a hundredth is a typed value, not a decision.

**interior** — do containers in one row start reading on the same line, and does a component's inset scale with the type it holds.

Read [how to judge the output](references/reading.md) before acting on it: several shapes look like defects and are not, and the difference is usually written in the code beside them.

## The loop

1. Measure. `--json before.json`.
2. Judge each finding against [reading.md](references/reading.md). Kill the false positives out loud; a report that lists them next to real defects is worth nothing.
3. Fix, one change per commit. [fixes.md](references/fixes.md) carries the patterns that change a target or a gap without moving a single glyph.
4. Prove it: `--baseline before.json` reports how many text runs moved. For a fix that is meant to be invisible, the answer is zero.

Screenshots come last and answer one question — *does this read right?* — which no number answers. Capture in bands, not one full page: a tall page times a 2× scale runs past the compositor's texture limit and the capture comes back stitched, with every coordinate silently wrong.

## What the numbers cannot see

Whether the thing is any good. The audit finds a gap that contradicts itself, never a page that is correct and lifeless. When a finding and the design disagree, the design has the floor — but it has to say why, next to the value, or it is drift wearing a justification.
