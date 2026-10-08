import { afterAll, describe, expect, test } from "bun:test";
import { spawnSync } from "node:child_process";
import {
  existsSync,
  mkdirSync,
  mkdtempSync,
  readdirSync,
  readFileSync,
  realpathSync,
  rmSync,
  statSync,
  writeFileSync,
} from "node:fs";
import { dirname, join } from "node:path";

const CLI = join(import.meta.dir, "..", "src", "cli.ts");
const root = mkdtempSync(join(import.meta.dir, ".worktree-lifecycle-"));
const emptyGitConfig = join(root, "empty-gitconfig");
writeFileSync(emptyGitConfig, "");
const childEnv: NodeJS.ProcessEnv = {
  ...process.env,
  GIT_CONFIG_GLOBAL: emptyGitConfig,
  GIT_CONFIG_SYSTEM: "/dev/null",
  GIT_TERMINAL_PROMPT: "0",
};

afterAll(() => rmSync(root, { recursive: true, force: true }));

interface Run {
  status: number;
  stdout: string;
  stderr: string;
}

function git(args: string[], cwd: string): string {
  const result = spawnSync("git", args, { cwd, encoding: "utf8", env: childEnv });
  if (result.status !== 0) {
    throw new Error(`git ${args.join(" ")} failed in ${cwd}: ${result.stderr}`);
  }
  return result.stdout;
}

function runList(cwd: string): Run {
  const result = spawnSync(process.execPath, [CLI, "worktree", "list"], {
    cwd,
    encoding: "utf8",
    env: childEnv,
  });
  return {
    status: result.status ?? 1,
    stdout: result.stdout ?? "",
    stderr: result.stderr ?? "",
  };
}

function initRepo(): string {
  const base = mkdtempSync(join(root, "repo-"));
  const repo = join(base, "primary");
  mkdirSync(repo);
  git(["init", "-q", "-b", "main"], repo);
  git(["config", "user.name", "Ada Lovelace"], repo);
  git(["config", "user.email", "ada@example.com"], repo);
  git(["config", "commit.gpgsign", "false"], repo);
  mkdirSync(join(repo, "src"));
  writeFileSync(join(repo, "README.md"), "# fixture\n");
  writeFileSync(join(repo, "src", "shared.ts"), "export const value = 1;\n");
  git(["add", "-A"], repo);
  git(["commit", "-q", "-m", "fixture base"], repo);
  return repo;
}

function worktreePath(repo: string, name: string): string {
  return join(`${repo}.worktrees`, name);
}

function addBranchWorktree(repo: string, name: string, branch = `feat/${name}`): string {
  const path = worktreePath(repo, name);
  mkdirSync(dirname(path), { recursive: true });
  git(["worktree", "add", "--quiet", "-b", branch, path, "refs/heads/main"], repo);
  return path;
}

function addDetachedWorktree(repo: string, name: string): string {
  const path = worktreePath(repo, name);
  mkdirSync(dirname(path), { recursive: true });
  git(["worktree", "add", "--quiet", "--detach", path, "refs/heads/main"], repo);
  return path;
}

function checkpointPath(worktree: string, slug: string): string {
  return join(worktree, ".ai-engineering", "workflow", "checkpoints", `${slug}.json`);
}

function lifecycle(phase: string): object {
  return {
    phase,
    plan_approval: phase === "awaiting-plan-approval" ? "pending" : "approved",
    app_review: phase === "awaiting-app-review" ? "pending" : "not-started",
    reviewed_main: null,
  };
}

function checkpointPlan(slug: string, phase: string, files: string[] = []): Record<string, unknown> {
  const gate = () => ({ status: "pending", attempts: 0, findings: [] });
  return {
    slug,
    checkpoints: [{
      id: 1,
      status: "pending",
      gates: { behavior: gate(), ui: gate(), review: gate() },
      files,
    }],
    lifecycle: lifecycle(phase),
  };
}

function writeCheckpoint(worktree: string, slug: string, value: object): string {
  const path = checkpointPath(worktree, slug);
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, `${JSON.stringify(value, null, 2)}\n`);
  return path;
}

function commitCheckpoint(worktree: string, path: string): void {
  git(["add", path], worktree);
  git(["commit", "-q", "-m", "add checkpoint"], worktree);
}

function repoSnapshot(repo: string, worktrees: string[], checkpointFiles: string[]): string {
  const contents = checkpointFiles.map((path) => {
    if (!existsSync(path)) return [path, "missing"];
    if (statSync(path).isDirectory()) return [path, "directory", ...readdirSync(path)];
    return [path, readFileSync(path, "utf8")];
  });
  return JSON.stringify({
    refs: git(["for-each-ref", "--format=%(refname) %(objectname)", "refs/heads"], repo),
    registrations: git(["worktree", "list", "--porcelain"], repo),
    statuses: [repo, ...worktrees].map((path) => [
      realpathSync(path),
      git(["status", "--porcelain", "--untracked-files=all"], path),
    ]),
    contents,
  });
}

describe("ai-eng worktree lifecycle (checkpoint 2)", () => {
  test("U5: list uses only Git-listed feature worktrees and each worktree's own checkpoint path", () => {
    const repo = initRepo();
    const alpha = addBranchWorktree(repo, "alpha");
    const beta = addBranchWorktree(repo, "beta");

    writeCheckpoint(repo, "alpha", checkpointPlan("alpha", "primary-only"));
    writeCheckpoint(repo, "ghost", checkpointPlan("ghost", "not-listed"));
    writeCheckpoint(alpha, "alpha", checkpointPlan("alpha", "implementation"));
    writeCheckpoint(beta, "beta", checkpointPlan("beta", "awaiting-plan-approval"));

    const result = runList(repo);
    expect(result.status).toBe(0);
    expect(result.stdout).toContain("alpha");
    expect(result.stdout).toContain(realpathSync(alpha));
    expect(result.stdout).toContain("implementation");
    expect(result.stdout).toContain("beta");
    expect(result.stdout).toContain(realpathSync(beta));
    expect(result.stdout).toContain("awaiting-plan-approval");
    expect(result.stdout).not.toContain("primary-only");
    expect(result.stdout).not.toContain("not-listed");
    expect(result.stdout).not.toContain("ghost");
  });

  test("U6: clean, dirty, detached and unclassified Git worktrees report their status and evidence read-only", () => {
    const repo = initRepo();
    const clean = addBranchWorktree(repo, "alpha");
    const dirty = addBranchWorktree(repo, "beta");
    const detached = addDetachedWorktree(repo, "gamma");
    const unclassified = addBranchWorktree(repo, "delta", "topic/other");
    writeFileSync(join(dirty, "README.md"), "# local edit\n");

    expect(git(["status", "--porcelain", "--untracked-files=all"], clean)).toBe("");
    expect(git(["status", "--porcelain", "--untracked-files=all"], dirty)).toContain("README.md");
    expect(git(["worktree", "list", "--porcelain"], repo)).toContain("detached");
    expect(git(["worktree", "list", "--porcelain"], repo)).toContain("refs/heads/topic/other");

    const before = repoSnapshot(repo, [clean, dirty, detached, unclassified], []);
    const result = runList(repo);
    const after = repoSnapshot(repo, [clean, dirty, detached, unclassified], []);

    expect(result.status).toBe(0);
    expect(result.stdout).toContain(realpathSync(clean));
    expect(result.stdout.toLowerCase()).toContain("clean");
    expect(result.stdout).toContain(realpathSync(dirty));
    expect(result.stdout.toLowerCase()).toContain("dirty");
    expect(result.stdout).toContain("README.md");
    expect(result.stdout).toContain(realpathSync(detached));
    expect(result.stdout.toLowerCase()).toContain("detached");
    expect(result.stdout).toContain(realpathSync(unclassified));
    expect(result.stdout).toContain("topic/other");
    expect(result.stdout.toLowerCase()).toContain("unclassified");
    expect(after).toBe(before);
  });

  test("U7: missing, unreadable, malformed and legacy lifecycle state stays visible as unknown", () => {
    const repo = initRepo();
    const missing = addBranchWorktree(repo, "missing");
    const unreadable = addBranchWorktree(repo, "unreadable");
    const malformed = addBranchWorktree(repo, "malformed");
    const legacy = addBranchWorktree(repo, "legacy");

    const unreadablePath = checkpointPath(unreadable, "unreadable");
    mkdirSync(unreadablePath, { recursive: true });
    const malformedPath = writeCheckpoint(malformed, "malformed", {
      lifecycle: { phase: "ready-to-merge", plan_approval: "approved", app_review: "approved", reviewed_main: "not-a-commit" },
    });
    writeFileSync(malformedPath, "{ invalid json\n");
    const legacyPlan = checkpointPlan("legacy", "implementation");
    delete legacyPlan.lifecycle;
    writeCheckpoint(legacy, "legacy", legacyPlan);

    const result = runList(repo);
    expect(result.status).toBe(0);
    for (const [slug, path] of [
      ["missing", missing],
      ["unreadable", unreadable],
      ["malformed", malformed],
      ["legacy", legacy],
    ]) {
      expect(result.stdout).toContain(slug);
      expect(result.stdout).toContain(realpathSync(path));
    }
    expect(result.stdout.toLowerCase()).toContain("unknown");
    expect(result.stdout.match(/unknown/gi)?.length ?? 0).toBeGreaterThanOrEqual(4);
    expect(result.stdout).not.toContain("ready-to-merge");
    expect(result.stdout).not.toContain("approved");
  });

  test("U9: likely-overlap evidence names Git status and each relevant checkpoint path without mutation", () => {
    const repo = initRepo();
    const alpha = addBranchWorktree(repo, "alpha");
    const beta = addBranchWorktree(repo, "beta");
    const plan = (slug: string) => checkpointPlan(slug, "implementation", ["src/shared.ts"]);
    const alphaCheckpoint = writeCheckpoint(alpha, "alpha", plan("alpha"));
    const betaCheckpoint = writeCheckpoint(beta, "beta", plan("beta"));
    commitCheckpoint(alpha, alphaCheckpoint);
    commitCheckpoint(beta, betaCheckpoint);
    writeFileSync(join(alpha, "src", "shared.ts"), "export const value = 2;\n");

    expect(git(["status", "--porcelain", "--untracked-files=all"], alpha)).toContain("src/shared.ts");
    const before = repoSnapshot(repo, [alpha, beta], [alphaCheckpoint, betaCheckpoint]);
    const result = runList(repo);
    const after = repoSnapshot(repo, [alpha, beta], [alphaCheckpoint, betaCheckpoint]);

    expect(result.status).toBe(0);
    expect(result.stdout.toLowerCase()).toContain("overlap");
    expect(result.stdout).toContain("src/shared.ts");
    expect(result.stdout).toContain(alphaCheckpoint);
    expect(result.stdout).toContain(betaCheckpoint);
    expect(after).toBe(before);
  });
});
