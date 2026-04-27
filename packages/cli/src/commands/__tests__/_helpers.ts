import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

/**
 * Test helpers shared across CLI command suites.
 *
 * `withTmpCwd` creates a tmpdir, chdirs into it, runs the closure, and tears
 * down the directory + restores cwd afterwards. Bun's test runner is
 * single-threaded per file, so `process.chdir` is safe; concurrent files do
 * not interfere because each file gets its own tmpdir.
 *
 * `capture` swaps `process.stdout.write` / `process.stderr.write` for
 * appenders so we can assert on what a command printed without re-routing
 * the actual TTY.
 */
export const withTmpCwd = async <T>(
  prefix: string,
  fn: (root: string) => Promise<T>,
): Promise<T> => {
  const original = process.cwd();
  const root = mkdtempSync(join(tmpdir(), prefix));
  try {
    process.chdir(root);
    return await fn(root);
  } finally {
    process.chdir(original);
    rmSync(root, { recursive: true, force: true });
  }
};

export interface Captured {
  stdout: string;
  stderr: string;
  exitCode: number;
}

export const capture = async (fn: () => Promise<number>): Promise<Captured> => {
  const origStdout = process.stdout.write.bind(process.stdout);
  const origStderr = process.stderr.write.bind(process.stderr);
  let stdout = "";
  let stderr = "";
  process.stdout.write = ((chunk: string | Uint8Array): boolean => {
    stdout += typeof chunk === "string" ? chunk : Buffer.from(chunk).toString("utf8");
    return true;
  }) as typeof process.stdout.write;
  process.stderr.write = ((chunk: string | Uint8Array): boolean => {
    stderr += typeof chunk === "string" ? chunk : Buffer.from(chunk).toString("utf8");
    return true;
  }) as typeof process.stderr.write;
  try {
    const exitCode = await fn();
    return { stdout, stderr, exitCode };
  } finally {
    process.stdout.write = origStdout;
    process.stderr.write = origStderr;
  }
};
