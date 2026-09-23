# Artifact design — the visual language of an ai-engineering artifact

The house style for every HTML page **ai-engineering itself generates**:
`spec.html`, `plan.html`, a recap, a research page, an issue report, a design
direction, an audit report. Read it before writing one of those.

It is **not** a design system for the product a governed project builds. That is a
different job with a different owner: ai-design routes *that* work to whatever
design skill is installed, and the outcome is the project's own visual world — not
this one. Two documents, two audiences: this one is how the framework speaks,
the project's is how the product speaks.

The artifact is read next to the others, often in one review. Four artifacts in
four invented styles read as four products, and the reader spends attention on
the difference instead of the content. So the block below is copied **verbatim**
into the artifact's `<style>`, and the vocabulary is chosen from, never
introduced around it. So every artifact also carries the `{ai}` favicon as an
inline data URI in its `<head>`, before `<style>`:

```html
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 32 32%22%3E%3Crect width=%2232%22 height=%2232%22 rx=%227%22 fill=%22%23001E2B%22/%3E%3Crect x=%220.5%22 y=%220.5%22 width=%2231%22 height=%2231%22 rx=%226.5%22 fill=%22none%22 stroke=%22%2300ED64%22 stroke-opacity=%220.35%22/%3E%3Ctext x=%2216%22 y=%2217%22 text-anchor=%22middle%22 dominant-baseline=%22central%22 font-family=%22ui-monospace, Menlo, Consolas, 'DejaVu Sans Mono', monospace%22 font-size=%2214%22 font-weight=%22700%22 letter-spacing=%22-1%22%3E%3Ctspan fill=%22%2300ED64%22%3E%7B%3C/tspan%3E%3Ctspan fill=%22%23E8EEF7%22%3Eai%3C/tspan%3E%3Ctspan fill=%22%2300ED64%22%3E%7D%3C/tspan%3E%3C/text%3E%3C/svg%3E">
```

Inline, never a file: an artifact is one self-contained page opened from
`file://` — no sibling asset can be assumed to travel with it. The URI is a
single source in this document; when the `{ai}` mark changes, re-cut every
carrier of this line (the two shipped templates and this document).

## The tokens

```css
/* ── {ai} Engineering — the artifact design system ─────────────────────────
   Tokens are the brand's, at system stacks so an artifact renders offline:
   one signal green, neutral borders, the reading tint for small green,
   dark-only. Anything ai-engineering renders as an artifact — spec.html,
   plan.html, a recap, a research page, a report — inherits this block
   verbatim.                                                                */
:root{
  --bg:#001E2B; --surface:#112733; --surface-2:#1C2D38;
  --line:rgba(61,79,88,.3); --line-strong:rgba(61,79,88,.6);
  --accent:#00ED64; --accent-dim:#71F6BA;
  --text:#FFFFFF; --dim:#C1C7C6; --comment:#889397;
  --ok:#00ED64; --bad:#FF6960; --warn:#FFC010; --purple:#B45AF2; --orange:#FFC010;
  --mono:'SF Mono','JetBrains Mono','Fira Code',ui-monospace,monospace;
  --sans:-apple-system,BlinkMacSystemFont,'Inter',system-ui,sans-serif;

  /* type: one scale, tracking and leading set per size, never one value for all */
  --fs-display:44px; --lh-display:1.06; --ls-display:-.028em;
  --fs-h2:26px;      --lh-h2:1.16;      --ls-h2:-.018em;
  --fs-h3:17px;      --lh-h3:1.32;      --ls-h3:-.006em;
  --fs-h4:14px;      --lh-h4:1.35;
  --fs-body:15px;    --lh-body:1.62;
  --fs-small:13.5px; --lh-small:1.55;
  --fs-mono:12.5px;  --lh-mono:1.7;
  --fs-label:10.5px;

  /* space: a 4px rhythm, so nothing lands on an arbitrary number */
  --s1:4px; --s2:8px; --s3:12px; --s4:16px; --s5:24px; --s6:32px; --s7:48px; --s8:64px;
  --radius:12px; --radius-sm:8px; --container:1040px; --measure:68ch;
}
*{margin:0;padding:0;box-sizing:border-box}
html{scroll-behavior:smooth;-webkit-text-size-adjust:100%}
body{
  background:var(--bg);color:var(--text);font-family:var(--sans);
  font-size:var(--fs-body);line-height:var(--lh-body);
  font-synthesis-weight:none;-webkit-font-smoothing:antialiased;
}
::selection{background:rgba(0,237,100,.28)}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline;text-underline-offset:3px}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:3px}
.skip{position:absolute;top:var(--s2);left:var(--s2);z-index:99;background:var(--surface);
      border:1px solid var(--line-strong);border-radius:var(--radius-sm);padding:13px 20px;
      transform:translateY(-160%);transition:transform .15s ease-out}
.skip:focus{transform:none}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%);white-space:nowrap}

/* ── hero ─────────────────────────────────────────────────────────────── */
.hero{
  position:relative;overflow:hidden;text-align:center;
  padding:88px var(--s6) 56px;border-bottom:1px solid var(--line);
  background-image:
    linear-gradient(var(--line) 1px,transparent 1px),
    linear-gradient(90deg,var(--line) 1px,transparent 1px),
    radial-gradient(ellipse 80% 60% at 50% 0%,#11273366,transparent);
  background-size:32px 32px,32px 32px,100% 100%;
}
.hero .stamp{
  display:inline-block;font-family:var(--mono);font-size:var(--fs-label);
  letter-spacing:.26em;text-transform:uppercase;color:var(--accent);
  border:1px solid var(--line-strong);border-radius:3px;padding:6px 14px;
  margin-bottom:var(--s5);
}
.hero h1{font-size:var(--fs-display);line-height:var(--lh-display);
         letter-spacing:var(--ls-display);font-weight:740}
.hero h1 .x{color:var(--accent)}
.hero .sub{font-size:17px;line-height:1.6;color:var(--dim);max-width:62ch;
           margin:var(--s4) auto 0}
.hero .sub strong{color:var(--text);font-weight:620}
.hero .meta{font-family:var(--mono);font-size:11.5px;line-height:1.6;color:var(--dim);
            margin:var(--s5) auto 0;max-width:66ch;letter-spacing:.02em}
.hero .meta b{color:var(--accent-dim);font-weight:500}
.hero .corner{position:absolute;width:22px;height:22px;border:0 solid var(--accent);opacity:.85}
.hero .tl{top:18px;left:18px;border-width:2px 0 0 2px}
.hero .tr{top:18px;right:18px;border-width:2px 2px 0 0}
.hero .bl{bottom:18px;left:18px;border-width:0 0 2px 2px}
.hero .br{bottom:18px;right:18px;border-width:0 2px 2px 0}

/* ── nav: translucent chrome, content scrolls under it ────────────────── */
nav{
  position:sticky;top:0;z-index:50;
  display:flex;flex-wrap:wrap;justify-content:center;gap:2px 4px;
  padding:var(--s2) var(--s4);
  background:rgba(0,30,43,.78);backdrop-filter:blur(14px) saturate(150%);
  border-bottom:1px solid var(--line);
  font-family:var(--mono);font-size:11px;
}
nav a{color:var(--dim);letter-spacing:.03em;padding:6px 9px;border-radius:999px;
      white-space:nowrap;transition:color .15s,background .15s}
nav a:hover{color:var(--accent);text-decoration:none;background:rgba(0,237,100,.06)}
nav a.active{color:var(--accent);background:rgba(0,237,100,.1);font-weight:600}
nav a b{color:var(--accent);font-weight:500;margin-right:5px;opacity:.75}
nav a.active b{opacity:1}

/* ── page ─────────────────────────────────────────────────────────────── */
.container{max-width:var(--container);margin:0 auto;padding:0 var(--s5)}
section{padding:64px 0 52px;border-bottom:1px solid var(--line);scroll-margin-top:88px}
section:last-of-type{border-bottom:none}
h2{font-size:var(--fs-h2);line-height:var(--lh-h2);letter-spacing:var(--ls-h2);font-weight:700}
h2 .num{display:block;font-family:var(--mono);font-size:11px;font-weight:400;
        letter-spacing:.22em;color:var(--accent);margin-bottom:var(--s2)}
h3{font-size:var(--fs-h3);line-height:var(--lh-h3);letter-spacing:var(--ls-h3);
   font-weight:640;margin:var(--s6) 0 var(--s3)}
h4{font-size:var(--fs-h4);line-height:var(--lh-h4);font-weight:640}
h2+p,h3+p,h3+div,h2+div{margin-top:var(--s3)}
p{color:var(--dim);max-width:var(--measure);margin:0 auto var(--s3);text-align:center}
p:last-child{margin-bottom:0}
p strong,li strong{color:var(--text);font-weight:620}
ul,ol{margin:var(--s3) 0 var(--s5) var(--s5)}
li{color:var(--dim);font-size:14px;line-height:1.6;margin-bottom:var(--s2);max-width:var(--measure)}
li strong{color:var(--text)}
.dim{color:var(--comment)}

/* ── code ─────────────────────────────────────────────────────────────── */
code{font-family:var(--mono);font-size:var(--fs-mono);background:var(--surface-2);
     border:1px solid var(--line);border-radius:5px;padding:1px 6px;color:var(--accent-dim);
     overflow-wrap:anywhere}
pre{background:var(--surface-2);border:1px solid var(--line);border-radius:var(--radius-lg);
    padding:var(--s4) var(--s5);overflow-x:auto;font-family:var(--mono);
    font-size:var(--fs-mono);line-height:var(--lh-mono);color:var(--dim);margin:var(--s4) 0;
    -webkit-overflow-scrolling:touch}
pre code{background:none;border:none;padding:0;color:inherit;overflow-wrap:normal}
pre,.flow,.tbl-wrap{scrollbar-color:var(--line-strong) transparent;scrollbar-width:thin}
pre::-webkit-scrollbar,.flow::-webkit-scrollbar,.tbl-wrap::-webkit-scrollbar{height:8px;width:8px}
pre::-webkit-scrollbar-thumb,.flow::-webkit-scrollbar-thumb,.tbl-wrap::-webkit-scrollbar-thumb{
  background:var(--line-strong);border-radius:99px}
pre::-webkit-scrollbar-track,.flow::-webkit-scrollbar-track,.tbl-wrap::-webkit-scrollbar-track{background:transparent}
pre .c{color:var(--comment)} pre .k{color:var(--accent)} pre .s{color:var(--ok)}
pre .t{color:var(--purple)} pre .n{color:var(--orange)} pre .b{color:var(--text);font-weight:600}
.flow{white-space:pre;font-size:12px;line-height:1.75;overflow-x:auto;-webkit-overflow-scrolling:touch}

/* ── panels ───────────────────────────────────────────────────────────── */
.bracket{position:relative;border:1px solid var(--line);background:var(--surface-2);
         border-radius:var(--radius-lg);padding:var(--s5) var(--s5) var(--s4);margin:var(--s5) 0}
.bracket::before,.bracket::after{content:'';position:absolute;width:14px;height:14px;
         border:0 solid var(--accent)}
.bracket::before{top:-1px;left:-1px;border-width:2px 0 0 2px}
.bracket::after{bottom:-1px;right:-1px;border-width:0 2px 2px 0}
.bracket>.tag{position:absolute;top:-9px;left:18px;background:var(--bg);padding:0 10px;
         font-family:var(--mono);font-size:var(--fs-label);letter-spacing:.22em;
         text-transform:uppercase;color:var(--accent)}
.bracket pre{margin:0;border:none;background:none;padding:0}

.card{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius-lg);
      padding:var(--s5);display:flex;flex-direction:column;gap:var(--s2)}
.card h3,.card h4{display:flex;align-items:flex-start;gap:var(--s2)}
.card h3,.card h4{min-height:22px;line-height:22px}
.card h3{font-size:var(--fs-h4);line-height:var(--lh-h4);font-weight:640;margin:0}
.card p{font-size:var(--fs-small);line-height:var(--lh-small);margin:0}
.card .src{font-family:var(--mono);font-size:11px;color:var(--comment)}
.card pre{font-size:12px;line-height:1.6;margin:var(--s2) 0 0}

.note{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius-lg);
      padding:var(--s5);margin:var(--s5) 0}
.note h3,.note h4{font-family:var(--mono);font-size:var(--fs-label);letter-spacing:.18em;
         text-transform:uppercase;color:var(--accent-dim);margin:0 0 var(--s3)}
.note p{font-size:var(--fs-small);line-height:var(--lh-small);margin:0}
.note.ok{border-color:rgba(0,237,100,.3)} .note.ok h4{color:var(--ok)}
.note.warn{border-color:rgba(255,192,16,.3)} .note.warn h4{color:var(--warn)}
.note.danger{border-color:rgba(255,105,96,.3)} .note.danger h4{color:var(--bad)}

.grid{display:grid;gap:var(--s3);margin:var(--s5) 0;align-items:stretch}
.grid>*{min-width:0}
pre{max-width:100%}
.g2{grid-template-columns:repeat(2,minmax(0,1fr))}
.g3{grid-template-columns:repeat(3,minmax(0,1fr))}
.g4{grid-template-columns:repeat(4,minmax(0,1fr))}
.stats{display:flex;gap:var(--s3);flex-wrap:wrap;justify-content:center;margin:var(--s5) 0}
.stat{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius-lg);
      padding:var(--s4) var(--s5);min-width:132px;text-align:center}
.stat .v{font-family:var(--mono);font-size:22px;font-weight:700;color:var(--text)}
.stat .v em{font-style:normal;color:var(--accent)}
.stat .l{font-family:var(--mono);font-size:var(--fs-label);letter-spacing:.14em;
         text-transform:uppercase;color:var(--dim);margin-top:var(--s1)}

/* ── tables: a component, not a spill ─────────────────────────────────── */
.tbl-wrap{border:1px solid var(--line);border-radius:var(--radius-lg);background:var(--surface-2);
          overflow-x:auto;-webkit-overflow-scrolling:touch;margin:var(--s4) 0}
table{width:100%;border-collapse:collapse;font-size:var(--fs-small)}
th{text-align:left;padding:12px var(--s4) 10px;white-space:nowrap;
   font-family:var(--mono);font-size:var(--fs-label);letter-spacing:.12em;
   text-transform:uppercase;color:var(--accent);border-bottom:1px solid var(--line-strong)}
td{padding:13px var(--s4);border-bottom:1px solid var(--line);color:var(--dim);
   vertical-align:top;line-height:var(--lh-small)}
tr:last-child td{border-bottom:none}
td:first-child{color:var(--text);font-weight:520}
@media (hover:hover) and (pointer:fine){tbody tr:hover td{background:rgba(17,39,51,.35)}}
td code{overflow-wrap:normal;word-break:keep-all}
table{min-width:640px}

/* ── pills, marks ─────────────────────────────────────────────────────── */
.pill{display:inline-block;font-family:var(--mono);font-size:10px;line-height:1.5;font-weight:600;
      padding:2px 8px;border-radius:999px;letter-spacing:.05em;white-space:nowrap;color:var(--text)}
.p-ok{background:rgba(0,237,100,.13);border:1px solid rgba(0,237,100,.32)}
.p-bad{background:rgba(255,105,96,.13);border:1px solid rgba(255,105,96,.34)}
.p-warn{background:rgba(255,192,16,.12);border:1px solid rgba(255,192,16,.32)}
.p-fix{background:rgba(0,237,100,.1);border:1px solid rgba(0,237,100,.35)}
.p-dim{background:rgba(17,39,51,.6);color:var(--dim);border:1px solid var(--line)}
.check{color:var(--ok);font-weight:600} .cross{color:var(--bad);font-weight:600}
.half{color:var(--warn);font-weight:600} .center{text-align:center}

/* ── pipeline: real boxes, not ASCII ─────────────────────────────────── */
.pipe{display:flex;align-items:stretch;margin:var(--s5) 0;flex-wrap:wrap;gap:0}
.pipe .stage{flex:1 1 150px;min-width:0;background:var(--surface);
             border:1px solid var(--line);padding:var(--s3) var(--s4) var(--s3)}
.pipe .stage:first-child{border-radius:var(--radius-lg) 0 0 var(--radius-lg)}
.pipe .stage:last-child{border-radius:0 var(--radius-lg) var(--radius-lg) 0}
.pipe .stage+.stage{border-left:none}
.pipe .stage::after{content:'▸';position:absolute;right:-6px;top:50%;transform:translateY(-50%);
                    color:var(--accent);font-size:13px;z-index:2}
.pipe .stage{position:relative}
.pipe .stage:last-child::after{content:''}
.pipe .ph{font-family:var(--mono);font-size:10px;letter-spacing:.16em;text-transform:uppercase;color:var(--accent)}
.pipe .sk{font-family:var(--mono);font-size:12px;color:var(--text);margin-top:var(--s2);line-height:1.5}
.pipe .q{font-size:11.5px;color:var(--dim);margin-top:var(--s1)}

.tiers{display:flex;flex-direction:column;gap:var(--s2);margin:var(--s5) 0}
.tier{display:flex;gap:var(--s4);align-items:baseline;border:1px solid var(--line);
      border-radius:var(--radius-lg);padding:var(--s3) var(--s4);background:var(--surface);flex-wrap:wrap}
.tier .tname{font-family:var(--mono);font-size:11px;letter-spacing:.08em;min-width:148px;
             color:var(--accent);text-transform:uppercase}
.tier .tbody{flex:1 1 240px;font-size:var(--fs-small);color:var(--dim);min-width:0}
.tier .tbody b{color:var(--text)}
.tier .tlat{font-family:var(--mono);font-size:11px;color:var(--warn);text-align:right}

footer{text-align:center;padding:var(--s7) var(--s5) var(--s6);
       border-top:1px solid var(--line);font-family:var(--mono);font-size:11px;
       color:var(--comment);letter-spacing:.08em;line-height:2.1}
footer .x{color:var(--accent)}
footer a{color:var(--dim);display:inline-block;padding:12px 4px}

@media (max-width:900px){
  .g2,.g3,.g4{grid-template-columns:1fr}
  .hero{padding:64px var(--s5) 44px}
  .hero h1{font-size:34px;letter-spacing:-.022em}
  .hero .sub{font-size:16px}
  .pipe .stage{border-left:1px solid var(--line);border-radius:var(--radius-lg)!important;flex-basis:100%}
  .pipe .stage+.stage{margin-top:var(--s2)}
  .pipe .stage::after{content:''}
  .tier .tlat{text-align:left}
}
@media (max-width:820px){
  nav a{padding:14px 8px}
}
@media (max-width:560px){
  .container{padding:0 var(--s4)}
  nav{font-size:10.5px;gap:0 2px;flex-wrap:nowrap;justify-content:flex-start;
      overflow-x:auto;scrollbar-width:none}
  nav::-webkit-scrollbar{display:none}
  nav::after{content:'';position:sticky;right:0;flex:0 0 28px;margin-left:-28px;
      background:linear-gradient(90deg,transparent,rgba(0,30,43,.95));pointer-events:none}
  nav a{padding:14px 8px}
  table{font-size:13px} th,td{padding:10px var(--s3)}
  pre{font-size:11.5px;padding:var(--s3) var(--s4)}
}
@media (prefers-reduced-motion:reduce){
  html{scroll-behavior:auto}
  *{animation:none!important;transition:none!important}
}
@media (prefers-reduced-transparency:reduce){
  nav{background:var(--bg);backdrop-filter:none}
}
@media (prefers-contrast:more){
  :root{--dim:#E8EDEB;--comment:#C1C7C6}
  .card,.note,p,li,td{color:var(--dim)}
  nav a{color:#E8EDEB}
}
@media print{
  nav,.skip{display:none}
  body{background:#fff;color:#111}
  section{page-break-inside:avoid}
}
```

## The rules that hold across every artifact

1. **Dark only, one signal.** Light mode is never generated. `--accent` is the
   one signal green and `--accent-dim` is that green dimmed for small text; links,
   focus and emphasis read one or the other. `--ok` / `--bad` / `--warn` mark
   state, `--purple` and `--orange` live inside a code block, and nothing else
   carries chroma.
2. **Two voices.** Prose and headings are set in the sans stack; code, data and
   measurement — commands, paths, numbers, labels, table headers — are set in
   the mono one. Mono never sets a paragraph, and is never decoration for prose.
3. **A numbered document gets numbers.** Mono `01`, `02` above each `h2`, and a
   sticky nav once the artifact has more than five sections. The number is a
   coordinate a reviewer cites, not a flourish.
4. **Measure before width.** Prose stops at `--measure`; a table, a diagram or a
   flow may use the full container. A paragraph that runs the width of a table
   is a defect.
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
   it; nothing is ever invisible while an animation runs.
9. **Structure is semantic.** `<header>` / `<nav>` / `<main>`, one `<section>`
   per numbered block, a skip link, `lang`, a `<title>`, and headings that never
   skip a level.
10. **Never:** emoji as icons · a gradient as decoration · a second signal hue ·
    a colored left border wider than 1px · a shadow without offset and blur · a
    card inside a card.

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
| Stats | `.stats > .stat` | a short row of counts, never a dashboard |
| Marks | `.check` / `.cross` / `.half` | yes · no · partial, inside a cell |

## The block

Copy this into `<style>` as it stands. `hero`, `nav` and `footer` apply to a
standalone document; `spec.html` and `plan.html` omit the hero and keep the rest.

```css
/* ── {ai} Engineering — the artifact design system ─────────────────────────
   Tokens are the brand's, at system stacks so an artifact renders offline:
   one signal green, neutral borders, the reading tint for small green,
   dark-only. Anything ai-engineering renders as an artifact — spec.html,
   plan.html, a recap, a research page, a report — inherits this block
   verbatim.                                                                */
:root{
  --bg:#001E2B; --surface:#112733; --surface-2:#1C2D38;
  --line:rgba(61,79,88,.3); --line-strong:rgba(61,79,88,.6);
  --accent:#00ED64; --accent-dim:#71F6BA;
  --text:#FFFFFF; --dim:#C1C7C6; --comment:#889397;
  --ok:#00ED64; --bad:#FF6960; --warn:#FFC010; --purple:#B45AF2; --orange:#FFC010;
  --mono:'SF Mono','JetBrains Mono','Fira Code',ui-monospace,monospace;
  --sans:-apple-system,BlinkMacSystemFont,'Inter',system-ui,sans-serif;

  /* type: one scale, tracking and leading set per size, never one value for all */
  --fs-display:44px; --lh-display:1.06; --ls-display:-.028em;
  --fs-h2:26px;      --lh-h2:1.16;      --ls-h2:-.018em;
  --fs-h3:17px;      --lh-h3:1.32;      --ls-h3:-.006em;
  --fs-h4:14px;      --lh-h4:1.35;
  --fs-body:15px;    --lh-body:1.62;
  --fs-small:13.5px; --lh-small:1.55;
  --fs-mono:12.5px;  --lh-mono:1.7;
  --fs-label:10.5px;

  /* space: a 4px rhythm, so nothing lands on an arbitrary number */
  --s1:4px; --s2:8px; --s3:12px; --s4:16px; --s5:24px; --s6:32px; --s7:48px; --s8:64px;
  --radius:12px; --radius-sm:8px; --container:1040px; --measure:68ch;
}
*{margin:0;padding:0;box-sizing:border-box}
html{scroll-behavior:smooth;-webkit-text-size-adjust:100%}
body{
  background:var(--bg);color:var(--text);font-family:var(--sans);
  font-size:var(--fs-body);line-height:var(--lh-body);
  font-synthesis-weight:none;-webkit-font-smoothing:antialiased;
}
::selection{background:rgba(0,237,100,.28)}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline;text-underline-offset:3px}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:3px}
.skip{position:absolute;top:var(--s2);left:var(--s2);z-index:99;background:var(--surface);
      border:1px solid var(--line-strong);border-radius:var(--radius-sm);padding:14px 18px;
      clip-path:inset(50%);width:1px;height:1px;overflow:hidden}
.skip:focus{clip-path:none;width:auto;height:auto}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%);white-space:nowrap}

/* ── hero ─────────────────────────────────────────────────────────────── */
.hero{
  position:relative;overflow:hidden;text-align:center;
  padding:88px var(--s6) 56px;border-bottom:1px solid var(--line);
  background-image:
    linear-gradient(var(--line) 1px,transparent 1px),
    linear-gradient(90deg,var(--line) 1px,transparent 1px),
    radial-gradient(ellipse 80% 60% at 50% 0%,#11273366,transparent);
  background-size:32px 32px,32px 32px,100% 100%;
}
.hero .stamp{
  display:inline-block;font-family:var(--mono);font-size:var(--fs-label);
  letter-spacing:.26em;text-transform:uppercase;color:var(--accent);
  border:1px solid var(--line-strong);border-radius:3px;padding:6px 14px;
  margin-bottom:var(--s5);
}
.hero h1{font-size:var(--fs-display);line-height:var(--lh-display);
         letter-spacing:var(--ls-display);font-weight:740}
.hero h1 .x{color:var(--accent)}
.hero .sub{font-size:17px;line-height:1.6;color:var(--dim);max-width:62ch;
           margin:var(--s4) auto 0}
.hero .sub strong{color:var(--text);font-weight:620}
.hero .meta{font-family:var(--mono);font-size:11.5px;line-height:1.6;color:var(--dim);
            margin:var(--s5) auto 0;max-width:66ch;letter-spacing:.02em}
.hero .meta b{color:var(--accent-dim);font-weight:500}
.hero .corner{position:absolute;width:22px;height:22px;border:0 solid var(--accent);opacity:.85}
.hero .tl{top:18px;left:18px;border-width:2px 0 0 2px}
.hero .tr{top:18px;right:18px;border-width:2px 2px 0 0}
.hero .bl{bottom:18px;left:18px;border-width:0 0 2px 2px}
.hero .br{bottom:18px;right:18px;border-width:0 2px 2px 0}

/* ── nav: translucent chrome, content scrolls under it ────────────────── */
nav{
  position:sticky;top:0;z-index:50;
  display:flex;flex-wrap:wrap;justify-content:center;gap:2px 4px;
  padding:var(--s2) var(--s4);
  background:rgba(0,30,43,.78);backdrop-filter:blur(14px) saturate(150%);
  border-bottom:1px solid var(--line);
  font-family:var(--mono);font-size:11px;
}
nav a{color:var(--dim);letter-spacing:.03em;padding:6px 9px;border-radius:999px;
      white-space:nowrap;transition:color .15s,background .15s}
nav a:hover{color:var(--accent);text-decoration:none;background:rgba(0,237,100,.06)}
nav a.active{color:var(--accent);background:rgba(0,237,100,.1);font-weight:600}
nav a b{color:var(--accent);font-weight:500;margin-right:5px;opacity:.75}
nav a.active b{opacity:1}

/* ── page ─────────────────────────────────────────────────────────────── */
.container{max-width:var(--container);margin:0 auto;padding:0 var(--s5)}
section{padding:64px 0 52px;border-bottom:1px solid var(--line);scroll-margin-top:88px}
section:last-of-type{border-bottom:none}
h2{font-size:var(--fs-h2);line-height:var(--lh-h2);letter-spacing:var(--ls-h2);font-weight:700}
h2 .num{display:block;font-family:var(--mono);font-size:11px;font-weight:400;
        letter-spacing:.22em;color:var(--accent);margin-bottom:var(--s2)}
h3{font-size:var(--fs-h3);line-height:var(--lh-h3);letter-spacing:var(--ls-h3);
   font-weight:640;margin:var(--s6) 0 var(--s3)}
h4{font-size:var(--fs-h4);line-height:var(--lh-h4);font-weight:640}
h2+p,h3+p,h3+div,h2+div{margin-top:var(--s3)}
p{color:var(--dim);max-width:var(--measure);margin:0 auto var(--s3);text-align:center}
p:last-child{margin-bottom:0}
p strong,li strong{color:var(--text);font-weight:620}
ul,ol{margin:var(--s3) 0 var(--s5) var(--s5)}
li{color:var(--dim);font-size:14px;line-height:1.6;margin-bottom:var(--s2);max-width:var(--measure)}
li strong{color:var(--text)}
.dim{color:var(--comment)}

/* ── code ─────────────────────────────────────────────────────────────── */
code{font-family:var(--mono);font-size:var(--fs-mono);background:var(--surface-2);
     border:1px solid var(--line);border-radius:5px;padding:1px 6px;color:var(--accent-dim);
     overflow-wrap:anywhere}
pre{background:var(--surface-2);border:1px solid var(--line);border-radius:var(--radius-lg);
    padding:var(--s4) var(--s5);overflow-x:auto;font-family:var(--mono);
    font-size:var(--fs-mono);line-height:var(--lh-mono);color:var(--dim);margin:var(--s4) 0;
    -webkit-overflow-scrolling:touch}
pre code{background:none;border:none;padding:0;color:inherit;overflow-wrap:normal}
pre,.flow,.tbl-wrap{scrollbar-color:var(--line-strong) transparent;scrollbar-width:thin}
pre::-webkit-scrollbar,.flow::-webkit-scrollbar,.tbl-wrap::-webkit-scrollbar{height:8px;width:8px}
pre::-webkit-scrollbar-thumb,.flow::-webkit-scrollbar-thumb,.tbl-wrap::-webkit-scrollbar-thumb{
  background:var(--line-strong);border-radius:99px}
pre::-webkit-scrollbar-track,.flow::-webkit-scrollbar-track,.tbl-wrap::-webkit-scrollbar-track{background:transparent}
pre .c{color:var(--comment)} pre .k{color:var(--accent)} pre .s{color:var(--ok)}
pre .t{color:var(--purple)} pre .n{color:var(--orange)} pre .b{color:var(--text);font-weight:600}
.flow{white-space:pre;font-size:12px;line-height:1.75;overflow-x:auto;-webkit-overflow-scrolling:touch}

/* ── panels ───────────────────────────────────────────────────────────── */
.bracket{position:relative;border:1px solid var(--line);background:var(--surface-2);
         border-radius:var(--radius-lg);padding:var(--s5) var(--s5) var(--s4);margin:var(--s5) 0}
.bracket::before,.bracket::after{content:'';position:absolute;width:14px;height:14px;
         border:0 solid var(--accent)}
.bracket::before{top:-1px;left:-1px;border-width:2px 0 0 2px}
.bracket::after{bottom:-1px;right:-1px;border-width:0 2px 2px 0}
.bracket>.tag{position:absolute;top:-9px;left:18px;background:var(--bg);padding:0 10px;
         font-family:var(--mono);font-size:var(--fs-label);letter-spacing:.22em;
         text-transform:uppercase;color:var(--accent)}
.bracket pre{margin:0;border:none;background:none;padding:0}

.card{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius-lg);
      padding:var(--s5);display:flex;flex-direction:column;gap:var(--s2)}
.card h3,.card h4{display:flex;align-items:center;gap:var(--s2);flex-wrap:wrap}
.card h3,.card h4{min-height:1.6em}
.card h3{font-size:var(--fs-h4);line-height:var(--lh-h4);font-weight:640;margin:0}
.card p{font-size:var(--fs-small);line-height:var(--lh-small);margin:0}
.card .src{font-family:var(--mono);font-size:11px;color:var(--comment)}
.card pre{font-size:12px;line-height:1.6;margin:var(--s2) 0 0}

.note{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius-lg);
      padding:var(--s5);margin:var(--s5) 0}
.note h3,.note h4{font-family:var(--mono);font-size:var(--fs-label);letter-spacing:.18em;
         text-transform:uppercase;color:var(--accent-dim);margin:0 0 var(--s3)}
.note p{font-size:var(--fs-small);line-height:var(--lh-small);margin:0}
.note.ok{border-color:rgba(0,237,100,.3)} .note.ok h4{color:var(--ok)}
.note.warn{border-color:rgba(255,192,16,.3)} .note.warn h4{color:var(--warn)}
.note.danger{border-color:rgba(255,105,96,.3)} .note.danger h4{color:var(--bad)}

.grid{display:grid;gap:var(--s3);margin:var(--s5) 0;align-items:stretch}
.grid>*{min-width:0}
pre{max-width:100%}
.g2{grid-template-columns:repeat(2,minmax(0,1fr))}
.g3{grid-template-columns:repeat(3,minmax(0,1fr))}
.g4{grid-template-columns:repeat(4,minmax(0,1fr))}
.stats{display:flex;gap:var(--s3);flex-wrap:wrap;justify-content:center;margin:var(--s5) 0}
.stat{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius-lg);
      padding:var(--s4) var(--s5);min-width:132px;text-align:center}
.stat .v{font-family:var(--mono);font-size:22px;font-weight:700;color:var(--text)}
.stat .v em{font-style:normal;color:var(--accent)}
.stat .l{font-family:var(--mono);font-size:var(--fs-label);letter-spacing:.14em;
         text-transform:uppercase;color:var(--dim);margin-top:var(--s1)}

/* ── tables: a component, not a spill ─────────────────────────────────── */
.tbl-wrap{border:1px solid var(--line);border-radius:var(--radius-lg);background:var(--surface-2);
          overflow-x:auto;-webkit-overflow-scrolling:touch;margin:var(--s4) 0}
table{width:100%;border-collapse:collapse;font-size:var(--fs-small)}
th{text-align:left;padding:12px var(--s4) 10px;white-space:nowrap;
   font-family:var(--mono);font-size:var(--fs-label);letter-spacing:.12em;
   text-transform:uppercase;color:var(--accent);border-bottom:1px solid var(--line-strong)}
td{padding:13px var(--s4);border-bottom:1px solid var(--line);color:var(--dim);
   vertical-align:top;line-height:var(--lh-small)}
tr:last-child td{border-bottom:none}
td:first-child{color:var(--text);font-weight:520}
@media (hover:hover) and (pointer:fine){tbody tr:hover td{background:rgba(17,39,51,.35)}}
td code{overflow-wrap:normal;word-break:keep-all}
table{min-width:640px}

/* ── pills, marks ─────────────────────────────────────────────────────── */
.pill{display:inline-block;font-family:var(--mono);font-size:10px;line-height:1.5;font-weight:600;
      padding:2px 8px;border-radius:999px;letter-spacing:.05em;white-space:nowrap;color:var(--text)}
.p-ok{background:rgba(0,237,100,.13);border:1px solid rgba(0,237,100,.32)}
.p-bad{background:rgba(255,105,96,.13);border:1px solid rgba(255,105,96,.34)}
.p-warn{background:rgba(255,192,16,.12);border:1px solid rgba(255,192,16,.32)}
.p-fix{background:rgba(0,237,100,.1);border:1px solid rgba(0,237,100,.35)}
.p-dim{background:rgba(17,39,51,.6);color:var(--dim);border:1px solid var(--line)}
.check{color:var(--ok);font-weight:600} .cross{color:var(--bad);font-weight:600}
.half{color:var(--warn);font-weight:600} .center{text-align:center}

/* ── pipeline: real boxes, not ASCII ─────────────────────────────────── */
.pipe{display:flex;align-items:stretch;margin:var(--s5) 0;flex-wrap:wrap;gap:0}
.pipe .stage{flex:1 1 150px;min-width:0;background:var(--surface);
             border:1px solid var(--line);padding:var(--s3) var(--s4) var(--s3)}
.pipe .stage:first-child{border-radius:var(--radius-lg) 0 0 var(--radius-lg)}
.pipe .stage:last-child{border-radius:0 var(--radius-lg) var(--radius-lg) 0}
.pipe .stage+.stage{border-left:none}
.pipe .stage::after{content:'▸';position:absolute;right:-6px;top:50%;transform:translateY(-50%);
                    color:var(--accent);font-size:13px;z-index:2}
.pipe .stage{position:relative}
.pipe .stage:last-child::after{content:''}
.pipe .ph{font-family:var(--mono);font-size:10px;letter-spacing:.16em;text-transform:uppercase;color:var(--accent)}
.pipe .sk{font-family:var(--mono);font-size:12px;color:var(--text);margin-top:var(--s2);line-height:1.5}
.pipe .q{font-size:11.5px;color:var(--dim);margin-top:var(--s1)}

.tiers{display:flex;flex-direction:column;gap:var(--s2);margin:var(--s5) 0}
.tier{display:flex;gap:var(--s4);align-items:baseline;border:1px solid var(--line);
      border-radius:var(--radius-lg);padding:var(--s3) var(--s4);background:var(--surface);flex-wrap:wrap}
.tier .tname{font-family:var(--mono);font-size:11px;letter-spacing:.08em;min-width:148px;
             color:var(--accent);text-transform:uppercase}
.tier .tbody{flex:1 1 240px;font-size:var(--fs-small);color:var(--dim);min-width:0}
.tier .tbody b{color:var(--text)}
.tier .tlat{font-family:var(--mono);font-size:11px;color:var(--warn);text-align:right}

footer{text-align:center;padding:var(--s7) var(--s5) var(--s6);
       border-top:1px solid var(--line);font-family:var(--mono);font-size:11px;
       color:var(--comment);letter-spacing:.08em;line-height:2.1}
footer .x{color:var(--accent)}
footer a{color:var(--dim);display:inline-block;padding:12px 4px}

@media (max-width:900px){
  .g2,.g3,.g4{grid-template-columns:1fr}
  .hero{padding:64px var(--s5) 44px}
  .hero h1{font-size:34px;letter-spacing:-.022em}
  .hero .sub{font-size:16px}
  section{padding:var(--s7) 0 var(--s6)}
  .pipe .stage{border-left:1px solid var(--line);border-radius:var(--radius-lg)!important;flex-basis:100%}
  .pipe .stage+.stage{margin-top:var(--s2)}
  .pipe .stage::after{content:''}
  .tier .tlat{text-align:left}
}
@media (max-width:560px){
  .container{padding:0 var(--s4)}
  nav{font-size:10.5px;gap:0 2px;flex-wrap:nowrap;justify-content:flex-start;
      overflow-x:auto;scrollbar-width:none}
  nav::-webkit-scrollbar{display:none}
  nav::after{content:'';position:sticky;right:0;flex:0 0 28px;margin-left:-28px;
      background:linear-gradient(90deg,transparent,rgba(0,30,43,.95));pointer-events:none}
  nav a{padding:14px 8px}
  table{font-size:13px} th,td{padding:10px var(--s3)}
  pre{font-size:11.5px;padding:var(--s3) var(--s4)}
}
@media (prefers-reduced-motion:reduce){
  html{scroll-behavior:auto}
  *{animation:none!important;transition:none!important}
}
@media (prefers-reduced-transparency:reduce){
  nav{background:var(--bg);backdrop-filter:none}
}
@media (prefers-contrast:more){
  :root{--dim:#E8EDEB;--comment:#C1C7C6}
  .card,.note,p,li,td{color:var(--dim)}
  nav a{color:#E8EDEB}
}
@media print{
  nav,.skip{display:none}
  body{background:#fff;color:#111}
  section{page-break-inside:avoid}
}
```

## Source

ai-engineering (own), Apache-2.0. The values are LeafyGreen UI's
(`mongodb/leafygreen-ui`, Apache-2.0, taken verbatim): the palette and the
component grammar, not the identity — no MongoDB logo, wordmark or leaf is
reproduced anywhere, and no commercial font is shipped. `brand/tokens.json`
records them; the two shipped templates carry the same block.

## Done when

- The artifact renders at 320, 768 and 1440px with no sideways page scroll.
- Every text/ground pair clears its contrast floor.
- No heading level is skipped; the nav's links all resolve.
- The tokens are the ones above, unchanged — a diff in a token is a defect, not
  a preference.
