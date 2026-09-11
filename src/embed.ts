// The binary IS the payload (blueprint 07): init/update/installCanon read every
// skill and template from EMBEDDED — never from disk paths, never from the network.

import { EMBEDDED } from "./assets.ts";
import { writeFileSync, mkdirSync, chmodSync, existsSync, readFileSync, readdirSync, unlinkSync, rmdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { hashFile } from "./skills-lint.ts";

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

/** The skills canon proper: dot-entries under skills/ hold the generated chain
 *  bundle, payload for the plugin hosts and not a skill anyone loads. Materializing
 *  them planted a 33 KB build artifact in every canon and every mirror, counted as
 *  canon by doctor (measured 2026-09-10). One predicate, every consumer. */
export function canonSkills(): Map<string, string> {
  const out = new Map<string, string>();
  for (const [path, ref] of embeddedUnder("skills/")) {
    if (path.slice("skills/".length).startsWith(".")) continue;
    out.set(path, ref);
  }
  return out;
}

export type CanonDrift = { verified: number; drift: number; missing: number; stale: number; foreign: number };

/** Files sitting in the canon home that this binary does not ship. The line between
 *  "ours to sweep" and "somebody else's to leave alone" is the skill folder: a path
 *  inside a folder we ship is a file we used to ship — a renamed asset, a deleted
 *  page — while anything else in the canon home (a skill of your own, a symlink) is
 *  not ours to delete. Dot entries are the OS talking (.DS_Store) and are ignored
 *  either way. Measured 2026-09-11: a renamed asset stayed in every installed canon
 *  forever, because canonDrift only walked the payload and an orphan was invisible. */
export function canonExtras(homeDir: string): { stale: string[]; foreign: string[] } {
  const payload = canonSkills();
  const shipped = new Set([...payload.keys()].map((path) => path.split("/")[1] ?? ""));
  const stale: string[] = [];
  const foreign: string[] = [];
  const walk = (dir: string, relative: string): void => {
    let entries;
    try {
      entries = readdirSync(dir, { withFileTypes: true });
    } catch {
      return; // an unreadable directory is reported by nobody and breaks nothing
    }
    for (const entry of entries) {
      if (entry.name.startsWith(".")) continue;
      const rel = relative.length === 0 ? entry.name : `${relative}/${entry.name}`;
      const absolute = join(dir, entry.name);
      if (entry.isSymbolicLink()) {
        foreign.push(`skills/${rel}`); // someone linked something in: never ours
        continue;
      }
      if (entry.isDirectory()) {
        walk(absolute, rel);
        continue;
      }
      if (payload.has(`skills/${rel}`)) continue;
      if (shipped.has(rel.split("/")[0]!)) stale.push(`skills/${rel}`);
      else foreign.push(`skills/${rel}`);
    }
  };
  walk(join(homeDir, "skills"), "");
  return { stale: stale.sort(), foreign: foreign.sort() };
}

/** Sweep the stale files inside folders we ship, then the directories they leave
 *  empty. Never touches a foreign path: deleting a file we did not install is the
 *  worst class of bug a governance tool can have (§14.3). */
export function removeStaleCanonFiles(homeDir: string): string[] {
  const skillsRoot = join(homeDir, "skills");
  const removed: string[] = [];
  for (const key of canonExtras(homeDir).stale) {
    const absolute = join(homeDir, key);
    try {
      unlinkSync(absolute);
    } catch {
      continue;
    }
    removed.push(key);
    let dir = dirname(absolute);
    while (dir.length > skillsRoot.length && dir.startsWith(skillsRoot)) {
      try {
        if (readdirSync(dir).length > 0) break;
        rmdirSync(dir);
      } catch {
        break;
      }
      dir = dirname(dir);
    }
  }
  return removed;
}

/** The installed canon against this binary's payload, byte for byte — the one
 *  predicate `init` and `doctor` share (health is a measurement, not a claim).
 *  Existence probes and a marker file lied twice (measured 2026-09-10): "global
 *  canon intact · nothing to install" over a canon with 34 files missing, and
 *  after an upgrade — notice.ts caches the REGISTRY version in the same
 *  version.json that installCanon wrote the INSTALLED version into. It counts the
 *  files the payload no longer has as well: a canon can be complete and dirty at
 *  once, and only the payload walk saw half of that (measured 2026-09-11). */
export function canonDrift(homeDir: string): CanonDrift {
  const extras = canonExtras(homeDir);
  const out: CanonDrift = { verified: 0, drift: 0, missing: 0, stale: extras.stale.length, foreign: extras.foreign.length };
  for (const [path, ref] of canonSkills()) {
    const installed = join(homeDir, path);
    const embedded = new URL(ref, import.meta.url).pathname;
    if (!existsSync(installed)) out.missing += 1;
    else if (existsSync(embedded) && hashFile(installed) === hashFile(embedded)) out.verified += 1;
    else out.drift += 1;
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
  for (const [path, ref] of canonSkills()) {
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
  if (!existsSync(source)) return; // missing asset: init reports the count, doctor catches drift
  mkdirSync(dirname(dest), { recursive: true });
  writeFileSync(dest, readFileSync(source));
  if (executablePattern.test(dest)) chmodSync(dest, 0o755);
}

function readEmbeddedText(ref: string): string {
  // ref is the module-resolved asset path Bun rewrites at build time; the URL
  // form keeps relative refs working in the source tree.
  return readFileSync(new URL(ref, import.meta.url).pathname, "utf8");
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
/** Source of the chain bundle for in-process plugin hosts (P0-2). The bundle is
 *  generated by scripts/gen-assets.ts into skills/.chain-bundle/ and travels
 *  embedded like any other payload file — a self-contained module, not a
 *  pointer into src/ (whose relative imports die in a foreign repo). */
export function embeddedChainBundle(): string {
  const bundled = embeddedUnder("skills/.chain-bundle/");
  const ref = bundled.get("skills/.chain-bundle/ai-eng-chain.ts");
  if (!ref) throw new Error("chain bundle not embedded — regenerate assets: bun scripts/gen-assets.ts");
  return readEmbeddedText(ref);
}
