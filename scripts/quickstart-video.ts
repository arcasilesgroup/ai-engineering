#!/usr/bin/env bun
// scripts/quickstart-video.ts — analyzes the real VHS recording of quickstart.tape, renders
// 1920x1080 brand graphics (intro card, stage chrome, burned-in captions, pixel-locked
// non-colour-only highlights, closing card) from brand/tokens.json, and writes the deterministic
// ffmpeg filtergraph consumed by .github/assets/tapes/quickstart-video.sh.
//
// Nothing here invents a CLI line or a count: every number shown in a caption, callout badge,
// or poster manifest is parsed straight from the recorded raw.ascii and verified against the
// rendered video pixels.

import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import type { Locator } from "playwright-core";
import { colour } from "./readme-figures.ts";

const ROOT = join(import.meta.dir, "..");
const MARK_DATA_URI = `data:image/svg+xml;base64,${readFileSync(join(ROOT, "brand", "mark.svg")).toString("base64")}`;

const CANVAS_W = 1920;
const CANVAS_H = 1080;
const TERM_X = 94;
const TERM_Y = 132;
const TERM_W = 1732;
const TERM_H = 776;
const FPS = 25;

// Pacing budgets (seconds) — tuned so every panel and burned-in caption clears comfortable
// human reading speed (~2.5-3.2 words/sec plus scan time) before any cut.
const INTRO_DURATION = 4.2;
const OUTRO_DURATION = 5.4;
const CARD_XFADE = 0.35;
const ACT_XFADE = 0.25;

const ACT1_HOLD_CONTRACT = 4.2;
const ACT1_HOLD_HOOKS = 4.2;
const ACT2_HOLD_OVERVIEW = 3.6;
const ACT2_HOLD_DENY = 5.6;
const ACT2_HOLD_VERIFIED = 5.6;
const ACT3_HOLD_LANES = 5.6;
const ACT4_HOLD_SURFACES = 5.8;

const FONTS = "https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@92,400;92,600;92,700;92,800&family=JetBrains+Mono:wght@500;600;700&display=block";
const SANS = "'Archivo', sans-serif";
const MONO = "'JetBrains Mono', monospace";

const PALETTE = {
  field: colour("black"),
  raised: colour("gray.dark4"),
  surface3: colour("gray.dark3"),
  ink: colour("white"),
  body: colour("gray.light2"),
  muted: colour("gray.light1"),
  border: colour("gray.base"),
  hairline: `${colour("gray.base")}55`,
  accent: colour("green.base"),
  accentText: colour("green.light1"),
  accentDeep: colour("green.dark2"),
  onAccent: colour("black"),
  bad: colour("red.light1"),
  badText: colour("red.light2"),
  warn: colour("yellow.base"),
  grid: `${colour("white")}0D`,
  glow: `${colour("green.base")}16`,
  band: `${colour("white")}08`,
} as const;

export type QuickstartFacts = {
  version: string;
  width: number;
  height: number;
  fps: number;
  durationSeconds: number;
  rulesCount: number;
  rulesLines: number;
  mirrorsOk: number;
  mirrorsTotal: number;
  canonVerified: number;
  canonTotal: number;
  lockAssets: number;
  denyMs: number;
  receiptP50Ms: number;
  receiptP95Ms: number;
  checksTotal: number;
  checksOk: number;
  checksWarn: number;
  checksFail: number;
  branch: string;
  baseBranch: string;
  activeLanes: number;
  maxLanes: number;
  uncommitted: number;
  surfacesAfterAdd: [string, string];
  mirrorTargets: number;
};

type ParsedAscii = {
  facts: Omit<QuickstartFacts, "width" | "height" | "fps" | "durationSeconds">;
  doctorLinesAfterPipe: string[];
  denyLineIndex: number;
  checksLineIndex: number;
  verifiedLineIndex: number;
};

type ActBounds = {
  startFrame: number;
  outputFrame: number;
  settledFrame: number;
  endFrame: number;
};

type PixelBand = {
  top: number;
  bottom: number;
  maxX: number;
};

const escapeHtml = (text: string): string =>
  text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

function withAccent(text: string, accent: string): string {
  const at = text.indexOf(accent);
  if (at < 0) throw new Error(`accent "${accent}" is not in "${text}"`);
  return `${escapeHtml(text.slice(0, at))}<em>${escapeHtml(accent)}</em>${escapeHtml(text.slice(at + accent.length))}`;
}

function mustMatch(text: string, pattern: RegExp, label: string): RegExpMatchArray {
  const match = text.match(pattern);
  if (!match) throw new Error(`raw.ascii missing expected ${label} (${pattern})`);
  return match;
}

/** Parse every real CLI count and the exact doctor output line order from VHS raw.ascii. */
function parseAscii(asciiText: string): ParsedAscii {
  const frames = asciiText
    .split(/^─+$/m)
    .map((chunk) => chunk.trimEnd())
    .filter((chunk) => chunk.trim().length > 0);

  const findLast = (predicate: (frame: string) => boolean, label: string): string => {
    for (let index = frames.length - 1; index >= 0; index -= 1) {
      const candidate = frames[index];
      if (candidate !== undefined && predicate(candidate)) return candidate;
    }
    throw new Error(`raw.ascii did not contain settled frame for ${label}`);
  };

  const initFrame = findLast(
    (frame) => frame.includes("Your contract files") && frame.includes("ai-eng.lock") && frame.includes("Nothing committed."),
    "ai-eng init",
  );
  const doctorFrame = findLast(
    (frame) => frame.includes("doctor · my-app · ai-eng") && frame.includes("Chain verified."),
    "ai-eng doctor",
  );
  const workFrame = findLast(
    (frame) => frame.includes("active lanes:") && frame.includes("feat/auth"),
    "ai-eng work",
  );
  const configFrame = findLast(
    (frame) => frame.includes("config · my-app · ai-eng") && frame.includes("Surfaces changed") && frame.includes("Mirrors verified"),
    "ai-eng config --add cursor",
  );

  const version = mustMatch(doctorFrame, /doctor · my-app · ai-eng (\d+\.\d+\.\d+)/, "version")[1] as string;
  const lockAssets = Number(mustMatch(initFrame, /ai-eng\.lock · (\d+) assets with sha256/, "lock asset count")[1]);
  const rulesMatch = mustMatch(doctorFrame, /AGENTS\.md · (\d+) rules · (\d+) lines/, "AGENTS.md rules");
  const mirrorsMatch = mustMatch(doctorFrame, /mirrors · (\d+)\/(\d+) mirrors carry linked skills/, "mirrors");
  const canonMatch = mustMatch(doctorFrame, /canon · (\d+)\/(\d+) files verified/, "canon");
  const denyMs = Number(mustMatch(doctorFrame, /chain test · adversarial payload \(git commit -n\) → DENY in (\d+)ms/, "live deny latency")[1]);
  const receiptsMatch = mustMatch(doctorFrame, /p50 (\d+)ms · p95 (\d+)ms/, "receipt latency");
  const checksMatch = mustMatch(doctorFrame, /(\d+) checks: (\d+) OK · (\d+) WARN · (\d+) FAIL/, "doctor checks summary");
  const workHeader = mustMatch(workFrame, /my-app · base ([A-Za-z0-9._/-]+) · \d+ active/, "work header");
  const workLane = mustMatch(workFrame, /active\s+([A-Za-z0-9._/-]+)\s+\d+\s+d\s+checked out · (\d+) uncommitted/, "work lane");
  const workActive = mustMatch(workFrame, /active lanes:\s+(\d+)\/(\d+)/, "active lanes");
  const configSurfaces = mustMatch(configFrame, /2 enabled:\s+([a-z0-9-]+),\s+([a-z0-9-]+)/, "enabled surfaces");
  const configTargets = Number(mustMatch(configFrame, /✓\s+(\d+) targets/, "mirror targets")[1]);

  // Lines that carry visible characters past the left vertical `│` column (col >= 3),
  // matching the x >= 46 horizontal pixel scan of the rendered doctor frame 1-to-1.
  const doctorLinesAfterPipe = doctorFrame
    .split("\n")
    .filter((line) => line.slice(3).trim().length > 0);

  const denyLineIndex = doctorLinesAfterPipe.findIndex((line) => line.includes("chain test") && line.includes("DENY in"));
  const checksLineIndex = doctorLinesAfterPipe.findIndex((line) => /\d+ checks:/.test(line));
  const verifiedLineIndex = doctorLinesAfterPipe.findIndex((line) => line.includes("Chain verified."));
  if (denyLineIndex < 0 || checksLineIndex < 0 || verifiedLineIndex < 0) {
    throw new Error(`Could not locate highlight lines in doctor output (deny=${denyLineIndex}, checks=${checksLineIndex}, verified=${verifiedLineIndex})`);
  }

  return {
    facts: {
      version,
      rulesCount: Number(rulesMatch[1]),
      rulesLines: Number(rulesMatch[2]),
      mirrorsOk: Number(mirrorsMatch[1]),
      mirrorsTotal: Number(mirrorsMatch[2]),
      canonVerified: Number(canonMatch[1]),
      canonTotal: Number(canonMatch[2]),
      lockAssets,
      denyMs,
      receiptP50Ms: Number(receiptsMatch[1]),
      receiptP95Ms: Number(receiptsMatch[2]),
      checksTotal: Number(checksMatch[1]),
      checksOk: Number(checksMatch[2]),
      checksWarn: Number(checksMatch[3]),
      checksFail: Number(checksMatch[4]),
      branch: workLane[1] as string,
      baseBranch: workHeader[1] as string,
      activeLanes: Number(workActive[1]),
      maxLanes: Number(workActive[2]),
      uncommitted: Number(workLane[2]),
      surfacesAfterAdd: [configSurfaces[1] as string, configSurfaces[2] as string],
      mirrorTargets: configTargets,
    },
    doctorLinesAfterPipe,
    denyLineIndex,
    checksLineIndex,
    verifiedLineIndex,
  };
}

/** Detect the exact start, output, and settled frame of all four recorded acts in raw.mp4. */
function analyzeActs(rawMp4: string): { acts: ActBounds[]; totalFrames: number } {
  const probeW = 433;
  const probeH = 194;
  const proc = Bun.spawnSync([
    "ffmpeg",
    "-v",
    "error",
    "-i",
    rawMp4,
    "-vf",
    `scale=${probeW}:${probeH}:flags=area`,
    "-f",
    "rawvideo",
    "-pix_fmt",
    "rgb24",
    "pipe:1",
  ], { maxBuffer: 512 * 1024 * 1024 });
  if (!proc.success) throw new Error(`ffmpeg frame scan failed: ${proc.stderr.toString()}`);

  const raw = proc.stdout;
  const frameBytes = probeW * probeH * 3;
  const totalFrames = Math.floor(raw.length / frameBytes);
  if (totalFrames < 50) throw new Error(`raw.mp4 too short (${totalFrames} frames)`);

  // Background is #001E2B = (0, 30, 43). Body starts cleanly below row 0 and cursor (y >= 60px = 15 in 1/4 scale).
  const bodyPixels: number[] = [];
  const bodyDiffs: number[] = [];
  const bodyStartOffset = 15 * probeW * 3;

  for (let frame = 0; frame < totalFrames; frame += 1) {
    const base = frame * frameBytes;
    const prevBase = (frame - 1) * frameBytes;
    let nonBg = 0;
    let changed = 0;
    for (let offset = bodyStartOffset; offset < frameBytes; offset += 3) {
      const r = raw[base + offset] ?? 0;
      const g = raw[base + offset + 1] ?? 0;
      const b = raw[base + offset + 2] ?? 0;
      if (Math.abs(r) + Math.abs(g - 30) + Math.abs(b - 43) > 36) nonBg += 1;
      if (frame > 0) {
        const pr = raw[prevBase + offset] ?? 0;
        const pg = raw[prevBase + offset + 1] ?? 0;
        const pb = raw[prevBase + offset + 2] ?? 0;
        if (Math.abs(r - pr) + Math.abs(g - pg) + Math.abs(b - pb) > 24) changed += 1;
      }
    }
    bodyPixels.push(nonBg);
    bodyDiffs.push(changed);
  }

  // An act begins at frame 0 and each subsequent transition from non-empty body back to blank body.
  const starts: number[] = [0];
  for (let frame = 1; frame < totalFrames; frame += 1) {
    if ((bodyPixels[frame] ?? 0) === 0 && (bodyPixels[frame - 1] ?? 0) > 20) {
      starts.push(frame);
    }
  }
  if (starts.length !== 4) {
    throw new Error(`Expected 4 acts in raw.mp4, detected ${starts.length} starts at frames [${starts.join(", ")}]`);
  }

  const acts: ActBounds[] = starts.map((startFrame, index) => {
    const nextStart = starts[index + 1] ?? totalFrames;
    const endFrame = nextStart - 1;
    let outputFrame = -1;
    for (let frame = startFrame; frame <= endFrame; frame += 1) {
      if ((bodyPixels[frame] ?? 0) > 15) {
        outputFrame = frame;
        break;
      }
    }
    if (outputFrame < 0) throw new Error(`Act ${index + 1} produced no visible body output`);
    // Last significant change in body pixels (threshold > 25 ignores single-cell cursor blink).
    let settledFrame = outputFrame;
    for (let frame = outputFrame; frame <= endFrame; frame += 1) {
      if ((bodyDiffs[frame] ?? 0) > 25) settledFrame = frame;
    }
    settledFrame = Math.min(endFrame, settledFrame + 3);
    return { startFrame, outputFrame, settledFrame, endFrame };
  });

  return { acts, totalFrames };
}

/** Measure exact pixel Y-bands and rightmost X of every text line in the settled doctor frame. */
function measureDoctorBands(rawMp4: string, settledFrame: number, expectedCount: number): PixelBand[] {
  const proc = Bun.spawnSync([
    "ffmpeg",
    "-v",
    "error",
    "-i",
    rawMp4,
    "-vf",
    `select=eq(n\\,${settledFrame})`,
    "-fps_mode",
    "passthrough",
    "-frames:v",
    "1",
    "-f",
    "rawvideo",
    "-pix_fmt",
    "rgb24",
    "pipe:1",
  ], { maxBuffer: 16 * 1024 * 1024 });
  if (!proc.success) throw new Error(`ffmpeg doctor frame extraction failed: ${proc.stderr.toString()}`);

  const buf = proc.stdout;
  if (buf.length < TERM_W * TERM_H * 3) {
    throw new Error(`Unexpected doctor frame byte length: ${buf.length}`);
  }

  // Skip columns 0..49 where the continuous vertical `│` box pipe and empty `$ ` cursor live.
  const scanStartX = 50;
  const rowActive: boolean[] = [];
  const rowMaxX: number[] = [];

  for (let y = 0; y < TERM_H; y += 1) {
    let activeCount = 0;
    let maxX = 0;
    const rowBase = y * TERM_W * 3;
    for (let x = scanStartX; x < TERM_W; x += 1) {
      const idx = rowBase + x * 3;
      const r = buf[idx] ?? 0;
      const g = buf[idx + 1] ?? 0;
      const b = buf[idx + 2] ?? 0;
      if (Math.abs(r) + Math.abs(g - 30) + Math.abs(b - 43) > 32) {
        activeCount += 1;
        if (x > maxX) maxX = x;
      }
    }
    rowActive.push(activeCount >= 2 && maxX >= 90);
    rowMaxX.push(maxX);
  }

  const bands: PixelBand[] = [];
  let inBand = false;
  let top = 0;
  let maxX = 0;
  for (let y = 0; y < TERM_H; y += 1) {
    if (rowActive[y]) {
      if (!inBand) {
        inBand = true;
        top = y;
        maxX = rowMaxX[y] ?? 0;
      } else if ((rowMaxX[y] ?? 0) > maxX) {
        maxX = rowMaxX[y] ?? 0;
      }
    } else if (inBand) {
      // Allow a 1px descender/dot gap inside the same glyph row without bridging adjacent lines.
      const lookAhead = rowActive[y + 1] ?? false;
      if (!lookAhead) {
        bands.push({ top, bottom: y - 1, maxX });
        inBand = false;
      }
    }
  }
  if (inBand) bands.push({ top, bottom: TERM_H - 1, maxX });

  if (bands.length !== expectedCount) {
    throw new Error(`Doctor pixel row count (${bands.length}) did not match raw.ascii text row count (${expectedCount})`);
  }
  return bands;
}

// ---------------------------------------------------------------------------
// Brand HTML pages (1920x1080)
// ---------------------------------------------------------------------------

const htmlDoc = (body: string, css: string): string => `<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="${FONTS}"><style>
*{box-sizing:border-box;margin:0;padding:0}html,body{width:${CANVAS_W}px;height:${CANVAS_H}px;overflow:hidden;background:transparent}em{font-style:normal}
${css}</style></head><body>${body}</body></html>`;

const cornerBracketsHtml = `<i class="corner tl"></i><i class="corner tr"></i><i class="corner bl"></i><i class="corner br"></i>`;
const cornerBracketsCss = `
.corner{position:absolute;width:28px;height:28px;border:0 solid ${PALETTE.accent};opacity:.92}
.corner.tl{top:22px;left:22px;border-width:2.5px 0 0 2.5px}
.corner.tr{top:22px;right:22px;border-width:2.5px 2.5px 0 0}
.corner.bl{bottom:22px;left:22px;border-width:0 0 2.5px 2.5px}
.corner.br{bottom:22px;right:22px;border-width:0 2.5px 2.5px 0}`;

const fieldBackgroundCss = `
background-color:${PALETTE.field};
background-image:linear-gradient(${PALETTE.grid} 1px,transparent 1px),linear-gradient(90deg,${PALETTE.grid} 1px,transparent 1px);
background-size:32px 32px;`;

function introCardHtml(facts: ParsedAscii["facts"]): string {
  const steps = [
    { num: "01", cmd: "ai-eng init", role: "Write contract" },
    { num: "02", cmd: "ai-eng doctor", role: "Live deny + verify" },
    { num: "03", cmd: "ai-eng work", role: "Git lane board" },
    { num: "04", cmd: "ai-eng config", role: "Add Cursor" },
  ];
  const chips = steps
    .map(
      (step) => `<div class="step"><span class="step-num">${step.num}</span><span class="step-cmd">${escapeHtml(step.cmd)}</span><span class="step-role">${escapeHtml(step.role)}</span></div>`,
    )
    .join("");
  return htmlDoc(
    `<div id="canvas">
  <i class="band"></i>
  ${cornerBracketsHtml}
  <header class="top">
    <span class="eyebrow">11 / GET IT</span>
    <span class="meta-tag">REAL TERMINAL SESSION · ai-eng ${escapeHtml(facts.version)} · SOUND OFF</span>
  </header>
  <main class="center">
    <div class="mark" data-overhang><img alt="" src="${MARK_DATA_URI}"></div>
    <h1 data-overhang>
      <i class="plus tl"></i><i class="plus tr"></i><i class="plus bl"></i><i class="plus br"></i>
      ${withAccent("Try it on one repo", "one repo")}
    </h1>
    <p class="sub">Install the contract, fire a real refusal, check lanes, and add a second agent host.</p>
    <div class="steps">${chips}</div>
  </main>
  <footer class="foot">
    <span>{ai} engineering · local · 0 model calls</span>
    <span>every number below comes from this run</span>
  </footer>
</div>`,
    `#canvas{position:relative;width:${CANVAS_W}px;height:${CANVAS_H}px;${fieldBackgroundCss}display:flex;flex-direction:column;justify-content:space-between;padding:44px 76px}
${cornerBracketsCss}
.band{position:absolute;left:0;right:0;top:240px;height:520px;background:${PALETTE.band};-webkit-mask-image:radial-gradient(ellipse 56% 52% at 50% 50%,#000 52%,transparent 100%);mask-image:radial-gradient(ellipse 56% 52% at 50% 50%,#000 52%,transparent 100%)}
.top,.foot{position:relative;display:flex;justify-content:space-between;align-items:center;font:600 17px/1 ${MONO};letter-spacing:.14em;color:${PALETTE.muted}}
.eyebrow{text-transform:uppercase;color:${PALETTE.body}}
.foot{font-weight:500;letter-spacing:.08em}
.center{position:relative;display:flex;flex-direction:column;align-items:center;text-align:center;gap:30px}
.mark{position:relative;width:96px;height:96px;transform:rotate(-3deg);margin-bottom:6px}
.mark::before{content:"";position:absolute;left:50%;top:50%;width:320px;height:320px;margin:-160px 0 0 -160px;border-radius:50%;background:radial-gradient(circle,${PALETTE.glow},transparent 68%)}
.mark img{position:relative;display:block;width:96px;height:96px}
h1{position:relative;display:inline-block;font:800 94px/1.04 ${SANS};font-stretch:92%;letter-spacing:-.03em;color:${PALETTE.ink}}
h1 em{color:${PALETTE.accent};text-decoration:underline;text-decoration-thickness:4px;text-underline-offset:12px;text-decoration-skip-ink:none}
.plus{position:absolute;width:16px;height:16px}.plus::before,.plus::after{content:"";position:absolute;background:${PALETTE.accent};opacity:.9}
.plus::before{left:7px;top:0;width:2.5px;height:16px}.plus::after{top:7px;left:0;height:2.5px;width:16px}
.plus.tl{left:-52px;top:-16px}.plus.tr{right:-52px;top:-16px}.plus.bl{left:-52px;bottom:-16px}.plus.br{right:-52px;bottom:-16px}
.sub{max-width:1180px;font:400 32px/1.4 ${SANS};color:${PALETTE.body}}
.steps{margin-top:16px;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:18px;width:100%;max-width:1460px}
.step{border:1.5px solid ${PALETTE.border};border-radius:12px;background:${PALETTE.raised};padding:18px 22px;display:flex;flex-direction:column;align-items:flex-start;gap:8px;text-align:left}
.step-num{font:700 14px/1 ${MONO};letter-spacing:.14em;color:${PALETTE.accentText}}
.step-cmd{font:700 20px/1.2 ${MONO};color:${PALETTE.ink}}
.step-role{font:400 17px/1.3 ${SANS};color:${PALETTE.muted}}`,
  );
}

function closingCardHtml(facts: ParsedAscii["facts"]): string {
  return htmlDoc(
    `<div id="canvas">
  <i class="band"></i>
  ${cornerBracketsHtml}
  <header class="top">
    <span class="eyebrow">11 / GET IT · START NOW</span>
    <span class="meta-tag">APACHE-2.0 · BUN >= 1.4.4 · ai-eng ${escapeHtml(facts.version)}</span>
  </header>
  <main class="center">
    <div class="mark" data-overhang><img alt="" src="${MARK_DATA_URI}"></div>
    <h1 data-overhang>
      <i class="plus tl"></i><i class="plus tr"></i><i class="plus bl"></i><i class="plus br"></i>
      ${withAccent("Run it on your repo", "your repo")}
    </h1>
    <div class="cmd-card">
      <div class="cmd-head">
        <span class="cmd-chip">FIRST COMMAND</span>
        <span class="cmd-note">or: npm install -g ai-engineering@latest</span>
      </div>
      <div class="cmd-row is-primary"><span class="prompt">$</span><span class="code">bun add -g ai-engineering@latest</span><span class="tag">01 install</span></div>
      <div class="cmd-row"><span class="prompt">$</span><span class="code">ai-eng init</span><span class="tag">02 govern</span></div>
      <div class="cmd-row"><span class="prompt">$</span><span class="code">ai-eng doctor</span><span class="tag">03 verify</span></div>
    </div>
    <p class="sub">Runs locally · 0 hosted services · 0 model calls · Every refusal saved in <code>.ai-engineering/receipts/</code></p>
  </main>
  <footer class="foot">
    <span>github.com/arcasilesgroup/ai-engineering</span>
    <span>ai-engineering.arcasiles.com</span>
  </footer>
</div>`,
    `#canvas{position:relative;width:${CANVAS_W}px;height:${CANVAS_H}px;${fieldBackgroundCss}display:flex;flex-direction:column;justify-content:space-between;padding:44px 76px}
${cornerBracketsCss}
.band{position:absolute;left:0;right:0;top:220px;height:560px;background:${PALETTE.band};-webkit-mask-image:radial-gradient(ellipse 56% 52% at 50% 50%,#000 52%,transparent 100%);mask-image:radial-gradient(ellipse 56% 52% at 50% 50%,#000 52%,transparent 100%)}
.top,.foot{position:relative;display:flex;justify-content:space-between;align-items:center;font:600 17px/1 ${MONO};letter-spacing:.14em;color:${PALETTE.muted}}
.eyebrow{text-transform:uppercase;color:${PALETTE.body}}
.foot{font-weight:500;letter-spacing:.08em}
.center{position:relative;display:flex;flex-direction:column;align-items:center;text-align:center;gap:28px}
.mark{position:relative;width:82px;height:82px;transform:rotate(-3deg)}
.mark::before{content:"";position:absolute;left:50%;top:50%;width:280px;height:280px;margin:-140px 0 0 -140px;border-radius:50%;background:radial-gradient(circle,${PALETTE.glow},transparent 68%)}
.mark img{position:relative;display:block;width:82px;height:82px}
h1{position:relative;display:inline-block;font:800 78px/1.05 ${SANS};font-stretch:92%;letter-spacing:-.03em;color:${PALETTE.ink}}
h1 em{color:${PALETTE.accent};text-decoration:underline;text-decoration-thickness:4px;text-underline-offset:10px;text-decoration-skip-ink:none}
.plus{position:absolute;width:14px;height:14px}.plus::before,.plus::after{content:"";position:absolute;background:${PALETTE.accent};opacity:.9}
.plus::before{left:6px;top:0;width:2px;height:14px}.plus::after{top:6px;left:0;height:2px;width:14px}
.plus.tl{left:-46px;top:-14px}.plus.tr{right:-46px;top:-14px}.plus.bl{left:-46px;bottom:-14px}.plus.br{right:-46px;bottom:-14px}
.cmd-card{width:100%;max-width:1180px;border:2px solid ${PALETTE.accent};border-radius:14px;background:${PALETTE.raised};padding:26px 34px;display:flex;flex-direction:column;gap:14px;text-align:left;box-shadow:0 30px 80px -24px rgba(0,0,0,.75)}
.cmd-head{display:flex;justify-content:space-between;align-items:center;padding-bottom:14px;border-bottom:1px solid ${PALETTE.hairline}}
.cmd-chip{font:700 14px/1 ${MONO};letter-spacing:.12em;padding:6px 14px;border-radius:999px;background:${PALETTE.accent};color:${PALETTE.onAccent}}
.cmd-note{font:500 17px/1 ${MONO};color:${PALETTE.muted}}
.cmd-row{display:grid;grid-template-columns:28px minmax(0,1fr) auto;align-items:center;gap:14px;padding:12px 18px;border-radius:10px;background:${PALETTE.field};border:1px solid ${PALETTE.hairline}}
.cmd-row.is-primary{border:1.5px solid ${PALETTE.accent};background:${PALETTE.field}}
.prompt{font:700 26px/1 ${MONO};color:${PALETTE.accent}}
.code{font:700 26px/1.2 ${MONO};color:${PALETTE.ink}}
.tag{font:600 15px/1 ${MONO};letter-spacing:.08em;text-transform:uppercase;color:${PALETTE.accentText}}
.sub{font:400 24px/1.4 ${SANS};color:${PALETTE.body}}
.sub code{font:600 21px/1 ${MONO};color:${PALETTE.accentText}}`,
  );
}

type StageActMeta = {
  index: number;
  windowTitle: string;
  windowBadge: string;
};

const STAGE_STEPS = ["01 INIT", "02 DOCTOR", "03 WORK", "04 CONFIG"] as const;

function stageHtml(act: StageActMeta, facts: ParsedAscii["facts"]): string {
  const pills = STAGE_STEPS.map((label, idx) => {
    const isDone = idx < act.index;
    const isCurrent = idx === act.index;
    const cls = isCurrent ? "pill is-current" : isDone ? "pill is-done" : "pill";
    const glyph = isCurrent ? "▸" : isDone ? "✓" : "·";
    return `<span class="${cls}"><span class="glyph">${glyph}</span>${label}</span>`;
  }).join("");

  return htmlDoc(
    `<div id="canvas">
  ${cornerBracketsHtml}
  <header class="hud">
    <div class="brand-left">
      <img class="brand-mark" alt="" src="${MARK_DATA_URI}">
      <span class="eyebrow">11 / GET IT</span>
      <span class="sep">·</span>
      <span class="ver">ai-eng ${escapeHtml(facts.version)}</span>
    </div>
    <nav class="stepper">${pills}</nav>
  </header>
  <section class="window">
    <div class="win-bar">
      <div class="dots"><i class="dot"></i><i class="dot"></i><i class="dot"></i><span class="win-title">${escapeHtml(act.windowTitle)}</span></div>
      <span class="win-badge">${escapeHtml(act.windowBadge)}</span>
    </div>
    <div class="win-well"></div>
  </section>
</div>`,
    `#canvas{position:relative;width:${CANVAS_W}px;height:${CANVAS_H}px;${fieldBackgroundCss}}
${cornerBracketsCss}
.hud{position:absolute;top:24px;left:92px;right:92px;height:56px;display:flex;justify-content:space-between;align-items:center}
.brand-left{display:flex;align-items:center;gap:14px}
.brand-mark{width:34px;height:34px;display:block}
.eyebrow{font:700 16px/1 ${MONO};letter-spacing:.14em;text-transform:uppercase;color:${PALETTE.ink}}
.sep{color:${PALETTE.border};font:600 18px/1 ${MONO}}
.ver{font:600 16px/1 ${MONO};letter-spacing:.04em;color:${PALETTE.accentText}}
.stepper{display:flex;align-items:center;gap:10px}
.pill{display:inline-flex;align-items:center;gap:8px;padding:8px 15px;border-radius:999px;border:1px solid ${PALETTE.border};background:${PALETTE.raised};font:600 14px/1 ${MONO};letter-spacing:.08em;color:${PALETTE.muted}}
.pill.is-done{border-color:${PALETTE.accentDeep};color:${PALETTE.accentText};background:${PALETTE.raised}}
.pill.is-current{border:1.5px solid ${PALETTE.accent};background:${PALETTE.accent};color:${PALETTE.onAccent};font-weight:700}
.glyph{font-weight:700}
.window{position:absolute;left:${TERM_X - 2}px;top:${TERM_Y - 38}px;width:${TERM_W + 4}px;height:${TERM_H + 40}px;border-radius:14px;border:2px solid ${PALETTE.border};background:${PALETTE.field};overflow:hidden;box-shadow:0 32px 84px -26px rgba(0,0,0,.78)}
.win-bar{height:38px;padding:0 18px;background:${PALETTE.raised};border-bottom:1px solid ${PALETTE.hairline};display:flex;justify-content:space-between;align-items:center}
.dots{display:flex;align-items:center;gap:8px}
.dot{width:11px;height:11px;border-radius:50%;background:${PALETTE.border};opacity:.65}
.win-title{margin-left:10px;font:600 14px/1 ${MONO};color:${PALETTE.body}}
.win-badge{font:600 14px/1 ${MONO};color:${PALETTE.accentText};letter-spacing:.04em}
.win-well{width:${TERM_W}px;height:${TERM_H}px;background:${PALETTE.field}}`,
  );
}

type CaptionSpec = {
  id: string;
  badge: string;
  tone: "accent" | "deny" | "pass";
  textHtml: string;
  meta: string;
};

function captionHtml(spec: CaptionSpec): string {
  const barColor = spec.tone === "deny" ? PALETTE.bad : PALETTE.accent;
  const badgeCss =
    spec.tone === "deny"
      ? `border:1.5px solid ${PALETTE.bad};background:color-mix(in srgb,${PALETTE.bad} 16%,${PALETTE.field});color:${PALETTE.badText}`
      : spec.tone === "pass"
        ? `border:1.5px solid ${PALETTE.accent};background:${PALETTE.accent};color:${PALETTE.onAccent}`
        : `border:1.5px solid ${PALETTE.accent};background:color-mix(in srgb,${PALETTE.accent} 14%,${PALETTE.field});color:${PALETTE.accentText}`;

  return htmlDoc(
    `<div id="canvas">
  <div class="dock">
    <i class="bar"></i>
    <div class="content">
      <div class="top-row">
        <span class="badge">${escapeHtml(spec.badge)}</span>
        <span class="meta">${escapeHtml(spec.meta)}</span>
      </div>
      <p class="line">${spec.textHtml}</p>
    </div>
  </div>
</div>`,
    `#canvas{position:relative;width:${CANVAS_W}px;height:${CANVAS_H}px;background:transparent}
.dock{position:absolute;left:${TERM_X - 2}px;top:926px;width:${TERM_W + 4}px;height:122px;border-radius:12px;border:1.5px solid ${PALETTE.border};background:${PALETTE.raised};display:flex;overflow:hidden;box-shadow:0 18px 44px -18px rgba(0,0,0,.7)}
.bar{width:6px;flex:0 0 6px;background:${barColor}}
.content{flex:1 1 auto;padding:16px 26px 18px;display:flex;flex-direction:column;justify-content:center;gap:12px}
.top-row{display:flex;justify-content:space-between;align-items:center;gap:16px}
.badge{display:inline-flex;align-items:center;gap:6px;padding:5px 13px;border-radius:999px;font:700 14px/1 ${MONO};letter-spacing:.1em;text-transform:uppercase;${badgeCss}}
.meta{font:500 15px/1 ${MONO};color:${PALETTE.muted};letter-spacing:.04em}
.line{font:600 27px/1.28 ${SANS};color:${PALETTE.ink};letter-spacing:-.01em}
.line code{font:600 24px/1 ${MONO};color:${PALETTE.accentText};background:${PALETTE.field};padding:3px 9px;border-radius:6px;border:1px solid ${PALETTE.hairline}}
.line code.is-deny{color:${PALETTE.badText};border-color:${PALETTE.bad}}`,
  );
}

type HighlightSpec = {
  topY: number;
  bottomY: number;
  maxX: number;
  chipText: string;
  chipTone: "deny" | "pass";
  title: string;
  monoDetail: string;
  subDetail: string;
};

/** Transparent 1920x1080 overlay that softly dims non-target terminal rows and frames the real line
 *  in the brand's Spring Green accent with an explicit non-colour-only callout card on the right. */
function highlightHtml(spec: HighlightSpec): string {
  const isMultiRow = spec.bottomY - spec.topY > 30;
  const padY = isMultiRow ? 5 : 3;
  const spotTop = Math.max(TERM_Y + 4, TERM_Y + spec.topY - padY);
  const spotBottom = Math.min(TERM_Y + TERM_H - 4, TERM_Y + spec.bottomY + padY);
  const spotHeight = spotBottom - spotTop;
  const boxLeft = TERM_X + 4;
  const boxWidth = Math.min(spec.maxX + 34, 1140);
  const boxRight = boxLeft + boxWidth;
  const cardLeft = Math.max(boxRight + 48, 1210);
  const cardWidth = TERM_X + TERM_W - cardLeft - 24;
  const midY = Math.round((spotTop + spotBottom) / 2);
  const cardHeight = 148;
  const cardTop = Math.max(TERM_Y + 24, Math.min(TERM_Y + TERM_H - cardHeight - 24, midY - Math.round(cardHeight / 2)));
  const leaderWidth = Math.max(18, cardLeft - boxRight);

  const chipCss =
    spec.chipTone === "deny"
      ? `border:1.5px solid ${PALETTE.bad};background:color-mix(in srgb,${PALETTE.bad} 16%,${PALETTE.field});color:${PALETTE.badText}`
      : `border:1.5px solid ${PALETTE.accent};background:${PALETTE.accent};color:${PALETTE.onAccent}`;

  const iconSvg =
    spec.chipTone === "deny"
      ? `<svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true"><path d="M2.5 2.5L11.5 11.5M11.5 2.5L2.5 11.5" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/></svg>`
      : `<svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true"><path d="M2 7.5L5.5 11L12 3.5" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>`;

  return htmlDoc(
    `<div id="canvas">
  <div class="scrim top"></div>
  <div class="scrim bottom"></div>
  <div class="scrim right-band"></div>
  <div class="frame"><i class="rail"></i></div>
  <div class="leader"><i class="node"></i></div>
  <aside class="callout">
    <span class="chip">${iconSvg}<span>${escapeHtml(spec.chipText)}</span></span>
    <strong class="title">${escapeHtml(spec.title)}</strong>
    <p class="mono">${escapeHtml(spec.monoDetail)}</p>
    <p class="sub">${escapeHtml(spec.subDetail)}</p>
  </aside>
</div>`,
    `#canvas{position:relative;width:${CANVAS_W}px;height:${CANVAS_H}px;background:transparent}
.scrim{position:absolute;background:rgba(0,30,43,0.58)}
.scrim.top{left:${TERM_X}px;top:${TERM_Y}px;width:${TERM_W}px;height:${Math.max(0, spotTop - TERM_Y)}px}
.scrim.bottom{left:${TERM_X}px;top:${spotBottom}px;width:${TERM_W}px;height:${Math.max(0, TERM_Y + TERM_H - spotBottom)}px}
.scrim.right-band{left:${boxRight}px;top:${spotTop}px;width:${Math.max(0, TERM_X + TERM_W - boxRight)}px;height:${spotHeight}px}
.frame{position:absolute;left:${boxLeft}px;top:${spotTop}px;width:${boxWidth}px;height:${spotHeight}px;border-radius:8px;border:2.5px solid ${PALETTE.accent};box-shadow:0 0 0 1px rgba(0,237,100,0.22),0 0 28px rgba(0,237,100,0.18);overflow:hidden}
.rail{position:absolute;left:0;top:0;bottom:0;width:4px;background:${PALETTE.accent}}
.leader{position:absolute;left:${boxRight}px;top:${midY - 1}px;width:${leaderWidth}px;height:2.5px;background:${PALETTE.accent}}
.node{position:absolute;right:-5px;top:-4px;width:10px;height:10px;border-radius:50%;background:${PALETTE.accent}}
.callout{position:absolute;left:${cardLeft}px;top:${cardTop}px;width:${cardWidth}px;min-height:${cardHeight}px;border-radius:12px;border:2px solid ${PALETTE.accent};background:${PALETTE.raised};padding:18px 22px;display:flex;flex-direction:column;gap:9px;box-shadow:0 24px 64px -20px rgba(0,0,0,.85)}
.chip{align-self:flex-start;display:inline-flex;align-items:center;gap:8px;padding:5px 12px;border-radius:999px;font:700 13px/1 ${MONO};letter-spacing:.1em;text-transform:uppercase;${chipCss}}
.title{font:800 22px/1.15 ${SANS};font-stretch:92%;letter-spacing:-.02em;color:${PALETTE.ink}}
.mono{font:700 16px/1.25 ${MONO};color:${PALETTE.accentText}}
.sub{font:400 16px/1.35 ${SANS};color:${PALETTE.body}}`,
  );
}

async function checkNoOverflow(box: Locator): Promise<string | null> {
  return box.evaluate((element): string | null => {
    if (element.scrollWidth > element.clientWidth || element.scrollHeight > element.clientHeight) {
      return `canvas scrolls (${element.scrollWidth}x${element.scrollHeight} in ${element.clientWidth}x${element.clientHeight})`;
    }
    return null;
  });
}

type RenderItem = { file: string; html: string; transparent: boolean; families: string[] };

async function renderOverlays(items: RenderItem[], outDir: string): Promise<void> {
  const { chromium } = await import("playwright-core");
  mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch({ channel: "chrome" });
  try {
    const context = await browser.newContext({ viewport: { width: CANVAS_W, height: CANVAS_H }, deviceScaleFactor: 1 });
    const tab = await context.newPage();
    for (const item of items) {
      await tab.setContent(item.html, { waitUntil: "networkidle" });
      await tab.evaluate(() => document.fonts.ready);
      const hasFonts = await tab.evaluate(
        (wanted) => wanted.every((family) => [...document.fonts].some((face) => face.family === family && face.status === "loaded")),
        item.families,
      );
      if (!hasFonts) throw new Error(`Google Fonts did not load for ${item.file}`);
      const box = tab.locator("#canvas");
      const overflow = await checkNoOverflow(box);
      if (overflow) throw new Error(`${item.file}: ${overflow}`);
      await box.screenshot({ path: join(outDir, item.file), omitBackground: item.transparent });
    }
    await context.close();
  } finally {
    await browser.close();
  }
}

const fmt = (seconds: number): string => seconds.toFixed(3);

/** Build the deterministic ffmpeg input manifest and filter_complex script. */
function buildFiltergraph(
  acts: ActBounds[],
  rawMp4: string,
  outDir: string,
): { inputs: string[]; filtergraph: string; durationSeconds: number } {
  type InputSpec = { path: string; loopDuration?: number };
  const specs: InputSpec[] = [{ path: rawMp4 }];
  const pushImg = (file: string, loopDuration: number): number => {
    const idx = specs.length;
    specs.push({ path: join(outDir, file), loopDuration });
    return idx;
  };
  const pushStatic = (file: string): number => {
    const idx = specs.length;
    specs.push({ path: join(outDir, file) });
    return idx;
  };

  const act1 = acts[0] as ActBounds;
  const act2 = acts[1] as ActBounds;
  const act3 = acts[2] as ActBounds;
  const act4 = acts[3] as ActBounds;

  const act1RunDur = (act1.settledFrame - act1.startFrame + 1) / FPS;
  const act1Hold = ACT1_HOLD_CONTRACT + ACT1_HOLD_HOOKS;
  const act1Total = act1RunDur + act1Hold;

  const act2RunDur = (act2.settledFrame - act2.startFrame + 1) / FPS;
  const act2Hold = ACT2_HOLD_OVERVIEW + ACT2_HOLD_DENY + ACT2_HOLD_VERIFIED;
  const act2Total = act2RunDur + act2Hold;

  const act3RunDur = (act3.settledFrame - act3.startFrame + 1) / FPS;
  const act3Total = act3RunDur + ACT3_HOLD_LANES;

  const act4RunDur = (act4.settledFrame - act4.startFrame + 1) / FPS;
  const act4Total = act4RunDur + ACT4_HOLD_SURFACES;

  const introIdx = pushImg("intro.png", INTRO_DURATION);
  const outroIdx = pushImg("outro.png", OUTRO_DURATION);

  const stage1Idx = pushImg("stage-act1.png", act1Total);
  const stage2Idx = pushImg("stage-act2.png", act2Total);
  const stage3Idx = pushImg("stage-act3.png", act3Total);
  const stage4Idx = pushImg("stage-act4.png", act4Total);

  const cap1aIdx = pushStatic("cap-1a.png");
  const cap1bIdx = pushStatic("cap-1b.png");
  const cap1cIdx = pushStatic("cap-1c.png");

  const cap2aIdx = pushStatic("cap-2a.png");
  const cap2bIdx = pushStatic("cap-2b.png");
  const cap2cIdx = pushStatic("cap-2c.png");
  const cap2dIdx = pushStatic("cap-2d.png");

  const cap3aIdx = pushStatic("cap-3a.png");
  const cap3bIdx = pushStatic("cap-3b.png");

  const cap4aIdx = pushStatic("cap-4a.png");
  const cap4bIdx = pushStatic("cap-4b.png");

  const hlDenyStart = act2RunDur + ACT2_HOLD_OVERVIEW;
  const hlVerifiedStart = hlDenyStart + ACT2_HOLD_DENY;
  const hlDenyIdx = pushImg("hl-deny.png", ACT2_HOLD_DENY);
  const hlVerifiedIdx = pushImg("hl-verified.png", ACT2_HOLD_VERIFIED);

  const lines: string[] = [];

  // Intro & outro normalized to exact FPS and timebase.
  lines.push(`[${introIdx}:v]fps=${FPS},format=rgba,setpts=PTS-STARTPTS[intro];`);
  lines.push(`[${outroIdx}:v]fps=${FPS},format=rgba,setpts=PTS-STARTPTS[outro];`);

  // Act 1: init
  const act1Split = act1RunDur + ACT1_HOLD_CONTRACT;
  lines.push(
    `[0:v]trim=start_frame=${act1.startFrame}:end_frame=${act1.settledFrame + 1},setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop_duration=${fmt(act1Hold)},fps=${FPS},format=rgba[raw1];`,
  );
  lines.push(`[${stage1Idx}:v]fps=${FPS},format=rgba,setpts=PTS-STARTPTS[st1];`);
  lines.push(`[st1][raw1]overlay=${TERM_X}:${TERM_Y}:shortest=1[s1_0];`);
  lines.push(`[s1_0][${cap1aIdx}:v]overlay=0:0:enable='lt(t,${fmt(act1RunDur)})'[s1_1];`);
  lines.push(`[s1_1][${cap1bIdx}:v]overlay=0:0:enable='between(t,${fmt(act1RunDur)},${fmt(act1Split)})'[s1_2];`);
  lines.push(`[s1_2][${cap1cIdx}:v]overlay=0:0:enable='gte(t,${fmt(act1Split)})'[act1];`);

  // Act 2: doctor + smooth non-colour-only highlights on live deny & chain verified
  lines.push(
    `[0:v]trim=start_frame=${act2.startFrame}:end_frame=${act2.settledFrame + 1},setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop_duration=${fmt(act2Hold)},fps=${FPS},format=rgba[raw2];`,
  );
  lines.push(`[${stage2Idx}:v]fps=${FPS},format=rgba,setpts=PTS-STARTPTS[st2];`);
  lines.push(`[st2][raw2]overlay=${TERM_X}:${TERM_Y}:shortest=1[s2_0];`);
  lines.push(
    `[${hlDenyIdx}:v]fps=${FPS},format=rgba,fade=t=in:st=0:d=0.22:alpha=1,fade=t=out:st=${fmt(ACT2_HOLD_DENY - 0.22)}:d=0.22:alpha=1,setpts=PTS+${fmt(hlDenyStart)}/TB[hld];`,
  );
  lines.push(
    `[${hlVerifiedIdx}:v]fps=${FPS},format=rgba,fade=t=in:st=0:d=0.22:alpha=1,setpts=PTS+${fmt(hlVerifiedStart)}/TB[hlv];`,
  );
  lines.push(`[s2_0][hld]overlay=0:0:eof_action=pass[s2_1];`);
  lines.push(`[s2_1][hlv]overlay=0:0:eof_action=pass[s2_2];`);
  lines.push(`[s2_2][${cap2aIdx}:v]overlay=0:0:enable='lt(t,${fmt(act2RunDur)})'[s2_3];`);
  lines.push(`[s2_3][${cap2bIdx}:v]overlay=0:0:enable='between(t,${fmt(act2RunDur)},${fmt(hlDenyStart)})'[s2_4];`);
  lines.push(`[s2_4][${cap2cIdx}:v]overlay=0:0:enable='between(t,${fmt(hlDenyStart)},${fmt(hlVerifiedStart)})'[s2_5];`);
  lines.push(`[s2_5][${cap2dIdx}:v]overlay=0:0:enable='gte(t,${fmt(hlVerifiedStart)})'[act2];`);

  // Act 3: work
  lines.push(
    `[0:v]trim=start_frame=${act3.startFrame}:end_frame=${act3.settledFrame + 1},setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop_duration=${fmt(ACT3_HOLD_LANES)},fps=${FPS},format=rgba[raw3];`,
  );
  lines.push(`[${stage3Idx}:v]fps=${FPS},format=rgba,setpts=PTS-STARTPTS[st3];`);
  lines.push(`[st3][raw3]overlay=${TERM_X}:${TERM_Y}:shortest=1[s3_0];`);
  lines.push(`[s3_0][${cap3aIdx}:v]overlay=0:0:enable='lt(t,${fmt(act3RunDur)})'[s3_1];`);
  lines.push(`[s3_1][${cap3bIdx}:v]overlay=0:0:enable='gte(t,${fmt(act3RunDur)})'[act3];`);

  // Act 4: config --add cursor
  lines.push(
    `[0:v]trim=start_frame=${act4.startFrame}:end_frame=${act4.settledFrame + 1},setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop_duration=${fmt(ACT4_HOLD_SURFACES)},fps=${FPS},format=rgba[raw4];`,
  );
  lines.push(`[${stage4Idx}:v]fps=${FPS},format=rgba,setpts=PTS-STARTPTS[st4];`);
  lines.push(`[st4][raw4]overlay=${TERM_X}:${TERM_Y}:shortest=1[s4_0];`);
  lines.push(`[s4_0][${cap4aIdx}:v]overlay=0:0:enable='lt(t,${fmt(act4RunDur)})'[s4_1];`);
  lines.push(`[s4_1][${cap4bIdx}:v]overlay=0:0:enable='gte(t,${fmt(act4RunDur)})'[act4];`);

  // Chain all 6 segments with clean fades (no whooshes, no whips — terminal and type only).
  const off1 = INTRO_DURATION - CARD_XFADE;
  const off2 = off1 + act1Total - ACT_XFADE;
  const off3 = off2 + act2Total - ACT_XFADE;
  const off4 = off3 + act3Total - ACT_XFADE;
  const off5 = off4 + act4Total - CARD_XFADE;
  const durationSeconds = Number((off5 + OUTRO_DURATION).toFixed(1));

  lines.push(`[intro][act1]xfade=transition=fade:duration=${fmt(CARD_XFADE)}:offset=${fmt(off1)}[v01];`);
  lines.push(`[v01][act2]xfade=transition=fade:duration=${fmt(ACT_XFADE)}:offset=${fmt(off2)}[v02];`);
  lines.push(`[v02][act3]xfade=transition=fade:duration=${fmt(ACT_XFADE)}:offset=${fmt(off3)}[v03];`);
  lines.push(`[v03][act4]xfade=transition=fade:duration=${fmt(ACT_XFADE)}:offset=${fmt(off4)}[v04];`);
  lines.push(`[v04][outro]xfade=transition=fade:duration=${fmt(CARD_XFADE)}:offset=${fmt(off5)},format=yuv420p[vout]`);

  // Serialize ffmpeg input args one per line so the shell script passes them safely.
  const argLines: string[] = [];
  for (const spec of specs) {
    if (spec.loopDuration !== undefined) {
      argLines.push("-loop", "1", "-framerate", String(FPS), "-t", fmt(spec.loopDuration), "-i", spec.path);
    } else {
      argLines.push("-i", spec.path);
    }
  }

  return { inputs: argLines, filtergraph: lines.join("\n"), durationSeconds };
}

async function main(): Promise<void> {
  const [rawMp4, rawAscii, outDir, factsOut] = process.argv.slice(2);
  if (!rawMp4 || !rawAscii || !outDir || !factsOut) {
    throw new Error("usage: bun scripts/quickstart-video.ts <raw.mp4> <raw.ascii> <outDir> <factsOut.json>");
  }

  const parsed = parseAscii(readFileSync(rawAscii, "utf8"));
  const { acts } = analyzeActs(rawMp4);
  const doctorAct = acts[1] as ActBounds;
  const doctorBands = measureDoctorBands(rawMp4, doctorAct.settledFrame, parsed.doctorLinesAfterPipe.length);

  const denyBand = doctorBands[parsed.denyLineIndex] as PixelBand;
  const checksBand = doctorBands[parsed.checksLineIndex] as PixelBand;
  const verifiedBand = doctorBands[parsed.verifiedLineIndex] as PixelBand;
  const { facts } = parsed;

  const metaTag = `real run · ai-eng ${facts.version} · sound off`;

  const captions: CaptionSpec[] = [
    {
      id: "cap-1a",
      badge: "01 · INIT",
      tone: "accent",
      textHtml: `Govern a repository in one command: <code>ai-eng init --surface claude-code --yes</code>.`,
      meta: metaTag,
    },
    {
      id: "cap-1b",
      badge: "01 · CONTRACT",
      tone: "accent",
      textHtml: `Writes editable <code>AGENTS.md</code> and <code>DECISIONS.md</code>, plus config and a ${facts.lockAssets}-asset sha256 lock.`,
      meta: metaTag,
    },
    {
      id: "cap-1c",
      badge: "01 · SAFE BY DEFAULT",
      tone: "accent",
      textHtml: `Installs marker-managed git floor hooks, commits nothing, and points to <code>ai-eng doctor</code>.`,
      meta: metaTag,
    },
    {
      id: "cap-2a",
      badge: "02 · DOCTOR",
      tone: "accent",
      textHtml: `Run <code>ai-eng doctor</code> to audit all ${facts.checksTotal} checks live.`,
      meta: metaTag,
    },
    {
      id: "cap-2b",
      badge: `02 · ${facts.checksTotal} CHECKS`,
      tone: "accent",
      textHtml: `Checks <code>AGENTS.md</code> (${facts.rulesCount} rules), ${facts.canonVerified}/${facts.canonTotal} canon files with 0 drift, and git hooks with gitleaks.`,
      meta: metaTag,
    },
    {
      id: "cap-2c",
      badge: "✕ 02 · LIVE DENY · BLOCKED",
      tone: "deny",
      textHtml: `Live adversarial probe tries <code class="is-deny">git commit -n</code> — refused with <code class="is-deny">DENY</code> in ${facts.denyMs}ms before git starts.`,
      meta: `receipt p50 ${facts.receiptP50Ms}ms · p95 ${facts.receiptP95Ms}ms`,
    },
    {
      id: "cap-2d",
      badge: "✓ 02 · CHAIN VERIFIED · PASS",
      tone: "pass",
      textHtml: `All ${facts.checksTotal} checks pass — ${facts.checksOk} OK, ${facts.checksWarn} WARN, ${facts.checksFail} FAIL — and the guard chain is verified.`,
      meta: metaTag,
    },
    {
      id: "cap-3a",
      badge: "03 · WORK",
      tone: "accent",
      textHtml: `Run <code>ai-eng work</code> to read the live git lane board.`,
      meta: metaTag,
    },
    {
      id: "cap-3b",
      badge: "03 · LANE BOARD",
      tone: "accent",
      textHtml: `Tracks <code>${escapeHtml(facts.branch)}</code> against <code>${escapeHtml(facts.baseBranch)}</code> (${facts.activeLanes}/${facts.maxLanes} active lanes, ${facts.uncommitted} uncommitted files).`,
      meta: metaTag,
    },
    {
      id: "cap-4a",
      badge: "04 · ADD SURFACE",
      tone: "accent",
      textHtml: `Add a second agent host: <code>ai-eng config --add cursor</code>.`,
      meta: metaTag,
    },
    {
      id: "cap-4b",
      badge: "✓ 04 · MULTI-HOST",
      tone: "pass",
      textHtml: `Writes <code>.cursor/hooks.json</code> and verifies ${facts.mirrorTargets} skill mirrors — now 2 enforced hosts: ${escapeHtml(facts.surfacesAfterAdd[0])} and ${escapeHtml(facts.surfacesAfterAdd[1])}.`,
      meta: metaTag,
    },
  ];

  const bothFonts = ["Archivo", "JetBrains Mono"];
  const monoOnly = ["JetBrains Mono"];
  const renderItems: RenderItem[] = [
    { file: "intro.png", html: introCardHtml(facts), transparent: false, families: bothFonts },
    { file: "outro.png", html: closingCardHtml(facts), transparent: false, families: bothFonts },
    {
      file: "stage-act1.png",
      html: stageHtml({ index: 0, windowTitle: "my-app — bash", windowBadge: "$ ai-eng init · claude-code" }, facts),
      transparent: false,
      families: monoOnly,
    },
    {
      file: "stage-act2.png",
      html: stageHtml({ index: 1, windowTitle: "my-app — bash", windowBadge: "$ ai-eng doctor · live probe" }, facts),
      transparent: false,
      families: monoOnly,
    },
    {
      file: "stage-act3.png",
      html: stageHtml({ index: 2, windowTitle: "my-app — bash", windowBadge: `$ ai-eng work · ${facts.branch} → ${facts.baseBranch}` }, facts),
      transparent: false,
      families: monoOnly,
    },
    {
      file: "stage-act4.png",
      html: stageHtml({ index: 3, windowTitle: "my-app — bash", windowBadge: "$ ai-eng config --add cursor" }, facts),
      transparent: false,
      families: monoOnly,
    },
    ...captions.map((cap) => ({ file: `${cap.id}.png`, html: captionHtml(cap), transparent: true, families: bothFonts })),
    {
      file: "hl-deny.png",
      html: highlightHtml({
        topY: denyBand.top,
        bottomY: denyBand.bottom,
        maxX: denyBand.maxX,
        chipText: "REFUSED LIVE · DENY",
        chipTone: "deny",
        title: "Blocked before git starts",
        monoDetail: `git commit -n → DENY in ${facts.denyMs}ms`,
        subDetail: "Adversarial probe proves the hook stops shortcuts live.",
      }),
      transparent: true,
      families: bothFonts,
    },
    {
      file: "hl-verified.png",
      html: highlightHtml({
        topY: checksBand.top,
        bottomY: verifiedBand.bottom,
        maxX: Math.max(checksBand.maxX, verifiedBand.maxX),
        chipText: "CHAIN VERIFIED · PASS",
        chipTone: "pass",
        title: `All ${facts.checksTotal} checks passed`,
        monoDetail: `${facts.checksOk} OK · ${facts.checksWarn} WARN · ${facts.checksFail} FAIL`,
        subDetail: "Contract, canon, floor hooks, and carrier enforced.",
      }),
      transparent: true,
      families: bothFonts,
    },
  ];

  await renderOverlays(renderItems, outDir);

  const plan = buildFiltergraph(acts, rawMp4, outDir);
  writeFileSync(join(outDir, "filtergraph.txt"), `${plan.filtergraph}\n`, "utf8");
  writeFileSync(join(outDir, "inputs.args"), `${plan.inputs.join("\n")}\n`, "utf8");

  const fullFacts: QuickstartFacts = {
    ...facts,
    width: CANVAS_W,
    height: CANVAS_H,
    fps: FPS,
    durationSeconds: plan.durationSeconds,
  };
  writeFileSync(factsOut, `${JSON.stringify(fullFacts, null, 2)}\n`, "utf8");

  console.log(
    `ok  quickstart overlays (${renderItems.length} PNGs) · deny row y=${denyBand.top}..${denyBand.bottom} (${facts.denyMs}ms) · verified rows y=${checksBand.top}..${verifiedBand.bottom} · target ${plan.durationSeconds}s`,
  );
}

if (import.meta.main) await main();
