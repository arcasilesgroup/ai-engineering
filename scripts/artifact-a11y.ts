/**
 * The static accessibility gate — the part of WCAG 2.2 AA that markup alone can
 * prove. It runs inside `bun test`, so a page that ships without a `lang`, a
 * second `h1`, a table without a caption or a script from a CDN fails on the
 * machine of whoever wrote it, not in a browser review three weeks later.
 *
 * What it cannot see is what a browser computes: rendered contrast over a
 * background, overlap, reflow. That is `scripts/artifact-axe.ts`, which opens
 * every page in system Chrome.
 *
 * Every rule returns one message per problem, prefixed with the page it was
 * found in. A message names the defect and why it matters, because the reader
 * of a failure is the person who has to fix it.
 */

import { Script } from "node:vm";

const COMMENT = /<!--[\s\S]*?-->/g;
/** Code samples are text a reader copies, never structure a browser renders. */
const PREFORMATTED = /<pre\b[^>]*>[\s\S]*?<\/pre>/gi;
const HEADING = /<h([1-6])\b/gi;
const TH_TAG = /<th\b([^>]*)>/gi;
const TABLE = /<table\b[^>]*>([\s\S]*?)<\/table>/gi;
const INLINE_SVG = /<svg\b([^>]*)>([\s\S]*?)<\/svg>/gi;
const ARIA_REF = /\baria-(labelledby|describedby|controls)\s*=\s*"([^"]*)"/gi;
const ID_ATTRIBUTE = /\bid\s*=\s*"([^"]*)"/g;
const SCRIPT_SRC = /<script\b[^>]*\bsrc\s*=\s*"([^"]*)"/gi;
const LINK_TAG = /<link\b[^>]*>/gi;
const INLINE_HANDLER = /\son([a-z]+)\s*=\s*"/gi;
const VIEWPORT = /<meta\b[^>]*name\s*=\s*"viewport"[^>]*>/i;
const TAG = /<(\/?)([a-z][a-z0-9-]*)\b([^>]*)>/gi;
const VOID = new Set(["area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"]);

/** A `data:` URI carries the bytes inline; anything else is a request off the page. */
function isInline(value: string): boolean {
  return value.trim().toLowerCase().startsWith("data:");
}

function attribute(tag: string, name: string): string | null {
  const found = new RegExp(`\\b${name}\\s*=\\s*"([^"]*)"`, "i").exec(tag);
  return found === null ? null : (found[1] ?? "");
}

/**
 * Which `h1` elements a reader actually meets. A single-page app keeps one root
 * per state and hides the rest, so two `h1` in the source can still mean one
 * heading on screen; `hidden` is the browser's own "not rendered", and the gate
 * reads it the same way instead of asking the page to lie about its markup.
 */
function h1Visibility(html: string): boolean[] {
  const visible: boolean[] = [];
  const stack: { name: string; isHidden: boolean }[] = [];
  let hiddenDepth = 0;
  for (const [whole, closing, rawName, attrs] of html.matchAll(TAG)) {
    const name = (rawName ?? "").toLowerCase();
    if (closing === "/") {
      const at = stack.map((element) => element.name).lastIndexOf(name);
      if (at >= 0) hiddenDepth -= stack.splice(at).filter((element) => element.isHidden).length;
      continue;
    }
    if (name === "h1") visible.push(hiddenDepth === 0);
    if (VOID.has(name) || whole.endsWith("/>")) continue;
    const isHidden = /\shidden(?:\s|=|$)/i.test(attrs ?? "");
    stack.push({ name, isHidden });
    if (isHidden) hiddenDepth += 1;
  }
  return visible;
}

/** Zoom is blocked when the page caps the scale below 2× or forbids scaling at all. */
function blocksZoom(viewport: string): boolean {
  const content = attribute(viewport, "content") ?? "";
  if (/user-scalable\s*=\s*(?:no|0)/i.test(content)) return true;
  const maxScale = /maximum-scale\s*=\s*([0-9.]+)/i.exec(content)?.[1];
  return maxScale !== undefined && Number(maxScale) < 2;
}

export function staticA11yProblems(html: string, label: string): string[] {
  const problems: string[] = [];
  const add = (message: string): number => problems.push(`${label}: ${message}`);
  // Commented-out example markup is advice to the agent writing the page, not
  // markup a reader or a screen reader ever meets.
  const page = html.replace(COMMENT, "");
  const structure = page.replace(PREFORMATTED, "");

  const htmlTag = /<html\b([^>]*)>/i.exec(page)?.[1] ?? "";
  if ((attribute(htmlTag, "lang") ?? "").trim() === "") {
    add('no <html lang="...">, so a screen reader guesses the language');
  }

  const title = /<title>([\s\S]*?)<\/title>/i.exec(page)?.[1]?.trim() ?? "";
  if (title === "") add("no non-empty <title>, so the tab and the window name nothing");

  const visibility = h1Visibility(structure);
  if (visibility.length === 0) add("no h1 heading, so the page names no subject");
  const visibleH1 = visibility.filter(Boolean).length;
  if (visibleH1 > 1) add(`${visibleH1} h1 headings side by side; a rendered page carries exactly one`);

  [...structure.matchAll(HEADING)]
    .map((match) => Number(match[1]))
    .reduce((previous, level) => {
      if (previous > 0 && level > previous + 1) add(`heading order skips from h${previous} to h${level}`);
      return level;
    }, 0);

  for (const [tag] of structure.matchAll(TH_TAG)) {
    if (attribute(tag ?? "", "scope") === null) add("a <th> has no scope, so its column has no name");
  }
  for (const [table] of structure.matchAll(TABLE)) {
    if (!/<caption\b/i.test(table ?? "")) add("a <table> has no <caption>, so its subject is unnamed");
  }
  for (const [, attrs, body] of structure.matchAll(INLINE_SVG)) {
    if (attribute(attrs ?? "", "role") !== "img") add('an <svg> has no role="img", so assistive tech skips it');
    if (!/<title\b/i.test(body ?? "")) add("an <svg> has no <title>, so its picture has no name");
  }

  const ids = [...structure.matchAll(ID_ATTRIBUTE)].map((match) => match[1] ?? "");
  const seen = new Set<string>();
  for (const id of ids) {
    if (seen.has(id)) add(`duplicate id "${id}", so a link lands on the wrong place`);
    seen.add(id);
  }
  for (const [, relation, reference] of structure.matchAll(ARIA_REF)) {
    for (const id of (reference ?? "").split(/\s+/).filter((value) => value !== "")) {
      if (!seen.has(id)) add(`aria-${relation}="${id}" points at an id the page does not have`);
    }
  }

  for (const [, src] of structure.matchAll(SCRIPT_SRC)) {
    if (!isInline(src ?? "")) add(`external script ${src ?? ""} — an artifact opens offline`);
  }
  for (const [tag] of structure.matchAll(LINK_TAG)) {
    if (!/\brel\s*=\s*"stylesheet"/i.test(tag ?? "")) continue;
    const href = attribute(tag ?? "", "href") ?? "";
    if (!isInline(href)) add(`external stylesheet ${href} — an artifact opens offline`);
  }
  for (const [, handler] of structure.matchAll(INLINE_HANDLER)) {
    add(`inline on${handler ?? ""} handler — the page carries one script, not many`);
  }

  const viewport = VIEWPORT.exec(structure)?.[0] ?? "";
  if (viewport !== "" && blocksZoom(viewport)) add("the viewport blocks zoom, so a reader cannot enlarge the text");

  for (const [media, requirement] of [
    ["forced-colors", "forced-colors layer, so Windows high contrast keeps every box visible"],
    ["prefers-reduced-motion", "prefers-reduced-motion rule, so the reader's own setting wins"],
    ["print", "print rule, so the page survives paper"],
  ] as const) {
    if (!new RegExp(`@media[^{]*${media}`).test(page)) add(`no ${requirement}`);
  }

  return problems;
}

const MODULE_STATEMENT = /^\s*(?:import|export)\b/m;
const FORBIDDEN = ["innerHTML", "outerHTML", "insertAdjacentHTML", "eval", "fetch"] as const;

/**
 * The page script is one classic ES2019 script with no network and no string
 * built from data. A classic script parses without an import or an export, and
 * every write goes through `textContent`, so markup never becomes executable.
 */
export function scriptProblems(js: string): string[] {
  const problems: string[] = [];
  const isModule = MODULE_STATEMENT.test(js);
  if (isModule) problems.push("brand/components.js: is an ES module; a page script is classic");
  for (const name of FORBIDDEN) {
    if (new RegExp(`\\b${name}\\b`).test(js)) problems.push(`brand/components.js: uses ${name}`);
  }
  if (!isModule) {
    try {
      // Parsing without running: a classic script that does not parse never reaches a page.
      // A module already failed that parse above, so its message is not repeated.
      new Script(js);
    } catch (error) {
      problems.push(`brand/components.js: does not parse as a classic script (${(error as Error).message})`);
    }
  }
  return problems;
}
