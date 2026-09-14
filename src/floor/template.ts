// The git floor's second life: `init.templateDir` makes every NEW clone of a governed
// repo be born with the three shims. The shims stay in `.git/hooks/` — same place, same
// marker — so the sweep, the coexistence with husky and the contract do not change; what
// changes is that a clone no longer starts unguarded (.github/workflows/check.yml existed
// to rebuild them after the fact, which is the symptom of a carrier in the wrong place).
//
// `core.hooksPath` global stays discarded, with its measured reason: a LOCAL hooksPath
// (husky, pre-commit) beats the global one and silently leaves the repo ungoverned.
//
// Three rules, and none of them is "write over what is there":
//   1. no templateDir → ours, and the previous value (none) is recorded;
//   2. a templateDir the USER already had → our shims are copied INTO it, marker-managed,
//      and their setting is never touched;
//   3. a templateDir that is ours → the shims are made current, nothing else.

import { existsSync, mkdirSync, readdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { embeddedTemplate } from "../embed.ts";
import { home } from "../env.ts";

export const SHIMS = ["pre-commit", "commit-msg", "pre-push"] as const;

const MARKER = "ai-eng git floor shim";

export type TemplateReport = { line: string; status: "created" | "joined" | "current" | "failed" };

function gitConfig(args: string[]): { code: number; out: string } {
  const done = spawnSync("git", ["config", "--global", ...args], { encoding: "utf8" });
  return { code: done.status ?? 1, out: `${done.stdout ?? ""}${done.stderr ?? ""}`.trim() };
}

/** The global templateDir as it stands, or null. `--get` exits 1 when unset. */
export function currentTemplateDir(): string | null {
  const done = gitConfig(["--get", "init.templateDir"]);
  return done.code === 0 && done.out.length > 0 ? done.out : null;
}

function shimBody(name: string): string {
  return embeddedTemplate(`git-${name}.tpl`);
}

/** Whose hooks live here: ours (there is a file with our marker and none without it),
 *  theirs (there is a file and it is not ours), or empty (no hook file at all).
 *
 *  "theirs" is the important answer: a directory holding a person's pre-commit must never
 *  be written over, and the previous version of this function returned "empty" for it —
 *  which turned the one protection into a force write. */
function shimState(dir: string): "ours" | "theirs" | "empty" {
  const hooks = join(dir, "hooks");
  if (!existsSync(hooks)) return "empty";
  let ours = false;
  for (const name of SHIMS) {
    const path = join(hooks, name);
    if (!existsSync(path)) continue;
    let body = "";
    try {
      body = readFileSync(path, "utf8");
    } catch {
      return "theirs"; // unreadable is not ours
    }
    if (!body.includes(MARKER)) return "theirs";
    ours = true;
  }
  return ours ? "ours" : "empty";
}

function writeShims(dir: string, force: boolean): number {
  const hooks = join(dir, "hooks");
  mkdirSync(hooks, { recursive: true });
  let written = 0;
  for (const name of SHIMS) {
    const path = join(hooks, name);
    const body = shimBody(name);
    if (existsSync(path) && !force) {
      // Never trample a hook a person wrote: ours only replace ours.
      let current = "";
      try {
        current = readFileSync(path, "utf8");
      } catch {
        continue;
      }
      if (!current.includes(MARKER)) continue;
      if (current === body) continue;
    }
    writeFileSync(path, body, { mode: 0o755 });
    written += 1;
  }
  return written;
}

/** Put the floor in the template dir, whatever it turns out to be. `previous` is the
 *  value found before this call and `ours` the directory this install owns, which
 *  uninstall needs to undo exactly. */
export function installTemplateDir(): { line: string; status: TemplateReport["status"]; previous: string | null; ours: string | null } {
  const previous = currentTemplateDir();
  if (previous === null) {
    // Ours lives with the canon it belongs to (~/.ai-engineering/git-template), so it is
    // deleted with the rest on uninstall instead of leaving a directory nobody owns.
    const dir = join(home(), "git-template");
    writeShims(dir, true);
    const done = gitConfig(["init.templateDir", dir]);
    if (done.code !== 0) return { line: `git init.templateDir not set: ${done.out}`, status: "failed", previous, ours: null };
    return { line: `git init.templateDir → ${dir} (new clones are born with the floor)`, status: "created", previous, ours: dir };
  }
  // A template dir the user already had: our shims go INSIDE it. Their setting is theirs.
  // A template dir the user already had: our shims go INSIDE it, and their setting is
  // theirs. A hooks/ dir holding someone else's hooks is left alone entirely — the one
  // thing this must never do is overwrite a person's hook to install ours.
  const written = writeShims(previous, shimState(previous) === "empty");
  return {
    line:
      written > 0
        ? `git init.templateDir keeps your ${previous} · our three shims written inside it`
        : `git init.templateDir keeps your ${previous} · our shims already current`,
    status: written > 0 ? "joined" : "current",
    previous,
    ours: null,
  };
}

/** Uninstall's half: put the global setting back the way it was, and take our shims out of
 *  a template dir that was the user's. Nothing is deleted from a directory we did not
 *  create beyond our own marker-managed files. */
export function restoreTemplateDir(previous: string | null, ours: string | null): string {
  const current = currentTemplateDir();
  if (current === null) return "git init.templateDir was not set — nothing to restore";
  if (previous !== null && previous === current) {
    // We joined their directory: our shims come out, their setting stays.
    const hooks = join(current, "hooks");
    let removed = 0;
    for (const name of SHIMS) {
      const path = join(hooks, name);
      try {
        if (readFileSync(path, "utf8").includes(MARKER)) {
          rmSync(path, { force: true });
          removed += 1;
        }
      } catch {
        /* absent or unreadable: not ours */
      }
    }
    try {
      if (existsSync(hooks) && readdirSync(hooks).length === 0) rmSync(hooks, { recursive: true, force: true });
    } catch {
      /* leave what is not ours */
    }
    return `git init.templateDir kept yours (${current}) · ${removed} ai-eng shim(s) removed from it`;
  }
  if (ours !== null && current !== ours) return `git init.templateDir is now ${current} — left as it is (it is not the one this install set)`;
  // The value we found is the value we put back — a setting the user owns is never simply
  // deleted, and a report that claims a restore has to be one.
  if (previous !== null) gitConfig(["init.templateDir", previous]);
  else gitConfig(["--unset", "init.templateDir"]);
  if (ours !== null) rmSync(ours, { recursive: true, force: true });
  return previous === null ? "git init.templateDir unset (it was unset before)" : `git init.templateDir restored to ${previous}`;
}
