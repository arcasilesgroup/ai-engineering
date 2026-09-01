// --no-verify, and everything else that skips .git/hooks — plus every linter silence,
// because silencing a check is the same act as skipping a hook. ~110 LOC ported from
// v1's no_verify_guard.py (80) extended per §10 with the SILENCES row.

import { resolve, isAbsolute } from "node:path";
import { existsSync } from "node:fs";
import type { Payload } from "../chain/payload.ts";

type Skip = { pattern: RegExp; label: string };

const SKIPS: Skip[] = [
  { pattern: /\bgit\b[^|;&]*\b(commit|push|merge|rebase|am)\b[^|;&]*--no-verify/, label: "--no-verify" },
  { pattern: /\bgit\b[^|;&]*\bcommit\b[^|;&]*(?<![\w-])-[a-zA-Z]*n/, label: "git commit -n" },
  { pattern: /\bHUSKY=0\b|\bPRE_COMMIT_ALLOW_NO_VERIFY\b|\bSKIP_HOOKS\b/, label: "an environment flag" },
  { pattern: /\brm\b[^|;&]*\.git\/hooks/, label: "deleting .git/hooks" },
];

const SILENCES: RegExp[] = [
  /\/\/\s*eslint-disable(?!-next-line\s+prettier)/,
  /\/\*\s*eslint-disable(?!-next-line\s+prettier)/,
  /@ts-(ignore|expect-error|nocheck)/,
  /#\s*(noqa|nosec)\b/,
  /\bNOLINTNEXTLINE\b/,
  /"\$allow-list"\s*:/,
];

const INLINE = /-c\s+core\.hooksPath=(\S*)/gi;

/** Every value this command would leave core.hooksPath at, as written. Empty string
 *  means unset, which stops every hook in the repo and says nothing. */
export function hooksPathTargets(command: string): string[] {
  const words = command.split(/\s+/);
  const found: string[] = [];
  for (const match of command.matchAll(INLINE)) found.push(match[1]!.replace(/^["']|["']$/g, ""));
  if (words.some((w) => w === "config") && words.some((w) => w.toLowerCase() === "core.hookspath")) {
    if (words.some((w) => w.startsWith("--unset"))) {
      found.push("");
    } else if (!words.some((w) => ["--get", "--get-all", "--list"].includes(w))) {
      const index = words.findIndex((w) => w.toLowerCase() === "core.hookspath");
      const after = words.slice(index + 1).filter((w) => !w.startsWith("-"));
      if (after.length > 0) found.push(after[0]!.replace(/^["']|["']$/g, ""));
    }
  }
  return found;
}

/** Decided on the value, never on the verb. Resolved against the repo root first:
 *  this repo's own bootstrap writes the relative form, and a string comparison
 *  would deny the command that installs the hooks. */
export function hooksPathElsewhere(value: string, repoRoot: string | null): boolean {
  if (!value) return true;
  const root = repoRoot ?? process.cwd();
  try {
    const candidate = isAbsolute(value) ? value : resolve(root, value);
    return !existsSync(candidate); // our planted floor is the only path that exists AND is ours
  } catch {
    return true;
  }
}

export type GuardResult = { deny: true; reason: string } | { deny: false } | undefined;

/** Judge a Bash command for hook skips. */
export function checkBash(command: string, repoRoot: string | null): GuardResult {
  for (const target of hooksPathTargets(command)) {
    if (hooksPathElsewhere(target, repoRoot)) {
      return {
        deny: true,
        reason: `this points core.hooksPath at ${target || "nothing"} instead of the floor this install wires, so the git hooks stop running and nothing says so. Whatever the hooks would have said is what needs fixing.`,
      };
    }
  }
  for (const skip of SKIPS) {
    if (skip.pattern.test(command)) {
      return {
        deny: true,
        reason: `${skip.label} skips the git hooks, the floor every agent and every person in this repository commits through. Whatever the hooks would have said is what needs fixing. Run the command without it.`,
      };
    }
  }
  return undefined;
}

/** Judge file content for linter silences — the same act in the other vocabulary. */
export function checkContent(content: string): GuardResult {
  for (const rule of SILENCES) {
    if (rule.test(content)) {
      return {
        deny: true,
        reason:
          "this silences a check (eslint-disable / @ts-ignore / noqa / nosec / NOLINT / allow-list). Silencing a check is skipping a hook. If the skip is legitimate, .ai-engineering/overrides.toml with a reason — it lands in the receipt and the commit.",
      };
    }
  }
  return undefined;
}

const OVERRIDE_HINT =
  "Si el skip es legítimo, abre .ai-engineering/overrides.toml con un reason — quedará en el receipt y en el commit.";

export const NO_VERIFY_REASON_TAIL = OVERRIDE_HINT;

export function runNoVerify(payload: Payload, repoRoot: string | null): GuardResult {
  if (payload.tool_name === "Bash" || payload.tool_name === "PowerShell") {
    const command = payload.tool_input["command"];
    if (typeof command === "string" && command.length > 0) return checkBash(command, repoRoot);
    return undefined;
  }
  // Edit|Write|MultiEdit|NotebookEdit judge the content being written.
  const newString = payload.tool_input["new_string"] ?? payload.tool_input["content"] ?? "";
  if (typeof newString === "string" && newString.length > 0) return checkContent(newString);
  return undefined;
}
