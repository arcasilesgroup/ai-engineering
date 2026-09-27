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

  test("a failing fetch: fetchStatus surfaces the failure and classification stays conservative", () => {
    const repo = fixtureRepo("broken-origin-conservative", "trunk");
    git(["remote", "add", "origin", join(sandboxRoot, "missing-origin.git")], repo);
    const doc = analyzeDoc(["--all", repo], sandboxRoot);
    // fetchStatus still surfaces the failure inside the one parseable document.
    expect(String(doc.fetchStatus)).toContain("failed: ");
    // Conservative under a broken remote: nothing fabricated into the batch, and no
    // delete command anywhere in the document.
    expect(doc.batch).toEqual([]);
    expect(commandStrings(doc).filter((command) => /branch -[dD]/.test(command))).toEqual([]);
  });
});

// Checkpoint 1 (ai-git-cleanup-v3): mode flags, migration plan pinned to the default
// branch, and classification on real fixtures — all subprocess-level. Every remote is
// a local path, so nothing here touches a network.

// Every string in the document that looks like a git command — the exact strings a
// consumer would execute, wherever in the JSON they are nested.
function commandStrings(value: unknown): string[] {
  if (typeof value === "string") return value.includes("git ") ? [value] : [];
  if (Array.isArray(value)) return value.flatMap(commandStrings);
  if (value && typeof value === "object") return Object.values(value).flatMap(commandStrings);
  return [];
}

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

let fixtureSeq = 0;
function nextBase(name: string): string {
  fixtureSeq += 1;
  return `cli-${name}-${fixtureSeq}`;
}

// A repo with a local origin: trunk pushed, origin/HEAD set, HEAD moved to a feature
// branch so current !== default — the configuration the R4 pull pin requires.
function currentNotDefaultFixture(name: string): string {
  const base = nextBase(name);
  const repo = fixtureRepo(base, "trunk");
  const origin = bareOrigin(base);
  git(["remote", "add", "origin", origin], repo);
  git(["push", "-q", "-u", "origin", "HEAD"], repo);
  git(["symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/trunk"], repo);
  git(["switch", "-q", "-c", "feature/work"], repo);
  return repo;
}

function analyzeDoc(args: string[], cwd: string): Record<string, unknown> {
  const run = runAnalyze(args, cwd);
  expect(run.status).toBe(0);
  // JSON.parse of the whole stdout doubles as the one-JSON-document check.
  return JSON.parse(run.stdout) as Record<string, unknown>;
}

describe("analyze.mjs mode flags", () => {
  test("--sync emits only the migration plan: classification, batch and report sections absent", () => {
    const repo = currentNotDefaultFixture("mode-sync");
    const doc = analyzeDoc(["--sync", repo], sandboxRoot);
    expect(doc).toBeObject();
    // Own-property checks, not truthiness: an empty-but-present section must not pass
    // as absent, and a missing section must not pass as present (R2).
    expect(doc).toHaveProperty("migration");
    expect("classification" in doc).toBe(false);
    expect("batch" in doc).toBe(false);
    expect("report" in doc).toBe(false);
    // No delete command of any kind leaks into the sync-only document.
    expect(commandStrings(doc).filter((command) => /branch -[dD]/.test(command))).toEqual([]);
  });

  test("--branches emits classification, batch and report with migration, stash and pull sections absent", () => {
    const repo = currentNotDefaultFixture("mode-branches");
    const doc = analyzeDoc(["--branches", repo], sandboxRoot);
    expect(doc).toBeObject();
    expect("migration" in doc).toBe(false);
    expect(doc).toHaveProperty("classification");
    expect(doc).toHaveProperty("batch");
    expect(doc).toHaveProperty("report");
    // The whole document carries no pull or stash command: migration cannot hide here.
    expect(commandStrings(doc).filter((command) => command.includes("pull") || command.includes("stash"))).toEqual([]);
  });

  test("mode default: no flag equals explicit --all and every invocation parses as one JSON document", () => {
    const repo = currentNotDefaultFixture("mode-default");
    const explicit = runAnalyze(["--all", repo], sandboxRoot);
    const implicit = runAnalyze([repo], sandboxRoot);
    const branches = runAnalyze(["--branches", repo], sandboxRoot);
    expect(explicit.status).toBe(0);
    expect(implicit.status).toBe(0);
    expect(branches.status).toBe(0);
    const allDoc = JSON.parse(explicit.stdout) as Record<string, unknown>;
    const noFlagDoc = JSON.parse(implicit.stdout) as Record<string, unknown>;
    JSON.parse(branches.stdout);
    expect(noFlagDoc).toEqual(allDoc);
    // The default mode is --all: migration, classification, batch and report all present.
    expect(allDoc).toHaveProperty("migration");
    expect(allDoc).toHaveProperty("classification");
    expect(allDoc).toHaveProperty("batch");
    expect(allDoc).toHaveProperty("report");
  });
});

describe("analyze.mjs classification on real fixtures", () => {
  test("a branch merged into default lands in the batch as -d with its exact command", () => {
    const repo = fixtureRepo("cli-merged", "trunk");
    git(["branch", "feature/merged"], repo);
    commitOn(repo, "trunk-only.md", "# trunk moved on\n", "trunk commit after branch");
    const doc = analyzeDoc(["--all", repo], sandboxRoot);
    const batch = doc.batch as Array<Record<string, unknown>>;
    const entry = batch.find((item) => item.branch === "feature/merged");
    expect(entry).toBeObject();
    expect(entry?.action).toBe("-d");
    // The exact string a consumer executes, quoting included (L13).
    expect(String(entry?.command)).toContain("git branch -d 'feature/merged'");
  });

  test("a tree-identical branch lands in the batch as -D with empty-diff evidence", () => {
    const repo = fixtureRepo("cli-tree-identical", "trunk");
    // Different commit than trunk, identical tree: make a change, then revert it, so
    // git diff trunk..<branch> is empty while the tip is not an ancestor — the exact
    // -D configuration.
    git(["switch", "-q", "-c", "feature/same-tree"], repo);
    commitOn(repo, "scratch.md", "# temporary\n", "temporary change");
    git(["rm", "-q", "scratch.md"], repo);
    git(["commit", "-q", "-m", "revert the temporary change"], repo);
    const doc = analyzeDoc(["--all", repo], sandboxRoot);
    // Fixture precondition: the tree really is identical to trunk (R3).
    const diff = spawnSync("git", ["diff", "--quiet", "trunk..feature/same-tree"], {
      cwd: repo,
      encoding: "utf8",
      env: childEnv,
    });
    expect(diff.status).toBe(0);
    const batch = doc.batch as Array<Record<string, unknown>>;
    const entry = batch.find((item) => item.branch === "feature/same-tree");
    expect(entry).toBeObject();
    expect(entry?.action).toBe("-D");
    expect(entry?.evidence).toBe("empty diff vs default");
    expect(String(entry?.command)).toContain("git branch -D 'feature/same-tree'");
  });

  test("[gone] upstream with a divergent diff stays KEEP: absent from the batch, surfaced in the report", () => {
    const base = nextBase("gone-divergent");
    const repo = fixtureRepo(base, "trunk");
    const origin = bareOrigin(base);
    git(["remote", "add", "origin", origin], repo);
    git(["push", "-q", "-u", "origin", "HEAD"], repo);
    git(["symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/trunk"], repo);
    // Push a feature branch, delete it on the origin, then keep committing locally:
    // upstream [gone] AND a non-empty diff — the KEEP (needs review) configuration.
    git(["switch", "-q", "-c", "feature/gone"], repo);
    commitOn(repo, "gone.md", "# local divergence\n", "local-only commit");
    git(["push", "-q", "-u", "origin", "feature/gone"], repo);
    git(["push", "origin", "--delete", "feature/gone"], repo);
    commitOn(repo, "gone-more.md", "# more local work\n", "another local commit");
    const doc = analyzeDoc(["--all", repo], sandboxRoot);
    // Fixture precondition asserted against the emitted document itself (R3).
    expect(String(doc.fetchStatus)).toBe("ok");
    const batch = doc.batch as Array<Record<string, unknown>>;
    expect(batch.map((entry) => entry.branch)).not.toContain("feature/gone");
    // Not silently dropped: the branch still appears in the document for review.
    expect(JSON.stringify(doc)).toContain("feature/gone");
  });

  test("a PROTECTED-regex branch never reaches the batch", () => {
    const repo = fixtureRepo("cli-protected", "trunk");
    // `staging` is PROTECTED and not a KNOWN_DEFAULTS name, so protection alone (not
    // default-branch detection) must keep it out of the batch.
    git(["branch", "staging"], repo);
    commitOn(repo, "staging-work.md", "# staging-only work\n", "staging commit");
    const doc = analyzeDoc(["--all", repo], sandboxRoot);
    const batch = doc.batch as Array<Record<string, unknown>>;
    expect(batch.map((entry) => entry.branch)).not.toContain("staging");
    // The branch is still reported, never silently dropped.
    expect(JSON.stringify(doc)).toContain("staging");
  });
});

describe("analyze.mjs migration plan at the CLI boundary", () => {
  // Local-only behind state: the origin gains a commit trunk does not have, so the
  // default is behind — the configuration under which the pull must be emitted
  // regardless of the implementer's level-with-upstream emission policy.
  function behindCurrentNotDefault(name: string): string {
    const repo = currentNotDefaultFixture(name);
    const originUrl = spawnSync("git", ["remote", "get-url", "origin"], {
      cwd: repo,
      encoding: "utf8",
      env: childEnv,
    });
    if (originUrl.status !== 0) throw new Error(`origin url failed: ${originUrl.stderr}`);
    const other = cloneOf(originUrl.stdout.trim(), `${name}-other`);
    commitOn(other, "remote.md", "# advanced remotely\n", "remote-only commit");
    git(["push", "-q", "origin", "HEAD"], other);
    git(["fetch", "-q", "origin"], repo);
    return repo;
  }

  test("the emitted pull names the default branch while HEAD is on a feature branch", () => {
    const repo = behindCurrentNotDefault("pull-pin");
    const doc = analyzeDoc(["--all", repo], sandboxRoot);
    expect(doc).toHaveProperty("migration");
    const commands = commandStrings(doc);
    const pulls = commands.filter((command) => command.includes("pull --ff-only"));
    expect(pulls).toHaveLength(1);
    // R4/L17: exact default-pinned destination, never HEAD, never the current branch.
    expect(pulls[0]).toBe("git pull --ff-only 'origin' 'trunk'");
    // The pre-migration current branch is recorded for the report.
    expect(JSON.stringify(doc.migration)).toContain("feature/work");
    // Read-only proof: the analyzer emitted the commands but did not run them — HEAD
    // is still on the feature branch and no stash exists (R1).
    const head = spawnSync("git", ["rev-parse", "--abbrev-ref", "HEAD"], {
      cwd: repo,
      encoding: "utf8",
      env: childEnv,
    });
    expect(head.stdout.trim()).toBe("feature/work");
    const stashes = spawnSync("git", ["stash", "list"], {
      cwd: repo,
      encoding: "utf8",
      env: childEnv,
    });
    expect(stashes.stdout.trim()).toBe("");
  });

  test("every emitted git command in a real --all document is push-free", () => {
    // The exact configuration where a push could hide: default ahead of its upstream,
    // a queued deletion, and migration in one document (R3), worktree clean so no
    // stash command muddies the scan.
    const base = nextBase("push-scan");
    const repo = fixtureRepo(base, "trunk");
    const origin = bareOrigin(base);
    git(["remote", "add", "origin", origin], repo);
    git(["push", "-q", "-u", "origin", "HEAD"], repo);
    git(["symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/trunk"], repo);
    git(["branch", "feature/merged"], repo);
    commitOn(repo, "local.md", "# local only\n", "local-only commit");
    git(["switch", "-q", "-c", "feature/work"], repo);
    const doc = analyzeDoc(["--all", repo], sandboxRoot);
    const commands = commandStrings(doc);
    expect(commands.length).toBeGreaterThan(0);
    expect(commands.filter((command) => /push/.test(command))).toEqual([]);
  });

  test("a queued worktree removal adds git worktree prune", () => {
    const repo = fixtureRepo("cli-prune-present", "trunk");
    git(["branch", "feature/done"], repo);
    git(["worktree", "add", "-q", join(sandboxRoot, "cli-prune-linked"), "feature/done"], repo);
    const doc = analyzeDoc(["--all", repo], sandboxRoot);
    const commands = commandStrings(doc);
    // Fixture precondition: the removal really is queued, or the prune claim is vacuous.
    expect(commands.filter((command) => command.includes("worktree remove"))).toHaveLength(1);
    const prunes = commands.filter((command) => command.includes("worktree prune"));
    expect(prunes).toHaveLength(1);
    expect(prunes[0]).toContain("git worktree prune");
  });

  test("no queued worktree removal: no prune command", () => {
    const repo = fixtureRepo("cli-prune-absent", "trunk");
    git(["switch", "-q", "-c", "feature/work"], repo);
    const doc = analyzeDoc(["--all", repo], sandboxRoot);
    // Prove the "none queued" configuration holds, or the absence check is vacuous (R3).
    const commands = commandStrings(doc);
    expect(commands.filter((command) => command.includes("worktree remove"))).toEqual([]);
    expect(commands.filter((command) => command.includes("prune"))).toEqual([]);
  });

  test("stdout stays a single JSON document with the migration plan present", () => {
    const repo = currentNotDefaultFixture("single-json");
    const run = runAnalyze(["--all", repo], sandboxRoot);
    expect(run.status).toBe(0);
    // JSON.parse of the whole stdout doubles as the single-document check: stray
    // output or a second document fails to parse.
    const doc = JSON.parse(run.stdout) as Record<string, unknown>;
    expect(doc).toBeObject();
    expect(doc).toHaveProperty("migration");
  });
});
