<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 32 32%22%3E%3Crect width=%2232%22 height=%2232%22 rx=%227%22 fill=%22%23001E2B%22/%3E%3Crect x=%220.5%22 y=%220.5%22 width=%2231%22 height=%2231%22 rx=%226.5%22 fill=%22none%22 stroke=%22%2300ED64%22 stroke-opacity=%220.35%22/%3E%3Ctext x=%2216%22 y=%2217%22 text-anchor=%22middle%22 dominant-baseline=%22central%22 font-family=%22ui-monospace, Menlo, Consolas, 'DejaVu Sans Mono', monospace%22 font-size=%2214%22 font-weight=%22700%22 letter-spacing=%22-1%22%3E%3Ctspan fill=%22%2300ED64%22%3E%7B%3C/tspan%3E%3Ctspan fill=%22%23E8EEF7%22%3Eai%3C/tspan%3E%3Ctspan fill=%22%2300ED64%22%3E%7D%3C/tspan%3E%3C/text%3E%3C/svg%3E">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="ai-engineering, written by an AI agent">
<title>The gallery · every part of an ai-engineering artifact</title>
<style>
/* brand:begin */
:root{
  --bg:#001E2B; --surface:#112733; --surface-2:#1C2D38;
  --line:rgba(61,79,88,.3); --line-strong:rgba(61,79,88,.6);
  --accent:#00ED64; --accent-dim:#71F6BA;
  --text:#FFFFFF; --dim:#C1C7C6; --comment:#889397;
  --ok:#00ED64; --bad:#FF6960; --warn:#FFC010; --purple:#B45AF2; --orange:#FFC010; --blue:#0498EC;
  --cat-green:#71F6BA; --cat-purple:#F1D4FD; --cat-amber:#FFC010; --cat-red:#FFCDC7; --cat-blue:#C3E7FE;
  --print-bg:#FFFFFF; --print-text:#001E2B; --print-dim:#3D4F58; --print-accent:#00684A; --print-bad:#970606; --print-warn:#944F01; --print-line:#889397;
  --hue:var(--line-strong);
  --mono:ui-monospace,'SF Mono','Cascadia Code','JetBrains Mono',Consolas,'DejaVu Sans Mono','Liberation Mono',monospace;
  --sans:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;
  --fs-display:44px; --lh-display:1.06; --ls-display:-.028em;
  --fs-h2:26px; --lh-h2:1.16; --ls-h2:-.018em;
  --fs-h3:17px; --lh-h3:1.32; --ls-h3:-.006em;
  --fs-h4:14px; --lh-h4:1.35;
  --fs-body:15px; --lh-body:1.62;
  --fs-small:13.5px; --lh-small:1.55;
  --fs-mono:12.5px; --lh-mono:1.7;
  --fs-label:10.5px;
  --s1:4px; --s2:8px; --s3:12px; --s4:16px; --s5:24px; --s6:32px; --s7:48px; --s8:64px;
  --radius:12px; --radius-sm:8px; --radius-lg:var(--radius); --container:1040px; --measure:68ch;
}
*{margin:0;padding:0;box-sizing:border-box}
html{scroll-behavior:smooth;-webkit-text-size-adjust:100%}
body{background:var(--bg);color:var(--text);font-family:var(--sans);font-size:var(--fs-body);line-height:var(--lh-body);font-synthesis-weight:none;-webkit-font-smoothing:antialiased}
::selection{background:rgba(0,237,100,.28)}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline;text-underline-offset:3px}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:3px}
.skip{position:absolute;top:var(--s2);left:var(--s2);z-index:99;background:var(--surface);border:1px solid var(--line-strong);border-radius:var(--radius-sm);padding:13px 20px;transform:translateY(-160%);transition:transform .15s ease-out}
.skip:focus{transform:none}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%);white-space:nowrap}
.hero{position:relative;overflow:hidden;text-align:center;padding:88px var(--s6) 56px;border-bottom:1px solid var(--line);background-image:linear-gradient(var(--line) 1px,transparent 1px),linear-gradient(90deg,var(--line) 1px,transparent 1px),radial-gradient(ellipse 80% 60% at 50% 0%,#11273366,transparent);background-size:32px 32px,32px 32px,100% 100%}
.hero .stamp{display:inline-block;font-family:var(--mono);font-size:var(--fs-label);letter-spacing:.26em;text-transform:uppercase;color:var(--accent);border:1px solid var(--line-strong);border-radius:3px;padding:6px 14px;margin-bottom:var(--s5)}
.hero h1{font-size:var(--fs-display);line-height:var(--lh-display);letter-spacing:var(--ls-display);font-weight:740}
.hero h1 .x{color:var(--accent)}
.hero .sub{font-size:17px;line-height:1.6;color:var(--dim);max-width:62ch;margin:var(--s4) auto 0}
.hero .sub strong{color:var(--text);font-weight:620}
.hero .meta{font-family:var(--mono);font-size:11.5px;line-height:1.6;color:var(--dim);margin:var(--s5) auto 0;max-width:66ch;letter-spacing:.02em}
.hero .meta b{color:var(--accent-dim);font-weight:500}
.hero .corner{position:absolute;width:22px;height:22px;border:0 solid var(--accent);opacity:.85}
.hero .tl{top:18px;left:18px;border-width:2px 0 0 2px}
.hero .tr{top:18px;right:18px;border-width:2px 2px 0 0}
.hero .bl{bottom:18px;left:18px;border-width:0 0 2px 2px}
.hero .br{bottom:18px;right:18px;border-width:0 2px 2px 0}
nav{position:sticky;top:0;z-index:50;display:flex;flex-wrap:wrap;justify-content:center;gap:2px 4px;padding:var(--s2) var(--s4);background:rgba(0,30,43,.78);backdrop-filter:blur(14px) saturate(150%);border-bottom:1px solid var(--line);font-family:var(--mono);font-size:11px}
nav a{color:var(--dim);letter-spacing:.03em;padding:6px 9px;border-radius:999px;white-space:nowrap;transition:color .15s,background .15s}
nav a:hover{color:var(--accent);text-decoration:none;background:rgba(0,237,100,.06)}
nav a.active{color:var(--accent);background:rgba(0,237,100,.1);font-weight:600}
nav a b{color:var(--accent);font-weight:500;margin-right:5px;opacity:.75}
nav a.active b{opacity:1}
.container{max-width:var(--container);margin:0 auto;padding:0 var(--s5)}
section{padding:56px 0 44px;border-bottom:1px solid var(--line);scroll-margin-top:88px}
section:last-of-type{border-bottom:none}
h2{font-size:var(--fs-h2);line-height:var(--lh-h2);letter-spacing:var(--ls-h2);font-weight:700}
h2 .num{display:block;font-family:var(--mono);font-size:11px;font-weight:400;letter-spacing:.22em;color:var(--accent);margin-bottom:var(--s2)}
h3{font-size:var(--fs-h3);line-height:var(--lh-h3);letter-spacing:var(--ls-h3);font-weight:660;margin:var(--s5) 0 var(--s3)}
h4{font-size:var(--fs-h4);line-height:var(--lh-h4);font-weight:640}
h2+p,h3+p,h3+div,h2+div{margin-top:var(--s3)}
p{color:var(--dim);margin:0 0 var(--s3);text-align:left}
p:last-child{margin-bottom:0}
p strong,li strong{color:var(--text);font-weight:620}
ul{margin:var(--s3) 0 var(--s5) var(--s5)}
ol{margin:var(--s3) 0 var(--s5);text-align:left;list-style:none;padding-left:0;counter-reset:ref}
li{color:var(--dim);font-size:14px;line-height:1.6;margin-bottom:var(--s3);padding-left:var(--s2)}
ol li{counter-increment:ref;padding-left:2.4em;position:relative}
ol li::before{content:counter(ref) ".";position:absolute;left:0;color:var(--comment);font-family:var(--mono);font-size:12px;width:2em;text-align:right}
li strong{color:var(--text)}
.dim{color:var(--comment)}
code{font-family:var(--mono);font-size:var(--fs-mono);background:var(--surface-2);border:1px solid var(--line);border-radius:5px;padding:1px 6px;color:var(--accent-dim);overflow-wrap:anywhere}
pre{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius-lg);padding:var(--s4) var(--s5);overflow-x:auto;font-family:var(--mono);font-size:var(--fs-mono);line-height:var(--lh-mono);color:var(--dim);margin:var(--s4) 0;-webkit-overflow-scrolling:touch}
pre code{background:none;border:none;padding:0;color:inherit;overflow-wrap:normal}
pre,.flow,.tbl-wrap{scrollbar-color:var(--line-strong) transparent;scrollbar-width:thin}
pre::-webkit-scrollbar,.flow::-webkit-scrollbar,.tbl-wrap::-webkit-scrollbar{height:8px;width:8px}
pre::-webkit-scrollbar-thumb,.flow::-webkit-scrollbar-thumb,.tbl-wrap::-webkit-scrollbar-thumb{background:var(--line-strong);border-radius:99px}
pre::-webkit-scrollbar-track,.flow::-webkit-scrollbar-track,.tbl-wrap::-webkit-scrollbar-track{background:transparent}
pre .c{color:var(--comment)} pre .k{color:var(--accent)} pre .s{color:var(--ok)}
pre .t{color:var(--purple)} pre .n{color:var(--orange)} pre .b{color:var(--text);font-weight:600}
.flow{white-space:pre;font-size:12px;line-height:1.75;overflow-x:auto;-webkit-overflow-scrolling:touch}
.bracket{position:relative;border:1px solid var(--line);background:var(--bg);border-radius:var(--radius-lg);padding:var(--s5) var(--s5) var(--s4);margin:var(--s5) 0}
.bracket::before,.bracket::after{content:'';position:absolute;width:14px;height:14px;border:0 solid var(--accent)}
.bracket::before{top:-1px;left:-1px;border-width:2px 0 0 2px}
.bracket::after{bottom:-1px;right:-1px;border-width:0 2px 2px 0}
.bracket>.tag{position:absolute;top:-9px;left:18px;background:var(--bg);padding:0 10px;font-family:var(--mono);font-size:var(--fs-label);letter-spacing:.22em;text-transform:uppercase;color:var(--accent)}
.bracket pre{margin:0;border:none;background:none;padding:0}
.card{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius-lg);padding:var(--s5);display:flex;flex-direction:column;gap:var(--s2)}
.card h3,.card h4{display:flex;align-items:flex-start;gap:var(--s2)}
.card h3,.card h4{min-height:22px;line-height:22px}
.card h3{font-size:var(--fs-h4);line-height:var(--lh-h4);font-weight:640;margin:0}
.card p{font-size:var(--fs-small);line-height:var(--lh-small);margin:0}
.card .src{font-family:var(--mono);font-size:11px;color:var(--comment)}
.card pre{font-size:12px;line-height:1.6;margin:var(--s2) 0 0}
.note{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius-lg);padding:var(--s5);margin:var(--s5) 0}
.note h3,.note h4{font-family:var(--mono);font-size:var(--fs-label);letter-spacing:.18em;text-transform:uppercase;color:var(--accent-dim);margin:0 0 var(--s3)}
.note p{font-size:var(--fs-small);line-height:var(--lh-small);margin:0;text-align:left}
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
.stat{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius-lg);padding:var(--s4) var(--s5);min-width:132px;text-align:center}
.stat .v{font-family:var(--mono);font-size:22px;font-weight:700;color:var(--text)}
.stat .v em{font-style:normal;color:var(--accent)}
.stat .l{font-family:var(--mono);font-size:var(--fs-label);letter-spacing:.14em;text-transform:uppercase;color:var(--dim);margin-top:var(--s1)}
.tbl-wrap{border:1px solid var(--line);border-radius:var(--radius-lg);background:var(--surface-2);overflow-x:auto;-webkit-overflow-scrolling:touch;margin:var(--s4) 0}
table{width:100%;border-collapse:collapse;font-size:var(--fs-small)}
th{text-align:left;padding:12px var(--s4) 10px;white-space:nowrap;font-family:var(--mono);font-size:var(--fs-label);letter-spacing:.12em;text-transform:uppercase;color:var(--accent);border-bottom:1px solid var(--line-strong)}
td{padding:13px var(--s4);border-bottom:1px solid var(--line);color:var(--dim);vertical-align:top;line-height:var(--lh-small)}
tr:last-child td{border-bottom:none}
td:first-child{color:var(--text);font-weight:520}
@media (hover:hover) and (pointer:fine){tbody tr:hover td{background:rgba(17,39,51,.35)}}
td code{overflow-wrap:normal;word-break:keep-all}
table{min-width:640px}
.pill{display:inline-block;font-family:var(--mono);font-size:10px;line-height:1.5;font-weight:600;padding:2px 8px;border-radius:999px;letter-spacing:.05em;white-space:nowrap;color:var(--text)}
.p-ok{background:rgba(0,237,100,.13);border:1px solid rgba(0,237,100,.32)}
.p-bad{background:rgba(255,105,96,.13);border:1px solid rgba(255,105,96,.34)}
.p-warn{background:rgba(255,192,16,.12);border:1px solid rgba(255,192,16,.32)}
.p-fix{background:rgba(0,237,100,.1);border:1px solid rgba(0,237,100,.35)}
.p-dim{background:rgba(17,39,51,.6);color:var(--dim);border:1px solid var(--line)}
.check{color:var(--ok);font-weight:600} .cross{color:var(--bad);font-weight:600}
.half{color:var(--warn);font-weight:600} .center{text-align:center}
.btn{display:inline-block;border:1px solid rgba(0,237,100,.35);border-radius:999px;padding:8px 18px;margin:var(--s2) 0;color:var(--accent);font-family:var(--mono);font-size:12px;text-decoration:none;transition:background .15s}
.btn:hover{background:rgba(0,237,100,.08);text-decoration:none}
.pipe{display:flex;align-items:stretch;margin:var(--s5) 0;flex-wrap:wrap;gap:0}
.pipe .stage{flex:1 1 150px;min-width:0;background:var(--surface);border:1px solid var(--line);padding:var(--s3) var(--s4) var(--s3)}
.pipe .stage:first-child{border-radius:var(--radius-lg) 0 0 var(--radius-lg)}
.pipe .stage:last-child{border-radius:0 var(--radius-lg) var(--radius-lg) 0}
.pipe .stage+.stage{border-left:none}
.pipe .stage::after{content:'▸';position:absolute;right:-6px;top:50%;transform:translateY(-50%);color:var(--accent);font-size:13px;z-index:2}
.pipe .stage{position:relative}
.pipe .stage:last-child::after{content:''}
.pipe .ph{font-family:var(--mono);font-size:10px;letter-spacing:.16em;text-transform:uppercase;color:var(--accent)}
.pipe .sk{font-family:var(--mono);font-size:12px;color:var(--text);margin-top:var(--s2);line-height:1.5}
.pipe .q{font-size:11.5px;color:var(--dim);margin-top:var(--s1)}
.tiers{display:flex;flex-direction:column;gap:var(--s2);margin:var(--s5) 0}
.tier{display:flex;gap:var(--s4);align-items:baseline;border:1px solid var(--line);border-radius:var(--radius-lg);padding:var(--s3) var(--s4);background:var(--surface);flex-wrap:wrap}
.tier .tname{font-family:var(--mono);font-size:11px;letter-spacing:.08em;min-width:148px;color:var(--accent);text-transform:uppercase}
.tier .tbody{flex:1 1 240px;font-size:var(--fs-small);color:var(--dim);min-width:0}
.tier .tbody b{color:var(--text)}
.tier .tlat{font-family:var(--mono);font-size:11px;color:var(--warn);text-align:right}
/* ── items: the expandable row, and the band chip that ranks it ───────── */
.band{display:inline-block;font-family:var(--mono);font-size:10px;line-height:1.5;font-weight:700;padding:2px 8px;border-radius:999px;letter-spacing:.08em;white-space:nowrap;color:var(--text);border:1px solid transparent}
.band-p0{background:rgba(255,105,96,.16);border-color:rgba(255,105,96,.46)}
.band-p1{background:rgba(255,192,16,.14);border-color:rgba(255,192,16,.44)}
.band-p2{background:rgba(0,237,100,.12);border-color:rgba(0,237,100,.36)}
.band-p3,.band-p4,.band-p5{background:rgba(17,39,51,.6);border-color:var(--line);color:var(--dim)}
.items{display:flex;flex-direction:column;gap:var(--s2);margin:var(--s5) 0}
.item{border:1px solid var(--line);border-radius:var(--radius-lg);background:var(--surface)}
.item>summary{display:flex;align-items:baseline;gap:var(--s3);flex-wrap:wrap;padding:var(--s3) var(--s4);cursor:pointer;list-style:none;border-radius:var(--radius-lg)}
.item>summary::-webkit-details-marker{display:none}
.item>summary::after{content:'+';font-family:var(--mono);font-size:13px;line-height:1;color:var(--comment)}
.item[open]>summary::after{content:'\2013'}
.item[open]>summary{border-bottom:1px solid var(--line);border-radius:var(--radius-lg) var(--radius-lg) 0 0}
.item>summary:hover{background:rgba(17,39,51,.35)}
.item .iid{font-family:var(--mono);font-size:12px;font-weight:600;white-space:nowrap}
.item .ititle{flex:1 1 300px;min-width:0;font-size:var(--fs-small);line-height:var(--lh-small);color:var(--text);font-weight:520}
.item .imeta{font-family:var(--mono);font-size:11px;color:var(--warn);white-space:nowrap}
.item .ibody{padding:var(--s3) var(--s4) var(--s4);display:grid;gap:var(--s2)}
.kv{display:grid;grid-template-columns:128px minmax(0,1fr);gap:var(--s3);align-items:baseline}
.kv>span{font-size:var(--fs-small);line-height:var(--lh-small);color:var(--dim);text-align:left}
.ilbl{font-family:var(--mono);font-size:var(--fs-label);letter-spacing:.18em;text-transform:uppercase;color:var(--accent-dim)}
.xref{font-family:var(--mono);font-size:10.5px;color:var(--comment)}
.xref a{color:var(--comment);text-decoration:underline;text-underline-offset:2px}
.xref a:hover{color:var(--accent);text-decoration:none}
.sig{display:flex;gap:var(--s3);flex-wrap:wrap;font-family:var(--mono);font-size:10.5px;color:var(--comment)}
.sig b{color:var(--dim);font-weight:500}
.legend{display:grid;gap:var(--s2);border:1px solid var(--line);border-radius:var(--radius-lg);background:var(--surface);padding:var(--s5);margin:var(--s5) 0}
.legend>div{display:flex;gap:var(--s3);align-items:baseline;flex-wrap:wrap}
.legend .lname{min-width:104px}
.legend p{margin:0}
.hero .mark{display:flex;width:44px;height:44px;align-items:center;justify-content:center;margin:0 auto var(--s4);border:1px solid var(--line-strong);border-radius:var(--radius-sm);background:var(--surface);font-family:var(--mono);font-size:16px;font-weight:700;color:var(--text);letter-spacing:-.04em}
.hero .mark .x{color:var(--accent)}
@media (max-width:700px){.kv{grid-template-columns:1fr;gap:var(--s1)}}
footer{text-align:center;padding:var(--s7) var(--s5) var(--s6);border-top:1px solid var(--line);font-family:var(--mono);font-size:11px;color:var(--comment);letter-spacing:.08em;line-height:2.1}
footer .x{color:var(--accent)}
footer a{color:var(--dim);display:inline-block;padding:12px 4px}
@media (max-width:900px){.g2,.g3,.g4{grid-template-columns:1fr}.hero{padding:64px var(--s5) 44px}.hero h1{font-size:34px;letter-spacing:-.022em}.hero .sub{font-size:16px}.pipe .stage{border-left:1px solid var(--line);border-radius:var(--radius-lg)!important;flex-basis:100%}.pipe .stage+.stage{margin-top:var(--s2)}.pipe .stage::after{content:''}.tier .tlat{text-align:left}}
@media (max-width:820px){nav a{padding:14px 8px}}
@media (max-width:560px){.container{padding:0 var(--s4)}nav{font-size:10.5px;gap:0 2px;flex-wrap:nowrap;justify-content:flex-start;overflow-x:auto;scrollbar-width:none}nav::-webkit-scrollbar{display:none}nav::after{content:'';position:sticky;right:0;flex:0 0 28px;margin-left:-28px;background:linear-gradient(90deg,transparent,rgba(0,30,43,.95));pointer-events:none}nav a{padding:14px 8px}table{font-size:13px}th,td{padding:10px var(--s3)}pre{font-size:11.5px;padding:var(--s3) var(--s4)}}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}*{animation:none!important;transition:none!important}}
@media (prefers-reduced-transparency:reduce){nav{background:var(--bg);backdrop-filter:none}}
@media (prefers-contrast:more){:root{--dim:#E8EDEB;--comment:#C1C7C6}.card,.note,p,li,td{color:var(--dim)}nav a{color:#E8EDEB}}
@media print{nav,.skip{display:none}section{page-break-inside:avoid}}
/* ── component layer ──────────────────────────────────────────────────────
   Diagrams, tabs, code, filters, steps, checklists, highlights, category
   chips, verdict cards, terminal cards, open tables and flow trees. Colours
   come from the :root tokens only; a tint is color-mix over a token.       */
html{scroll-padding-top:96px}
h3.sub-h{font-size:var(--fs-h3);line-height:var(--lh-h3);letter-spacing:var(--ls-h3);font-weight:640;margin:var(--s6) 0 var(--s3)}
section>p strong{color:var(--text)}
kbd{font-family:var(--mono);font-size:12px;line-height:1.4;color:var(--text);background:var(--surface-2);border:1px solid var(--line-strong);border-bottom-width:2px;border-radius:4px;padding:1px 6px}
/* diagram: a figure holding inline SVG, named for assistive tech, with a text alternative */
.diagram{margin:var(--s5) 0;border:1px solid var(--line);border-radius:var(--radius-lg);background:var(--surface-2);padding:var(--s4) var(--s4) var(--s3)}
.diagram .canvas{overflow-x:auto;scrollbar-width:thin;scrollbar-color:var(--line-strong) transparent}
.diagram svg{display:block;width:100%;height:auto;min-width:720px}
.diagram figcaption{font-size:var(--fs-small);line-height:var(--lh-small);color:var(--dim);margin-top:var(--s3);text-align:left}
.diagram figcaption b{color:var(--text);font-weight:600}
.diagram details{margin-top:var(--s2);font-size:var(--fs-small);line-height:var(--lh-small);color:var(--dim)}
.diagram details>summary{cursor:pointer;font-family:var(--mono);font-size:12px;color:var(--accent-dim);padding:8px 0;min-height:32px}
.diagram details ol,.diagram details ul{padding-left:var(--s5);display:grid;gap:var(--s1)}
.dg-node rect{fill:var(--surface);stroke:var(--line-strong);stroke-width:1}
.dg-node.is-source rect{stroke:var(--accent);stroke-width:1.5}
.dg-node.is-gate rect{stroke:var(--warn);stroke-dasharray:5 4}
.dg-node .t{fill:var(--text);font-family:var(--mono);font-size:13px;font-weight:600}
.dg-node .d{fill:var(--dim);font-family:var(--sans);font-size:11.5px}
.dg-edge{fill:none;stroke:var(--accent-dim);stroke-width:1.5}
.dg-edge.is-check{stroke:var(--warn);stroke-dasharray:5 4}
.dg-head{fill:var(--accent-dim)}
.dg-head.is-check{fill:var(--warn)}
.dg-lbl{fill:var(--dim);font-family:var(--mono);font-size:11px}
/* tabs: underline tabs in the reading voice; one accent bar slides under the chosen tab.
   The script builds the tab row from .tabpanel blocks; without it the panels stack. */
.tabs{margin:var(--s5) 0}
.tabs .tablist{position:relative;display:flex;gap:var(--s1);border-bottom:1px solid var(--line-strong);overflow-x:auto;scrollbar-width:none;scroll-snap-type:x proximity}
.tabs .tablist::-webkit-scrollbar{display:none}
.tabs .tablist.has-more{-webkit-mask-image:linear-gradient(90deg,#000 82%,transparent);mask-image:linear-gradient(90deg,#000 82%,transparent)}
.tabs [role=tab]{flex:0 0 auto;display:inline-flex;align-items:center;gap:var(--s2);font:inherit;font-family:var(--sans);font-size:14px;line-height:1.3;font-weight:560;color:var(--dim);background:none;border:0;border-radius:var(--radius-sm) var(--radius-sm) 0 0;padding:12px 14px;min-height:44px;cursor:pointer;white-space:nowrap;scroll-snap-align:start;transition:color .15s ease,background-color .15s ease}
.tabs [role=tab] .tab-key{font-family:var(--mono);font-size:12px;font-weight:700;color:var(--comment)}
.tabs [role=tab][aria-selected=true]{color:var(--text);font-weight:650}
.tabs [role=tab][aria-selected=true] .tab-key{color:var(--accent)}
.tabs [role=tab]:focus-visible{outline-offset:-2px}
@media (hover:hover) and (pointer:fine){.tabs [role=tab]:hover{color:var(--text);background:var(--surface)}}
.tabs .tab-ind{position:absolute;left:0;bottom:0;width:1px;height:2px;background:var(--accent);transform-origin:0 0;transition:transform 220ms cubic-bezier(.23,1,.32,1);pointer-events:none}
.tabs .tab-ind.is-instant{transition:none}
.tabs.is-enhanced .tabpanel{padding:var(--s5) 0 0}
.tabs:not(.is-enhanced) .tabpanel{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius-lg);padding:var(--s5);margin-bottom:var(--s3)}
.tabpanel:focus-visible{outline-offset:6px}
.tabpanel>:first-child{margin-top:0} .tabpanel>:last-child{margin-bottom:0} .tabpanel>.pipe{margin:0}
.tabs.is-enhanced .tab-h{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%);white-space:nowrap}
.tabpanel h4{font-size:var(--fs-h3);line-height:var(--lh-h3);font-weight:680;margin:0 0 var(--s2);display:flex;gap:var(--s2) var(--s3);align-items:center;flex-wrap:wrap}
.tabpanel p{font-size:var(--fs-body);line-height:1.65;color:var(--dim);margin:0}
/* gains and costs: the sign is drawn and repeated as a hidden word */
.proscons{list-style:none;margin:var(--s4) 0 0;padding:0;display:grid;gap:var(--s2)}
.proscons>li{display:grid;grid-template-columns:22px minmax(0,1fr);align-items:baseline;margin:0;padding:var(--s2) 0;border-top:1px solid var(--line);font-size:var(--fs-small);line-height:var(--lh-small);color:var(--dim)}
.proscons .pm{font-family:var(--mono);font-size:14px;font-weight:700;text-align:center}
.proscons .pro .pm{color:var(--ok)} .proscons .con .pm{color:var(--bad)}
/* code block: a labelled header, the code, and a copy button the script reveals */
.code{margin:var(--s4) 0;border:1px solid var(--line);border-radius:var(--radius-lg);background:var(--surface);overflow:hidden}
.code .code-head{display:flex;justify-content:space-between;align-items:center;gap:var(--s3);padding:6px var(--s2) 6px var(--s4);border-bottom:1px solid var(--line);font-family:var(--mono);font-size:12px;color:var(--dim)}
.code pre{margin:0;border:none;border-radius:0;background:none}
.code pre .add{color:var(--ok)} .code pre .del{color:var(--bad)}
.copy,.tool{font:inherit;font-family:var(--mono);font-size:12px;color:var(--dim);background:var(--surface);border:1px solid var(--line-strong);border-radius:var(--radius-sm);padding:4px 12px;min-height:32px;cursor:pointer}
@media (hover:hover) and (pointer:fine){.copy:hover,.tool:hover{color:var(--accent);border-color:var(--accent)}}
.copy,.tool,.chip{transition:transform 160ms ease-out,color .15s ease,border-color .15s ease,background-color .15s ease}
.copy:active,.tool:active,.chip:active{transform:scale(.97)}
@media (pointer:coarse){.copy,.tool,.chip{min-height:44px}}
/* filters: a single-choice chip row that narrows a list or a table */
.filters{display:flex;gap:var(--s2);flex-wrap:wrap;align-items:center;margin:var(--s4) 0 0}
.filters .flbl{font-family:var(--mono);font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--comment);margin-right:var(--s1)}
.chip{font:inherit;font-family:var(--mono);font-size:12px;color:var(--dim);background:var(--surface);border:1px solid var(--line-strong);border-radius:999px;padding:6px 14px;min-height:32px;cursor:pointer}
@media (hover:hover) and (pointer:fine){.chip:hover{color:var(--accent);border-color:var(--accent)}}
.chip[aria-pressed=true]{color:var(--bg);background:var(--accent);border-color:var(--accent);font-weight:700}
.chip[aria-pressed=true]::before{content:'\2713\00a0'}
.toolbar{display:flex;justify-content:flex-end;gap:var(--s2);margin:var(--s4) 0 calc(-1 * var(--s3))}
/* steps: an ordered sequence the reader follows top to bottom */
.steps{list-style:none;counter-reset:step;margin:var(--s5) 0;display:grid;gap:var(--s2)}
.steps>li{counter-increment:step;position:relative;padding:var(--s3) var(--s4) var(--s3) 60px;border:1px solid var(--line);border-radius:var(--radius-lg);background:var(--surface);font-size:var(--fs-small);line-height:var(--lh-small);color:var(--dim)}
.steps>li::before{content:counter(step,decimal-leading-zero);position:absolute;left:var(--s4);top:var(--s3);font-family:var(--mono);font-size:12px;font-weight:600;color:var(--accent)}
.steps>li b{color:var(--text);font-weight:600}
/* checklist: a criterion with its state written as a word, never colour alone */
.checklist{list-style:none;margin:var(--s4) 0;display:grid;gap:var(--s2)}
.checklist>li{display:grid;grid-template-columns:88px minmax(0,1fr);gap:var(--s3);align-items:baseline;font-size:var(--fs-small);line-height:var(--lh-small);color:var(--dim);padding:var(--s2) 0;border-bottom:1px solid var(--line)}
.checklist>li:last-child{border-bottom:none}
.checklist .state{font-family:var(--mono);font-size:11px;letter-spacing:.06em}
.checklist b{color:var(--text);font-weight:600}
.item .ibody p{font-size:var(--fs-small);line-height:var(--lh-small);color:var(--dim)}
[hidden]{display:none!important}
@media (max-width:700px){.checklist>li{grid-template-columns:1fr;gap:var(--s1)}.steps>li{padding-left:var(--s4);padding-top:36px}}
@media (max-width:560px){.item>summary{flex-wrap:nowrap;align-items:flex-start}.item .ititle{flex:1 1 auto}}
/* highlight: the one callout that carries an accent bar (rule 12 allows it here only) */
.callout{background:var(--surface);border:1px solid var(--line);border-left:3px solid var(--accent);border-radius:0 var(--radius-lg) var(--radius-lg) 0;padding:var(--s5);margin:var(--s5) 0}
.callout.is-bad{border-left-color:var(--bad)} .callout.is-warn{border-left-color:var(--warn)}
.callout h3{font-size:var(--fs-h4);line-height:var(--lh-h4);font-weight:680;color:var(--text);margin:0 0 var(--s2)}
.callout p{font-size:var(--fs-body);line-height:1.7;color:var(--dim);margin:0}
.callout b,.card b,td b{color:var(--text);font-weight:650}
/* category chip: the word names the category; the hue only groups it */
.cat{display:inline-block;font-family:var(--mono);font-size:11px;line-height:1.5;font-weight:600;letter-spacing:.04em;padding:3px 10px;border-radius:999px;white-space:nowrap;vertical-align:middle;color:var(--dim);border:1px solid var(--hue);background:color-mix(in srgb,var(--hue) 12%,transparent)}
.cat.c-green{--hue:var(--accent);color:var(--cat-green)}
.cat.c-purple{--hue:var(--purple);color:var(--cat-purple)}
.cat.c-amber{--hue:var(--warn);color:var(--cat-amber)}
.cat.c-red{--hue:var(--bad);color:var(--cat-red)}
.cat.c-blue{--hue:var(--blue);color:var(--cat-blue)}
/* card head: a chip and a title on one line; verdict cards wear a full coloured border */
.card .card-h{display:flex;align-items:center;gap:var(--s2) var(--s3);flex-wrap:wrap;font-size:var(--fs-h3);line-height:var(--lh-h3);font-weight:680;min-height:0;margin:0 0 var(--s1)}
.card p{color:var(--dim)}
.card ul>li{margin:0}
.card ul{padding-left:var(--s5);display:grid;gap:var(--s2);font-size:var(--fs-small);line-height:var(--lh-small);color:var(--dim)}
.card.is-good{border-color:color-mix(in srgb,var(--ok) 55%,transparent)}
.card.is-bad{border-color:color-mix(in srgb,var(--bad) 60%,transparent)}
.card.is-warn{border-color:color-mix(in srgb,var(--warn) 55%,transparent)}
.card pre.term{background:none;border:none;padding:0;margin:var(--s1) 0 0;font-size:12.5px;line-height:1.75;color:var(--dim)}
.term .ok{color:var(--ok)} .term .bad{color:var(--bad)} .term .b{color:var(--text);font-weight:600}
/* open table: no box, a strong header rule, quiet row rules */
.tbl-wrap{background:transparent;border:none;border-radius:0}
.tbl-wrap th{border-bottom:2px solid var(--line-strong);white-space:normal}
.tbl-wrap td{border-bottom:1px solid var(--line-strong);color:var(--dim)}
.tbl-wrap td:first-child{color:var(--text)}
@media (max-width:640px){
  table.is-stackable{min-width:0}
  table.is-stackable thead{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%)}
  table.is-stackable,table.is-stackable tbody,table.is-stackable tr,table.is-stackable td{display:block;width:100%}
  table.is-stackable tr{padding:var(--s3) 0;border-bottom:1px solid var(--line-strong)}
  table.is-stackable td{border:none;padding:var(--s1) 0}
  table.is-stackable td:first-child{font-size:var(--fs-body);padding-bottom:var(--s2)}
  table.is-stackable td[data-label]:not(:first-child)::before{content:attr(data-label);content:attr(data-label) / "";display:block;font-family:var(--mono);font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--accent-dim);margin-bottom:2px}
}
.mark-ok{color:var(--ok);font-weight:650} .mark-bad{color:var(--bad);font-weight:650} .mark-warn{color:var(--warn);font-weight:650}
/* flow tree: a terminal-shaped diagram; tree glyphs are hidden from screen readers */
.flow{font-family:var(--mono);font-size:12.5px;line-height:1.85;color:var(--dim);background:var(--surface);border:1px solid var(--line);border-radius:var(--radius-lg);padding:var(--s5);margin:0;scrollbar-width:thin;scrollbar-color:var(--line-strong) transparent}
.flow .nd{color:var(--accent);font-weight:700} .flow .ed{color:var(--comment)} .flow .lb{color:var(--accent-dim)}
.flow .wd{color:var(--warn)} .flow .rd{color:var(--bad);font-weight:600} .flow .b{color:var(--text);font-weight:600}
figure.bracket{margin:var(--s6) 0 var(--s5)}
figure.bracket>figcaption.tag{line-height:1.6}
/* type floor: no label under 11px, no running text under 12px */
.stat .l,th,.note h3,.note h4,.ilbl,.pipe .ph,.bracket>.tag,.pill,.band,.xref,.sig,.card .src,.item .imeta{font-size:11px}
nav{font-size:11.5px}
footer{font-size:12px;letter-spacing:.02em}
.pipe .q,.hero .meta{font-size:12px}
.hero .sub{text-align:center}
@media (forced-colors:active){
  .card,.note,.item,.stat,.tier,.legend,.tbl-wrap,.diagram,.code,.steps>li,.tabs .tabpanel,.flow,.cat{border:1px solid CanvasText}
  .callout{border:1px solid CanvasText;border-left:4px solid CanvasText}
  .chip,.copy,.tool{border:1px solid ButtonText}
  .chip[aria-pressed=true]{forced-color-adjust:none;background:Highlight;color:HighlightText;border-color:Highlight}
  .tabs [role=tab][aria-selected=true]{text-decoration:underline;text-underline-offset:6px;text-decoration-thickness:2px}
  .tabs .tab-ind{background:Highlight}
  .dg-node rect{fill:Canvas;stroke:CanvasText} .dg-node .t,.dg-node .d,.dg-lbl{fill:CanvasText}
  .dg-edge{stroke:CanvasText} .dg-head{fill:CanvasText}
  :focus-visible{outline:2px solid Highlight}
}
@media print{
  :root{--bg:var(--print-bg);--surface:var(--print-bg);--surface-2:var(--print-bg);--text:var(--print-text);--dim:var(--print-dim);--comment:var(--print-dim);--accent:var(--print-accent);--accent-dim:var(--print-accent);--ok:var(--print-accent);--bad:var(--print-bad);--warn:var(--print-warn);--orange:var(--print-warn);--line:var(--print-line);--line-strong:var(--print-line)}
  body{background:var(--print-bg);color:var(--print-text)}
  .hero{background-image:none}
  .pill,.band,.chip,.cat{background:none!important}
  .cat{color:var(--text)!important;border-color:var(--line-strong)!important}
  .tabs .tablist,.copy,.tool,.filters,.toolbar,.hero .corner{display:none!important}
  .tabs .tabpanel{display:block!important;border:1px solid var(--line-strong)}
  .diagram,.code,.card,.note,.item,.steps>li{break-inside:avoid}
}
/* brand:end */
/* The gallery adds no style of its own: it is the reference for the shared
   classes, so a rule that lives only here would prove nothing. */
</style>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<div id="live" class="sr" role="status" aria-live="polite"></div>

<header class="hero">
  <span class="corner tl"></span><span class="corner tr"></span>
  <span class="corner bl"></span><span class="corner br"></span>
  <div class="mark"><span class="x">{</span>ai<span class="x">}</span></div>
  <h1>The gallery</h1>
  <p class="sub">Every part of an artifact, live, with the markup that makes it. Read this page before writing one; copy a template instead of a style.</p>
  <div class="meta">Source: <b>brand/components.css</b> and <b>brand/components.js</b> · generated into <b>brand/gallery.html.tpl</b> by <b>bun scripts/brand.ts gen</b></div>
</header>

<nav>
  <a href="#g-structure"><b>01</b>Structure</a>
  <a href="#g-blocks"><b>02</b>Blocks</a>
  <a href="#g-diagrams"><b>03</b>Diagrams</a>
  <a href="#g-interactive"><b>04</b>Interactive</a>
  <a href="#g-behaviour"><b>05</b>Behaviour</a>
</nav>

<main id="main">
<div class="container">

<section id="g-structure" aria-labelledby="g-h-structure">
  <h2 id="g-h-structure"><span class="num">01</span>The structure every page shares</h2>
  <p>A page is a hero, a sticky nav, numbered sections and a footer. Nothing else is invented: if a page needs a part that is not on this page, the part is added here first.</p>
  <div class="grid g2">

    <article class="card" id="g-hero">
      <h3>Hero and the {ai} mark</h3>
      <p class="src">header.hero · .mark · h1 · .sub · .meta</p>
      <p>Live at the top of this page: the mark names the family before the subject, then one <code>h1</code>, one subtitle and one meta line.</p>
      <div class="code"><div class="code-head"><span>markup</span><button class="copy" type="button" hidden>Copy</button></div><pre><code>&lt;header class="hero"&gt;
  &lt;div class="mark"&gt;&lt;span class="x"&gt;{&lt;/span&gt;ai&lt;span class="x"&gt;}&lt;/span&gt;&lt;/div&gt;
  &lt;h1&gt;{{title}}&lt;/h1&gt;
  &lt;p class="sub"&gt;{{subtitle}}&lt;/p&gt;
&lt;/header&gt;</code></pre></div>
      <ul class="checklist">
        <li><span class="state mark-ok">Do</span><span>One <code>h1</code>, the page's subject.</span></li>
        <li><span class="state mark-bad">Don't</span><span>Add a stamp line under the mark; the mark already names the family.</span></li>
      </ul>
    </article>

    <article class="card" id="g-section">
      <h3>Section and its number</h3>
      <p class="src">section · h2 · .num</p>
      <p>The number is a coordinate a reviewer cites, so it is never decoration.</p>
      <div class="code"><div class="code-head"><span>markup</span><button class="copy" type="button" hidden>Copy</button></div><pre><code>&lt;section id="s1" aria-labelledby="h-s1"&gt;
  &lt;h2 id="h-s1"&gt;&lt;span class="num"&gt;01&lt;/span&gt;The idea&lt;/h2&gt;
  &lt;p&gt;One plain sentence, then the visual.&lt;/p&gt;
&lt;/section&gt;</code></pre></div>
      <ul class="checklist">
        <li><span class="state mark-ok">Do</span><span>Open each section with one plain sentence (D13).</span></li>
        <li><span class="state mark-bad">Don't</span><span>Skip a heading level to reach the size you want.</span></li>
      </ul>
    </article>

    <article class="card" id="g-footer">
      <h3>Footer and the AI note</h3>
      <p class="src">footer · meta generator</p>
      <p>The footer and a <code>generator</code> meta say an AI agent wrote the page (EU AI Act, class minimal).</p>
      <div class="code"><div class="code-head"><span>markup</span><button class="copy" type="button" hidden>Copy</button></div><pre><code>&lt;meta name="generator" content="ai-engineering, written by an AI agent"&gt;
&lt;footer&gt;
  &lt;span class="x"&gt;{&lt;/span&gt;ai&lt;span class="x"&gt;}&lt;/span&gt; Engineering · Brainstorm ·
  written by an AI agent
&lt;/footer&gt;</code></pre></div>
      <ul class="checklist">
        <li><span class="state mark-ok">Do</span><span>Keep both the meta and the footer line.</span></li>
        <li><span class="state mark-bad">Don't</span><span>Remove the attribution to save a line.</span></li>
      </ul>
    </article>

    <article class="card" id="g-nav">
      <h3>Nav and the scroll-spy</h3>
      <p class="src">nav · a.active · aria-current</p>
      <p>The template's script marks the link whose heading has cleared the bar, at the same 88px as <code>scroll-margin-top</code>.</p>
      <div class="kv"><span class="ilbl">Keys</span><span>Tab reaches every link; the light focus ring clears the sticky bar (2.4.11).</span></div>
      <div class="code"><div class="code-head"><span>markup</span><button class="copy" type="button" hidden>Copy</button></div><pre><code>&lt;nav&gt;
  &lt;a href="#s1"&gt;&lt;b&gt;01&lt;/b&gt;The idea&lt;/a&gt;
&lt;/nav&gt;</code></pre></div>
      <ul class="checklist">
        <li><span class="state mark-ok">Do</span><span>Add one link per numbered section, in order.</span></li>
        <li><span class="state mark-bad">Don't</span><span>Paint the active section by hand; the spy owns it.</span></li>
      </ul>
    </article>

  </div>
</section>

<section id="g-blocks" aria-labelledby="g-h-blocks">
  <h2 id="g-h-blocks"><span class="num">02</span>The blocks prose is made of</h2>
  <p>These carry the words. Each one sets its own leading, so a pill or a label looks the same in a card, a table cell and a note.</p>
  <div class="grid g2">

    <article class="card" id="g-card">
      <h3>Card</h3>
      <p class="src">.card · .src · .card-h</p>
      <p>A unit of prose with a heading, two to four per row.</p>
      <div class="grid g2">
        <div class="card"><h4 class="card-h"><span class="cat c-green">kept</span> A chip and a title</h4><p>The head puts state and subject on one line.</p></div>
        <div class="card"><h4>A plain card</h4><p>Reach for it before inventing a box.</p></div>
      </div>
      <div class="code"><div class="code-head"><span>markup</span><button class="copy" type="button" hidden>Copy</button></div><pre><code>&lt;article class="card"&gt;
  &lt;h4 class="card-h"&gt;&lt;span class="cat c-green"&gt;kept&lt;/span&gt; Title&lt;/h4&gt;
  &lt;p&gt;One subject.&lt;/p&gt;
&lt;/article&gt;</code></pre></div>
      <ul class="checklist">
        <li><span class="state mark-ok">Do</span><span>One subject per card, one heading at its top.</span></li>
        <li><span class="state mark-bad">Don't</span><span>Nest a card inside a card.</span></li>
      </ul>
    </article>

    <article class="card" id="g-note">
      <h3>Note</h3>
      <p class="src">.note · .ok · .warn · .danger</p>
      <div class="note ok"><h4>Checked</h4><p>A rule the reader must not miss.</p></div>
      <div class="note warn"><h4>Watch</h4><p>The same block, amber.</p></div>
      <div class="note danger"><h4>Stop</h4><p>The same block, red.</p></div>
      <div class="code"><div class="code-head"><span>markup</span><button class="copy" type="button" hidden>Copy</button></div><pre><code>&lt;div class="note warn"&gt;
  &lt;h4&gt;Watch&lt;/h4&gt;&lt;p&gt;One line.&lt;/p&gt;
&lt;/div&gt;</code></pre></div>
      <ul class="checklist">
        <li><span class="state mark-ok">Do</span><span>Keep a note to one short paragraph.</span></li>
        <li><span class="state mark-bad">Don't</span><span>Stack three notes where one sentence would do.</span></li>
      </ul>
    </article>

    <article class="card" id="g-pill">
      <h3>Pill and band</h3>
      <p class="src">.pill · .band</p>
      <p>A state inside a cell or a heading. The word always names the state; colour repeats it.</p>
      <p><span class="pill p-ok">kept</span> <span class="pill p-warn">extended</span> <span class="pill p-bad">removed</span> <span class="pill p-fix">new</span> <span class="pill p-dim">frozen</span></p>
      <p><span class="band band-p0">P0</span> <span class="band band-p1">P1</span> <span class="band band-p2">P2</span> <span class="band band-p3">P3</span></p>
      <div class="code"><div class="code-head"><span>markup</span><button class="copy" type="button" hidden>Copy</button></div><pre><code>&lt;span class="pill p-ok"&gt;kept&lt;/span&gt;
&lt;span class="band band-p1"&gt;P1&lt;/span&gt;</code></pre></div>
      <ul class="checklist">
        <li><span class="state mark-ok">Do</span><span>Key every chip in the page's <code>.legend</code>.</span></li>
        <li><span class="state mark-bad">Don't</span><span>Let colour alone carry the state.</span></li>
      </ul>
    </article>

    <article class="card" id="g-legend">
      <h3>Legend</h3>
      <p class="src">.legend · .lname</p>
      <div class="legend">
        <div><span class="lname"><span class="band band-p1">P1</span></span><p>Blocks: the next milestone waits for this.</p></div>
        <div><span class="lname"><span class="band band-p3">P3</span></span><p>Informs: one line, or silence.</p></div>
      </div>
      <div class="code"><div class="code-head"><span>markup</span><button class="copy" type="button" hidden>Copy</button></div><pre><code>&lt;div class="legend"&gt;
  &lt;div&gt;&lt;span class="lname"&gt;&lt;span class="band band-p1"&gt;P1&lt;/span&gt;&lt;/span&gt;
  &lt;p&gt;Blocks …&lt;/p&gt;&lt;/div&gt;
&lt;/div&gt;</code></pre></div>
      <ul class="checklist">
        <li><span class="state mark-ok">Do</span><span>Put the legend with the first section that uses the chip.</span></li>
        <li><span class="state mark-bad">Don't</span><span>Use a chip the page never explains.</span></li>
      </ul>
    </article>

    <article class="card" id="g-table">
      <h3>Table</h3>
      <p class="src">.tbl-wrap · table · caption · th scope</p>
      <div class="tbl-wrap">
        <table class="is-stackable">
          <caption>Three parts and what each one proves</caption>
          <thead><tr><th scope="col">Part</th><th scope="col">Proves</th><th scope="col">Where</th></tr></thead>
          <tbody>
            <tr><td>Styles</td><td>Every page is one family</td><td><code>brand/components.css</code></td></tr>
            <tr><td>Script</td><td>Tabs, copy, filters</td><td><code>brand/components.js</code></td></tr>
            <tr><td>Gate</td><td>Markup meets WCAG</td><td><code>bun test</code></td></tr>
          </tbody>
        </table>
      </div>
      <div class="code"><div class="code-head"><span>markup</span><button class="copy" type="button" hidden>Copy</button></div><pre><code>&lt;div class="tbl-wrap"&gt;&lt;table class="is-stackable"&gt;
  &lt;caption&gt;What this table is about&lt;/caption&gt;
  &lt;thead&gt;&lt;tr&gt;&lt;th scope="col"&gt;Part&lt;/th&gt;&lt;/tr&gt;&lt;/thead&gt;
  &lt;tbody&gt;&lt;tr&gt;&lt;td&gt;Styles&lt;/td&gt;&lt;/tr&gt;&lt;/tbody&gt;
&lt;/table&gt;&lt;/div&gt;</code></pre></div>
      <ul class="checklist">
        <li><span class="state mark-ok">Do</span><span>Give every table a caption and every <code>th</code> a scope.</span></li>
        <li><span class="state mark-bad">Don't</span><span>Box a table; an open table reads better.</span></li>
      </ul>
    </article>

    <article class="card" id="g-stats">
      <h3>Stats, marks and signals</h3>
      <p class="src">.stats · .check · .xref · .sig</p>
      <div class="stats">
        <div class="stat"><div class="v">52<em>/52</em></div><div class="l">Pairs</div></div>
        <div class="stat"><div class="v">8</div><div class="l">Templates</div></div>
        <div class="stat"><div class="v">0</div><div class="l">Violations</div></div>
      </div>
      <p><span class="check">✔ pass</span> · <span class="cross">✘ fail</span> · <span class="half">⚠ partial</span></p>
      <p class="xref">also in §04, §06</p>
      <p class="sig"><b>3</b> open · <b>1</b> blocking</p>
      <div class="code"><div class="code-head"><span>markup</span><button class="copy" type="button" hidden>Copy</button></div><pre><code>&lt;div class="stats"&gt;
  &lt;div class="stat"&gt;&lt;div class="v"&gt;52&lt;em&gt;/52&lt;/em&gt;&lt;/div&gt;
  &lt;div class="l"&gt;Pairs&lt;/div&gt;&lt;/div&gt;
&lt;/div&gt;
&lt;span class="check"&gt;✔ pass&lt;/span&gt;</code></pre></div>
      <ul class="checklist">
        <li><span class="state mark-ok">Do</span><span>Follow every mark with a word.</span></li>
        <li><span class="state mark-bad">Don't</span><span>Build a dashboard; a stats row is not one.</span></li>
      </ul>
    </article>

    <article class="card" id="g-item">
      <h3>Item, and expand all</h3>
      <p class="src">.items · .item · .toolbar · .kv · .ilbl</p>
      <div class="toolbar"><button class="tool" type="button" data-expand="g-items" hidden>Expand all</button></div>
      <div class="items" id="g-items">
        <details class="item" id="g-i1"><summary><span class="iid">D1</span><span class="ititle">A native disclosure, never a scripted one</span></summary>
          <div class="ibody"><div class="kv"><span class="ilbl">Why</span><span>Keyboard, find-in-page and print keep working with no script.</span></div></div></details>
        <details class="item" id="g-i2"><summary><span class="iid">D2</span><span class="ititle">The summary scans closed, the body explains open</span></summary>
          <div class="ibody"><div class="kv"><span class="ilbl">Effect</span><span>An id, a title and a chip; the body carries the context.</span></div></div></details>
      </div>
      <div class="code"><div class="code-head"><span>markup</span><button class="copy" type="button" hidden>Copy</button></div><pre><code>&lt;div class="toolbar"&gt;
  &lt;button class="tool" type="button" data-expand="items" hidden&gt;Expand all&lt;/button&gt;
&lt;/div&gt;
&lt;div class="items" id="items"&gt;
  &lt;details class="item"&gt;&lt;summary&gt;&lt;span class="iid"&gt;D1&lt;/span&gt;
  &lt;span class="ititle"&gt;Title&lt;/span&gt;&lt;/summary&gt;&lt;div class="ibody"&gt;…&lt;/div&gt;&lt;/details&gt;
&lt;/div&gt;</code></pre></div>
      <ul class="checklist">
        <li><span class="state mark-ok">Do</span><span>Give every item a unique id when another section links to it.</span></li>
        <li><span class="state mark-bad">Don't</span><span>Repeat an id across sections; suffix the later one <code>-s&lt;NN&gt;</code>.</span></li>
      </ul>
    </article>

    <article class="card" id="g-steps">
      <h3>Steps and checklist</h3>
      <p class="src">ol.steps · ul.checklist · .state</p>
      <ol class="steps">
        <li><b>Copy the template.</b> One file, inside the project.</li>
        <li><b>Fill its sections.</b> Words, tables, diagrams.</li>
        <li><b>Run the gate.</b> Parity, the static gate, then Chrome.</li>
      </ol>
      <ul class="checklist">
        <li><span class="state mark-ok">Do</span><span>Keep the order the reader follows.</span></li>
        <li><span class="state mark-bad">Don't</span><span>Number a list that has no order.</span></li>
      </ul>
      <div class="code"><div class="code-head"><span>markup</span><button class="copy" type="button" hidden>Copy</button></div><pre><code>&lt;ol class="steps"&gt;&lt;li&gt;&lt;b&gt;Copy&lt;/b&gt; the template.&lt;/li&gt;&lt;/ol&gt;
&lt;ul class="checklist"&gt;&lt;li&gt;&lt;span class="state mark-ok"&gt;Do&lt;/span&gt;
&lt;span&gt;The rule.&lt;/span&gt;&lt;/li&gt;&lt;/ul&gt;</code></pre></div>
    </article>

    <article class="card" id="g-bracket">
      <h3>Bracket, pipeline and tiers</h3>
      <p class="src">.bracket · .pipe · .tiers</p>
      <figure class="bracket"><figcaption class="tag">shell</figcaption><pre><code>bun scripts/brand.ts gen</code></pre></figure>
      <div class="pipe">
        <div class="stage"><div class="ph">01 · source</div><div class="sk">brand/</div><div class="q">one place</div></div>
        <div class="stage"><div class="ph">02 · gen</div><div class="sk">templates</div><div class="q">inlined</div></div>
        <div class="stage"><div class="ph">03 · gate</div><div class="sk">bun test</div><div class="q">red on drift</div></div>
      </div>
      <div class="tiers">
        <div class="tier"><span class="tname">blocks</span><span class="tbody">Drift, a WCAG miss, an external request.</span><span class="tlat">must fix</span></div>
        <div class="tier"><span class="tname">informs</span><span class="tbody">Weight over the budget.</span><span class="tlat">one line</span></div>
      </div>
      <ul class="checklist">
        <li><span class="state mark-ok">Do</span><span>Use a pipeline when the boxes are the message.</span></li>
        <li><span class="state mark-bad">Don't</span><span>Draw a pipeline with an image.</span></li>
      </ul>
    </article>

  </div>
</section>

<section id="g-diagrams" aria-labelledby="g-h-diagrams">
  <h2 id="g-h-diagrams"><span class="num">03</span>Diagrams carry a text version</h2>
  <p>A diagram is a figure with an inline SVG, a title, a description and a text version a reader can open; colour comes from brand classes, never from the drawing.</p>

  <article class="card" id="g-diagram">
    <h3>Diagram</h3>
    <p class="src">figure.diagram · svg role="img" · .dg-node · .dg-edge · .dg-head</p>
    <figure class="diagram" aria-labelledby="g-dg-cap">
      <div class="canvas">
        <svg viewBox="0 0 960 200" role="img" aria-labelledby="g-dg-title g-dg-desc">
          <title id="g-dg-title">Three source files feed one generator, which writes every page</title>
          <desc id="g-dg-desc">A tokens file and two component files point into a generator box. The generator points to one page box that stands for all eight templates.</desc>
          <g class="dg-node is-source"><rect x="20" y="40" width="210" height="60" rx="8"/><text class="t" x="36" y="68">tokens.json</text><text class="d" x="36" y="88">every value</text></g>
          <g class="dg-node is-source"><rect x="20" y="112" width="210" height="60" rx="8"/><text class="t" x="36" y="140">components.css</text><text class="d" x="36" y="160">every part</text></g>
          <g class="dg-node is-gate"><rect x="370" y="76" width="200" height="60" rx="8"/><text class="t" x="392" y="104">brand.ts gen</text><text class="d" x="392" y="124">inlines</text></g>
          <g class="dg-node"><rect x="710" y="76" width="220" height="60" rx="8"/><text class="t" x="732" y="104">eight templates</text><text class="d" x="732" y="124">one family</text></g>
          <path class="dg-edge" d="M230 70 L310 70 L310 96 L370 96"/>
          <path class="dg-edge" d="M230 142 L310 142 L310 116 L370 116"/>
          <path class="dg-edge is-check" d="M570 106 L710 106"/>
          <path class="dg-head" d="M704 101 L714 106 L704 111 Z"/>
          <path class="dg-head is-check" d="M704 101 L714 106 L704 111 Z"/>
          <text class="dg-lbl" x="586" y="98">writes</text>
        </svg>
      </div>
      <figcaption id="g-dg-cap"><b>Figure 1.</b> The source files, the generator and what it writes. The dashed edge is a check, not a write.</figcaption>
      <details><summary>Text version of figure 1</summary>
        <ol>
          <li><code>brand/tokens.json</code> and <code>brand/components.css</code> are the two sources.</li>
          <li><code>bun scripts/brand.ts gen</code> reads them and inlines the result.</li>
          <li>The eight templates come out carrying the same bytes.</li>
        </ol>
      </details>
    </figure>
    <div class="code"><div class="code-head"><span>markup</span><button class="copy" type="button" hidden>Copy</button></div><pre><code>&lt;figure class="diagram" aria-labelledby="d1-cap"&gt;
  &lt;div class="canvas"&gt;
    &lt;svg viewBox="0 0 960 200" role="img" aria-labelledby="d1-title d1-desc"&gt;
      &lt;title id="d1-title"&gt;What the picture shows&lt;/title&gt;
      &lt;desc id="d1-desc"&gt;A sentence a reader hears.&lt;/desc&gt;
      &lt;g class="dg-node is-source"&gt;&lt;rect x="20" y="40" width="210"
        height="60" rx="8"/&gt;&lt;text class="t" x="36" y="68"&gt;Source&lt;/text&gt;&lt;/g&gt;
      &lt;path class="dg-edge" d="M230 70 L370 96"/&gt;
      &lt;path class="dg-head" d="M704 101 L714 106 L704 111 Z"/&gt;
    &lt;/svg&gt;
  &lt;/div&gt;
  &lt;figcaption id="d1-cap"&gt;&lt;b&gt;Figure 1.&lt;/b&gt; What it shows.&lt;/figcaption&gt;
  &lt;details&gt;&lt;summary&gt;Text version of figure 1&lt;/summary&gt;&lt;ol&gt;…&lt;/ol&gt;&lt;/details&gt;
&lt;/figure&gt;</code></pre></div>
    <ul class="checklist">
      <li><span class="state mark-ok">Do</span><span>Write the text version; it is the picture for a screen reader.</span></li>
      <li><span class="state mark-bad">Don't</span><span>Put a colour on the drawing; brand classes own every stroke.</span></li>
    </ul>
  </article>

  <article class="card" id="g-flow">
    <h3>Flow tree</h3>
    <p class="src">figure.bracket · pre.flow · .nd · .ed · .lb · .wd · .rd</p>
    <figure class="bracket"><figcaption class="tag">where a page comes from</figcaption>
<pre class="flow"><span class="nd">templates/brainstorm.html.tpl</span>
├─ <span class="ed" aria-hidden="true">─▶</span> copy it into the project
├─ <span class="ed" aria-hidden="true">─▶</span> fill the sections with words
└─ <span class="wd" aria-hidden="true">─▶</span> run <span class="lb">bun test</span> · red on drift</pre>
    </figure>
    <div class="code"><div class="code-head"><span>markup</span><button class="copy" type="button" hidden>Copy</button></div><pre><code>&lt;figure class="bracket"&gt;
  &lt;figcaption class="tag"&gt;Where a page comes from&lt;/figcaption&gt;
  &lt;pre class="flow"&gt;&lt;span class="nd"&gt;source&lt;/span&gt;
  &lt;span class="ed" aria-hidden="true"&gt;─▶&lt;/span&gt; out&lt;/pre&gt;
&lt;/figure&gt;</code></pre></div>
    <ul class="checklist">
      <li><span class="state mark-ok">Do</span><span>Hide the tree glyphs; the words read in order without them.</span></li>
      <li><span class="state mark-bad">Don't</span><span>Let a glyph be the only thing that says what happens next.</span></li>
    </ul>
  </article>
</section>

<section id="g-interactive" aria-labelledby="g-h-interactive">
  <h2 id="g-h-interactive"><span class="num">04</span>The parts that respond</h2>
  <p>Every one of these reads with the script off: tabs stack as headed panels, and the copy, filter and expand buttons stay hidden until the script reveals them.</p>
  <div class="grid g2">

    <article class="card" id="g-tabs">
      <h3>Tabs</h3>
      <p class="src">.tabs · .tabpanel · data-tab · data-key · data-badge</p>
      <div class="tabs">
        <div class="tabpanel" id="g-panel-a" data-tab="The chosen one" data-key="A" data-badge="chosen">
          <h4>One panel, one heading</h4>
          <p>Options side by side, one visible. The row is built from the panels, so the markup is a plain list of headed panels.</p>
        </div>
        <div class="tabpanel" id="g-panel-b" data-tab="The other one" data-key="B">
          <h4>The second panel</h4>
          <p>Arrow keys move between tabs and select as they go; Home and End jump to the ends.</p>
        </div>
      </div>
      <div class="kv"><span class="ilbl">Keys</span><span>ArrowRight, ArrowLeft, Home, End move and select. With the script off the panels stack, each under its heading.</span></div>
      <div class="code"><div class="code-head"><span>markup</span><button class="copy" type="button" hidden>Copy</button></div><pre><code>&lt;div class="tabs"&gt;
  &lt;div class="tabpanel" id="p-a" data-tab="First" data-key="A"&gt;
    &lt;h4&gt;Heading&lt;/h4&gt;&lt;p&gt;One panel.&lt;/p&gt;
  &lt;/div&gt;
&lt;/div&gt;</code></pre></div>
      <ul class="checklist">
        <li><span class="state mark-ok">Do</span><span>Give each panel a heading; it is the tab's name with the script off.</span></li>
        <li><span class="state mark-bad">Don't</span><span>Put a tab row inside a tab panel.</span></li>
      </ul>
    </article>

    <article class="card" id="g-code">
      <h3>Code block and copy</h3>
      <p class="src">.code · .code-head · button.copy · #live</p>
      <div class="code"><div class="code-head"><span>shell · the one command</span><button class="copy" type="button" hidden>Copy</button></div><pre><code>bun scripts/brand.ts parity</code></pre></div>
      <div class="kv"><span class="ilbl">Keys</span><span>Tab reaches Copy; Enter or Space copies. The result is announced politely. Blocked from <code>file://</code>, it says to copy by hand.</span></div>
      <div class="code"><div class="code-head"><span>markup</span><button class="copy" type="button" hidden>Copy</button></div><pre><code>&lt;div class="code"&gt;
  &lt;div class="code-head"&gt;&lt;span&gt;shell&lt;/span&gt;
  &lt;button class="copy" type="button" hidden&gt;Copy&lt;/button&gt;&lt;/div&gt;
  &lt;pre&gt;&lt;code&gt;bun test&lt;/code&gt;&lt;/pre&gt;
&lt;/div&gt;</code></pre></div>
      <ul class="checklist">
        <li><span class="state mark-ok">Do</span><span>Label the block with what it is, not with a language name.</span></li>
        <li><span class="state mark-bad">Don't</span><span>Ship a Copy button that is visible before the script runs.</span></li>
      </ul>
    </article>

    <article class="card" id="g-diff">
      <h3>Diff lines</h3>
      <p class="src">pre .add · .del</p>
      <div class="code"><div class="code-head"><span>diff · one line each way</span><button class="copy" type="button" hidden>Copy</button></div><pre><code><span class="del">- copy that document's whole CSS block in verbatim</span>
<span class="add">+ copy templates/brainstorm.html.tpl and fill its sections</span></code></pre></div>
      <ul class="checklist">
        <li><span class="state mark-ok">Do</span><span>Write the <code>+</code> and the <code>-</code> in the text.</span></li>
        <li><span class="state mark-bad">Don't</span><span>Rely on green and red to say which is which.</span></li>
      </ul>
    </article>

    <article class="card" id="g-filters">
      <h3>Filters</h3>
      <p class="src">.filters[data-target] · button.chip[data-filter] · data-tags</p>
      <div class="filters" data-target="g-rows" role="group" aria-labelledby="g-flt-lbl" hidden>
        <span class="flbl" id="g-flt-lbl">Show</span>
        <button class="chip" type="button" data-filter="all" aria-pressed="true">All</button>
        <button class="chip" type="button" data-filter="new" aria-pressed="false">New</button>
        <button class="chip" type="button" data-filter="kept" aria-pressed="false">Kept</button>
      </div>
      <div class="tbl-wrap">
        <table class="is-stackable" id="g-rows">
          <caption>Two rows a filter narrows</caption>
          <thead><tr><th scope="col">Part</th><th scope="col">State</th></tr></thead>
          <tbody>
            <tr data-tags="new"><td>Diagram</td><td>New</td></tr>
            <tr data-tags="kept"><td>Table</td><td>Kept</td></tr>
          </tbody>
        </table>
      </div>
      <div class="kv"><span class="ilbl">Keys</span><span>Tab reaches each chip, Enter or Space presses it, and the count is announced. With the script off the row is hidden and every row shows.</span></div>
      <div class="code"><div class="code-head"><span>markup</span><button class="copy" type="button" hidden>Copy</button></div><pre><code>&lt;div class="filters" data-target="rows" role="group"
  aria-labelledby="lbl" hidden&gt;
  &lt;span class="flbl" id="lbl"&gt;Show&lt;/span&gt;
  &lt;button class="chip" type="button" data-filter="all"
    aria-pressed="true"&gt;All&lt;/button&gt;
&lt;/div&gt;</code></pre></div>
      <ul class="checklist">
        <li><span class="state mark-ok">Do</span><span>Tag the rows the filter narrows.</span></li>
        <li><span class="state mark-bad">Don't</span><span>Filter a list the reader needs in full.</span></li>
      </ul>
    </article>

    <article class="card" id="g-callout">
      <h3>Highlight</h3>
      <p class="src">.callout · .is-bad · .is-warn</p>
      <div class="callout"><h3>The one thing to take away</h3><p>This is the only block on the page with an accent bar, which is exactly why it works.</p></div>
      <div class="callout is-warn"><h3>And when it is a warning</h3><p>The bar turns amber; the words still say it.</p></div>
      <div class="code"><div class="code-head"><span>markup</span><button class="copy" type="button" hidden>Copy</button></div><pre><code>&lt;div class="callout"&gt;
  &lt;h3&gt;The takeaway&lt;/h3&gt;&lt;p&gt;One paragraph.&lt;/p&gt;
&lt;/div&gt;</code></pre></div>
      <ul class="checklist">
        <li><span class="state mark-ok">Do</span><span>Keep one or two on a page.</span></li>
        <li><span class="state mark-bad">Don't</span><span>Give any other block a coloured left border.</span></li>
      </ul>
    </article>

    <article class="card" id="g-cat">
      <h3>Category chip</h3>
      <p class="src">.cat · .c-green · .c-purple · .c-amber · .c-red · .c-blue</p>
      <p><span class="cat c-green">keys tested</span> <span class="cat c-purple">carriers</span> <span class="cat c-amber">file:// untested</span> <span class="cat c-red">research item 3</span> <span class="cat c-blue">website</span></p>
      <p>Five hues group things. The chip's word names the category, so the colour never carries the meaning alone.</p>
      <div class="code"><div class="code-head"><span>markup</span><button class="copy" type="button" hidden>Copy</button></div><pre><code>&lt;span class="cat c-green"&gt;keys tested&lt;/span&gt;</code></pre></div>
      <ul class="checklist">
        <li><span class="state mark-ok">Do</span><span>Let the word name the category.</span></li>
        <li><span class="state mark-bad">Don't</span><span>Use a chip as a verdict; that is a pill or a verdict card.</span></li>
      </ul>
    </article>

    <article class="card" id="g-verdict">
      <h3>Verdict card and terminal card</h3>
      <p class="src">.card.is-good · .is-bad · pre.term</p>
      <div class="grid g2">
        <div class="card is-good"><h4 class="card-h"><span class="cat c-green">chosen</span> One source</h4><p>Generated into every page, checked by parity.</p></div>
        <div class="card is-bad"><h4 class="card-h"><span class="cat c-red">rejected</span> Eight copies</h4><p>Two of them escape every gate.</p></div>
      </div>
      <div class="card"><pre class="term"><span class="b">$ bun test</span>
<span class="ok">✔ parity</span> 8 templates
<span class="bad">✘ contrast</span> 1 pair below 4.5:1</pre></div>
      <div class="code"><div class="code-head"><span>markup</span><button class="copy" type="button" hidden>Copy</button></div><pre><code>&lt;div class="card is-good"&gt;&lt;h4 class="card-h"&gt;
  &lt;span class="cat c-green"&gt;chosen&lt;/span&gt; Title&lt;/h4&gt;&lt;/div&gt;
&lt;pre class="term"&gt;&lt;span class="ok"&gt;✔ pass&lt;/span&gt;&lt;/pre&gt;</code></pre></div>
      <ul class="checklist">
        <li><span class="state mark-ok">Do</span><span>State the verdict as a word in the chip.</span></li>
        <li><span class="state mark-bad">Don't</span><span>Let the border be the only signal.</span></li>
      </ul>
    </article>

    <article class="card" id="g-proscons">
      <h3>Gains and costs</h3>
      <p class="src">ul.proscons · li.pro · li.con</p>
      <ul class="proscons">
        <li class="pro"><span class="pm" aria-hidden="true">+</span><span><b>Gain:</b> one pipeline, no new tool.</span></li>
        <li class="con"><span class="pm" aria-hidden="true">−</span><span><b>Cost:</b> every page carries the full CSS.</span></li>
      </ul>
      <div class="code"><div class="code-head"><span>markup</span><button class="copy" type="button" hidden>Copy</button></div><pre><code>&lt;ul class="proscons"&gt;
  &lt;li class="pro"&gt;&lt;span class="pm" aria-hidden="true"&gt;+&lt;/span&gt;
  &lt;span&gt;&lt;b&gt;Gain:&lt;/b&gt; …&lt;/span&gt;&lt;/li&gt;
&lt;/ul&gt;</code></pre></div>
      <ul class="checklist">
        <li><span class="state mark-ok">Do</span><span>Repeat the sign as a hidden word for a screen reader.</span></li>
        <li><span class="state mark-bad">Don't</span><span>Leave the sign as the only meaning.</span></li>
      </ul>
    </article>

    <article class="card" id="g-kbd">
      <h3>Keyboard key and status message</h3>
      <p class="src">kbd · #live.sr[role=status]</p>
      <p>Press <kbd>Tab</kbd> to move, <kbd>Enter</kbd> to act. Copy, filter and expand results are announced in the status region at the top of the page.</p>
      <div class="code"><div class="code-head"><span>markup</span><button class="copy" type="button" hidden>Copy</button></div><pre><code>&lt;div id="live" class="sr" role="status" aria-live="polite"&gt;&lt;/div&gt;
Press &lt;kbd&gt;Tab&lt;/kbd&gt; to move.</code></pre></div>
      <ul class="checklist">
        <li><span class="state mark-ok">Do</span><span>Keep one status region per page and write to it with <code>textContent</code>.</span></li>
        <li><span class="state mark-bad">Don't</span><span>Show a result only as a colour or a button label.</span></li>
      </ul>
    </article>

  </div>
</section>

<section id="g-behaviour" aria-labelledby="g-h-behaviour">
  <h2 id="g-h-behaviour"><span class="num">05</span>Behaviour under each condition</h2>
  <p>The same page under the conditions a reader actually meets: the keyboard only, the script off, paper, Windows high contrast and a phone.</p>
  <div class="tbl-wrap">
    <table class="is-stackable">
      <caption>How each interactive part behaves, and what proves it</caption>
      <thead><tr><th scope="col">Part</th><th scope="col">Keyboard</th><th scope="col">Script off</th><th scope="col">Print</th><th scope="col">Forced colours</th></tr></thead>
      <tbody>
        <tr><td>Tabs</td><td><span class="mark-ok">✔ arrows, Home, End</span></td><td><span class="mark-ok">✔ panels stack</span></td><td><span class="mark-ok">✔ every panel</span></td><td><span class="mark-ok">✔ selected tab underlined</span></td></tr>
        <tr><td>Copy</td><td><span class="mark-ok">✔ native button</span></td><td><span class="mark-ok">✔ hidden</span></td><td><span class="mark-ok">✔ hidden</span></td><td><span class="mark-ok">✔ system button colour</span></td></tr>
        <tr><td>Filters</td><td><span class="mark-ok">✔ Tab, Enter, Space</span></td><td><span class="mark-ok">✔ hidden, every row</span></td><td><span class="mark-ok">✔ hidden</span></td><td><span class="mark-ok">✔ Highlight on the pressed chip</span></td></tr>
        <tr><td>Items</td><td><span class="mark-ok">✔ native details</span></td><td><span class="mark-ok">✔ open one by one</span></td><td><span class="mark-ok">✔ all open</span></td><td><span class="mark-ok">✔ borders kept</span></td></tr>
        <tr><td>Diagram</td><td><span class="mark-ok">✔ text version opens</span></td><td><span class="mark-ok">✔ full picture</span></td><td><span class="mark-ok">✔ full picture</span></td><td><span class="mark-warn">⚠ strokes map to CanvasText, unproven off Chromium</span></td></tr>
      </tbody>
    </table>
  </div>
  <div class="callout"><h3>What each gate proves</h3><p><code>bun scripts/brand.ts contrast</code> measures every declared pair; the static gate inside <code>bun test</code> reads the markup; and <code>bun run a11y</code> opens every page in system Chrome to measure what only a browser computes.</p></div>
</section>

</div>
</main>

<footer>
  <span class="x">{</span>ai<span class="x">}</span> Engineering · Gallery · brand design system<br>
  written by an AI agent · the reference every artifact copies<br>
  <a href="#main">↑ top</a>
</footer>
<!-- brand:js:begin --><script>
/* scroll-spy: mark the nav link for the section in view.
   Lead matches scroll-margin-top (88px): the highlight flips when the
   heading clears the sticky nav. */
(function () {
  const lead = 88;
  const links = document.querySelectorAll('nav a[href^="#"]');
  function updateNav() {
    let current = "";
    for (const link of links) {
      const href = link.getAttribute("href");
      if (!href) continue;
      const section = document.getElementById(href.slice(1));
      if (!section) continue;
      if (section.getBoundingClientRect().top <= lead) current = href.slice(1);
    }
    for (const link of links) {
      const on = link.getAttribute("href") === "#" + current;
      link.classList.toggle("active", on);
      if (on) link.setAttribute("aria-current", "location");
      else link.removeAttribute("aria-current");
    }
  }
  window.addEventListener("scroll", updateNav, { passive: true });
  updateNav();
})();

/* components: progressive enhancement for tabs, copy, filters and expand-all.
   Every part of the page reads without this script; it only adds controls.
   It writes with textContent and reads nothing from the network. */
(function () {
  const live = document.getElementById("live");
  function announce(message) {
    if (!live) return;
    live.textContent = "";
    setTimeout(function () { live.textContent = message; }, 60);
  }

  /* Tabs, per the WAI-ARIA Authoring Practices tabs pattern (automatic activation).
     The tab list is built from each panel's data-tab label, so the markup stays one
     list of headed panels that also reads well with the script off. */
  document.querySelectorAll(".tabs").forEach(function (tabs, setIndex) {
    const panels = Array.from(tabs.querySelectorAll(":scope > .tabpanel"));
    if (panels.length < 2) return;
    const list = document.createElement("div");
    list.className = "tablist";
    list.setAttribute("role", "tablist");
    const buttons = panels.map(function (panel, i) {
      const button = document.createElement("button");
      button.type = "button";
      button.id = "tab-" + setIndex + "-" + i;
      button.setAttribute("role", "tab");
      button.setAttribute("aria-controls", panel.id);
      /* Label parts: an optional key ("A"), the name, an optional state chip ("chosen"). */
      if (panel.dataset.key) {
        const key = document.createElement("span");
        key.className = "tab-key";
        key.textContent = panel.dataset.key;
        button.appendChild(key);
      }
      const name = document.createElement("span");
      name.textContent = panel.dataset.tab || "Tab " + (i + 1);
      button.appendChild(name);
      if (panel.dataset.badge) {
        const badge = document.createElement("span");
        badge.className = "cat c-green";
        badge.textContent = panel.dataset.badge;
        button.appendChild(badge);
      }
      panel.setAttribute("role", "tabpanel");
      panel.setAttribute("aria-labelledby", button.id);
      panel.tabIndex = 0;
      list.appendChild(button);
      return button;
    });
    const indicator = document.createElement("span");
    indicator.className = "tab-ind";
    indicator.setAttribute("aria-hidden", "true");
    list.appendChild(indicator);
    let current = 0;
    /* The bar moves with transform only; a keyboard move is instant, because a
       motion repeated on every arrow press reads as lag. */
    function placeIndicator(isInstant) {
      const button = buttons[current];
      indicator.classList.toggle("is-instant", isInstant);
      indicator.style.transform = "translateX(" + button.offsetLeft + "px) scaleX(" + button.offsetWidth + ")";
    }
    function select(index, moveFocus) {
      current = index;
      buttons.forEach(function (button, i) {
        const isSelected = i === index;
        button.setAttribute("aria-selected", String(isSelected));
        button.tabIndex = isSelected ? 0 : -1;
        panels[i].hidden = !isSelected;
      });
      placeIndicator(moveFocus);
      /* Keep the chosen tab inside a row that scrolls, without moving the page. */
      const chosen = buttons[index];
      if (chosen.offsetLeft < list.scrollLeft || chosen.offsetLeft + chosen.offsetWidth > list.scrollLeft + list.clientWidth) {
        list.scrollLeft = chosen.offsetLeft - 16;
      }
      if (moveFocus) chosen.focus({ preventScroll: true });
      markOverflow();
    }
    /* A row that runs past the screen fades at the edge that hides more tabs. */
    function markOverflow() {
      list.classList.toggle("has-more", list.scrollLeft + list.clientWidth < list.scrollWidth - 1);
    }
    list.addEventListener("scroll", markOverflow, { passive: true });
    buttons.forEach(function (button, i) {
      button.addEventListener("click", function () { select(i, false); });
      button.addEventListener("keydown", function (event) {
        const last = buttons.length - 1;
        const next = { ArrowRight: i === last ? 0 : i + 1, ArrowLeft: i === 0 ? last : i - 1, Home: 0, End: last }[event.key];
        if (next === undefined) return;
        event.preventDefault();
        select(next, true);
      });
    });
    tabs.insertBefore(list, panels[0]);
    tabs.classList.add("is-enhanced");
    select(0, false);
    placeIndicator(true);
    if (window.ResizeObserver) new ResizeObserver(function () { placeIndicator(true); markOverflow(); }).observe(list);
  });

  /* Tables: on a narrow screen each row stacks as a block and each cell shows its
     column name. Explicit roles keep the table semantics that display:block drops. */
  document.querySelectorAll(".tbl-wrap table").forEach(function (table) {
    const heads = Array.from(table.querySelectorAll("thead th")).map(function (th) { return th.textContent.trim(); });
    table.setAttribute("role", "table");
    table.querySelectorAll("thead, tbody").forEach(function (group) { group.setAttribute("role", "rowgroup"); });
    table.querySelectorAll("tr").forEach(function (row) {
      row.setAttribute("role", "row");
      Array.from(row.children).forEach(function (cell, i) {
        cell.setAttribute("role", cell.tagName === "TH" ? "columnheader" : "cell");
        if (cell.tagName === "TD" && heads[i]) cell.dataset.label = heads[i];
      });
    });
    table.classList.add("is-stackable");
  });

  /* A region that scrolls sideways must take keyboard focus, or its hidden part is out
     of reach (WCAG 2.1.1). Only regions that overflow at the current width get a stop. */
  const scrollers = Array.from(document.querySelectorAll("pre, .canvas, .tbl-wrap"));
  function markScrollers() {
    scrollers.forEach(function (region) {
      if (region.scrollWidth > region.clientWidth + 1) region.tabIndex = 0;
      else region.removeAttribute("tabindex");
    });
  }
  markScrollers();
  window.addEventListener("resize", markScrollers, { passive: true });

  /* Copy: the button copies its block's code and says so in the status region. */
  document.querySelectorAll(".code .copy").forEach(function (button) {
    button.hidden = false;
    button.addEventListener("click", function () {
      const code = button.closest(".code").querySelector("pre").innerText;
      const done = function () { button.textContent = "Copied"; announce("Code copied"); setTimeout(function () { button.textContent = "Copy"; }, 2000); };
      const failed = function () { announce("Copy is blocked here: select the code and copy it by hand"); };
      if (navigator.clipboard) navigator.clipboard.writeText(code).then(done, failed);
      else failed();
    });
  });

  /* Filters: one pressed chip at a time narrows the rows tagged with its value. */
  document.querySelectorAll(".filters").forEach(function (bar) {
    const target = document.getElementById(bar.dataset.target);
    if (!target) return;
    const rows = Array.from(target.querySelectorAll("[data-tags]"));
    const chips = Array.from(bar.querySelectorAll(".chip"));
    bar.hidden = false;
    chips.forEach(function (chip) {
      chip.addEventListener("click", function () {
        const value = chip.dataset.filter;
        let shown = 0;
        chips.forEach(function (other) { other.setAttribute("aria-pressed", String(other === chip)); });
        rows.forEach(function (row) {
          const isMatch = value === "all" || row.dataset.tags.split(" ").includes(value);
          row.hidden = !isMatch;
          if (isMatch) shown += 1;
        });
        announce(shown + " of " + rows.length + " shown");
      });
    });
  });

  /* Expand all: opens or closes every item in the named list. */
  document.querySelectorAll("[data-expand]").forEach(function (button) {
    const list = document.getElementById(button.dataset.expand);
    if (!list) return;
    button.hidden = false;
    button.addEventListener("click", function () {
      const shouldOpen = button.dataset.state !== "open";
      list.querySelectorAll("details").forEach(function (item) { item.open = shouldOpen; });
      button.dataset.state = shouldOpen ? "open" : "closed";
      button.textContent = shouldOpen ? "Collapse all" : "Expand all";
    });
  });

  /* Print: a closed item prints as its title only, so printing opens them all. */
  window.addEventListener("beforeprint", function () {
    document.querySelectorAll("details").forEach(function (item) { item.open = true; });
  });
})();
</script><!-- brand:js:end -->
</body>
</html>
