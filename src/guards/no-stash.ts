// no-stash — lane rule 3: work never leaves its branch for the stash. A stash belongs to
// no branch and shows on no board; a 54-day-old stash of a branch deleted since is how
// it ends. Reading and restoring a stash stays allowed: that is how one gets out of it.

import type { Payload } from "../payload.ts";
import type { GuardResult } from "./no-verify.ts";
import { commandIndex, inlineShellPrograms, shellSegments, shellWords } from "./shell.ts";

/** The subcommands that read a stash or bring it back. Everything else makes or drops one. */
const RESTORES = new Set(["list", "show", "apply", "pop", "branch"]);
/** git's own options that take the next word as their value. */
const VALUE_OPTIONS = new Set(["-C", "-c", "--git-dir", "--work-tree", "--namespace", "--config-env"]);

const REASON =
  "BLOCKED: git stash takes work off its branch, where no board sees it. Commit it on the branch instead " +
  '(git commit -m "wip: …"); to stop for a while, ai-eng work park <branch> "<reason>". ' +
  "Reading or restoring a stash (list, show, apply, pop, branch) is fine.";

/** The stash subcommand a shell segment runs, "" for a bare `git stash`, or null when the
 *  segment is not git stash at all. */
function stashSubcommand(segment: string): string | null {
  const words = shellWords(segment).filter((word) => !word.isOperator).map((word) => word.value);
  const at = commandIndex(words);
  if (words[at] === undefined || !/(^|[\\/])git(\.exe)?$/.test(words[at])) return null;
  let index = at + 1;
  while (index < words.length && words[index]!.startsWith("-")) index += VALUE_OPTIONS.has(words[index]!) ? 2 : 1;
  if (words[index] !== "stash") return null;
  return words[index + 1] ?? "";
}

export function runNoStash(payload: Payload): GuardResult {
  if (payload.tool_name !== "Bash" && payload.tool_name !== "PowerShell" && payload.tool_name !== "shell" && payload.tool_name !== "command") return undefined;
  const command = payload.tool_input["command"];
  if (typeof command !== "string" || command.length === 0) return undefined;
  // A command the grammar cannot read is the other guards' to judge; this one only
  // speaks about a stash it can see.
  const segments = shellSegments(command);
  if (segments === null) return undefined;
  const programs = [command, ...inlineShellPrograms(command)];
  for (const program of programs) {
    const parts = program === command ? segments : shellSegments(program);
    if (parts === null) continue;
    for (const segment of parts) {
      const subcommand = stashSubcommand(segment.text);
      if (subcommand !== null && !RESTORES.has(subcommand)) return { deny: true, reason: REASON };
    }
  }
  return undefined;
}
