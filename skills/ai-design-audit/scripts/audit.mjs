#!/usr/bin/env node
// Measure a rendered web UI. Every number here comes out of a real browser laying
// out real type at a real width — never out of a stylesheet, because a declared
// value and a painted pixel are two different claims.
//
//   node audit.mjs --base http://localhost:4321 --routes / /about --widths 390 1440
//
// --checks picks the passes; --baseline turns the run into a before/after proof.

import { existsSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { inflateSync } from "node:zlib";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

/* ── argv ──────────────────────────────────────────────────────────────── */

const ALL_CHECKS = ["geometry", "contrast", "collision", "proximity", "type", "interior"];

function parseArgs(argv) {
  const out = { base: null, routes: ["/"], widths: [390, 820, 1440], checks: [...ALL_CHECKS], json: null, baseline: null, aaa: true, quiet: false, target: 44 };
  let key = null;
  for (const a of argv) {
    if (a.startsWith("--")) {
      key = a.slice(2);
      if (key === "quiet") { out.quiet = true; key = null; }
      else if (key === "aa") { out.aaa = false; key = null; }
      else if (!(key in out)) { fail(`unknown flag --${key}`); }
      else if (Array.isArray(out[key])) out[key] = [];
      continue;
    }
    if (!key) fail(`stray argument "${a}"`);
    if (Array.isArray(out[key])) out[key].push(key === "widths" ? Number(a) : a);
    else if (key === "target") out[key] = Number(a);
    else { out[key] = a; key = null; }
  }
  if (key && !Array.isArray(out[key])) fail(`--${key} needs a value`);
  if (!out.base) fail("--base <url> is required (serve the BUILT output, not a dev server)");
  try {
    const url = new URL(out.base);
    if (!/^https?:$/.test(url.protocol)) throw new Error();
  } catch { fail(`--base must be an absolute http(s) URL, got "${out.base}"`); }
  if (!out.routes.length) fail("--routes needs at least one route");
  if (!out.widths.length || out.widths.some((w) => !Number.isFinite(w) || w < 1)) {
    fail("--widths needs one or more positive numbers");
  }
  if (!Number.isFinite(out.target) || out.target < 1) fail("--target needs a positive number");
  if (!out.checks.length) fail("--checks needs at least one check");
  const bad = out.checks.filter((c) => !ALL_CHECKS.includes(c));
  if (bad.length) fail(`unknown check(s): ${bad.join(", ")}. Known: ${ALL_CHECKS.join(", ")}`);
  return out;
}
function fail(msg) { console.error(`audit: ${msg}`); process.exit(2); }

const ARGS = parseArgs(process.argv.slice(2));

/* ── playwright, wherever it lives ─────────────────────────────────────── */

// The library can be a direct dependency, a transitive one, hoisted to a monorepo
// root, or installed globally. Walking up from the cwd covers the first three and
// costs nothing; a bare specifier covers the case where this file is run by a
// package that already depends on it.
async function loadChromium() {
  const pkgs = ["playwright", "playwright-core", "@playwright/test"];
  const roots = [];
  for (let d = process.cwd(); ; d = join(d, "..")) {
    roots.push(join(d, "node_modules"));
    if (d === join(d, "..")) break;
  }
  roots.push(join(process.env.HOME ?? "", ".npm-global/lib/node_modules"),
    "/opt/homebrew/lib/node_modules", "/usr/local/lib/node_modules",
    join(process.env.HOME ?? "", ".bun/install/global/node_modules"));
  const specs = [...pkgs];
  for (const r of roots) for (const p of pkgs) specs.push(join(r, p, "index.mjs"), join(r, p, "index.js"));
  for (const spec of specs) {
    try {
      const mod = await import(spec.startsWith("/") ? pathToFileURL(spec).href : spec);
      const chromium = mod.chromium ?? mod.default?.chromium;
      if (chromium) return chromium;
    } catch {}
  }
  fail("playwright not found. Run from a project that has it, or `npm i -D playwright && npx playwright install chromium`");
}

// Playwright pins one browser build and the pin drifts out from under a project.
// Fall back to any cached build rather than refusing to measure anything.
async function launch(chromium) {
  try { return await chromium.launch(); } catch {}
  const roots = [
    join(process.env.HOME ?? "", "Library/Caches/ms-playwright"),
    join(process.env.HOME ?? "", ".cache/ms-playwright"),
  ];
  const exes = ["chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing",
    "chrome-mac/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing",
    "chrome-linux/chrome"];
  for (const root of roots) {
    if (!existsSync(root)) continue;
    for (const dir of readdirSync(root).filter((d) => d.startsWith("chromium-")).reverse()) {
      for (const exe of exes) {
        const p = join(root, dir, exe);
        if (!existsSync(p)) continue;
        try {
          const b = await chromium.launch({ executablePath: p });
          if (!ARGS.quiet) console.error(`  note: pinned build unavailable, using cached ${dir}`);
          return b;
        } catch {}
      }
    }
  }
  fail("no usable chromium. `npx playwright install chromium`");
}

/* ── PNG, decoded here so the only dependency is the browser ───────────── */

function decodePNG(buf) {
  let p = 8, w = 0, h = 0, depth = 0, type = 0;
  const idat = [];
  while (p < buf.length) {
    const len = buf.readUInt32BE(p);
    const tag = buf.toString("ascii", p + 4, p + 8);
    const body = buf.subarray(p + 8, p + 8 + len);
    if (tag === "IHDR") {
      w = body.readUInt32BE(0); h = body.readUInt32BE(4);
      depth = body[8]; type = body[9];
      if (depth !== 8 || (type !== 2 && type !== 6) || body[12] !== 0) {
        throw new Error(`unsupported PNG (depth ${depth}, colour ${type}, interlace ${body[12]})`);
      }
    } else if (tag === "IDAT") idat.push(body);
    else if (tag === "IEND") break;
    p += 12 + len;
  }
  const bpp = type === 6 ? 4 : 3;
  const raw = inflateSync(Buffer.concat(idat));
  const stride = w * bpp;
  const out = Buffer.alloc(w * h * bpp);
  let prev = Buffer.alloc(stride);
  for (let y = 0; y < h; y++) {
    const filter = raw[y * (stride + 1)];
    const line = raw.subarray(y * (stride + 1) + 1, y * (stride + 1) + 1 + stride);
    const cur = out.subarray(y * stride, (y + 1) * stride);
    line.copy(cur);
    for (let i = 0; i < stride; i++) {
      const a = i >= bpp ? cur[i - bpp] : 0, b = prev[i], c = i >= bpp ? prev[i - bpp] : 0;
      switch (filter) {
        case 1: cur[i] = (cur[i] + a) & 255; break;
        case 2: cur[i] = (cur[i] + b) & 255; break;
        case 3: cur[i] = (cur[i] + ((a + b) >> 1)) & 255; break;
        case 4: {
          const pa = Math.abs(b - c), pb = Math.abs(a - c), pc = Math.abs(a + b - 2 * c);
          cur[i] = (cur[i] + (pa <= pb && pa <= pc ? a : pb <= pc ? b : c)) & 255; break;
        }
      }
    }
    prev = cur;
  }
  return { width: w, height: h, bpp, data: out };
}

const lin = (c) => { c /= 255; return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4 };
const luma = (r, g, b) => 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
const ratio = (a, b) => { const [hi, lo] = a > b ? [a, b] : [b, a]; return (hi + 0.05) / (lo + 0.05) };
const hex = (c) => "#" + c.map((v) => v.toString(16).padStart(2, "0")).join("");

/* ── in-page collectors ────────────────────────────────────────────────── */
// One evaluate per page. Everything below runs in the browser.

const COLLECT = ({ target }) => {
  const sel = (e) => {
    if (!e || !e.tagName) return "?";
    const cls = typeof e.className === "string" && e.className.trim()
      ? "." + e.className.trim().split(/\s+/)
        .filter((c) => !/^(is-|has-|reveal|in-view|active$|visible$)/.test(c))
        .slice(0, 2).join(".")
      : "";
    return e.tagName.toLowerCase() + cls;
  };
  const path = (e) => { const p = []; for (let n = e; n && n.tagName && p.length < 3; n = n.parentElement) p.unshift(sel(n)); return p.join(" > ") };
  // Normalize every CSS Color 4 form through the same sRGB canvas Chromium
  // screenshots into. Regexes cannot parse `color(display-p3 …)`, percentages,
  // or alpha, and a contrast audit must not silently reinterpret any of them.
  const colourCanvas = document.createElement("canvas");
  colourCanvas.width = colourCanvas.height = 1;
  const colourCtx = colourCanvas.getContext("2d", { willReadFrequently: true });
  const rgba = (value) => {
    colourCtx.clearRect(0, 0, 1, 1);
    colourCtx.fillStyle = value;
    colourCtx.fillRect(0, 0, 1, 1);
    return [...colourCtx.getImageData(0, 0, 1, 1).data];
  };
  // Classes are presentation and truncated by `sel`; neither makes a stable
  // before/after identity. A structural nth-of-type path distinguishes repeated
  // labels and cards, so one moved "Read more" cannot hide behind another.
  const domKey = (e) => {
    const parts = [];
    for (let n = e; n && n.tagName; n = n.parentElement) {
      if (n.id) { parts.unshift(`#${n.id}`); break; }
      let nth = 1;
      for (let p = n.previousElementSibling; p; p = p.previousElementSibling) if (p.tagName === n.tagName) nth++;
      parts.unshift(`${n.tagName.toLowerCase()}:nth-of-type(${nth})`);
      if (n === document.body) break;
    }
    return parts.join(">");
  };
  const shown = (e) => {
    const cs = getComputedStyle(e);
    if (cs.display === "none" || cs.visibility === "hidden" || +cs.opacity < 0.05) return false;
    const r = e.getBoundingClientRect();
    return r.width > 1 && r.height > 1;
  };
  // The union of the glyphs and pictures an element actually paints. Element boxes
  // lie: a block spans its column whether its text fills it or not, so every
  // "overlap" and every "gap" measured off boxes is measuring the wrong thing.
  const ink = (e) => {
    let t = Infinity, b = -Infinity, l = Infinity, r = -Infinity, any = false;
    const walk = (n) => {
      if (n.nodeType === 3) {
        if (!n.textContent.trim()) return;
        const rng = document.createRange(); rng.selectNode(n);
        for (const q of rng.getClientRects()) {
          if (q.width < 1 || q.height < 1) continue;
          any = true; t = Math.min(t, q.top); b = Math.max(b, q.bottom); l = Math.min(l, q.left); r = Math.max(r, q.right);
        }
        return;
      }
      if (n.nodeType !== 1) return;
      if (!shown(n)) return;
      // Decoration is not ink. A 300px watermark glyph parked below its card's
      // bottom edge is a text node, and counting it drags the card's ink 50px
      // past where a reader sees the card end — which silently shrinks every gap
      // measured after it.
      if (n.getAttribute("aria-hidden") === "true") return;
      if (/^(IMG|SVG|VIDEO|CANVAS|PICTURE)$/.test(n.tagName)) {
        const q = n.getBoundingClientRect();
        any = true; t = Math.min(t, q.top); b = Math.max(b, q.bottom); l = Math.min(l, q.left); r = Math.max(r, q.right);
        return;
      }
      for (const k of n.childNodes) walk(k);
    };
    walk(e);
    return any ? { top: t, bottom: b, left: l, right: r } : null;
  };
  const runs = (e) => {
    const out = [];
    for (let ni = 0; ni < e.childNodes.length; ni++) {
      const n = e.childNodes[ni];
      if (n.nodeType !== 3 || n.textContent.trim().length < 2) continue;
      const rng = document.createRange(); rng.selectNode(n);
      let ri = 0;
      for (const q of rng.getClientRects()) {
        if (q.width > 3 && q.height > 3) out.push({ q, text: n.textContent.trim(), run: `${ni}:${ri}` });
        ri++;
      }
    }
    return out;
  };

  const de = document.documentElement;
  const vw = de.clientWidth;
  const out = {
    overflow: { scrollW: de.scrollWidth, clientW: vw, over: de.scrollWidth - vw },
    past: [], targets: [], fractional: [], strokes: [], images: [], headings: [],
    text: [], collisions: [], groups: [], containers: [], anchors: [],
  };

  /* geometry ------------------------------------------------------------ */
  for (const e of document.querySelectorAll("body *")) {
    if (!shown(e)) continue;
    const cs = getComputedStyle(e), r = e.getBoundingClientRect();
    if ((r.right > vw + 0.5 || r.left < -0.5) && cs.position !== "fixed"
      && cs.overflow === "visible" && cs.overflowX === "visible") {
      out.past.push({ el: path(e), left: +r.left.toFixed(2), right: +r.right.toFixed(2), vw });
    }
    for (const side of ["Top", "Right", "Bottom", "Left"]) {
      const w = parseFloat(cs[`border${side}Width`]);
      if (w > 0 && Math.abs(w - Math.round(w)) > 0.001) {
        out.fractional.push({ el: path(e), side: side.toLowerCase(), w, radius: cs.borderRadius });
      }
    }
    // strokes: a boxed edge is a container; a single side is a rule
    const wd = ["Top", "Right", "Bottom", "Left"].map((s) => parseFloat(cs[`border${s}Width`]));
    const cl = ["Top", "Right", "Bottom", "Left"].map((s) => cs[`border${s}Color`]);
    const sides = wd.filter(Boolean).length;
    for (let i = 0; i < 4; i++) {
      if (!wd[i] || /,\s*0\)$/.test(cl[i])) continue;
      const len = Math.round(i % 2 ? r.height : r.width);
      if (len < 24) continue;
      out.strokes.push({ el: path(e), side: ["top", "right", "bottom", "left"][i], w: wd[i], color: cl[i], boxed: sides === 4, len });
    }
    if (e.tagName === "HR") out.strokes.push({ el: path(e), side: "hr", w: 1, color: cs.color, boxed: false, len: Math.round(r.width) });
    for (const pe of ["::before", "::after"]) {
      const p = getComputedStyle(e, pe);
      if (p.content === "none") continue;
      const pw = parseFloat(p.width), ph = parseFloat(p.height);
      const horiz = pw > 40 && ph > 0 && ph <= 3, vert = ph > 40 && pw > 0 && pw <= 3;
      if (!horiz && !vert) continue;
      if (p.backgroundColor === "rgba(0, 0, 0, 0)" && !/gradient|url/.test(p.backgroundImage)) continue;
      out.strokes.push({ el: path(e) + pe, side: horiz ? "rule-h" : "rule-v", w: Math.min(pw, ph), color: p.backgroundColor, boxed: false, len: Math.round(Math.max(pw, ph)) });
    }
  }

  /* targets ------------------------------------------------------------- */
  for (const e of document.querySelectorAll("a,button,summary,[role=button],input,select,textarea,label[for]")) {
    if (!shown(e)) continue;
    const r = e.getBoundingClientRect();
    // A stretched link owns its positioned ancestor's box, so measure that instead.
    let box = { w: r.width, h: r.height }, via = "self";
    for (const pe of ["::after", "::before"]) {
      const p = getComputedStyle(e, pe);
      if (p.content === "none" || p.position !== "absolute") continue;
      if (parseFloat(p.top) !== 0 || parseFloat(p.left) !== 0) continue;
      let anc = e.parentElement;
      while (anc && getComputedStyle(anc).position === "static") anc = anc.parentElement;
      if (!anc) continue;
      const ar = anc.getBoundingClientRect();
      if (ar.width >= r.width && ar.height >= r.height) { box = { w: ar.width, h: ar.height }; via = "stretched"; }
    }
    const inSentence = !!e.closest("p, li, blockquote, dd, figcaption, .prose");
    out.targets.push({ el: path(e), w: +box.w.toFixed(1), h: +box.h.toFixed(1), via, inSentence, text: (e.textContent || "").trim().slice(0, 32) });
  }

  /* text roles ---------------------------------------------------------- */
  for (const e of document.querySelectorAll("body *")) {
    if (!shown(e)) continue;
    if (e.closest("[hidden],[aria-hidden=true]") || e.classList.contains("sr-only") || e.closest(".sr-only")) continue;
    const own = [...e.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim().length > 1);
    if (!own) continue;
    const cs = getComputedStyle(e);
    const size = parseFloat(cs.fontSize);
    const lh = cs.lineHeight === "normal" ? null : parseFloat(cs.lineHeight);
    const box = ink(e) ?? e.getBoundingClientRect();
    let fixed = false;
    for (let n = e; n; n = n.parentElement) if (getComputedStyle(n).position === "fixed") { fixed = true; break; }
    out.text.push({
      role: sel(e), tag: e.tagName.toLowerCase(),
      size: +size.toFixed(2),
      leading: lh === null ? null : +(lh / size).toFixed(3),
      tracking: +((parseFloat(cs.letterSpacing) || 0) / size).toFixed(4),
      weight: cs.fontWeight, color: cs.color, ink: rgba(cs.webkitTextFillColor || cs.color),
      family: cs.fontFamily.split(",")[0].replace(/["']/g, ""),
      transform: cs.textTransform,
      text: (e.textContent || "").trim().slice(0, 40),
      fixed,
      x: box.left + scrollX, y: box.top + scrollY, w: box.right - box.left, h: box.bottom - box.top,
    });
  }

  /* collisions ---------------------------------------------------------- */
  {
    const all = [];
    for (const e of document.querySelectorAll("body *")) {
      if (!shown(e)) continue;
      const cs = getComputedStyle(e);
      if (cs.position === "fixed") continue;                       // overlays are meant to overlap
      if (cs.webkitLineClamp && cs.webkitLineClamp !== "none") continue; // the rect overflows the visible box by design
      if (e.classList.contains("sr-only") || e.closest(".sr-only,[aria-hidden=true]")) continue;
      for (const { q, text } of runs(e)) all.push({ node: e, el: sel(e), text, q });
    }
    const hits = new Set();
    for (let i = 0; i < all.length; i++) {
      for (let j = i + 1; j < all.length; j++) {
        const a = all[i], b = all[j];
        if (a.node === b.node) continue;                            // an element's own line boxes
        if (a.node.contains(b.node) || b.node.contains(a.node)) continue;
        const ox = Math.min(a.q.right, b.q.right) - Math.max(a.q.left, b.q.left);
        const oy = Math.min(a.q.bottom, b.q.bottom) - Math.max(a.q.top, b.q.top);
        if (ox > 2 && oy > 2) hits.add(`${a.el} "${a.text.slice(0, 18)}" over ${b.el} "${b.text.slice(0, 18)}" (${ox.toFixed(0)}x${oy.toFixed(0)})`);
      }
    }
    out.collisions = [...hits];
  }

  /* proximity ----------------------------------------------------------- */
  // ONLY HOMOGENEOUS SIBLINGS. The law of proximity is a claim about a set of
  // like things — three cards, six rows, four links. A section holding a heading,
  // a grid and a button is a hierarchy, not a group, and comparing its child
  // spacing to the deepest gap anywhere inside it compares two different levels
  // and always "fails". Same tag and same class signature is the test.
  {
    const root = document.querySelector("main") || document.body;
    const hosts = new Set([root, ...root.querySelectorAll("*")]);
    for (const c of hosts) {
      const kids = [...c.children].filter(shown);
      if (kids.length < 3) continue;
      const sig = (e) => e.tagName + "|" + (typeof e.className === "string"
        ? e.className.split(/\s+/).filter((x) => x && !/^(is-|has-|reveal|in-view)/.test(x)).sort().join(".") : "");
      const sigs = new Set(kids.map(sig));
      if (sigs.size > 1) continue;
      const boxes = kids.map(ink);
      if (boxes.some((b) => !b)) continue;
      const between = [];
      for (let i = 1; i < boxes.length; i++) {
        if (boxes[i].top < boxes[i - 1].bottom - 2) { between.length = 0; break; } // side by side
        between.push(+(boxes[i].top - boxes[i - 1].bottom).toFixed(1));
      }
      if (between.length < 2) continue;
      // Block children only. An `em` and a `strong` in one paragraph land on
      // different lines, and the distance between their rects is a line break,
      // not a gap between two things.
      let within = 0, withinWhat = "";
      for (const k of kids) {
        const gk = [...k.children].filter((x) => shown(x) && !getComputedStyle(x).display.startsWith("inline"))
          .map((x) => ({ el: sel(x), b: ink(x) })).filter((x) => x.b);
        for (let i = 1; i < gk.length; i++) {
          if (gk[i].b.top < gk[i - 1].b.bottom - 2) continue;
          const g = gk[i].b.top - gk[i - 1].b.bottom;
          if (g > within) { within = g; withinWhat = gk[i].el; }
        }
      }
      if (within <= 0) continue;
      const minBetween = Math.min(...between);
      out.groups.push({ container: path(c), item: sel(kids[0]), n: kids.length, between: minBetween, within: +within.toFixed(1), withinWhat, ratio: +(minBetween / within).toFixed(2) });
    }
  }

  /* interiors ----------------------------------------------------------- */
  {
    for (const c of document.querySelectorAll("body *")) {
      if (!shown(c)) continue;
      const cs = getComputedStyle(c);
      const pt = parseFloat(cs.paddingTop), pl = parseFloat(cs.paddingLeft);
      if (pt < 8 || pl < 8) continue;
      const r = c.getBoundingClientRect();
      if (r.width < 120 || r.height < 60) continue;
      const framed = parseFloat(cs.borderTopWidth) > 0 || cs.backgroundColor !== "rgba(0, 0, 0, 0)";
      if (!framed) continue;
      // The loudest REAL type inside. A watermark glyph is 200px of decoration and
      // would otherwise decide this container's whole ratio.
      let lead = 0, leadEl = "";
      for (const k of c.querySelectorAll("*")) {
        if (!shown(k)) continue;
        if (k.getAttribute("aria-hidden") === "true" || k.closest("[aria-hidden=true]")) continue;
        const ks = getComputedStyle(k);
        if (ks.userSelect === "none" || ks.pointerEvents === "none") continue;
        const own = [...k.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim().length > 1);
        const s = parseFloat(ks.fontSize);
        if (own && s > lead) { lead = s; leadEl = sel(k); }
      }
      const first = [...c.children].filter(shown).map(ink).filter(Boolean).sort((a, b) => a.top - b.top)[0];
      out.containers.push({
        el: sel(c), parent: c.parentElement ? sel(c.parentElement) : "",
        pad: [pt, parseFloat(cs.paddingRight), parseFloat(cs.paddingBottom), pl],
        w: Math.round(r.width), top: +(r.top + scrollY).toFixed(1),
        lead: +lead.toFixed(1), leadEl,
        padPerLead: lead ? +(pt / lead).toFixed(3) : null,
        firstInk: first ? +(first.top - r.top).toFixed(1) : null,
      });
    }
  }

  /* headings, images, anchors ------------------------------------------- */
  // DOM order, not painted order: a visually-hidden landmark heading is real to a
  // screen reader, and skipping it invents a level jump that nobody has.
  for (const h of document.querySelectorAll("h1,h2,h3,h4,h5,h6")) {
    if (getComputedStyle(h).display === "none" || h.closest("[hidden],[aria-hidden=true]")) continue;
    out.headings.push({ level: +h.tagName[1], text: (h.textContent || "").trim().slice(0, 48) });
  }
  for (const img of document.querySelectorAll("img")) {
    const r = img.getBoundingClientRect();
    out.images.push({
      src: (img.currentSrc || img.src || "").split("/").pop(),
      alt: img.getAttribute("alt"), loading: img.getAttribute("loading"),
      decoding: img.getAttribute("decoding"), fetchpriority: img.getAttribute("fetchpriority"),
      width: img.getAttribute("width"), height: img.getAttribute("height"),
      srcset: !!img.getAttribute("srcset"), sizes: img.getAttribute("sizes"),
      natural: [img.naturalWidth, img.naturalHeight], box: [Math.round(r.width), Math.round(r.height)],
    });
  }
  // Stable anchors for a before/after proof: where a given run of text is painted.
  for (const e of document.querySelectorAll("body *")) {
    if (!shown(e)) continue;
    if (e.closest("[hidden],[aria-hidden=true]") || e.classList.contains("sr-only") || e.closest(".sr-only")) continue;
    for (const { q, text, run } of runs(e)) {
      out.anchors.push({ k: `${domKey(e)}|${run}|${text.slice(0, 24)}`, x: +q.left.toFixed(2), y: +(q.top + scrollY).toFixed(2) });
    }
  }
  return out;
};

/* ── drive the browser ─────────────────────────────────────────────────── */

const chromium = await loadChromium();
const browser = await launch(chromium);
const needsPixels = ARGS.checks.includes("contrast");
const pages = [];
const runFailures = [];

for (const route of ARGS.routes) {
  for (const width of ARGS.widths) {
    const ctx = await browser.newContext({
      viewport: { width, height: 1000 },
      deviceScaleFactor: needsPixels ? 2 : 1,
      reducedMotion: "reduce",
      bypassCSP: true,                       // the freeze below is an inline style
    });
    const page = await ctx.newPage();
    const errors = [];
    page.on("pageerror", (e) => errors.push(String(e).slice(0, 200)));
    page.on("console", (m) => {
      if (m.type() === "error" && !m.text().startsWith("Failed to load resource")) errors.push(m.text().slice(0, 200));
    });
    page.on("response", (r) => {
      const req = r.request();
      if (r.status() < 400 || req.resourceType() === "document" || /\/favicon(?:\.[^/]*)?$/.test(new URL(r.url()).pathname)) return;
      errors.push(`${req.resourceType()} HTTP ${r.status()} — ${r.url()}`.slice(0, 200));
    });
    page.on("requestfailed", (req) => {
      if (/\/favicon(?:\.[^/]*)?$/.test(new URL(req.url()).pathname)) return;
      errors.push(`${req.resourceType()} failed — ${req.url()}`.slice(0, 200));
    });
    const href = new URL(route, ARGS.base).href;
    const res = await page.goto(href, { waitUntil: "load" }).catch(() => null);
    if (!res) {
      const line = `${route} @${width}: unreachable (${href})`;
      console.error(`  ${line}`);
      runFailures.push(line);
      await ctx.close();
      continue;
    }
    if (!res.ok()) runFailures.push(`${route} @${width}: HTTP ${res.status()} (${href})`);
    await page.evaluate(() => document.fonts?.ready).catch(() => {});
    await page.addStyleTag({
      content: `*,*::before,*::after{animation-duration:.001s!important;animation-delay:0s!important;transition-duration:.001s!important}`,
    }).catch(() => {});
    // Walk the page so every IntersectionObserver reveal fires, then come back.
    await page.evaluate(async () => {
      for (let y = 0; y < document.body.scrollHeight; y += 400) { scrollTo(0, y); await new Promise((r) => setTimeout(r, 20)) }
      scrollTo(0, 0); await new Promise((r) => setTimeout(r, 300));
    });
    const data = await page.evaluate(COLLECT, { target: ARGS.target });
    data.route = route; data.width = width; data.status = res.status(); data.errors = errors;

    if (needsPixels) {
      const DPR = 2;
      // BANDS, NOT ONE FULL-PAGE CAPTURE. A tall page times a 2x scale factor runs
      // past Chromium's texture limit; the capture still comes back, just stitched
      // or scaled, and every coordinate silently stops pointing at the pixel it
      // names. Measuring a footer's contrast against the paper it is nowhere near
      // is the shape that bug takes. One viewport-sized capture per band of text
      // cannot exceed the limit and cannot drift.
      const VH = 1000;
      await page.addStyleTag({ content: `*{scroll-behavior:auto!important}` }).catch(() => {});
      // Photograph the ground, not the already-painted glyph. Inferring the
      // background from a crop containing both fails exactly when ink and ground
      // are similar: antialiasing makes them one cluster and low contrast vanishes.
      // Text fill is paint-only, so making it transparent preserves every box and
      // every coordinate collected above.
      await page.evaluate(() => {
        for (const e of document.querySelectorAll("body *")) {
          const own = [...e.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim().length > 1);
          if (!own) continue;
          e.style.setProperty("-webkit-text-fill-color", "transparent", "important");
          e.style.setProperty("text-shadow", "none", "important");
          e.style.setProperty("text-decoration-color", "transparent", "important");
        }
      });
      // Fixed chrome needs its own ground before it is hidden from later bands.
      // Otherwise a dark button in a fixed header is compared to the page paper
      // underneath the now-hidden header and becomes a confident false failure.
      const fixedText = data.text.filter((t) => t.fixed);
      const fixedPng = fixedText.length ? decodePNG(await page.screenshot()) : null;
      // A pinned header paints over the band it floats above, and the text under
      // it would be measured against the header's own ground. HIDE it, never
      // unpin it: `position: fixed` is out of flow, so `static` puts it back IN
      // and pushes the whole document down — after every y coordinate has already
      // been collected. That is a misalignment that looks exactly like a contrast
      // failure, and it reported paper-coloured labels as sitting on the footer.
      await page.evaluate(() => {
        for (const e of document.querySelectorAll("body *")) {
          const p = getComputedStyle(e).position;
          if (p === "fixed") { e.setAttribute("data-audit-hidden", "1"); e.style.visibility = "hidden" }
          else if (p === "sticky") { e.setAttribute("data-audit-unstuck", "1"); e.style.position = "static" }
        }
      });
      const bands = new Map();
      for (const t of data.text.filter((row) => !row.fixed)) {
        const b = Math.floor(t.y / VH);
        if (!bands.has(b)) bands.set(b, []);
        bands.get(b).push(t);
      }
      data.contrast = [];
      const measure = (list, png, shot) => {
        for (const t of list) {
          const x0 = Math.max(0, Math.round(t.x * DPR)), y0 = Math.max(0, Math.round((t.y - shot) * DPR));
          const x1 = Math.min(png.width, Math.round((t.x + t.w) * DPR)), y1 = Math.min(png.height, Math.round((t.y - shot + t.h) * DPR));
          if (x1 - x0 < 4 || y1 - y0 < 4 || y0 < 0) continue;
          const hist = new Map();
          let n = 0;
          for (let y = y0; y < y1; y++) for (let x = x0; x < x1; x++) {
            const i = (png.width * y + x) * png.bpp;
            const k = (png.data[i] << 16) | (png.data[i + 1] << 8) | png.data[i + 2];
            hist.set(k, (hist.get(k) || 0) + 1); n++;
          }
          if (n < 60) continue;
          // THE INK IS KNOWN — it is the element's computed `color`. The screenshot
          // above contains ground only. Use its low-contrast fifth percentile rather
          // than one worst pixel (grain/noise) or its mode (which misses a bad patch
          // under text over a photograph).
          const declared = t.ink;
          if (!declared || declared.length !== 4 || declared[3] === 0) continue;
          const ranked = [...hist].map(([k, count]) => {
            const px = [(k >> 16) & 255, (k >> 8) & 255, k & 255];
            const alpha = declared[3] / 255;
            const actual = declared.slice(0, 3).map((v, i) => Math.round(v * alpha + px[i] * (1 - alpha)));
            return { px, actual, count, contrast: ratio(luma(...actual), luma(...px)) };
          }).sort((a, b) => a.contrast - b.contrast);
          const percentile = Math.max(1, Math.ceil(n * 0.05));
          let seen = 0, bg = null, ink = null;
          for (const row of ranked) {
            seen += row.count;
            if (seen >= percentile) { bg = row.px; ink = row.actual; break; }
          }
          if (!bg || !ink) continue;
          const Lbg = luma(...bg);
          const r = ratio(luma(...ink), Lbg);
          const large = t.size >= 24 || (t.size >= 18.66 && +t.weight >= 700);
          data.contrast.push({
            role: t.role, text: t.text, size: t.size, weight: t.weight,
            ink: hex(ink), bg: hex(bg), ratio: +r.toFixed(2),
            need: ARGS.aaa ? (large ? 4.5 : 7) : (large ? 3 : 4.5),
            large,
            // An emoji paints its own colours and ignores `color`, so the pair above
            // describes nothing. 1.4.3 does not cover it either.
            colourGlyph: /\p{Extended_Pictographic}/u.test(t.text) && t.text.replace(/\p{Extended_Pictographic}|\s/gu, "").length < 2,
          });
        }
      };
      if (fixedPng) measure(fixedText, fixedPng, 0);
      for (const [b, list] of [...bands].sort((a, b2) => a[0] - b2[0])) {
        const top = b * VH;
        await page.evaluate((y) => scrollTo(0, y), top);
        await page.waitForTimeout(60);
        const shot = await page.evaluate(() => window.scrollY);
        measure(list, decodePNG(await page.screenshot()), shot);
      }
      await page.evaluate(() => {
        for (const e of document.querySelectorAll("[data-audit-unstuck]")) e.style.position = "";
        for (const e of document.querySelectorAll("[data-audit-hidden]")) e.style.visibility = "";
      });
    }
    pages.push(data);
    await ctx.close();
  }
}
await browser.close();

/* ── report ────────────────────────────────────────────────────────────── */

const P = (...a) => { if (!ARGS.quiet) console.log(...a) };
const findings = [];
const add = (check, severity, line, detail) => findings.push({ check, severity, line, ...detail });
const dedupe = (rows, key) => { const m = new Map(); for (const r of rows) { const k = key(r); if (!m.has(k)) m.set(k, r) } return [...m.values()] };

for (const line of runFailures) add("runtime", "high", line);

if (ARGS.checks.includes("geometry")) {
  P("\n── geometry ────────────────────────────────────────────────");
  for (const p of pages) {
    if (p.overflow.over > 0) add("geometry", "high", `${p.route} @${p.width}: page scrolls ${p.overflow.over}px sideways`);
    for (const e of p.errors) add("geometry", "high", `${p.route} @${p.width}: console error — ${e}`);
  }
  // Bleeding past the viewport is usually the design. It is a note so it can be
  // read once and dismissed, and it is deduped to the element so a full-bleed
  // portrait does not report itself at every width.
  for (const r of dedupe(pages.flatMap((p) => p.past.map((x) => ({ ...x, route: p.route, width: p.width }))), (x) => x.el)) {
    add("geometry", "note", `${r.route} @${r.width}: ${r.el} spans ${r.left}..${r.right} of ${r.vw} (bleed, or an overflow nobody meant)`);
  }
  const tooSmall = dedupe(
    pages.filter((p) => p.width <= 820).flatMap((p) => p.targets
      .filter((t) => !t.inSentence && (t.w < ARGS.target || t.h < ARGS.target))
      .map((t) => ({ ...t, route: p.route }))),
    (t) => t.el + t.text);
  for (const t of tooSmall.sort((a, b) => Math.min(a.w, a.h) - Math.min(b.w, b.h))) {
    add("geometry", t.h < 24 || t.w < 24 ? "high" : "medium",
      `${t.w}x${t.h} target (${t.via}) — ${t.el} "${t.text}"  [${t.route}]`);
  }
  for (const f of dedupe(pages.flatMap((p) => p.fractional), (x) => x.el + x.side + x.w)) {
    add("geometry", "medium", `${f.w}px ${f.side} border on ${f.el} (radius ${f.radius}) — half-pixel strokes render as a cut ring`);
  }
  for (const i of dedupe(pages.flatMap((p) => p.images), (x) => x.src)) {
    const over = i.natural[0] && i.box[0] ? i.natural[0] / (i.box[0] * 2) : 0;
    if (over > 1.3) add("geometry", "low", `${i.src}: ${i.natural.join("x")} source for a ${i.box.join("x")} box — ${over.toFixed(1)}x oversampled at 2dpr, no srcset`);
    if (i.alt === null) add("geometry", "high", `${i.src}: no alt attribute at all (use alt="" if decorative)`);
    if (!i.width || !i.height) add("geometry", "medium", `${i.src}: no width/height attributes — reserves no space, shifts layout`);
  }
  // Structure is a property of the route, not of the width it is read at.
  for (const p of dedupe(pages, (x) => x.route)) {
    const lv = p.headings.map((h) => h.level);
    const h1 = lv.filter((x) => x === 1).length;
    if (h1 !== 1) add("geometry", "medium", `${p.route}: ${h1} h1 elements`);
    for (let i = 1; i < lv.length; i++) if (lv[i] > lv[i - 1] + 1) {
      add("geometry", "medium", `${p.route}: heading jumps h${lv[i - 1]} → h${lv[i]} at "${p.headings[i].text}"`);
      break;
    }
  }
}

if (ARGS.checks.includes("contrast")) {
  P("\n── contrast (measured off painted pixels) ──────────────────");
  const rows = pages.flatMap((p) => (p.contrast ?? []).map((c) => ({ ...c, route: p.route, width: p.width })));
  const worst = new Map();
  for (const c of rows) { const k = `${c.role}|${c.size}`; if (!worst.has(k) || c.ratio < worst.get(k).ratio) worst.set(k, c) }
  const bad = [...worst.values()].filter((c) => c.ratio < c.need && !c.colourGlyph).sort((a, b) => a.ratio - b.ratio);
  P(`  ${worst.size} distinct text roles measured, ${bad.length} under target`);
  for (const c of bad) {
    add("contrast", c.ratio < c.need * 0.7 ? "high" : "medium",
      `${c.ratio}:1 (needs ${c.need}) — ${c.size}px ${c.role}, ${c.ink} on ${c.bg}  [${c.route}@${c.width}] "${c.text}"`);
  }
}

if (ARGS.checks.includes("collision")) {
  P("\n── collision (glyph over glyph) ────────────────────────────");
  const hits = dedupe(pages.flatMap((p) => p.collisions.map((c) => ({ c, route: p.route, width: p.width }))), (x) => x.c);
  P(hits.length ? `  ${hits.length} overlapping text runs` : "  none");
  for (const h of hits) add("collision", "high", `${h.route} @${h.width}: ${h.c}`);
}

if (ARGS.checks.includes("proximity")) {
  P("\n── proximity + strokes ─────────────────────────────────────");
  const groups = dedupe(pages.flatMap((p) => p.groups.map((g) => ({ ...g, route: p.route, width: p.width }))), (g) => g.container + g.width)
    .filter((g) => g.ratio < 1.5).sort((a, b) => a.ratio - b.ratio);
  for (const g of groups) {
    add("proximity", g.ratio < 1 ? "high" : "medium",
      `ratio ${g.ratio} — ${g.container} separates its ${g.n} children by ${g.between}px but holds ${g.within}px inside one (${g.withinWhat})  [${g.route}@${g.width}]`);
  }
  const rules = dedupe(pages.flatMap((p) => p.strokes.filter((s) => !s.boxed).map((s) => ({ ...s, route: p.route }))), (s) => s.el + s.side + s.w);
  const boxed = new Set(pages.flatMap((p) => p.strokes.filter((s) => s.boxed).map((s) => s.el))).size;
  P(`  ${rules.length} rule(s) — a single-sided stroke; ${boxed} boxed container edges not listed`);
  for (const s of rules.sort((a, b) => b.len - a.len)) {
    add("proximity", "note", `${s.w}px ${s.side} ${s.color} on ${s.el} (${s.len}px long)  [${s.route}]`);
  }
}

if (ARGS.checks.includes("type")) {
  P("\n── type scale (one role, one answer) ───────────────────────");
  const roles = new Map();
  for (const p of pages) for (const t of p.text) {
    const k = `${t.role}|${t.size}`;
    if (!roles.has(k)) roles.set(k, { ...t, route: p.route, width: p.width });
  }
  // A NEAR MISS IS THE SIGNAL, NOT A DIFFERENCE. Two roles set at the same size in
  // the same face at the same weight and case are doing the same job, and if their
  // leading or tracking differ by a hundredth that is a typed value, not a decision
  // anybody made. A large difference at the same size is usually two real roles —
  // a lede is not a body paragraph — so it is left alone.
  // `em`, `strong`, a bare `span` — text INSIDE a role, not a role. An italic
  // opening by a hundredth against the body it sits in is an optical correction
  // every type designer makes, and comparing it to its own paragraph is noise.
  const INLINE = /^(em|strong|b|i|u|s|small|code|kbd|abbr|span|a|sup|sub|mark|time)$/;
  const bucket = new Map();
  for (const t of roles.values()) {
    if (INLINE.test(t.tag) && !t.role.includes(".")) continue;
    const k = `${t.family}|${t.transform}|${t.weight}|${t.size.toFixed(1)}`;
    if (!bucket.has(k)) bucket.set(k, []);
    bucket.get(k).push(t);
  }
  // One line per bucket: what most roles at this rung say, and who disagrees by a
  // hair. Reporting every pair turns one outlier among eight peers into eight
  // findings and buries the one thing worth reading.
  const odd = (list, pick, tol, label, severity) => {
    const vals = list.map(pick).filter((v) => v !== null);
    if (vals.length < 3) return;
    const tally = new Map();
    for (const v of vals) tally.set(v, (tally.get(v) ?? 0) + 1);
    const [main, mainN] = [...tally].sort((a, b) => b[1] - a[1])[0];
    if (mainN < 2) return;
    const strays = list.filter((t) => {
      const v = pick(t);
      return v !== null && v !== main && Math.abs(v - main) <= tol && (label !== "tracking" || (Math.abs(v) > 0.005 && Math.abs(main) > 0.005));
    });
    if (!strays.length) return;
    const [face, tf, wt, size] = list[0]._k.split("|");
    add("type", severity,
      `${size}px ${face}${tf === "none" ? "" : " " + tf} w${wt}: ${mainN} roles set ${label} ${main}, ` +
      strays.map((t) => `${t.role} sets ${pick(t)}`).join(" and ") +
      ` — under ${tol} apart, which is a typed value rather than a decision`);
  };
  for (const [k, list] of bucket) {
    for (const t of list) t._k = k;
    odd(list, (t) => t.leading, 0.03, "leading", "medium");
    odd(list, (t) => t.tracking, 0.015, "tracking", "low");
  }
}

if (ARGS.checks.includes("interior")) {
  P("\n── interiors ───────────────────────────────────────────────");
  // Same container class, same row: does every one start reading on the same line?
  for (const p of pages) {
    const rows = new Map();
    for (const c of p.containers) {
      if (c.firstInk === null) continue;
      const k = `${c.parent}|${c.el}|${Math.round(c.top)}`;
      if (!rows.has(k)) rows.set(k, []);
      rows.get(k).push(c);
    }
    for (const [k, list] of rows) {
      if (list.length < 2) continue;
      const offs = list.map((c) => c.firstInk);
      const spread = Math.max(...offs) - Math.min(...offs);
      if (spread > 2) {
        add("interior", spread > 12 ? "high" : "medium",
          `${list[0].el} — ${list.length} in one row start reading ${spread.toFixed(1)}px apart  [${p.route}@${p.width}]`);
      }
    }
  }
  // Does the inset scale with the type it holds?
  // Variants of one component — `.card` and `.card.feature` — are one tier with two
  // volumes, so their inset should be one ratio of the type they hold. Two unrelated
  // components are not comparable and are not compared: the base class has to match.
  const tiers = new Map();
  for (const p of pages) for (const c of p.containers) {
    if (!c.padPerLead || c.lead < 12) continue;
    const base = c.el.split(".").slice(0, 2).join(".");
    const k = `${base}|${p.width}`;
    if (!tiers.has(k)) tiers.set(k, []);
    tiers.get(k).push(c);
  }
  for (const [k, list] of tiers) {
    const variants = dedupe(list, (c) => c.el);
    if (variants.length < 2) continue;
    const rs = variants.map((c) => c.padPerLead);
    const lo = Math.min(...rs), hi = Math.max(...rs);
    if (hi / lo > 1.35) {
      const tight = variants.find((c) => c.padPerLead === lo), loose = variants.find((c) => c.padPerLead === hi);
      add("interior", "medium",
        `inset does not follow type: ${tight.el} sets ${tight.lead}px inside ${tight.pad[0]}px (${lo}) while ${loose.el} sets ${loose.lead}px inside ${loose.pad[0]}px (${hi})  [${k.split("|")[1]}px]`);
    }
  }
}

/* ── baseline proof ────────────────────────────────────────────────────── */

const anchors = {};
for (const p of pages) {
  const m = {};
  for (const a of p.anchors) if (!(a.k in m)) m[a.k] = [a.x, a.y];
  anchors[`${p.route}@${p.width}`] = m;
}

if (ARGS.baseline) {
  P("\n── against the baseline ────────────────────────────────────");
  if (!existsSync(ARGS.baseline)) fail(`baseline not found: ${ARGS.baseline}`);
  let before;
  try { before = JSON.parse(readFileSync(ARGS.baseline, "utf8")).anchors ?? {}; }
  catch { fail(`baseline is not valid audit JSON: ${ARGS.baseline}`); }
  const beforePages = new Set(Object.keys(before));
  const nowPages = new Set(Object.keys(anchors));
  const missingPages = [...beforePages].filter((p) => !nowPages.has(p));
  const extraPages = [...nowPages].filter((p) => !beforePages.has(p));
  if (missingPages.length || extraPages.length) {
    add("baseline", "high",
      `page set differs — missing: ${missingPages.join(", ") || "none"}; new: ${extraPages.join(", ") || "none"}`);
  }
  let same = 0, moved = 0, gone = 0, fresh = 0;
  const shifts = [];
  for (const [page, now] of Object.entries(anchors)) {
    const then = before[page];
    if (!then) continue;
    for (const [k, v] of Object.entries(now)) {
      if (!(k in then)) { fresh++; continue }
      const dx = v[0] - then[k][0], dy = v[1] - then[k][1];
      if (Math.abs(dx) < 0.5 && Math.abs(dy) < 0.5) same++;
      else { moved++; shifts.push(`${page} ${k} moved ${dx.toFixed(1)},${dy.toFixed(1)}`) }
    }
    for (const k of Object.keys(then)) if (!(k in now)) gone++;
  }
  P(`  ${same} text runs unchanged, ${moved} moved, ${fresh} new, ${gone} gone`);
  for (const s of shifts.slice(0, 40)) P(`    ${s}`);
  if (shifts.length > 40) P(`    …and ${shifts.length - 40} more`);
}

/* ── output ────────────────────────────────────────────────────────────── */

const order = { high: 0, medium: 1, low: 2, note: 3 };
findings.sort((a, b) => order[a.severity] - order[b.severity]);
if (!ARGS.quiet) {
  console.log("\n════ findings ══════════════════════════════════════════════");
  if (!findings.length) console.log("  nothing measured came back wrong");
  for (const f of findings) console.log(`  ${f.severity.toUpperCase().padEnd(6)} ${f.check.padEnd(10)} ${f.line}`);
  const n = (s) => findings.filter((f) => f.severity === s).length;
  console.log(`\n  ${n("high")} high · ${n("medium")} medium · ${n("low")} low · ${n("note")} note` +
    `   (${pages.length}/${ARGS.routes.length * ARGS.widths.length} route-widths measured)`);
}
if (ARGS.json) {
  writeFileSync(ARGS.json, JSON.stringify({ base: ARGS.base, checks: ARGS.checks, findings, anchors, failures: runFailures, pages: pages.map((p) => ({ route: p.route, width: p.width, status: p.status })) }, null, 1));
  if (!ARGS.quiet) console.log(`\n  written to ${ARGS.json}`);
}
process.exit(findings.some((f) => f.severity === "high") ? 1 : 0);
