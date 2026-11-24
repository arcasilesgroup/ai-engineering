#!/usr/bin/env bun
// scripts/readme-assets.ts — renders the README's images from the repo, with no image model.
//
// Every pixel is typeset or drawn here, from brand/tokens.json and the brand's own component
// styles, in dark and light: the hero, the section headings, the two buttons, the "blocks" and
// "informs" cards, the guards refusal and receipts ledger panels, the skills grid and the five
// figures (scripts/readme-figures.ts). A model misspells and its output cannot be re-rendered;
// this can. Change a line in a table below, run `bun scripts/readme-assets.ts`, commit the
// images it wrote.
//
// The animated quickstart recording (.github/assets/quickstart.gif) is recorded with VHS
// against the real `ai-eng` CLI (.github/assets/tapes/quickstart.tape).
//
// Pass a filename fragment to render only the matching files (`bun scripts/readme-assets.ts figure-`).
// Needs Google Chrome (playwright-core drives it, as scripts/artifact-axe.ts does), network
// for Google Fonts at render time only, and `cwebp`. The README itself loads no font.

import { mkdirSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import type { Locator, Page } from "playwright-core";
import { TABLE } from "../src/chain/mod.ts";
import { checkBash, checkContent } from "../src/guards/no-verify.ts";
import { isTestCommand, rewrite } from "../src/guards/wrap.ts";
import { receiptEventName, type Receipt } from "../src/receipts.ts";
import { colour, DIAGRAM_VARS, FIGURE_CSS, FIGURES, figureFile, figureSvg, FIGURE_WIDTH, type Mode } from "./readme-figures.ts";

const ROOT = join(import.meta.dir, "..");
export const OUT_DIR = join(ROOT, ".github", "assets", "readme");

export type { Mode };
export const MODES: readonly Mode[] = ["dark", "light"];

/** One section heading. `accent` is the one word that takes the green, `label` the eyebrow. */
export type Heading = { slug: string; label: string; text: string; accent: string };

// The twelve section headings rendered for README.md; tests/readme-assets.spec.ts checks the alt text matches.
export const HEADINGS: readonly Heading[] = [
  { slug: "guards", label: "Guards", text: "Refused before it runs", accent: "Refused" },
  { slug: "receipts", label: "Receipts", text: "Every refusal on file", accent: "on file" },
  { slug: "skills", label: "Skills", text: "Skills, sorted by the job", accent: "job" },
  { slug: "fail-closed", label: "Fail closed", text: "Unsure means no", accent: "no" },
  { slug: "your-repo", label: "Your repo", text: "The rules live in your repo", accent: "your repo" },
  { slug: "measured", label: "Measured", text: "Numbers you can rerun", accent: "rerun" },
  { slug: "where-it-stops", label: "Known limits", text: "Where the agent still can", accent: "still can" },
  { slug: "under-the-hood", label: "Under the hood", text: "One CLI, many hosts", accent: "One CLI" },
  { slug: "release", label: "Release", text: "One way to ship", accent: "One way" },
  { slug: "answers", label: "Answers", text: "What sceptics ask", accent: "sceptics" },
  { slug: "get-it", label: "Get it", text: "Try it on one repo", accent: "one repo" },
  { slug: "build-with-us", label: "Build with us", text: "Found a way past it?", accent: "way past" },
];

export type Button = { slug: string; text: string; width: number; filled: boolean };

export const BUTTONS: readonly Button[] = [
  { slug: "start", text: "Get started", width: 180, filled: true },
  { slug: "proof", text: "See the proof", width: 200, filled: false },
];

/** The hero copy and canvas: tilted brand/mark.svg on a soft glow, two-weight claim, refused-call line, and mono ledger. */
export const HERO = {
  wordmark: "{ai} engineering",
  claim: "Guardrails for the AI Coding Agents you already run",
  accent: "Guardrails",
  lightFrom: "you already run",
  command: "git commit --no-verify",
  verdict: "deny",
  ledger: "{ai} engineering · local · no model calls",
  width: 1280,
  height: 480,
} as const;

/** The two callout cards. `kind` picks the border: red for what stops you, green for what only tells you. */
export type Card = { slug: string; kind: "bad" | "good"; chip: string; title: string; bullets: string[]; closing: string };

export const CARDS: readonly Card[] = [
  {
    slug: "blocks",
    kind: "bad",
    chip: "blocks",
    title: "Refused before the call runs",
    bullets: ["`--no-verify`, `git commit -n` and `HUSKY=0`", "a comment that silences a linter", "an edit to the hooks or `.ai-engineering/`"],
    closing: "On the 7 hosts enforced and verified.",
  },
  {
    slug: "informs",
    kind: "good",
    chip: "informs",
    title: "Told, not stopped",
    bullets: ["`zed` and `agy` get skills and advice, no refusal", "a `review` verdict lets the call go ahead with a note", "`ai-eng doctor` warns about drift and false alarms"],
    closing: "Nothing here stops the agent.",
  },
];

/** The skills, grouped by job. `star` marks the one skill the build-loop figure explains. */
export type SkillGroup = { title: string; line: string; skills: readonly string[]; star?: string };

// tests/readme-assets.spec.ts proves these lists are exactly the directories under skills/.
export const SKILL_GROUPS: readonly SkillGroup[] = [
  { title: "Shape the idea", line: "Pin down what to build and why, with sources you can check.", skills: ["ai-brainstorm", "ai-research", "ai-architect", "ai-read-docs"] },
  { title: "Build it", line: "Make the thing, from a clickable mock-up to the tested feature.", skills: ["ai-orchestrator", "ai-test-planner", "ai-prototype", "ai-design-md-planner"], star: "ai-orchestrator" },
  { title: "Understand the code", line: "Find where things live, and why they break.", skills: ["ai-explore", "ai-codegraph", "ai-debug", "ai-note"] },
  { title: "Check the work", line: "A second opinion with evidence, before you ship.", skills: ["ai-verify", "ai-adversarial-loop", "ai-security", "ai-stress-test", "ai-audit-code", "ai-audit-design", "ai-review-ui"] },
  { title: "Ship and write it up", line: "Open the pull request, and keep the docs true to the code.", skills: ["ai-pr", "ai-write", "ai-audit-docs", "ai-visual-recap", "ai-issue-report"] },
  { title: "Keep the repo in order", line: "Rank the backlog, and keep the agent's guidance current.", skills: ["ai-triage", "ai-refresh-project", "ai-writing-behavior"] },
];

/** One PreToolUse attempt judged by the guard chain before the tool runs. */
export type GuardLane = {
  kind: "bash-deny" | "edit-deny" | "bash-rewrite";
  prefix: "$" | "+";
  input: string;
  flag: string;
  guard: "no-verify" | "wrap";
  verdict: "deny" | "rewrite";
  reason: string;
};

// Every lane here is checked against its real guard (`checkBash`, `checkContent`, `isTestCommand`/`rewrite`)
// at render time and in tests/readme-assets.spec.ts.
export const GUARD_LANES: readonly GuardLane[] = [
  {
    kind: "bash-deny",
    prefix: "$",
    input: "git commit --no-verify",
    flag: "--no-verify",
    guard: "no-verify",
    verdict: "deny",
    reason: "--no-verify skips the git hooks. Run the command without it.",
  },
  {
    kind: "bash-deny",
    prefix: "$",
    input: "git commit -n -m fix",
    flag: "-n",
    guard: "no-verify",
    verdict: "deny",
    reason: "git commit -n skips the git hooks. Fix what they would flag.",
  },
  {
    kind: "bash-deny",
    prefix: "$",
    input: "HUSKY=0 git commit -m fix",
    flag: "HUSKY=0",
    guard: "no-verify",
    verdict: "deny",
    reason: "an environment flag skips the git hooks. Refused before git starts.",
  },
  {
    kind: "edit-deny",
    prefix: "+",
    input: "// eslint-disable-next-line",
    flag: "eslint-disable-next-line",
    guard: "no-verify",
    verdict: "deny",
    reason: "Silencing a check is skipping a hook. No override covers this guard.",
  },
  {
    kind: "bash-rewrite",
    prefix: "$",
    input: "bun test",
    flag: "bun test",
    guard: "wrap",
    verdict: "rewrite",
    reason: "Rewritten to ai-eng wrap test, which prints only the failures.",
  },
];

/** Run the real guard behind a Section 01 lane and return its verbatim denial reason or rewritten command. */
export function verifyGuardLane(lane: GuardLane): string {
  if (lane.kind === "bash-deny") {
    const result = checkBash(lane.input, ROOT);
    if (!result || !result.deny) throw new Error(`expected no-verify to deny "${lane.input}", got allow`);
    return result.reason;
  }
  if (lane.kind === "edit-deny") {
    const result = checkContent(lane.input);
    if (!result || !result.deny) throw new Error(`expected no-verify to deny edit "${lane.input}", got allow`);
    return result.reason;
  }
  const decision = isTestCommand(lane.input);
  if (!decision.wrap) throw new Error(`expected wrap to rewrite "${lane.input}", got pass-through`);
  const rewritten = rewrite(lane.input);
  if (!rewritten.startsWith("ai-eng wrap test ")) {
    throw new Error(`expected wrap rewrite to target ai-eng wrap test, got "${rewritten}"`);
  }
  return rewritten;
}

/** On-disk filename written by `writeReceipt` in `src/receipts.ts`: `<ISO-stamp>-<event>-<operation_id>.json`. */
export function receiptFilename(receipt: Receipt): string {
  const stamp = receipt.ts.replace(/[:.]/g, "-");
  return `${stamp}-${receiptEventName(receipt.event)}-${receipt.operation_id}.json`;
}

/** Number of guards in `TABLE[event]` whose tool matcher applies to `tool`. */
export function guardCountFor(event: string, tool: string): number {
  return (TABLE[event] ?? []).filter((row) => row.matcher.test(tool)).length;
}

/** Three representative receipts accumulating in `.ai-engineering/receipts/`, typed against `src/receipts.ts`. */
export const SAMPLE_RECEIPTS: readonly Receipt[] = [
  {
    schema: "urn:ai-eng:receipt:2",
    operation_id: "7d07ec0d",
    ts: "2026-11-23T17:48:59.882Z",
    event: "PreToolUse",
    surface: "claude-code",
    tool: "Bash",
    guards: { ran: ["self-protect", "no-verify"], denied_by: "no-verify" },
    latency_ms: 3,
    outcome: "deny",
  },
  {
    schema: "urn:ai-eng:receipt:2",
    operation_id: "c6f8ffd7",
    ts: "2026-11-23T17:49:03.556Z",
    event: "PreToolUse",
    surface: "claude-code",
    tool: "Edit",
    guards: { ran: ["self-protect"], denied_by: "self-protect" },
    latency_ms: 2,
    outcome: "deny",
  },
  {
    schema: "urn:ai-eng:receipt:2",
    operation_id: "a20c2d8e",
    ts: "2026-11-23T17:49:07.362Z",
    event: "PreToolUse",
    surface: "claude-code",
    tool: "Bash",
    guards: {
      ran: ["self-protect", "no-verify", "no-stash", "policy", "injection", "loop", "checkpoint", "lease", "wrap"],
      denied_by: null,
    },
    latency_ms: 3,
    outcome: "allow",
  },
];

export const RECEIPT_CAVEAT = {
  label: "Log, not proof",
  headline: "A receipt is a log, not proof.",
  detail: "Each verdict writes one JSON file in `.ai-engineering/receipts/`. Anyone who can write to that folder can write one, so treat it as an audit trail, never as cryptographic evidence.",
} as const;

const PANEL_WIDTH = 960;
const GRID_WIDTH = 880;
const HEADING_WIDTH = 800;
const HEADING_HEIGHT = 112;
const BUTTON_HEIGHT = 48;
const CARD_WIDTH = 420;

export const headingFile = (slug: string, mode: Mode) => `heading-${slug}-${mode}.webp`;
export const buttonFile = (slug: string, mode: Mode) => `button-${slug}-${mode}.webp`;
export const heroFile = (mode: Mode) => `hero-${mode}.webp`;
export const cardFile = (slug: string, mode: Mode) => `card-${slug}-${mode}.webp`;
export const guardsRefusedFile = (mode: Mode) => `guards-refused-${mode}.webp`;
export const receiptsLedgerFile = (mode: Mode) => `receipts-ledger-${mode}.webp`;
export const skillsGridFile = (mode: Mode) => `skills-grid-${mode}.webp`;

/** The guards panel's alt text: all five lanes (three hook skips, linter silence, and test rewrite), their guards, verdicts and reasons. */
export const guardsRefusedAlt = (): string =>
  `Five PreToolUse verdicts before the tool runs: ${GUARD_LANES.map((lane) => `${lane.input} handled by ${lane.guard} returns ${lane.verdict} (${lane.reason})`).join(" ")} The stderr artifact prints the live no-verify denial message and exits with status 2.`;

/** The receipts panel's alt text: the three accumulating receipt files, their real on-disk filenames, per-tool guard counts and the log-not-proof caveat. */
export const receiptsLedgerAlt = (): string =>
  `Three receipt files accumulating in .ai-engineering/receipts/: ${SAMPLE_RECEIPTS.map((receipt) => `${receiptFilename(receipt)} (${receipt.tool}, denied by ${receipt.guards.denied_by ?? "none"}, ${receipt.latency_ms} ms, ${receipt.guards.ran.length} of ${guardCountFor(receipt.event, receipt.tool)} guards ran, outcome ${receipt.outcome})`).join("; ")}. ${RECEIPT_CAVEAT.headline} ${RECEIPT_CAVEAT.detail.replaceAll("`", "")}`;

/** The grid's alt text: every group, then every skill in it, so a screen reader gets the same list. */
export const skillsGridAlt = (): string =>
  `The ${SKILL_GROUPS.reduce((total, group) => total + group.skills.length, 0)} skills in six groups. ${SKILL_GROUPS.map((group) => `${group.title}: ${group.skills.join(", ")}.`).join(" ")}`;

/** Every file this script owns in OUT_DIR, so a test can prove none is missing or orphaned. */
export function renderedFiles(): string[] {
  return MODES.flatMap((mode) => [
    ...HEADINGS.map((heading) => headingFile(heading.slug, mode)),
    ...BUTTONS.map((button) => buttonFile(button.slug, mode)),
    ...CARDS.map((card) => cardFile(card.slug, mode)),
    ...FIGURES.map((figure) => figureFile(figure, mode)),
    guardsRefusedFile(mode),
    receiptsLedgerFile(mode),
    skillsGridFile(mode),
    heroFile(mode),
  ]);
}

// ---------------------------------------------------------------------------
// Colour: read from brand/tokens.json, never typed here.
// ---------------------------------------------------------------------------

export type Theme = {
  field: string;
  raised: string;
  well: string;
  ink: string;
  muted: string;
  panelMuted: string;
  accent: string;
  border: string;
  hairline: string;
  buttonInk: string;
  fill: string;
  grid: string;
  band: string;
  glow: string;
  bad: string;
  badText: string;
  good: string;
  goodText: string;
  warn: string;
  warnText: string;
};

// Light is the ivory surface, the one light surface the brand names (tokens.json semantic.surface.surface-ivory).
// `panelMuted` uses gray.dark2 on light so mono text sitting directly on 5% grid crossings stays above 6.7:1.
export const THEMES: Record<Mode, Theme> = {
  dark: {
    field: colour("black"), raised: colour("gray.dark4"), well: colour("black"), ink: colour("white"), muted: colour("gray.light1"), panelMuted: colour("gray.light1"), accent: colour("green.base"),
    border: colour("gray.base"), hairline: `${colour("gray.base")}55`, buttonInk: colour("black"), fill: colour("green.base"), grid: `${colour("white")}0D`, band: `${colour("white")}08`, glow: `${colour("green.base")}14`,
    bad: colour("red.light1"), badText: colour("red.light2"), good: colour("green.base"), goodText: colour("green.light1"), warn: colour("yellow.base"), warnText: colour("yellow.base"),
  },
  light: {
    field: colour("gray.light3"), raised: colour("white"), well: colour("gray.light3"), ink: colour("black"), muted: colour("gray.dark1"), panelMuted: colour("gray.dark2"), accent: colour("green.dark2"),
    border: colour("gray.base"), hairline: `${colour("gray.base")}66`, buttonInk: colour("black"), fill: colour("green.base"), grid: `${colour("gray.dark1")}14`, band: `${colour("white")}B3`, glow: `${colour("green.dark2")}14`,
    bad: colour("red.dark2"), badText: colour("red.dark2"), good: colour("green.dark2"), goodText: colour("green.dark2"), warn: colour("yellow.dark2"), warnText: colour("yellow.dark2"),
  },
};

// ---------------------------------------------------------------------------
// Markup
// ---------------------------------------------------------------------------

const FONTS = "https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@92,400;92,700;92,800&family=JetBrains+Mono:wght@500;700&display=block";
const SANS = "'Archivo', sans-serif";
const MONO = "'JetBrains Mono', monospace";

const escapeHtml = (text: string): string => text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

/** The text with its accent word wrapped, once. A missing accent is a bug in the table. */
function withAccent(text: string, accent: string): string {
  const at = text.indexOf(accent);
  if (at < 0) throw new Error(`accent "${accent}" is not in "${text}"`);
  return `${escapeHtml(text.slice(0, at))}<em>${escapeHtml(accent)}</em>${escapeHtml(text.slice(at + accent.length))}`;
}

/** Backtick spans become <code>, so a card can name `--no-verify` the way the README does. */
const withCode = (text: string): string => escapeHtml(text).replace(/`([^`]+)`/g, "<code>$1</code>");

const page = (body: string, css: string): string => `<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="${FONTS}"><style>
*{box-sizing:border-box;margin:0;padding:0}html,body{background:transparent}em{font-style:normal}
${css}</style></head><body>${body}</body></html>`;

function headingPage(heading: Heading, index: number, theme: Theme): string {
  const eyebrow = `${String(index + 1).padStart(2, "0")} / ${heading.label}`;
  return page(
    `<div id="asset"><p class="eyebrow">${escapeHtml(eyebrow)}</p><h2>${withAccent(heading.text, heading.accent)}</h2></div>`,
    `#asset{width:${HEADING_WIDTH}px;height:${HEADING_HEIGHT}px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;text-align:center}
.eyebrow{font:500 13px/1 ${MONO};letter-spacing:.12em;text-transform:uppercase;color:${theme.muted}}
h2{font:800 48px/1.05 ${SANS};font-stretch:92%;letter-spacing:-.03em;color:${theme.ink};white-space:nowrap}
h2 em{color:${theme.accent}}`,
  );
}

function buttonPage(button: Button, theme: Theme): string {
  const look = button.filled ? `background:${theme.fill};color:${theme.buttonInk}` : `border:1px solid ${theme.border};color:${theme.ink}`;
  return page(
    `<div id="asset">${escapeHtml(button.text)}</div>`,
    `#asset{width:${button.width}px;height:${BUTTON_HEIGHT}px;border-radius:6px;display:flex;align-items:center;justify-content:center;font:700 18px/1 ${SANS};font-stretch:92%;white-space:nowrap;${look}}`,
  );
}

// The mark is the website's favicon, copied byte for byte (brand/mark.svg). It goes in as an image, the
// way a browser draws a favicon, so no glyph here is typeset or redrawn: the tilt and the glow move the
// whole mark and change no part of it.
const MARK_DATA_URI = `data:image/svg+xml;base64,${readFileSync(join(ROOT, "brand", "mark.svg")).toString("base64")}`;

/**
 * The brand hero (brand/components.css `.hero`) with a few extra beats: a faint grid under a brighter band, four
 * green brackets, the tilted mark on a soft glow, a two-weight claim whose first word sits inside a rule, four
 * crosshairs around the claim, one product moment (the refused call) and a mono ledger.
 */
function heroPage(theme: Theme): string {
  const tailAt = HERO.claim.indexOf(HERO.lightFrom);
  if (tailAt < 0) throw new Error(`lightFrom "${HERO.lightFrom}" is not in the claim`);
  const heavy = HERO.claim.slice(0, tailAt).trimEnd();
  const light = HERO.claim.slice(tailAt);
  return page(
    `<div id="asset"><i class="band"></i><i class="corner tl"></i><i class="corner tr"></i><i class="corner bl"></i><i class="corner br"></i>
<div class="mark" data-overhang><img alt="" src="${MARK_DATA_URI}"></div>
<h1 data-overhang><i class="plus tl"></i><i class="plus tr"></i><i class="plus bl"></i><i class="plus br"></i>${withAccent(heavy, HERO.accent)}<span class="light">${escapeHtml(light)}</span></h1>
<p class="term"><span>$ ${escapeHtml(HERO.command)}</span><span class="cursor" data-overhang></span><b>${escapeHtml(HERO.verdict)}</b></p>
<p class="meta">${escapeHtml(HERO.ledger)}</p></div>`,
    `#asset{position:relative;overflow:hidden;width:${HERO.width}px;height:${HERO.height}px;border-radius:12px;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:0 96px;
background-color:${theme.field};background-image:linear-gradient(${theme.grid} 1px,transparent 1px),linear-gradient(90deg,${theme.grid} 1px,transparent 1px);background-size:32px 32px}
.band{position:absolute;left:0;right:0;top:110px;height:250px;background:${theme.band};-webkit-mask-image:radial-gradient(ellipse 52% 50% at 50% 50%,#000 55%,transparent 100%);mask-image:radial-gradient(ellipse 52% 50% at 50% 50%,#000 55%,transparent 100%)}
.corner{position:absolute;width:26px;height:26px;border:0 solid ${theme.accent};opacity:.9}
.corner.tl{top:20px;left:20px;border-width:2px 0 0 2px}.corner.tr{top:20px;right:20px;border-width:2px 2px 0 0}.corner.bl{bottom:20px;left:20px;border-width:0 0 2px 2px}.corner.br{bottom:20px;right:20px;border-width:0 2px 2px 0}
.mark{position:relative;width:72px;height:72px;margin-bottom:26px;transform:rotate(-3deg)}
.mark::before{content:"";position:absolute;left:50%;top:50%;width:230px;height:230px;margin:-115px 0 0 -115px;border-radius:50%;background:radial-gradient(circle,${theme.glow},transparent 68%)}
.mark img{position:relative;display:block;width:72px;height:72px}
h1{position:relative;display:inline-block;font:800 58px/1.1 ${SANS};font-stretch:92%;letter-spacing:-.03em;color:${theme.ink}}
h1 em{color:${theme.accent};text-decoration:underline;text-decoration-thickness:2px;text-underline-offset:8px;text-decoration-skip-ink:none}
h1 .light{display:block;font-weight:400}
.plus{position:absolute;width:12px;height:12px}.plus::before,.plus::after{content:"";position:absolute;background:${theme.accent};opacity:.9}
.plus::before{left:5px;top:0;width:2px;height:12px}.plus::after{top:5px;left:0;height:2px;width:12px}
.plus.tl{left:-32px;top:-12px}.plus.tr{right:-32px;top:-12px}.plus.bl{left:-32px;bottom:-12px}.plus.br{right:-32px;bottom:-12px}
.term{margin-top:26px;display:flex;align-items:center;font:500 18px/1 ${MONO};color:${theme.muted}}
.term b{font-weight:700;color:${theme.accent}}
.cursor{position:relative;display:inline-block;width:10px;height:20px;margin:0 11px;background:${theme.muted};opacity:.9}
.cursor::after{content:"";position:absolute;left:-3px;right:-3px;top:50%;height:2px;background:${theme.ink};transform:translateY(-1px)}
.meta{margin-top:20px;font:500 14px/1 ${MONO};letter-spacing:.16em;color:${theme.muted}}`,
  );
}

/** A callout card: a chip, a title, bullets, one closing line. The edge is the whole border, never one side. */
function cardPage(card: Card, theme: Theme): string {
  const edge = card.kind === "bad" ? theme.bad : theme.good;
  const chipText = card.kind === "bad" ? theme.badText : theme.goodText;
  return page(
    `<div id="asset"><p class="head"><span class="chip">${escapeHtml(card.chip)}</span><b>${escapeHtml(card.title)}</b></p>
<ul>${card.bullets.map((bullet) => `<li>${withCode(bullet)}</li>`).join("")}</ul><p class="close">${escapeHtml(card.closing)}</p></div>`,
    `#asset{width:${CARD_WIDTH}px;border:1.5px solid ${edge};border-radius:12px;background:${theme.raised};padding:22px 24px}
.head{display:flex;flex-wrap:wrap;align-items:center;gap:8px 12px;margin-bottom:14px}
.chip{font:600 12px/1.5 ${MONO};letter-spacing:.04em;padding:3px 10px;border-radius:999px;border:1px solid ${edge};color:${chipText};background:color-mix(in srgb,${edge} 12%,transparent)}
.head b{font:700 20px/1.2 ${SANS};font-stretch:92%;letter-spacing:-.01em;color:${theme.ink}}
ul{padding-left:20px;display:grid;gap:8px;font:400 15px/1.45 ${SANS};color:${theme.muted}}
code{font:500 13px/1 ${MONO};color:${theme.ink}}
.close{margin-top:16px;padding-top:12px;border-top:1px solid ${theme.border};font:700 15px/1.4 ${SANS};color:${theme.ink}}`,
  );
}

/** Shared architectural frame for README showcase panels: navy/ivory field, 5% grid, four corner brackets, mono eyebrow, one accent word, ledger footer. */
function panelFrameCss(theme: Theme): string {
  return `#asset{position:relative;overflow:hidden;width:${PANEL_WIDTH}px;border-radius:12px;border:1px solid ${theme.border};padding:38px 40px 30px;
background-color:${theme.field};background-image:linear-gradient(${theme.grid} 1px,transparent 1px),linear-gradient(90deg,${theme.grid} 1px,transparent 1px);background-size:32px 32px}
.corner{position:absolute;width:22px;height:22px;border:0 solid ${theme.accent};opacity:.9}
.corner.tl{top:14px;left:14px;border-width:2px 0 0 2px}.corner.tr{top:14px;right:14px;border-width:2px 2px 0 0}.corner.bl{bottom:14px;left:14px;border-width:0 0 2px 2px}.corner.br{bottom:14px;right:14px;border-width:0 2px 2px 0}
.p-top{display:flex;justify-content:space-between;align-items:baseline;gap:16px;margin-bottom:10px}
.p-eyebrow{font:600 13.5px/1 ${MONO};letter-spacing:.14em;text-transform:uppercase;color:${theme.panelMuted}}
.p-tag{font:500 13.5px/1 ${MONO};color:${theme.panelMuted}}
.p-title{font:800 30px/1.1 ${SANS};font-stretch:92%;letter-spacing:-.025em;color:${theme.ink};margin-bottom:22px}
.p-title em{color:${theme.accent}}
.p-foot{margin-top:20px;display:flex;justify-content:space-between;align-items:center;gap:16px;font:500 13.5px/1.2 ${MONO};letter-spacing:.04em;color:${theme.panelMuted}}`;
}

/** Highlight the exact trigger token inside a command or edit line so the match reads at a glance. */
function withFlagMark(command: string, flag: string, tone: "deny" | "rewrite"): string {
  const at = command.indexOf(flag);
  if (at < 0) throw new Error(`flag "${flag}" is not in "${command}"`);
  const cls = tone === "rewrite" ? "flag is-rewrite" : "flag";
  return `${escapeHtml(command.slice(0, at))}<mark class="${cls}">${escapeHtml(flag)}</mark>${escapeHtml(command.slice(at + flag.length))}`;
}

/** Section 01: five PreToolUse lanes (three hook skips, one linter silence, one test-command rewrite) plus one live stderr artifact. */
function guardsRefusedPage(theme: Theme): string {
  const liveOutputs = GUARD_LANES.map((lane) => verifyGuardLane(lane));
  const artifactReason = liveOutputs[0] as string;
  const arrowSvg = (stroke: string) =>
    `<svg class="arrow" width="22" height="12" viewBox="0 0 22 12" aria-hidden="true"><path d="M1 6H19" stroke="${stroke}" stroke-width="1.6" stroke-linecap="round"/><path d="M14 2L20 6L14 10" fill="none" stroke="${stroke}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
  const lanes = GUARD_LANES.map((lane) => {
    const isRewrite = lane.verdict === "rewrite";
    const arrow = arrowSvg(isRewrite ? theme.good : theme.bad);
    const pillClass = isRewrite ? "pill is-rewrite" : "pill is-deny";
    const promptClass = lane.prefix === "+" ? "prompt is-edit" : "prompt";
    const guardClass = isRewrite ? "guard is-rewrite" : "guard";
    return `<div class="lane">
  <p class="cmd"><span class="${promptClass}">${escapeHtml(lane.prefix)}</span><span>${withFlagMark(lane.input, lane.flag, lane.verdict)}</span></p>
  <span class="${guardClass}">${escapeHtml(lane.guard)}</span>
  <div class="verdict">${arrow}<span class="${pillClass}">${escapeHtml(lane.verdict)}</span></div>
  <p class="reason">${escapeHtml(lane.reason)}</p>
</div>`;
  }).join("");
  return page(
    `<div id="asset"><i class="corner tl"></i><i class="corner tr"></i><i class="corner bl"></i><i class="corner br"></i>
<div class="p-top"><span class="p-eyebrow">01 / Guards</span><span class="p-tag">PreToolUse · no-verify · wrap</span></div>
<h2 class="p-title">${withAccent("Refused or rewritten before the tool runs", "Refused")}</h2>
<div class="cols"><span>Attempt</span><span>Guard</span><span class="c-verdict">Verdict</span><span>Reason</span></div>
<div class="lanes">${lanes}</div>
<div class="artifact">
  <div class="art-head"><span class="art-lbl">Actual stderr message · no-verify</span><span class="art-exit">exit 2</span></div>
  <p class="art-line"><span class="art-brand">[ai-eng]</span> <span class="art-guard">no-verify:</span> ${escapeHtml(artifactReason)}</p>
</div>
<div class="p-foot"><span>{ai} engineering · src/guards/no-verify.ts · src/guards/wrap.ts</span><span>not every answer is a refusal</span></div>
</div>`,
    `${panelFrameCss(theme)}
.cols{display:grid;grid-template-columns:288px 86px 122px minmax(0,1fr);gap:12px;padding:0 18px 8px;font:600 13.5px/1 ${MONO};letter-spacing:.12em;text-transform:uppercase;color:${theme.panelMuted}}
.cols .c-verdict{padding-left:30px}
.lanes{display:grid;gap:9px}
.lane{display:grid;grid-template-columns:288px 86px 122px minmax(0,1fr);gap:12px;align-items:center;border:1px solid ${theme.border};border-radius:12px;background:${theme.raised};padding:13px 18px}
.cmd{display:flex;align-items:baseline;gap:7px;font:500 14px/1.35 ${MONO};color:${theme.ink};white-space:nowrap}
.prompt{color:${theme.accent};font-weight:700}
.prompt.is-edit{color:${theme.badText}}
.flag{background:color-mix(in srgb,${theme.bad} 16%,transparent);color:${theme.badText};border:1px solid color-mix(in srgb,${theme.bad} 55%,transparent);border-radius:5px;padding:1px 5px;font-weight:700}
.flag.is-rewrite{background:color-mix(in srgb,${theme.good} 16%,transparent);color:${theme.goodText};border-color:color-mix(in srgb,${theme.good} 55%,transparent)}
.guard{font:600 13.5px/1 ${MONO};color:${theme.muted};white-space:nowrap}
.guard.is-rewrite{color:${theme.goodText}}
.verdict{display:flex;align-items:center;gap:8px}
.arrow{flex:0 0 auto;display:block}
.pill{display:inline-flex;align-items:center;justify-content:center;font:700 13.5px/1 ${MONO};letter-spacing:.03em;padding:5px 11px;border-radius:999px;white-space:nowrap}
.pill.is-deny{border:1px solid ${theme.bad};color:${theme.badText};background:color-mix(in srgb,${theme.bad} 13%,transparent)}
.pill.is-rewrite{border:1px solid ${theme.good};color:${theme.goodText};background:color-mix(in srgb,${theme.good} 13%,transparent)}
.reason{font:400 14px/1.4 ${SANS};color:${theme.muted};text-wrap:balance}
.artifact{margin-top:14px;border:1px solid ${theme.border};border-radius:12px;background:${theme.well};padding:14px 20px}
.art-head{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:8px;padding-bottom:8px;border-bottom:1px solid ${theme.hairline}}
.art-lbl{font:600 13.5px/1 ${MONO};letter-spacing:.1em;text-transform:uppercase;color:${theme.muted}}
.art-exit{font:700 13.5px/1 ${MONO};color:${theme.badText}}
.art-line{font:500 13.5px/1.55 ${MONO};color:${theme.ink}}
.art-brand{color:${theme.goodText};font-weight:700}
.art-guard{color:${theme.badText};font-weight:700}`,
  );
}

/** Section 02: three side-by-side receipt cards showing accumulation, plus the log-not-proof caveat given typographic weight. */
function receiptsLedgerPage(theme: Theme): string {
  const cards = SAMPLE_RECEIPTS.map((receipt) => {
    const isDeny = receipt.outcome === "deny";
    const date = receipt.ts.slice(0, 10);
    const time = `${receipt.ts.slice(11, 19)}Z`;
    const shortName = `…-${receiptEventName(receipt.event)}-${receipt.operation_id}.json`;
    const guardValue = receipt.guards.denied_by ?? "none";
    const ranCount = receipt.guards.ran.length;
    const totalGuards = guardCountFor(receipt.event, receipt.tool);
    const guardClass = isDeny ? "val is-bad" : "val is-muted";
    const pillClass = isDeny ? "pill is-deny" : "pill is-allow";
    return `<article class="rcpt">
  <header class="rcpt-head"><span class="rcpt-id">${escapeHtml(shortName)}</span><span class="rcpt-ts">${escapeHtml(date)} · ${escapeHtml(time)}</span></header>
  <dl class="fields">
    <div class="row"><dt>Tried</dt><dd class="val">${escapeHtml(receipt.tool)}</dd></div>
    <div class="row"><dt>Denied by</dt><dd class="${guardClass}">${escapeHtml(guardValue)}</dd></div>
    <div class="row"><dt>Latency</dt><dd class="val num">${receipt.latency_ms} ms</dd></div>
    <div class="row"><dt>Outcome</dt><dd><span class="${pillClass}">${escapeHtml(receipt.outcome)}</span></dd></div>
  </dl>
  <p class="rcpt-meta">${escapeHtml(receipt.surface)} · ${ranCount} of ${totalGuards} ran</p>
</article>`;
  }).join("");
  return page(
    `<div id="asset"><i class="corner tl"></i><i class="corner tr"></i><i class="corner bl"></i><i class="corner br"></i>
<div class="p-top"><span class="p-eyebrow">02 / Receipts</span><span class="p-tag">.ai-engineering/receipts/</span></div>
<h2 class="p-title">${withAccent("Three verdicts, three files in your repo", "files")}</h2>
<div class="cards">${cards}</div>
<div class="caveat">
  <div class="caveat-top"><span class="caveat-chip">${escapeHtml(RECEIPT_CAVEAT.label)}</span><strong class="caveat-head">${escapeHtml(RECEIPT_CAVEAT.headline)}</strong></div>
  <p class="caveat-body">${withCode(RECEIPT_CAVEAT.detail)}</p>
</div>
<div class="p-foot"><span>{ai} engineering · src/receipts.ts</span><span>&lt;ISO&gt;-&lt;event&gt;-&lt;id&gt;.json · + denies.json</span></div>
</div>`,
    `${panelFrameCss(theme)}
.cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}
.rcpt{border:1px solid ${theme.border};border-radius:12px;background:${theme.raised};padding:18px 20px 16px;display:flex;flex-direction:column;gap:12px}
.rcpt-head{display:flex;flex-direction:column;gap:5px;padding-bottom:10px;border-bottom:1px solid ${theme.hairline}}
.rcpt-id{font:700 13.5px/1.2 ${MONO};color:${theme.ink};white-space:nowrap}
.rcpt-ts{font:500 13.5px/1 ${MONO};font-variant-numeric:tabular-nums;color:${theme.muted}}
.fields{display:grid;gap:10px}
.row{display:flex;justify-content:space-between;align-items:center;gap:10px}
dt{font:600 13.5px/1 ${MONO};letter-spacing:.08em;text-transform:uppercase;color:${theme.muted}}
dd{margin:0}
.val{font:700 14.5px/1.2 ${MONO};color:${theme.ink}}
.val.num{font-variant-numeric:tabular-nums}
.val.is-bad{color:${theme.badText}}
.val.is-muted{color:${theme.muted};font-weight:500}
.pill{display:inline-flex;align-items:center;justify-content:center;font:700 13.5px/1 ${MONO};letter-spacing:.04em;padding:5px 12px;border-radius:999px;white-space:nowrap}
.pill.is-deny{border:1px solid ${theme.bad};color:${theme.badText};background:color-mix(in srgb,${theme.bad} 13%,transparent)}
.pill.is-allow{border:1px solid ${theme.good};color:${theme.goodText};background:color-mix(in srgb,${theme.good} 13%,transparent)}
.rcpt-meta{margin-top:2px;padding-top:10px;border-top:1px solid ${theme.hairline};font:500 13.5px/1.2 ${MONO};font-variant-numeric:tabular-nums;color:${theme.muted}}
.caveat{margin-top:18px;border:1.5px dashed ${theme.warn};border-radius:12px;background:${theme.raised};padding:18px 22px;display:flex;flex-direction:column;gap:8px}
.caveat-top{display:flex;align-items:center;flex-wrap:wrap;gap:10px 14px}
.caveat-chip{font:700 13.5px/1 ${MONO};letter-spacing:.1em;text-transform:uppercase;padding:5px 12px;border-radius:999px;border:1px solid ${theme.warn};color:${theme.warnText};background:color-mix(in srgb,${theme.warn} 12%,transparent)}
.caveat-head{font:800 22px/1.15 ${SANS};font-stretch:92%;letter-spacing:-.02em;color:${theme.ink}}
.caveat-body{font:400 15px/1.45 ${SANS};color:${theme.muted}}
.caveat-body code{font:500 13.5px/1 ${MONO};color:${theme.ink}}`,
  );
}

/** Six tiles, three across: a title and its count, one plain line, then the names in small mono type. */
function skillsGridPage(theme: Theme): string {
  const tiles = SKILL_GROUPS.map((group) => {
    const names = group.skills.map((name) => `<span class="skill">${escapeHtml(name)}${name === group.star ? '<i class="star">★</i>' : ""}</span>`).join("");
    return `<section><p class="top"><b>${escapeHtml(group.title)}</b><span class="count">${group.skills.length}</span></p><p class="line">${escapeHtml(group.line)}</p><p class="names">${names}</p></section>`;
  }).join("");
  return page(
    `<div id="asset">${tiles}</div>`,
    `#asset{width:${GRID_WIDTH}px;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}
section{border:1px solid ${theme.border};border-radius:12px;background:${theme.raised};padding:20px;display:flex;flex-direction:column;gap:10px}
.top{display:flex;align-items:center;justify-content:space-between;gap:8px}
.top b{font:800 20px/1.15 ${SANS};font-stretch:92%;letter-spacing:-.02em;color:${theme.ink}}
.count{font:600 12px/1.5 ${MONO};padding:2px 9px;border-radius:999px;border:1px solid ${theme.good};color:${theme.goodText}}
.line{font:400 15px/1.45 ${SANS};color:${theme.muted}}
.names{display:flex;flex-wrap:wrap;gap:6px;padding-top:6px}
.skill{font:500 12.5px/1 ${MONO};color:${theme.ink};padding:5px 8px;border-radius:6px;border:1px solid ${theme.border};background:${theme.field}}
.star{font-style:normal;color:${theme.accent};margin-left:5px}`,
  );
}

function figurePage(figureIndex: number, mode: Mode): string {
  const vars = Object.entries({ ...DIAGRAM_VARS[mode], "--mono": MONO, "--sans": SANS }).map(([name, value]) => `${name}:${value}`).join(";");
  return page(`<div id="asset">${figureSvg(FIGURES[figureIndex] as (typeof FIGURES)[number])}</div>`, `:root{${vars}}#asset{width:${FIGURE_WIDTH}px;line-height:0}\n${FIGURE_CSS}`);
}

// ---------------------------------------------------------------------------
// Rendering
// ---------------------------------------------------------------------------

type Job = { file: string; html: string; families: string[]; isFigure: boolean; minPxAt800?: number };

function jobs(): Job[] {
  return MODES.flatMap((mode) => {
    const theme = THEMES[mode];
    const both = ["Archivo", "JetBrains Mono"];
    return [
      ...HEADINGS.map((heading, index) => ({ file: headingFile(heading.slug, mode), html: headingPage(heading, index, theme), families: both, isFigure: false })),
      ...BUTTONS.map((button) => ({ file: buttonFile(button.slug, mode), html: buttonPage(button, theme), families: ["Archivo"], isFigure: false })),
      ...CARDS.map((card) => ({ file: cardFile(card.slug, mode), html: cardPage(card, theme), families: both, isFigure: false })),
      ...FIGURES.map((figure, index) => ({ file: figureFile(figure, mode), html: figurePage(index, mode), families: both, isFigure: true })),
      { file: guardsRefusedFile(mode), html: guardsRefusedPage(theme), families: both, isFigure: false, minPxAt800: 11 },
      { file: receiptsLedgerFile(mode), html: receiptsLedgerPage(theme), families: both, isFigure: false, minPxAt800: 11 },
      { file: skillsGridFile(mode), html: skillsGridPage(theme), families: both, isFigure: false },
      { file: heroFile(mode), html: heroPage(theme), families: both, isFigure: false },
    ];
  });
}

/** Type and line art stay lossless: a lossy pass would fringe every glyph edge. */
function encode(png: string, webp: string): void {
  const result = Bun.spawnSync(["cwebp", "-quiet", "-lossless", "-z", "9", "-exact", png, "-o", webp]);
  if (!result.success) throw new Error(`cwebp failed for ${webp}: ${result.stderr.toString()}`);
}

async function main(): Promise<void> {
  const { chromium } = await import("playwright-core");
  mkdirSync(OUT_DIR, { recursive: true });
  const scratch = mkdtempSync(join(tmpdir(), "readme-assets-"));
  const browser = await chromium.launch({ channel: "chrome" });
  try {
    const only = process.argv[2] ?? "";
    for (const job of jobs().filter((candidate) => candidate.file.includes(only))) {
      const context = await browser.newContext({ deviceScaleFactor: 2 });
      const tab = await context.newPage();
      await tab.setContent(job.html, { waitUntil: "networkidle" });
      await tab.evaluate(() => document.fonts.ready);
      // A silent fallback font would ship wrong type that still looks plausible.
      const hasFonts = await tab.evaluate((wanted) => wanted.every((family) => [...document.fonts].some((face) => face.family === family && face.status === "loaded")), job.families);
      if (!hasFonts) throw new Error(`Google Fonts did not load for ${job.file}; check the network and run again`);
      const box = tab.locator("#asset");
      const overflow = job.isFigure ? await svgTextOverflow(tab) : await boxTextOverflow(box);
      if (overflow) throw new Error(`${job.file}: ${overflow}`);
      if (job.minPxAt800 !== undefined) {
        const tooSmall = await boxMinFontAt800(box, job.minPxAt800);
        if (tooSmall) throw new Error(`${job.file}: ${tooSmall}`);
      }
      const png = join(scratch, `${job.file}.png`);
      await box.screenshot({ path: png, omitBackground: true });
      encode(png, join(OUT_DIR, job.file));
      await context.close();
      console.log(`ok  ${job.file}`);
    }
  } finally {
    await browser.close();
    rmSync(scratch, { recursive: true, force: true });
  }
}

async function boxTextOverflow(box: Locator): Promise<string | null> {
  const culprit = await box.evaluate((element): string | null => {
    if (element.scrollWidth > element.clientWidth || element.scrollHeight > element.clientHeight) return `the canvas scrolls (${element.scrollWidth}x${element.scrollHeight} in ${element.clientWidth}x${element.clientHeight})`;
    const style = getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    const contentLeft = rect.left + Number.parseFloat(style.borderLeftWidth) + Number.parseFloat(style.paddingLeft);
    const contentRight = rect.right - Number.parseFloat(style.borderRightWidth) - Number.parseFloat(style.paddingRight);
    const contentTop = rect.top + Number.parseFloat(style.borderTopWidth) + Number.parseFloat(style.paddingTop);
    const contentBottom = rect.bottom - Number.parseFloat(style.borderBottomWidth) - Number.parseFloat(style.paddingBottom);
    const slack = 0.5;
    for (const child of element.querySelectorAll("*")) {
      // A box that draws outside itself on purpose (the hero's crosshairs, the glow round the mark) says so with data-overhang.
      if (!child.hasAttribute("data-overhang") && child.scrollWidth > child.clientWidth) return `<${child.tagName.toLowerCase()} class="${child.className}"> is wider than its box`;
      if (getComputedStyle(child).position === "absolute") continue;
      const childRect = child.getBoundingClientRect();
      if (
        childRect.left < contentLeft - slack ||
        childRect.right > contentRight + slack ||
        childRect.top < contentTop - slack ||
        childRect.bottom > contentBottom + slack
      ) {
        return `<${child.tagName.toLowerCase()} class="${child.className}"> leaves the canvas content box`;
      }
    }
    return null;
  });
  return culprit ? `text overflows its canvas: ${culprit}` : null;
}

/** Every visible text node must stay at or above `floorPx` when GitHub renders the image at 800 px wide. */
async function boxMinFontAt800(box: Locator, floorPx: number): Promise<string | null> {
  return box.evaluate((element, minPx): string | null => {
    const width = element.getBoundingClientRect().width;
    const scale = Math.min(1, 800 / width);
    const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
    let current: Node | null;
    while ((current = walker.nextNode()) !== null) {
      if (!current.textContent?.trim()) continue;
      const host = current.parentElement;
      if (!host) continue;
      const computed = Number.parseFloat(getComputedStyle(host).fontSize);
      const rendered = computed * scale;
      if (rendered < minPx - 0.05) {
        return `"${current.textContent.trim().slice(0, 32)}" renders at ${rendered.toFixed(1)}px at 800px wide (floor ${minPx}px)`;
      }
    }
    return null;
  }, floorPx);
}

/** SVG text never wraps: any line that leaves its node, column or the canvas is a layout bug. */
async function svgTextOverflow(tab: Page): Promise<string | null> {
  return tab.evaluate(() => {
    const svg = document.querySelector("svg") as SVGSVGElement;
    const canvas = svg.viewBox.baseVal.width;
    for (const text of svg.querySelectorAll("text")) {
      const box = (text as SVGTextElement).getBBox();
      const container = text.parentElement?.querySelector(":scope > rect") as SVGRectElement | null;
      const limit = container ? container.x.baseVal.value + container.width.baseVal.value - 8 : canvas - 12;
      if (box.x + box.width > limit) return `"${text.textContent}" runs past ${Math.round(limit)}px (ends at ${Math.round(box.x + box.width)})`;
    }
    return null;
  });
}

if (import.meta.main) await main();
