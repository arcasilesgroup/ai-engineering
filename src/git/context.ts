// src/git/context.ts — where am I and what does my work merge into (brainstorm 6.7).
// The base order is: explicit argument, then `[git] base` in config.toml, then the
// default branch of the current branch's upstream remote (or origin) read from local
// refs, else ask. A base equal to the current branch also asks. The forge step (6.7
// step 4) lives in ai-pr, never here: this module does not touch the network.
import { existsSync, readFileSync, realpathSync } from "node:fs";
import { join } from "node:path";
import { type GitResult, runGit } from "./run.ts";

export type BaseSource = "explicit" | "config" | "remote-head" | "ask";

export interface GitContext {
  /** The realpathed toplevel of the checkout or linked worktree holding cwd. */
  root: string;
  /** Short branch name; null when HEAD is detached. */
  branch: string | null;
  isDetached: boolean;
  isLinkedWorktree: boolean;
  /** Short branch name of the base; null exactly when baseSource is "ask". */
  base: string | null;
  baseSource: BaseSource;
  /** The remote whose HEAD named the base (base lives at refs/remotes/<baseRemote>/<base>);
   *  non-null exactly when baseSource is "remote-head". */
  baseRemote: string | null;
}

const HEADS = "refs/heads/";
const FALLBACK_REMOTE = "origin";

/** Every read is isolated from global and system config: only the repo decides (R8). */
function git(cwd: string, args: string[]): GitResult {
  return runGit(args, { cwd, isolated: true });
}

function realpathOr(path: string): string {
  try {
    return realpathSync(path);
  } catch {
    return path;
  }
}

function locate(cwd: string): { root: string; isLinkedWorktree: boolean } {
  const done = git(cwd, ["rev-parse", "--path-format=absolute", "--show-toplevel", "--git-dir", "--git-common-dir"]);
  const lines = done.stdout.split("\n").filter((line) => line !== "");
  const [toplevel, gitDir, commonDir] = lines;
  if (done.status !== 0 || lines.length !== 3 || toplevel === undefined || gitDir === undefined || commonDir === undefined) {
    const reason = done.stderr.trim() === "" ? "" : ` (${done.stderr.trim()})`;
    throw new Error(`not inside a Git working tree: ${cwd}${reason}; run from inside the repository or one of its worktrees`);
  }
  return { root: realpathSync(toplevel), isLinkedWorktree: realpathOr(gitDir) !== realpathOr(commonDir) };
}

/** The checked-out branch, or null for a detached HEAD; anything else fails closed. */
function currentBranch(root: string): string | null {
  const done = git(root, ["symbolic-ref", "--quiet", "HEAD"]);
  const ref = done.stdout.trim();
  if (done.status === 0 && ref.startsWith(HEADS)) return ref.slice(HEADS.length);
  // --quiet makes a detached HEAD the one silent failure; every other answer is unexpected.
  if (done.status === 1 && done.stdout === "" && done.stderr === "") return null;
  const reason = done.stderr.trim() || ref || `git exited ${done.status}`;
  throw new Error(`cannot read the current branch in ${root}: ${reason}; check HEAD with \`git -C ${root} symbolic-ref HEAD\``);
}

/** A base name must be a plain branch name, so it can never smuggle an option or a revision expression into a later command. */
function requireBranchName(root: string, name: string, origin: string, fix: string): string {
  const done = git(root, ["check-ref-format", "--branch", name]);
  if (done.status === 0 && done.stdout.trim() === name) return name;
  throw new Error(`${origin} is not a valid branch name: ${JSON.stringify(name)}; ${fix}`);
}

/** The parsed config.toml, or undefined when there is none. loadConfig reads a file it
 *  cannot parse as {}, which would silently drop a declared base: this read throws (R8). */
function readConfig(path: string): unknown {
  if (!existsSync(path)) return undefined;
  try {
    return Bun.TOML.parse(readFileSync(path, "utf8"));
  } catch (error) {
    throw new Error(`cannot read ${path} (${error instanceof Error ? error.message : String(error)}): fix the TOML so it parses, or remove the file`);
  }
}

/** `[git] base`, or undefined when config.toml or the key is absent; a file that exists but cannot be read throws (R8). */
function configuredBase(root: string): string | undefined {
  const path = join(root, ".ai-engineering", "config.toml");
  const config = readConfig(path);
  const section = typeof config === "object" && config !== null && "git" in config ? config.git : undefined;
  if (section === undefined) return undefined;
  if (typeof section !== "object" || section === null || Array.isArray(section)) {
    throw new Error(`git in ${path} must be a [git] table; write the base as [git] base = "<branch>"`);
  }
  const value = "base" in section ? section.base : undefined;
  if (value === undefined) return undefined;
  const fix = `set [git] base to a branch name in ${path}`;
  if (typeof value !== "string") throw new Error(`[git] base in ${path} must be a string; ${fix}`);
  return requireBranchName(root, value, `[git] base in ${path}`, fix);
}

/** The current branch's upstream remote, else origin (also for a detached HEAD). */
function baseRemote(root: string, branch: string | null): string {
  if (branch === null) return FALLBACK_REMOTE;
  // for-each-ref matches by prefix, so the exact ref is picked from its own output.
  const done = git(root, ["for-each-ref", "--format=%(refname)%00%(upstream:remotename)", `${HEADS}${branch}`]);
  if (done.status !== 0) {
    throw new Error(`cannot read the upstream of ${branch} in ${root}: ${done.stderr.trim()}; check it with \`git -C ${root} for-each-ref refs/heads/${branch}\``);
  }
  for (const line of done.stdout.split("\n")) {
    const [refname, remote] = line.split("\0");
    // "." is a local upstream: there is no remote default branch to read from it.
    if (refname === `${HEADS}${branch}` && remote !== undefined && remote !== "" && remote !== ".") return remote;
  }
  return FALLBACK_REMOTE;
}

/** The branch refs/remotes/<remote>/HEAD points at, read from local refs; null when absent or dangling. */
function remoteDefault(root: string, remote: string): string | null {
  const prefix = `refs/remotes/${remote}/`;
  const done = git(root, ["symbolic-ref", "--quiet", `${prefix}HEAD`]);
  const target = done.stdout.trim();
  if (done.status !== 0 || !target.startsWith(prefix) || target === `${prefix}HEAD`) return null;
  const resolves = git(root, ["rev-parse", "--verify", "--quiet", `${target}^{commit}`]);
  return resolves.status === 0 ? target.slice(prefix.length) : null;
}

type DetectedBase = Pick<GitContext, "baseSource" | "baseRemote"> & { base: string };

function detectBase(root: string, branch: string | null, explicitBase: string | undefined): DetectedBase | null {
  if (explicitBase !== undefined) {
    const base = requireBranchName(root, explicitBase, "the explicit base", "pass a plain branch name such as release/2.6");
    return { base, baseSource: "explicit", baseRemote: null };
  }
  const fromConfig = configuredBase(root);
  if (fromConfig !== undefined) return { base: fromConfig, baseSource: "config", baseRemote: null };
  const remote = baseRemote(root, branch);
  const fromRemote = remoteDefault(root, remote);
  return fromRemote === null ? null : { base: fromRemote, baseSource: "remote-head", baseRemote: remote };
}

/** Throws, naming cwd, when cwd is not inside a Git working tree. */
export function resolveContext(cwd: string, opts: { explicitBase?: string } = {}): GitContext {
  const { root, isLinkedWorktree } = locate(cwd);
  const branch = currentBranch(root);
  const where = { root, branch, isDetached: branch === null, isLinkedWorktree };
  const detected = detectBase(root, branch, opts.explicitBase);
  // The first source that answers decides: a base equal to the current branch asks, it never falls through.
  if (detected === null || detected.base === branch) return { ...where, base: null, baseSource: "ask", baseRemote: null };
  return { ...where, ...detected };
}
