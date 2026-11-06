// src/git/run.ts — the one Git runner: status, raw stdout and stderr, never a throw.
import { spawnSync } from "node:child_process";

/** Git's documented "no config file" value. Not os.devNull: Git for Windows maps the literal
 *  "/dev/null" to NUL, but cannot access(2) node's `\\.\nul` and fails every command. */
const NO_CONFIG_FILE = "/dev/null";

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
  return { ...env, GIT_CONFIG_GLOBAL: NO_CONFIG_FILE, GIT_CONFIG_SYSTEM: NO_CONFIG_FILE, GIT_CONFIG_NOSYSTEM: "1", ...overrides };
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

/** `git var GIT_*_IDENT` prints `Name <email> <epoch> <offset>`. */
const IDENT_LINE = /^(.+) <([^<>]*)> \d+ [+-]\d{4}$/;

/** The author and committer an isolated commit records. The isolated runner ignores the
 *  global config where most machines keep the identity, so git itself is asked, with the
 *  normal config and environment, through `git var`: it applies git's own precedence
 *  (GIT_AUTHOR_* / GIT_COMMITTER_* env, then author.* / committer.*, then user.*, then
 *  EMAIL) and the names are passed explicitly. Only the repository-relocating variables
 *  are dropped, so cwd still decides the repository (R8). Where git would refuse to
 *  commit, this refuses too. */
export function commitIdentityEnv(cwd: string): NodeJS.ProcessEnv | Error {
  const env = repositoryScopedEnv(cwd);
  if (env instanceof Error) return env;
  const identity: NodeJS.ProcessEnv = {};
  for (const role of ["AUTHOR", "COMMITTER"]) {
    const read = runGit(["var", `GIT_${role}_IDENT`], { cwd, env });
    const parsed = IDENT_LINE.exec(read.stdout.trim());
    if (read.status !== 0 || parsed === null) {
      const reason = read.stderr.trim().split("\n").pop() || `git var GIT_${role}_IDENT exited ${read.status}`;
      return new Error(`no Git commit identity (${reason}); ${IDENTITY_FIX}`);
    }
    identity[`GIT_${role}_NAME`] = parsed[1];
    identity[`GIT_${role}_EMAIL`] = parsed[2];
  }
  return identity;
}
