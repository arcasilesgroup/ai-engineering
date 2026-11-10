import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

// PERMISSIONS.md is the authorization spec for the optional Azure triage adapter: its
// route table must name exactly the Azure DevOps paths the collector builds. This test
// derives both sides from their own sources so a doc edit or a code edit alone goes red.
const ROOT = resolve(import.meta.dir, "..");
const PERMISSIONS_PATH = "PERMISSIONS.md";
const COLLECTOR_PATH = "skills/ai-triage/scripts/collect-azure.mjs";

/** Route paths in the PERMISSIONS.md table: `| \`GET /{project}/...\` | Allowed | ... |`. */
function declaredPaths(content: string): string[] {
  const routes = [...content.matchAll(/^\|\s*`(?:GET|POST)\s+(\/[^`]+)`\s*\|/gm)]
    .map((match) => match[1] ?? "");
  if (routes.length === 0) throw new Error(`No route rows parsed from ${PERMISSIONS_PATH}`);
  return routes.sort();
}

/** Doc-style placeholder for a collector identifier, or null when it names no path segment
 *  (e.g. `${category}` inside an error message — the `_apis` filter drops that template). */
function docPlaceholder(name: string): string | null {
  const lower = name.toLowerCase();
  if (lower.includes("project")) return "project";
  if (lower.includes("team")) return "team";
  if (lower.includes("backlog")) return "backlogId";
  if (lower.includes("id")) return "id";
  return null;
}

/** Route path templates in the collector source: expand `${name}` placeholders against the
 *  file's own `const name = \`...\`` assignments, then keep the Azure REST paths. */
function collectorPaths(source: string): string[] {
  const assignments = new Map<string, string>();
  for (const match of source.matchAll(/(?:const|let)\s+(\w+)\s*=\s*`([^`]*)`/g)) {
    assignments.set(match[1] ?? "", match[2] ?? "");
  }
  const expand = (text: string, seen: Set<string>): string =>
    text.replace(/\$\{([\w.]+)\}/g, (_match, name: string) => {
      const template = assignments.get(name.split(".")[0] ?? "");
      if (template !== undefined) {
        if (seen.has(name)) throw new Error(`Circular path template reference: ${name}`);
        return expand(template, new Set([...seen, name]));
      }
      const placeholder = docPlaceholder(name.split(".").at(-1) ?? name);
      return placeholder === null ? `\${${name}}` : `{${placeholder}}`;
    });
  const paths = [...source.matchAll(/`([^`]*)`/g)]
    // Keep only templates with literal path segments outside `${...}` placeholders (a "/").
    // Pure placeholder assemblies — route keys (`GET ${...}`), endpoint concatenations
    // (`${scope.organization}${path}`), error messages — are not route templates, and every
    // path they compose from is scanned on its own.
    .filter((match) =>
      (match[1] ?? "").replace(/\$\{[^}]*\}/g, "").includes("/"),
    )
    .map((match) => expand(match[1] ?? "", new Set()))
    .filter((path) => path.includes("_apis") && !path.endsWith("/"));
  for (const path of paths) {
    const unknown = /\$\{([\w.]+)\}/.exec(path)?.[1];
    if (unknown) throw new Error(`Unknown path placeholder in ${COLLECTOR_PATH}: \${${unknown}}`);
  }
  const unique = [...new Set(paths)]
    .map((path) => path.replace(/\$\{([\w.]+)\}/g, (_match, name: string) =>
      `{${docPlaceholder(name.split(".").at(-1) ?? name)}}`))
    .sort();
  if (unique.length === 0) throw new Error(`No route templates parsed from ${COLLECTOR_PATH}`);
  return unique;
}

describe("PERMISSIONS route parity", () => {
  test("PERMISSIONS.md declares exactly the Azure routes collect-azure.mjs builds", () => {
    const declared = declaredPaths(readFileSync(resolve(ROOT, PERMISSIONS_PATH), "utf8"));
    const built = collectorPaths(readFileSync(resolve(ROOT, COLLECTOR_PATH), "utf8"));
    const undeclared = built.filter((path) => !declared.includes(path));
    const unbuilt = declared.filter((path) => !built.includes(path));
    expect({ builtButUndeclared: undeclared, declaredButNotBuilt: unbuilt }).toEqual({
      builtButUndeclared: [],
      declaredButNotBuilt: [],
    });
  });
});
