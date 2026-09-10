// src/surfaces/adapters.ts — generators per surface: JSON-stdio (Claude/Cursor/Codex/Copilot)
// or TS module (OpenCode/OMP). Surface = ~150 LOC of adapter + its proof (§13).

import surfacesJson from "./surfaces.json";
import { writeFileSync, mkdirSync, symlinkSync, unlinkSync, readdirSync, lstatSync, existsSync, readFileSync, realpathSync, rmdirSync } from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";
import { home, versionFile } from "../env.ts";
import { materializeSkills, embeddedTemplate } from "../embed.ts";
import type { Dialect } from "../chain/dialect.ts";

export type Surface = {
  readonly id: string;
  readonly label: string;
  readonly tier: "core" | "experimental" | "best-effort" | "skills-only";
  /** The host's denial vocabulary in the chain (chain/dialect.ts). Absent for the
   *  hosts that run the chain in-process — their template turns the outcome into
   *  throw/block itself. */
  readonly dialect?: Dialect;
  readonly can: { readonly deny: boolean | "throw"; readonly rewriteOut: boolean | "total-replacement" };
  readonly settingsFile?: string;
  readonly pluginFile?: string;
  readonly chainFile?: string;
  readonly note?: string;
};

export const SURFACES: Surface[] = (surfacesJson as { surfaces: Surface[] }).surfaces;

/** What the chain must write when this surface denies. Default: claude. */
export function surfaceDialect(id: string | undefined): Dialect {
  return SURFACES.find((s) => s.id === id)?.dialect ?? "claude";
}

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

/** The home the mirrors hang off: AI_ENG_HOME when a test set it, otherwise the real
 *  physical home — a test install never rewrites the REAL ~/.claude/skills etc.
 *  (measured: /tmp/aibrain-demo hijack, 2026-09-01). */
function mirrorBase(): string {
  return process.env.AI_ENG_HOME !== undefined ? home() : homedir();
}

/** Where each surface discovers skills (§08): one canon, three mirrors beside the
 *  canon. Without the override the base is the physical home and the paths are
 *  exactly §08's. */
export function mirrorTargets(): MirrorTarget[] {
  const base = mirrorBase();
  return [
    { dir: join(base, ".claude", "skills"), label: "~/.claude/skills" },
    { dir: join(base, ".agents", "skills"), label: "~/.agents/skills" },
    { dir: join(base, ".config", "opencode", "skill"), label: "~/.config/opencode/skill" },
  ];
}

/** Install the global canon once per machine, then symlink the mirrors (junction or
 *  verified copy on Windows — symlinks where the OS supports them). `machineHooks`
 *  is `init --global`: the hosts whose CLI ignores a per-project hooks file need the
 *  machine-level one, and only an explicit --global may write outside the repo. */
export function installCanon(version: string, options: { machineHooks?: boolean } = {}): string[] {
  const lines: string[] = [];
  const canonDir = join(home(), "skills");
  materializeSkills(canonDir);
  const entries = readdirSync(canonDir, { withFileTypes: true }).filter((e) => e.isDirectory() && !e.name.startsWith("."));
  lines.push(`✓ ${home()}/skills/ — ${entries.length} ai-* skills installed`);
  // Seeds the 24h notice cache (§14.0). Health never reads this file: init and
  // doctor byte-compare the canon against the payload (canonDrift) — this same
  // path also carries the REGISTRY version after a notice check (2026-09-10).
  writeFileSync(versionFile(), JSON.stringify({ version, ts: Date.now() }));
  lines.push("✓ ~/.ai-engineering/version.json — version + 24h cache");
  for (const target of mirrorTargets()) {
    mkdirSync(target.dir, { recursive: true });
    const count = linkSkills(canonDir, target.dir);
    lines.push(`✓ Symlink → ${target.label} (${count} skills)`);
  }
  const commands = installCommands(canonDir);
  if (commands.count > 0) lines.push(`✓ ~/.config/opencode/commands/ — ${commands.count} slash commands (/ai-*)`);
  if (options.machineHooks === true) lines.push(`✓ ${installCopilotCliHook()}`);
  return lines;
}

/** Copilot CLI 1.0.83 reads `~/.copilot/hooks/*.json` and does NOT read the repo's
 *  `.github/hooks/*.json` — measured 2026-09-10, headless and interactive-after-trust
 *  (the repo probe never fired; the user-level one did, in both). VS Code Copilot Chat
 *  and the cloud agent do read the repo copy, which is what init writes.
 *
 *  The wrapper fails OPEN when `ai-eng` is not on PATH, on purpose: a machine-level
 *  hook that fails closed with a missing binary denies every tool call in every
 *  session of every repo, which is exactly what the leftover v1 wiring did to this
 *  machine ("Hook command failed with code 127 ... (fail-closed)", copilot log). */
function installCopilotCliHook(): string {
  const dir = join(mirrorBase(), ".copilot", "hooks");
  mkdirSync(dir, { recursive: true });
  writeFileSync(join(dir, "ai-eng.json"), embeddedTemplate("settings.copilot.cli.json.tpl"));
  return "~/.copilot/hooks/ai-eng.json — machine hook (Copilot CLI ignores repo hooks)";
}

/** Everything installCanon wrote OUTSIDE the canon home, removed on uninstall's
 *  "everything" scope: the mirrors would otherwise point into a deleted canon and the
 *  command shims and machine hook would survive as orphans (measured 2026-09-10).
 *  Only ai-eng's own entries go — a real directory a person put in a mirror stays. */
export function removeMachineArtifacts(): number {
  const base = mirrorBase();
  const canonDir = join(home(), "skills");
  // Resolved on both sides: macOS tmpdir() hands out /var/... while the symlink
  // resolves to /private/var/..., and a raw startsWith silently kept every link.
  const canonical = (path: string): string => {
    try {
      return realpathSync(path);
    } catch {
      return path;
    }
  };
  const canonReal = canonical(canonDir);
  let removed = 0;
  const names = (dir: string): string[] => {
    try {
      return readdirSync(dir);
    } catch {
      return [];
    }
  };
  for (const target of mirrorTargets()) {
    for (const name of names(target.dir)) {
      const link = join(target.dir, name);
      try {
        if (lstatSync(link).isSymbolicLink() && canonical(link).startsWith(canonReal)) {
          unlinkSync(link);
          removed += 1;
        }
      } catch {
        /* not ours or not readable: leave it */
      }
    }
    pruneIfEmpty(target.dir);
  }
  for (const name of names(canonDir)) {
    const command = join(base, ".config", "opencode", "commands", `${name}.md`);
    try {
      if (readFileSync(command, "utf8").includes(`Load the \`${name}\` skill`)) {
        unlinkSync(command);
        removed += 1;
      }
    } catch {
      /* absent or not ours */
    }
  }
  pruneIfEmpty(join(base, ".config", "opencode", "commands"));
  const hook = join(base, ".copilot", "hooks", "ai-eng.json");
  try {
    if (readFileSync(hook, "utf8").includes("ai-eng chain")) {
      unlinkSync(hook);
      removed += 1;
    }
  } catch {
    /* absent or not ours */
  }
  pruneIfEmpty(join(base, ".copilot", "hooks"));
  return removed;
}

/** Remove a directory only when it is empty — our sweep emptied it, and an empty
 *  scaffold is noise. A mirror still holding someone else's skills stays. */
function pruneIfEmpty(dir: string): void {
  try {
    if (readdirSync(dir).length === 0) rmdirSync(dir);
  } catch {
    /* absent or not empty: nothing to prune */
  }
}

/** OpenCode loads skills but does not list them as `/name`; a command file per skill
 *  does it, `$ARGUMENTS` carrying the human's text. Derived from the canon, so a new
 *  skill is a command the day it ships — never a second list to keep in sync.
 *  Cursor, Copilot CLI and Copilot Chat in VS Code read the mirrors themselves
 *  (.agents/skills, .claude/skills) and need no shim (measured 2026-09-10). */
function installCommands(canonDir: string): { count: number } {
  const dir = join(mirrorBase(), ".config", "opencode", "commands");
  let count = 0;
  for (const name of readdirSync(canonDir)) {
    if (name.startsWith(".")) continue;
    const skillFile = join(canonDir, name, "SKILL.md");
    if (!existsSync(skillFile)) continue;
    const description = skillDescription(readFileSync(skillFile, "utf8"));
    const body = `---\ndescription: ${description}\n---\n\nLoad the \`${name}\` skill via the skill tool, then execute it for this request:\n\n$ARGUMENTS\n`;
    mkdirSync(dir, { recursive: true });
    writeFileSync(join(dir, `${name}.md`), body);
    count += 1;
  }
  return { count };
}

/** One palette line out of a SKILL.md description: folded YAML collapsed to a single
 *  string, cut at a word boundary so the list stays readable. */
function skillDescription(markdown: string): string {
  const block = /^---\n([\s\S]*?)\n---/.exec(markdown)?.[1] ?? "";
  const first = /^description:[ \t]*(.*)$/m.exec(block);
  const head = (first?.[1] ?? "").trim();
  const folded = head === "" || /^[>|]-?$/.test(head);
  // A folded value (`description: >-`) lives in the indented lines after the key, up
  // to the next unindented line — the next frontmatter key.
  const continuation = folded
    ? block.slice((first?.index ?? 0) + (first?.[0].length ?? 0)).split(/\n(?=\S)/)[0]!.replace(/\n\s*/g, " ")
    : head;
  const text = continuation.replace(/\s+/g, " ").trim();
  return text.length <= 200 ? text : `${text.slice(0, 200).replace(/\s\S*$/, "")}…`;
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
