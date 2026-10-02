<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 32 32%22%3E%3Crect width=%2232%22 height=%2232%22 rx=%227%22 fill=%22%23001E2B%22/%3E%3Crect x=%220.5%22 y=%220.5%22 width=%2231%22 height=%2231%22 rx=%226.5%22 fill=%22none%22 stroke=%22%2300ED64%22 stroke-opacity=%220.35%22/%3E%3Ctext x=%2216%22 y=%2217%22 text-anchor=%22middle%22 dominant-baseline=%22central%22 font-family=%22ui-monospace, Menlo, Consolas, 'DejaVu Sans Mono', monospace%22 font-size=%2214%22 font-weight=%22700%22 letter-spacing=%22-1%22%3E%3Ctspan fill=%22%2300ED64%22%3E%7B%3C/tspan%3E%3Ctspan fill=%22%23E8EEF7%22%3Eai%3C/tspan%3E%3Ctspan fill=%22%2300ED64%22%3E%7D%3C/tspan%3E%3C/text%3E%3C/svg%3E">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Triage · {{repo}} · {{date}}</title>
<style>
:root{
  --bg:#001E2B; --surface:#112733; --surface-2:#1C2D38;
  --line:rgba(61,79,88,.3); --line-strong:rgba(61,79,88,.6);
  --accent:#00ED64; --accent-dim:#71F6BA;
  --text:#FFFFFF; --dim:#C1C7C6; --comment:#889397;
  --ok:#00ED64; --bad:#FF6960; --warn:#FFC010; --purple:#B45AF2; --orange:#FFC010;
  --mono:'SF Mono','JetBrains Mono','Fira Code',ui-monospace,monospace;
  --sans:-apple-system,BlinkMacSystemFont,'Inter',system-ui,sans-serif;
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
p{color:var(--dim);margin:0 auto var(--s3);text-align:justify;hyphens:auto}
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
pre{background:var(--surface-2);border:1px solid var(--line);border-radius:var(--radius-lg);padding:var(--s4) var(--s5);overflow-x:auto;font-family:var(--mono);font-size:var(--fs-mono);line-height:var(--lh-mono);color:var(--dim);margin:var(--s4) 0;-webkit-overflow-scrolling:touch}
pre code{background:none;border:none;padding:0;color:inherit;overflow-wrap:normal}
pre,.flow,.tbl-wrap{scrollbar-color:var(--line-strong) transparent;scrollbar-width:thin}
pre::-webkit-scrollbar,.flow::-webkit-scrollbar,.tbl-wrap::-webkit-scrollbar{height:8px;width:8px}
pre::-webkit-scrollbar-thumb,.flow::-webkit-scrollbar-thumb,.tbl-wrap::-webkit-scrollbar-thumb{background:var(--line-strong);border-radius:99px}
pre::-webkit-scrollbar-track,.flow::-webkit-scrollbar-track,.tbl-wrap::-webkit-scrollbar-track{background:transparent}
pre .c{color:var(--comment)} pre .k{color:var(--accent)} pre .s{color:var(--ok)}
pre .t{color:var(--purple)} pre .n{color:var(--orange)} pre .b{color:var(--text);font-weight:600}
.flow{white-space:pre;font-size:12px;line-height:1.75;overflow-x:auto;-webkit-overflow-scrolling:touch}
.bracket{position:relative;border:1px solid var(--line);background:var(--surface-2);border-radius:var(--radius-lg);padding:var(--s5) var(--s5) var(--s4);margin:var(--s5) 0}
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
@media print{nav,.skip{display:none}body{background:#fff;color:#111}section{page-break-inside:avoid}}
</style>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>

<header class="hero">
  <span class="corner tl"></span><span class="corner tr"></span>
  <span class="corner bl"></span><span class="corner br"></span>
  <div class="mark" aria-hidden="true"><span class="x">{</span>ai<span class="x">}</span></div>
  <div class="stamp">Triage · {{repo}} · {{date}}</div>
  <h1>{{title}}</h1>
  <p class="sub">{{subtitle}}</p>
  <div class="meta">{{meta}}</div>
</header>

<nav>
  <!-- One link per section, same order as the sections below, numbered with
       .num and no hole after a deletion:
       <a href="#s01"><b>01</b>Snapshot</a> ... -->
</nav>

<main id="main">
<div class="container">

<!-- Triage contract (ai-github-triage): the page is a decision surface, not a
     transcript. Every claim is a permalink at a commit SHA; no permalink means
     no claim. The reader must be able to pick the first item to work on from
     section 02 alone, and act on it with the commands in section 08.

     THE ITEM ROW. Every item on the page - a ranked entry, a bug, a closable
     issue, a feature, a pull request - is one expandable row with the same
     shape, so a reader learns it once and the sections differ only in which
     chips they carry. The row is a native <details>: no script, keyboard and
     find-in-page work, and the closed state is the scan.

       <details class="item" id="i{{number}}">
         <summary>
           <span class="band band-p0">P0</span>          the band chip
           <a class="iid" href="{{url}}">#{{number}}</a> the id IS the link out
           <span class="ititle">{{title}}</span>        bold subject, code inline
           <span class="imeta">{{effort}}</span>        the right rail
         </summary>
         <div class="ibody">
           <div class="kv"><span class="ilbl">Context</span><span>{{context}}</span></div>
           <div class="kv"><span class="ilbl">Why now</span><span>{{why_now}}</span></div>
           <div class="kv"><span class="ilbl">Signals</span><span class="sig">{{signals}}</span></div>
           <div class="kv"><span class="ilbl">Evidence</span><span class="xref">{{evidence}}</span></div>
         </div>
       </details>

     Context is plain language for an engineer who has read nothing: what the
     item is about, why it exists, what happens if nobody touches it. Not a
     restatement of the title. A row whose context is missing says so.

     BAND, and the chip that carries it: P0 .band-p0 (build red, data loss,
     security, or already fixed) - P1 .band-p1 (confirmed bug with a
     reproduction, HIGH or CRITICAL) - P2 .band-p2 (confirmed bug without a
     reproduction, or MEDIUM) - P3..P5 .band-p3/.band-p4/.band-p5 (neutral).
     The order of the rows IS the rank; there is no '01' column to maintain.

     DUPLICATES ACROSS SECTIONS ARE THE POINT, not a bug: an issue that is
     already fixed appears in Close or park AND at the top of the queue. Every
     row carries id="i<number>", so a row in one section links to the same item
     in another, and its Evidence line ends with the 'also in' cross-refs. The
     reader must be able to tell, without scrolling twice, that it is one item.

     Sections, in this order:
       01 Snapshot          the counts, as .stats, then the .legend (band and
                            severity, so a chip is never a colour with no key)
       02 Start here        the ranked queue: .items > .item, best first
       03 Fix now           confirmed bugs, ordered by severity
       04 Answer            questions with a drafted answer, one .item each
       05 Close or park     stale, duplicate, out of scope, already fixed
       06 Feature requests  assessed: feasibility + existing implementation
       07 Pull requests     CI, review state, merge readiness
       08 First three moves a numbered ol, then one .bracket per command block
       09 Method            repo, commit, scope, tools used, tools absent, and
                            the coverage: how many items were read deeply
                            against how many were only catalogued

     Delete a section with nothing in it and renumber the survivors 01..N, so the
     nav has no hole: an empty heading reads as "we found nothing", which is a
     different claim from "we did not look".

     Components: .stats > .stat > .v + .l · .items > .item (+ .band, .iid,
     .ititle, .imeta, .ibody, .kv, .ilbl, .sig, .xref) · .legend · .tbl-wrap >
     table · .card > h4 + p · .note (+ .ok/.warn/.danger) · .grid.g2/.g3/.g4 ·
     .bracket > .tag + pre · pre with .c/.k/.s/.t/.n/.b · .pill (+ .p-ok/.p-bad/
     .p-warn/.p-fix/.p-dim).
     A note's label is an <h3> directly under the section's <h2> (and a card's is
     an <h3> or <h4> after one): an h4 straight under an h2 skips a level, and the
     layout rule is that no heading level is ever skipped.
     Copy the CSS block, the {ai} favicon and the scroll-spy script verbatim, do
     not retype them: the shell is what makes this page one of the family, and a
     hand-rolled scroll-spy is how the nav stops marking the section in view. -->

<section id="s01">
  <h2><span class="num">01 · Snapshot</span>The backlog in numbers</h2>
  <div class="stats">
    <div class="stat"><div class="v">{{open_items}}</div><div class="l">open items</div></div>
    <div class="stat"><div class="v">{{issues}}</div><div class="l">issues</div></div>
    <div class="stat"><div class="v">{{pull_requests}}</div><div class="l">pull requests</div></div>
    <div class="stat"><div class="v">{{ranked}}</div><div class="l">verified, ranked</div></div>
  </div>
  <p>{{snapshot_prose}}</p>
  <div class="legend">
    <div><span class="lname"><span class="band band-p0">P0</span></span><p>{{legend_p0}}</p></div>
    <div><span class="lname"><span class="band band-p1">P1</span></span><p>{{legend_p1}}</p></div>
    <div><span class="lname"><span class="band band-p2">P2</span></span><p>{{legend_p2}}</p></div>
    <div><span class="lname"><span class="band band-p5">P5</span></span><p>{{legend_p5}}</p></div>
  </div>
</section>

<section id="s02">
  <h2><span class="num">02 · Start here</span>What to work on first</h2>
  <p>{{ranking_prose}}</p>
  <div class="items">
    <!-- one .item per ranked entry, best first, band chip + linked id:
    <details class="item" id="i{{number}}">
      <summary>
        <span class="band band-{{band}}">{{band_label}}</span>
        <a class="iid" href="{{url}}">#{{number}}</a>
        <span class="ititle">{{title}}</span>
        <span class="imeta">{{effort}}</span>
      </summary>
      <div class="ibody">
        <div class="kv"><span class="ilbl">Context</span><span>{{context}}</span></div>
        <div class="kv"><span class="ilbl">Why now</span><span>{{why_now}}</span></div>
        <div class="kv"><span class="ilbl">Signals</span><span class="sig">{{signals}}</span></div>
        <div class="kv"><span class="ilbl">Evidence</span><span class="xref">{{evidence}}</span></div>
      </div>
    </details>
    -->
  </div>
</section>

<section id="s03">
  <h2><span class="num">03 · Fix now</span>Confirmed bugs</h2>
  <div class="items">
    <!-- verdict + severity chips, then the same .ibody:
    <details class="item" id="i{{number}}">
      <summary>
        <span class="pill p-ok">{{verdict}}</span>
        <span class="pill {{severity_class}}">{{severity}}</span>
        <a class="iid" href="{{url}}">#{{number}}</a>
        <span class="ititle">{{title}}</span>
      </summary>
      <div class="ibody">
        <div class="kv"><span class="ilbl">Context</span><span>{{context}}</span></div>
        <div class="kv"><span class="ilbl">Root cause</span><span>{{root_cause}}</span></div>
        <div class="kv"><span class="ilbl">Evidence</span><span class="xref">{{evidence}}</span></div>
      </div>
    </details>
    -->
  </div>
</section>

<section id="s04">
  <h2><span class="num">04 · Answer</span>Questions with an answer ready</h2>
  <div class="items">
    <!-- the draft answer goes in the body, verbatim, so it can be sent as-is.
    <details class="item" id="i{{number}}">
      <summary>
        <span class="pill p-ok">{{verdict}}</span>
        <a class="iid" href="{{url}}">#{{number}}</a>
        <span class="ititle">{{question}}</span>
      </summary>
      <div class="ibody">
        <div class="kv"><span class="ilbl">Context</span><span>{{context}}</span></div>
        <div class="kv"><span class="ilbl">Draft answer</span><span>{{draft_answer}}</span></div>
        <div class="kv"><span class="ilbl">Confidence</span><span>{{confidence}}</span></div>
      </div>
    </details>
    -->
  </div>
</section>

<section id="s05">
  <h2><span class="num">05 · Close or park</span>Nothing to build</h2>
  <div class="items">
    <!-- reason chip + the same .ibody; the row says who closes it and why:
    <details class="item" id="i{{number}}">
      <summary>
        <span class="pill p-dim">{{verdict}}</span>
        <a class="iid" href="{{url}}">#{{number}}</a>
        <span class="ititle">{{title}}</span>
      </summary>
      <div class="ibody">
        <div class="kv"><span class="ilbl">Context</span><span>{{context}}</span></div>
        <div class="kv"><span class="ilbl">Reason</span><span>{{reason}}</span></div>
        <div class="kv"><span class="ilbl">Evidence</span><span class="xref">{{evidence}}</span></div>
      </div>
    </details>
    -->
  </div>
</section>

<section id="s06">
  <h2><span class="num">06 · Feature requests</span>Assessed, not promised</h2>
  <div class="items">
    <!-- feasibility chip + the same .ibody:
    <details class="item" id="i{{number}}">
      <summary>
        <span class="pill p-dim">{{feasibility}}</span>
        <a class="iid" href="{{url}}">#{{number}}</a>
        <span class="ititle">{{title}}</span>
      </summary>
      <div class="ibody">
        <div class="kv"><span class="ilbl">Context</span><span>{{context}}</span></div>
        <div class="kv"><span class="ilbl">Exists today</span><span>{{exists_today}}</span></div>
        <div class="kv"><span class="ilbl">Evidence</span><span class="xref">{{evidence}}</span></div>
      </div>
    </details>
    -->
  </div>
</section>

<section id="s07">
  <h2><span class="num">07 · Pull requests</span>Merge readiness</h2>
  <div class="items">
    <!-- action chip (MERGE / WAIT / REBASE / BLOCKED) + the same .ibody:
    <details class="item" id="i{{number}}">
      <summary>
        <span class="pill {{action_class}}">{{action}}</span>
        <a class="iid" href="{{url}}">#{{number}}</a>
        <span class="ititle">{{title}}</span>
        <span class="imeta">{{branch}}</span>
      </summary>
      <div class="ibody">
        <div class="kv"><span class="ilbl">Context</span><span>{{context}}</span></div>
        <div class="kv"><span class="ilbl">Checks</span><span>{{checks}}</span></div>
        <div class="kv"><span class="ilbl">Closes</span><span class="xref">{{closes}}</span></div>
      </div>
    </details>
    -->
  </div>
</section>

<section id="s08">
  <h2><span class="num">08 · First three moves</span>The next ninety minutes</h2>
  <ol>
    <li><strong>#{{number}} {{title}}</strong> · {{move}} <a href="{{permalink}}">permalink</a></li>
  </ol>
  <div class="bracket"><span class="tag">commands</span><pre>gh issue view {{number}} --repo {{repo}} --json title,body,comments</pre></div>
</section>

<section id="s09">
  <h2><span class="num">09 · Method</span>What was read</h2>
  <p>{{method}}</p>
  <p>{{coverage}}</p>
</section>

</div>
</main>

<footer>
  <span class="x">{</span>ai<span class="x">}</span> Engineering · Triage · {{repo}} · {{date}}<br>
  {{footer}}
  <a href="#main">↑ top</a>
</footer>
<script>
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
</script>
</body>
</html>
