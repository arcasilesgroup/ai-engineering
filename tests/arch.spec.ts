// Arch test (H5) — the single source of truth is .ai-engineering/arch.rules.json,
// projected here via archunit 2.4.0 (npm real name; "ArchUnitTS" 404s). Empty Test
// Protection: a typo in a layer glob yields an EMPTY slice and the slice-must-match
// assertions below fail the suite — never a silent green (§16.2).
import { describe, test, expect } from "bun:test";
import { projectSlices, type MapFunction } from "archunit";
import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";

interface ArchRule {
  from: string;
  mayNotImport: string;
  except?: string;
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

/** A whole-file path inside its declared layer. Self-edges and files no layer claims
 *  are dropped: this projects architecture, it does not audit coverage. */
const mapEdge: MapFunction = (edge) => {
  if (edge.external) return undefined;
  const source = layerOf(edge.source);
  const target = layerOf(edge.target);
  if (source === undefined || target === undefined || source === target) return undefined;
  return { sourceLabel: source, targetLabel: target };
};

const slices = () => {
  const builder = projectSlices();
  builder.mapFunction = mapEdge;
  return builder;
};

/** One archunit check per mayNotImport target in the JSON (projected rules). */
describe("architecture (arch.rules.json — single source of truth, §16.2)", () => {
  const known = Object.keys(config.layers);
  for (const rule of config.rules) {
    if (!rule.mayNotImport || rule.mayNotImport === "cycles") continue;
    for (const target of rule.mayNotImport.split(",").map((layer) => layer.trim())) {
      // A rule naming a layer the config does not declare tests nothing; the
      // protection test below is what turns that into a red suite.
      if (!known.includes(rule.from) || !known.includes(target)) continue;
      test(`${rule.from} must not import ${target}`, async () => {
        const violations = await slices().shouldNot().containDependency(rule.from, target).check();
        expect(violations).toEqual([]);
      });
    }
  }

  test("slices matched real files and real imports (empty-test protection)", async () => {
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
    // And the projection must SEE an import that exists. "No violations" is what an
    // empty graph answers too, so a known-true edge is the only thing that tells the
    // two apart: the chain reads the governed repo through src/env.ts.
    const seen = await slices().shouldNot().containDependency("chain", "env").check();
    expect(seen.length).toBeGreaterThan(0);
  });
});
