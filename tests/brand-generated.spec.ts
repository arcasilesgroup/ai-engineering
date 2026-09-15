/**
 * The generated set's own oracle.
 *
 * `parity` proves that what is committed matches what `gen` computes. It cannot prove that
 * `gen` computes the *right* thing: if the breakpoint derivation quietly returned an empty
 * list — a regex that stopped matching, a file that moved — parity would stay green and the
 * design record would state, with confidence, that the site has no responsive thresholds.
 * That exact shape bit this work twice: a hue measurement that returned "nothing" because
 * of a silent `NaN`, and a type check that demanded the wrong kind of value.
 *
 * So these assertions read the generated files and ask whether they describe the tree.
 */
import { describe, test, expect } from "bun:test";
import { existsSync, readFileSync, readdirSync } from "node:fs";
import { loadTokens, type Tokens } from "../scripts/brand.ts";
import { join } from "node:path";

const ROOT = join(import.meta.dir, "..");
const WEB = join(ROOT, "..", "ai-engineering-web");
/** The sibling web repo is private and is not checked out in CI (nor mounted into
 *  the mutation sandbox): where its tree is absent these assertions have no subject,
 *  so they skip instead of failing. Locally the suite still reads the real thing.
 *  ponytail: brand.ts mutants covered only here survive the local campaign until
 *  the sandbox mounts ai-engineering-web. */
const hasWeb = existsSync(join(WEB, ".impeccable", "design.json"));
const read = (path: string): string => readFileSync(path, "utf8");

/** The `--name: value` declarations of the generated stylesheet's `:root`. */
const cssTokens = (): Record<string, string> => {
  const text = read(join(WEB, "src", "styles", "tokens.css"));
  const block = /:root\s*\{([\s\S]*?)\n\}/.exec(text);
  if (block === null) throw new Error("the generated stylesheet has no :root block");
  const out: Record<string, string> = {};
  for (const decl of block[1]!.matchAll(/--([a-z0-9-]+):\s*([^;]+);/g)) out[decl[1]!] = decl[2]!.trim();
  return out;
};

/** The parts of the design record these assertions read. */
interface DesignRecord {
  extensions: {
    accessibility: { pairs: { ratio: number; min: number }[] };
    colorMeta: Record<string, unknown>;
    breakpoints: { values: string[] };
  };
}

const design = (): DesignRecord =>
  JSON.parse(read(join(WEB, ".impeccable", "design.json"))) as DesignRecord;

/** The resolved value of a semantic token, straight from the declaration. */
const resolve = (t: Tokens, name: string): string => {
  for (const group of Object.values(t.semantic)) {
    const token = (group as Record<string, { ref: string; alpha?: number } | undefined>)[name];
    if (!token) continue;
    const [family, step] = token.ref.split(".");
    const entry = (t.families as Record<string, string | Record<string, string>>)[family!]!;
    const hex = typeof entry === "string" ? entry : entry[step!]!;
    if (token.alpha === undefined) return hex;
    const n = parseInt(hex.slice(1), 16);
    return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${token.alpha})`;
  }
  throw new Error(`unknown token: ${name}`);
};

describe("the generated stylesheet carries the declared values", () => {
  test.skipIf(!hasWeb)("the accent and the field are what the declaration says they are", async () => {
    const tokens = await loadTokens();
    const css = cssTokens();
    expect(css["accent"]).toBe(resolve(tokens, "accent"));
    expect(css["bg-deep"]).toBe(resolve(tokens, "bg"));
    expect(css["font-sans"]).toBe(tokens.typography.families["sans"]!);
  });

  test.skipIf(!hasWeb)("it declares every semantic colour, so no component can fall back to nothing", async () => {
    const tokens = await loadTokens();
    const css = cssTokens();
    for (const token of ["accent-text", "link", "border", "surface-2", "muted", "text", "danger", "warn"]) {
      expect(css[token], `--${token} is missing from the generated stylesheet`).toBeDefined();
    }
  });
});

describe("the design record describes the tree it came from", () => {
  test.skipIf(!hasWeb)("it carries one accessibility row per declared pair, and every row passes its level", async () => {
    const tokens = await loadTokens();
    const rows = design().extensions.accessibility.pairs;
    expect(rows.length).toBe(tokens.pairs.length);
    for (const row of rows) {
      expect(row.ratio, `a pair measures ${row.ratio}:1 against a floor of ${row.min}`).toBeGreaterThanOrEqual(row.min);
    }
  });

  test.skipIf(!hasWeb)("it carries one colour entry per semantic token", async () => {
    const tokens = await loadTokens();
    const declared = Object.values(tokens.semantic).reduce<number>((n, group) => n + Object.keys(group).length, 0);
    expect(Object.keys(design().extensions.colorMeta).length).toBe(declared);
  });

  test.skipIf(!hasWeb)("the breakpoints it lists are the ones the stylesheet actually uses", () => {
    const values = design().extensions.breakpoints.values;
    // An empty list here would mean the derivation stopped reading the CSS, not that the
    // site stopped being responsive.
    expect(values.length).toBeGreaterThan(0);

    const walk = (dir: string): string[] =>
      readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
        const path = join(dir, entry.name);
        if (entry.isDirectory()) return walk(path);
        return /\.(css|astro)$/.test(path) ? [readFileSync(path, "utf8")] : [];
      });
    const sources = walk(join(WEB, "src")).join("\n");
    for (const value of values) {
      expect(sources, `${value} is listed as a breakpoint but appears in no stylesheet`).toContain(value);
    }
  });
});
