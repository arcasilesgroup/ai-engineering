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
    expect(JSON.parse(analysis.stdout)).toBeObject();
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
    expect(JSON.parse(analysis.stdout)).toBeObject();
    expect(analysis.stdout).toContain("trunk");
  });

  test("a path outside any git repository exits non-zero with a repo error", () => {
    const plainDirectory = join(sandboxRoot, "plain-directory");
    mkdirSync(plainDirectory);
    const analysis = runAnalyze([plainDirectory], sandboxRoot);
    expect(analysis.status).not.toBe(0);
    expect(analysis.stderr).toMatch(/not a git repo/i);
  });
});
