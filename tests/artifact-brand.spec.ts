/**
 * Artifact brand gate — one token set for every HTML artifact ai-engineering
 * generates. `spec.html` and `plan.html` carry the tokens inline (they must
 * render standalone, with no request of their own), and the canon's artifact
 * design system is the reference every other generator copies from. A token that
 * differs between them is a defect, not a preference: the artifacts are read side
 * by side, and two of them in two palettes read as two products.
 */
import { describe, test, expect } from "bun:test";
import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";

const ROOT = join(import.meta.dir, "..");
const REFERENCE = "skills/ai-design/references/artifact-design.md";
const TEMPLATES = ["templates/spec.html.tpl", "templates/plan.html.tpl"];
const read = (path: string): string => readFileSync(join(ROOT, path), "utf8");

/** The `--name: value` declarations of the first `:root` block in a text. */
function rootTokens(text: string): Record<string, string> {
  const start = text.indexOf(":root");
  if (start < 0) throw new Error("no :root block");
  const open = text.indexOf("{", start);
  const close = text.indexOf("}", open);
  const out: Record<string, string> = {};
  for (const m of text.slice(open + 1, close).matchAll(/--([a-z0-9-]+)\s*:\s*([^;]+);/g)) {
    out[m[1]!] = m[2]!.trim();
  }
  return out;
}

/** Every SKILL.md in the canon, so the gate covers a skill added tomorrow. */
function skillFiles(): string[] {
  const out: string[] = [];
  const walk = (dir: string): void => {
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      const full = join(dir, entry.name);
      if (entry.isDirectory()) walk(full);
      else if (entry.name === "SKILL.md") out.push(full);
    }
  };
  walk(join(ROOT, "skills"));
  return out;
}

const reference = rootTokens(read(REFERENCE));

describe("the artifact design system is the single token source", () => {
  test("it declares the brand's core tokens", () => {
    for (const token of ["bg", "surface", "accent", "text", "dim", "ok", "bad", "warn"]) {
      expect(reference[token], `--${token} is missing`).toBeTruthy();
    }
    expect(reference["accent"]).toBe("#00D4AA");
    expect(reference["bg"]).toBe("#0B1120");
  });

  for (const template of TEMPLATES) {
    test(`${template} declares the reference's tokens and no others`, () => {
      const tokens = rootTokens(read(template));
      const drift: string[] = [];
      for (const [name, value] of Object.entries(tokens)) {
        if (!(name in reference)) drift.push(`--${name} is not in the reference`);
        else if (reference[name] !== value) drift.push(`--${name}: ${value} vs ${reference[name]}`);
      }
      expect(drift).toEqual([]);
      // A template that loses the accent renders an artifact in no product's colors.
      expect(tokens["accent"]).toBe(reference["accent"]);
    });
  }
});

describe("every skill that emits an artifact names the design system", () => {
  test("each one links artifact-design.md, so no generator invents a second style", () => {
    const silent: string[] = [];
    for (const file of skillFiles()) {
      const body = readFileSync(file, "utf8");
      const writes = /^Writes:\s*(.+)$/m.exec(body)?.[1];
      if (!writes?.includes(".html")) continue;
      if (!body.includes("artifact-design.md")) silent.push(file.slice(ROOT.length + 1));
    }
    expect(silent).toEqual([]);
  });
});
