// State-matched screenshots of a prototype and its live route.
// Drives both sides through the same scenario steps, fingerprints the UI state on each,
// and flags pairs whose states diverge, so reviewers never compare an empty form with a submitted one.
//
// Run from the repo root:
//   npx -y -p playwright sh -c 'NODE_PATH="$(dirname "$(command -v playwright)")/.." node skills/ai-review-ui/capture.cjs <name> [baseUrl]'
// Reads   .ai-engineering/workflow/prototypes/<name>.states.json
// Writes  .playwright/review/<name>/<state>-<width>-{proto,live}.png and states.json
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const argv = process.argv.slice(2);
const si = argv.indexOf("--scope");
// Scope = the regions (data-region names) the current checkpoint has built; null = whole screen.
const scope = si >= 0 ? argv.splice(si, 2)[1].split(",").map((s) => s.trim()).filter(Boolean) : null;
const [name, base = "http://localhost:3000"] = argv;
if (!name) { console.error("usage: skills/ai-review-ui/capture.cjs <prototype-name> [baseUrl] [--scope region1,region2]"); process.exit(1); }

const root = process.cwd();
const scenarioPath = path.join(root, ".ai-engineering", "workflow", "prototypes", `${name}.states.json`);
const sc = JSON.parse(fs.readFileSync(scenarioPath, "utf8"));
const out = path.join(root, ".playwright", "review", name);
fs.mkdirSync(out, { recursive: true });

const viewports = sc.viewports || [[1440, 900], [375, 812]];
const now = new Date(sc.now || "2026-10-01T10:00:00");
const auth = path.join(root, sc.auth || ".playwright/auth.json");
const login = sc.login || "/login"; // sign-in path; a redirect here means the saved session expired
const localLive = /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?/.test(base);
const FREEZE = "*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important}";

// Non-exact: a <select> wrapped in its <label> gets the selected option appended to its accessible name.
const field = (page, label) => page.getByLabel(label).first();

async function step(page, s) {
  const o = { timeout: 5000 };
  if (s.fill !== undefined) return field(page, s.fill).fill(String(s.value ?? ""), o);
  if (s.select !== undefined) return field(page, s.select).selectOption({ label: s.value }, o);
  if (s.check !== undefined) return field(page, s.check).check(o);
  if (s.click !== undefined) return page.getByRole(s.role || "button", { name: s.click, exact: true }).first().click(o);
  if (s.press !== undefined) return page.keyboard.press(s.press);
  if (s.waitFor !== undefined) return page.getByText(s.waitFor).first().waitFor(o);
  if (s.wait !== undefined) return page.waitForTimeout(s.wait);
  throw new Error(`unknown step ${JSON.stringify(s)}`);
}

// What "state" the screen is in: form values, open dialogs, visible errors. Not content, so fake vs real data doesn't matter.
// With a scope, elements inside out-of-scope data-regions are ignored (pages without data-region are unaffected).
const fingerprint = (page, scope) => page.evaluate((scope) => {
  const inScope = (el) => { const r = el.closest("[data-region]"); return !scope || !r || scope.includes(r.dataset.region); };
  const vis = (el) => inScope(el) && !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length) && getComputedStyle(el).visibility !== "hidden";
  const labelOf = (el) => {
    const l = el.labels?.[0]?.cloneNode(true);
    l?.querySelectorAll("input,select,textarea").forEach((c) => c.remove());
    return (l?.textContent || el.getAttribute("aria-label") || el.name || "").replace(/\s+/g, " ").trim().replace(/\s*\*$/, "");
  };
  const fields = {};
  for (const el of document.querySelectorAll("input:not([type=hidden]),select,textarea")) {
    if (!vis(el) || !labelOf(el)) continue;
    fields[labelOf(el)] = ["checkbox", "radio"].includes(el.type) ? el.checked : el.value;
  }
  const dialogs = [...document.querySelectorAll("[role=dialog],[role=alertdialog],dialog[open]")].filter(vis)
    .map((d) => (d.querySelector("h1,h2,h3")?.innerText || d.getAttribute("aria-label") || "dialog").trim());
  return {
    fields,
    dialogs,
    alerts: [...document.querySelectorAll("[role=alert],[role=status]")].filter((e) => vis(e) && e.innerText.trim()).length,
    invalid: [...document.querySelectorAll("[aria-invalid=true]")].filter(vis).length,
  };
}, scope);

function diff(p, l) {
  const m = [];
  for (const k of new Set([...Object.keys(p.fields), ...Object.keys(l.fields)])) {
    if (!(k in l.fields)) m.push(`field "${k}" only in prototype`);
    else if (!(k in p.fields)) m.push(`field "${k}" only in live`);
    else if (String(p.fields[k]) !== String(l.fields[k])) m.push(`field "${k}": prototype=${JSON.stringify(p.fields[k])} live=${JSON.stringify(l.fields[k])}`);
  }
  if (p.dialogs.length !== l.dialogs.length) m.push(`open dialogs: prototype=${JSON.stringify(p.dialogs)} live=${JSON.stringify(l.dialogs)}`);
  if (!!p.alerts !== !!l.alerts) m.push(`alert/status message: prototype=${p.alerts} live=${l.alerts}`);
  if (!!p.invalid !== !!l.invalid) m.push(`invalid fields: prototype=${p.invalid} live=${l.invalid}`);
  return m;
}

async function side(browser, vp, url, steps, storage) {
  const ctx = await browser.newContext({ viewport: { width: vp[0], height: vp[1] }, reducedMotion: "reduce", ...(storage ? { storageState: storage } : {}) });
  const page = await ctx.newPage();
  await page.clock.setFixedTime(now);
  const res = { errors: [] };
  try {
    await page.goto(url, { waitUntil: "networkidle" });
    await page.addStyleTag({ content: FREEZE });
    for (const [i, s] of steps.entries()) {
      try { await step(page, s); } catch (e) { res.errors.push(`step ${i + 1} ${JSON.stringify(s)}: ${e.message.split("\n")[0]}`); break; }
    }
    await page.waitForLoadState("networkidle").catch(() => {});
    await page.waitForTimeout(300);
    res.fp = await fingerprint(page, scope);
    res.page = page;
    if (new URL(page.url()).pathname === login && !url.includes(login)) res.errors.push(`redirected to ${login}: sign-in session missing or expired`);
  } catch (e) { res.errors.push(e.message.split("\n")[0]); res.page = page; }
  return { ...res, ctx };
}

(async () => {
  const browser = await chromium.launch();
  const report = [];
  const states = scope ? sc.states.filter((st) => st.regions?.length && st.regions.every((r) => scope.includes(r))) : sc.states;
  if (scope) console.log(`scope ${scope.join(",")}: ${states.length}/${sc.states.length} states (${sc.states.filter((s) => !states.includes(s)).map((s) => s.name).join(", ") || "none"} out of scope)`);
  for (const vp of viewports) {
    for (const st of states) {
      const tag = `${st.name}-${vp[0]}`;
      const q = st.proto_query ? `?${st.proto_query}` : "";
      const proto = await side(browser, vp, `file://${path.join(root, ".ai-engineering", "workflow", "prototypes", `${name}.html`)}${q}`, st.steps || []);
      await proto.page?.screenshot({ path: path.join(out, `${tag}-proto.png`), fullPage: true });
      const entry = { state: st.name, viewport: vp, proto: { fp: proto.fp, errors: proto.errors } };

      let why = null;
      if (st.live === false) why = st.live_note || "not reproducible on live";
      else if (st.mutates && !localLive) why = "mutating state skipped: live is not a local server";
      if (why) { entry.live = { skipped: why }; entry.comparable = false; }
      else {
        const a = st.auth ? path.join(root, st.auth) : auth;
        const live = await side(browser, vp, `${base}${sc.route}${st.live_query ? `?${st.live_query}` : ""}`, st.steps || [], fs.existsSync(a) ? a : undefined);
        await live.page?.screenshot({ path: path.join(out, `${tag}-live.png`), fullPage: true });
        entry.live = { fp: live.fp, errors: live.errors };
        entry.mismatches = [...proto.errors.map((e) => `prototype ${e}`), ...live.errors.map((e) => `live ${e}`),
          ...(proto.fp && live.fp ? diff(proto.fp, live.fp) : [])];
        entry.comparable = entry.mismatches.length === 0;
        await live.ctx.close();
      }
      await proto.ctx.close();
      report.push(entry);
      console.log(`${entry.comparable ? "match   " : entry.live.skipped ? "proto-only" : "MISMATCH"}  ${tag}${entry.live.skipped ? ` (${entry.live.skipped})` : ""}${entry.mismatches?.length ? "\n    - " + entry.mismatches.join("\n    - ") : ""}`);
    }
  }
  fs.writeFileSync(path.join(out, "states.json"), JSON.stringify({ scope, states: report }, null, 2));
  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
