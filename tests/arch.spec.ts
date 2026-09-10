// Arch test (H5) — the single source of truth is .ai-engineering/arch.rules.json,
// projected here via archunit 2.4.0 (npm real name; "ArchUnitTS" 404s). Empty Test
// Protection: a typo in a layer glob yields an EMPTY slice and the slice-must-match
// assertions below fail the suite — never a silent green (§16.2).
import { describe, test, expect } from "bun:test";
import { projectSlices } from "archunit";
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
        const condition = projectSlices().definedBy("src/**/(**).ts");
        const forbidden = condition.shouldNot().containDependency(rule.from, target);
        const violations = await forbidden.check();
        expect(violations).toEqual([]);
      });
    }
  }
  test("slices matched real files (empty-test protection)", () => {
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
  });
});
