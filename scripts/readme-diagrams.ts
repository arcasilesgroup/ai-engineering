#!/usr/bin/env bun
// scripts/readme-diagrams.ts — renders the README's two diagrams from the repo.
//
// The hand-written skill SVG this replaces named `ai-plan`, `ai-goal` and
// `ai-proof`: three skills that no longer exist, in the README's biggest picture.
// A diagram a human edits drifts; a diagram the repo renders cannot. Update the
// diagram by changing the tables below, and the run fails if a skill is renamed,
// added or removed without the diagram following.

import { existsSync, readdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const ROOT = join(import.meta.dir, "..");
const ASSETS = join(ROOT, ".github", "assets");

const MONO = "'JetBrains Mono','Fira Code','SF Mono',ui-monospace,monospace";
const SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif";

type Palette = {
  bg: string;
  panel: string;
  stroke: string;
  title: string;
  body: string;
  muted: string;
  accent: string;
  accentSoft: string;
  deny: string;
  rewrite: string;
  allow: string;
};

const DARK: Palette = {
  bg: "#001E2B",
  panel: "#112733",
  stroke: "#25505F",
  title: "#FFFFFF",
  body: "#C1C7C6",
  muted: "#889397",
  accent: "#00ED64",
  accentSoft: "#71F6BA",
  deny: "#FF6960",
  rewrite: "#FFC010",
  allow: "#00ED64",
};

const LIGHT: Palette = {
  bg: "#FFFFFF",
  panel: "#F9FBFA",
  stroke: "#C1C7C6",
  title: "#001E2B",
  body: "#3D4F58",
  muted: "#5C6C75",
  accent: "#00684A",
  accentSoft: "#00A35C",
  deny: "#970606",
  rewrite: "#944F01",
  allow: "#00684A",
};

/** XML-safe text, so a name with `&` or `<` cannot break the file. */
const esc = (s: string): string => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

function text(
  x: number,
  y: number,
  value: string,
  opts: { size?: number; fill: string; weight?: number; mono?: boolean; anchor?: string; tracking?: number },
): string {
  const family = opts.mono ? MONO : SANS;
  const anchor = opts.anchor ? ` text-anchor="${opts.anchor}"` : "";
  const weight = opts.weight ? ` font-weight="${opts.weight}"` : "";
  const tracking = opts.tracking ? ` letter-spacing="${opts.tracking}"` : "";
  return `<text x="${x}" y="${y}" font-family="${family}" font-size="${opts.size ?? 14}" fill="${opts.fill}"${weight}${anchor}${tracking}>${esc(value)}</text>`;
}

function box(x: number, y: number, w: number, h: number, pal: Palette, accent = false): string {
  const stroke = accent ? pal.accent : pal.stroke;
  return `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="12" fill="${pal.panel}" stroke="${stroke}" stroke-width="1.25"/>`;
}

function arrow(x1: number, y1: number, x2: number, y2: number, pal: Palette): string {
  return `<path d="M ${x1} ${y1} L ${x2} ${y2}" fill="none" stroke="${pal.accent}" stroke-width="1.75" stroke-linecap="round" marker-end="url(#head)"/>`;
}

/** A labelled card: a big title, one or two body lines, an optional footer. */
function card(
  x: number,
  y: number,
  w: number,
  h: number,
  pal: Palette,
  node: { title: string; lines?: string[]; foot?: string },
): string {
  const parts = [box(x, y, w, h, pal)];
  parts.push(text(x + 18, y + 30, node.title, { size: 17, fill: pal.title, weight: 700, mono: true }));
  (node.lines ?? []).forEach((line, i) => {
    parts.push(text(x + 18, y + 54 + i * 19, line, { size: 13, fill: pal.body }));
  });
  if (node.foot) parts.push(text(x + 18, y + h - 14, node.foot, { size: 12.5, fill: pal.accentSoft, mono: true }));
  return parts.join("\n");
}

/** Wrapping row of small chips; returns the SVG and the height it consumed. */
function chips(
  items: string[],
  x0: number,
  y0: number,
  maxX: number,
  pal: Palette,
  size = 13,
): { svg: string; height: number } {
  const gap = 12;
  const pad = 14;
  const height = 30;
  const rowGap = 12;
  let x = x0;
  let y = y0;
  const parts: string[] = [];
  for (const item of items) {
    const w = item.length * (size * 0.62) + pad * 2;
    if (x + w > maxX) {
      x = x0;
      y += height + rowGap;
    }
    parts.push(`<rect x="${x}" y="${y}" width="${w}" height="${height}" rx="7" fill="${pal.panel}" stroke="${pal.stroke}"/>`);
    parts.push(text(x + w / 2, y + 20, item, { size, fill: pal.title, mono: true, anchor: "middle" }));
    x += w + gap;
  }
  return { svg: parts.join("\n"), height: y - y0 + height };
}

// ── the data the diagrams render ────────────────────────────────────────────

const SKILLS_DIR = join(ROOT, "skills");
const installedSkills = readdirSync(SKILLS_DIR)
  .filter((name) => existsSync(join(SKILLS_DIR, name, "SKILL.md")))
  .sort();

const PIPELINE = ["ai-brainstorm", "ai-orchestrator", "ai-verify", "ai-visual-recap"];
const FEEDS_IN = ["ai-research", "ai-architect"];
const TRIGGERED = ["ai-security", "ai-write"];
const ON_DEMAND = installedSkills.filter((s) => !PIPELINE.includes(s) && !FEEDS_IN.includes(s) && !TRIGGERED.includes(s));

const LANES = [
  { id: "light", detail: "ai-brainstorm → ai-verify · a verdict, no contract" },
  { id: "standard", detail: "ai-brainstorm → ai-orchestrator → ai-verify → the recap" },
  { id: "full", detail: "the same, plus research, architecture, security and docs when a trigger fires" },
];

const GUARDS = [
  { name: "self-protect", detail: "writes against governance" },
  { name: "no-verify", detail: "hook skips, linter silences" },
  { name: "policy", detail: "system · net · workspace" },
  { name: "injection", detail: "text that gives orders" },
  { name: "wrap", detail: "rewrites a test command" },
  { name: "loop", detail: "the same call, again" },
];

const VERDICTS = [
  { title: "DENY", key: "deny", detail: ["exit 2 · the call never runs", "the reason, in the host's own dialect"] },
  { title: "REWRITE", key: "rewrite", detail: ["the host runs a safer command", "the original is kept in the receipt"] },
  { title: "ALLOW", key: "allow", detail: ["exit 0 · the call runs", "still written down, still auditable"] },
];

/** Fail the render when a skill the diagram names is not installed. */
function assertSkillsExist(names: string[], where: string): void {
  for (const name of names) {
    if (!existsSync(join(SKILLS_DIR, name, "SKILL.md"))) {
      throw new Error(`readme-diagrams: ${where} names "${name}", which has no skills/${name}/SKILL.md`);
    }
  }
}

// ── diagram 1: the skill pipeline ───────────────────────────────────────────

function skillDiagram(pal: Palette): string {
  const W = 1360;
  const parts: string[] = [];
  parts.push(text(40, 54, "{ai} engineering · one pipeline", { size: 25, fill: pal.title, weight: 700, mono: true }));
  parts.push(
    text(40, 82, `${installedSkills.length} skills. Each declares in its front matter what it writes, who reads it,`, { size: 15, fill: pal.body }),
  );
  parts.push(text(40, 102, "when it dies, and what runs next — so the handoff is a contract, not a convention.", { size: 15, fill: pal.body }));

  parts.push(text(40, 148, "LANES", { size: 12, fill: pal.accent, weight: 700, mono: true, tracking: 2 }));
  LANES.forEach((lane, i) => {
    const y = 160 + i * 34;
    parts.push(`<rect x="118" y="${y}" width="104" height="26" rx="7" fill="${pal.panel}" stroke="${pal.stroke}"/>`);
    parts.push(text(170, y + 18, lane.id, { size: 13, fill: pal.accent, weight: 700, mono: true, anchor: "middle" }));
    parts.push(text(238, y + 18, lane.detail, { size: 14, fill: pal.body }));
  });

  // Feeders sit above the orchestrator, triggers below verify and the recap.
  const nodes = [
    { x: 90, y: 420, w: 250, h: 96, title: PIPELINE[0], lines: ["the idea, said in plain", "language"] },
    { x: 400, y: 420, w: 250, h: 96, title: PIPELINE[1], lines: ["builds it in gated", "checkpoints you approve"] },
    { x: 710, y: 420, w: 250, h: 96, title: PIPELINE[2], lines: ["a verdict with evidence,", "not an impression"] },
    { x: 1020, y: 420, w: 250, h: 96, title: PIPELINE[3], lines: ["the diff, as an", "interactive page"] },
  ];
  const feeds = [
    { x: 275, y: 290, w: 250, h: 72, title: FEEDS_IN[0], lines: ["answers what the repo", "cannot"] },
    { x: 550, y: 290, w: 250, h: 72, title: FEEDS_IN[1], lines: ["the approach, the stack,", "the tradeoff"] },
  ];
  const triggered = [
    { x: 710, y: 560, w: 250, h: 72, title: TRIGGERED[0], lines: ["a six-phase audit,", "adversarially validated"] },
    { x: 1020, y: 560, w: 250, h: 72, title: TRIGGERED[1], lines: ["the README, the wiki,", "the API doc"] },
  ];

  parts.push(text(40, 282, "FEEDS THE CONTRACT", { size: 12, fill: pal.accent, weight: 700, mono: true, tracking: 1.6 }));
  for (const n of feeds) parts.push(card(n.x, n.y, n.w, n.h, pal, n));
  for (const n of nodes) parts.push(card(n.x, n.y, n.w, n.h, pal, n));
  parts.push(text(40, 554, "FIRES AFTER VERIFY", { size: 12, fill: pal.accent, weight: 700, mono: true, tracking: 1.6 }));
  for (const n of triggered) parts.push(card(n.x, n.y, n.w, n.h, pal, n));

  // Pipeline arrows.
  const midY = 468;
  for (const [a, b] of [
    [0, 1],
    [1, 2],
  ]) {
    const from = nodes[a]!;
    const to = nodes[b]!;
    parts.push(arrow(from.x + from.w, midY, to.x - 4, midY, pal));
  }
  // The recap is the terminal node: the arrow in is the pipeline's last hop.
  parts.push(arrow(nodes[2]!.x + nodes[2]!.w, midY, nodes[3]!.x - 4, midY, pal));
  parts.push(`<path d="M 400 362 L 400 392 L 490 392 L 490 416" fill="none" stroke="${pal.accent}" stroke-width="1.75" stroke-linecap="round" marker-end="url(#head)"/>`);
  parts.push(`<path d="M 675 362 L 675 392 L 560 392 L 560 416" fill="none" stroke="${pal.accent}" stroke-width="1.75" stroke-linecap="round" marker-end="url(#head)"/>`);
  parts.push(arrow(835, 516, 835, 556, pal));
  parts.push(arrow(1145, 516, 1145, 556, pal));

  parts.push(text(40, 672, "ON DEMAND · ANYWHERE IN THE CHAIN", { size: 12, fill: pal.accent, weight: 700, mono: true, tracking: 1.6 }));
  const cloud = chips(ON_DEMAND, 40, 688, 1320, pal);
  parts.push(cloud.svg);

  const H = 688 + cloud.height + 40;
  return frame(W, H, pal, parts.join("\n"));
}

// ── diagram 2: the life of one tool call ────────────────────────────────────

function guardDiagram(pal: Palette): string {
  const W = 1360;
  const parts: string[] = [];
  parts.push(text(40, 54, "{ai} engineering · the life of one tool call", { size: 25, fill: pal.title, weight: 700, mono: true }));
  parts.push(text(40, 82, "The host hands every call to one dispatcher before it runs. Guards decide, the verdict", { size: 15, fill: pal.body }));
  parts.push(text(40, 102, "goes back in the host's own dialect, and a receipt lands on disk.", { size: 15, fill: pal.body }));

  const row1 = [
    { x: 40, title: "The agent", lines: ["asks for one tool call"] },
    { x: 460, title: "The host", lines: ["sends the payload on stdin,", "asks for a verdict"] },
    { x: 880, title: "ai-eng chain", lines: ["your binary · no model call", "· no network"] },
  ];
  for (const n of row1) parts.push(card(n.x, 150, 380, 88, pal, n));
  parts.push(arrow(420, 194, 456, 194, pal));
  parts.push(arrow(840, 194, 876, 194, pal));

  parts.push(text(40, 296, "PRETOOLUSE · SIX GUARDS, IN ORDER · THE FIRST DENY WINS", {
    size: 12,
    fill: pal.accent,
    weight: 700,
    mono: true,
    tracking: 1.2,
  }));
  GUARDS.forEach((guard, i) => {
    const x = 40 + i * 216;
    parts.push(box(x, 312, 200, 66, pal));
    parts.push(text(x + 14, 338, guard.name, { size: 15, fill: pal.title, weight: 700, mono: true }));
    parts.push(text(x + 14, 358, guard.detail, { size: 12, fill: pal.body }));
  });

  parts.push(arrow(680, 378, 680, 414, pal));
  parts.push(text(680, 432, "the first guard that fires decides", { size: 13, fill: pal.muted, anchor: "middle" }));

  const verdictY = 452;
  VERDICTS.forEach((verdict, i) => {
    const x = 40 + i * 440;
    const color = verdict.key === "deny" ? pal.deny : verdict.key === "rewrite" ? pal.rewrite : pal.allow;
    parts.push(box(x, verdictY, 400, 96, pal, true));
    parts.push(text(x + 18, verdictY + 34, verdict.title, { size: 18, fill: color, weight: 700, mono: true, tracking: 1.5 }));
    verdict.detail.forEach((line, j) => {
      parts.push(text(x + 18, verdictY + 58 + j * 19, line, { size: 13, fill: pal.body }));
    });
  });

  parts.push(arrow(680, 548, 680, 584, pal));
  parts.push(card(40, 600, 1280, 90, pal, {
    title: "A receipt for every verdict",
    lines: [".ai-engineering/receipts/ · one file per call, plus summary.json and denies.json · committed with the work"],
    foot: "doctor reads them back: denies per guard, per tool, over 90 days",
  }));
  parts.push(text(40, 728, "USERPROMPTSUBMIT · ONE MORE GUARD: spoken-secret reads the prompt before it enters the transcript", {
    size: 12.5,
    fill: pal.muted,
    mono: true,
    tracking: 0.6,
  }));

  return frame(W, 760, pal, parts.join("\n"));
}

function frame(w: number, h: number, pal: Palette, body: string): string {
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" role="img">
<defs>
<marker id="head" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 1 L 9 5 L 0 9 z" fill="${pal.accent}"/></marker>
</defs>
<rect width="${w}" height="${h}" fill="${pal.bg}"/>
${body}
</svg>
`;
}

// ── write ───────────────────────────────────────────────────────────────────

assertSkillsExist([...PIPELINE, ...FEEDS_IN, ...TRIGGERED], "the pipeline");
for (const lane of LANES) {
  for (const named of lane.detail.match(/ai-[a-z-]+/g) ?? []) {
    if (!installedSkills.includes(named)) throw new Error(`readme-diagrams: a lane names "${named}", which is not installed`);
  }
}

for (const [name, pal] of [
  ["skill-chain-dark", DARK],
  ["skill-chain-light", LIGHT],
  ["guard-flow-dark", DARK],
  ["guard-flow-light", LIGHT],
] as const) {
  const svg = (name.startsWith("skill-chain") ? skillDiagram : guardDiagram)(pal);
  writeFileSync(join(ASSETS, `${name}.svg`), svg);
  console.log(`wrote .github/assets/${name}.svg`);
}
