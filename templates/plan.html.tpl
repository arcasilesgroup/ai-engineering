# {ai} Engineering — blueprint v17 plan.html template (§22 branding)
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>plan.html — CÓMO · {{hito}}</title>
<style>
  :root { --bg:#0B1120; --surface:#121E36; --line:rgba(0,212,170,.15); --accent:#00D4AA; --text:#F8FAFB; --dim:#A9BBD0; --warn:#eab308; --mono:'SF Mono',monospace; }
  * { margin:0; padding:0; box-sizing:border-box; }
  body { background:var(--bg); color:var(--text); font-family:-apple-system,system-ui,sans-serif; padding:48px 32px; }
  h1 { font-size:28px; } h1 .x { color:var(--accent); }
  h2 { color:var(--accent); font-family:var(--mono); font-size:13px; text-transform:uppercase; letter-spacing:.2em; margin:32px 0 12px; }
  table { width:100%; border-collapse:collapse; }
  td { padding:8px 10px; border-bottom:1px solid var(--line); color:var(--dim); font-size:13.5px; }
  td:first-child { font-family:var(--mono); color:var(--accent); }
</style>
</head>
<body>
<h1><span class="x">{ai}</span> plan · {{hito}}</h1>
<p style="color:var(--dim)">CÓMO, CUÁNDO y EN QUÉ ORDEN. Lo marca el bucle (ai-goal); la CI no lo ejecuta — su verdad derivada son los receipts de spec.html.</p>
<h2>Pasos → gates</h2>
<table>
<tr><td>1</td><td>…</td><td>cierra G1</td><td>🟡</td></tr>
</table>
</body>
</html>
