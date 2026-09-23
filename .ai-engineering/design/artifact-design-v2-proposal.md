# Artifact Design v2 — Proposal

> Merge this into `skills/ai-design/references/artifact-design.md` via PR.
> Adds: page skeleton, body text alignment, component usage rules, footer format.
> CSS block: the `p` rule changes from `margin-bottom:var(--s3)` to `margin:0 auto var(--s3);text-align:center` (already applied to all research files).

---

## The page skeleton

Every standalone artifact follows this HTML structure. Copy it verbatim; change
only the content inside each element. `spec.html` and `plan.html` omit the
`<header class="hero">` and start at `<nav>`.

```html
<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,…">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Research NNN — Title</title>
<style>/* THE BLOCK — copy verbatim from §The block */</style>
</head>
<body>
<a class="skip" href="#main">Saltar al contenido</a>

<header class="hero">
  <span class="corner tl"></span><span class="corner tr"></span>
  <span class="corner bl"></span><span class="corner br"></span>
  <div class="stamp">Research · NNN · YYYY-MM-DD</div>
  <h1>Primary <span class="x">keyword</span><br>Secondary line</h1>
  <p class="sub">One or two sentences: <strong>what</strong> this report covers and <strong>why</strong>.</p>
  <div class="meta">tools used: <b>tool-a</b> · <b>tool-b</b><br>
  degraded-tool: <b>tool-c</b> (reason)</div>
</header>

<nav>
  <a href="#s1"><b>01</b>Section title</a>
  <a href="#s2"><b>02</b>Section title</a>
  <!-- one <a> per <section>, numbered, matching h2 .num -->
</nav>

<main id="main">
<div class="container">

<section id="s1">
<h2><span class="num">01</span>Section title</h2>
<!-- content -->
</section>

<section id="s2">
<h2><span class="num">02</span>Section title</h2>
<!-- content -->
</section>

<!-- more sections… -->

</div>
</main>

<footer>
  <span class="x">{</span>ai<span class="x">}</span> Engineering · Research NNN · YYYY-MM-DD<br>
  tools: list · degraded: list
</footer>
</body>
</html>
```

## Body text alignment

Body text (`p`) is **justified** with hyphenation, spanning the full container
width. Justified text distributes word spacing evenly across the line, creating
clean edges on both sides. `hyphens:auto` allows syllable breaks to reduce
rivers of white space. No `max-width` cap — the text uses the same width as
tables, brackets, and cards.

```css
p{color:var(--dim);margin:0 auto var(--s3);text-align:justify;hyphens:auto}
```

Lists (`ul`, `ol`) stay **left-aligned** with `max-width:var(--measure)` —
justified lists with short lines create ugly gaps.

## When to use which component

| Content | Component | Why |
|---|---|---|
| A paragraph of prose | `p` | Default body text, centered at --measure |
| A data point or code sample in a bordered box | `.bracket` + `.tag` | The corner marks signal "this is evidence, not prose" |
| A comparison of items (2–4) | `.grid.g2` / `.g3` / `.g4` + `.card` | Cards force equal height and shared alignment |
| A rule, warning, or key decision | `.note` (+ `.ok` / `.warn` / `.danger`) | Draws the eye; the color signals severity |
| A row of summary counts | `.stats` + `.stat` | Use for ≤8 metrics; more belongs in a table |
| A comparative fact across rows | `.tbl-wrap` + `table` | Every table gets the wrapper for border + scrollbar |
| A yes/no/partial verdict | `.pill` + `.p-ok` / `.p-bad` / `.p-warn` | Inline in table cells or headings |
| A ranked list of findings | `.grid.gN` + `.card` | Each card = one finding with heading + body |

## Footer format

Every standalone artifact ends with:

```html
<footer>
  <span class="x">{</span>ai<span class="x">}</span> Engineering · Research NNN · YYYY-MM-DD<br>
  tools: tool-a, tool-b · degraded: tool-c
</footer>
```

The `{ai}` mark uses `.x` for the green braces. The second line lists tools
used and tools absent, separated by `·`.

## CSS changes

### 1. Body text — justified, full-width

In the `p` rule within the CSS block, change:

```css
/* BEFORE */
p{color:var(--dim);max-width:var(--measure);margin-bottom:var(--s3)}

/* AFTER */
p{color:var(--dim);margin:0 auto var(--s3);text-align:justify;hyphens:auto}
```

No `max-width` — spans the full container like tables, brackets, cards.
Lists stay `max-width:var(--measure)` for readability with bullets/numbers.

### 2. Section spacing — tighter

```css
/* BEFORE */
section{padding:64px 0 52px;...}

/* AFTER */
section{padding:56px 0 44px;...}
```

### 3. h3 hierarchy — more weight

```css
/* BEFORE */
h3{...font-weight:640;margin:var(--s6) 0 var(--s3)}

/* AFTER */
h3{...font-weight:660;margin:var(--s5) 0 var(--s3)}
```

### 4. Note text — left-aligned

```css
/* ADD to .note p */
.note p{...text-align:left}
```

### 5. Ordered lists — custom counters

```css
/* REPLACE default ol/ul/li block */
ul{margin:var(--s3) 0 var(--s5) var(--s5)}
ol{margin:var(--s3) 0 var(--s5);text-align:left;list-style:none;padding-left:0;counter-reset:ref}
li{color:var(--dim);font-size:14px;line-height:1.6;margin-bottom:var(--s3);padding-left:var(--s2)}
ol li{counter-increment:ref;padding-left:2.4em;position:relative}
ol li::before{content:counter(ref) ".";position:absolute;left:0;color:var(--comment);font-family:var(--mono);font-size:12px;width:2em;text-align:right}
```

Numbers are mono, gray, right-aligned under the section title.

### 6. Buttons — owner actions

```css
/* ADD */
.btn{display:inline-block;border:1px solid rgba(0,237,100,.35);border-radius:999px;padding:8px 18px;margin:var(--s2) 0;color:var(--accent);font-family:var(--mono);font-size:12px;text-decoration:none;transition:background .15s}
.btn:hover{background:rgba(0,237,100,.08);text-decoration:none}
```

All changes appear twice in the file (main CSS block and copy-paste block).
Both must be updated.
