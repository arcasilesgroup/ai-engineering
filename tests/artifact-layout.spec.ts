/**
 * Layout gate — artifact-design.md rule 4 made executable: "Prose justifies to
 * the container... Centered or 68ch-capped body text is the defect: it breaks
 * the left edge everything else shares."
 *
 * The tokens gate (artifact-brand.spec.ts) proves the palette is one palette.
 * It never looked at layout, so research pages shipped with `p` centered and
 * capped at 68ch — text floating mid-viewport while tables ran to the rails —
 * and one shipped with sections in no `.container` at all, so headings sat on
 * the viewport edge. Same tokens, unreadable page: alignment is the other half
 * of "one family".
 *
 * Scope: every sectioned page under .ai-engineering/ (research, recap,
 * brainstorm, audits — not workflow/, which is product UI wearing the tokens)
 * and the three shipped carriers in templates/. A page with <section> is a
 * reading artifact and takes the contract whole.
 *
 * The doc itself is under gate too: it carries the CSS block twice ("The
 * tokens" and "The block"), and the two copies had already drifted — an agent
 * copying from one and an agent copying from the other ship different skip
 * links. One document, one block.
 */
import { describe, expect, test } from "bun:test";
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

const ROOT = join(import.meta.dir, "..");
const DESIGN = "skills/ai-brainstorm/references/artifact-design.md";
const CARRIERS = ["templates/recap.html.tpl", "templates/brainstorm.html.tpl", "templates/research.html.tpl"] as const;

function read(path: string): string {
  return readFileSync(join(ROOT, path), "utf8");
}

/** Every sectioned artifact page: .ai-engineering minus the workflow viewers, plus the carriers. */
function sectionedArtifacts(): string[] {
  const out: string[] = [];
  const walk = (dir: string): void => {
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      const full = join(dir, entry.name);
      if (entry.isDirectory()) {
        if (entry.name === "workflow") continue;
        walk(full);
      } else if (entry.name.endsWith(".html") && readFileSync(full, "utf8").includes("<section")) {
        out.push(full.slice(ROOT.length + 1));
      }
    }
  };
  walk(join(ROOT, ".ai-engineering"));
  for (const carrier of CARRIERS) {
    if (read(carrier).includes("<section")) out.push(carrier);
  }
  return out;
}

describe("artifact layout — rule 4, the left edge everything shares", () => {
  test("body prose justifies to the container; centered or capped p is the defect", () => {
    const violations: string[] = [];
    for (const file of sectionedArtifacts()) {
      const style = /<style[^>]*>([\s\S]*?)<\/style>/.exec(read(file))?.[1];
      if (style === undefined) {
        violations.push(`${file}: no <style> block`);
        continue;
      }
      // Whitespace-stripped so formatting variants of the same rule compare equal.
      const flat = style.replace(/\s+/g, "");
      const rule = /(?<![\w.:-])p\{[^}]*\}/.exec(flat)?.[0] ?? null;
      if (rule === null) {
        violations.push(`${file}: no body p rule found`);
      } else if (rule.includes("text-align:center")) {
        violations.push(`${file}: p is centered — ${rule}`);
      } else if (rule.includes("max-width:var(--measure)")) {
        violations.push(`${file}: p is capped at 68ch — ${rule}`);
      } else if (!rule.includes("text-align:justify")) {
        violations.push(`${file}: p does not justify — ${rule}`);
      }
      // A note inherits p's alignment: without its own left, the callout the
      // reader must not miss is the most badly aligned box on the page.
      const note = /\.notep\{[^}]*\}/.exec(flat)?.[0];
      if (note !== undefined && !note.includes("text-align:left")) {
        violations.push(`${file}: .note p does not sit left — ${note}`);
      }
      // The panel itself shares the rails too; an auto margin re-centers it.
      const panel = /\.note\{[^}]*\}/.exec(flat)?.[0];
      if (panel !== undefined && /\bmargin:[^;}]*\bauto\b/.test(panel)) {
        violations.push(`${file}: .note panel is centered — ${panel}`);
      }
      // Lists keep their own left rail; an auto horizontal margin re-centers
      // the block and opens the gap rule 4 exists to prevent.
      for (const list of flat.matchAll(/(?<![\w.-])(?:ul,ol|ol,ul|ul|ol)\{[^}]*\}/g)) {
        if (list[0].includes("auto")) {
          violations.push(`${file}: list block is centered — ${list[0]}`);
        }
      }
    }
    expect(violations.join("\n")).toBe("");
  });

  test("every sectioned page wraps its content in a .container", () => {
    const violations: string[] = [];
    for (const file of sectionedArtifacts()) {
      if (!/class="[^"]*\bcontainer\b/.test(read(file))) {
        violations.push(`${file}: <section> with no .container — headings and tables run to the viewport edge`);
      }
    }
    expect(violations.join("\n")).toBe("");
  });

  test("artifact-design.md carries one CSS block, not two drifting copies", () => {
    const blocks = [...read(DESIGN).matchAll(/```css\r?\n([\s\S]*?)```/g)].map((m) =>
      (m[1] ?? "").replace(/\s+/g, ""),
    );
    expect(blocks.length).toBeGreaterThanOrEqual(2);
    const drift = blocks.filter((block) => block !== blocks[0]);
    expect(drift.length).toBe(0);
  });

  test("every var() a checked page uses is declared in its own :root", () => {
    const undeclared: string[] = [];
    const check = (label: string, css: string): void => {
      const flat = css.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\s+/g, "");
      const root = /:root\{([^}]*)\}/.exec(flat)?.[1] ?? "";
      const declared = new Set([...root.matchAll(/(--[a-z0-9-]+):/g)].map((m) => m[1]));
      const used = new Set([...flat.matchAll(/var\((--[a-z0-9-]+)/g)].map((m) => m[1]));
      const missing = [...used].filter((name) => !declared.has(name));
      if (missing.length > 0) undeclared.push(`${label}: ${missing.join(", ")}`);
    };
    // An undeclared var() invalidates the whole declaration: border-radius
    // computes to 0px and every card and table renders square. The canonical
    // block first — every artifact copies from it — then each page's own
    // inline block, because pages frozen before the block was fixed still
    // carry the dangling reference.
    const block = read(DESIGN).match(/```css\r?\n([\s\S]*?)```/)?.[1] ?? "";
    check(DESIGN, block);
    for (const file of sectionedArtifacts()) {
      const style = /<style[^>]*>([\s\S]*?)<\/style>/.exec(read(file))?.[1];
      if (style !== undefined) check(file, style);
    }
    expect(undeclared.join("\n")).toBe("");
  });

  test("the shipped carriers carry the canonical block whole", () => {
    const block = read(DESIGN).match(/```css\r?\n([\s\S]*?)```/)?.[1] ?? "";
    const strip = (css: string): string =>
      css.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\s+/g, "").replace(/;}/g, "}");
    const canonical = strip(block);
    const missing: string[] = [];
    for (const carrier of CARRIERS) {
      // The design doc promises "the shipped templates carry the same
      // block"; a carrier missing a component rule ships an unstyled element
      // the moment a writer uses it.
      const style = /<style[^>]*>([\s\S]*?)<\/style>/.exec(read(carrier))?.[1] ?? "";
      if (!strip(style).includes(canonical)) missing.push(carrier);
    }
    expect(missing.join("\n")).toBe("");
  });
});
