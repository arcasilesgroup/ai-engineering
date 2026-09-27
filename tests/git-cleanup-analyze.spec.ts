// tests/git-cleanup-analyze.spec.ts — unit layer of the ai-git-cleanup test plan (checkpoints 1-2):
// analyze.mjs classification logic driven through real temp repositories (the script builds its
// own survey from git plumbing, so fixtures are the only honest input). Sandbox rides on the
// environment the child git inherits; GIT_CONFIG_GLOBAL points at an empty file so the machine's
// ~/.gitconfig cannot decide what any child git does.

import { afterAll, describe, expect, test } from "bun:test";
import { spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const script = join(import.meta.dir, "..", "skills", "ai-git-cleanup", "scripts", "analyze.mjs");
const sandboxRoot = mkdtempSync(join(tmpdir(), "ai-eng-git-cleanup-analyze-"));
const emptyGitConfig = join(sandboxRoot, "empty-gitconfig");
writeFileSync(emptyGitConfig, "");

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

interface BranchEntry {
  branch?: string;
  reason?: string;
  command?: string;
  verifyWith?: string;
  cluster?: string;
  worktreePath?: string;
}

interface WorktreeEntry {
  path?: string;
  branch?: string;
  dirty?: boolean;
  stale?: boolean;
  command?: string;
}

interface Report {
  fetchStatus?: string;
  defaultBranch?: string;
  currentBranch?: string;
  deleteCandidates?: BranchEntry[];
  needsReview?: BranchEntry[];
  keep?: BranchEntry[];
  worktrees?: WorktreeEntry[];
  unanalyzed?: BranchEntry[];
  postSync?: Record<string, unknown>;
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

// Every case funnels through here: exit 0 and one parseable JSON document, else the test
// fails on the script's absence/misbehaviour instead of on a half-read report.
function analyze(repo: string): Report {
  const run = runAnalyze([repo], sandboxRoot);
  expect(run.status).toBe(0);
  return JSON.parse(run.stdout) as Report;
}

function commit(repo: string, file: string, text: string): void {
  writeFileSync(join(repo, file), text);
  git(["add", "-A"], repo);
  git(["commit", "-q", "-m", `add ${file}`], repo);
}

function names(entries: BranchEntry[] | undefined): string[] {
  return (entries ?? []).map((entry) => entry.branch ?? "");
}

function entryFor(entries: BranchEntry[] | undefined, branch: string): BranchEntry | undefined {
  return (entries ?? []).find((entry) => entry.branch === branch);
}

// Every key/value pair in the document at any depth: conditional-field checks run over
// the whole emitted structure, so they hold wherever a section lands (R2).
function deepPairs(value: unknown, key = ""): [string, unknown][] {
  if (Array.isArray(value)) return value.flatMap((item) => deepPairs(item, key));
  if (value !== null && typeof value === "object") {
    const pairs: [string, unknown][] = [];
    for (const [childKey, child] of Object.entries(value)) {
      pairs.push([childKey, child], ...deepPairs(child, childKey));
    }
    return pairs;
  }
  return [[key, value]];
}

// Command-bearing fields: values under command/verifyWith keys plus any string a shell
// could execute. The postSync commands qualify wherever they live, so no section rename
// can hide a command from the invariant scans (R3).
function commandStrings(value: unknown): string[] {
  return deepPairs(value).flatMap(([key, entry]) =>
    typeof entry === "string" && (key.includes("command") || key.includes("verifyWith") || entry.startsWith("git "))
      ? [entry]
      : [],
  );
}

// Local-file remote for the postSync fixtures: main pushed with its upstream configured,
// so level/behind/ahead states come from origin/main alone — no network involved.
function fixtureWithOrigin(name: string): string {
  const repo = fixtureRepo(name, "main");
  const origin = join(sandboxRoot, `${name}-origin.git`);
  git(["init", "-q", "-b", "main", "--bare", origin], sandboxRoot);
  git(["remote", "add", "origin", origin], repo);
  git(["push", "-q", "-u", "origin", "main"], repo);
  return repo;
}

describe("analyze.mjs", () => {
  test("survey: one JSON document carries every bucket from a real repo inventory", () => {
    const repo = fixtureRepo("survey", "main");
    git(["checkout", "-q", "-b", "feature/merged"], repo);
    commit(repo, "a.md", "work");
    git(["checkout", "-q", "main"], repo);
    git(["merge", "-q", "--no-ff", "feature/merged"], repo);
    const report = analyze(repo);
    expect(report.deleteCandidates).toBeArray();
    expect(report.needsReview).toBeArray();
    expect(report.keep).toBeArray();
    expect(report.worktrees).toBeArray();
    expect(report.unanalyzed).toBeArray();
    // The inventory saw the merged branch: it is classified, not dropped.
    expect(names(report.deleteCandidates)).toContain("feature/merged");
  });

  test("PROTECTED regex: main/master/develop/staging/production/release-*/hotfix-* are never deletable", () => {
    const repo = fixtureRepo("protected", "main");
    // Each protected sibling sits on main with no extra work, so only the PROTECTED
    // rule can be what keeps them out of deleteCandidates. A merged non-protected
    // branch proves the bucket itself is reachable.
    for (const branch of ["master", "develop", "staging", "production", "release-2026.09", "hotfix-1"]) {
      git(["branch", branch], repo);
    }
    git(["checkout", "-q", "-b", "feature/done"], repo);
    commit(repo, "done.md", "finished work");
    git(["checkout", "-q", "main"], repo);
    git(["merge", "-q", "--no-ff", "feature/done"], repo);
    const report = analyze(repo);
    expect(names(report.deleteCandidates)).toContain("feature/done");
    for (const branch of ["main", "master", "develop", "staging", "production", "release-2026.09", "hotfix-1"]) {
      expect(names(report.deleteCandidates)).not.toContain(branch);
    }
  });

  test("default branch: origin/HEAD normalizes a non-standard default that is never deletable", () => {
    const repo = fixtureRepo("default branch mainline", "mainline");
    // A non-standard default name is only provable through origin/HEAD; without
    // that anchor the analyzer must fail closed rather than guess from the HEAD.
    const origin = join(sandboxRoot, "mainline-origin.git");
    git(["init", "-q", "-b", "mainline", "--bare", origin], sandboxRoot);
    git(["remote", "add", "origin", origin], repo);
    git(["push", "-q", "origin", "mainline"], repo);
    git(["symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/mainline"], repo);
    git(["checkout", "-q", "-b", "feature/done"], repo);
    commit(repo, "done.md", "finished work");
    git(["checkout", "-q", "mainline"], repo);
    git(["merge", "-q", "--no-ff", "feature/done"], repo);
    const report = analyze(repo);
    expect(report.defaultBranch).toBe("mainline");
    expect(names(report.deleteCandidates)).toContain("feature/done");
    expect(names(report.deleteCandidates)).not.toContain("mainline");
    expect(names(report.keep)).toContain("mainline");
  });

  test("no default anchor: without origin/HEAD or a known default, nothing is deletable", () => {
    const repo = fixtureRepo("no default anchor", "mainline");
    // HEAD sits on a feature branch that fully contains mainline: resolving the
    // default from the checked-out branch would declare the true default safe to
    // delete, so the run must fail closed instead.
    git(["checkout", "-q", "-b", "feature/x"], repo);
    const report = analyze(repo);
    expect(report.defaultBranch).toBe("");
    expect(report.deleteCandidates).toEqual([]);
    expect(entryFor(report.unanalyzed, "mainline")?.reason).toBe("NO_DEFAULT_BRANCH");
    expect(entryFor(report.unanalyzed, "feature/x")?.reason).toBe("NO_DEFAULT_BRANCH");
  });

  test("current branch: the checked-out branch is keep, never a delete candidate", () => {
    const repo = fixtureRepo("current branch", "main");
    git(["checkout", "-q", "-b", "feature/checked-out"], repo);
    commit(repo, "wip.md", "in flight");
    const report = analyze(repo);
    expect(names(report.keep)).toContain("feature/checked-out");
    expect(names(report.deleteCandidates)).not.toContain("feature/checked-out");
  });

  test("current branch: a merged branch left checked out is CURRENT_BRANCH keep at unique zero", () => {
    const repo = fixtureRepo("current branch merged", "main");
    git(["checkout", "-q", "-b", "feature/merged"], repo);
    commit(repo, "m.md", "merged work");
    git(["checkout", "-q", "main"], repo);
    git(["merge", "-q", "--no-ff", "feature/merged"], repo);
    git(["checkout", "-q", "feature/merged"], repo);
    const report = analyze(repo);
    // Zero unique commits against main: only the checked-out guard stands between
    // this branch and the merge-base delete gate below it.
    expect(entryFor(report.keep, "feature/merged")?.reason).toBe("CURRENT_BRANCH");
    expect(names(report.deleteCandidates)).not.toContain("feature/merged");
  });

  test("cluster: two-segment clusters group siblings without absorbing other one-segment names", () => {
    const repo = fixtureRepo("cluster", "main");
    // All three feature/api branches are merged (no extra commits), so clustering is
    // the only thing that can tie them together; feature/login shares only "feature".
    for (const branch of ["feature/api", "feature/api-v2", "feature/api-refactor", "feature/login"]) {
      git(["branch", branch], repo);
    }
    const report = analyze(repo);
    const all = [...(report.deleteCandidates ?? []), ...(report.keep ?? []), ...(report.needsReview ?? [])];
    const apiCluster = entryFor(all, "feature/api")?.cluster;
    expect(apiCluster).toBeString();
    expect(apiCluster).not.toBe("");
    expect(entryFor(all, "feature/api-v2")?.cluster).toBe(apiCluster as string);
    expect(entryFor(all, "feature/api-refactor")?.cluster).toBe(apiCluster as string);
    expect(entryFor(all, "feature/login")?.cluster).not.toBe(apiCluster as string);
  });

  test("SAFE_TO_DELETE: a merged branch carries a merge-base ancestry guard against the default branch", () => {
    const repo = fixtureRepo("SAFE_TO_DELETE", "main");
    git(["checkout", "-q", "-b", "feature/merged"], repo);
    commit(repo, "m.md", "merged work");
    git(["checkout", "-q", "main"], repo);
    git(["merge", "-q", "--no-ff", "feature/merged"], repo);
    const report = analyze(repo);
    const entry = entryFor(report.deleteCandidates, "feature/merged");
    expect(entry).toBeDefined();
    expect(entry?.reason).toBe("SAFE_TO_DELETE");
    // The guard names the default branch itself, never an upstream remote ref.
    expect(entry?.verifyWith).toBe("git merge-base --is-ancestor 'refs/heads/feature/merged' 'main'");
    // Pinned to -d, single-quoted: a -D or unquoted refname would slip past the guard.
    expect(entry?.command).toBe("git branch -d 'feature/merged'");
  });

  test("UNPUSHED_WORK: commits ahead of the upstream are keep", () => {
    const origin = join(sandboxRoot, "unpushed-origin.git");
    git(["init", "-q", "-b", "main", "--bare", origin], sandboxRoot);
    const repo = fixtureRepo("UNPUSHED_WORK", "main");
    git(["remote", "add", "origin", origin], repo);
    git(["push", "-q", "origin", "main"], repo);
    git(["checkout", "-q", "-b", "feature/wip"], repo);
    commit(repo, "p.md", "pushed work");
    git(["push", "-q", "-u", "origin", "feature/wip"], repo);
    // One commit lands after the push: ahead of the upstream, so unpushed > 0.
    commit(repo, "wip.md", "unpushed work");
    const report = analyze(repo);
    expect(names(report.keep)).toContain("feature/wip");
    expect(entryFor(report.keep, "feature/wip")?.reason).toBe("UNPUSHED_WORK");
    expect(names(report.deleteCandidates)).not.toContain("feature/wip");
  });

  test("gone: a [gone] upstream lands in needsReview and never in deleteCandidates", () => {
    const origin = join(sandboxRoot, "gone-origin.git");
    git(["init", "-q", "-b", "main", "--bare", origin], sandboxRoot);
    const repo = fixtureRepo("gone", "main");
    git(["remote", "add", "origin", origin], repo);
    git(["checkout", "-q", "-b", "feature/pushed"], repo);
    commit(repo, "p.md", "pushed work");
    git(["push", "-q", "-u", "origin", "feature/pushed"], repo);
    git(["push", "-q", "origin", "main"], repo);
    // The remote branch disappears; the analyzer's prune turns the upstream into [gone].
    git(["push", "origin", "--delete", "feature/pushed"], repo);
    const report = analyze(repo);
    expect(names(report.deleteCandidates)).not.toContain("feature/pushed");
    expect(names(report.needsReview)).toContain("feature/pushed");
  });

  test("SYNCED: a tracked branch level with a live remote is keep", () => {
    const origin = join(sandboxRoot, "synced-origin.git");
    git(["init", "-q", "-b", "main", "--bare", origin], sandboxRoot);
    const repo = fixtureRepo("SYNCED", "main");
    git(["remote", "add", "origin", origin], repo);
    git(["checkout", "-q", "-b", "feature/synced"], repo);
    commit(repo, "s.md", "synced work");
    git(["push", "-q", "-u", "origin", "feature/synced"], repo);
    git(["push", "-q", "origin", "main"], repo);
    const report = analyze(repo);
    expect(names(report.keep)).toContain("feature/synced");
    expect(entryFor(report.keep, "feature/synced")?.reason).toBe("SYNCED_WITH_REMOTE");
    expect(names(report.deleteCandidates)).not.toContain("feature/synced");
  });

  test("LOCAL_WORK: a local-only branch with unique work is keep", () => {
    const repo = fixtureRepo("LOCAL_WORK", "main");
    git(["checkout", "-q", "-b", "feature/local"], repo);
    commit(repo, "l.md", "local experiment");
    const report = analyze(repo);
    expect(names(report.keep)).toContain("feature/local");
    expect(entryFor(report.keep, "feature/local")?.reason).toBe("LOCAL_WORK");
    expect(names(report.deleteCandidates)).not.toContain("feature/local");
  });

  test("quot: hostile refnames are emitted single-quoted with apostrophe escaping", () => {
    const repo = fixtureRepo("quot", "main");
    // Valid git refname carrying every shell metacharacter that must stay inert.
    const hostile = "evil/$(id)`x`;|&'ref";
    git(["branch", hostile], repo);
    const report = analyze(repo);
    const quoted = `'refs/heads/${hostile.replaceAll("'", "''")}'`;
    const expected = `git merge-base --is-ancestor ${quoted} 'main'`;
    // The hostile branch sits on main with no extra work, so it must reach a
    // delete candidate whose guard is the quoted form — never a bare refname.
    const entry = entryFor(report.deleteCandidates, hostile);
    expect(entry).toBeDefined();
    expect(entry?.verifyWith).toBe(expected);
    // No unquoted reference to the hostile refname anywhere in the document.
    expect(JSON.stringify(report).includes(`refs/heads/${hostile}`)).toBe(false);
  });

  test("dirty: a dirty worktree is flagged and never stale; a clean deletable one is stale", () => {
    const repo = fixtureRepo("dirty", "main");
    git(["checkout", "-q", "-b", "feature/clean-wt"], repo);
    commit(repo, "c.md", "merged work");
    git(["checkout", "-q", "main"], repo);
    git(["merge", "-q", "--no-ff", "feature/clean-wt"], repo);
    // Create the branch without checking it out: git refuses to add a linked
    // worktree for a branch the main worktree already holds.
    git(["branch", "feature/dirty-wt"], repo);
    const cleanPath = join(sandboxRoot, "wt-clean");
    const dirtyPath = join(sandboxRoot, "wt-dirty");
    git(["worktree", "add", "-q", cleanPath, "feature/clean-wt"], repo);
    git(["worktree", "add", "-q", dirtyPath, "feature/dirty-wt"], repo);
    // Uncommitted change: status is non-empty, so the worktree must be refused.
    writeFileSync(join(dirtyPath, "uncommitted.md"), "work in progress\n");
    const report = analyze(repo);
    const dirty = (report.worktrees ?? []).find((wt) => wt.branch === "feature/dirty-wt");
    expect(dirty).toBeDefined();
    expect(dirty?.dirty).toBe(true);
    expect(dirty?.stale).not.toBe(true);
    // Stale only when the worktree is clean and its branch is deletable.
    const clean = (report.worktrees ?? []).find((wt) => wt.branch === "feature/clean-wt");
    expect(clean).toBeDefined();
    expect(clean?.dirty).toBe(false);
    expect(clean?.stale).toBe(true);
    // The delete candidate carries the holding worktree's path, so the single
    // approved plan can order the worktree removal before the branch delete.
    expect(entryFor(report.deleteCandidates, "feature/clean-wt")?.worktreePath).toBe(clean?.path);
  });

  test("unanalyzed: the bucket is present even when every branch classifies", () => {
    const repo = fixtureRepo("unanalyzed", "main");
    git(["branch", "feature/only"], repo);
    const report = analyze(repo);
    expect(report.unanalyzed).toBeArray();
    expect(report.unanalyzed).toHaveLength(0);
  });

  test("malformed: a broken ref inventory fails closed, never a delete plan", () => {
    const repo = fixtureRepo("malformed", "main");
    // A ref that is not a SHA breaks the inventory survey mid-read.
    writeFileSync(join(repo, ".git", "refs", "heads", "broken"), "not-a-sha\n");
    const run = runAnalyze([repo], sandboxRoot);
    if (run.status === 0) {
      const report = JSON.parse(run.stdout) as Report;
      expect(report.deleteCandidates ?? []).toEqual([]);
    } else {
      expect(run.stdout).not.toContain("SAFE_TO_DELETE");
    }
  });

  test('fetchStatus: a working origin yields exactly "ok" as its own top-level property in one JSON document', () => {
    const origin = join(sandboxRoot, "fetch-ok-origin.git");
    git(["init", "-q", "-b", "main", "--bare", origin], sandboxRoot);
    const repo = fixtureRepo("fetch ok", "main");
    git(["remote", "add", "origin", origin], repo);
    git(["push", "-q", "origin", "main"], repo);
    const run = runAnalyze([repo], sandboxRoot);
    expect(run.status).toBe(0);
    // Parsing the whole stdout doubles as the single-JSON-document check: anything
    // printed outside the one document would make this parse throw.
    const report = JSON.parse(run.stdout) as Report;
    expect(Object.keys(report)).toContain("fetchStatus");
    expect(report.fetchStatus).toBe("ok");
  });

  test('fetchStatus: with no origin the fetch is skipped and the field is still exactly "ok"', () => {
    const repo = fixtureRepo("fetch no origin", "main");
    const run = runAnalyze([repo], sandboxRoot);
    expect(run.status).toBe(0);
    const report = JSON.parse(run.stdout) as Report;
    expect(Object.keys(report)).toContain("fetchStatus");
    expect(report.fetchStatus).toBe("ok");
  });

  test('fetchStatus: a broken origin surfaces "failed: <first stderr line, trimmed>" and classification stays conservative', () => {
    const repo = fixtureRepo("fetch failed", "main");
    git(["remote", "add", "origin", join(sandboxRoot, "missing-fetch-origin.git")], repo);
    git(["checkout", "-q", "-b", "feature/local"], repo);
    commit(repo, "local.md", "local work");
    git(["checkout", "-q", "main"], repo);
    // The exact reason comes from replaying the identical fetch against the identical
    // fixture, so the field is pinned without hardcoding git's wording or a
    // machine-specific path into the test.
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
    const run = runAnalyze([repo], sandboxRoot);
    expect(run.status).toBe(0);
    const report = JSON.parse(run.stdout) as Report;
    expect(Object.keys(report)).toContain("fetchStatus");
    expect(report.fetchStatus).toBe(`failed: ${firstStderrLine}`);
    // Conservative classification under a failed fetch: the fallback default branch
    // still resolves, and nothing is fabricated into a delete plan.
    expect(report.defaultBranch).toBe("main");
    expect(report.deleteCandidates).toEqual([]);
    expect(entryFor(report.keep, "feature/local")?.reason).toBe("LOCAL_WORK");
  });

  test("prune: a queued worktree removal surfaces the exact git worktree prune command in the plan", () => {
    const repo = fixtureRepo("prune-queued", "main");
    git(["checkout", "-q", "-b", "feature/clean-wt"], repo);
    commit(repo, "c.md", "clean worktree work");
    git(["checkout", "-q", "main"], repo);
    git(["merge", "-q", "--no-ff", "feature/clean-wt"], repo);
    git(["worktree", "add", "-q", join(sandboxRoot, "wt-prune-queued"), "feature/clean-wt"], repo);
    const report = analyze(repo);
    expect(Object.keys(report)).toContain("fetchStatus");
    expect(report.fetchStatus).toBe("ok");
    // The qualifying configuration: a removal is really queued for this worktree...
    const queued = (report.worktrees ?? []).find((worktree) => worktree.branch === "feature/clean-wt");
    expect(queued?.stale).toBe(true);
    expect(queued?.command).toBe(`git worktree remove '${queued?.path}'`);
    // ...and only then does the sync section exist and carry the exact prune command.
    expect(Object.hasOwn(report, "postSync")).toBe(true);
    expect(commandStrings(report)).toContain("git worktree prune");
  });

  test("prune: a refused dirty worktree queues no removal, so no git worktree prune command exists", () => {
    const repo = fixtureRepo("prune-refused", "main");
    // L10: create the branch without checking it out — the linked worktree holds it.
    git(["branch", "feature/wip-wt"], repo);
    const path = join(sandboxRoot, "wt-prune-refused");
    git(["worktree", "add", "-q", path, "feature/wip-wt"], repo);
    writeFileSync(join(path, "uncommitted.md"), "work in progress\n");
    const report = analyze(repo);
    expect(Object.keys(report)).toContain("fetchStatus");
    expect(report.fetchStatus).toBe("ok");
    expect(Object.hasOwn(report, "postSync")).toBe(true);
    // The refusal stands between the dirty worktree and every command: a worktree exists
    // but none is queued, so the prune conditional must not fire (R3).
    const held = (report.worktrees ?? []).find((worktree) => worktree.branch === "feature/wip-wt");
    expect(held?.dirty).toBe(true);
    expect(held?.command).toBeUndefined();
    expect(commandStrings(report).some((command) => command.includes("worktree prune"))).toBe(false);
  });

  test("pull: a default branch behind its upstream carries git pull --ff-only with the upstream name and behind count", () => {
    const repo = fixtureWithOrigin("pull-behind");
    commit(repo, "b.md", "upstream work");
    commit(repo, "b2.md", "more upstream work");
    git(["push", "-q", "origin", "main"], repo);
    // The local tip rewinds, so origin/main holds exactly the two commits this clone
    // lacks: behind 2, ahead 0, measured against the configured upstream.
    git(["reset", "-q", "--hard", "HEAD~2"], repo);
    const report = analyze(repo);
    expect(Object.keys(report)).toContain("fetchStatus");
    expect(report.fetchStatus).toBe("ok");
    expect(Object.hasOwn(report, "postSync")).toBe(true);
    const pull = commandStrings(report).find((command) => command.startsWith("git pull --ff-only"));
    expect(pull).toBeDefined();
    expect(pull).toContain("origin");
    // The behind count the gate shows, exact against the commits this fixture created.
    const behind = deepPairs(report)
      .filter(([key]) => /behind/i.test(key))
      .map(([, value]) => value);
    expect(behind.map(Number)).toContain(2);
    // Classification stays conservative: a behind default branch is never deletable.
    expect(names(report.deleteCandidates)).not.toContain("main");
  });

  test("pull: a level default branch carries no git pull --ff-only command", () => {
    const repo = fixtureWithOrigin("pull-level");
    const report = analyze(repo);
    expect(Object.keys(report)).toContain("fetchStatus");
    expect(report.fetchStatus).toBe("ok");
    expect(Object.hasOwn(report, "postSync")).toBe(true);
    expect(commandStrings(report).some((command) => command.startsWith("git pull --ff-only"))).toBe(false);
  });

  test("ahead: a default branch ahead of its upstream is report-only — ahead count emitted, never a push command", () => {
    const repo = fixtureWithOrigin("ahead-default");
    commit(repo, "ahead.md", "local ahead work");
    commit(repo, "ahead2.md", "more local ahead work");
    const report = analyze(repo);
    expect(Object.keys(report)).toContain("fetchStatus");
    expect(report.fetchStatus).toBe("ok");
    expect(Object.hasOwn(report, "postSync")).toBe(true);
    const commands = commandStrings(report);
    // Report-only: being ahead must not fire the pull conditional, and no command
    // anywhere in the document may push — the invariant holds unconditionally (R3).
    expect(commands.some((command) => command.startsWith("git pull --ff-only"))).toBe(false);
    expect(commands.some((command) => command.includes("push"))).toBe(false);
    // The emitted ahead count, exact against the two commits this fixture created.
    const ahead = deepPairs(report)
      .filter(([key]) => /ahead/i.test(key))
      .map(([, value]) => value);
    expect(ahead.map(Number)).toContain(2);
  });

  test("single view: the report carries every command, guard, and back-link the one gate renders", () => {
    const repo = fixtureRepo("single view", "main");
    git(["checkout", "-q", "-b", "feature/merged"], repo);
    commit(repo, "m.md", "merged work");
    git(["checkout", "-q", "main"], repo);
    git(["merge", "-q", "--no-ff", "feature/merged"], repo);
    git(["checkout", "-q", "-b", "feature/clean-wt"], repo);
    commit(repo, "c.md", "clean worktree work");
    git(["checkout", "-q", "main"], repo);
    git(["merge", "-q", "--no-ff", "feature/clean-wt"], repo);
    git(["worktree", "add", "-q", join(sandboxRoot, "wt-single-view"), "feature/clean-wt"], repo);
    const report = analyze(repo);
    // The gate's fetch banner reads from the same document as everything else.
    expect(Object.keys(report)).toContain("fetchStatus");
    expect(report.fetchStatus).toBe("ok");
    expect(report.defaultBranch).toBe("main");

    // Every bucket and the checkout the merged view renders, present with this fixture's
    // exact contents (R2/L11): nothing the gate reads may be missing from the report.
    expect(Object.hasOwn(report, "currentBranch")).toBe(true);
    expect(report.currentBranch).toBe("main");
    expect(Object.hasOwn(report, "keep")).toBe(true);
    expect(Object.hasOwn(report, "needsReview")).toBe(true);
    expect(Object.hasOwn(report, "unanalyzed")).toBe(true);
    expect(names(report.keep)).toEqual(["main"]);
    expect(report.needsReview).toEqual([]);
    expect(report.unanalyzed).toEqual([]);

    const candidates = report.deleteCandidates ?? [];
    expect(candidates).toHaveLength(2);
    expect(names(candidates)).toContain("feature/merged");
    expect(names(candidates)).toContain("feature/clean-wt");
    // Per-row plan: the exact delete command and ancestry guard on every candidate.
    for (const entry of candidates) {
      expect(entry.command).toBe(`git branch -d '${entry.branch}'`);
      expect(entry.verifyWith).toBe(`git merge-base --is-ancestor 'refs/heads/${entry.branch}' 'main'`);
    }

    const stale = (report.worktrees ?? []).filter((worktree) => worktree.stale === true);
    expect(stale).toHaveLength(1);
    const staleEntry = stale[0];
    expect(staleEntry).toBeDefined();
    const stalePath = staleEntry?.path ?? "";
    expect(stalePath).not.toBe("");
    expect(staleEntry?.command).toBe(`git worktree remove '${stalePath}'`);

    // Back-link: the held candidate names the worktree entry that must be removed first.
    const held = entryFor(candidates, "feature/clean-wt");
    expect(held?.worktreePath).toBe(stalePath);
    expect(staleEntry?.branch).toBe("feature/clean-wt");
    expect(entryFor(candidates, "feature/merged")?.worktreePath).toBeUndefined();
  });
});
