// src/git/run.ts — the one Git runner: status, raw stdout and stderr, never a throw.
import { spawnSync } from "node:child_process";
import { devNull } from "node:os";

export interface GitResult {
  status: number;
  stdout: string;
  stderr: string;
}

export interface GitRunOptions {
  cwd: string;
  env?: NodeJS.ProcessEnv;
  /** Ignore the user's global and system config, config injected through the environment,
   *  and the repository-discovery variables (GIT_DIR, GIT_WORK_TREE, ...) a hook inherits,
   *  so cwd and the repository's own config alone decide what git sees (R8). `env` is
   *  then layered on top, so a caller can pass values it resolved on purpose. */
  isolated?: boolean;
}

let repositoryEnvVars: string[] | undefined;

/** The variables git itself lists as repository-local (config injection included), asked of git once per process (R7). */
function localEnvVars(cwd: string): string[] | Error {
  if (repositoryEnvVars !== undefined) return repositoryEnvVars;
  const done = spawnSync("git", ["rev-parse", "--local-env-vars"], { cwd, encoding: "utf8", env: { ...process.env, GIT_TERMINAL_PROMPT: "0" } });
  const names = (done.stdout ?? "").split("\n").filter((name) => name !== "");
  if (done.error !== undefined || done.status !== 0 || !names.includes("GIT_DIR")) {
    return new Error(`cannot list git's repository variables (git rev-parse --local-env-vars): ${done.stderr || String(done.error ?? `exit ${done.status}`)}`);
  }
  repositoryEnvVars = names;
  return names;
}

/** The environment without the variables that relocate the repository or inject config. */
function repositoryScopedEnv(cwd: string): NodeJS.ProcessEnv | Error {
  const names = localEnvVars(cwd);
  if (names instanceof Error) return names;
  const env: NodeJS.ProcessEnv = { ...process.env };
  for (const name of names) delete env[name];
  return env;
}

function isolatedEnv(cwd: string, overrides: NodeJS.ProcessEnv | undefined): NodeJS.ProcessEnv | Error {
  const env = repositoryScopedEnv(cwd);
  if (env instanceof Error) return env;
  return { ...env, GIT_CONFIG_GLOBAL: devNull, GIT_CONFIG_SYSTEM: devNull, GIT_CONFIG_NOSYSTEM: "1", ...overrides };
}

export function runGit(args: string[], opts: GitRunOptions): GitResult {
  try {
    const baseEnv = opts.isolated === true ? isolatedEnv(opts.cwd, opts.env) : opts.env ?? process.env;
    // Isolation that cannot be established denies: the run never falls back to the ambient environment.
    if (baseEnv instanceof Error) return { status: 1, stdout: "", stderr: baseEnv.message };
    const env = { ...baseEnv, GIT_TERMINAL_PROMPT: "0" };
    const done = spawnSync("git", args, { cwd: opts.cwd, encoding: "utf8", env });
    const stdout = done.stdout ?? "";
    const stderr = done.stderr ?? "";
    // A spawn failure (no git binary, missing cwd) or a signal leaves no exit status.
    if (done.error !== undefined || done.status === null) {
      return { status: 1, stdout, stderr: stderr || String(done.error ?? `git stopped by ${done.signal}`) };
    }
    return { status: done.status, stdout, stderr };
  } catch (error) {
    return { status: 1, stdout: "", stderr: String(error) };
  }
}

const IDENTITY_FIX = 'set it with `git config --global user.name "Your Name"` and `git config --global user.email "you@example.com"`';

/** The author and committer an isolated commit records. The isolated runner ignores the
 *  global config where most machines keep `user.name` and `user.email`, so the identity
 *  is read the normal way (local, then global and system config) and passed explicitly;
 *  an identity already set in the environment still wins, as it would for git itself.
 *  Only the repository-relocating variables are dropped, so cwd still decides the
 *  repository (R8). A failed read or a missing value refuses rather than guessing. */
export function commitIdentityEnv(cwd: string): NodeJS.ProcessEnv | Error {
  const env = repositoryScopedEnv(cwd);
  if (env instanceof Error) return env;
  const configured: Record<string, string> = {};
  for (const key of ["user.name", "user.email"]) {
    const read = runGit(["config", "--get", key], { cwd, env });
    if (read.status === 1 && read.stderr.trim() === "") continue;
    if (read.status !== 0 || read.stderr.trim() !== "") {
      return new Error(`cannot read git ${key} (${read.stderr.trim() || `git config exited ${read.status}`})`);
    }
    const value = read.stdout.trim();
    if (value !== "") configured[key] = value;
  }
  const identity: NodeJS.ProcessEnv = {
    GIT_AUTHOR_NAME: process.env.GIT_AUTHOR_NAME || configured["user.name"],
    GIT_AUTHOR_EMAIL: process.env.GIT_AUTHOR_EMAIL || configured["user.email"],
    GIT_COMMITTER_NAME: process.env.GIT_COMMITTER_NAME || configured["user.name"],
    GIT_COMMITTER_EMAIL: process.env.GIT_COMMITTER_EMAIL || configured["user.email"],
  };
  const missing = Object.keys(identity).filter((name) => !identity[name]);
  if (missing.length > 0) return new Error(`no Git commit identity (${missing.join(", ")} unresolved); ${IDENTITY_FIX}`);
  return identity;
}
