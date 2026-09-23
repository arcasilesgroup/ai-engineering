# Fixes that change what you meant and nothing else

The hard part of a visual fix is not the change; it is proving the change was the only one. Run with `--baseline before.json` afterwards and read the count of moved text runs. For anything meant to be invisible, that count is zero.

## Grow a touch target without moving its text

```css
padding-block: 10px;
margin-block: -10px;
```

The touch box grows, the glyphs stay, the rhythm of the block around it is identical. Two traps:

**Vertical padding on an *inline* box paints and hits but does not push its neighbours**, so it reaches into whatever sits below and takes clicks meant for that. Give the element `inline-block` first.

**Do not reach for `inline-flex` to get `align-items: center`.** It makes the element a flex *container*, and a flex container discards the whitespace between a text node and a following element — the space before a trailing arrow vanishes and the whole group shifts. An element that is already a flex item is blockified anyway, so the padding is layout without declaring anything.

Where the box *is* the thing you see — a pill with a border and a fill on hover — there is nothing to borrow back. Raise its `min-height` and accept the four pixels.

## Make a row read from one line

Top-anchor the stack. `justify-content: flex-end` agrees the bottoms; the slack then collects at the bottom, which is usually where a watermark or a lift already lives, and reads as room rather than as a gap.

Check the narrow case in the same commit. Two labels that share a line at 1440 may not fit at 320, and a stack anchored the other way was the only thing keeping them apart.

## Separate by air instead of a line

Move whatever vertical rhythm the rule was carrying into the margin, and set the gap from the ratio rather than by eye: the space *between* two blocks against the largest space *inside* one. 1.5× is a floor that survives an argument.

A rule that sits between two halves of a two-column pair disappears when only one half exists. That is not a style violation, it is a line pointing at nothing.

## Derive the gutter, do not pick it

A grid gap has one job: make a card group with itself before it groups with its neighbour. Find the largest break inside the cards it separates and take 1.5× of that. Every card grid on a site can then share one token, and the number has an argument attached instead of a taste.

## Let the inset follow the type

Take the base component's inset ÷ its largest title. Apply that ratio to each variant's own title size. A loud variant then gets room in proportion to what it holds, instead of a bigger title in the same box.

## Collapse a type scale without flattening it

Same size, same face, same weight, same case, different leading by a hundredth: pick one. Genuinely different leadings at one size are usually two roles — a lede is not a body paragraph — and collapsing those loses the hierarchy.

Before changing any value, look for the reason beside it. Whole-pixel line boxes on pills, an italic's optical tracking and a display ladder that tightens as it grows are all decisions that look exactly like drift from the outside.

## Prove it

```bash
node scripts/audit.mjs --base $URL --routes … --widths … --json before.json   # on the branch point
# … make the change …
node scripts/audit.mjs --base $URL --routes … --widths … --baseline before.json
```

Then a pixel diff, if the project has one, and eyes last. The numbers say nothing moved; only a person says it reads right.
