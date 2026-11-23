// lease — lane rule 2: one folder, one writer. The first session that writes in a folder
// holds it while it keeps writing; another session's write there is stopped and sent to a
// worktree. Two sessions in one checkout is how one session's `git add -A` swept another's
// 34 files, and how a mixed-tree commit became the base of six PRs nobody could merge.
//
// The lease lives in the folder's own git directory (`.git/`, or a worktree's gitdir), so
// it is never committed and each worktree has its own. A write is judged in the checkout it
// lands in, not the one the session started in: the file's folder, or the folder a git
// command acts in (`-C`, a `cd` the shell surely ran first). Otherwise the guard would send
// a session to a worktree and then stop its first commit there. It lapses after `[work]
// lease_minutes` (15) without a write: a session that ended without saying so frees the
// folder by itself. SessionEnd frees it at once where the host sends one, and
// `ai-eng work release` frees it by hand. A host that names no session is never judged:
// without an id, every call would look like a new session.

import { existsSync, mkdirSync, readFileSync, realpathSync, rmSync, statSync, writeFileSync } from "node:fs";
import { basename, dirname, join, resolve } from "node:path";
import { loadConfig } from "../env.ts";
import type { Payload } from "../payload.ts";
import type { GuardResult } from "./no-verify.ts";
import { commandIndex, fileRedirectTargets, inlineShellPrograms, normalizeRedirects, shellSegments, shellWords, stripRedirectWords, type ShellWord } from "./shell.ts";

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

/** A `cd` before the git command only moves it when the shell surely ran that `cd` first and
 *  in the same shell: no subshell, pipeline, `||` branch or substitution anywhere in the line.
 *  Otherwise the command is judged where it started, which is the stricter answer. */
const UNSURE_CD = /[|()`]|\$\(/;

/** The folders the git writes in this command act in: the folder `-C` names (each `-C` adds to
 *  the last), else the folder a plain `cd <dir>` before it leads to, else `cwd`. */
function gitWriteDirs(command: string, cwd: string): string[] {
  const normalized = normalizeRedirects(command);
  const segments = shellSegments(normalized);
  if (segments === null) return [];
  const isCdSure = !UNSURE_CD.test(normalized);
  let dir = cwd;
  const dirs: string[] = [];
  for (const segment of segments) {
    const words = stripRedirectWords(shellWords(segment.text));
    const values = words.map((word) => word.value);
    const at = commandIndex(values);
    const name = values[at];
    if (name === "cd" || name === "pushd") {
      dir = nextDir(dir, cwd, isCdSure, words, at);
      continue;
    }
    if (name === undefined || !/(^|[\\/])git(\.exe)?$/.test(name)) continue;
    let gitDir = dir;
    let index = at + 1;
    while (index < values.length && values[index]!.startsWith("-")) {
      if (values[index] === "-C" && values[index + 1] !== undefined) gitDir = resolve(gitDir, values[index + 1]!);
      index += GIT_VALUE_OPTIONS.has(values[index]!) ? 2 : 1;
    }
    if (GIT_WRITES.has(values[index] ?? "")) dirs.push(gitDir);
  }
  return dirs;
}

const SHELL_FILE_WRITERS = new Set(["rm", "touch", "mkdir", "truncate", "tee"]);
const SHELL_DEST_WRITERS = new Set(["cp", "mv"]);

/** Advance `dir` when a segment is a plain `cd`/`pushd` in an unambiguous command. */
function nextDir(dir: string, cwd: string, isCdSure: boolean, words: ReturnType<typeof shellWords>, at: number): string {
  const values = words.map((word) => word.value);
  const target = words[at + 1];
  // `cd` alone, `cd -`, a path with `$x`/`*`/`?` in it, or one that starts with `~`: a place
  // this reading cannot name. A `~` later in the word is a plain letter (`RUNNER~1`, the
  // short name Windows gives its temp folder); the shell expands only a leading one.
  const isPlain = target !== undefined && values.length === at + 2 && !/[$*?]/.test(target.unquoted) && !target.unquoted.startsWith("~") && target.value !== "-";
  if (isCdSure && isPlain && existsSync(resolve(dir, target.value))) return resolve(dir, target.value);
  return isCdSure ? cwd : dir;
}

function sedInPlaceTargets(args: readonly ShellWord[]): ShellWord[] {
  let isInPlace = false;
  let hasScriptFlag = false;
  let separateInPlaceExt: string | undefined;
  const positionals: ShellWord[] = [];
  for (let index = 0; index < args.length; index++) {
    const word = args[index]!;
    const value = word.value;
    if (value === "--") {
      positionals.push(...args.slice(index + 1));
      break;
    }
    if (/^-[A-Za-z]*i/.test(value) || value.startsWith("--in-place")) {
      isInPlace = true;
      if (/^-[A-Za-z]*i$/.test(value)) {
        const next = args[index + 1];
        if (next !== undefined && !next.value.startsWith("-")) separateInPlaceExt = next.value;
      }
      continue;
    }
    if (value === "-e" || value === "-f" || value === "--expression" || value === "--file") {
      hasScriptFlag = true;
      index++;
      continue;
    }
    if (/^-[A-Za-z]*[ef]/.test(value) || value.startsWith("--expression=") || value.startsWith("--file=")) {
      hasScriptFlag = true;
      continue;
    }
    if (value.startsWith("-")) continue;
    positionals.push(word);
  }
  if (!isInPlace) return [];
  const skipBackupExt = separateInPlaceExt !== undefined && (
    separateInPlaceExt === "" ||
    (positionals.length >= (hasScriptFlag ? 2 : 3) && !/[/;\s]/.test(separateInPlaceExt))
  );
  const skipCount = (skipBackupExt ? 1 : 0) + (hasScriptFlag ? 0 : 1);
  return positionals
    .slice(skipCount)
    .filter((word) => !word.value.startsWith("/dev/") && !/[$`*?[]/.test(word.unquoted));
}

/** Directories a shell command writes into via redirects (`>`, `>>`) or common file-writing verbs.
 *  `2>&1`, `>&-`, `/dev/*`, and read commands return nothing. */
function shellWriteDirs(command: string, cwd: string): string[] {
  const normalized = normalizeRedirects(command);
  const segments = shellSegments(normalized);
  if (segments === null) return [];
  const isCdSure = !UNSURE_CD.test(normalized);
  let dir = cwd;
  const dirs: string[] = [];
  for (const segment of segments) {
    const words = shellWords(segment.text);
    const plain = stripRedirectWords(words);
    const values = plain.map((word) => word.value);
    const at = commandIndex(values);
    const verb = basename(values[at] ?? "");
    if (verb === "cd" || verb === "pushd") {
      dir = nextDir(dir, cwd, isCdSure, plain, at);
      continue;
    }
    for (const target of fileRedirectTargets(words)) {
      if (!/[$`*?[]/.test(target.unquoted)) dirs.push(dirname(resolve(dir, target.value)));
    }
    const args = plain.slice(at + 1);
    const nonFlagPaths = args.filter((word) => !word.value.startsWith("-") && !word.value.startsWith("/dev/") && !/[$`*?[]/.test(word.unquoted));
    if (SHELL_FILE_WRITERS.has(verb)) {
      for (const target of nonFlagPaths) dirs.push(dirname(resolve(dir, target.value)));
    } else if (SHELL_DEST_WRITERS.has(verb) && nonFlagPaths.length >= 2) {
      const dest = nonFlagPaths.at(-1)!;
      dirs.push(dirname(resolve(dir, dest.value)));
    } else if (verb === "sed") {
      for (const target of sedInPlaceTargets(args)) dirs.push(dirname(resolve(dir, target.value)));
    }
  }
  return dirs;
}

/** The file a file-writing tool targets, as the host names it. */
function targetPath(payload: Payload): string | null {
  for (const key of ["file_path", "notebook_path", "path"]) {
    const value = payload.tool_input[key];
    if (typeof value === "string" && value.length > 0) return value;
  }
  return null;
}

/** The checkout a path lies in: the nearest folder at or above it that holds a `.git`. */
function checkoutOf(path: string): string | null {
  let dir = resolve(path);
  for (;;) {
    if (existsSync(join(dir, ".git"))) return dir;
    const parent = dirname(dir);
    if (parent === dir) return null;
    dir = parent;
  }
}

/** The repository's shared git directory: `.git` itself, or what a worktree's gitdir names. */
function commonDirOf(checkout: string): string | null {
  const gitDir = gitDirOf(checkout);
  if (gitDir === null) return null;
  let common = gitDir; // no commondir file: this is the main checkout's own .git
  try {
    common = resolve(gitDir, readFileSync(join(gitDir, "commondir"), "utf8").trim());
  } catch {
    /* the main checkout */
  }
  // git writes a worktree's pointer as a real path (/private/var on macOS, the long
  // C:\Users\runneradmin on Windows) while the root may arrive through a link (/var) or an
  // 8.3 short name (RUNNER~1): compare where they really are. Only the native call expands
  // a short name.
  try {
    return realpathSync.native(common);
  } catch {
    return common;
  }
}

/** The checkouts of this repository a call writes into. A file or a git command aimed at a
 *  temp folder or another repository is nobody's here; one aimed at a worktree of this
 *  repository is that worktree's to hold, not the main checkout's. */
function writtenCheckouts(payload: Payload, root: string): string[] {
  const cwd = typeof payload["cwd"] === "string" && payload["cwd"].length > 0 ? resolve(payload["cwd"]) : resolve(root);
  let dirs: string[];
  if (FILE_WRITES.has(payload.tool_name)) {
    const target = targetPath(payload);
    dirs = [target === null ? cwd : dirname(resolve(cwd, target))];
  } else if (payload.tool_name === "Bash" || payload.tool_name === "PowerShell" || payload.tool_name === "shell" || payload.tool_name === "command") {
    const command = payload.tool_input["command"];
    if (typeof command !== "string") dirs = [];
    else {
      const programs = [command, ...inlineShellPrograms(command)];
      dirs = programs.flatMap((program) => [...gitWriteDirs(program, cwd), ...shellWriteDirs(program, cwd)]);
    }
  } else {
    return [];
  }
  const repository = commonDirOf(root);
  const checkouts = new Set<string>();
  for (const dir of dirs) {
    const checkout = checkoutOf(dir);
    if (checkout !== null && repository !== null && commonDirOf(checkout) === repository) checkouts.add(checkout);
  }
  return [...checkouts];
}

/** The guard: hold each folder written on this session's write, or stop another session's. */
export function runLease(payload: Payload, root: string | null, now: number = Date.now()): GuardResult {
  const session = typeof payload.session_id === "string" ? payload.session_id.trim() : "";
  if (root === null || session === "") return undefined;
  const minutes = leaseMinutes(root);
  const checkouts = writtenCheckouts(payload, root);
  const held = checkouts
    .map((checkout) => ({ checkout, lease: readLease(checkout) }))
    .find(({ lease }) => lease !== null && lease.session !== session && now - lease.ts < minutes * MINUTE_MS);
  if (held === undefined) {
    for (const checkout of checkouts) writeLease(checkout, { session, ts: now });
    return undefined;
  }
  const lease = held.lease!;
  const idle = Math.floor((now - lease.ts) / MINUTE_MS);
  const left = Math.max(1, minutes - idle);
  return {
    deny: true,
    reason:
      `BLOCKED: another session (${lease.session.slice(0, 8)}, last write ${idle} min ago) is writing in ${held.checkout}. ` +
      "One folder, one writer: do this work in a worktree — your host's worktree support, or `ai-eng worktree new <branch>` and its reported path. " +
      `If that session has ended, \`ai-eng work release\` frees the folder now; otherwise it frees itself in ${left} min.`,
  };
}
