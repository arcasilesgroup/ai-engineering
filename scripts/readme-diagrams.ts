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
  ivory: string;
  panel: string;
  card: string;
  hot: string;
  faint: string;
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
  ivory: "#001E2B",
  panel: "#112733",
  card: "#112733",
  hot: "#0F2C36",
  faint: "#3D4F58",
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
  ivory: "#F9FBFA",
  panel: "#F9FBFA",
  card: "#FFFFFF",
  hot: "#EDF6F2",
  faint: "#C1C7C6",
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

/** Every skill the diagram names, so a rename fails the render instead of the picture. */
const NAMED_SKILLS = [
  "ai-brainstorm",
  "ai-orchestrator",
  "ai-verify",
  "ai-visual-recap",
  "ai-research",
  "ai-architect",
  "ai-design-md-planner",
  "ai-audit-design",
  "ai-security",
  "ai-write",
];

type PhaseCard = { cmd: string; sub: string; out?: string; hot?: boolean };
type Phase = { idx: string; name: string; cards: PhaseCard[]; gate?: string };

/** The pipeline as the site draws it: five phases, no lanes, one gate per column. */
const PHASES: Phase[] = [
  {
    idx: "01",
    name: "frame",
    cards: [{ cmd: "/ai-brainstorm", sub: "the idea, said in plain language", out: "writes brainstorm.html" }],
  },
  {
    idx: "02",
    name: "contract",
    cards: [{ cmd: "/ai-orchestrator", sub: "writes what must hold, and the check that proves it", out: "writes spec.html · plan.html" }],
    gate: "STOP · a human approves",
  },
  {
    idx: "03",
    name: "the loop",
    cards: [{ cmd: "/ai-orchestrator", sub: "phase two: runs the plan, three gates per checkpoint", hot: true }],
    gate: "ai-eng spec run",
  },
  {
    idx: "04",
    name: "verdict",
    cards: [{ cmd: "/ai-verify", sub: "judges the work against the standard it was given", out: "reads spec.html" }],
  },
  {
    idx: "05",
    name: "the close",
    cards: [
      { cmd: "/ai-security", sub: "the security trigger fired" },
      { cmd: "/ai-write", sub: "the public interface changed" },
      { cmd: "/ai-visual-recap", sub: "the terminal node" },
    ],
    gate: "ai-eng spec close",
  },
];

/** The three skills that feed the contract from outside the pipeline. */
const FEEDS = [
  { cmd: "/ai-research", sub: "answers what the repo cannot" },
  { cmd: "/ai-architect", sub: "pins the layer rules" },
  { cmd: "ai-design-md-planner → ai-audit-design", sub: "the UI lane, on the ui trigger" },
];

const ON_DEMAND = installedSkills.filter((s) => !NAMED_SKILLS.includes(s));

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

/** Break a sentence so it fits a column, by an average glyph width. */
function wrapWords(value: string, maxChars: number): string[] {
  const lines: string[] = [];
  let line = "";
  for (const word of value.split(" ")) {
    const candidate = line ? `${line} ${word}` : word;
    if (candidate.length > maxChars && line) {
      lines.push(line);
      line = word;
    } else {
      line = candidate;
    }
  }
  if (line) lines.push(line);
  return lines;
}

/** One skill node. The hot variant marks the phase where the agent is working. */
function node(x: number, y: number, w: number, h: number, pal: Palette, n: PhaseCard): string {
  const fill = n.hot ? pal.hot : pal.panel;
  const stroke = n.hot ? pal.accent : pal.stroke;
  const pad = 14;
  const parts = [`<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="12" fill="${fill}" stroke="${stroke}" stroke-width="1.25"/>`];
  parts.push(text(x + pad, y + 25, n.cmd, { size: 14, fill: n.hot ? pal.accent : pal.title, weight: 700, mono: true }));
  wrapWords(n.sub, Math.floor((w - pad * 2) / 6.3))
    .slice(0, 3)
    .forEach((line, i) => parts.push(text(x + pad, y + 46 + i * 17, line, { size: 12.5, fill: pal.body })));
  if (n.out) parts.push(text(x + pad, y + h - 12, n.out, { size: 11.5, fill: pal.accent, mono: true }));
  return parts.join("\n");
}

/** A stop the pipeline waits on. Dashed, because it is a state, not a skill. */
function gate(x: number, y: number, w: number, h: number, pal: Palette, label: string): string {
  return [
    `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="7" fill="none" stroke="${pal.accent}" stroke-dasharray="4 3" opacity="0.9"/>`,
    text(x + 10, y + 19, label, { size: 12, fill: pal.accent, weight: 700, mono: true }),
  ].join("\n");
}

/** A feeder card: dashed outline, an up-arrow back toward the chain. */
function feed(x: number, y: number, w: number, h: number, pal: Palette, n: { cmd: string; sub: string }): string {
  const pad = 14;
  const arrowX = x + w - 22;
  const parts = [
    `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="12" fill="none" stroke="${pal.faint}" stroke-dasharray="5 4"/>`,
    text(x + pad, y + 27, n.cmd, { size: 13, fill: pal.title, weight: 700, mono: true }),
    `<path d="M ${arrowX} ${y + 27} L ${arrowX} ${y + 14} M ${arrowX - 5} ${y + 19} L ${arrowX} ${y + 14} L ${arrowX + 5} ${y + 19}" fill="none" stroke="${pal.accent}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>`,
  ];
  wrapWords(n.sub, Math.floor((w - pad * 2) / 6.6))
    .slice(0, 2)
    .forEach((line, i) => parts.push(text(x + pad, y + 52 + i * 17, line, { size: 12.5, fill: pal.body })));
  return parts.join("\n");
}

function skillDiagram(pal: Palette): string {
  const W = 1400;
  const CX = W / 2;
  const parts: string[] = [];

  parts.push(`<path d="M 585 66 L 625 66" stroke="${pal.accent}" stroke-width="1.5"/>`);
  parts.push(text(639, 71, "THE SKILLS CHAIN", { size: 12, fill: pal.accent, weight: 700, mono: true, tracking: 2.4 }));
  parts.push(text(CX - 10, 140, "One pipeline,", { size: 44, fill: pal.title, weight: 800, anchor: "end" }));
  parts.push(text(CX + 10, 140, "five phases.", { size: 44, fill: pal.accent, weight: 800, anchor: "start" }));

  const colW = 232;
  const arrowW = 40;
  const phaseNumY = 208;
  const cardTop = 226;
  const singleH = 118;
  const smallH = 58;
  const smallGap = 10;
  const rowH = Math.max(singleH, 3 * smallH + 2 * smallGap);
  const gateY = cardTop + rowH + 14;
  const gateH = 28;
  const arrowY = cardTop + singleH / 2;

  PHASES.forEach((phase, i) => {
    const x = 40 + i * (colW + arrowW);
    parts.push(text(x, phaseNumY, phase.idx, { size: 12, fill: pal.title, weight: 700, mono: true, tracking: 1.6 }));
    parts.push(text(x + 28, phaseNumY, `· ${phase.name.toUpperCase()}`, { size: 12, fill: pal.muted, mono: true, tracking: 1.6 }));
    phase.cards.forEach((c, j) =>
      parts.push(node(x, cardTop + j * (smallH + smallGap), colW, phase.cards.length > 1 ? smallH : singleH, pal, c)),
    );
    if (phase.gate) parts.push(gate(x, gateY, colW, gateH, pal, phase.gate));
    if (i < PHASES.length - 1) parts.push(arrow(x + colW + 6, arrowY, x + colW + arrowW - 8, arrowY, pal));
  });

  const feedsLabelY = gateY + gateH + 52;
  parts.push(text(40, feedsLabelY, "FEEDS THE CONTRACT", { size: 12, fill: pal.accent, weight: 700, mono: true, tracking: 1.8 }));
  const feedTop = feedsLabelY + 16;
  FEEDS.forEach((f, i) => parts.push(feed(40 + i * 448, feedTop, 424, 78, pal, f)));

  const odLabelY = feedTop + 78 + 52;
  parts.push(text(40, odLabelY, "ON DEMAND · ANYWHERE IN THE CHAIN", { size: 12, fill: pal.accent, weight: 700, mono: true, tracking: 1.8 }));
  const cloud = chips(ON_DEMAND, 40, odLabelY + 16, 1360, pal);
  parts.push(cloud.svg);

  const H = odLabelY + 16 + cloud.height + 44;
  const tint = `<defs><radialGradient id="tint" cx="50%" cy="0%" r="72%"><stop offset="0%" stop-color="${pal.accent}" stop-opacity="0.07"/><stop offset="100%" stop-color="${pal.accent}" stop-opacity="0"/></radialGradient></defs><rect width="${W}" height="${H}" fill="url(#tint)"/>`;
  return frame(W, H, { ...pal, bg: pal.ivory, panel: pal.card }, tint + parts.join("\n"));
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

assertSkillsExist(NAMED_SKILLS, "the skills diagram");

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
