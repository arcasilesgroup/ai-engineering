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
  /** Ignore the user's global and system config (and config injected through the
   *  environment) so only the repository's own config decides what git sees (R8). */
  isolated?: boolean;
}

function isolatedEnv(): NodeJS.ProcessEnv {
  const env: NodeJS.ProcessEnv = { ...process.env, GIT_CONFIG_GLOBAL: devNull, GIT_CONFIG_SYSTEM: devNull, GIT_CONFIG_NOSYSTEM: "1" };
  for (const injected of ["GIT_CONFIG_COUNT", "GIT_CONFIG_PARAMETERS", "GIT_CONFIG"]) delete env[injected];
  return env;
}

export function runGit(args: string[], opts: GitRunOptions): GitResult {
  try {
    const env = { ...(opts.isolated === true ? isolatedEnv() : process.env), GIT_TERMINAL_PROMPT: "0" };
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
