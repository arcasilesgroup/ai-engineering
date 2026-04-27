import { afterEach, beforeEach, describe, expect, test } from "bun:test";
import { spawnSync } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { isErr, isOk } from "../../../shared/kernel/result.ts";
import { GitError } from "../../../shared/ports/git.ts";
import { GitAdapter } from "../git.ts";

const gitOnPath = (() => {
  const r = spawnSync("git", ["--version"]);
  return r.status === 0;
})();

const dscribe = gitOnPath ? describe : describe.skip;

let repo = "";
let adapter: GitAdapter;

const run = (cwd: string, ...args: string[]): string => {
  const r = spawnSync("git", args, { cwd, encoding: "utf8" });
  if (r.status !== 0) {
    throw new Error(`git ${args.join(" ")} failed: ${r.stderr}\nstdout: ${r.stdout}`);
  }
  return r.stdout.trim();
};

const initRepo = (path: string): void => {
  run(path, "init", "--quiet", "--initial-branch=main");
  run(path, "config", "user.email", "test@example.com");
  run(path, "config", "user.name", "Test User");
  run(path, "config", "commit.gpgsign", "false");
};

beforeEach(() => {
  if (!gitOnPath) return;
  repo = mkdtempSync(join(tmpdir(), "ai-eng-git-"));
  initRepo(repo);
  adapter = new GitAdapter(repo);
});

afterEach(() => {
  if (!gitOnPath) return;
  rmSync(repo, { recursive: true, force: true });
});

dscribe("GitAdapter — currentBranch", () => {
  test("returns the initial branch name on a fresh repo", async () => {
    // Need at least one commit before HEAD points at a branch ref.
    writeFileSync(join(repo, "README.md"), "hello");
    run(repo, "add", "README.md");
    run(repo, "commit", "-m", "init", "--quiet");

    const r = await adapter.currentBranch();
    expect(isOk(r)).toBe(true);
    if (isOk(r)) expect(r.value).toBe("main");
  });

  test("reflects checkout to a feature branch", async () => {
    writeFileSync(join(repo, "f.txt"), "x");
    run(repo, "add", "f.txt");
    run(repo, "commit", "-m", "init", "--quiet");
    run(repo, "checkout", "-b", "feature/foo", "--quiet");

    const r = await adapter.currentBranch();
    if (isOk(r)) expect(r.value).toBe("feature/foo");
  });
});

dscribe("GitAdapter — isDirty", () => {
  test("clean repo returns false", async () => {
    writeFileSync(join(repo, "a.txt"), "x");
    run(repo, "add", "a.txt");
    run(repo, "commit", "-m", "init", "--quiet");

    const r = await adapter.isDirty();
    if (isOk(r)) expect(r.value).toBe(false);
  });

  test("dirty workdir returns true", async () => {
    writeFileSync(join(repo, "a.txt"), "x");
    run(repo, "add", "a.txt");
    run(repo, "commit", "-m", "init", "--quiet");

    writeFileSync(join(repo, "a.txt"), "y");
    const r = await adapter.isDirty();
    if (isOk(r)) expect(r.value).toBe(true);
  });

  test("untracked file makes it dirty", async () => {
    writeFileSync(join(repo, "a.txt"), "x");
    run(repo, "add", "a.txt");
    run(repo, "commit", "-m", "init", "--quiet");

    writeFileSync(join(repo, "new.txt"), "z");
    const r = await adapter.isDirty();
    if (isOk(r)) expect(r.value).toBe(true);
  });
});

dscribe("GitAdapter — stagedFiles", () => {
  test("empty when nothing is staged", async () => {
    writeFileSync(join(repo, "a.txt"), "x");
    run(repo, "add", "a.txt");
    run(repo, "commit", "-m", "init", "--quiet");

    const r = await adapter.stagedFiles();
    if (isOk(r)) expect(r.value).toEqual([]);
  });

  test("lists staged files", async () => {
    writeFileSync(join(repo, "a.txt"), "x");
    writeFileSync(join(repo, "b.txt"), "y");
    run(repo, "add", "a.txt");
    run(repo, "add", "b.txt");

    const r = await adapter.stagedFiles();
    if (isOk(r)) {
      const sorted = [...r.value].sort();
      expect(sorted).toEqual(["a.txt", "b.txt"]);
    }
  });
});

dscribe("GitAdapter — hash", () => {
  test("resolves HEAD to a 40-char SHA", async () => {
    writeFileSync(join(repo, "a.txt"), "x");
    run(repo, "add", "a.txt");
    run(repo, "commit", "-m", "init", "--quiet");

    const r = await adapter.hash("HEAD");
    if (isOk(r)) {
      expect(r.value).toMatch(/^[0-9a-f]{40}$/);
      const expected = run(repo, "rev-parse", "HEAD");
      expect(r.value).toBe(expected);
    }
  });

  test("rejects an unknown ref with GitError", async () => {
    writeFileSync(join(repo, "a.txt"), "x");
    run(repo, "add", "a.txt");
    run(repo, "commit", "-m", "init", "--quiet");

    const r = await adapter.hash("nope-not-a-ref");
    expect(isErr(r)).toBe(true);
    if (isErr(r)) expect(r.error).toBeInstanceOf(GitError);
  });
});

dscribe("GitAdapter — commit", () => {
  test("creates a commit and returns the new SHA", async () => {
    writeFileSync(join(repo, "a.txt"), "x");
    run(repo, "add", "a.txt");

    const r = await adapter.commit("feat: first");
    expect(isOk(r)).toBe(true);
    if (isOk(r)) {
      expect(r.value).toMatch(/^[0-9a-f]{40}$/);
      const head = run(repo, "rev-parse", "HEAD");
      expect(r.value).toBe(head);
    }
  });

  test("refuses an empty commit by default", async () => {
    writeFileSync(join(repo, "a.txt"), "x");
    run(repo, "add", "a.txt");
    run(repo, "commit", "-m", "init", "--quiet");

    const r = await adapter.commit("noop");
    expect(isErr(r)).toBe(true);
  });

  test("allows an empty commit with allowEmpty", async () => {
    writeFileSync(join(repo, "a.txt"), "x");
    run(repo, "add", "a.txt");
    run(repo, "commit", "-m", "init", "--quiet");

    const r = await adapter.commit("ci: trigger", { allowEmpty: true });
    expect(isOk(r)).toBe(true);
  });
});

dscribe("GitAdapter — push (force-push refusal)", () => {
  test("refuses force-push at the boundary (synchronous throw)", () => {
    expect(() => adapter.push("origin", "main", { force: true } as never)).toThrow();
  });

  test("returns GitError when no remote is configured", async () => {
    writeFileSync(join(repo, "a.txt"), "x");
    run(repo, "add", "a.txt");
    run(repo, "commit", "-m", "init", "--quiet");

    const r = await adapter.push("origin", "main");
    expect(isErr(r)).toBe(true);
    if (isErr(r)) expect(r.error).toBeInstanceOf(GitError);
  });

  test("succeeds when pushing to a local bare remote", async () => {
    const bare = mkdtempSync(join(tmpdir(), "ai-eng-bare-"));
    try {
      run(bare, "init", "--bare", "--quiet", "--initial-branch=main");
      writeFileSync(join(repo, "a.txt"), "x");
      run(repo, "add", "a.txt");
      run(repo, "commit", "-m", "init", "--quiet");
      run(repo, "remote", "add", "origin", bare);

      const r = await adapter.push("origin", "main");
      expect(isOk(r)).toBe(true);
    } finally {
      rmSync(bare, { recursive: true, force: true });
    }
  });
});

dscribe("GitAdapter — diff", () => {
  test("returns empty diff for a clean repo", async () => {
    writeFileSync(join(repo, "a.txt"), "x");
    run(repo, "add", "a.txt");
    run(repo, "commit", "-m", "init", "--quiet");

    const r = await adapter.diff();
    if (isOk(r)) expect(r.value).toBe("");
  });

  test("returns a unified diff for unstaged changes", async () => {
    writeFileSync(join(repo, "a.txt"), "alpha\n");
    run(repo, "add", "a.txt");
    run(repo, "commit", "-m", "init", "--quiet");

    writeFileSync(join(repo, "a.txt"), "beta\n");
    const r = await adapter.diff();
    if (isOk(r)) {
      expect(r.value).toContain("a.txt");
      expect(r.value).toContain("-alpha");
      expect(r.value).toContain("+beta");
    }
  });

  test("with ref returns diff against that ref", async () => {
    writeFileSync(join(repo, "a.txt"), "alpha\n");
    run(repo, "add", "a.txt");
    run(repo, "commit", "-m", "init", "--quiet");
    const first = run(repo, "rev-parse", "HEAD");

    writeFileSync(join(repo, "a.txt"), "beta\n");
    run(repo, "add", "a.txt");
    run(repo, "commit", "-m", "second", "--quiet");

    const r = await adapter.diff(first);
    if (isOk(r)) {
      expect(r.value).toContain("-alpha");
      expect(r.value).toContain("+beta");
    }
  });
});

dscribe("GitAdapter — worktreeRoot", () => {
  test("returns the repo's worktree root", async () => {
    writeFileSync(join(repo, "a.txt"), "x");
    run(repo, "add", "a.txt");
    run(repo, "commit", "-m", "init", "--quiet");

    const r = await adapter.worktreeRoot();
    expect(isOk(r)).toBe(true);
    if (isOk(r)) {
      // macOS prepends /private to /var/folders symlinks; compare via realpath
      const expected = run(repo, "rev-parse", "--show-toplevel");
      expect(r.value).toBe(expected);
    }
  });

  test("returns GitError outside a repo", async () => {
    const outside = mkdtempSync(join(tmpdir(), "ai-eng-not-repo-"));
    try {
      const off = new GitAdapter(outside);
      const r = await off.worktreeRoot();
      expect(isErr(r)).toBe(true);
      if (isErr(r)) expect(r.error).toBeInstanceOf(GitError);
    } finally {
      rmSync(outside, { recursive: true, force: true });
    }
  });
});
