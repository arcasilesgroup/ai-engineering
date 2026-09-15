# The brand, in one file

`brand/tokens.json` is the single source of truth for how `{ai} engineering` looks.
Every colour, every type step, every corner radius and every shadow in the product —
the `ai-eng` CLI, the landing site, the product blueprint and the HTML artifacts the
framework generates — is declared there once and derived from there.

Nothing downstream invents a value. If you want to change the brand, you change this
file and run one command.

## Where it comes from

The palette is LeafyGreen UI, MongoDB's design system, taken **verbatim** from
[`mongodb/leafygreen-ui`](https://github.com/mongodb/leafygreen-ui/blob/main/packages/palette/src/palette.ts)
(`packages/palette/src/palette.ts`, Apache-2.0). We adopt the palette, the type
treatment, the geometry and the component shapes — the visual grammar.

We do **not** adopt the identity: no MongoDB logo, wordmark or leaf glyph appears
anywhere in this repository, and none may be added. Those are trademarks, and this
system is `{ai} engineering`'s own.

Two deliberate substitutions, both stated rather than hidden:

- **Type.** MongoDB's own faces (Euclid Circular A, and the condensed display face on
  mongodb.com) are commercial and are not shipped. Archivo stands in for the language,
  JetBrains Mono keeps the instruments. See `DESIGN.md` in the landing site.
- **Artifacts.** The generated HTML artifacts (`spec.html`, `plan.html`, a recap) name
  system font stacks instead of the brand's, because an artifact has to render when it
  is opened from a folder with no network and no installed webfont.

## The commands

Run these from the repository root.

| Command | What it answers |
|---|---|
| `bun scripts/brand.ts check` | Is `tokens.json` itself valid — every reference resolvable, every colour family running dark to light, every required section present? |
| `bun scripts/brand.ts gen` | Write everything the tokens produce. Never hand-edit those files; this command owns them. |
| `bun scripts/brand.ts parity` | Does what is committed still match the tokens? Fails when someone edited a generated file by hand — and when the `theme-color` meta tag, the one palette value that lives in hand-written markup, has gone stale. |
| `bun scripts/brand.ts contrast` | Is every text-on-surface pair legible? Prints each measured WCAG 2.1 ratio and the level it must reach. |
| `bun scripts/brand.ts artifact` | Do the inline token blocks in the generated artifacts still match the brand? |
| `bun scripts/brand.ts legacy` | Has the previous palette really gone from both repositories? |

## What keeps the gates honest

A gate that only ever says yes is indistinguishable from one that stopped checking. Three
components here had that property until they were given an oracle, and each one turned out to
be wrong in a way nothing else could see:

| Test | What it defends | What it found |
|---|---|---|
| `tests/brand-check.spec.ts` | the validator, fed a declaration that breaks each rule | the validator **crashed** on a malformed entry instead of reporting it, and a later version of it demanded the wrong type for `lineHeight` — a validator that breaks the build on a valid file |
| `tests/brand-contrast.spec.ts` | the WCAG maths, against published values (`#767676` passes AA on white, `#777777` does not) | pins the border decision: `#5C6C75` measured 2.76:1 on a raised surface, which is why `--border` is `gray.base` |
| `tests/brand-generated.spec.ts` | that `gen` computes the *right* thing, not merely a stable thing | a broken breakpoint derivation left `design.json` claiming the site has no responsive thresholds — with `parity` still green |

Run them with `bun test tests/brand-*.spec.ts`, or as part of `bun test`.

## What `gen` writes

| File | Who reads it |
|---|---|
| `../ai-engineering-web/src/styles/tokens.css` | The landing site. Its CSS custom properties are the names the components already use. |
| `../ai-engineering-web/src/styles/tokens.json` | **The declaration itself, byte-for-byte.** The site consumes the CSS, not this file — it exists so somebody working only in that repository can read the whole system: the semantic layer, the reason beside each value, the contrast pairs, the artifact vocabulary. Generated and parity-checked, so "verbatim" is enforced rather than promised. |
| `src/theme.ts` | The CLI. The banner's brand green and the terminal-native status marks. |
| `../ai-engineering-web/.impeccable/design.json` | The design record the `impeccable` skill reads: every colour with its ramp, the type scale, the shadows, and the contrast table. |

`gen` is idempotent: running it twice changes nothing the second time. `parity` is what
proves that, and it is the reason a hand edit to `tokens.css` cannot survive a review.

Two ways to check it, depending on whether the work is committed:

```sh
# Before committing (what to run here and now): the artifacts must hash identically
# across two runs.
shasum ../ai-engineering-web/src/styles/tokens.css src/theme.ts \
       ../ai-engineering-web/.impeccable/design.json \
       ../ai-engineering-web/src/styles/tokens.json > /tmp/before
bun scripts/brand.ts gen && shasum -c /tmp/before      # every line: OK

# After committing: the criterion's own form, which can only be empty once the
# generated files are in the tree's history.
git status --porcelain -- ../ai-engineering-web/src/styles/tokens.css \
                            ../ai-engineering-web/src/styles/tokens.json \
                            ../ai-engineering-web/.impeccable/design.json src/theme.ts
```

## If you are not a coder

Read `tokens.json` top to bottom. The first section after the provenance note is the
raw palette — eight colour families, each with its shades ordered from darkest to
lightest. The section after that, `semantic`, gives those shades a **job**: this one is
the page background, this one is a border, this one is text you must be able to read.
The rest describes type, corners, shadows and motion.

The rules that matter are written as `purpose` strings beside each token. They are the
reason a value exists, and they are the thing to read before changing one.
