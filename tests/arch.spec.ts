// Arch test (H5) — the single source of truth is .ai-engineering/arch.rules.json.
// The import graph is scanned directly (Glob over src + the relative `from "…"`
// lines): archunit's pattern language cannot express these layer globs, so the
// library ended up as a thin pass-through over a hand-rolled map anyway.
// Empty Test Protection: a typo in a layer glob yields an EMPTY slice and the
// assertions below fail the suite — never a silent green (§16.2).
import { describe, test, expect } from "bun:test";
import { readFileSync, readdirSync } from "node:fs";
import { join, relative, resolve, dirname } from "node:path";

interface ArchRule {
  from?: string;
  mayNotImport?: string;
  forbid?: string;
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

type Layer = { name: string; re: RegExp };

const layerMatches = (file: string, layers: Layer[] = LAYERS): string[] =>
  layers.filter((layer) => layer.re.test(file)).map((layer) => layer.name);

const layerOf = (file: string): string | undefined => layerMatches(file)[0];

function layerCoverageIssues(files: string[], layers: Layer[] = LAYERS): { file: string; matches: string[] }[] {
  return files.flatMap((file) => {
    const matches = layerMatches("src/" + file, layers);
    return matches.length === 1 ? [] : [{ file, matches }];
  });
}

type ImportEdge = { from: string; to: string };

/** Every source file under src/, relative to src/. */
const SRC = resolve(import.meta.dir, "..", "src");
function sourceFiles(directory = SRC): string[] {
  const files: string[] = [];
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) files.push(...sourceFiles(path));
    else if (entry.isFile()) files.push(relative(SRC, path).replace(/\\/g, "/"));
  }
  return files.sort();
}

/** Every relative TypeScript import, with paths relative to src/. */
const moduleEdges = (files: string[]): ImportEdge[] => {
  const out: ImportEdge[] = [];
  for (const path of files.filter((file) => /\.(?:[cm]?ts|tsx)$/.test(file))) {
    const text = readFileSync(join(SRC, path), "utf8");
    const imports = /\bfrom\s*["'](\.[^"']+)["']|\bimport\s*\(\s*["'](\.[^"']+)["']|\bimport\s+["'](\.[^"']+)["']/g;
    for (const m of text.matchAll(imports)) {
      const specifier = m[1] ?? m[2] ?? m[3]!;
      out.push({
        from: path.replace(/\\/g, "/"),
        to: relative(SRC, resolve(dirname(join(SRC, path)), specifier)).replace(/\\/g, "/"),
      });
    }
  }
  return out;
};

/** Project the module graph into layer labels, dropping same-layer edges. */
const edges = (modules: ImportEdge[]): ImportEdge[] => modules.flatMap(({ from, to }) => {
  const source = layerOf("src/" + from);
  const target = layerOf("src/" + to);
  return source !== undefined && target !== undefined && source !== target ? [{ from: source, to: target }] : [];
});

function findCycle(imports: ImportEdge[]): string[] | undefined {
  const outgoing = new Map<string, string[]>();
  for (const { from, to } of imports) outgoing.set(from, [...(outgoing.get(from) ?? []), to]);
  const visiting = new Set<string>();
  const visited = new Set<string>();
  const path: string[] = [];
  let cycle: string[] | undefined;

  const visit = (module: string): boolean => {
    if (visiting.has(module)) {
      cycle = [...path.slice(path.indexOf(module)), module];
      return true;
    }
    if (visited.has(module)) return false;
    visiting.add(module);
    path.push(module);
    for (const dependency of outgoing.get(module) ?? []) {
      if (visit(dependency)) return true;
    }
    path.pop();
    visiting.delete(module);
    visited.add(module);
    return false;
  };

  for (const module of outgoing.keys()) {
    if (visit(module)) return cycle;
  }
  return undefined;
}

/** One check per mayNotImport target in the JSON (projected rules). */
describe("architecture (arch.rules.json — single source of truth, §16.2)", () => {
  const known = Object.keys(config.layers);
  const files = sourceFiles();
  const modules = moduleEdges(files);
  const graph = edges(modules);
  const requiredRestrictions = [
    ["guards", "chain"],
    ["guards", "commands"],
    ["guards", "cli"],
    ["payload", "guards"],
    ["payload", "chain"],
    ["payload", "commands"],
    ["payload", "cli"],
    ["payload", "surfaces"],
    ["commands", "cli"],
    ["git", "commands"],
    ["git", "cli"],
    ["git", "chain"],
    ["git", "guards"],
    ["workflow", "commands"],
    ["workflow", "cli"],
    ["workflow", "chain"],
  ] as const;

  for (const rule of config.rules) {
    if (rule.forbid === "cycles") {
      test("forbids import cycles, including same-layer cycles", () => {
        expect(findCycle([
          { from: "chain/mod.ts", to: "chain/dialect.ts" },
          { from: "chain/dialect.ts", to: "chain/mod.ts" },
        ])).toEqual(["chain/mod.ts", "chain/dialect.ts", "chain/mod.ts"]);
        expect(findCycle(modules)).toBeUndefined();
      });
      continue;
    }
    if (!rule.from || !rule.mayNotImport) continue;
    for (const target of rule.mayNotImport.split(",").map((layer) => layer.trim())) {
      // A rule naming a layer the config does not declare tests nothing; the
      // protection test below is what turns that into a red suite.
      if (!known.includes(rule.from) || !known.includes(target)) continue;
      test(`${rule.from} must not import ${target}`, () => {
        expect(graph.filter((edge) => edge.from === rule.from && edge.to === target)).toEqual([]);
      });
    }
  }

  for (const [source, target] of requiredRestrictions) {
    test(`${source} must not import ${target} (§6.3)`, () => {
      const hasLayers = known.includes(source) && known.includes(target);
      const hasRule = config.rules.some((rule) =>
        rule.from === source && rule.mayNotImport?.split(",").map((layer) => layer.trim()).includes(target),
      );
      const violations = graph.filter((edge) => edge.from === source && edge.to === target);
      expect({ hasLayers, hasRule, violations }).toEqual({ hasLayers: true, hasRule: true, violations: [] });
    });
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
      if (!rule.mayNotImport || !rule.from) continue;
      expect(known).toContain(rule.from);
      for (const layer of rule.mayNotImport.split(",")) expect(known).toContain(layer.trim());
    }
    // And the graph must SEE an import that exists. "No violations" is what an
    // empty graph answers too, so a known-true edge is the only thing that tells the
    // two apart: the chain reads the governed repo through src/env.ts.
    expect(graph.filter((edge) => edge.from === "chain" && edge.to === "env").length).toBeGreaterThan(0);
  });

  test("assigns every src file to exactly one layer", () => {
    expect(layerCoverageIssues(files)).toEqual([]);
  });

  test("rejects uncovered and overlapping file fixtures", () => {
    const fixtureLayers = [
      { name: "first", re: layerRegex("src/first/**,src/shared.ts") },
      { name: "second", re: layerRegex("src/second/**,src/shared.ts") },
    ];
    expect(layerCoverageIssues(["uncovered.ts"], fixtureLayers))
      .toEqual([{ file: "uncovered.ts", matches: [] }]);
    expect(layerCoverageIssues(["shared.ts"], fixtureLayers))
      .toEqual([{ file: "shared.ts", matches: ["first", "second"] }]);
  });

  test("checkpoint JSON file I/O is owned by src/workflow/checkpoint.ts", () => {
    const checkpointReaders = files
      .filter((path) => path.endsWith(".ts"))
      .filter((path) => {
        const source = readFileSync(join(SRC, path), "utf8");
        const readsCheckpointPath = /readFileSync\s*\(\s*(?:absolutePath|checkpointPath|checkpointFile)\b/i.test(source) ||
          /readFileSync\s*\(\s*(?:join|resolve)\([^)]*checkpoints/i.test(source);
        const parsesCheckpointContents = /JSON\.parse\s*\(\s*[A-Za-z_$][\w$]*checkpoint[\w$]*/i.test(source);
        return readsCheckpointPath || parsesCheckpointContents;
      })
      .sort();
    expect(checkpointReaders).toEqual(["workflow/checkpoint.ts"]);
  });
});
