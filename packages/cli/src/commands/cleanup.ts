import { spawn } from "node:child_process";

import { GitAdapter, isErr } from "@ai-engineering/runtime";

import { hasFlag, parseArgs, stringFlag } from "./_args.ts";
import type { CommandHandler } from "./index.ts";

/**
 * `ai-eng cleanup` — branch hygiene helper.
 *
 * Steps:
 *   1. `git fetch --prune` to discard remote-tracking branches that no
 *      longer exist upstream.
 *   2. List local branches already merged into the default base
 *      (`main` by default; override with `--base <ref>`).
 *   3. Print the candidates. Without `--yes` the command stops there
 *      (dry-run by default — Constitution: never destructive without
 *      explicit user confirmation).
 *
 * Currently does NOT delete branches even with `--yes` because branch
 * deletion is destructive; Phase 4.1 emits the candidate list and lets
 * the user copy the suggested command. Future phases can extend this
 * with an explicit `--delete` opt-in once UX flows are agreed.
 */
const runGitOutput = (
  cwd: string,
  args: ReadonlyArray<string>,
): Promise<{ ok: boolean; stdout: string; stderr: string }> =>
  new Promise((resolve) => {
    const child = spawn("git", [...args], { cwd });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (d: Buffer) => {
      stdout += d.toString("utf8");
    });
    child.stderr.on("data", (d: Buffer) => {
      stderr += d.toString("utf8");
    });
    child.on("error", () => resolve({ ok: false, stdout, stderr }));
    child.on("close", (code) => resolve({ ok: code === 0, stdout, stderr }));
  });

const listMergedBranches = async (
  cwd: string,
  base: string,
): Promise<{ ok: true; branches: string[] } | { ok: false; reason: string }> => {
  const r = await runGitOutput(cwd, ["branch", "--merged", base]);
  if (!r.ok) {
    return {
      ok: false,
      reason: r.stderr.trim() || `git branch --merged ${base} failed`,
    };
  }
  const branches = r.stdout
    .split("\n")
    .map((line) => line.replace(/^\*\s*/, "").trim())
    .filter((line) => line.length > 0)
    .filter((line) => line !== base && line !== "main" && line !== "master");
  return { ok: true, branches };
};

export const cleanup: CommandHandler = async (args) => {
  const parsed = parseArgs(args);
  const base = stringFlag(parsed, "base") ?? "main";
  const cwd = process.cwd();
  const adapter = new GitAdapter(cwd);

  // Surface adapter-level failure consistently with other commands.
  const root = await adapter.worktreeRoot();
  if (isErr(root)) {
    process.stderr.write(`cleanup: not a git repo (${root.error.message})\n`);
    return 1;
  }

  const fetchResult = await runGitOutput(cwd, ["fetch", "--prune"]);
  if (!fetchResult.ok) {
    process.stderr.write(
      `cleanup: git fetch --prune failed: ${fetchResult.stderr.trim() || "(unknown)"}\n`,
    );
    return 1;
  }
  process.stdout.write("[ai-eng] cleanup: fetched + pruned remote refs.\n");

  const merged = await listMergedBranches(cwd, base);
  if (!merged.ok) {
    process.stderr.write(`cleanup: ${merged.reason}\n`);
    return 1;
  }
  if (hasFlag(parsed, "json")) {
    process.stdout.write(
      `${JSON.stringify({ base, merged: merged.branches, deleted: [] }, null, 2)}\n`,
    );
    return 0;
  }
  if (merged.branches.length === 0) {
    process.stdout.write(
      `[ai-eng] cleanup: no local branches merged into ${base}; nothing to tidy.\n`,
    );
    return 0;
  }
  process.stdout.write(
    `[ai-eng] cleanup: ${merged.branches.length} branch(es) merged into ${base}:\n`,
  );
  for (const b of merged.branches) {
    process.stdout.write(`  - ${b}\n`);
  }
  if (!hasFlag(parsed, "yes")) {
    process.stdout.write(
      "[ai-eng] cleanup: dry-run. Re-run with --yes to confirm (delete will still require: git branch -d <name>).\n",
    );
    return 0;
  }
  process.stdout.write("[ai-eng] cleanup: --yes acknowledged. Suggested command:\n");
  process.stdout.write(
    `    git branch -d ${merged.branches.map((b) => JSON.stringify(b)).join(" ")}\n`,
  );
  return 0;
};
