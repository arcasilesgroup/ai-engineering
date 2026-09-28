// tests/git-cleanup-analyze.spec.ts — unit layer of the ai-git-cleanup-v3 test plan (checkpoint 1):
// analyze.mjs driven through real temp repositories (the script builds its own survey from git
// plumbing, so fixtures are the only honest input). Sandbox rides on the environment the child git
// inherits; GIT_CONFIG_GLOBAL points at an empty file so the machine's ~/.gitconfig cannot decide
// what any child git does. No network: every remote is a local bare repository.
//
// The v3 document this spec pins: one JSON document with fetchStatus, defaultBranch, a `migration`
// plan (previousBranch, defaultBranch, switch/pull steps, conditional stash/pop steps — each with
// an on-failure WARN annotation), ONE `batch` array (entries: branch, category, action `-d`/`-D`,
// evidence, guarded single-quoted command, optional worktreePath), `keep` (fail-closed KEEP
// decisions), `unanalyzed`, `worktrees`, `postCleanup` (only when a removal is queued), and
// `report` (previousBranch, stashState, per-branch rows).

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

interface MigrationStep {
  command?: string;
  warn?: string;
  message?: string;
}

interface Migration {
  previousBranch?: string;
  defaultBranch?: string;
  switch?: MigrationStep;
  pull?: MigrationStep;
  stash?: MigrationStep;
  pop?: MigrationStep;
}

interface BatchEntry {
  branch?: string;
  category?: string;
  action?: string;
  evidence?: string;
  command?: string;
  cluster?: string;
  worktreePath?: string;
}

interface KeepEntry {
  branch?: string;
  reason?: string;
  evidence?: string;
  cluster?: string;
}

interface WorktreeEntry {
  path?: string;
  branch?: string;
  dirty?: boolean;
  dirtyFiles?: string[];
  stale?: boolean;
  requiresAcknowledgment?: boolean;
  command?: string;
}

interface ReportRow {
  branch?: string;
  action?: string;
  reason?: string;
  upstream?: string;
  ahead?: number | null;
  behind?: number | null;
}

interface Report {
  fetchStatus?: string;
  defaultBranch?: string;
  migration?: Migration;
  batch?: BatchEntry[];
  keep?: KeepEntry[];
  unanalyzed?: KeepEntry[];
  worktrees?: WorktreeEntry[];
  postCleanup?: Record<string, unknown>;
  report?: {
    previousBranch?: string;
    stashState?: string;
    branches?: ReportRow[];
  };
}

afterAll(() => {
  rmSync(sandboxRoot, { recursive: true, force: true });
});

function git(args: string[], cwd: string): void {
  const done = spawnSync("git", args, { cwd, encoding: "utf8", env: childEnv });
  if (done.status !== 0) throw new Error(`git ${args.join(" ")} failed: ${done.stderr}`);
}

function gitOut(args: string[], cwd: string): string {
  const done = spawnSync("git", args, { cwd, encoding: "utf8", env: childEnv });
  if (done.status !== 0) throw new Error(`git ${args.join(" ")} failed: ${done.stderr}`);
  return done.stdout.trim();
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

function names(entries: BatchEntry[] | KeepEntry[] | undefined): string[] {
  return (entries ?? []).map((entry) => entry.branch ?? "");
}

function entryFor<T extends BatchEntry | KeepEntry>(entries: T[] | undefined, branch: string): T | undefined {
  return (entries ?? []).find((entry) => entry.branch === branch);
}

// Every key/value pair in the document at any depth: conditional-field checks run over
// the whole emitted structure, so they hold wherever a section lands (R2).
function deepPairs(value: unknown, key = ""): [string, unknown][] {
  if (Array.isArray(value)) return value.flatMap((item) => deepPairs(item, key));
  if (value !== null && typeof value === "object") {
    const pairs: [string, unknown][] = [];
    for (const [childKey, child] of Object.entries(value)) {
      // Primitive children come back from the leaf return below — pushing them here too
      // would double-count every string leaf (e.g. one prune command emitted twice).
      if (child !== null && typeof child === "object") pairs.push([childKey, child]);
      pairs.push(...deepPairs(child, childKey));
    }
    return pairs;
  }
  return [[key, value]];
}

// Command-bearing fields: values under command/verifyWith keys plus any string a shell
// could execute. The migration/postCleanup commands qualify wherever they live, so no
// section rename can hide a command from the invariant scans (R3).
function commandStrings(value: unknown): string[] {
  return deepPairs(value).flatMap(([key, entry]) =>
    typeof entry === "string" && (key.includes("command") || key.includes("verifyWith") || entry.startsWith("git "))
      ? [entry]
      : [],
  );
}

// Local-file remote: main pushed with its upstream configured, so level/behind/ahead
// states come from origin/main alone — no network involved.
function fixtureWithOrigin(name: string): string {
  const repo = fixtureRepo(name, "main");
  const origin = join(sandboxRoot, `${name}-origin.git`);
  git(["init", "-q", "-b", "main", "--bare", origin], sandboxRoot);
  git(["remote", "add", "origin", origin], repo);
  git(["push", "-q", "-u", "origin", "main"], repo);
  return repo;
}

describe("analyze.mjs", () => {
  test("no default anchor: without origin/HEAD or a known default, nothing is deletable and no switch targets mutable state", () => {
    const repo = fixtureRepo("no default anchor", "mainline");
    // HEAD sits on a feature branch that fully contains mainline: resolving the
    // default from the checked-out branch would declare the true default safe to
    // delete, so the run must fail closed instead (L16/R4).
    git(["checkout", "-q", "-b", "feature/x"], repo);
    const report = analyze(repo);
    expect(report.defaultBranch).toBe("");
    expect(report.batch).toEqual([]);
    // No migration switch target anchored to mutable state: the document must not
    // carry any `git switch` command when no default could be proven.
    expect(commandStrings(report).some((command) => command.startsWith("git switch"))).toBe(false);
    // Uncertainty is surfaced for every branch, in KEEP or unanalyzed — never dropped.
    for (const branch of ["mainline", "feature/x"]) {
      const surfaced = [...(report.keep ?? []), ...(report.unanalyzed ?? [])].find((entry) => entry.branch === branch);
      expect(surfaced?.reason).toBe("NO_DEFAULT_BRANCH");
    }
  });

  test("current branch: the checked-out branch is keep, never a delete candidate", () => {
    const repo = fixtureRepo("current branch", "main");
    git(["checkout", "-q", "-b", "feature/checked-out"], repo);
    commit(repo, "wip.md", "in flight");
    const report = analyze(repo);
    expect(report.batch).toBeArray();
    expect(names(report.keep)).toContain("feature/checked-out");
    expect(names(report.batch)).not.toContain("feature/checked-out");
  });

  test("current branch: a merged branch left checked out is CURRENT_BRANCH keep, never batched", () => {
    const repo = fixtureRepo("current branch merged", "main");
    git(["checkout", "-q", "-b", "feature/merged"], repo);
    commit(repo, "m.md", "merged work");
    git(["checkout", "-q", "main"], repo);
    git(["merge", "-q", "--no-ff", "feature/merged"], repo);
    git(["checkout", "-q", "feature/merged"], repo);
    const report = analyze(repo);
    // Merged AND checked out: only the current-branch protection stands between this
    // branch and the `-d` classification (R3/L12 exact configuration).
    expect(entryFor(report.keep, "feature/merged")?.reason).toBe("CURRENT_BRANCH");
    expect(report.batch).toBeArray();
    expect(names(report.batch)).not.toContain("feature/merged");
  });

  test("cluster: two-segment clusters group siblings without absorbing other one-segment names", () => {
    const repo = fixtureRepo("cluster", "main");
    // All four feature branches sit on main with no extra work, so only clustering
    // can tie feature/api siblings together; feature/login shares only "feature".
    for (const branch of ["feature/api", "feature/api-v2", "feature/api-refactor", "feature/login"]) {
      git(["branch", branch], repo);
    }
    const report = analyze(repo);
    const all = [...(report.batch ?? []), ...(report.keep ?? []), ...(report.unanalyzed ?? [])];
    const apiCluster = entryFor(all, "feature/api")?.cluster;
    expect(apiCluster).toBeString();
    expect(apiCluster).not.toBe("");
    expect(entryFor(all, "feature/api-v2")?.cluster).toBe(apiCluster as string);
    expect(entryFor(all, "feature/api-refactor")?.cluster).toBe(apiCluster as string);
    expect(entryFor(all, "feature/login")?.cluster).not.toBe(apiCluster as string);
  });

  test("SAFE_TO_DELETE: a merged branch batched as -d carries the exact guarded single-quoted command", () => {
    const repo = fixtureRepo("SAFE_TO_DELETE", "main");
    git(["checkout", "-q", "-b", "feature/merged"], repo);
    commit(repo, "m.md", "merged work");
    git(["checkout", "-q", "main"], repo);
    git(["merge", "-q", "--no-ff", "feature/merged"], repo);
    const report = analyze(repo);
    const entry = entryFor(report.batch, "feature/merged");
    expect(entry).toBeDefined();
    expect(entry?.action).toBe("-d");
    // One guarded command: ancestry proof and delete, quoting every refname, with the
    // default branch itself as the proof target — never an upstream remote ref.
    expect(entry?.command).toBe(
      "git merge-base --is-ancestor 'refs/heads/feature/merged' 'main' && git branch -d 'feature/merged'",
    );
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
    expect(report.batch).toBeArray();
    expect(names(report.batch)).not.toContain("feature/wip");
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
    expect(report.batch).toBeArray();
    expect(names(report.batch)).not.toContain("feature/synced");
  });

  test("LOCAL_WORK: a local-only branch with unique work is keep", () => {
    const repo = fixtureRepo("LOCAL_WORK", "main");
    git(["checkout", "-q", "-b", "feature/local"], repo);
    commit(repo, "l.md", "local experiment");
    const report = analyze(repo);
    expect(names(report.keep)).toContain("feature/local");
    expect(entryFor(report.keep, "feature/local")?.reason).toBe("LOCAL_WORK");
    expect(report.batch).toBeArray();
    expect(names(report.batch)).not.toContain("feature/local");
  });

  test("quot: hostile refnames are emitted single-quoted with apostrophe escaping", () => {
    const repo = fixtureRepo("quot", "main");
    // Valid git refname carrying every shell metacharacter that must stay inert.
    const hostile = "evil/$(id)`x`;|&'ref";
    git(["branch", hostile], repo);
    const report = analyze(repo);
    const quote = (value: string) => `'${value.replaceAll("'", "''")}'`;
    // The hostile branch sits on main with no extra work, so it must reach the batch
    // whose guarded command quotes every refname — never a bare metacharacter.
    const entry = entryFor(report.batch, hostile);
    expect(entry).toBeDefined();
    expect(entry?.command).toBe(
      `git merge-base --is-ancestor ${quote(`refs/heads/${hostile}`)} ${quote("main")} && git branch -d ${quote(hostile)}`,
    );
    // No unquoted reference to the hostile refname anywhere in the document.
    expect(JSON.stringify(report).includes(`refs/heads/${hostile}`)).toBe(false);
  });

  test("protected before triage: the current branch with a [gone] upstream lands in KEEP, never batched", () => {
    const origin = join(sandboxRoot, "gone-current-origin.git");
    git(["init", "-q", "-b", "main", "--bare", origin], sandboxRoot);
    const repo = fixtureRepo("gone current", "main");
    git(["remote", "add", "origin", origin], repo);
    git(["push", "-q", "origin", "main"], repo);
    // The current branch loses its upstream on the remote while HEAD stays on it:
    // triage alone ([gone] + non-empty diff) would swallow it, so only the protection
    // filter running BEFORE categorization can land it in KEEP (L18/R3 exact config).
    git(["checkout", "-q", "-b", "feature/current"], repo);
    commit(repo, "c.md", "current work");
    git(["push", "-q", "-u", "origin", "feature/current"], repo);
    git(["push", "origin", "--delete", "feature/current"], repo);
    const report = analyze(repo);
    expect(gitOut(["symbolic-ref", "--quiet", "--short", "HEAD"], repo)).toBe("feature/current");
    const protectedEntry = entryFor(report.keep, "feature/current");
    expect(protectedEntry).toBeDefined();
    expect(protectedEntry?.reason).toBe("CURRENT_BRANCH");
    expect(names(report.batch)).not.toContain("feature/current");
    // Old needsReview semantics are gone: no review bucket can swallow it either.
    expect(Object.hasOwn(report, "needsReview")).toBe(false);
    expect(report.unanalyzed ?? []).toEqual([]);
  });

  test("protection filter: PROTECTED names, the default and linked-worktree-held branches never reach the batch", () => {
    const repo = fixtureRepo("protection filter", "main");
    // release/2026.09 is merged (would satisfy -d) and hotfix-1 is tree-identical
    // to main with no commits of its own beyond the fixture (would satisfy -D):
    // only the PROTECTED rule can be what keeps them out of the batch.
    git(["branch", "hotfix-1"], repo);
    git(["checkout", "-q", "-b", "release/2026.09"], repo);
    commit(repo, "rel.md", "release work");
    git(["checkout", "-q", "main"], repo);
    git(["merge", "-q", "--no-ff", "release/2026.09"], repo);
    git(["checkout", "-q", "-b", "feature/done"], repo);
    commit(repo, "done.md", "finished work");
    git(["checkout", "-q", "main"], repo);
    git(["merge", "-q", "--no-ff", "feature/done"], repo);
    // A branch held by a linked worktree whose removal never queues (dirty) is
    // never deletable: the worktree outlives the run.
    git(["branch", "feature/held"], repo);
    const heldPath = join(sandboxRoot, "wt-protection-held");
    git(["worktree", "add", "-q", heldPath, "feature/held"], repo);
    writeFileSync(join(heldPath, "uncommitted.md"), "work in progress\n");
    const report = analyze(repo);
    // The batch itself is reachable: a merged non-protected branch proves it.
    expect(names(report.batch)).toContain("feature/done");
    for (const branch of ["release/2026.09", "hotfix-1"]) {
      expect(entryFor(report.keep, branch)?.reason).toBe("PROTECTED");
      expect(names(report.batch)).not.toContain(branch);
    }
    expect(entryFor(report.keep, "main")?.reason).toBe("DEFAULT_BRANCH");
    expect(names(report.batch)).not.toContain("main");
    expect(names(report.batch)).not.toContain("feature/held");
  });

  test("tracked not-merged: a live upstream lands in KEEP with its exact reason, absent from the batch", () => {
    // Synced config: level with its live upstream.
    const syncedOrigin = join(sandboxRoot, "tracked-synced-origin.git");
    git(["init", "-q", "-b", "main", "--bare", syncedOrigin], sandboxRoot);
    const synced = fixtureRepo("tracked synced", "main");
    git(["remote", "add", "origin", syncedOrigin], synced);
    git(["checkout", "-q", "-b", "feature/synced"], synced);
    commit(synced, "s.md", "synced work");
    git(["push", "-q", "-u", "origin", "feature/synced"], synced);
    git(["push", "-q", "origin", "main"], synced);
    const syncedReport = analyze(synced);
    expect(entryFor(syncedReport.keep, "feature/synced")?.reason).toBe("SYNCED_WITH_REMOTE");
    expect(syncedReport.batch).toBeArray();
    expect(names(syncedReport.batch)).not.toContain("feature/synced");

    // Unpushed-ahead config: live upstream, one commit landed after the push.
    const wipOrigin = join(sandboxRoot, "tracked-wip-origin.git");
    git(["init", "-q", "-b", "main", "--bare", wipOrigin], sandboxRoot);
    const wip = fixtureRepo("tracked wip", "main");
    git(["remote", "add", "origin", wipOrigin], wip);
    git(["push", "-q", "origin", "main"], wip);
    git(["checkout", "-q", "-b", "feature/wip"], wip);
    commit(wip, "p.md", "pushed work");
    git(["push", "-q", "-u", "origin", "feature/wip"], wip);
    commit(wip, "wip.md", "unpushed work");
    const wipReport = analyze(wip);
    expect(entryFor(wipReport.keep, "feature/wip")?.reason).toBe("UNPUSHED_WORK");
    expect(wipReport.batch).toBeArray();
    expect(names(wipReport.batch)).not.toContain("feature/wip");
  });

  test("survey: one JSON document carries the migration, batch, keep, worktrees and report sections", () => {
    const repo = fixtureRepo("survey", "main");
    git(["checkout", "-q", "-b", "feature/merged"], repo);
    commit(repo, "a.md", "work");
    git(["checkout", "-q", "main"], repo);
    git(["merge", "-q", "--no-ff", "feature/merged"], repo);
    const report = analyze(repo);
    expect(Object.hasOwn(report, "fetchStatus")).toBe(true);
    expect(Object.hasOwn(report, "migration")).toBe(true);
    expect(Object.hasOwn(report, "batch")).toBe(true);
    expect(Object.hasOwn(report, "keep")).toBe(true);
    expect(Object.hasOwn(report, "worktrees")).toBe(true);
    expect(Object.hasOwn(report, "report")).toBe(true);
    // The inventory saw the merged branch: it is classified into the batch, not dropped.
    expect(names(report.batch)).toContain("feature/merged");
  });

  test("classification: a branch merged into default is batched as -d with category, evidence and guarded command", () => {
    const repo = fixtureRepo("merged into default", "main");
    git(["checkout", "-q", "-b", "feature/merged"], repo);
    commit(repo, "m.md", "merged work");
    git(["checkout", "-q", "main"], repo);
    git(["merge", "-q", "--no-ff", "feature/merged"], repo);
    const report = analyze(repo);
    const tip = gitOut(["rev-parse", "feature/merged"], repo).slice(0, 12);
    const entry = entryFor(report.batch, "feature/merged");
    expect(entry).toBeDefined();
    // Every field the one ask renders and executes (R1/R2/L13).
    expect(entry?.action).toBe("-d");
    expect(entry?.category).toBeString();
    expect(entry?.category).not.toBe("");
    expect(entry?.evidence).toContain(tip);
    expect(entry?.command).toBe(
      "git merge-base --is-ancestor 'refs/heads/feature/merged' 'main' && git branch -d 'feature/merged'",
    );
    expect(entry?.worktreePath).toBeUndefined();
  });

  test("classification: tree-identical branch with empty diff vs default is batched as -D", () => {
    const repo = fixtureRepo("empty diff vs default", "main");
    // A squash-style twin: feature/treesame commits once, main cherry-picks the same
    // change as a different sha. The branch is NOT on the merged list (not an
    // ancestor) but `git diff main..feature/treesame` is empty.
    git(["checkout", "-q", "-b", "feature/treesame"], repo);
    commit(repo, "t.md", "same content");
    git(["checkout", "-q", "main"], repo);
    // The pick must differ from the original: a same-second, same-message cherry-pick
    // re-creates the identical sha (same parent, tree, message, author/committer), which
    // would make feature/treesame an ancestor and hand the code the -d path. A distinct
    // message keeps the tip a different sha while the trees stay identical.
    git(["cherry-pick", "--no-commit", "feature/treesame"], repo);
    git(["commit", "-q", "-m", "pick: same content"], repo);
    const report = analyze(repo);
    expect(gitOut(["branch", "--merged", "main"], repo)).not.toContain("feature/treesame");
    const entry = entryFor(report.batch, "feature/treesame");
    expect(entry).toBeDefined();
    expect(entry?.action).toBe("-D");
    expect(entry?.evidence).toBe("empty diff vs default");
    expect(entry?.command).toBe("git branch -D 'feature/treesame'");
  });

  test("current branch: a tree-identical branch left checked out is CURRENT_BRANCH keep, never -D", () => {
    const repo = fixtureRepo("current empty diff", "main");
    // Same squash-twin premise as the -D case, but HEAD stays on the twin: only the
    // checked-out protection stands between this branch and the -D batch (R3/L18).
    git(["checkout", "-q", "-b", "feature/treesame"], repo);
    commit(repo, "t.md", "same content");
    git(["checkout", "-q", "main"], repo);
    git(["cherry-pick", "--no-commit", "feature/treesame"], repo);
    git(["commit", "-q", "-m", "pick: same content"], repo);
    git(["checkout", "-q", "feature/treesame"], repo);
    // Fixture premises proven against the real git state before asserting the
    // classification (L19): HEAD sits on the branch, it is not merged, diff is empty.
    expect(gitOut(["symbolic-ref", "--short", "HEAD"], repo)).toBe("feature/treesame");
    expect(gitOut(["branch", "--merged", "main"], repo)).not.toContain("feature/treesame");
    expect(
      spawnSync("git", ["diff", "--quiet", "main..feature/treesame"], { cwd: repo, encoding: "utf8", env: childEnv })
        .status,
    ).toBe(0);
    const report = analyze(repo);
    expect(entryFor(report.keep, "feature/treesame")?.reason).toBe("CURRENT_BRANCH");
    expect(report.batch).toBeArray();
    expect(names(report.batch)).not.toContain("feature/treesame");
    // No emitted command anywhere may target the checked-out branch (R1: exact contents).
    expect(commandStrings(report).some((command) => command.includes("feature/treesame"))).toBe(false);
  });

  // The double space in this title is deliberate: the plan's `-t 'gone + empty diff'`
  // filter compiles as a regex — "gone", one-or-more spaces, a literal space, then
  // "empty diff" — so a literal "+" in the title would match nothing.
  test("classification: gone  empty diff is batched as -D with the exact evidence", () => {
    const origin = join(sandboxRoot, "gone-empty-origin.git");
    git(["init", "-q", "-b", "main", "--bare", origin], sandboxRoot);
    const repo = fixtureRepo("gone empty", "main");
    git(["remote", "add", "origin", origin], repo);
    git(["push", "-q", "origin", "main"], repo);
    // Tree-identical but NOT an ancestor (main holds the same change under a
    // different sha), and the upstream disappears on the remote: the exact
    // [gone]-AND-empty-diff config. An empty commit would trip the machine's
    // pre-commit hook, so the twin comes from a cherry-pick like any staged change.
    git(["checkout", "-q", "-b", "feature/gone-empty"], repo);
    commit(repo, "t.md", "same content");
    git(["checkout", "-q", "main"], repo);
    // Same distinct-message pick as the tree-identical sibling: an identical-sha pick
    // would land feature/gone-empty on the merged list and yield -d instead of the
    // [gone] + empty diff -D this case pins.
    git(["cherry-pick", "--no-commit", "feature/gone-empty"], repo);
    git(["commit", "-q", "-m", "pick: same content"], repo);
    git(["push", "-q", "-u", "origin", "feature/gone-empty"], repo);
    git(["push", "origin", "--delete", "feature/gone-empty"], repo);
    const report = analyze(repo);
    const entry = entryFor(report.batch, "feature/gone-empty");
    expect(entry).toBeDefined();
    expect(entry?.action).toBe("-D");
    expect(entry?.evidence).toBe("[gone] + empty diff");
    expect(entry?.command).toBe("git branch -D 'feature/gone-empty'");
  });

  // Double space as in the sibling case: the plan's `-t 'gone + non-empty'` is a regex.
  test("classification: gone  non-empty diff lands in KEEP, never batched, never a command", () => {
    const origin = join(sandboxRoot, "gone-diff-origin.git");
    git(["init", "-q", "-b", "main", "--bare", origin], sandboxRoot);
    const repo = fixtureRepo("gone non-empty", "main");
    git(["remote", "add", "origin", origin], repo);
    git(["push", "-q", "origin", "main"], repo);
    // Unique work behind a [gone] upstream: work not proven merged → KEEP with its
    // reason surfaced in the report (old needsReview semantics are gone, R3).
    git(["checkout", "-q", "-b", "feature/pushed"], repo);
    commit(repo, "p.md", "pushed work");
    git(["push", "-q", "-u", "origin", "feature/pushed"], repo);
    git(["push", "origin", "--delete", "feature/pushed"], repo);
    // Return HEAD to main so the protection filter cannot swallow this case: the triage
    // path itself must produce REMOTE_GONE here (the CURRENT_BRANCH pin at the
    // protected-before-triage test covers the HEAD-on-feature configuration).
    git(["checkout", "-q", "main"], repo);
    const report = analyze(repo);
    expect(names(report.batch)).not.toContain("feature/pushed");
    const kept = entryFor(report.keep, "feature/pushed");
    expect(kept).toBeDefined();
    expect(kept?.reason).toBe("REMOTE_GONE");
    expect(Object.hasOwn(report, "needsReview")).toBe(false);
    const row = (report.report?.branches ?? []).find((candidate) => candidate.branch === "feature/pushed");
    expect(row?.reason).toBe("REMOTE_GONE");
    expect(row?.action).toBe("keep");
  });

  test("migration plan: current≠default pull pins the default branch as destination and the run stays read-only", () => {
    const repo = fixtureWithOrigin("migration plan");
    commit(repo, "b.md", "upstream work");
    commit(repo, "b2.md", "more upstream work");
    git(["push", "-q", "origin", "main"], repo);
    // Local tip rewinds: origin/main holds exactly the two commits this clone lacks,
    // and HEAD moves off main — the current≠default configuration where a pull
    // emitting HEAD or the current branch would mutate the wrong ref (R4/L17).
    git(["reset", "-q", "--hard", "HEAD~2"], repo);
    git(["checkout", "-q", "-b", "feature/migration"], repo);
    const before = {
      head: gitOut(["symbolic-ref", "--quiet", "--short", "HEAD"], repo),
      mainTip: gitOut(["rev-parse", "main"], repo),
      featureTip: gitOut(["rev-parse", "feature/migration"], repo),
      stashes: gitOut(["stash", "list"], repo),
    };
    const report = analyze(repo);
    expect(report.migration?.previousBranch).toBe("feature/migration");
    expect(report.migration?.defaultBranch).toBe("main");
    expect(report.migration?.switch?.command).toBe("git switch 'main'");
    // The exact pull: default ref name as destination — never HEAD, never the
    // current branch (the L17 bug: `git pull` merges into HEAD).
    expect(report.migration?.pull?.command).toBe("git pull --ff-only 'origin' 'main'");
    expect(report.migration?.pull?.command).not.toContain("HEAD");
    expect(report.migration?.pull?.command).not.toContain("feature/migration");
    // Read-only proof: the analyzer emitted the commands, it did not execute them.
    expect(gitOut(["symbolic-ref", "--quiet", "--short", "HEAD"], repo)).toBe(before.head);
    expect(gitOut(["rev-parse", "main"], repo)).toBe(before.mainTip);
    expect(gitOut(["rev-parse", "feature/migration"], repo)).toBe(before.featureTip);
    expect(gitOut(["stash", "list"], repo)).toBe(before.stashes);
    // The default stays report-only behind its upstream, exact against the fixture.
    const mainRow = (report.report?.branches ?? []).find((row) => row.branch === "main");
    expect(mainRow?.behind).toBe(2);
    expect(names(report.batch)).not.toContain("main");
  });

  test("stash: dirty worktree plans the auto-stash and pop steps, clean worktree emits neither", () => {
    // Dirty configuration: uncommitted work must be stashed before the switch and
    // popped after it, with the stash identity recorded (R3 exact configuration).
    const dirty = fixtureRepo("stash dirty", "main");
    writeFileSync(join(dirty, "uncommitted.md"), "work in progress\n");
    const dirtyReport = analyze(dirty);
    const stashCommand = dirtyReport.migration?.stash?.command;
    expect(stashCommand).toBeDefined();
    expect(stashCommand?.startsWith("git stash push -m cleanup-auto-stash-")).toBe(true);
    expect(dirtyReport.migration?.pop?.command).toBe("git stash pop");
    // The recorded stash state names the same stash the plan will create.
    expect(dirtyReport.report?.stashState).toBeString();
    expect(dirtyReport.report?.stashState?.startsWith("cleanup-auto-stash-")).toBe(true);
    expect(stashCommand).toContain(dirtyReport.report?.stashState ?? "");

    // Clean configuration: the absence half is proven, not vacuous — a real worktree
    // with nothing to stash emits no stash and no pop step at all.
    const clean = fixtureRepo("stash clean", "main");
    const cleanReport = analyze(clean);
    expect(cleanReport.report?.stashState).toBe("none");
    expect(Object.hasOwn(cleanReport.migration ?? {}, "stash")).toBe(false);
    expect(Object.hasOwn(cleanReport.migration ?? {}, "pop")).toBe(false);
    expect(commandStrings(cleanReport).some((command) => command.includes("stash"))).toBe(false);
  });

  test("WARN: the pull and pop steps carry on-failure annotations as emitted plan fields", () => {
    // Behind its upstream (pull step qualifies under either emission policy) and
    // dirty (pop step qualifies): both WARN annotations exist as data, not prose.
    const repo = fixtureWithOrigin("warn annotations");
    commit(repo, "b.md", "upstream work");
    git(["push", "-q", "origin", "main"], repo);
    git(["reset", "-q", "--hard", "HEAD~1"], repo);
    writeFileSync(join(repo, "uncommitted.md"), "work in progress\n");
    const report = analyze(repo);
    const pull = report.migration?.pull;
    expect(pull?.command).toBe("git pull --ff-only 'origin' 'main'");
    expect(pull?.warn).toBeString();
    expect(pull?.warn).toContain("WARN");
    const pop = report.migration?.pop;
    expect(pop?.command).toBe("git stash pop");
    expect(pop?.warn).toBeString();
    expect(pop?.warn).toContain("WARN");
    // The pop annotation is the stash-pop-conflict path: the stash is left in place.
    expect(pop?.warn?.toLowerCase()).toContain("stash");
  });

  test("one ask: a single batch object carries every field the ask renders, with no second confirmation source", () => {
    const repo = fixtureRepo("one ask", "main");
    git(["checkout", "-q", "-b", "feature/merged"], repo);
    commit(repo, "m.md", "merged work");
    git(["checkout", "-q", "main"], repo);
    git(["merge", "-q", "--no-ff", "feature/merged"], repo);
    git(["checkout", "-q", "-b", "feature/clean-wt"], repo);
    commit(repo, "c.md", "clean worktree work");
    git(["checkout", "-q", "main"], repo);
    git(["merge", "-q", "--no-ff", "feature/clean-wt"], repo);
    git(["worktree", "add", "-q", join(sandboxRoot, "wt-one-ask"), "feature/clean-wt"], repo);
    const report = analyze(repo);
    expect(report.fetchStatus).toBe("ok");
    expect(report.defaultBranch).toBe("main");
    // ONE batch container, not per-branch gates (R2).
    expect(Array.isArray(report.batch)).toBe(true);
    const batch = report.batch ?? [];
    expect(batch).toHaveLength(2);
    for (const entry of batch) {
      expect(entry?.branch).toBeString();
      expect(entry?.category).toBeString();
      expect(entry?.category).not.toBe("");
      expect(entry?.action).toBeString();
      expect(entry?.evidence).toBeString();
      expect(entry?.command).toBeString();
      expect(entry?.command).toContain("'");
    }
    // The worktree-held candidate names the worktree entry that must go first (L14).
    expect(entryFor(batch, "feature/clean-wt")?.worktreePath).toBeString();
    expect(entryFor(batch, "feature/merged")?.worktreePath).toBeUndefined();
    // Everything the ask renders comes from this one document: no second
    // confirmation source anywhere in the structure.
    const confirmationKeys = deepPairs(report).filter(([key]) => /confirm|^ask$|gate/i.test(key));
    expect(confirmationKeys).toEqual([]);
    expect(report.keep).toBeDefined();
    expect(report.report?.branches).toBeDefined();
  });

  test("worktree: dirty never queues, stale queues the exact remove, and prune exists only when a removal queues", () => {
    const repo = fixtureRepo("worktree", "main");
    git(["checkout", "-q", "-b", "feature/clean-wt"], repo);
    commit(repo, "c.md", "merged work");
    git(["checkout", "-q", "main"], repo);
    git(["merge", "-q", "--no-ff", "feature/clean-wt"], repo);
    // L10: create the branch without checking it out — git refuses to hold the same
    // branch in two worktrees.
    git(["branch", "feature/dirty-wt"], repo);
    const cleanPath = join(sandboxRoot, "wt-clean");
    const dirtyPath = join(sandboxRoot, "wt-dirty");
    git(["worktree", "add", "-q", cleanPath, "feature/clean-wt"], repo);
    git(["worktree", "add", "-q", dirtyPath, "feature/dirty-wt"], repo);
    writeFileSync(join(dirtyPath, "uncommitted.md"), "work in progress\n");
    const report = analyze(repo);
    const dirty = (report.worktrees ?? []).find((wt) => wt.branch === "feature/dirty-wt");
    expect(dirty).toBeDefined();
    expect(dirty?.dirty).toBe(true);
    expect(dirty?.stale).not.toBe(true);
    expect(dirty?.command).toBeUndefined();
    // The dirty worktree carries the explicit data-loss-acknowledgment flag and
    // never queues a removal — its branch is not deletable while it is held.
    expect(dirty?.requiresAcknowledgment).toBe(true);
    expect(names(report.batch)).not.toContain("feature/dirty-wt");

    // Stale only when the worktree is clean and its branch is deletable; the removal
    // command is exact and single-quoted (R1/L13).
    const clean = (report.worktrees ?? []).find((wt) => wt.branch === "feature/clean-wt");
    expect(clean).toBeDefined();
    expect(clean?.dirty).toBe(false);
    expect(clean?.stale).toBe(true);
    expect(clean?.command).toBe(`git worktree remove '${cleanPath}'`);

    // Back-link (L14): the batch candidate names the worktree entry's path, so the
    // ask can order the removal before the branch delete.
    expect(entryFor(report.batch, "feature/clean-wt")?.worktreePath).toBe(clean?.path);

    // Post-cleanup: a removal IS queued → the exact prune command exists, in the
    // postCleanup section and nowhere else.
    expect(Object.hasOwn(report, "postCleanup")).toBe(true);
    expect(report.postCleanup?.prune).toBe("git worktree prune");
    const pruneCommands = commandStrings(report).filter((command) => command.includes("worktree prune"));
    expect(pruneCommands).toEqual(["git worktree prune"]);

    // Absence half (R3): no queued removal → no prune command anywhere.
    const refusedRepo = fixtureRepo("worktree refused", "main");
    git(["branch", "feature/wip-wt"], refusedRepo);
    const refusedPath = join(sandboxRoot, "wt-refused");
    git(["worktree", "add", "-q", refusedPath, "feature/wip-wt"], refusedRepo);
    writeFileSync(join(refusedPath, "uncommitted.md"), "work in progress\n");
    const refused = analyze(refusedRepo);
    const held = (refused.worktrees ?? []).find((wt) => wt.branch === "feature/wip-wt");
    expect(held?.dirty).toBe(true);
    expect(held?.command).toBeUndefined();
    expect(commandStrings(refused).some((command) => command.includes("worktree prune"))).toBe(false);
    expect(names(refused.batch)).not.toContain("feature/wip-wt");
  });

  test("report: per-branch rows are inventory-complete with action, reason, upstream and ahead-behind", () => {
    const repo = fixtureRepo("report", "main");
    const origin = join(sandboxRoot, "report-origin.git");
    git(["init", "-q", "-b", "main", "--bare", origin], sandboxRoot);
    git(["remote", "add", "origin", origin], repo);
    git(["push", "-q", "-u", "origin", "main"], repo);
    git(["checkout", "-q", "-b", "feature/merged"], repo);
    commit(repo, "m.md", "merged work");
    git(["checkout", "-q", "main"], repo);
    git(["merge", "-q", "--no-ff", "feature/merged"], repo);
    git(["checkout", "-q", "-b", "feature/local"], repo);
    commit(repo, "l.md", "local work");
    git(["checkout", "-q", "main"], repo);
    // The --no-ff merge carried 2 commits and 2 more land locally without a push:
    // the default is ahead 4 (rev-list origin/main..main), report-only.
    commit(repo, "ahead.md", "local ahead work");
    commit(repo, "ahead2.md", "more local ahead work");
    const report = analyze(repo);
    const rows = report.report?.branches ?? [];
    const branchCount = gitOut(["for-each-ref", "--format=%(refname:short)", "refs/heads"], repo)
      .split("\n")
      .filter(Boolean).length;
    // Inventory-complete (L11): row count equals branch count, no bucket silently unfilled.
    expect(rows).toHaveLength(branchCount);
    for (const row of rows) {
      expect(Object.hasOwn(row, "action")).toBe(true);
      expect(Object.hasOwn(row, "reason")).toBe(true);
      expect(Object.hasOwn(row, "upstream")).toBe(true);
      expect(Object.hasOwn(row, "ahead")).toBe(true);
      expect(Object.hasOwn(row, "behind")).toBe(true);
    }
    // The default's ahead/behind counts are report data, exact against the fixture.
    const mainRow = rows.find((row) => row.branch === "main");
    expect(mainRow?.upstream).toBe("origin/main");
    expect(mainRow?.ahead).toBe(4);
    expect(mainRow?.behind).toBe(0);
    expect(mainRow?.action).toBe("keep");
    const mergedRow = rows.find((row) => row.branch === "feature/merged");
    expect(mergedRow?.action).toBe("-d");
    const localRow = rows.find((row) => row.branch === "feature/local");
    expect(localRow?.action).toBe("keep");
    expect(localRow?.reason).toBe("LOCAL_WORK");
    // The recorded pre-migration (previous) branch travels in the report too.
    expect(report.report?.previousBranch).toBe("main");
    // Report-only: no command anywhere may push, in this exact config.
    expect(commandStrings(report).some((command) => command.includes("push"))).toBe(false);
  });

  test("push: no command field anywhere contains push, with ahead default, queued deletions and migration in one document", () => {
    const repo = fixtureWithOrigin("no push");
    // Default ahead of its upstream: the config where a push could hide.
    commit(repo, "ahead.md", "local ahead work");
    commit(repo, "ahead2.md", "more local ahead work");
    git(["checkout", "-q", "-b", "feature/merged"], repo);
    commit(repo, "m.md", "merged work");
    git(["checkout", "-q", "main"], repo);
    git(["merge", "-q", "--no-ff", "feature/merged"], repo);
    const report = analyze(repo);
    // Non-vacuous: migration and queued deletions really are in this document.
    expect(report.migration?.switch?.command).toBe("git switch 'main'");
    const batch = report.batch ?? [];
    expect(batch.length).toBeGreaterThan(0);
    const commands = commandStrings(report);
    expect(commands.length).toBeGreaterThan(0);
    // The invariant holds over every command-bearing field (R3).
    expect(commands.filter((command) => command.includes("push"))).toEqual([]);
  });

  test("default branch: origin/HEAD normalizes a non-standard default that is never deletable", () => {
    const repo = fixtureRepo("default branch mainline", "mainline");
    // A non-standard default name is only provable through origin/HEAD; without
    // that anchor the analyzer must fail closed rather than guess from HEAD.
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
    expect(report.migration?.defaultBranch).toBe("mainline");
    expect(names(report.batch)).toContain("feature/done");
    expect(names(report.batch)).not.toContain("mainline");
    expect(entryFor(report.keep, "mainline")?.reason).toBe("DEFAULT_BRANCH");
  });

  test("broken inventory: a malformed ref inventory fails closed — empty batch, uncertainty surfaced as KEEP", () => {
    const repo = fixtureRepo("broken inventory", "main");
    git(["checkout", "-q", "-b", "feature/x"], repo);
    commit(repo, "x.md", "work");
    git(["checkout", "-q", "main"], repo);
    // A ref that is not a SHA breaks the inventory survey mid-read: git warns and
    // keeps going, so the run must still emit one JSON document (exit 0) with every
    // branch in KEEP and nothing deletable (R1/R3).
    writeFileSync(join(repo, ".git", "refs", "heads", "broken"), "not-a-sha\n");
    const report = analyze(repo);
    expect(report.batch).toEqual([]);
    for (const branch of ["main", "feature/x"]) {
      expect(entryFor(report.keep, branch)?.reason).toBe("INVENTORY_INCOMPLETE");
    }
    // The broken ref itself is surfaced, never silently dropped.
    const broken = [...(report.keep ?? []), ...(report.unanalyzed ?? [])].find((entry) => entry.branch === "broken");
    expect(broken?.reason).toBe("BROKEN_REF");
    expect(names(report.batch)).not.toContain("broken");
  });

  test("unanalyzed: the bucket is present even when every branch classifies", () => {
    const repo = fixtureRepo("unanalyzed", "main");
    git(["branch", "feature/only"], repo);
    const report = analyze(repo);
    expect(report.unanalyzed).toBeArray();
    expect(report.unanalyzed).toHaveLength(0);
    // feature/only sits on main with no extra work: it classifies into the batch.
    expect(names(report.batch)).toContain("feature/only");
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
    expect(report.batch).toEqual([]);
    expect(entryFor(report.keep, "feature/local")?.reason).toBe("LOCAL_WORK");
  });
});