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
   *  so cwd and the repository's own config alone decide what git sees (R8). */
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

function isolatedEnv(cwd: string): NodeJS.ProcessEnv | Error {
  const names = localEnvVars(cwd);
  if (names instanceof Error) return names;
  const env: NodeJS.ProcessEnv = { ...process.env, GIT_CONFIG_GLOBAL: devNull, GIT_CONFIG_SYSTEM: devNull, GIT_CONFIG_NOSYSTEM: "1" };
  for (const name of names) delete env[name];
  return env;
}

export function runGit(args: string[], opts: GitRunOptions): GitResult {
  try {
    const baseEnv = opts.isolated === true ? isolatedEnv(opts.cwd) : opts.env ?? process.env;
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
