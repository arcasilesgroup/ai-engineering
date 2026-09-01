// The binary IS the payload (blueprint 07): init/update/installCanon read every
// skill and template from EMBEDDED — never from disk paths, never from the network.

import { EMBEDDED } from "./assets.ts";
import { writeFileSync, mkdirSync, chmodSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";

/** Every embedded path under a prefix (e.g. "skills/" or "templates/"). Keys are
 *  normalized: generated as "../skills/..." relative to src/, stripped to "skills/...". */
export function embeddedUnder(prefix: string): Map<string, string> {
  const out = new Map<string, string>();
  for (const [rawPath, ref] of Object.entries(EMBEDDED)) {
    const path = rawPath.replace(/^(\.\.\/)+/, "");
    if (path.startsWith(prefix)) out.set(path, ref);
  }
  return out;
}

/** Materialize all embedded skills into a target directory. The embedded refs are
 *  absolute paths at runtime — Bun rewrites the import to the asset's real location,
 *  and in a compiled binary it is the virtualized copy inside the executable. */
export function materializeSkills(destRoot: string): string[] {
  const lines: string[] = [];
  const executablePattern = /\.(mjs|sh)$/;
  mkdirSync(destRoot, { recursive: true });
  let count = 0;
  for (const [path, ref] of embeddedUnder("skills/")) {
    const dest = join(destRoot, path.slice("skills/".length));
    const { pathname } = new URL(ref, import.meta.url);
    if (!existsSync(pathname)) {
      // Inside a compiled binary the asset lives at its ORIGINAL absolute path —
      // Bun --compile preserves the string. The ref is already the path.
      resolvedFromRef(ref, dest, executablePattern);
    } else {
      resolvedFromRef(pathname, dest, executablePattern);
    }
    count += 1;
  }
  lines.push(`materialized ${count} assets → ${destRoot}`);
  return lines;
}

function resolvedFromRef(source: string, dest: string, executablePattern: RegExp): void {
  const { readFileSync } = require("node:fs") as typeof import("node:fs");
  if (!existsSync(source)) return; // missing asset: init reports the count, doctor catches drift
  mkdirSync(dirname(dest), { recursive: true });
  writeFileSync(dest, readFileSync(source));
  if (executablePattern.test(dest)) chmodSync(dest, 0o755);
}

/** One embedded template, rendered with {{vars}}. Lookup by suffix so callers can
 *  use plain names ("AGENTS.md.tpl") regardless of the generated key prefix. */
export function embeddedTemplate(name: string, vars: Record<string, string> = {}): string {
  for (const [key, ref] of Object.entries(EMBEDDED)) {
    if (key === `templates/${name}` || key === `../templates/${name}`) {
      const content = readEmbeddedText(ref);
      let out = content;
      for (const [k, v] of Object.entries(vars)) out = out.split(`{{${k}}}`).join(v);
      return out;
    }
  }
  throw new Error(`template not embedded: ${name}`);
}

/** Source text of the chain module, embedded for in-process plugins (OpenCode/OMP). */
export function embeddedText(key: string): string {
  if (key === "src-chain") {
    // import.meta.dir inside the compiled binary is virtual; the plugin template
    // imports "./ai-eng-chain.ts", which we materialize as the bundled chain source.
    return CHAIN_SOURCE_PLACEHOLDER;
  }
  throw new Error(`unknown embedded text: ${key}`);
}

const CHAIN_SOURCE_PLACEHOLDER = "// materialized by installCanon — see embed.ts";

function readEmbeddedText(ref: string): string {
  const { pathname } = new URL(ref, import.meta.url);
  const { readFileSync } = require("node:fs") as typeof import("node:fs");
  return readFileSync(pathname, "utf8");
}

export function hasEmbedded(path: string): boolean {
  return path in EMBEDDED;
}
