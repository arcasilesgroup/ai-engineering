<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>plan.html — HOW · {{milestone}}</title>
<style>
  :root { --bg:#0B1120; --surface:#121E36; --line:rgba(0,212,170,.15); --accent:#00D4AA; --text:#F8FAFB; --dim:#A9BBD0; --warn:#eab308; --ok:#22c55e; --mono:'SF Mono',ui-monospace,monospace; }
  * { margin:0; padding:0; box-sizing:border-box; }
  body { background:var(--bg); color:var(--text); font-family:-apple-system,system-ui,sans-serif; padding:48px 32px; }
  h1 { font-size:28px; } h1 .x { color:var(--accent); }
  h2 { color:var(--accent); font-family:var(--mono); font-size:13px; text-transform:uppercase; letter-spacing:.2em; margin:32px 0 12px; }
  h2 .num { color:var(--dim); margin-right:10px; }
  table { width:100%; border-collapse:collapse; }
  td, th { padding:8px 10px; border-bottom:1px solid var(--line); color:var(--dim); font-size:13.5px; text-align:left; }
  th { font-family:var(--mono); font-size:11px; text-transform:uppercase; letter-spacing:.1em; color:var(--accent); }
  td:first-child { font-family:var(--mono); color:var(--accent); }
  code { font-family:var(--mono); font-size:12.5px; color:#5FE6C6; }
  a { color:var(--accent); }
  .card { background:var(--surface); border:1px solid var(--line); border-radius:10px; padding:16px 18px; margin:10px 0; }
  .context { font-size:13.5px; color:var(--dim); line-height:1.55; }
</style>
</head>
<body>
<h1><span class="x">{ai}</span> plan · {{milestone}}</h1>
<p style="color:var(--dim)">HOW, WHEN, IN WHAT ORDER. The loop (ai-goal) marks it every iteration; CI never executes it — its derived truth is the receipts of spec.html.</p>

<h2><span class="num">00</span>Context chain</h2>
<div class="card context">
  <p>Research → spec → this plan. The loop keeps all three open; the plan never restates what the spec already says.</p>
  <div class="meta" style="display:flex;gap:24px;flex-wrap:wrap;color:var(--dim);font-size:13px;margin-top:8px">
    <span>Research: <b>{{research}}</b></span>
    <span>Spec: <b><a href="spec.html">spec.html</a></b></span>
    <span>Plan: <b>plan.html (this file)</b></span>
  </div>
</div>

<h2><span class="num">01</span>Steps → gates</h2>
<table>
<tr><th>#</th><th>Step</th><th>Closes</th><th>State</th></tr>
<tr><td>1</td><td>…</td><td>G1</td><td>🟡</td></tr>
</table>

<h2><span class="num">02</span>Risk & parallelism</h2>
<div class="card context">
  <p><code>Jobs:</code> marks steps that must never run in parallel (shared files, migrations, lock contention). Risky steps carry their rollback one line below.</p>
</div>

<h2><span class="num">03</span>Gates ledger</h2>
<table>
<tr><th>Gate</th><th>State</th><th>Receipt</th></tr>
<tr><td>G1</td><td>🟡</td><td>—</td></tr>
</table>
</body>
</html>
