<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 32 32%22%3E%3Crect width=%2232%22 height=%2232%22 rx=%227%22 fill=%22%23001E2B%22/%3E%3Crect x=%220.5%22 y=%220.5%22 width=%2231%22 height=%2231%22 rx=%226.5%22 fill=%22none%22 stroke=%22%2300ED64%22 stroke-opacity=%220.35%22/%3E%3Ctext x=%2216%22 y=%2217%22 text-anchor=%22middle%22 dominant-baseline=%22central%22 font-family=%22ui-monospace, Menlo, Consolas, 'DejaVu Sans Mono', monospace%22 font-size=%2214%22 font-weight=%22700%22 letter-spacing=%22-1%22%3E%3Ctspan fill=%22%2300ED64%22%3E%7B%3C/tspan%3E%3Ctspan fill=%22%23E8EEF7%22%3Eai%3C/tspan%3E%3Ctspan fill=%22%2300ED64%22%3E%7D%3C/tspan%3E%3C/text%3E%3C/svg%3E">
<title>plan.html — HOW · {{milestone}}</title>
<style>
  :root { --bg:#001E2B; --surface:#112733; --line:rgba(61,79,88,.3); --accent:#00ED64; --text:#FFFFFF; --dim:#C1C7C6; --warn:#FFC010; --ok:#00ED64; --mono:'SF Mono','JetBrains Mono','Fira Code',ui-monospace,monospace; }
  * { margin:0; padding:0; box-sizing:border-box; }
  body { background:var(--bg); color:var(--text); font-family:-apple-system,system-ui,sans-serif; padding:48px 32px; }
  h1 { font-size:28px; } h1 .x { color:var(--accent); }
  h2 { color:var(--accent); font-family:var(--mono); font-size:13px; text-transform:uppercase; letter-spacing:.2em; margin:32px 0 12px; }
  h2 .num { color:var(--dim); margin-right:10px; }
  table { width:100%; border-collapse:collapse; }
  td, th { padding:8px 10px; border-bottom:1px solid var(--line); color:var(--dim); font-size:13.5px; text-align:left; }
  th { font-family:var(--mono); font-size:11px; text-transform:uppercase; letter-spacing:.1em; color:var(--accent); }
  td:first-child { font-family:var(--mono); color:var(--accent); }
  code { font-family:var(--mono); font-size:12.5px; color:#71F6BA; }
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
