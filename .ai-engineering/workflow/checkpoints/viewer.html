<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Feature Progress</title>
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 32 32%22%3E%3Crect width=%2232%22 height=%2232%22 rx=%227%22 fill=%22%23001E2B%22/%3E%3Crect x=%220.5%22 y=%220.5%22 width=%2231%22 height=%2231%22 rx=%226.5%22 fill=%22none%22 stroke=%22%2300ED64%22 stroke-opacity=%220.35%22/%3E%3Ctext x=%2216%22 y=%2217%22 text-anchor=%22middle%22 dominant-baseline=%22central%22 font-family=%22ui-monospace, Menlo, Consolas, 'DejaVu Sans Mono', monospace%22 font-size=%2214%22 font-weight=%22700%22 letter-spacing=%22-1%22%3E%3Ctspan fill=%22%2300ED64%22%3E%7B%3C/tspan%3E%3Ctspan fill=%22%23E8EEF7%22%3Eai%3C/tspan%3E%3Ctspan fill=%22%2300ED64%22%3E%7D%3C/tspan%3E%3C/text%3E%3C/svg%3E">
<style>
:root{
  --bg:#001E2B; --surface:#112733; --surface-2:#1C2D38;
  --line:rgba(61,79,88,.3); --line-strong:rgba(61,79,88,.6);
  --accent:#00ED64; --accent-dim:#71F6BA;
  --text:#FFFFFF; --dim:#C1C7C6; --comment:#889397;
  --ok:#00ED64; --bad:#FF6960; --warn:#FFC010;
  --mono:'SF Mono','JetBrains Mono','Fira Code',ui-monospace,monospace;
  --sans:-apple-system,BlinkMacSystemFont,'Inter',system-ui,sans-serif;
  --fs-h2:26px; --lh-h2:1.16; --ls-h2:-.018em;
  --fs-h3:17px; --lh-h3:1.32; --ls-h3:-.006em;
  --fs-body:15px; --lh-body:1.62;
  --fs-small:13.5px; --lh-small:1.55;
  --fs-mono:12.5px; --fs-label:10.5px;
  --s1:4px; --s2:8px; --s3:12px; --s4:16px; --s5:24px; --s6:32px; --s7:48px;
  --radius:12px; --radius-sm:8px; --container:760px;
}
*{margin:0;padding:0;box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{
  background:var(--bg);color:var(--text);font-family:var(--sans);
  font-size:var(--fs-body);line-height:var(--lh-body);
  -webkit-font-smoothing:antialiased;
}
::selection{background:rgba(0,237,100,.28)}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline;text-underline-offset:3px}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:3px}
main{max-width:var(--container);margin:0 auto;padding:var(--s6) var(--s4) 80px}
.top{display:flex;justify-content:space-between;gap:var(--s3);flex-wrap:wrap;align-items:center}
.eyebrow{
  font-family:var(--mono);font-size:var(--fs-label);font-weight:600;
  letter-spacing:.22em;text-transform:uppercase;color:var(--accent);
}
.row{display:inline-flex;gap:10px;align-items:center}
.live{font-family:var(--mono);font-size:11.5px;color:var(--comment);display:inline-flex;gap:6px;align-items:center}
.live::before{content:"";width:8px;height:8px;border-radius:50%;background:var(--accent);animation:pulse 2s infinite}
.live.off::before{background:var(--line-strong);animation:none}
h1{font-size:var(--fs-h2);line-height:var(--lh-h2);letter-spacing:var(--ls-h2);font-weight:700;margin:var(--s2) 0 var(--s2)}
.lede{font-size:var(--fs-h3);line-height:var(--lh-h3);color:var(--dim);max-width:68ch;margin:0}
.muted{color:var(--comment)}
.banner{
  margin:var(--s5) 0 0;padding:14px var(--s4);border-radius:var(--radius-sm);
  font-weight:600;display:flex;gap:10px;align-items:center;border:1px solid;
}
.banner.run{background:rgba(0,237,100,.08);color:var(--accent-dim);border-color:rgba(0,237,100,.28)}
.banner.done{background:rgba(0,237,100,.13);color:var(--ok);border-color:rgba(0,237,100,.32)}
.banner.stop{background:rgba(255,105,96,.12);color:var(--bad);border-color:rgba(255,105,96,.34)}
.banner .dot{width:10px;height:10px;border-radius:50%;background:currentColor;flex:none}
.banner.run .dot{animation:pulse 1.6s infinite}
@keyframes pulse{50%{opacity:.25}}
.journey{display:flex;align-items:center;margin:calc(var(--s6) - 4px) -4px calc(var(--s2) - 4px);padding:4px;min-width:0;overflow-x:auto}
.journey .line{flex:1;height:2px;background:var(--line-strong);min-width:4px}
.journey .line.on{background:var(--accent)}
.jdot{
  border-radius:50%;display:grid;place-items:center;font-size:12px;font-weight:700;
  flex:none;border:2px solid var(--line-strong);background:var(--surface);color:var(--comment);
  cursor:pointer;padding:0;font-family:var(--sans);
}
.jdot.passed{background:var(--accent);border-color:var(--accent);color:#001E2B}
.jdot.running{border-color:var(--accent);color:var(--accent);box-shadow:0 0 0 4px rgba(0,237,100,.12)}
.jdot.failed,.jdot.blocked{border-color:var(--bad);color:var(--bad);box-shadow:0 0 0 4px rgba(255,105,96,.12)}
.jdot.blocked{background:var(--bad);color:#001E2B}
.caption{font-size:var(--fs-small);color:var(--comment);margin:0 0 var(--s5)}
.step{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);margin:var(--s3) 0}
.step.current{border-color:rgba(0,237,100,.45);box-shadow:0 0 0 1px rgba(0,237,100,.25)}
.step>summary{list-style:none;cursor:pointer;padding:var(--s4);display:grid;grid-template-columns:36px 1fr;gap:var(--s3)}
.step>summary::-webkit-details-marker{display:none}
.num{
  width:36px;height:36px;border-radius:50%;display:grid;place-items:center;font-weight:700;
  background:var(--surface-2);color:var(--comment);font-family:var(--mono);font-size:13px;
}
.passed .num{background:var(--accent);color:#001E2B}
.running .num{background:rgba(0,237,100,.12);color:var(--accent)}
.failed .num,.blocked .num{background:rgba(255,105,96,.14);color:var(--bad)}
.status{font-family:var(--mono);font-size:11px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--comment)}
.passed .status{color:var(--ok)} .running .status{color:var(--accent-dim)}
.failed .status,.blocked .status{color:var(--bad)} .pending .status{color:var(--comment)}
.what{font-size:var(--fs-h3);font-weight:640;line-height:var(--lh-h3);margin:2px 0 10px;color:var(--text)}
.checks{display:flex;flex-wrap:wrap;gap:6px}
.chk{
  font-size:13px;padding:3px 10px;border-radius:999px;border:1px solid var(--line);
  background:var(--surface-2);color:var(--dim);white-space:nowrap;font-family:var(--sans);
}
.chk.passed{background:rgba(0,237,100,.13);border-color:rgba(0,237,100,.32);color:var(--ok)}
.chk.failed{background:rgba(255,105,96,.13);border-color:rgba(255,105,96,.34);color:var(--bad)}
.chk.running{background:rgba(0,237,100,.1);border-color:rgba(0,237,100,.35);color:var(--accent-dim)}
.chk.na{background:transparent;border-style:dashed;color:var(--comment)}
.more{font-size:13px;color:var(--accent-dim);margin-top:10px}
.step[open] .more{display:none}
.body{padding:0 var(--s4) var(--s4) 64px}
.body h2{font-family:var(--mono);font-size:var(--fs-label);font-weight:600;letter-spacing:.18em;text-transform:uppercase;color:var(--accent-dim);margin:14px 0 4px}
.body p{margin:0;color:var(--dim);font-size:var(--fs-small);line-height:var(--lh-small);max-width:68ch;text-align:left}
.tech{margin-top:var(--s4);border-top:1px dashed var(--line);padding-top:10px;font-size:13px}
.tech>summary{cursor:pointer;color:var(--comment);font-family:var(--mono);font-size:12px;padding-block:13px}
.tech code,.tech .mono{font-family:var(--mono);font-size:var(--fs-mono);background:var(--surface-2);border:1px solid var(--line);border-radius:5px;padding:1px 6px;color:var(--accent-dim)}
.tech ul{margin:4px 0;padding-left:18px;color:var(--dim)}
.finding{border-left:3px solid var(--bad);background:rgba(255,105,96,.12);padding:6px 10px;margin:6px 0;font-family:var(--mono);font-size:12px;white-space:pre-wrap;word-break:break-word;color:var(--dim)}
.cmd{display:block;background:var(--surface-2);border:1px solid var(--line);border-radius:4px;padding:4px 8px;margin:3px 0;overflow-x:auto;white-space:pre;font-family:var(--mono);font-size:var(--fs-mono);color:var(--accent-dim)}
.panel{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);padding:var(--s4);margin-top:var(--s5)}
.panel h2{font-size:15px;margin:0 0 var(--s2);font-weight:640}
.panel ul{margin:0;padding-left:18px}.panel li{margin:4px 0;color:var(--dim);font-size:var(--fs-small)}
select{font:inherit;font-family:var(--mono);font-size:12px;background:var(--surface);color:var(--text);border:1px solid var(--line-strong);border-radius:6px;padding:4px 8px}
.drop{
  border:2px dashed var(--line-strong);border-radius:var(--radius);padding:var(--s7) var(--s4);
  text-align:center;background:var(--surface);margin-top:var(--s5);overflow-wrap:anywhere;
}
.drop.over{border-color:var(--accent)}
.drop h1{font-size:var(--fs-h3);line-height:var(--lh-h3);letter-spacing:var(--ls-h3);font-weight:640}
.drop p{margin:0 auto var(--s2);max-width:48ch;color:var(--dim);font-size:var(--fs-small);line-height:var(--lh-small)}
.drop strong{color:var(--text)}
.drop code{font-family:var(--mono);font-size:var(--fs-mono);color:var(--accent-dim)}
.drop input{min-height:44px}
@media (max-width:520px){.body{padding-left:var(--s4)} h1{font-size:22px}}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
</style>
</head>
<body>
<main>
  <div class="top" data-region="page-header">
    <span class="eyebrow">Feature progress</span>
    <span class="row"><span id="live" class="live off">offline</span></span>
  </div>

  <section id="empty" class="drop" data-region="empty-drop" hidden>
    <h1>Open a feature plan</h1>
    <p class="muted">Drop a file from <code>.ai-engineering/workflow/checkpoints/</code> here, or choose one:</p>
    <input type="file" id="file" accept=".json,application/json" aria-label="Feature plan file">
    <p class="muted" style="font-size:13px">For live updates, serve the repo root over HTTP and open <code>.ai-engineering/workflow/checkpoints/viewer.html?plan=&lt;slug&gt;</code></p>
  </section>

  <section id="app" hidden>
    <h1 id="title"></h1>
    <p class="lede" id="summary" data-region="plain-summary"></p>
    <div id="banner" class="banner run" role="status" data-region="status-banner"><span class="dot"></span><span id="bannerText"></span></div>
    <div class="journey" id="journey" aria-label="Steps overview" data-region="journey"></div>
    <p class="caption">Small steps first, each one a little bigger. A step must pass all its checks before the next one starts.</p>
    <div id="steps" data-region="checkpoint-card"></div>
    <div id="extra"></div>
  </section>
</main>

<script>
const SIZES = { xs: 1, s: 2, m: 3, l: 4, xl: 5 };
// Diameter encodes step size: 27, 32, 37, 42, 47. The small rungs stay under a 44px thumb target on purpose.
const CHECKS = [
  ["behavior", "Works", "Testing that it works"],
  ["ui", "Looks right", "Comparing it with the design"],
  ["review", "Code review", "Reviewing the code"],
];
const MAX_TRIES = 3;
const served = location.protocol.startsWith("http");
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
let plan = null, tests = null, lastText = "", lastTests = "", openIds = null;

const gs = (cp, k) => { const g = cp.gates?.[k]; return !g ? "pending" : g.status === "n/a" ? "na" : g.status || "pending"; };
const tries = (cp, k) => cp.gates?.[k]?.attempts || 0;
const nProblems = (cp) => CHECKS.reduce((n, [k]) => n + (cp.gates?.[k]?.findings?.length || 0), 0);

function stepState(cp, currentId) {
  if (cp.status === "passed") return "passed";
  if (CHECKS.some(([k]) => gs(cp, k) === "failed" && tries(cp, k) >= MAX_TRIES)) return "blocked";
  if (cp.id !== currentId) return "pending";
  return CHECKS.some(([k]) => gs(cp, k) === "failed") ? "failed" : "running";
}

function activity(cp) {
  const open = CHECKS.find(([k]) => ["pending", "failed"].includes(gs(cp, k)));
  if (!open) return "Wrapping up";
  const [k, , doing] = open;
  const started = CHECKS.some(([kk]) => ["passed", "failed"].includes(gs(cp, kk)));
  if (!started && !tries(cp, k)) return "Building it";
  return gs(cp, k) === "failed" ? `Fixing problems found while ${doing.toLowerCase()} (try ${tries(cp, k) + 1})` : doing;
}

const STATUS = { passed: "Done", running: "In progress", failed: "Fixing problems", blocked: "Stuck, needs you", pending: "Not started" };

function render() {
  const cps = plan.checkpoints || [];
  const current = cps.find((c) => c.status !== "passed");
  const done = cps.filter((c) => c.status === "passed").length;
  if (openIds === null) openIds = new Set(current ? [current.id] : []);

  $("title").textContent = plan.feature || plan.slug || "Untitled feature";
  $("summary").textContent = plan.plain_summary || plan.summary || "";
  document.title = `${plan.feature || "Feature"} · ${done}/${cps.length}`;

  const b = $("banner");
  if (plan.halted?.reason) { b.className = "banner stop"; $("bannerText").textContent = `Stopped. Needs your input: ${plan.halted.reason}`; }
  else if (!current) { b.className = "banner done"; $("bannerText").textContent = `All ${cps.length} steps done. Ready for you to try it.`; }
  else {
    const st = stepState(current, current.id);
    b.className = "banner " + (st === "blocked" ? "stop" : "run");
    $("bannerText").textContent = st === "blocked" ? `Step ${current.id} of ${cps.length} is stuck and needs you.` : `Step ${current.id} of ${cps.length}: ${activity(current)}`;
  }

  $("journey").innerHTML = cps.map((cp, i) => {
    const s = stepState(cp, current?.id), d = 22 + (SIZES[cp.size] || 1) * 5;
    return `${i ? `<span class="line ${cp.status === "passed" || s !== "pending" ? "on" : ""}"></span>` : ""}<button class="jdot ${s}" style="width:${d}px;height:${d}px" data-go="${esc(cp.id)}" title="Step ${esc(cp.id)}: ${cp.simple ? esc(cp.simple) + " · " : ""}${esc(STATUS[s])}" aria-label="Go to step ${esc(cp.id)}">${s === "passed" ? "✓" : esc(cp.id)}</button>`;
  }).join("");
  document.querySelectorAll("[data-go]").forEach((el) => el.onclick = () => {
    const go = +el.dataset.go;
    openIds.add(go);
    render();
    document.getElementById("step-" + go)?.scrollIntoView({ behavior: "smooth", block: "start" });
  });

  $("steps").innerHTML = cps.map((cp) => stepCard(cp, current?.id)).join("");
  document.querySelectorAll("details.step").forEach((d) => d.ontoggle = () => { const id = +d.dataset.id; d.open ? openIds.add(id) : openIds.delete(id); });

  const assumptions = plan.assumptions || [], later = plan.notes || [];
  $("extra").innerHTML =
    (assumptions.length ? `<div class="panel"><h2>Decisions made for you</h2><p class="muted" style="margin:0 0 6px;font-size:13px">Where the request didn't say, the plan picked these. Tell the agent if any are wrong.</p><ul>${assumptions.map((a) => `<li>${esc(a)}</li>`).join("")}</ul></div>` : "") +
    (later.length ? `<div class="panel"><h2>Left for later</h2><ul>${later.map((a) => `<li>${esc(a)}</li>`).join("")}</ul></div>` : "");
}

function stepCard(cp, currentId) {
  const s = stepState(cp, currentId), p = cp.plain || {};
  const checks = CHECKS.map(([k, label]) => {
    let st = gs(cp, k);
    if (st === "na") return `<span class="chk na" title="This step has no screen to compare">${label}: no screen</span>`;
    if (st === "pending" && s === "running" && activity(cp).startsWith(CHECKS.find(([kk]) => kk === k)[2])) st = "running";
    const icon = { passed: "✓", failed: "✕", running: "…", pending: "○" }[st];
    const t = tries(cp, k);
    return `<span class="chk ${esc(st)}">${icon} ${label}${t ? ` · ${esc(t)} ${t === 1 ? "retry" : "retries"}` : ""}</span>`;
  }).join("");

  const problems = CHECKS.flatMap(([k, label]) => (cp.gates?.[k]?.findings || []).map((f) => `<div class="finding"><b>${label}:</b> ${esc(typeof f === "string" ? f : JSON.stringify(f))}</div>`)).join("");
  const cpTests = tests ? ["unit", "api", "cli", "ui"].flatMap((l) => (tests.layers?.[l] || []).filter((t) => t.checkpoint === cp.id).map((t) => `<li><span class="mono">${l}</span> ${esc(t.case)}</li>`)).join("") : "";

  return `<details class="step ${s} ${cp.id === currentId ? "current" : ""}" id="step-${esc(cp.id)}" data-id="${esc(cp.id)}" ${openIds.has(cp.id) ? "open" : ""}>
    <summary>
      <span class="num">${s === "passed" ? "✓" : esc(cp.id)}</span>
      <span>
        <span class="status">Step ${esc(cp.id)} · ${STATUS[s]}</span>
        <div class="what">${esc(cp.simple || p.what || cp.goal || cp.title)}</div>
        <div class="checks">${checks}</div>
        <div class="more">Show more ▾</div>
      </span>
    </summary>
    <div class="body">
      ${cp.simple && p.what ? `<h2>What you get</h2><p>${esc(p.what)}</p>` : ""}
      ${p.why ? `<h2>Why it matters</h2><p>${esc(p.why)}</p>` : ""}
      ${p.check ? `<h2>How you can check it</h2><p>${esc(p.check)}</p>` : ""}
      ${cp.ui?.prototype ? `<h2>Design to compare with</h2><p>${served ? `<a href="../../../${esc(cp.ui.prototype)}" target="_blank" rel="noopener">Open the prototype</a>` : `<code>${esc(cp.ui.prototype)}</code>`}</p>` : ""}
      ${problems ? `<h2>Problems being fixed</h2><p>The automatic checks found ${nProblems(cp)} ${nProblems(cp) === 1 ? "problem" : "problems"}. The agent is fixing ${nProblems(cp) === 1 ? "it" : "them"} by itself, so you don't need to do anything.</p>` : ""}
      <details class="tech" data-region="tech-details"><summary>Technical details</summary>
        ${problems ? `<h2>Problems found</h2>${problems}` : ""}
        <p><b>${esc(cp.title)}</b> · size ${esc(cp.size)}${cp.builds_on?.length ? ` · builds on step ${cp.builds_on.map(esc).join(", ")}` : ""}</p>
        ${cp.goal ? `<p>${esc(cp.goal)}</p>` : ""}
        ${cp.acceptance?.length ? `<h2>Done when</h2><ul>${cp.acceptance.map((a) => `<li>${esc(a)}</li>`).join("")}</ul>` : ""}
        ${cp.tasks?.length ? `<h2>Tasks</h2><ul>${cp.tasks.map((a) => `<li>${esc(a)}</li>`).join("")}</ul>` : ""}
        ${cpTests ? `<h2>Tests</h2><ul>${cpTests}</ul>` : ""}
        ${cp.ui ? `<h2>Screen</h2><p><code>${esc(cp.ui.route)}</code>${cp.ui.scope?.length ? ` · parts: ${cp.ui.scope.map(esc).join(", ")}` : ""}</p>` : ""}
        ${cp.files?.length ? `<h2>Files</h2>${cp.files.map((f) => `<code>${esc(f)}</code>`).join("<br>")}` : ""}
        ${cp.verify?.length ? `<h2>Check commands</h2>${cp.verify.map((v) => `<code class="cmd">${esc(v)}</code>`).join("")}` : ""}
        ${plan.new_dependencies?.length && cp.id === 1 ? `<h2>New tools the feature needs</h2><ul>${plan.new_dependencies.map((a) => `<li>${esc(a)}</li>`).join("")}</ul>` : ""}
      </details>
    </div>
  </details>`;
}

function ensurePicker(files, slug) {
  let picker = $("picker");
  if (picker) return picker;
  picker = document.createElement("select");
  picker.id = "picker";
  picker.setAttribute("aria-label", "Choose a feature");
  picker.innerHTML = files.map((f) => `<option ${f === slug + ".json" ? "selected" : ""}>${esc(f.replace(/\.json$/, ""))}</option>`).join("");
  picker.onchange = (e) => { location.search = "?plan=" + encodeURIComponent(e.target.value); };
  $("live").parentElement.insertBefore(picker, $("live"));
  return picker;
}

function removePicker() {
  $("picker")?.remove();
}

function failLoad() {
  plan = null;
  $("empty").hidden = false;
  $("app").hidden = true;
  removePicker();
  return false;
}

function load(text) {
  if (text === lastText) return plan !== null;
  lastText = text;
  try { plan = JSON.parse(text); } catch (e) { return failLoad(); }
  if (plan === null || typeof plan !== "object" || Array.isArray(plan)) return failLoad();
  $("empty").hidden = true; $("app").hidden = false;
  render();
  return true;
}

async function fetchText(url) { const r = await fetch(url, { cache: "no-store" }); if (!r.ok) throw new Error(r.status); return r.text(); }

async function servedInit() {
  let files = [];
  try { files = [...(await fetchText("./")).matchAll(/href="([^"?/]+\.json)"/g)].map((m) => decodeURIComponent(m[1])); } catch {}
  const raw = new URLSearchParams(location.search).get("plan") || files[0]?.replace(/\.json$/, "");
  // A plan name is a flat file name, never a path: the URL is untrusted input
  // and the fetched JSON gets rendered, so no slashes or traversal reach fetch.
  const slug = raw && /^[\w.-]+$/.test(raw) ? raw : null;
  const canPick = files.length > 1;
  if (!slug) {
    $("empty").hidden = false;
    removePicker();
    $("live").className = "live off";
    $("live").textContent = "offline";
    return;
  }
  const tick = async () => {
    try {
      const ok = load(await fetchText(`./${slug}.json`));
      $("live").className = ok ? "live" : "live off";
      $("live").textContent = ok ? "live" : "offline";
      if (ok && canPick) ensurePicker(files, slug);
      else removePicker();
    } catch {
      $("empty").hidden = false; $("app").hidden = true;
      removePicker();
      $("live").className = "live off"; $("live").textContent = "offline";
    }
    try { const t = await fetchText(`../test-plans/${slug}.json`); if (t !== lastTests) { lastTests = t; tests = JSON.parse(t); if (plan) render(); } } catch {}
  };
  await tick();
  setInterval(tick, 3000);
}

function bindLocalFile() {
  const read = (f) => f && f.text().then(load);
  $("file").onchange = (e) => read(e.target.files[0]);
  addEventListener("dragover", (e) => { e.preventDefault(); $("empty").classList.add("over"); });
  addEventListener("dragleave", () => $("empty").classList.remove("over"));
  addEventListener("drop", (e) => { e.preventDefault(); $("empty").classList.remove("over"); read(e.dataTransfer.files[0]); });
}

bindLocalFile();
if (served) servedInit();
else $("empty").hidden = false;
</script>
</body>
</html>
