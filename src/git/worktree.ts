// src/git/worktree.ts — the reads every worktree verb shares: where worktrees live,
// which ones git registers, whether one is clean, and whether an operation is mid-way.
// Every read is isolated (R8) and a read that fails is reported, never treated as empty.

import { existsSync, realpathSync } from "node:fs";
import { resolve } from "node:path";
import { loadConfig, printable } from "../env.ts";
import { type GitResult, runGit } from "./run.ts";

export interface RegisteredWorktree {
  path: string;
  /** The full `refs/heads/...` ref, or null when the worktree is detached. */
  branchRef: string | null;
  detached: boolean;
  prunable: boolean;
}

export interface WorktreeStatus {
  paths: string[];
  untracked: string[];
  detail?: string;
}

function git(cwd: string, args: string[]): GitResult {
  return runGit(args, { cwd, isolated: true });
}

/** git reports canonical paths — so the worktree root, and every comparison
 *  against a registered path, happens in the same realpathed form. `.native`, because
 *  on Windows the plain call keeps 8.3 short names (C:\Users\RUNNER~1) that git expands. */
export function canonicalize(path: string): string {
  try {
    return realpathSync.native(path);
  } catch {
    return resolve(path);
  }
}

/** `<repo>.worktrees` beside the repository, or `[git].worktrees_dir` from the
 *  primary checkout's `.ai-engineering/config.toml` when that key is present. The
 *  config is read from the primary tree, so a relative value is resolved there too:
 *  resolving it against the process directory would make the same repository report
 *  one root from the primary tree and another from inside an open worktree. */
export function worktreeRoot(repo: string): string {
  const configured = loadConfig(repo).git?.["worktrees_dir"];
  if (typeof configured === "string" && configured.trim()) return canonicalize(resolve(repo, configured.trim()));
  return `${repo}.worktrees`;
}

/** Every worktree git knows, or the reason it could not be read — a list that cannot
 *  be read is never an empty list, because that would let a guard pass unexamined. */
export function listWorktrees(repo: string): { worktrees: RegisteredWorktree[] } | { detail: string } {
  const listed = git(repo, ["worktree", "list", "--porcelain"]);
  if (listed.status !== 0 || listed.stderr.trim() !== "") {
    return { detail: `git worktree list exited ${listed.status}: ${listed.stderr.trim()}` };
  }
  const worktrees: RegisteredWorktree[] = [];
  for (const block of listed.stdout.split("\n\n")) {
    if (block.trim() === "") continue;
    const lines = block.split("\n");
    const pathLine = lines.find((line) => line.startsWith("worktree "));
    if (!pathLine) return { detail: `unreadable worktree list entry ${JSON.stringify(printable(block))}` };
    worktrees.push({
      // git prints `C:/...` on Windows; resolve gives the platform's own separators.
      path: resolve(pathLine.slice("worktree ".length)),
      branchRef: lines.find((line) => line.startsWith("branch "))?.slice("branch ".length) ?? null,
      detached: lines.includes("detached"),
      prunable: lines.some((line) => line.startsWith("prunable")),
    });
  }
  return { worktrees };
}

/** The paths one `-z` record carries and how many tokens it used. `-z` keeps every
 *  path as raw bytes — NUL-separated, nothing quoted and nothing C-escaped, so no
 *  path ever needs unescaping and a non-ASCII one cannot slip past a comparison.
 *  A rename or copy (R/C in either status column) carries its source as the next
 *  token. null means the record is unreadable, which blocks. */
export function statusPaths(tokens: string[], index: number): { paths: string[]; next: number } | null {
  const record = tokens[index];
  if (record === undefined || record.length < 4 || record[2] !== " ") return null;
  const path = record.slice(3);
  const renamed = record.slice(0, 2).split("").some((flag) => flag === "R" || flag === "C");
  if (!renamed) return { paths: [path], next: index + 1 };
  const source = tokens[index + 1];
  if (source === undefined || source === "") return null;
  return { paths: [path, source], next: index + 2 };
}

/** Every changed and untracked path in a worktree; `detail` says why the status could not be trusted. */
export function worktreeStatus(path: string): WorktreeStatus {
  const status = git(path, ["--no-optional-locks", "status", "--porcelain", "--untracked-files=all", "-z"]);
  if (status.status !== 0 || status.stderr.trim() !== "") {
    return { paths: [], untracked: [], detail: status.stderr.trim() || `git status exited ${status.status}` };
  }
  const paths: string[] = [];
  const untracked: string[] = [];
  const tokens = status.stdout.split("\0");
  for (let index = 0; index < tokens.length; ) {
    const token = tokens[index] ?? "";
    if (token === "") {
      index += 1;
      continue;
    }
    const read = statusPaths(tokens, index);
    if (read === null) return { paths: [], untracked: [], detail: "unreadable git status record" };
    paths.push(...read.paths);
    if (token.startsWith("?? ")) untracked.push(...read.paths);
    index = read.next;
  }
  return { paths: [...new Set(paths)], untracked: [...new Set(untracked)] };
}

/** The rebase or merge a worktree is in the middle of, or why that could not be read; null when none is. */
export function gitOperationState(path: string): string | null {
  for (const name of ["rebase-merge", "rebase-apply", "MERGE_HEAD"]) {
    const location = git(path, ["rev-parse", "--git-path", name]);
    if (location.status !== 0 || location.stderr.trim() !== "") {
      return `cannot read git ${name} state: ${location.stderr.trim() || `git exited ${location.status}`}`;
    }
    // Only the newline git appends is stripped: a path may itself end in spaces.
    const gitPath = location.stdout.endsWith("\n") ? location.stdout.slice(0, -1) : location.stdout;
    if (gitPath === "") return `cannot read git ${name} state path`;
    if (existsSync(resolve(path, gitPath))) return `${name} is in progress`;
  }
  return null;
}
