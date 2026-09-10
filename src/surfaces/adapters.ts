// src/surfaces/adapters.ts — generators per surface: JSON-stdio (Claude/Cursor/Codex/Copilot)
// or TS module (OpenCode/OMP). Surface = ~150 LOC of adapter + its proof (§13).

import surfacesJson from "./surfaces.json";
import { writeFileSync, mkdirSync, symlinkSync, unlinkSync, readdirSync, lstatSync } from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";
import { home, versionFile } from "../env.ts";
import { materializeSkills } from "../embed.ts";

export type Surface = {
  readonly id: string;
  readonly label: string;
  readonly tier: "core" | "experimental" | "best-effort" | "skills-only";
  readonly can: { readonly deny: boolean | "throw"; readonly rewriteOut: boolean | "total-replacement" };
  readonly settingsFile?: string;
  readonly pluginFile?: string;
  readonly chainFile?: string;
  readonly note?: string;
};

export const SURFACES: Surface[] = (surfacesJson as { surfaces: Surface[] }).surfaces;

/** init aborts if the chosen surface cannot carry a required guard: better not to
 *  promise than to promise falsely (§13). */
export function surfaceCanGovern(surface: Surface): boolean {
  return surface.can.deny !== false;
}

/** The tier headers for the grouped surface multiselect (init + config share
 *  them): the group carries the capability class, the option hint the delta. */
export const SURFACE_TIERS: ReadonlyArray<readonly [string, string]> = [
  ["core", "core — deny + rewrite"],
  ["experimental", "experimental — rewrite may be partial"],
  ["best-effort", "best-effort — cloud FS: receipts may not survive"],
  ["skills-only", "skills only — no guards in hot-path"],
];

export type MirrorTarget = { dir: string; label: string };

/** Where each surface discovers skills (§08): one canon, three mirrors beside the
 *  canon. The mirror base is the canon home (env.home()): AI_ENG_HOME-isolable —
 *  a test install (AI_ENG_HOME=/tmp/...) never rewrites the REAL ~/.claude/skills
 *  etc. (measured: /tmp/aibrain-demo hijack, 2026-09-01). Without the override the
 *  base is the physical home and the paths are exactly §08's. */
export function mirrorTargets(): MirrorTarget[] {
  const base = process.env.AI_ENG_HOME !== undefined ? home() : homedir();
  return [
    { dir: join(base, ".claude", "skills"), label: "~/.claude/skills" },
    { dir: join(base, ".agents", "skills"), label: "~/.agents/skills" },
    { dir: join(base, ".config", "opencode", "skill"), label: "~/.config/opencode/skill" },
  ];
}

/** Install the global canon once per machine, then symlink the mirrors (junction or
 *  verified copy on Windows — symlinks where the OS supports them). */
export function installCanon(version: string): string[] {
  const lines: string[] = [];
  const canonDir = join(home(), "skills");
  materializeSkills(canonDir);
  const entries = readdirSync(canonDir, { withFileTypes: true }).filter((e) => e.isDirectory() && !e.name.startsWith("."));
  lines.push(`✓ ${home()}/skills/ — ${entries.length} ai-* skills installed`);
  writeFileSync(versionFile(), JSON.stringify({ version, ts: Date.now() }));
  lines.push("✓ ~/.ai-engineering/version.json — version + 24h cache");
  for (const target of mirrorTargets()) {
    mkdirSync(target.dir, { recursive: true });
    const count = linkSkills(canonDir, target.dir);
    lines.push(`✓ Symlink → ${target.label} (${count} skills)`);
  }
  return lines;
}

function linkSkills(canonDir: string, mirrorDir: string): number {
  let count = 0;
  for (const name of readdirSync(canonDir)) {
    if (name.startsWith(".")) continue; // the canon's dot-entries are payload, not skills
    const linkPath = join(mirrorDir, name);
    try {
      if (lstatSync(linkPath).isSymbolicLink()) {
        unlinkSync(linkPath);
      } else {
        continue; // a real directory there is not ours to replace
      }
    } catch {
      /* absent: create */
    }
    try {
      symlinkSync(join(canonDir, name), linkPath, "dir");
      count += 1;
    } catch {
      /* FS refused: leave absent, doctor reports the mirror gap */
    }
  }
  return count;
}
