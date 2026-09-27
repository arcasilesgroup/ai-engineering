// tests/git-cleanup-cli.spec.ts — CLI contract of skills/ai-git-cleanup/scripts/analyze.mjs
// (ai-git-cleanup test plan, cli layer): exit 0 with one JSON document on stdout, an optional
// repo path that defaults to the current directory, and best-effort git plumbing. Fixtures are
// real temp repositories whose only remotes are local paths — nothing here touches a network.
// GIT_CONFIG_GLOBAL points at an empty file so the machine's ~/.gitconfig (hooks, signing,
// identity) cannot decide what any child git does.

import { afterAll, describe, expect, test } from "bun:test";
import { spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const script = join(import.meta.dir, "..", "skills", "ai-git-cleanup", "scripts", "analyze.mjs");
const sandboxRoot = mkdtempSync(join(tmpdir(), "ai-eng-git-cleanup-cli-"));
const emptyGitConfig = join(sandboxRoot, "empty-gitconfig");
writeFileSync(emptyGitConfig, "");

// The script runs its own git commands, so the sandbox rides on the environment it
// inherits, and GIT_TERMINAL_PROMPT keeps a broken remote from hanging the suite.
const childEnv: NodeJS.ProcessEnv = {
  ...process.env,
  GIT_CONFIG_GLOBAL: emptyGitConfig,
  GIT_TERMINAL_PROMPT: "0",
};

interface AnalyzeRun {
  status: number;
  stdout: string;
  stderr: string;
}

afterAll(() => {
  rmSync(sandboxRoot, { recursive: true, force: true });
});

function git(args: string[], cwd: string): void {
  const done = spawnSync("git", args, { cwd, encoding: "utf8", env: childEnv });
  if (done.status !== 0) throw new Error(`git ${args.join(" ")} failed: ${done.stderr}`);
}

function runAnalyze(args: string[], cwd: string): AnalyzeRun {
  const done = spawnSync(process.execPath, [script, ...args], { cwd, encoding: "utf8", env: childEnv });
  return { status: done.status ?? 1, stdout: done.stdout ?? "", stderr: done.stderr ?? "" };
}

function fixtureRepo(name: string, branch: string): string {
  const root = join(sandboxRoot, name);
  mkdirSync(root, { recursive: true });
  git(["init", "-q", "-b", branch], root);
  git(["config", "user.name", "Ada Lovelace"], root);
  git(["config", "user.email", "ada@example.com"], root);
  git(["config", "commit.gpgsign", "false"], root);
  writeFileSync(join(root, "notes.md"), `# ${name}\n`);
  git(["add", "-A"], root);
  git(["commit", "-q", "-m", "fixture base"], root);
  return root;
}

describe("analyze.mjs CLI contract", () => {
  test("an explicit repo path exits 0 with a single JSON document on stdout", () => {
    const repo = fixtureRepo("explicit-path", "trunk");
    const analysis = runAnalyze([repo], sandboxRoot);
    expect(analysis.status).toBe(0);
    // JSON.parse doubles as the "single document" check: stray output or a second
    // document on stdout fails to parse.
    const report = JSON.parse(analysis.stdout) as Record<string, unknown>;
    expect(report).toBeObject();
    // The document describes this repository: its only branch is named in it.
    expect(analysis.stdout).toContain("trunk");
  });

  test("without an argument the current working directory is analyzed", () => {
    const repo = fixtureRepo("default-cwd", "trunk");
    const explicit = runAnalyze([repo], sandboxRoot);
    const fromCwd = runAnalyze([], repo);
    expect(explicit.status).toBe(0);
    expect(fromCwd.status).toBe(0);
    // Same repository either way: passing the path and standing in the directory agree.
    expect(JSON.parse(fromCwd.stdout)).toEqual(JSON.parse(explicit.stdout));
  });

  test("with no origin the fetch step is skipped instead of failing the run", () => {
    const repo = fixtureRepo("no-origin", "trunk");
    const analysis = runAnalyze([repo], sandboxRoot);
    expect(analysis.status).toBe(0);
    // Parsing the whole stdout doubles as the single-JSON-document check: stray output
    // or a second document fails to parse. No remote exists, so no remote-derived state
    // could be stale and fetchStatus must be exactly `ok`.
    const report = JSON.parse(analysis.stdout) as Record<string, unknown>;
    expect(report).toBeObject();
    expect(report.fetchStatus).toBe("ok");
  });

  test("the default branch comes from origin/HEAD when it exists", () => {
    const origin = join(sandboxRoot, "trunk-origin.git");
    git(["init", "-q", "-b", "trunk", "--bare", origin], sandboxRoot);
    const repo = fixtureRepo("origin-head", "trunk");
    git(["remote", "add", "origin", origin], repo);
    git(["push", "-q", "-u", "origin", "HEAD"], repo);
    git(["symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/trunk"], repo);
    const analysis = runAnalyze([repo], sandboxRoot);
    expect(analysis.status).toBe(0);
    expect(JSON.parse(analysis.stdout)).toBeObject();
    expect(analysis.stdout).toContain("trunk");
  });

  test("a failing fetch and a missing origin/HEAD fall back without corrupting stdout", () => {
    const repo = fixtureRepo("broken-origin", "trunk");
    // The origin path does not exist: git fetch fails loudly on stderr, and origin/HEAD
    // never comes to exist, so the default-branch fallback is the only path left.
    git(["remote", "add", "origin", join(sandboxRoot, "missing-origin.git")], repo);
    const analysis = runAnalyze([repo], sandboxRoot);
    expect(analysis.status).toBe(0);
    // Parsing the whole stdout doubles as the single-JSON-document check: a corrupted
    // stdout would fail to parse here.
    const report = JSON.parse(analysis.stdout) as Record<string, unknown>;
    expect(report).toBeObject();
    expect(analysis.stdout).toContain("trunk");
    // The failure must surface as `failed: <first stderr line, trimmed>`. The exact line
    // comes from replaying the identical fetch against the identical fixture, so the
    // reason is pinned without hardcoding a machine-specific path into the test.
    const fetch = spawnSync("git", ["fetch", "--prune", "origin"], {
      cwd: repo,
      encoding: "utf8",
      env: childEnv,
    });
    expect(fetch.status).not.toBe(0);
    const firstStderrLine = (fetch.stderr ?? "")
      .split("\n")
      .map((line) => line.trim())
      .find((line) => line.length > 0);
    expect(firstStderrLine).toBeString();
    expect(report.fetchStatus).toBe(`failed: ${firstStderrLine}`);
    // Conservative classification intact under a broken remote: the fallback derivation
    // still runs and no delete candidate is fabricated from stale remote state.
    expect(report.deleteCandidates).toEqual([]);
  });

  test("a path outside any git repository exits non-zero with a repo error", () => {
    const plainDirectory = join(sandboxRoot, "plain-directory");
    mkdirSync(plainDirectory);
    const analysis = runAnalyze([plainDirectory], sandboxRoot);
    expect(analysis.status).not.toBe(0);
    expect(analysis.stderr).toMatch(/not a git repo/i);
  });
});

// Checkpoint 2 (ai-git-cleanup-v2): subprocess-level proof of the post-cleanup sync
// plan against real upstream states. Every remote is a local path, so an "upstream"
// here is just another checkout of the same sandbox — no network anywhere.

function bareOrigin(name: string): string {
  const origin = join(sandboxRoot, `${name}.git`);
  git(["init", "-q", "-b", "trunk", "--bare", origin], sandboxRoot);
  return origin;
}

function cloneOf(origin: string, name: string): string {
  const clone = join(sandboxRoot, name);
  git(["clone", "-q", origin, clone], sandboxRoot);
  git(["config", "user.name", "Ada Lovelace"], clone);
  git(["config", "user.email", "ada@example.com"], clone);
  git(["config", "commit.gpgsign", "false"], clone);
  return clone;
}

function commitOn(disk: string, file: string, content: string, message: string): void {
  writeFileSync(join(disk, file), content);
  git(["add", "-A"], disk);
  git(["commit", "-q", "-m", message], disk);
}

// Fixture precondition, asserted by the tests themselves: the fixture must really be
// in the named upstream state or the assertion below proves nothing (R3).
function aheadBehind(repo: string): { ahead: number; behind: number } {
  const counts = spawnSync(
    "git",
    ["rev-list", "--left-right", "--count", "trunk...origin/trunk"],
    { cwd: repo, encoding: "utf8", env: childEnv },
  );
  if (counts.status !== 0) throw new Error(`upstream count failed: ${counts.stderr}`);
  const [ahead, behind] = counts.stdout.trim().split("\t").map(Number);
  return { ahead, behind };
}

// Several tests build the same state, so every fixture call needs its own directory:
// re-running git init plus commit in an existing repo finds nothing to commit and fails.
let fixtureSeq = 0;
function nextBase(name: string): string {
  fixtureSeq += 1;
  return `postsync-${name}-${fixtureSeq}`;
}

// A default branch whose upstream is one commit ahead: local trunk is behind 1.
function behindFixture(): string {
  const base = nextBase("behind");
  const repo = fixtureRepo(base, "trunk");
  const origin = bareOrigin(base);
  git(["remote", "add", "origin", origin], repo);
  git(["push", "-q", "-u", "origin", "HEAD"], repo);
  const other = cloneOf(origin, `${base}-other`);
  commitOn(other, "remote.md", "# advanced remotely\n", "remote-only commit");
  git(["push", "-q", "origin", "HEAD"], other);
  // The precondition reads origin/trunk, so the tracking ref must already be fresh
  // here; analyze would fetch anyway, but the fixture proves its own state first.
  git(["fetch", "-q", "origin"], repo);
  return repo;
}

// Local trunk and its upstream at the same commit: level.
function levelFixture(): string {
  const base = nextBase("level");
  const repo = fixtureRepo(base, "trunk");
  const origin = bareOrigin(base);
  git(["remote", "add", "origin", origin], repo);
  git(["push", "-q", "-u", "origin", "HEAD"], repo);
  return repo;
}

// A local commit never pushed: trunk ahead 1.
function aheadFixture(): string {
  const base = nextBase("ahead");
  const repo = fixtureRepo(base, "trunk");
  const origin = bareOrigin(base);
  git(["remote", "add", "origin", origin], repo);
  git(["push", "-q", "-u", "origin", "HEAD"], repo);
  commitOn(repo, "local.md", "# local only\n", "local-only commit");
  return repo;
}

// A clean linked worktree on a branch that is already an ancestor of trunk: the
// branch queues as SAFE_TO_DELETE and its worktree as stale (L10: the branch is
// created with `git branch` while trunk stays checked out, never checked out twice).
function staleWorktreeFixture(): string {
  const base = nextBase("stale-wt");
  const repo = fixtureRepo(base, "trunk");
  git(["branch", "feature/done"], repo);
  git(["worktree", "add", "-q", join(sandboxRoot, `${base}-linked`), "feature/done"], repo);
  return repo;
}

// Every string in the document that looks like a git command — the exact strings a
// consumer would execute, wherever in the JSON they are nested.
function commandStrings(value: unknown): string[] {
  if (typeof value === "string") return value.includes("git ") ? [value] : [];
  if (Array.isArray(value)) return value.flatMap(commandStrings);
  if (value && typeof value === "object") return Object.values(value).flatMap(commandStrings);
  return [];
}

function analyzeFixture(repo: string): Record<string, unknown> {
  const analysis = runAnalyze([repo], sandboxRoot);
  expect(analysis.status).toBe(0);
  return JSON.parse(analysis.stdout) as Record<string, unknown>;
}

describe("analyze.mjs CLI post-cleanup sync plan", () => {
  test("behind default: the plan includes git pull --ff-only for the default branch", () => {
    const repo = behindFixture();
    expect(aheadBehind(repo)).toEqual({ ahead: 0, behind: 1 });
    const report = analyzeFixture(repo);
    expect(report.defaultBranch).toBe("trunk");
    const pulls = commandStrings(report).filter((command) => command.includes("pull --ff-only"));
    expect(pulls).toHaveLength(1);
    expect(pulls[0]).toContain("git pull --ff-only");
    // The pull names its upstream: the plan tells the gate what it syncs from.
    expect(JSON.stringify(report)).toContain("origin/trunk");
  });

  test("level default: no pull command is emitted", () => {
    const repo = levelFixture();
    expect(aheadBehind(repo)).toEqual({ ahead: 0, behind: 0 });
    const report = analyzeFixture(repo);
    expect(commandStrings(report).filter((command) => command.includes("pull"))).toEqual([]);
  });

  test("ahead default: the ahead count is reported and no push is emitted", () => {
    const repo = aheadFixture();
    expect(aheadBehind(repo)).toEqual({ ahead: 1, behind: 0 });
    const report = analyzeFixture(repo);
    const postSync = report.postSync;
    expect(postSync).toBeObject();
    // Report-only marker: the ahead count travels in the plan, never a push command.
    expect(JSON.stringify(postSync)).toMatch(/"ahead"\s*:\s*1/);
    expect(commandStrings(report).filter((command) => command.includes("push"))).toEqual([]);
  });

  test("a queued worktree removal adds git worktree prune", () => {
    const repo = staleWorktreeFixture();
    const report = analyzeFixture(repo);
    // Fixture precondition: the worktree really is queued for removal.
    expect(commandStrings(report).filter((command) => command.includes("worktree remove"))).toHaveLength(1);
    const prunes = commandStrings(report).filter((command) => command.includes("worktree prune"));
    expect(prunes).toHaveLength(1);
    expect(prunes[0]).toContain("git worktree prune");
  });

  test("no worktree removal: no prune command", () => {
    const repo = levelFixture();
    const report = analyzeFixture(repo);
    // Prove the "none removed" configuration holds, or the absence check is vacuous.
    expect(commandStrings(report).filter((command) => command.includes("worktree remove"))).toEqual([]);
    expect(commandStrings(report).filter((command) => command.includes("prune"))).toEqual([]);
  });

  test("every emitted git command in the whole plan is push-free", () => {
    // The exact configuration where a push could hide: local work ahead of upstream
    // with real queued deletions in the same document (R3).
    const repo = aheadFixture();
    git(["branch", "feature/merged"], repo);
    git(["worktree", "add", "-q", join(sandboxRoot, "postsync-scan-linked"), "feature/merged"], repo);
    const report = analyzeFixture(repo);
    const commands = commandStrings(report);
    expect(commands.length).toBeGreaterThan(0);
    expect(commands.filter((command) => /push/.test(command))).toEqual([]);
  });

  test("fetchStatus and postSync coexist in one document", () => {
    const repo = behindFixture();
    const report = analyzeFixture(repo);
    expect(report.fetchStatus).toBe("ok");
    expect(report.postSync).toBeObject();
    expect(JSON.stringify(report.postSync)).toContain("git pull --ff-only");
  });

  test("stdout stays a single JSON document when postSync is present", () => {
    const repo = staleWorktreeFixture();
    const analysis = runAnalyze([repo], sandboxRoot);
    expect(analysis.status).toBe(0);
    // JSON.parse of the whole stdout doubles as the single-document check: stray
    // output or a second document fails to parse.
    const report = JSON.parse(analysis.stdout) as Record<string, unknown>;
    expect(report).toBeObject();
    expect(report.postSync).toBeObject();
  });
});
