// Only uninstall uses this: restore global Git template state recorded by older versions.

import { existsSync, readdirSync, readFileSync, rmSync } from "node:fs";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { home } from "../env.ts";

const SHIMS = ["pre-commit", "commit-msg", "pre-push"] as const;

const MARKER = "ai-eng git floor shim";

/** Keep Git config isolated when uninstall runs under a sandboxed machine home. */
function gitEnv(): NodeJS.ProcessEnv {
  if (process.env["AI_ENG_HOME"] === undefined) return process.env;
  if (process.env["GIT_CONFIG_GLOBAL"] !== undefined) return process.env;
  return { ...process.env, GIT_CONFIG_GLOBAL: join(home(), "gitconfig") };
}

function gitConfig(args: string[]): { code: number; out: string } {
  const done = spawnSync("git", ["config", "--global", ...args], { encoding: "utf8", env: gitEnv() });
  return { code: done.status ?? 1, out: `${done.stdout ?? ""}${done.stderr ?? ""}`.trim() };
}

function currentTemplateDir(): string | null {
  const done = gitConfig(["--get", "init.templateDir"]);
  return done.code === 0 && done.out.length > 0 ? done.out : null;
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
