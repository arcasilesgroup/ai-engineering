import { describe, expect, test } from "bun:test";
import { spawnSync } from "node:child_process";
import { writeFileSync } from "node:fs";
import { join } from "node:path";

import { cleanup } from "../cleanup.ts";
import { capture, withTmpCwd } from "./_helpers.ts";

const sh = (cwd: string, ...args: string[]): void => {
  const r = spawnSync(args[0] ?? "", args.slice(1), {
    cwd,
    stdio: "ignore",
    env: {
      ...process.env,
      GIT_AUTHOR_NAME: "t",
      GIT_AUTHOR_EMAIL: "t@t",
      GIT_COMMITTER_NAME: "t",
      GIT_COMMITTER_EMAIL: "t@t",
    },
  });
  if (r.status !== 0) {
    throw new Error(`command failed: ${args.join(" ")}`);
  }
};

const initRepoOnMain = (root: string): void => {
  sh(root, "git", "init", "-b", "main");
  sh(root, "git", "config", "user.email", "test@test");
  sh(root, "git", "config", "user.name", "Test");
  sh(root, "git", "config", "commit.gpgsign", "false");
  writeFileSync(join(root, "README.md"), "# tmp\n", "utf8");
  sh(root, "git", "add", "README.md");
  sh(root, "git", "commit", "-m", "initial");
};

describe("cleanup — happy path", () => {
  test("initialised repo on main with no merged branches returns 0", async () => {
    await withTmpCwd("ai-eng-cleanup-clean-", async (root) => {
      initRepoOnMain(root);
      const result = await capture(() => cleanup([]));
      expect(result.exitCode).toBe(0);
      expect(result.stdout).toMatch(/fetched \+ pruned|nothing to tidy/i);
    });
  });

  test("repo with a merged feature branch lists it as a candidate", async () => {
    await withTmpCwd("ai-eng-cleanup-merged-", async (root) => {
      initRepoOnMain(root);
      sh(root, "git", "checkout", "-b", "feature/done");
      writeFileSync(join(root, "f.txt"), "ok\n", "utf8");
      sh(root, "git", "add", "f.txt");
      sh(root, "git", "commit", "-m", "feature commit");
      sh(root, "git", "checkout", "main");
      sh(root, "git", "merge", "--no-ff", "feature/done", "-m", "merge");
      const result = await capture(() => cleanup([]));
      expect(result.exitCode).toBe(0);
      expect(result.stdout).toMatch(/feature\/done/);
      expect(result.stdout).toMatch(/dry-run/i);
    });
  });

  test("--json emits structured payload", async () => {
    await withTmpCwd("ai-eng-cleanup-json-", async (root) => {
      initRepoOnMain(root);
      const result = await capture(() => cleanup(["--json"]));
      expect(result.exitCode).toBe(0);
      const lines = result.stdout
        .split("\n")
        .filter((l) => l.length > 0 && !l.startsWith("[ai-eng]"));
      const parsed = JSON.parse(lines.join("\n"));
      expect(parsed).toHaveProperty("base");
      expect(parsed).toHaveProperty("merged");
    });
  });
});

describe("cleanup — error paths", () => {
  test("non-git directory returns exit 1", async () => {
    await withTmpCwd("ai-eng-cleanup-nogit-", async () => {
      const result = await capture(() => cleanup([]));
      expect(result.exitCode).toBe(1);
      expect(result.stderr).toMatch(/not a git repo/i);
    });
  });
});
