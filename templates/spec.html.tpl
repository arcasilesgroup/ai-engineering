<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>spec.html — WHAT · {{milestone}}</title>
<style>
  :root { --bg:#0B1120; --surface:#121E36; --line:rgba(0,212,170,.15); --accent:#00D4AA; --text:#F8FAFB; --dim:#A9BBD0; --ok:#22c55e; --bad:#ef4444; --warn:#eab308; --mono:'SF Mono',ui-monospace,monospace; }
  * { margin:0; padding:0; box-sizing:border-box; }
  body { background:var(--bg); color:var(--text); font-family:-apple-system,system-ui,sans-serif; padding:48px 32px; }
  h1 { font-size:28px; letter-spacing:-.5px; } h1 .x { color:var(--accent); }
  h2 { color:var(--accent); font-family:var(--mono); font-size:13px; text-transform:uppercase; letter-spacing:.2em; margin:32px 0 12px; }
  h2 .num { color:var(--dim); margin-right:10px; }
  .card { background:var(--surface); border:1px solid var(--line); border-radius:10px; padding:16px 18px; margin:10px 0; }
  .meta { display:flex; gap:24px; flex-wrap:wrap; color:var(--dim); font-size:13px; margin:8px 0 0; }
  .meta b { color:var(--text); font-weight:500; }
  code, pre { font-family:var(--mono); font-size:12.5px; color:#5FE6C6; }
  pre { background:#0E1830; border:1px solid var(--line); border-radius:8px; padding:12px; overflow-x:auto; color:var(--dim); }
  .gate .id { font-family:var(--mono); color:var(--accent); font-weight:600; }
  .gate .status { font-family:var(--mono); font-size:11px; }
  .gate .check { font-family:var(--mono); font-size:12px; color:var(--dim); display:block; margin-top:6px; }
  a { color:var(--accent); }
  .context { font-size:13.5px; color:var(--dim); line-height:1.55; }
</style>
</head>
<body>
<h1><span class="x">{ai}</span> spec · {{milestone}}</h1>
<p style="color:var(--dim)">WHAT and WHY — requirements and acceptance gates. Executed by <code>ai-eng spec run</code>; its sha256 is pinned in <code>ai-eng.lock</code> at approval (STOP 1).</p>

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
<p style="color:var(--dim)">unlazy gate format, executed by <code>ai-eng spec run</code> (gate-check.mjs). Max 30 per milestone. ABANDON: G&lt;n&gt; &lt;reason&gt; is the honest exit.</p>
<pre id="gates">
# Gates: {{milestone}}

- [ ] G1: <observable outcome>
  CHECK: test -f README.md
  EVIDENCE: pending

</pre>

<h2><span class="num">03</span>Constraints & contracts</h2>
<div class="card context"><p>Data contracts, boundaries, non-goals. A check says WHAT must hold; this says why the alternative was refused — point at the DECISIONS.md block.</p></div>

<h2><span class="num">04</span>EVIDENCE</h2>
<p style="color:var(--dim)">Verdicts land here as gates run. A gate without receipt or ABANDON keeps the milestone open.</p>
<pre id="evidence"># EVIDENCE: appended by spec run / ai-verify
</pre>
</body>
</html>
