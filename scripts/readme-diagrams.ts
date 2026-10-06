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
  "ai-orchestrator",
  "ai-brainstorm",
  "ai-research",
  "ai-architect",
  "ai-verify",
  "ai-security",
  "ai-write",
  "ai-visual-recap",
];

const BEFORE = [
  { cmd: "/ai-brainstorm", sub: "optional · pins the idea in plain language" },
  { cmd: "/ai-research", sub: "optional · evidence from outside the repo" },
  { cmd: "/ai-architect", sub: "optional · the approach and the layer rules" },
];

const AFTER = [
  { cmd: "/ai-verify", sub: "optional · a verdict with evidence" },
  { cmd: "/ai-security", sub: "optional · the six-phase audit" },
  { cmd: "/ai-write", sub: "optional · the README, the wiki, the API doc" },
  { cmd: "/ai-visual-recap", sub: "optional · the diff, as a page" },
];

/** The orchestrator's own gates, plus the human review that closes the loop. */
const GATES = ["behavior", "UI", "adversarial review"];

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

/** A dashed card for a skill you can leave out. */
function optCard(x: number, y: number, w: number, h: number, pal: Palette, n: { cmd: string; sub: string }): string {
  const pad = 16;
  const parts = [
    `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="12" fill="none" stroke="${pal.faint}" stroke-dasharray="5 4"/>`,
    text(x + pad, y + 32, n.cmd, { size: 15, fill: pal.title, weight: 700, mono: true }),
  ];
  wrapWords(n.sub, Math.floor((w - pad * 2) / 6.6))
    .slice(0, 2)
    .forEach((line, i) => parts.push(text(x + pad, y + 56 + i * 17, line, { size: 12.5, fill: pal.body })));
  return parts.join("\n");
}

/** A small chip, used for the gate names. */
/** Width of a gate chip, from its label. */
function gateChipWidth(label: string): number {
  return label.length * 7.6 + 26;
}

function skillDiagram(pal: Palette): string {
  const W = 1400;
  const CX = W / 2;
  const parts: string[] = [];

  parts.push(`<path d="M 585 66 L 625 66" stroke="${pal.accent}" stroke-width="1.5"/>`);
  parts.push(text(639, 71, "THE ORCHESTRATOR LOOP", { size: 12, fill: pal.accent, weight: 700, mono: true, tracking: 2.4 }));
  parts.push(text(CX - 10, 142, "One loop.", { size: 42, fill: pal.title, weight: 800, anchor: "end" }));
  parts.push(text(CX + 10, 142, "Everything else is optional.", { size: 42, fill: pal.accent, weight: 800, anchor: "start" }));
  parts.push(
    text(CX, 182, "ai-orchestrator is the whole workflow: it splits the feature into checkpoints, runs each one through its gates,", {
      size: 15.5,
      fill: pal.body,
      anchor: "middle",
    }),
  );
  parts.push(
    text(CX, 204, "and stops for you twice. Every other skill is optional, and they compose with whatever else you already run.", {
      size: 15.5,
      fill: pal.body,
      anchor: "middle",
    }),
  );

  parts.push(text(40, 266, "OPTIONAL · BEFORE THE LOOP", { size: 12, fill: pal.accent, weight: 700, mono: true, tracking: 1.8 }));
  BEFORE.forEach((b, i) => parts.push(optCard(40 + i * 450, 282, 420, 84, pal, b)));

  // The loop: the one mandatory thing in the picture.
  const panelY = 400;
  const panelH = 280;
  parts.push(`<rect x="40" y="${panelY}" width="1320" height="${panelH}" rx="16" fill="${pal.hot}" stroke="${pal.accent}" stroke-width="1.5"/>`);
  parts.push(text(72, panelY + 42, "/ai-orchestrator · the loop that runs it all", { size: 21, fill: pal.accent, weight: 700, mono: true }));
  parts.push(text(72, panelY + 68, "The only skill you have to run. It plans the checkpoints, then builds each one through its gates.", { size: 14, fill: pal.body }));

  // The checkpoint stepper: small steps first, one at a time.
  const cy = panelY + 136;
  const steps = ["1", "2", "3", "4", "5", "N"];
  steps.forEach((n, i) => {
    const cx = 112 + i * 108;
    const state = i < 3 ? "done" : i === 3 ? "now" : "todo";
    const fill = state === "done" ? pal.accent : pal.card;
    const stroke = state === "todo" ? pal.faint : pal.accent;
    const dash = state === "todo" ? ' stroke-dasharray="4 3"' : "";
    parts.push(`<circle cx="${cx}" cy="${cy}" r="19" fill="${fill}" stroke="${stroke}" stroke-width="1.5"${dash}/>`);
    parts.push(text(cx, cy + 6, n, { size: 15, fill: state === "done" ? pal.bg : pal.body, weight: 700, mono: true, anchor: "middle" }));
    if (i < steps.length - 1) parts.push(`<path d="M ${cx + 21} ${cy} L ${cx + 87} ${cy}" stroke="${pal.accent}" stroke-width="1.5"/>`);
  });
  parts.push(text(682, cy + 6, "one at a time · smallest first", { size: 13, fill: pal.muted, mono: true }));

  // The gates: how a checkpoint earns the next one.
  parts.push(text(72, panelY + 196, "A checkpoint passes its gates, or it cannot move on", { size: 13, fill: pal.muted, mono: true }));
  let gx = 72;
  for (const name of GATES) {
    const w = gateChipWidth(name);
    parts.push(`<rect x="${gx}" y="${panelY + 210}" width="${w}" height="32" rx="8" fill="${pal.card}" stroke="${pal.accent}"/>`);
    parts.push(text(gx + w / 2, panelY + 231, name, { size: 13.5, fill: pal.accent, weight: 700, mono: true, anchor: "middle" }));
    gx += w + 12;
  }
  parts.push(text(72, panelY + 268, "A failed gate re-plans and retries. Three failures on a split checkpoint stop and ask you.", { size: 12.5, fill: pal.muted }));

  // The two human stops, in their own column.
  parts.push(`<rect x="962" y="${panelY + 34}" width="362" height="38" rx="9" fill="none" stroke="${pal.accent}" stroke-dasharray="4 3"/>`);
  parts.push(text(982, panelY + 59, "STOP 1 · you approve the plan", { size: 14, fill: pal.accent, weight: 700, mono: true }));
  parts.push(`<path d="M 1143 ${panelY + 74} L 1143 ${panelY + 126}" fill="none" stroke="${pal.accent}" stroke-width="1.5" marker-end="url(#head)"/>`);
  parts.push(`<rect x="962" y="${panelY + 132}" width="362" height="38" rx="9" fill="none" stroke="${pal.accent}" stroke-dasharray="4 3"/>`);
  parts.push(text(982, panelY + 157, "STOP 2 · you review the app", { size: 14, fill: pal.accent, weight: 700, mono: true }));
  parts.push(text(982, panelY + 202, "The only two times it asks you", { size: 13, fill: pal.muted, mono: true }));
  parts.push(text(982, panelY + 226, "anything, from the first idea", { size: 13, fill: pal.muted, mono: true }));
  parts.push(text(982, panelY + 250, "to the finished pull request.", { size: 13, fill: pal.muted, mono: true }));

  parts.push(text(40, 726, "OPTIONAL · AFTER THE LOOP", { size: 12, fill: pal.accent, weight: 700, mono: true, tracking: 1.8 }));
  AFTER.forEach((a, i) => parts.push(optCard(40 + i * 335, 742, 315, 84, pal, a)));

  parts.push(text(CX, 866, "Every skill is optional except the loop · bring your own skills, and run them beside any other harness", {
    size: 14,
    fill: pal.muted,
    anchor: "middle",
  }));

  parts.push(text(40, 916, "ON DEMAND · ANYWHERE IN THE CHAIN", { size: 12, fill: pal.accent, weight: 700, mono: true, tracking: 1.8 }));
  const cloud = chips(ON_DEMAND, 40, 932, 1360, pal);
  parts.push(cloud.svg);

  const H = 932 + cloud.height + 44;
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
