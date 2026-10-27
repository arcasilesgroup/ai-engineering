// src/git/context.ts — where am I and what does my work merge into (brainstorm 6.7).
// The base order is: explicit argument, then `[git] base` in config.toml, then the
// default branch of the current branch's upstream remote (or origin) read from local
// refs, else ask. A base equal to the current branch also asks. The forge step (6.7
// step 4) lives in ai-pr, never here: this module does not touch the network.
import { realpathSync } from "node:fs";
import { join } from "node:path";
import { loadConfig } from "../env.ts";
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
    throw new Error(`not inside a Git working tree: ${cwd}${done.stderr.trim() === "" ? "" : ` (${done.stderr.trim()})`}`);
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
  throw new Error(`cannot read the current branch in ${root}: ${done.stderr.trim() || ref || `git exited ${done.status}`}`);
}

/** A base name must be a plain branch name, so it can never smuggle an option or a revision expression into a later command. */
function requireBranchName(root: string, name: string, origin: string): string {
  const done = git(root, ["check-ref-format", "--branch", name]);
  if (done.status === 0 && done.stdout.trim() === name) return name;
  throw new Error(`${origin} is not a valid branch name: ${JSON.stringify(name)}`);
}

function configuredBase(root: string): string | undefined {
  const value = loadConfig(root)["git"]?.["base"];
  if (value === undefined) return undefined;
  if (typeof value !== "string") throw new Error(`[git] base in ${join(root, ".ai-engineering", "config.toml")} must be a string`);
  return requireBranchName(root, value, "[git] base");
}

/** The current branch's upstream remote, else origin (also for a detached HEAD). */
function baseRemote(root: string, branch: string | null): string {
  if (branch === null) return FALLBACK_REMOTE;
  // for-each-ref matches by prefix, so the exact ref is picked from its own output.
  const done = git(root, ["for-each-ref", "--format=%(refname)%00%(upstream:remotename)", `${HEADS}${branch}`]);
  if (done.status !== 0) throw new Error(`cannot read the upstream of ${branch} in ${root}: ${done.stderr.trim()}`);
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

function detectBase(root: string, branch: string | null, explicitBase: string | undefined): { base: string; baseSource: BaseSource } | null {
  if (explicitBase !== undefined) return { base: requireBranchName(root, explicitBase, "the explicit base"), baseSource: "explicit" };
  const fromConfig = configuredBase(root);
  if (fromConfig !== undefined) return { base: fromConfig, baseSource: "config" };
  const fromRemote = remoteDefault(root, baseRemote(root, branch));
  return fromRemote === null ? null : { base: fromRemote, baseSource: "remote-head" };
}

/** Throws, naming cwd, when cwd is not inside a Git working tree. */
export function resolveContext(cwd: string, opts: { explicitBase?: string } = {}): GitContext {
  const { root, isLinkedWorktree } = locate(cwd);
  const branch = currentBranch(root);
  const where = { root, branch, isDetached: branch === null, isLinkedWorktree };
  const detected = detectBase(root, branch, opts.explicitBase);
  // The first source that answers decides: a base equal to the current branch asks, it never falls through.
  if (detected === null || detected.base === branch) return { ...where, base: null, baseSource: "ask" };
  return { ...where, ...detected };
}
