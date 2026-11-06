import { spyOn } from "bun:test";
import { worktreeMain } from "../../src/commands/worktree.ts";

export interface WorktreeCommandRun {
  status: number;
  stdout: string;
  stderr: string;
}

/** Call the command handler in-process; process-level CLI coverage stays in the contract tests. */
export function runWorktreeCommand(args: string[], cwd: string, env: NodeJS.ProcessEnv = {}): WorktreeCommandRun {
  const commandEnv = { ...env };
  const priorEnv = { ...process.env };
  const priorCwd = process.cwd();
  const stdoutChunks: string[] = [];
  const stderrChunks: string[] = [];
  const stdout = spyOn(process.stdout, "write").mockImplementation(((chunk: unknown) => {
    stdoutChunks.push(String(chunk));
    return true;
  }) as never);
  const stderr = spyOn(process.stderr, "write").mockImplementation(((chunk: unknown) => {
    stderrChunks.push(String(chunk));
    return true;
  }) as never);

  try {
    process.chdir(cwd);
    for (const key of Object.keys(process.env)) {
      if (!(key in commandEnv)) delete process.env[key];
    }
    for (const [key, value] of Object.entries(commandEnv)) {
      if (value === undefined) delete process.env[key];
      else process.env[key] = value;
    }
    const commandArgs = args[0] === "worktree" ? args.slice(1) : args;
    const force = commandArgs.includes("--force");
    const status = worktreeMain(commandArgs.filter((arg) => arg !== "--force"), force);
    return { status, stdout: stdoutChunks.join(""), stderr: stderrChunks.join("") };
  } finally {
    stdout.mockRestore();
    stderr.mockRestore();
    process.chdir(priorCwd);
    for (const key of Object.keys(process.env)) {
      if (!(key in priorEnv)) delete process.env[key];
    }
    Object.assign(process.env, priorEnv);
  }
}
