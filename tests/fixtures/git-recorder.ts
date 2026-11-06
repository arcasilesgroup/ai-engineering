import { spyOn } from "bun:test";
import * as childProcess from "node:child_process";
import { mkdirSync, readFileSync, writeFileSync, chmodSync } from "node:fs";
import { basename, delimiter, join } from "node:path";

export type GitRecorder = {
  /** Every git command line started while recording, one string of arguments each. */
  commands: () => string[];
  stop: () => void;
};

/** Starts recording the git commands a test's code starts. On POSIX a `git` shim on PATH
 *  sees every git, a child's too. Windows runs no shebang script, and Bun refuses to pass
 *  arguments such as `--format=%(refname)` through a batch shim's cmd.exe, so there the
 *  spawns of this process are spied instead. */
export function recordGitCommands(directory: string): GitRecorder {
  return process.platform === "win32" ? spyGitSpawns() : shimGitOnPath(directory);
}

function shimGitOnPath(directory: string): GitRecorder {
  const git = Bun.which("git");
  if (!git) throw new Error("git is not on PATH");
  const bin = join(directory, "git-bin");
  const log = join(bin, "commands");
  const quote = (value: string) => `'${value.replaceAll("'", "'\\''")}'`;
  mkdirSync(bin, { recursive: true });
  writeFileSync(join(bin, "git"), `#!/bin/sh\nprintf '%s\\n' "$*" >> ${quote(log)}\nexec ${quote(git)} "$@"\n`);
  chmodSync(join(bin, "git"), 0o755);
  const pathBefore = process.env["PATH"];
  process.env["PATH"] = `${bin}${delimiter}${pathBefore ?? ""}`;
  return {
    commands: () => readFileSync(log, "utf8").trim().split(/\r?\n/).filter(Boolean),
    stop: () => {
      if (pathBefore === undefined) delete process.env["PATH"];
      else process.env["PATH"] = pathBefore;
    },
  };
}

function spyGitSpawns(): GitRecorder {
  const recorded: string[] = [];
  const record = (command: unknown, args: unknown) => {
    if (/^git(\.exe)?$/i.test(basename(String(command))) && Array.isArray(args)) recorded.push(args.map(String).join(" "));
  };
  const spies: Array<{ mockRestore: () => void }> = [];
  for (const name of ["spawn", "spawnSync", "execFile", "execFileSync"] as const) {
    const original = childProcess[name] as (...values: unknown[]) => unknown;
    spies.push(spyOn(childProcess, name).mockImplementation(((...values: unknown[]) => {
      record(values[0], values[1]);
      return original(...values);
    }) as never));
  }
  for (const name of ["spawn", "spawnSync"] as const) {
    const original = Bun[name].bind(Bun) as (...values: unknown[]) => unknown;
    spies.push(spyOn(Bun, name).mockImplementation(((...values: unknown[]) => {
      const first = values[0] as { cmd?: unknown } | unknown[];
      const argv = Array.isArray(first) ? first : Array.isArray(first.cmd) ? first.cmd : [];
      record(argv[0], argv.slice(1));
      return original(...values);
    }) as never));
  }
  return {
    commands: () => [...recorded],
    stop: () => {
      for (const spy of spies) spy.mockRestore();
    },
  };
}
