#!/usr/bin/env bun
// scripts/readme-assets.ts — renders the README's images from the repo, with no image model.
//
// Every pixel is typeset or drawn here, from brand/tokens.json and the brand's own component
// styles, in dark and light: the hero, the section headings, the two buttons, the "blocks" and
// "informs" cards, the skills grid and the five figures (scripts/readme-figures.ts). A model misspells and its
// output cannot be re-rendered; this can. Change a line in a table below, run
// `bun scripts/readme-assets.ts`, commit the images it wrote.
//
// The four terminal stills in .github/assets/readme/ are not drawn here: VHS records them
// from real hook payloads (.github/assets/tapes/stills.tape).
//
// Pass a filename fragment to render only the matching files (`bun scripts/readme-assets.ts figure-`).
// Needs Google Chrome (playwright-core drives it, as scripts/artifact-axe.ts does), network
// for Google Fonts at render time only, and `cwebp`. The README itself loads no font.

import { mkdirSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import type { Locator, Page } from "playwright-core";
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

/** The hero: the brand's artifact hero (field, grid, corner brackets, the {ai} chip, display type, mono line). */
export const HERO = {
  eyebrow: "{ai} engineering",
  claim: "Guardrails for the AI Coding Agents you already run",
  accent: "Guardrails",
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
    bullets: ["`--no-verify`, `git commit -n` and `HUSKY=0`", "a comment that silences a linter", "an edit to `AGENTS.md`, the hooks or `.ai-engineering/`"],
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

const GRID_WIDTH = 880;
const HEADING_WIDTH = 800;
const HEADING_HEIGHT = 112;
const BUTTON_HEIGHT = 48;
const CARD_WIDTH = 420;

export const headingFile = (slug: string, mode: Mode) => `heading-${slug}-${mode}.webp`;
export const buttonFile = (slug: string, mode: Mode) => `button-${slug}-${mode}.webp`;
export const heroFile = (mode: Mode) => `hero-${mode}.webp`;
export const cardFile = (slug: string, mode: Mode) => `card-${slug}-${mode}.webp`;
export const skillsGridFile = (mode: Mode) => `skills-grid-${mode}.webp`;

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
  ink: string;
  muted: string;
  accent: string;
  border: string;
  buttonInk: string;
  fill: string;
  grid: string;
  glow: string;
  bad: string;
  badText: string;
  good: string;
  goodText: string;
};

// Light is the ivory surface, the one light surface the brand names (tokens.json semantic.surface.surface-ivory).
export const THEMES: Record<Mode, Theme> = {
  dark: {
    field: colour("black"), raised: colour("gray.dark4"), ink: colour("white"), muted: colour("gray.light1"), accent: colour("green.base"),
    border: colour("gray.base"), buttonInk: colour("black"), fill: colour("green.base"), grid: `${colour("gray.dark2")}4D`, glow: `${colour("gray.dark4")}66`,
    bad: colour("red.light1"), badText: colour("red.light2"), good: colour("green.base"), goodText: colour("green.light1"),
  },
  light: {
    field: colour("gray.light3"), raised: colour("white"), ink: colour("black"), muted: colour("gray.dark1"), accent: colour("green.dark2"),
    border: colour("gray.base"), buttonInk: colour("black"), fill: colour("green.base"), grid: `${colour("gray.light1")}73`, glow: `${colour("green.light3")}99`,
    bad: colour("red.dark2"), badText: colour("red.dark2"), good: colour("green.dark2"), goodText: colour("green.dark2"),
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

/** The brand hero (brand/components.css `.hero`): a faint grid, four green brackets, the {ai} chip, display type, a mono line. */
function heroPage(theme: Theme): string {
  return page(
    `<div id="asset"><i class="corner tl"></i><i class="corner tr"></i><i class="corner bl"></i><i class="corner br"></i>
<div class="mark"><em>{</em>ai<em>}</em></div><h1>${withAccent(HERO.claim, HERO.accent)}</h1><p class="meta">${escapeHtml(HERO.eyebrow)}</p></div>`,
    `#asset{position:relative;overflow:hidden;width:${HERO.width}px;height:${HERO.height}px;border-radius:12px;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:0 96px;
background-color:${theme.field};background-image:linear-gradient(${theme.grid} 1px,transparent 1px),linear-gradient(90deg,${theme.grid} 1px,transparent 1px),radial-gradient(ellipse 80% 60% at 50% 0%,${theme.glow},transparent);background-size:32px 32px,32px 32px,100% 100%}
.corner{position:absolute;width:26px;height:26px;border:0 solid ${theme.accent};opacity:.9}
.tl{top:20px;left:20px;border-width:2px 0 0 2px}.tr{top:20px;right:20px;border-width:2px 2px 0 0}.bl{bottom:20px;left:20px;border-width:0 0 2px 2px}.br{bottom:20px;right:20px;border-width:0 2px 2px 0}
.mark{display:flex;width:56px;height:56px;align-items:center;justify-content:center;border:1px solid ${theme.border};border-radius:8px;background:${theme.raised};font:700 20px/1 ${MONO};letter-spacing:-.04em;color:${theme.ink};margin-bottom:28px}
.mark em{color:${theme.accent}}
h1{font:800 58px/1.08 ${SANS};font-stretch:92%;letter-spacing:-.03em;color:${theme.ink};max-width:1100px}h1 em{color:${theme.accent}}
.meta{font:500 14px/1.6 ${MONO};letter-spacing:.02em;color:${theme.muted};margin-top:28px}`,
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

type Job = { file: string; html: string; families: string[]; isFigure: boolean };

function jobs(): Job[] {
  return MODES.flatMap((mode) => {
    const theme = THEMES[mode];
    const both = ["Archivo", "JetBrains Mono"];
    return [
      ...HEADINGS.map((heading, index) => ({ file: headingFile(heading.slug, mode), html: headingPage(heading, index, theme), families: both, isFigure: false })),
      ...BUTTONS.map((button) => ({ file: buttonFile(button.slug, mode), html: buttonPage(button, theme), families: ["Archivo"], isFigure: false })),
      ...CARDS.map((card) => ({ file: cardFile(card.slug, mode), html: cardPage(card, theme), families: both, isFigure: false })),
      ...FIGURES.map((figure, index) => ({ file: figureFile(figure, mode), html: figurePage(index, mode), families: both, isFigure: true })),
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
  const isOverflowing = await box.evaluate((element) => {
    if (element.scrollWidth > element.clientWidth || element.scrollHeight > element.clientHeight) return true;
    const style = getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    const contentLeft = rect.left + Number.parseFloat(style.borderLeftWidth) + Number.parseFloat(style.paddingLeft);
    const contentRight = rect.right - Number.parseFloat(style.borderRightWidth) - Number.parseFloat(style.paddingRight);
    const contentTop = rect.top + Number.parseFloat(style.borderTopWidth) + Number.parseFloat(style.paddingTop);
    const contentBottom = rect.bottom - Number.parseFloat(style.borderBottomWidth) - Number.parseFloat(style.paddingBottom);
    const slack = 0.5;
    for (const child of element.querySelectorAll("*")) {
      if (child.scrollWidth > child.clientWidth) return true;
      if (getComputedStyle(child).position === "absolute") continue;
      const childRect = child.getBoundingClientRect();
      if (
        childRect.left < contentLeft - slack ||
        childRect.right > contentRight + slack ||
        childRect.top < contentTop - slack ||
        childRect.bottom > contentBottom + slack
      ) {
        return true;
      }
    }
    return false;
  });
  return isOverflowing ? "text overflows its canvas" : null;
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
