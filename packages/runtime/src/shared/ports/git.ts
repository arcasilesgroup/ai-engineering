import type { Result } from "../kernel/result.ts";

/**
 * GitPort — driven port for Git operations.
 *
 * The domain never spawns `git` directly. All Git access goes through this
 * port so we can swap shell-driven CLI, libgit2 bindings, or HTTP-backed
 * remote-attestation Git proxies (regulated tier).
 *
 * Adapters MUST refuse `push --force` at the boundary. Force-pushing to any
 * branch is a Constitution-VIII violation and the adapter throws synchronously
 * (not a Result.err) because the caller should never have requested it.
 */
export interface GitPort {
  /** Returns the name of the currently checked-out branch. */
  currentBranch(): Promise<Result<string, GitError>>;

  /** True if the working tree has uncommitted changes (staged or unstaged). */
  isDirty(): Promise<Result<boolean, GitError>>;

  /** Files currently in the index, relative to the repo root. */
  stagedFiles(): Promise<Result<readonly string[], GitError>>;

  /** Resolves a ref (branch, tag, "HEAD", short-SHA) to its full SHA. */
  hash(ref: string): Promise<Result<string, GitError>>;

  /** Creates a commit from the current index. Returns the new SHA. */
  commit(message: string, opts?: { allowEmpty?: boolean }): Promise<Result<string, GitError>>;

  /** Pushes a branch to a remote. Force-push is refused at the boundary. */
  push(remote: string, branch: string): Promise<Result<void, GitError>>;

  /** Returns a unified diff. With no ref, diffs the working tree vs HEAD. */
  diff(ref?: string): Promise<Result<string, GitError>>;

  /** The absolute path of the repo's worktree root. */
  worktreeRoot(): Promise<Result<string, GitError>>;
}

export class GitError extends Error {
  constructor(
    message: string,
    public readonly retryable: boolean = false,
  ) {
    super(message);
    this.name = "GitError";
  }
}
