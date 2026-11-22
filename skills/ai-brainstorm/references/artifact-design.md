# Artifact design — the visual language of an ai-engineering artifact

The house style for every HTML page **ai-engineering itself generates**:
a brainstorm, a research page, a recap, an issue report, an audit report.
Read it before writing one of those.

It is **not** the design system of the product a governed project builds. That
file is `.ai-engineering/DESIGN.md`, written by `ai-design-md-planner`. Two
documents, two audiences: this one is how the framework speaks, `DESIGN.md` is
how the product speaks.

The artifact is read next to the others, often in one review. Four artifacts in
four invented styles read as four products, and the reader spends attention on
the difference instead of the content. So an artifact starts from a template in
`templates/` and only its words change: copy the template, fill its sections,
and write no CSS and no script. The vocabulary below is chosen from, never
introduced around. Every artifact also carries the `{ai}` favicon as an
inline data URI in its `<head>`, before `<style>`:

```html
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 32 32%22%3E%3Crect width=%2232%22 height=%2232%22 rx=%227%22 fill=%22%23001E2B%22/%3E%3Crect x=%220.5%22 y=%220.5%22 width=%2231%22 height=%2231%22 rx=%226.5%22 fill=%22none%22 stroke=%22%2300ED64%22 stroke-opacity=%220.35%22/%3E%3Ctext x=%2216%22 y=%2217%22 text-anchor=%22middle%22 dominant-baseline=%22central%22 font-family=%22ui-monospace, Menlo, Consolas, 'DejaVu Sans Mono', monospace%22 font-size=%2214%22 font-weight=%22700%22 letter-spacing=%22-1%22%3E%3Ctspan fill=%22%2300ED64%22%3E%7B%3C/tspan%3E%3Ctspan fill=%22%23E8EEF7%22%3Eai%3C/tspan%3E%3Ctspan fill=%22%2300ED64%22%3E%7D%3C/tspan%3E%3C/text%3E%3C/svg%3E">
```

Inline, never a file: an artifact is one self-contained page opened from
`file://` — no sibling asset can be assumed to travel with it. The URI is a
single source in this document; when the `{ai}` mark changes, re-cut every
carrier of this line (the templates and this document).

## The styles and the script

The tokens, the layout rules, the components and the scroll-spy live in
`brand/components.css` and `brand/components.js`. `bun scripts/brand.ts gen`
writes them between the `/* brand:begin */` … `/* brand:end */` markers inside
`<style>` and the `<!-- brand:js:begin -->` … `<!-- brand:js:end -->` markers
before `</body>` of every template, so they arrive inside every template.
`bun scripts/brand.ts parity` fails a template whose marked bytes differ, and
`bun scripts/brand.ts artifact` checks the tokens against `brand/tokens.json`.
Never edit the marked bytes of a template or of a page copied from one.

## The rules that hold across every artifact

1. **Dark only, one signal.** Light mode is never generated. `--accent` is the
   one signal green and `--accent-dim` is that green dimmed for small text; links,
   focus and emphasis read one or the other. `--ok` / `--bad` / `--warn` mark
   state, `--purple` and `--orange` live inside a code block. The one other
   place chroma appears is a category chip (`.cat`): five hues (green, purple,
   amber, red, blue) group things, and the chip's word always names the
   category, so the colour never carries the meaning alone.
2. **Two voices.** Prose and headings are set in the sans stack; code, data and
   measurement — commands, paths, numbers, labels, table headers — are set in
   the mono one. Mono never sets a paragraph, and is never decoration for prose.
3. **A numbered document gets numbers.** Mono `01`, `02` above each `h2`, and a
   sticky nav once the artifact has more than five sections. The number is a
   coordinate a reviewer cites, not a flourish.
4. **Prose sits on the left edge.** A `p` runs the full container width,
   left-aligned — the same rails as a table, a bracket or a card. Centered or
   68ch-capped body text is the defect: it breaks the left edge everything else
   shares. Prose is never justified: uneven word gaps slow some readers
   (WCAG 1.4.8). Each section opens with one plain sentence, then the visual.
5. **Contrast floors are not style.** Body text ≥ 4.5:1, large or bold ≥ 3:1.
   The palette's pairs already clear the floor — reach for `--dim` and
   `--comment` before any new tint, and never tint text toward gray on the
   accent.
6. **Contain the overflow.** A `pre`, a flow diagram or a wide table scrolls
   inside its own panel (`overflow-x:auto` plus the thin scrollbar). The page
   itself never scrolls sideways, at any width.
7. **One role, one leading.** A component sets its own `line-height`, so a pill
   or a label renders identically inside a card, a table cell and a note.
8. **No entrance animation on content.** The only movement is a functional state
   change — the nav's active section, a hover. `prefers-reduced-motion` disables
   it; nothing is ever invisible while an animation runs. The active section is
   not painted by hand: the scroll-spy in `brand/components.js` is part of the
   shell. While the reader scrolls, the link whose section heading has cleared
   the sticky nav carries `.active` and `aria-current="location"`; the lead is
   the same 88px as `scroll-margin-top`.
9. **Structure is semantic.** `<header>` / `<nav>` / `<main>`, one `<section>`
   per numbered block, a skip link, `lang`, a `<title>`, and headings that never
   skip a level.
10. **A list of work is a list of items.** Anything the reader may act on — a
    ranked entry, a bug, a feature, a pull request — is an `.item`: a native
    `<details>` whose `<summary>` scans closed (id, title, chips, effort) and
    whose body explains open (plain-language context, evidence, cross-refs). The
    disclosure is native, never scripted and never animated open: keyboard,
    find-in-page and print keep working, and nothing is invisible while an
    animation runs. An item the reader might meet twice carries `id="i<number>"` on
    its first occurrence and `id="i<number>-s<NN>"` on every later one, so no id
    repeats and one section can link to the same row in another.
11. **A chip carries a key.** Any glyph whose meaning is colour plus a word —
    a band, a severity, a verdict — is repeated in the page's `.legend` with the
    rule that assigns it. A chip the reader cannot look up is decoration wearing
    a state's clothes. The legend sits with the first section that uses it.
12. **Never:** emoji as icons · a gradient as decoration · a second signal hue ·
    a colored left border wider than 1px (the one exception is the 3px bar of a
    `.callout`, the highlight) · a shadow without offset and blur · a card inside
    a card · a state chip whose colour has no legend.

## The component vocabulary

| Component | Class | Use |
|---|---|---|
| Section | `.container` + `section` + `h2 .num` | one numbered block of the document |
| Card | `.card` (+ `.src`) | a unit of prose with a heading, in a `grid` of two to four |
| Note | `.note` (+ `.ok` / `.warn` / `.danger`) | a rule, a warning, a decision the reader must not miss |
| Pill | `.pill` (+ `.p-ok` / `.p-bad` / `.p-warn` / `.p-fix` / `.p-dim`) | state inside a table cell or a heading |
| Table | `.tbl-wrap > table` | any comparative fact — capabilities, verbs, flags, thresholds; every `<th>` carries `scope="col"` |
| Bracket | `.bracket` (+ `.tag`) | a bordered inset that holds one diagram or one sample |
| Flow | `.flow` | a terminal-shaped diagram, in mono, scrolling in its own panel |
| Pipeline | `.pipe > .stage` | an ordered sequence where the boxes *are* the message |
| Tier | `.tiers > .tier` | ranked rows: name, body, measurement |
| Item | `.items > .item` (+ `.iid` / `.ititle` / `.imeta` / `.ibody` / `.kv` / `.ilbl`) | one expandable record: a native `<details>` whose summary scans closed and whose body explains open |
| Band | `.band` (+ `.band-p0` … `.band-p5`) | the priority chip on an item, always keyed by the page's `.legend` |
| Legend | `.legend > div` (+ `.lname`) | the key to the chips: a colour the reader cannot look up is decoration |
| Cross-ref | `.xref` | the "also in" line that ties one item's rows together across sections |
| Signals | `.sig` | the flat mono trail of counts and links an item carries (reactions, comments, labels, milestone) |
| Stats | `.stats > .stat` | a short row of counts, never a dashboard |
| Marks | `.check` / `.cross` / `.half` | yes · no · partial, inside a cell |
| Brand mark | `.hero .mark` | the `{ai}` mark at the top of the hero, so the page names its family before its subject |
| Highlight | `.callout` (+ `.is-bad` / `.is-warn`) | the one thing on the page the reader must take away; the only box with an accent bar |
| Category chip | `.cat` (+ `.c-green` / `.c-purple` / `.c-amber` / `.c-red` / `.c-blue`) | groups rows or cards; its word names the category |
| Card head | `.card .card-h` | a chip and a title on one line |
| Verdict card | `.card.is-good` / `.is-bad` / `.is-warn` | two sides compared: blocks vs informs, before vs after |
| Terminal card | `.card pre.term` (+ `.ok` / `.bad` / `.b`) | command output, pass and fail written as words |
| Diagram | `figure.diagram` + inline `svg role="img"` (+ `.dg-node` / `.dg-edge` / `.dg-head` / `.dg-lbl`) | how parts connect; a `<title>`, a `<desc>` and a `<details>` text version |
| Flow tree | `figure.bracket` + `pre.flow` (+ `.nd` / `.ed` / `.lb` / `.wd` / `.rd`) | a terminal-shaped tree; glyphs in `.ed` carry `aria-hidden` |
| Tabs | `.tabs > .tabpanel[data-tab]` (+ `data-key`, `data-badge`) | options side by side; the script builds the tab row, panels stack without it |
| Gains and costs | `ul.proscons > li.pro` / `li.con` | the sign drawn, the word hidden for screen readers |
| Code block | `.code > .code-head` + `pre` (+ `button.copy`) | a labelled sample with a copy button the script reveals |
| Diff lines | `pre .add` / `.del` | `+` and `-` written in the text, colour second |
| Filters | `.filters[data-target] > button.chip[data-filter]` | narrows rows tagged `data-tags`; the count is announced |
| Expand all | `.toolbar > button.tool[data-expand]` | opens or closes every item in one list |
| Steps | `ol.steps` | an ordered sequence the reader follows |
| Checklist | `ul.checklist` (+ `.state`) | criteria with their state written as a word |
| Keyboard key | `kbd` | a key the reader presses |
| Status message | `#live.sr[role=status]` | where copy, filter and expand results are announced |

## Source

ai-engineering (own), Apache-2.0. The values are LeafyGreen UI's
(`mongodb/leafygreen-ui`, Apache-2.0, taken verbatim): the palette and the
component grammar, not the identity — no MongoDB logo, wordmark or leaf is
reproduced anywhere, and no commercial font is shipped. `brand/tokens.json`
records them; `brand/components.css` declares them and every template carries
the same bytes.

## Done when

- The artifact renders at 320, 768 and 1440px with no sideways page scroll.
- Every text/ground pair clears its contrast floor.
- No heading level is skipped; the nav's links all resolve.
- The page carries its template's brand region unchanged — a diff in a token or
  a rule is a defect, not a preference.
- Scrolling marks the nav link of the section in view with `.active`, because
  the template's brand script is in the page, unchanged.
- Every chip on the page resolves in its `.legend`, and every `.item` opens to a
  body that says something the closed row did not.
