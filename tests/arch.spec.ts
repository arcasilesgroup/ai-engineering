// Arch test (H5) — the single source of truth is .ai-engineering/arch.rules.json.
// The import graph is scanned directly (Glob over src + the relative `from "…"`
// lines): archunit's pattern language cannot express these layer globs, so the
// library ended up as a thin pass-through over a hand-rolled map anyway.
// Empty Test Protection: a typo in a layer glob yields an EMPTY slice and the
// assertions below fail the suite — never a silent green (§16.2).
import { describe, test, expect } from "bun:test";
import { readFileSync, readdirSync } from "node:fs";
import { join, relative, resolve, dirname } from "node:path";
import { Glob } from "bun";

interface ArchRule {
  from: string;
  mayNotImport: string;
}
interface ArchConfig {
  layers: Record<string, string>;
  rules: ArchRule[];
}

const config = JSON.parse(readFileSync(join(import.meta.dir, "..", ".ai-engineering", "arch.rules.json"), "utf8")) as ArchConfig;

/** One regex per layer, from that layer's own glob.
 *
 *  archunit's built-in pattern language cannot express these globs: it escapes `*`
 *  into a literal character, so the slice pattern it documents compiles to a regex
 *  that matches no path in this repository — the projection comes back empty and
 *  EVERY negative rule passes without looking at a single import. A green suite
 *  over an empty graph is the failure this file exists to catch, so the slicing is
 *  derived from the config here instead, in the glob dialect the config already
 *  uses: `**` spans anything, `*` stays inside one path segment, `{a,b}` is a
 *  choice, `,` separates alternatives. */
function layerRegex(glob: string): RegExp {
  const escaped = glob.replace(/[.+^$()|[\]\\]/g, "\\$&");
  const braced = escaped.replace(/\{([^}]*)\}/g, (_match, inner: string) => `(?:${inner.replace(/,/g, "|")})`);
  const expanded = braced
    .split("**").join("@@") // park `**` where the single-`*` pass below cannot eat one of its stars
    .split("*").join("[^/]*")
    .split("@@").join("[^]*")
    .split(",").join("|");
  return new RegExp(`^(?:${expanded})$`);
}

const LAYERS = Object.entries(config.layers).map(([name, glob]) => ({ name, re: layerRegex(glob) }));

const layerOf = (file: string): string | undefined => LAYERS.find((layer) => layer.re.test(file))?.name;

/** The real import graph: every src TypeScript file, every relative `from` edge,
 *  projected into layer labels. Self-edges and files no layer claims are dropped:
 *  this projects architecture, it does not audit coverage. */
const SRC = resolve(import.meta.dir, "..", "src");
const edges = (): Array<{ from: string; to: string }> => {
  const out: Array<{ from: string; to: string }> = [];
  for (const path of new Glob("**/*.ts").scanSync({ cwd: SRC })) {
    const source = layerOf("src/" + path.replace(/\\/g, "/"));
    if (source === undefined) continue;
    const text = readFileSync(join(SRC, path), "utf8");
    for (const m of text.matchAll(/from\s+["'](\.[^"']+)["']/g)) {
      const resolved = relative(SRC, resolve(dirname(join(SRC, path)), m[1]!));
      const target = layerOf("src/" + resolved.replace(/\\/g, "/"));
      if (target !== undefined && target !== source) out.push({ from: source, to: target });
    }
  }
  return out;
};

/** One check per mayNotImport target in the JSON (projected rules). */
describe("architecture (arch.rules.json — single source of truth, §16.2)", () => {
  const known = Object.keys(config.layers);
  const graph = edges();
  for (const rule of config.rules) {
    if (!rule.mayNotImport || rule.mayNotImport === "cycles") continue;
    for (const target of rule.mayNotImport.split(",").map((layer) => layer.trim())) {
      // A rule naming a layer the config does not declare tests nothing; the
      // protection test below is what turns that into a red suite.
      if (!known.includes(rule.from) || !known.includes(target)) continue;
      test(`${rule.from} must not import ${target}`, () => {
        expect(graph.filter((edge) => edge.from === rule.from && edge.to === target)).toEqual([]);
      });
    }
  }

  test("slices matched real files and real imports (empty-test protection)", () => {
    // A typo'd glob would project an EMPTY slice and the negative rules above would
    // pass trivially — so every layer glob must map to a real src directory, and the
    // rules file must declare every code directory the repo actually has.
    const srcDirs = readdirSync(join(import.meta.dir, "..", "src")).filter((d: string) => !d.includes("."));
    for (const dir of srcDirs) {
      expect(known).toContain(dir);
    }
    for (const rule of config.rules) {
      if (!rule.mayNotImport) continue;
      expect(known).toContain(rule.from);
      for (const layer of rule.mayNotImport.split(",")) expect(known).toContain(layer.trim());
    }
    // And the graph must SEE an import that exists. "No violations" is what an
    // empty graph answers too, so a known-true edge is the only thing that tells the
    // two apart: the chain reads the governed repo through src/env.ts.
    expect(graph.filter((edge) => edge.from === "chain" && edge.to === "env").length).toBeGreaterThan(0);
  });
});
