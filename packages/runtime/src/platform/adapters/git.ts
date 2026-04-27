import { spawn } from "node:child_process";

import { type Result, err, ok } from "../../shared/kernel/result.ts";
import { GitError, type GitPort } from "../../shared/ports/git.ts";

/**
 * GitAdapter — driven adapter that shells out to the system `git` binary.
 *
 * Why spawn over libgit2: we need full parity with developer-visible CLI
 * behaviour (hooks, config, GPG, signing, signed pushes), and we ship to
 * Bun + Node where libgit2 bindings are flaky. Spawn args are passed as an
 * array — never shell-interpolated — which is cross-platform safe.
 *
 * Constitution VIII: this adapter REFUSES `push --force` at the boundary.
 * Force-pushes are throw-synchronously rejected because no calling code
 * should ever request one; a Result.err would imply the caller can recover.
 */
export class GitAdapter implements GitPort {
  constructor(private readonly cwd: string) {}

  async currentBranch(): Promise<Result<string, GitError>> {
    return this.runStdout(["rev-parse", "--abbrev-ref", "HEAD"]);
  }

  async isDirty(): Promise<Result<boolean, GitError>> {
    const r = await this.runStdout(["status", "--porcelain"]);
    if (!r.ok) return r;
    return ok(r.value.length > 0);
  }

  async stagedFiles(): Promise<Result<readonly string[], GitError>> {
    const r = await this.runStdout(["diff", "--name-only", "--cached"]);
    if (!r.ok) return r;
    const files = r.value.length === 0 ? [] : r.value.split("\n");
    return ok(Object.freeze(files));
  }

  async hash(ref: string): Promise<Result<string, GitError>> {
    return this.runStdout(["rev-parse", "--verify", `${ref}^{commit}`]);
  }

  async commit(
    message: string,
    opts?: { allowEmpty?: boolean },
  ): Promise<Result<string, GitError>> {
    const args = ["commit", "-m", message];
    if (opts?.allowEmpty === true) args.push("--allow-empty");
    const c = await this.runStdout(args);
    if (!c.ok) return c;
    return this.hash("HEAD");
  }

  async push(
    remote: string,
    branch: string,
    opts?: Readonly<PushOptions>,
  ): Promise<Result<void, GitError>> {
    refuseForcePush(opts);
    const r = await this.runStdout(["push", remote, branch]);
    if (!r.ok) return r;
    return ok(undefined);
  }

  async diff(ref?: string): Promise<Result<string, GitError>> {
    const args = ref === undefined ? ["diff"] : ["diff", ref];
    return this.runStdout(args);
  }

  async worktreeRoot(): Promise<Result<string, GitError>> {
    return this.runStdout(["rev-parse", "--show-toplevel"]);
  }

  private runStdout(args: readonly string[]): Promise<Result<string, GitError>> {
    return new Promise((resolve) => {
      const child = spawn("git", [...args], { cwd: this.cwd });
      let stdout = "";
      let stderr = "";
      child.stdout.on("data", (d: Buffer) => {
        stdout += d.toString("utf8");
      });
      child.stderr.on("data", (d: Buffer) => {
        stderr += d.toString("utf8");
      });
      child.on("error", (e) => {
        resolve(err(new GitError(`git spawn failed: ${e.message}`, false)));
      });
      child.on("close", (code) => {
        if (code === 0) {
          resolve(ok(stdout.replace(/\n+$/, "")));
        } else {
          const msg = (stderr || stdout || `git ${args.join(" ")} exited ${code}`).trim();
          resolve(err(new GitError(msg, isRetryable(stderr))));
        }
      });
    });
  }
}

interface PushOptions {
  readonly force?: boolean;
  readonly forceWithLease?: boolean;
}

const refuseForcePush = (opts?: Readonly<PushOptions>): void => {
  if (opts === undefined) return;
  if (opts.force === true || opts.forceWithLease === true) {
    throw new Error("GitAdapter refuses force-push at the boundary (Constitution VIII)");
  }
};

const isRetryable = (stderr: string): boolean => {
  const s = stderr.toLowerCase();
  return (
    s.includes("could not resolve host") ||
    s.includes("connection refused") ||
    s.includes("timed out") ||
    s.includes("temporary failure")
  );
};
