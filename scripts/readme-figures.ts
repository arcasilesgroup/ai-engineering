// scripts/readme-figures.ts — the README's five figures, drawn from the repository.
//
// Each figure is data (nodes, edges, a caption, a text version) plus one small drawing
// routine. `scripts/readme-assets.ts` rasterises them, dark and light, in the shape the
// brand's own artifacts use: rounded nodes with a mono title and a sans one-liner, curved
// connectors, and a dashed amber line for a check rather than a flow. The `.dg-*` rules
// come from brand/components.css itself, and the colours from brand/tokens.json, so a
// figure cannot drift from the system it imitates.
//
// Every claim in a figure names the file that backs it. The README repeats each figure's
// `alt`, `caption` and `textVersion` word for word; tests/readme-assets.spec.ts fails if
// the two disagree.

import { readFileSync } from "node:fs";
import { join } from "node:path";

const ROOT = join(import.meta.dir, "..");

export type Mode = "dark" | "light";

type Families = Record<string, string | Record<string, string>>;
const families = (JSON.parse(readFileSync(join(ROOT, "brand", "tokens.json"), "utf8")) as { families: Families }).families;

/** `green.base` or `white` to its hex, so a token rename fails here instead of drifting. */
export function colour(path: string): string {
  const value = path.split(".").reduce<unknown>((node, key) => (node as Record<string, unknown> | undefined)?.[key], families);
  if (typeof value !== "string") throw new Error(`brand/tokens.json has no colour "${path}"`);
  return value;
}

/** The variables the brand's `.dg-*` rules read, filled for each mode. Light uses the ivory surface. */
export const DIAGRAM_VARS: Record<Mode, Record<string, string>> = {
  dark: {
    "--surface": colour("gray.dark4"), "--surface-2": colour("gray.dark3"), "--line-strong": colour("gray.base"),
    "--accent": colour("green.base"), "--accent-dim": colour("green.light1"), "--text": colour("white"), "--dim": colour("gray.light1"),
    "--comment": colour("gray.light1"), "--warn": colour("yellow.base"), "--bad": colour("red.light1"), "--ok": colour("green.base"),
  },
  light: {
    "--surface": colour("white"), "--surface-2": colour("gray.light3"), "--line-strong": colour("gray.base"),
    "--accent": colour("green.dark2"), "--accent-dim": colour("green.dark2"), "--text": colour("black"), "--dim": colour("gray.dark2"),
    "--comment": colour("gray.dark1"), "--warn": colour("yellow.dark2"), "--bad": colour("red.dark2"), "--ok": colour("green.dark2"),
  },
};

/** The brand's own `.dg-*` rules, read from the component file rather than retyped. */
function brandDiagramRules(): string {
  const css = readFileSync(join(ROOT, "brand", "components.css"), "utf8");
  const rules = css.split("\n").filter((line) => line.startsWith(".dg-"));
  if (rules.length < 8) throw new Error("brand/components.css lost its .dg-* diagram rules");
  return rules.join("\n");
}

// A README image is shown at about 830 px, so the type is set larger than the artifact's.
export const FIGURE_CSS = `${brandDiagramRules()}
.dg-node .t{font-size:15px}.dg-node .d{font-size:13px}.dg-lbl{font-size:12px}
.dg-node.is-deny rect{stroke:var(--bad);stroke-width:1.5}
.dg-node.is-ok rect{stroke:var(--accent);stroke-width:1.5}
.dg-node.is-gate rect{stroke-width:1.5}
.dg-edge{stroke:var(--accent)}.dg-head{fill:var(--accent)}
.dg-lbl.is-key{fill:var(--comment);letter-spacing:.12em;text-transform:uppercase;font-size:11px}
.dg-col{fill:var(--surface);stroke:var(--line-strong);stroke-width:1}
.dg-col.is-ok{stroke:var(--accent);stroke-width:1.5}.dg-col.is-gate{stroke:var(--warn);stroke-width:1.5;stroke-dasharray:5 4}
.dg-chip rect{fill:var(--surface-2);stroke:var(--line-strong)}.dg-chip text{fill:var(--text);font-family:var(--mono);font-size:13px}
.dg-head-t{fill:var(--text);font-family:var(--mono);font-size:14px;font-weight:700}
.dg-head-t.is-ok{fill:var(--accent)}.dg-head-t.is-gate{fill:var(--warn)}
.dg-note{fill:var(--dim);font-family:var(--sans);font-size:13px}
.dg-person{fill:var(--accent)}`;

// ---------------------------------------------------------------------------
// Drawing parts
// ---------------------------------------------------------------------------

type Point = [number, number];
type Kind = "plain" | "source" | "gate" | "deny" | "ok";
type NodeSpec = { x: number; y: number; w: number; title: string; lines?: string[]; kind?: Kind; h?: number };

const escapeXml = (text: string): string => text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

/** A node is as tall as its text: a title, then each one-liner. Two figures place edges by it. */
export const nodeHeight = (lineCount: number): number => (lineCount === 0 ? 44 : 66 + 18 * (lineCount - 1));

function node(spec: NodeSpec): string {
  const lines = spec.lines ?? [];
  const height = spec.h ?? nodeHeight(lines.length);
  const kindClass = spec.kind && spec.kind !== "plain" ? ` is-${spec.kind}` : "";
  const detail = lines.map((line, index) => `<text class="d" x="${spec.x + 16}" y="${spec.y + 50 + index * 18}">${escapeXml(line)}</text>`).join("");
  return `<g class="dg-node${kindClass}"><rect x="${spec.x}" y="${spec.y}" width="${spec.w}" height="${height}" rx="10"/><text class="t" x="${spec.x + 16}" y="${spec.y + 28}">${escapeXml(spec.title)}</text>${detail}</g>`;
}

type Direction = "h" | "v";
// `turn` is where along the gap the curve does its turning, 0 to 1. Two edges that share both
// anchors (the deny path and the dashed crash path in figure 1) take different turns, so the
// dashed one stays visible beside the solid one instead of hiding under it.
type EdgeSpec = { from: Point; to: Point; direction?: Direction; isCheck?: boolean; turn?: number };

/**
 * A cubic connector that ends in an arrowhead; a dashed amber one is a check, not a flow.
 * Both control points sit on the travel axis, so the curve leaves and arrives flat: a fan from
 * one anchor reads as one stem opening into branches, and every arrowhead lands square.
 */
function edge(spec: EdgeSpec): string {
  const [x1, y1] = spec.from;
  const [x2, y2] = spec.to;
  const checkClass = spec.isCheck ? " is-check" : "";
  const turn = spec.turn ?? 0.5;
  const inset = 8;
  if ((spec.direction ?? "h") === "h") {
    const stop = x2 - inset;
    const span = stop - x1;
    return `<path class="dg-edge${checkClass}" d="M${x1} ${y1} C${x1 + span * turn} ${y1} ${x1 + span * turn} ${y2} ${stop} ${y2}"/><path class="dg-head${checkClass}" d="M${x2 - 9} ${y2 - 5} L${x2} ${y2} L${x2 - 9} ${y2 + 5} Z"/>`;
  }
  const isDown = y2 > y1;
  const stop = isDown ? y2 - inset : y2 + inset;
  const span = stop - y1;
  const head = isDown ? `M${x2 - 5} ${y2 - 9} L${x2} ${y2} L${x2 + 5} ${y2 - 9} Z` : `M${x2 - 5} ${y2 + 9} L${x2} ${y2} L${x2 + 5} ${y2 + 9} Z`;
  return `<path class="dg-edge${checkClass}" d="M${x1} ${y1} C${x1} ${y1 + span * turn} ${x2} ${y1 + span * turn} ${x2} ${stop}"/><path class="dg-head${checkClass}" d="${head}"/>`;
}

type Side = "left" | "right" | "top" | "bottom";

/** The one point where edges meet a side of a node: its middle, never a corner. */
function anchor(spec: NodeSpec, side: Side): Point {
  const height = spec.h ?? nodeHeight(spec.lines?.length ?? 0);
  if (side === "left") return [spec.x, spec.y + height / 2];
  if (side === "right") return [spec.x + spec.w, spec.y + height / 2];
  if (side === "top") return [spec.x + spec.w / 2, spec.y];
  return [spec.x + spec.w / 2, spec.y + height];
}

type Branch = { at: Point; isCheck?: boolean; turn?: number };

/** Every edge out of one node starts at one anchor, then fans out. */
function fanOut(from: Point, branches: Branch[], direction: Direction = "h"): string {
  return branches.map(({ at, ...rest }) => edge({ from, to: at, direction, ...rest })).join("");
}

/** Every edge into one node lands on one anchor. */
function fanIn(branches: Branch[], to: Point, direction: Direction = "h"): string {
  return branches.map(({ at, ...rest }) => edge({ from: at, to, direction, ...rest })).join("");
}

const label = (x: number, y: number, text: string, extraClass = ""): string => `<text class="dg-lbl${extraClass}" x="${x}" y="${y}">${escapeXml(text)}</text>`;

/** The key every figure carries, so the dashed amber line is never a guess. */
function legend(x: number, y: number, solidMeaning: string | null, dashedMeaning: string): string {
  const dashedAt = solidMeaning === null ? x : x + 36 + solidMeaning.length * 7 + 24;
  const solid = solidMeaning === null ? "" : `<path class="dg-edge" d="M${x} ${y} L${x + 28} ${y}"/>${label(x + 36, y + 4, solidMeaning)}`;
  return `<g>${solid}<path class="dg-edge is-check" d="M${dashedAt} ${y} L${dashedAt + 28} ${y}"/>${label(dashedAt + 36, y + 4, dashedMeaning)}</g>`;
}

export const FIGURE_WIDTH = 960;

type Figure = {
  n: number;
  slug: string;
  height: number;
  alt: string;
  caption: string;
  textVersion: string[];
  svg: () => string;
};

// ---------------------------------------------------------------------------
// Figure 1: what happens to one tool call
// ---------------------------------------------------------------------------

function toolCallFigure(): string {
  const agent: NodeSpec = { x: 24, y: 170, w: 170, title: "agent", lines: ["proposes a tool call", "before it runs"], kind: "source" };
  const chain: NodeSpec = { x: 250, y: 161, w: 250, title: "ai-eng chain", lines: ["the host sends it the call", "guards judge it in a fixed", "order; the first deny wins"], kind: "ok" };
  const allow: NodeSpec = { x: 550, y: 40, w: 170, title: "allow", lines: ["the call goes ahead; a", "test run is rewritten"] };
  const annotate: NodeSpec = { x: 550, y: 170, w: 170, title: "annotate", lines: ["the call goes ahead,", "a review note rides along"] };
  const deny: NodeSpec = { x: 550, y: 300, w: 170, title: "deny", lines: ["the call is refused,", "with the reason"], kind: "deny" };
  const toolRuns: NodeSpec = { x: 770, y: 105, w: 166, title: "tool runs", lines: ["git, the editor", "or the shell"] };
  const toolNeverRuns: NodeSpec = { x: 770, y: 300, w: 166, title: "tool never runs", lines: ["the agent reads why", "and what to do"], kind: "deny" };
  const receipts: NodeSpec = { x: 195, y: 404, w: 360, title: ".ai-engineering/receipts/", lines: ["one JSON file per verdict, in your repository"] };
  return [
    ...[agent, chain, allow, annotate, deny, toolRuns, toolNeverRuns, receipts].map(node),
    edge({ from: anchor(agent, "right"), to: anchor(chain, "left") }),
    fanOut(anchor(chain, "right"), [
      { at: anchor(allow, "left") },
      { at: anchor(annotate, "left") },
      { at: anchor(deny, "left"), turn: 0.3 },
      { at: anchor(deny, "left"), isCheck: true, turn: 0.75 },
    ]),
    fanIn([{ at: anchor(allow, "right") }, { at: anchor(annotate, "right") }], anchor(toolRuns, "left")),
    edge({ from: anchor(deny, "right"), to: anchor(toolNeverRuns, "left") }),
    edge({ from: anchor(chain, "bottom"), to: anchor(receipts, "top"), direction: "v" }),
    label(388, 345, "every verdict"),
    label(770, 286, "denied before it runs", " is-key"),
    legend(24, 28, "a step", "a crash or an unsure guard ends in deny"),
  ].join("");
}

// ---------------------------------------------------------------------------
// Figure 2: the build loop, and the two places it stops for a person
// ---------------------------------------------------------------------------

/** A small person and a two-line label: the sign for a stop where a human decides. */
function stopSign(x: number, y: number, first: string, second: string): string {
  const person = `<g class="dg-person"><circle cx="${x + 5}" cy="${y - 9}" r="3.4"/><path d="M${x} ${y - 1} a5 4.4 0 0 1 10 0 Z"/></g>`;
  return `${person}${label(x + 16, y - 4, first)}${label(x + 16, y + 10, second)}`;
}

function buildLoopFigure(): string {
  const top = 64;
  const height = 84;
  const idea: NodeSpec = { x: 24, y: top, w: 140, h: height, title: "your idea", lines: ["a feature, in", "your own words"], kind: "source" };
  const plan: NodeSpec = { x: 284, y: top, w: 168, h: height, title: "plan", lines: ["numbered checkpoints,", "smallest first"] };
  const built: NodeSpec = { x: 496, y: top, w: 200, h: height, title: "checkpoints", lines: ["built one at a time, each", "gated before the next"], kind: "ok" };
  const ship: NodeSpec = { x: 808, y: top, w: 128, h: height, title: "ship it", lines: ["pull request or", "local merge"] };
  const gates: NodeSpec = { x: 496, y: 196, w: 200, h: height, title: "its gates", lines: ["a checkpoint that fails", "a gate does not move on"], kind: "gate" };
  return [
    ...[idea, plan, built, ship, gates].map(node),
    edge({ from: anchor(idea, "right"), to: anchor(plan, "left") }),
    edge({ from: anchor(plan, "right"), to: anchor(built, "left") }),
    edge({ from: anchor(built, "right"), to: anchor(ship, "left") }),
    edge({ from: anchor(gates, "top"), to: anchor(built, "bottom"), direction: "v", isCheck: true }),
    stopSign(172, 82, "you approve", "the idea"),
    stopSign(704, 82, "you review", "the app"),
    legend(24, 28, "a step", "a check, not a step"),
  ].join("");
}

// ---------------------------------------------------------------------------
// Figure 3: the layer stack and what only each layer stops
// ---------------------------------------------------------------------------

const LAYERS = [
  { layer: "guard chain", when: "before the tool runs", sees: "the agent's call", stops: "an attempt to skip a check", detail: ["--no-verify, git commit -n, HUSKY=0 and a linter-silencing comment are refused", "before git or the editor runs. A hook cannot see the flag that skips it."] },
  { layer: "git hooks", when: "at commit and push", sees: "the staged change", stops: "a secret in a commit", detail: ["gitleaks reads the staged diff, and diff --check reads the whitespace. It runs for a", "person in Vim too, and for an agent host that has no hook."] },
  { layer: "CI workflows", when: "on the server, after the push", sees: "the pushed branch", stops: "a push that skipped the hooks", detail: ["Typecheck, lint, tests and the scanners run where a laptop cannot switch them off.", "A local --no-verify never reaches this layer."] },
  { layer: "external review", when: "a reader of the diff", sees: "what the change means", stops: "a test deleted or weakened", detail: ["Every layer above passes it: ai-eng does not read test content. Only a reader who", "asks whether the change is right catches it."], isGap: true },
  { layer: "merge", when: "a person says yes", sees: "the whole change", stops: "a change nobody approved", detail: ["A person decides whether it ships. A release reaches npm only from a signed tag", "that a person approved."] },
] as const;

function layerStackFigure(): string {
  const top = 56;
  const rowHeight = 84;
  const rowGap = 16;
  const parts: string[] = [label(24, 30, "layer, in the order met", " is-key"), label(330, 30, "the thing only this layer stops", " is-key")];
  const layerNodes: NodeSpec[] = LAYERS.map((row, index) => ({ x: 24, y: top + index * (rowHeight + rowGap), w: 250, h: rowHeight, title: row.layer, lines: [row.when, row.sees] }));
  LAYERS.forEach((row, index) => {
    const layer = layerNodes[index] as NodeSpec;
    const stops: NodeSpec = { x: 330, y: layer.y, w: 606, h: rowHeight, title: row.stops, lines: [...row.detail], kind: "isGap" in row ? "gate" : "plain" };
    parts.push(node(layer), node(stops), edge({ from: anchor(layer, "right"), to: anchor(stops, "left") }));
    const next = layerNodes[index + 1];
    if (next !== undefined) parts.push(edge({ from: anchor(layer, "bottom"), to: anchor(next, "top"), direction: "v" }));
  });
  parts.push(legend(24, 56 + 5 * rowHeight + 4 * rowGap + 28, "the next layer", "a gap every layer above leaves"));
  return parts.join("");
}

// ---------------------------------------------------------------------------
// Figure 5: the single parse
// ---------------------------------------------------------------------------

const GUARD_PREDICATES = [
  ["no-verify", "is a hook skipped?"],
  ["no-stash", "is a stash created?"],
  ["policy", "is it inside the scope?"],
  ["self-protect", "is a rule edited?"],
  ["lease", "is another session here?"],
  ["injection", "does it carry orders?"],
] as const;

function singleParseFigure(): string {
  const guardTop = 38;
  const guardStep = 76;
  const command: NodeSpec = { x: 24, y: 179, w: 180, title: "one command", lines: ["git commit -n -m fix"], kind: "source" };
  const parse: NodeSpec = { x: 246, y: 161, w: 200, title: "one shell parse", lines: ["src/guards/shell.ts", "reads quotes, escapes,", "substitutions, heredocs"], kind: "ok" };
  const model: NodeSpec = { x: 488, y: 170, w: 210, title: "typed command model", lines: ["segments and their words", "what is code, what is data"], kind: "ok" };
  const contract: NodeSpec = { x: 246, y: 340, w: 452, title: "the check on the one reader", lines: ["tests/shell-guard-contract.spec.ts pins what every guard", "reads. A reader that splits or decodes one character", "differently from the shell fails."], kind: "gate" };
  const guards: NodeSpec[] = GUARD_PREDICATES.map(([name, question], index) => ({ x: 744, y: guardTop + index * guardStep, w: 192, title: name, lines: [question] }));
  return [
    ...[command, parse, model, ...guards, contract].map(node),
    edge({ from: anchor(command, "right"), to: anchor(parse, "left") }),
    edge({ from: anchor(parse, "right"), to: anchor(model, "left") }),
    fanOut(anchor(model, "right"), guards.map((guard) => ({ at: anchor(guard, "left") }))),
    label(744, 26, "guards, each a predicate", " is-key"),
    fanOut(anchor(contract, "top"), [{ at: anchor(parse, "bottom"), isCheck: true }, { at: anchor(model, "bottom"), isCheck: true }], "v"),
    legend(24, 470, "a step", "a test, not a step"),
  ].join("");
}

// ---------------------------------------------------------------------------
// Figure 4: surfaces, from the capability matrix
// ---------------------------------------------------------------------------

const ENFORCED_VERIFIED = ["claude-code", "cursor", "copilot-cli", "copilot-vscode", "opencode", "pi", "oh-my-pi"] as const;
const ENFORCED_UNVERIFIED = ["codex"] as const;
const ADVISORY = ["zed", "agy"] as const;

function chip(x: number, y: number, w: number, text: string): string {
  return `<g class="dg-chip"><rect x="${x}" y="${y}" width="${w}" height="30" rx="7"/><text x="${x + 12}" y="${y + 20}">${escapeXml(text)}</text></g>`;
}

function column(x: number, w: number, kind: "ok" | "gate" | "plain", head: string, subLines: string[], chips: string, notes: string[]): string {
  const headClass = kind === "plain" ? "" : ` is-${kind}`;
  const noteLines = notes.map((note, index) => `<text class="dg-note" x="${x + 16}" y="${300 + index * 18}">${escapeXml(note)}</text>`).join("");
  const sub = subLines.map((line, index) => `<text class="dg-note" x="${x + 16}" y="${76 + index * 18}">${escapeXml(line)}</text>`).join("");
  return `<g><rect class="dg-col${headClass}" x="${x}" y="24" width="${w}" height="336" rx="12"/><text class="dg-head-t${headClass}" x="${x + 16}" y="54">${escapeXml(head)}</text>${sub}${chips}${noteLines}</g>`;
}

function surfacesFigure(): string {
  const firstColumnChips = ENFORCED_VERIFIED.map((host, index) => chip(40 + (index % 2) * 188, 124 + Math.floor(index / 2) * 42, 172, host)).join("");
  const secondColumnChips = ENFORCED_UNVERIFIED.map((host, index) => chip(450, 124 + index * 42, 204, host)).join("");
  const thirdColumnChips = ADVISORY.map((host, index) => chip(698, 124 + index * 42, 222, host)).join("");
  return [
    column(24, 396, "ok", "enforced, verified: 7", ["a denial blocks the call, tested on this machine"], firstColumnChips, ["copilot-cli and copilot-vscode fail open on a timeout", "or when ai-eng is not on PATH; the matrix has the rest"]),
    column(434, 236, "gate", "enforced, unverified: 1", ["wired to deny; the CLI was", "not installed on the test Mac"], secondColumnChips, ["codex fails open", "on a hook error"]),
    column(682, 254, "plain", "advisory: 2", ["the host gives it no", "synchronous deny"], thirdColumnChips, ["zed has no hook API.", "agy has a hook template", "that nothing installs."]),
    node({ x: 24, y: 380, w: 912, title: "docs/surface-capability-matrix.md", lines: ["Measured 2026-11-23 on macOS arm64, from live probes. Every count above comes from this table."], kind: "gate" }),
    legend(24, 476, null, "the source of the counts"),
  ].join("");
}

// ---------------------------------------------------------------------------
// The five figures: the words the README repeats, and the drawing
// ---------------------------------------------------------------------------

export const FIGURES: readonly Figure[] = [
  {
    n: 1,
    slug: "tool-call",
    height: 480,
    alt: "Figure 1. The agent proposes a tool call. The ai-eng chain judges it before it runs. The verdict is allow, annotate or deny. On allow or annotate the tool runs; on deny the tool never runs and the agent is told why. Every verdict writes a receipt file in .ai-engineering/receipts/.",
    caption: "Figure 1. One tool call. The refusal arrives before the tool runs, so the call never starts. The dashed line is a check, not a step: a guard that crashes or cannot decide also ends in a refusal.",
    textVersion: [
      "The agent proposes a tool call: a command, an edit or a read.",
      "The host sends the call to `ai-eng chain`, which runs the guards in a fixed order. The first refusal wins.",
      "The verdict is allow (a recognised test command is rewritten to show only failures), annotate (the call goes ahead with a review note) or deny (the call is refused, with the reason).",
      "On allow or annotate the tool runs. On deny it never runs, and the agent is told why and what to do instead.",
      "A guard that crashes or cannot decide ends in a refusal.",
      "Every verdict writes one JSON file to `.ai-engineering/receipts/`.",
    ],
    svg: toolCallFigure,
  },
  {
    n: 2,
    slug: "loop",
    height: 304,
    alt: "Figure 2. The build loop of ai-orchestrator. Your idea goes to a plan after you approve the idea. The plan becomes numbered checkpoints, built one at a time and each gated before the next; a checkpoint that fails a gate does not move on. You review the app, and it ships as a pull request or a local merge.",
    caption: "Figure 2. The build loop. A checkpoint that fails a gate does not move on, and the loop stops for you twice: to approve the idea before it builds, and to review the app before it ships.",
    textVersion: [
      "You give `ai-orchestrator` a feature, in your own words. You approve the idea: that is the first stop.",
      "It splits the work into numbered checkpoints, smallest first.",
      "It builds one checkpoint at a time and gates each before the next. A checkpoint that fails a gate does not move on.",
      "You review the app: that is the second stop.",
      "On your approval, it ships as a pull request or a local merge.",
    ],
    svg: buildLoopFigure,
  },
  {
    n: 3,
    slug: "layers",
    height: 590,
    alt: "Figure 3. Five layers, in the order a change meets them, each with the one thing only it stops. The guard chain stops an attempt to skip a check. Git hooks stop a secret in a commit. CI workflows stop a push that skipped the hooks. External review catches a test that was deleted or weakened, which every layer above passes. A merge stops a change nobody approved.",
    caption: "Figure 3. The layers, in the order a change meets them. The dashed row is a gap: no layer above external review reads what a test checks.",
    textVersion: [
      "Guard chain, before the tool runs: it alone stops an attempt to skip a check, because a hook cannot see the flag that skips it.",
      "Git hooks, at commit and push: they alone read the staged diff for a secret, and they run for a person as well as an agent.",
      "CI workflows, on the server after the push: they alone stop a push that skipped the local hooks, because a laptop cannot switch them off.",
      "External review: it alone catches a test that was deleted or weakened. ai-eng does not read test content, so every layer above passes it.",
      "Merge: a person decides whether the change ships. A release reaches npm only from a signed tag that a person approved.",
    ],
    svg: layerStackFigure,
  },
  {
    n: 5,
    slug: "single-parse",
    height: 504,
    alt: "Figure 5. One command goes through one shell parse in src/guards/shell.ts into a typed command model. Six guards read that model as predicates: no-verify, no-stash, policy, self-protect, lease and injection. A dashed check, tests/shell-guard-contract.spec.ts, pins what the one reader returns.",
    caption: "Figure 5. One parse, many guards. Each guard asks a question of the same typed model, so none reads a command differently from the shell. The dashed box is a test, not a step.",
    textVersion: [
      "A command arrives as text, for example `git commit -n -m fix`.",
      "One reader, `src/guards/shell.ts`, parses it the way the shell will: quotes, escapes, substitutions and heredocs.",
      "The result is a typed command model: segments, their words, and which text is code and which is data.",
      "Six guards read that model as predicates: `no-verify` asks whether a hook is skipped, `no-stash` whether a stash is created, `policy` whether the call is inside the scope, `self-protect` whether a rule is edited, `lease` whether another session is writing there, and `injection` whether the text carries orders for the model.",
      "The check on the reader is `tests/shell-guard-contract.spec.ts`. It pins what every guard reads, so a reader that splits or decodes one character differently from the shell fails.",
    ],
    svg: singleParseFigure,
  },
  {
    n: 4,
    slug: "surfaces",
    height: 508,
    alt: "Figure 4. Ten agent hosts by what ai-eng can do on each, measured on 2026-11-23. Enforced and verified, seven: claude-code, cursor, copilot-cli, copilot-vscode, opencode, pi and oh-my-pi. Enforced but unverified, one: codex. Advisory, two: zed and agy. Copilot fails open on a timeout or when ai-eng is missing from PATH; codex fails open on a hook error.",
    caption: "Figure 4. Which hosts are enforced, which advise, which are unverified. Counts come from the capability matrix, measured 2026-11-23. The dashed box names the source.",
    textVersion: [
      "Enforced and verified, 7: `claude-code`, `cursor`, `copilot-cli`, `copilot-vscode`, `opencode`, `pi` and `oh-my-pi`. A denial blocks the call, tested on the measuring machine. The two Copilot hosts fail open on a timeout or when `ai-eng` is not on `PATH`.",
      "Enforced but unverified, 1: `codex`. It is wired to deny, but the CLI was not installed on the measuring machine. It fails open on a hook error.",
      "Advisory, 2: `zed` and `agy`. `zed` has no hook API; the `agy` hook file is a template that nothing installs. They offer skills and advice, never a refusal.",
      "The source of every count is `docs/surface-capability-matrix.md`, measured 2026-11-23 on macOS arm64.",
    ],
    svg: surfacesFigure,
  },
];

export const figureFile = (figure: Figure, mode: Mode): string => `figure-${figure.n}-${figure.slug}-${mode}.webp`;

/** The inline SVG for one figure, background card included. */
export function figureSvg(figure: Figure): string {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${FIGURE_WIDTH}" height="${figure.height}" viewBox="0 0 ${FIGURE_WIDTH} ${figure.height}"><rect x=".5" y=".5" width="${FIGURE_WIDTH - 1}" height="${figure.height - 1}" rx="12" fill="var(--surface-2)" stroke="var(--line-strong)"/>${figure.svg()}</svg>`;
}
