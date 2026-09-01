# {ai} Engineering — blueprint v17 spec.html template (§22 branding)
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>spec.html — QUÉ · {{hito}}</title>
<style>
  :root { --bg:#0B1120; --surface:#121E36; --line:rgba(0,212,170,.15); --accent:#00D4AA; --text:#F8FAFB; --dim:#A9BBD0; --ok:#22c55e; --bad:#ef4444; --mono:'SF Mono',monospace; }
  * { margin:0; padding:0; box-sizing:border-box; }
  body { background:var(--bg); color:var(--text); font-family:-apple-system,system-ui,sans-serif; padding:48px 32px; }
  h1 { font-size:28px; letter-spacing:-.5px; } h1 .x { color:var(--accent); }
  h2 { color:var(--accent); font-family:var(--mono); font-size:13px; text-transform:uppercase; letter-spacing:.2em; margin:32px 0 12px; }
  .gate { background:var(--surface); border:1px solid var(--line); border-radius:10px; padding:16px 18px; margin:10px 0; }
  .gate .id { font-family:var(--mono); color:var(--accent); font-weight:600; }
  .gate .status { font-family:var(--mono); font-size:11px; }
  code, pre { font-family:var(--mono); font-size:12.5px; color:#5FE6C6; }
  pre { background:#0E1830; border:1px solid var(--line); border-radius:8px; padding:12px; overflow-x:auto; color:var(--dim); }
</style>
</head>
<body>
<h1><span class="x">{ai}</span> spec · {{hito}}</h1>
<p style="color:var(--dim)">QUÉ y POR QUÉ — requisitos y gates de aceptación. Ejecutado por <code>ai-eng spec run</code>; su sha256 se fija en <code>ai-eng.lock</code> al aprobarse (PARADA 1).</p>
<h2>Gates</h2>
<p style="color:var(--dim)">Formato gates de unlazy (ejecutado por <code>ai-eng spec run</code> → gate-check.mjs). Máximo 30 por hito. ABANDON: G&lt;n&gt; &lt;razón&gt; como salida honesta.</p>
<pre id="gates">
# Gates: {{hito}}

- [ ] G1: <observable outcome>
  CHECK: test -f README.md
  EVIDENCE: pending

</pre>
</body>
</html>
