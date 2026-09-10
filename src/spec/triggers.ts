// Conditional nodes judge themselves: a node that only applies sometimes declares
// its own condition in the `## Lifecycle` block of its SKILL.md, so nothing here
// hardcodes a glob or a skill name (§20.1). `spec close` refuses and `doctor` warns
// when a condition fired and left no artifact behind — the "if it touches UI"
// sentence that used to be prose nobody could check.

import { readdirSync, readFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { home } from "../env.ts";

/** The canon on disk: the installed home first, this repo's own `skills/` second. */
export function canonSkillsDir(): string | null {
  const installed = join(home(), "skills");
  if (existsSync(installed)) return installed;
  const local = join(import.meta.dir, "..", "..", "skills");
  return existsSync(local) ? local : null;
}

/** The `## Lifecycle` section of a SKILL.md, or null when the skill declares none. */
export function lifecycleBlock(markdown: string): string | null {
  for (const section of markdown.split(/\n(?=## )/)) {
    if (/^## Lifecycle\s*$/m.test(section.split("\n")[0] ?? "")) return section;
  }
  return null;
}

/** `Key: value` lines of a block. The first occurrence wins; a block is a contract, not a diff. */
export function blockFields(block: string): Record<string, string> {
  const fields: Record<string, string> = {};
  for (const line of block.split("\n")) {
    const m = /^([A-Z][A-Za-z ]*):\s*(.+?)\s*$/.exec(line);
    if (m && fields[m[1]!] === undefined) fields[m[1]!] = m[2]!;
  }
  return fields;
}

export type Trigger = {
  id: string;
  skill: string;
  /** `path` fires from the diff and is evaluated here. `judgment` fires from a decision
   *  a machine cannot read — declaring it as a path would be theatre, so it is named
   *  and left to the planner and the human (§20.1). */
  kind: "path" | "judgment";
  globs: string[];
  excludes: string[];
  writes: string;
};

/** Every node that declares a condition, read from the canon rather than a list here. */
export function readTriggers(canonDir: string | null): Trigger[] {
  if (!canonDir) return [];
  const out: Trigger[] = [];
  for (const entry of readdirSync(canonDir, { withFileTypes: true })) {
    if (!entry.isDirectory() || !entry.name.startsWith("ai-")) continue;
    const file = join(canonDir, entry.name, "SKILL.md");
    if (!existsSync(file)) continue;
    const block = lifecycleBlock(readFileSync(file, "utf8"));
    if (!block) continue;
    const fields = blockFields(block);
    const id = fields["Trigger"];
    if (!id || id === "none" || !fields["Trigger when"]) continue;
    const split = (value: string | undefined): string[] =>
      (value ?? "").split(",").map((part) => part.trim()).filter((part) => part.length > 0);
    out.push({
      id,
      skill: entry.name,
      kind: fields["Trigger kind"] === "judgment" ? "judgment" : "path",
      globs: split(fields["Trigger when"]),
      excludes: split(fields["Trigger excludes"]),
      writes: (fields["Writes"] ?? "").split(",")[0]!.trim(),
    });
  }
  return out.sort((a, b) => a.id.localeCompare(b.id));
}

/** Files the milestone touched, worktree included: committed since the base, plus untracked. */
export function changedFiles(root: string, baseSha: string): string[] {
  const diff = spawnSync("git", ["-C", root, "diff", "--name-only", baseSha], { encoding: "utf8" });
  const untracked = spawnSync("git", ["-C", root, "ls-files", "--others", "--exclude-standard"], { encoding: "utf8" });
  if (diff.status !== 0) return [];
  const paths = `${diff.stdout}\n${untracked.status === 0 ? untracked.stdout : ""}`
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length > 0);
  return [...new Set(paths)];
}

/** A `Writes:` path with its generated segments wildcarded — `run-N`, `NNN-{name}`. */
export function artifactPattern(writesPath: string): string {
  return writesPath
    .split("/")
    .map((segment) => (/\{|\}|NNN|^N$|-N$/.test(segment) ? "*" : segment))
    .join("/");
}

/** Did the triggered node leave anything behind? A folder name is a promise; a file is proof. */
export function artifactExists(root: string, writesPath: string): boolean {
  if (!writesPath || writesPath.startsWith("nothing")) return true;
  const pattern = artifactPattern(writesPath);
  if (!pattern.includes("*")) return existsSync(join(root, pattern));
  try {
    for (const found of new Bun.Glob(pattern).scanSync({ cwd: root, onlyFiles: true })) {
      if (!found.endsWith("summary.json")) return true;
    }
  } catch {
    return false;
  }
  return false;
}

export type UnmetTrigger = { id: string; skill: string; sample: string };

/** Conditions that fired, produced nothing, and were not abandoned with a reason.
 *  `abandoned` carries the ids the milestone declared — a gate id or a trigger id. */
export function unmetTriggers(root: string, baseSha: string, abandoned: Set<string>): UnmetTrigger[] {
  const canon = canonSkillsDir();
  const files = changedFiles(root, baseSha);
  if (files.length === 0) return [];
  const unmet: UnmetTrigger[] = [];
  for (const trigger of readTriggers(canon)) {
    if (trigger.kind !== "path") continue; // a judgment condition is the planner's to honour
    if (abandoned.has(trigger.id)) continue;
    const matches = (glob: string, file: string): boolean => {
      try {
        return new Bun.Glob(glob).match(file);
      } catch {
        return false; // a malformed glob is a silent condition, never a crash
      }
    };
    const hit = files.find(
      (file) => trigger.globs.some((glob) => matches(glob, file)) && !trigger.excludes.some((glob) => matches(glob, file)),
    );
    if (!hit) continue;
    if (artifactExists(root, trigger.writes)) continue;
    unmet.push({ id: trigger.id, skill: trigger.skill, sample: hit });
  }
  return unmet;
}
