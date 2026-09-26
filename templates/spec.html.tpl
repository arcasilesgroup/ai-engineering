<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 32 32%22%3E%3Crect width=%2232%22 height=%2232%22 rx=%227%22 fill=%22%23001E2B%22/%3E%3Crect x=%220.5%22 y=%220.5%22 width=%2231%22 height=%2231%22 rx=%226.5%22 fill=%22none%22 stroke=%22%2300ED64%22 stroke-opacity=%220.35%22/%3E%3Ctext x=%2216%22 y=%2217%22 text-anchor=%22middle%22 dominant-baseline=%22central%22 font-family=%22ui-monospace, Menlo, Consolas, 'DejaVu Sans Mono', monospace%22 font-size=%2214%22 font-weight=%22700%22 letter-spacing=%22-1%22%3E%3Ctspan fill=%22%2300ED64%22%3E%7B%3C/tspan%3E%3Ctspan fill=%22%23E8EEF7%22%3Eai%3C/tspan%3E%3Ctspan fill=%22%2300ED64%22%3E%7D%3C/tspan%3E%3C/text%3E%3C/svg%3E">
<title>spec.html — WHAT · {{milestone}}</title>
<style>
  :root { --bg:#001E2B; --surface:#112733; --surface-2:#1C2D38; --line:rgba(61,79,88,.3); --line-strong:rgba(61,79,88,.6); --accent:#00ED64; --accent-dim:#71F6BA; --text:#FFFFFF; --dim:#C1C7C6; --comment:#889397; --warn:#FFC010; --bad:#FF6960; --ok:#00ED64; --purple:#B45AF2; --orange:#FFC010; --mono:'SF Mono','JetBrains Mono','Fira Code',ui-monospace,monospace; --sans:-apple-system,BlinkMacSystemFont,'Inter',system-ui,sans-serif;
    --fs-h2:26px; --lh-h2:1.16; --fs-h3:17px; --lh-h3:1.32; --fs-h4:14px; --lh-h4:1.35; --fs-body:15px; --lh-body:1.62; --fs-small:13.5px; --lh-small:1.55; --fs-mono:12.5px; --lh-mono:1.7; --fs-label:10.5px;
    --s1:4px; --s2:8px; --s3:12px; --s4:16px; --s5:24px; --s6:32px; --s7:48px; --radius:12px; --radius-sm:8px; --container:1040px; --measure:68ch; }
  * { margin:0; padding:0; box-sizing:border-box; }
  html { scroll-behavior:smooth; }
  body { background:var(--bg); color:var(--text); font-family:var(--sans); font-size:var(--fs-body); line-height:var(--lh-body); -webkit-font-smoothing:antialiased; max-width:var(--container); margin:0 auto; padding:48px var(--s5); }
  h1 { font-size:34px; letter-spacing:-.02em; font-weight:740; } h1 .x { color:var(--accent); }
  h2 { color:var(--accent); font-family:var(--mono); font-size:var(--fs-label); text-transform:uppercase; letter-spacing:.22em; margin:var(--s6) 0 var(--s4); }
  h2 .num { color:var(--dim); margin-right:10px; }
  h3 { font-size:var(--fs-h3); font-weight:660; }
  p { color:var(--dim); margin:0 auto var(--s3); text-align:justify; hyphens:auto; }
  .card { background:var(--surface); border:1px solid var(--line); border-radius:var(--radius); padding:var(--s5); margin:10px 0; }
  .meta { display:flex; gap:24px; flex-wrap:wrap; color:var(--dim); font-size:13px; margin:8px 0 0; }
  .meta b { color:var(--text); font-weight:500; }
  code, pre { font-family:var(--mono); font-size:var(--fs-mono); color:var(--accent-dim); }
  code { background:var(--surface-2); border:1px solid var(--line); border-radius:5px; padding:1px 6px; }
  pre { background:var(--surface-2); border:1px solid var(--line); border-radius:var(--radius); padding:var(--s4) var(--s5); overflow-x:auto; color:var(--dim); line-height:var(--lh-mono); }
  .gate .id { font-family:var(--mono); color:var(--accent); font-weight:600; }
  .gate .status { font-family:var(--mono); font-size:11px; }
  .gate .check { font-family:var(--mono); font-size:12px; color:var(--dim); display:block; margin-top:6px; }
  a { color:var(--accent); }
  .context { font-size:var(--fs-small); color:var(--dim); line-height:var(--lh-small); }
</style>
</head>
<body>
<h1><span class="x">{ai}</span> spec · {{milestone}}</h1>
<p style="color:var(--dim)">WHAT and WHY — requirements and acceptance gates. Its sha256 is pinned in <code>ai-eng.lock</code> at approval (STOP 1). <code>ai-eng spec close</code> checks the evidence.</p>

<h2><span class="num">00</span>Context chain</h2>
<div class="card context">
  <p>The research this milestone consumes, and the plan that executes it. Keep these links live — the LLM working this milestone reads all three.</p>
  <div class="meta">
    <span>Research: <b>{{research}}</b></span>
    <span>Spec: <b>spec.html (this file)</b></span>
    <span>Plan: <b><a href="plan.html">plan.html</a></b></span>
  </div>
</div>

<h2><span class="num">01</span>Work points</h2>
<p style="color:var(--dim)">Numbered sections: what must be done. Each point names the gates that prove it done.</p>

<div class="card">
  <h3 style="font-size:14px;color:var(--accent);font-family:var(--mono)">01 · <work point title></h3>
  <p class="context">What and why, in sentences a reviewer can check. No schedule here — order lives in plan.html.</p>
  <p class="context" style="margin-top:8px">Proves: G1, G2</p>
</div>

<h2><span class="num">02</span>Acceptance gates</h2>
<p style="color:var(--dim)">One box per outcome. Max 30 per milestone. ABANDON: G&lt;n&gt; &lt;reason&gt; is the honest exit. Evidence is a sentence of what the check found. <code>ai-eng spec close</code> refuses a gate whose evidence is still pending.</p>
<pre id="gates">
# Gates: {{milestone}}

- [ ] G1: <observable outcome>
  CHECK: <a command that PRINTS what it found, e.g. node scripts/report.mjs>
  EXPECT: <optional: the text, or /regex/, that must appear in that output>
  EVIDENCE: pending

- [ ] G2: <an outcome only existing artifacts can show>
  CHECK: sh -c 'test -f README.md && echo "README.md $(wc -c < README.md) bytes"'
  EVIDENCE: pending

</pre>

<h2><span class="num">03</span>Constraints & contracts</h2>
<div class="card context"><p>Data contracts, boundaries, non-goals. A check says WHAT must hold; this says why the alternative was refused — point at the DECISIONS.md block.</p></div>

<h2><span class="num">04</span>EVIDENCE</h2>
<p style="color:var(--dim)">Verdicts land here as gates run. A gate without receipt or ABANDON keeps the milestone open.</p>
<pre id="evidence"># EVIDENCE: written by the session / ai-verify
</pre>
</body>
</html>
