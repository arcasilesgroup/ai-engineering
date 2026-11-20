// lease — lane rule 2: one folder, one writer. The first session that writes in a folder
// holds it while it keeps writing; another session's write there is stopped and sent to a
// worktree. Two sessions in one checkout is how one session's `git add -A` swept another's
// 34 files, and how a mixed-tree commit became the base of six PRs nobody could merge.
//
// The lease lives in the folder's own git directory (`.git/`, or a worktree's gitdir), so
// it is never committed and each worktree has its own. It lapses after `[work]
// lease_minutes` (15) without a write: a session that ended without saying so frees the
// folder by itself. SessionEnd frees it at once where the host sends one, and
// `ai-eng work release` frees it by hand. A host that names no session is never judged:
// without an id, every call would look like a new session.

import { existsSync, mkdirSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs";
import { dirname, isAbsolute, join, relative as relativePath, resolve } from "node:path";
import { loadConfig } from "../env.ts";
import type { Payload } from "../payload.ts";
import type { GuardResult } from "./no-verify.ts";
import { commandIndex, shellSegments, shellWords } from "./shell.ts";

const MINUTE_MS = 60 * 1000;
const FILE_WRITES = new Set(["Edit", "Write", "MultiEdit", "NotebookEdit"]);
/** The git commands that write the index, a ref or the tree: how one session takes another's work. */
const GIT_WRITES = new Set(["add", "commit", "checkout", "switch", "reset", "restore", "merge", "rebase", "cherry-pick", "revert", "stash", "rm", "mv", "pull", "am", "apply"]);
const GIT_VALUE_OPTIONS = new Set(["-C", "-c", "--git-dir", "--work-tree", "--namespace", "--config-env"]);

export type Lease = { session: string; ts: number };

/** The folder's own git directory: `.git` itself, or the path a worktree's `.git` file names. */
export function gitDirOf(root: string): string | null {
  const dotGit = join(root, ".git");
  try {
    if (statSync(dotGit).isDirectory()) return dotGit;
    const pointer = /^gitdir:\s*(.+)$/m.exec(readFileSync(dotGit, "utf8"))?.[1]?.trim();
    return pointer === undefined ? null : resolve(root, pointer);
  } catch {
    return null;
  }
}

function leasePath(root: string): string | null {
  const gitDir = gitDirOf(root);
  return gitDir === null ? null : join(gitDir, "ai-eng", "lease.json");
}

export function readLease(root: string): Lease | null {
  const path = leasePath(root);
  if (path === null || !existsSync(path)) return null;
  try {
    const lease = JSON.parse(readFileSync(path, "utf8")) as Partial<Lease>;
    return typeof lease.session === "string" && typeof lease.ts === "number" ? { session: lease.session, ts: lease.ts } : null;
  } catch {
    return null;
  }
}

function writeLease(root: string, lease: Lease): void {
  const path = leasePath(root);
  if (path === null) return;
  try {
    mkdirSync(dirname(path), { recursive: true });
    writeFileSync(path, JSON.stringify(lease));
  } catch {
    /* a lease that cannot be written protects nothing, and must not block the work */
  }
}

/** Frees the folder: by hand, or at the end of the session that holds it. */
export function releaseLease(root: string, session?: string): boolean {
  const lease = readLease(root);
  if (lease === null || (session !== undefined && lease.session !== session)) return false;
  const path = leasePath(root);
  if (path !== null) rmSync(path, { force: true });
  return true;
}

export function leaseMinutes(root: string): number {
  const value = loadConfig(root)["work"]?.["lease_minutes"];
  return typeof value === "number" && Number.isInteger(value) && value > 0 ? value : 15;
}

/** A shell command that writes the index, a ref or the tree through git. */
function writesThroughGit(command: string): boolean {
  const segments = shellSegments(command);
  if (segments === null) return false;
  return segments.some((segment) => {
    const words = shellWords(segment.text).filter((word) => !word.isOperator).map((word) => word.value);
    const at = commandIndex(words);
    if (words[at] === undefined || !/(^|[\\/])git(\.exe)?$/.test(words[at])) return false;
    let index = at + 1;
    while (index < words.length && words[index]!.startsWith("-")) index += GIT_VALUE_OPTIONS.has(words[index]!) ? 2 : 1;
    return GIT_WRITES.has(words[index] ?? "");
  });
}

/** The file a file-writing tool targets, as the host names it. */
function targetPath(payload: Payload): string | null {
  for (const key of ["file_path", "notebook_path", "path"]) {
    const value = payload.tool_input[key];
    if (typeof value === "string" && value.length > 0) return value;
  }
  return null;
}

/** A write into this folder. A file written elsewhere (a temp file, another checkout) is
 *  not this folder's to hold: only its own tree, or a git command run in it. */
function isWriteInto(payload: Payload, root: string): boolean {
  if (FILE_WRITES.has(payload.tool_name)) {
    const target = targetPath(payload);
    if (target === null) return true;
    const cwd = typeof payload["cwd"] === "string" && payload["cwd"].length > 0 ? payload["cwd"] : root;
    const relative = relativePath(resolve(root), resolve(cwd, target));
    return relative === "" || !(relative.startsWith("..") || isAbsolute(relative));
  }
  if (payload.tool_name !== "Bash" && payload.tool_name !== "PowerShell") return false;
  const command = payload.tool_input["command"];
  return typeof command === "string" && writesThroughGit(command);
}

/** The guard: hold the folder on this session's write, or stop another session's write. */
export function runLease(payload: Payload, root: string | null, now: number = Date.now()): GuardResult {
  const session = typeof payload.session_id === "string" ? payload.session_id.trim() : "";
  if (root === null || session === "" || !isWriteInto(payload, root)) return undefined;
  const lease = readLease(root);
  const minutes = leaseMinutes(root);
  const isHeldByOther = lease !== null && lease.session !== session && now - lease.ts < minutes * MINUTE_MS;
  if (!isHeldByOther) {
    writeLease(root, { session, ts: now });
    return undefined;
  }
  const idle = Math.floor((now - lease.ts) / MINUTE_MS);
  const left = Math.max(1, minutes - idle);
  return {
    deny: true,
    reason:
      `BLOCKED: another session (${lease.session.slice(0, 8)}, last write ${idle} min ago) is writing in ${root}. ` +
      "One folder, one writer: do this work in a worktree — your host's worktree support, or `ai-eng worktree new <branch>` and its reported path. " +
      `If that session has ended, \`ai-eng work release\` frees the folder now; otherwise it frees itself in ${left} min.`,
  };
}
