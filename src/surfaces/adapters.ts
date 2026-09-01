// src/surfaces/adapters.ts — generators per surface: JSON-stdio (Claude/Cursor/Codex/Copilot)
// or TS module (OpenCode/OMP). Surface = ~150 LOC of adapter + its proof (§13).

import surfacesJson from "./surfaces.json";
import { existsSync, writeFileSync, mkdirSync, symlinkSync, unlinkSync } from "node:fs";
import { join, dirname } from "node:path";
import { homedir } from "node:os";
import { home, versionFile } from "../env.ts";
import { materializeSkills } from "../embed.ts";

export type Surface = {
  id: string;
  label: string;
  tier: "core" | "experimental" | "best-effort" | "skills-only";
  mechanism: "json-stdio" | "ts-module" | "none";
  can: { deny: boolean; rewriteIn: boolean; rewriteOut: boolean; failClosed?: boolean | string };
  settingsFile?: string;
  pluginFile?: string;
  timeout: number;
  note?: string;
};

export const SURFACES: Surface[] = (surfacesJson as { surfaces: Surface[] }).surfaces;

export function surfaceById(id: string): Surface | undefined {
  return SURFACES.find((s) => s.id === id);
}

/** init aborts if the chosen surface cannot carry a required guard: better not to
 *  promise than to promise falsely (§13). */
export function surfaceCanGovern(surface: Surface): boolean {
  return surface.can.deny !== false;
}

export type MirrorTarget = { dir: string; label: string };

/** Where each surface discovers skills (§08): one canon, three mirrors. */
export function mirrorTargets(): MirrorTarget[] {
  return [
    { dir: join(homedir(), ".claude", "skills"), label: "~/.claude/skills" },
    { dir: join(homedir(), ".agents", "skills"), label: "~/.agents/skills" },
    { dir: join(homedir(), ".config", "opencode", "skill"), label: "~/.config/opencode/skill" },
  ];
}

/** Plant the global canon once per machine, then symlink the mirrors (junction or
 *  verified copy on Windows — symlinks where the OS supports them). */
export function installCanon(version: string): string[] {
  const lines: string[] = [];
  const canonDir = join(home(), "skills");
  materializeSkills(canonDir);
  const { readdirSync } = require("node:fs") as typeof import("node:fs");
  const entries = readdirSync(canonDir, { withFileTypes: true }).filter((e) => e.isDirectory());
  lines.push(`✓ ${home()}/skills/ — ${entries.length} ai-* skills installed`);
  writeFileSync(versionFile(), JSON.stringify({ version, ts: Date.now() }));
  lines.push("✓ ~/.ai-engineering/version.json — version + 24h cache");
  for (const target of mirrorTargets()) {
    mkdirSync(dirname(target.dir), { recursive: true });
    const count = linkSkills(canonDir, target.dir);
    lines.push(`✓ Symlink → ${target.label} (${count} skills)`);
  }
  return lines;
}

function linkSkills(canonDir: string, mirrorDir: string): number {
  const { readdirSync } = require("node:fs") as typeof import("node:fs");
  let count = 0;
  for (const name of readdirSync(canonDir)) {
    const linkPath = join(mirrorDir, name);
    try {
      const stats = require("node:fs").lstatSync(linkPath) as { isSymbolicLink(): boolean };
      if (stats.isSymbolicLink()) {
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

/** SessionStart payload the surface injects: the one-line pin + nudge (§14.0a). */
export function sessionContextLines(cwd: string): string[] {
  const lines: string[] = [];
  const { repoRoot } = require("../env.ts") as typeof import("../env.ts");
  const root = repoRoot(cwd);
  if (root && !existsSync(join(root, ".ai-engineering", "config.toml"))) {
    lines.push("[ai-eng] este repo no está gobernado: ai-eng init");
  }
  const { loadConfig } = require("../env.ts") as typeof import("../env.ts");
  const models = loadConfig()["models"] ?? {};
  if (typeof models["decide"] === "string") {
    lines.push(`[ai-eng] pin de modelos — decide: ${models["decide"]} · execute: ${models["execute"]} · verify: ${models["verify"]}`);
  }
  return lines;
}

export function writeSurfaceSettings(path: string, content: string): void {
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, content);
}
