// tests/git-cleanup-flow.spec.ts — unit layer of the ai-git-cleanup test plan (checkpoint 2):
// one fixture repository run end to end through analyze.mjs, asserting the WHOLE emitted
// plan in its v3 shape (U18-U21): phase 0's pull pinned to the default in a current≠default
// fixture, the ONE batch array that is the single ask's payload with the phase sections in
// phase order, worktree-removal-before-branch-delete pairing with the back-link, dirty
// refusal outranking ordering, protection-before-triage in the document, the no-push scan,
// and the always-present unanalyzed bucket. The script builds its own survey from git
// plumbing, so the fixture is the spec. SKILL.md prose is asserted nowhere here (R1):
// structure gates cover the document, wording covers the review gate.
// GIT_CONFIG_GLOBAL points at an empty file so the machine's ~/.gitconfig cannot decide
// what any child git does; remotes are local paths, so nothing here touches a network.

import { afterAll, describe, expect, test } from "bun:test";
import { spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const script = join(import.meta.dir, "..", "skills", "ai-git-cleanup", "scripts", "analyze.mjs");
const sandboxRoot = mkdtempSync(join(tmpdir(), "ai-eng-git-cleanup-flow-"));
const emptyGitConfig = join(sandboxRoot, "empty-gitconfig");
writeFileSync(emptyGitConfig, "");

const childEnv: NodeJS.ProcessEnv = {
  ...process.env,
  GIT_CONFIG_GLOBAL: emptyGitConfig,
  GIT_TERMINAL_PROMPT: "0",
};

interface BatchEntry {
  branch?: string;
  action?: string;
  category?: string;
  evidence?: string;
  command?: string;
  worktreePath?: string;
}

interface KeepEntry {
  branch?: string;
  reason?: string;
  evidence?: string;
}

interface WorktreeEntry {
  path?: string;
  branch?: string;
  dirty?: boolean;
  dirtyFiles?: string[];
  requiresAcknowledgment?: boolean;
  stale?: boolean;
  command?: string;
}

interface MigrationStep {
  command?: string;
  warn?: string;
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
  migration?: {
    previousBranch?: string;
    defaultBranch?: string;
    stash?: MigrationStep;
    switch?: MigrationStep;
    pull?: MigrationStep;
    pop?: MigrationStep;
  };
  batch?: BatchEntry[];
  keep?: KeepEntry[];
  unanalyzed?: KeepEntry[];
  worktrees?: WorktreeEntry[];
  postCleanup?: { prune?: string };
  report?: {
    previousBranch?: string;
    stashState?: string;
    branches?: ReportRow[];
  };
}

// Every branch the fixture creates; the unanalyzed case proves each lands somewhere.
const fixtureBranches = [
  "main",
  "develop",
  "release/2026.09",
  "feature/merged",
  "feature/squashed",
  "feature/gone",
  "feature/unpushed",
  "feature/clean-wt",
  "feature/dirty-wt",
];

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

// Every key/value pair in the document at any depth, so conditional-field checks hold
// wherever a section lands (R2). Primitive leaves are returned once by their own frame —
// pushing them here too would double-count every string leaf (L19).
function deepPairs(value: unknown, key = ""): [string, unknown][] {
  if (Array.isArray(value)) return value.flatMap((item) => deepPairs(item, key));
  if (value !== null && typeof value === "object") {
    const pairs: [string, unknown][] = [];
    for (const [childKey, child] of Object.entries(value)) {
      if (child !== null && typeof child === "object") pairs.push([childKey, child]);
      pairs.push(...deepPairs(child, childKey));
    }
    return pairs;
  }
  return [[key, value]];
}

// Command-bearing fields: values under a command key plus any string a shell could
// execute. The migration, batch, worktree and postCleanup commands qualify wherever
// they live, so no section rename can hide a command from the invariant scans (R3).
function commandStrings(value: unknown): string[] {
  return deepPairs(value).flatMap(([key, entry]) =>
    typeof entry === "string" && (key.includes("command") || entry.startsWith("git ")) ? [entry] : [],
  );
}

function runAnalyze(repo: string): { stdout: string; report: Report } {
  const done = spawnSync(process.execPath, [script, repo], {
    cwd: sandboxRoot,
    encoding: "utf8",
    env: childEnv,
  });
  if (done.status !== 0) {
    throw new Error(`analyze.mjs failed (${done.status}): ${done.stderr}\n${done.stdout}`);
  }
  // JSON.parse doubles as the "one document" check: stray output fails to parse.
  return { stdout: done.stdout, report: JSON.parse(done.stdout) as Report };
}

// One fixture, one spawn, shared read-only by the four cases: each asserts a different
// slice of the same emitted plan. Raw stdout is kept so document-level claims (keys that
// must surface, strings that must never appear) run against what the script printed.
let cached: { stdout: string; report: Report } | null = null;
let buildError: Error | null = null;

function flow(): { stdout: string; report: Report } {
  if (cached) return cached;
  // A half-built fixture must not rebuild on the next case: re-running would hit
  // "remote already exists" and mask the original failure behind a second one.
  if (buildError) throw buildError;
  try {
    cached = buildFixture();
    return cached;
  } catch (error) {
    buildError = error instanceof Error ? error : new Error(String(error));
    throw buildError;
  }
}

function buildFixture(): { stdout: string; report: Report } {
  const repo = join(sandboxRoot, "repo");
  mkdirSync(repo, { recursive: true });
  git(["init", "-q", "-b", "main"], repo);
  git(["config", "user.name", "Ada Lovelace"], repo);
  git(["config", "user.email", "ada@example.com"], repo);
  git(["config", "commit.gpgsign", "false"], repo);
  commit(repo, "notes.md", "# flow fixture\n");
  const origin = join(sandboxRoot, "origin.git");
  git(["init", "-q", "-b", "main", "--bare", origin], sandboxRoot);
  git(["remote", "add", "origin", origin], repo);
  git(["push", "-q", "origin", "main"], repo);

  // Merged into main: the canonical -d delete, guarded by the merge-base check.
  git(["checkout", "-q", "-b", "feature/merged"], repo);
  commit(repo, "m.md", "merged work");
  git(["checkout", "-q", "main"], repo);
  git(["merge", "-q", "--no-ff", "feature/merged"], repo);

  // Squash twin with unique work: main took the same change under a different sha,
  // this branch still holds a commit main lacks — must stay KEEP, never a command.
  git(["checkout", "-q", "-b", "feature/squashed"], repo);
  commit(repo, "s.md", "squashed work");
  git(["checkout", "-q", "main"], repo);
  git(["merge", "-q", "--squash", "feature/squashed"], repo);
  git(["commit", "-q", "-m", "squash s.md"], repo);

  // Pushed then deleted on the remote: [gone] upstream with unmerged work → KEEP.
  git(["checkout", "-q", "-b", "feature/gone"], repo);
  commit(repo, "g.md", "gone work");
  git(["push", "-q", "-u", "origin", "feature/gone"], repo);
  git(["push", "-q", "origin", "--delete", "feature/gone"], repo);
  git(["checkout", "-q", "main"], repo);

  // Unpushed: one commit landed after the push → KEEP.
  git(["checkout", "-q", "-b", "feature/unpushed"], repo);
  commit(repo, "u.md", "pushed work");
  git(["push", "-q", "-u", "origin", "feature/unpushed"], repo);
  commit(repo, "u2.md", "unpushed work");
  git(["checkout", "-q", "main"], repo);

  // Worktree branches are created without being checked out here — git never allows
  // one branch in two worktrees. feature/clean-wt reaches the batch as the tree-identical
  // shape: main independently gains the same content under a different sha, so the
  // branch is NOT on the merged list while holding nothing the default lacks (-D).
  git(["branch", "develop"], repo);
  git(["branch", "release/2026.09"], repo);
  git(["branch", "feature/dirty-wt"], repo);
  git(["checkout", "-q", "-b", "feature/clean-wt"], repo);
  commit(repo, "c.md", "clean worktree work");
  git(["checkout", "-q", "main"], repo);
  // Same content, distinct commit: an identical parent+message+content would collapse
  // to the same sha and put the branch back on the merged list.
  writeFileSync(join(repo, "c.md"), "clean worktree work");
  git(["add", "-A"], repo);
  git(["commit", "-q", "-m", "c.md landed on main independently"], repo);
  const cleanPath = join(sandboxRoot, "wt-clean");
  const dirtyPath = join(sandboxRoot, "wt-dirty");
  git(["worktree", "add", "-q", cleanPath, "feature/clean-wt"], repo);
  git(["worktree", "add", "-q", dirtyPath, "feature/dirty-wt"], repo);
  // Uncommitted change: this worktree must be refused, never queued for removal.
  writeFileSync(join(dirtyPath, "uncommitted.md"), "work in progress\n");

  // The fixture proves its own premises before analyze runs (L19): each delete shape
  // and each refusal depends on a git state the assertions below rely on.
  const premises: [string[], number, string][] = [
    [["merge-base", "--is-ancestor", "feature/merged", "main"], 0, "feature/merged is merged into main (-d)"],
    [["merge-base", "--is-ancestor", "feature/squashed", "main"], 1, "feature/squashed is not on the merged list"],
    [["diff", "--quiet", "main..feature/squashed"], 1, "feature/squashed diverges from main (unique work, KEEP)"],
    [["merge-base", "--is-ancestor", "feature/clean-wt", "main"], 1, "feature/clean-wt is not on the merged list"],
    [["diff", "--quiet", "main..feature/clean-wt"], 0, "feature/clean-wt is tree-identical to main (-D)"],
    [["status", "--porcelain"], 0, "the dirty worktree has the uncommitted file"],
  ];
  for (const [args, status, why] of premises) {
    const cwd = args[0] === "status" ? dirtyPath : repo;
    const done = spawnSync("git", args, { cwd, encoding: "utf8", env: childEnv });
    if (done.status !== status) {
      throw new Error(`fixture premise failed (${why}): git ${args.join(" ")} exited ${done.status}`);
    }
  }

  return runAnalyze(repo);
}

describe("analyze.mjs flow fixture", () => {
  test("phase 0: in a current≠default fixture the pull names the default branch as destination and the run stays read-only", () => {
    // Own fixture (U18): the default is behind its upstream and HEAD sits on a
    // feature branch — the exact configuration where a pull emitting HEAD or the
    // current branch would mutate the wrong ref (R4/L17).
    const repo = join(sandboxRoot, "phase0-repo");
    mkdirSync(repo, { recursive: true });
    git(["init", "-q", "-b", "main"], repo);
    git(["config", "user.name", "Ada Lovelace"], repo);
    git(["config", "user.email", "ada@example.com"], repo);
    git(["config", "commit.gpgsign", "false"], repo);
    commit(repo, "notes.md", "# phase 0 fixture\n");
    const origin = join(sandboxRoot, "phase0-origin.git");
    git(["init", "-q", "-b", "main", "--bare", origin], sandboxRoot);
    git(["remote", "add", "origin", origin], repo);
    git(["push", "-q", "-u", "origin", "main"], repo);
    commit(repo, "b.md", "upstream work");
    commit(repo, "b2.md", "more upstream work");
    git(["push", "-q", "origin", "main"], repo);
    // Local tip rewinds: origin/main holds exactly the two commits this clone lacks,
    // and HEAD moves off main — the current≠default configuration.
    git(["reset", "-q", "--hard", "HEAD~2"], repo);
    git(["checkout", "-q", "-b", "feature/topic"], repo);
    const before = {
      head: gitOut(["symbolic-ref", "--quiet", "--short", "HEAD"], repo),
      headSha: gitOut(["rev-parse", "HEAD"], repo),
      mainSha: gitOut(["rev-parse", "main"], repo),
      heads: gitOut(["for-each-ref", "--format=%(refname) %(objectname)", "refs/heads"], repo),
      stashes: gitOut(["stash", "list"], repo),
      status: gitOut(["status", "--porcelain"], repo),
    };

    const { stdout, report } = runAnalyze(repo);
    expect(report.defaultBranch).toBe("main");
    // Premises proved from the document itself: current ≠ default, and the default
    // really is behind its upstream (the pull's only justification).
    expect(report.report?.previousBranch).toBe("feature/topic");
    const mainRow = (report.report?.branches ?? []).find((row) => row.branch === "main");
    expect(mainRow?.behind).toBe(2);
    expect(report.migration?.previousBranch).toBe("feature/topic");
    expect(report.migration?.defaultBranch).toBe("main");
    expect(report.migration?.switch?.command).toBe("git switch 'main'");
    // The exact pull: default ref name as destination — never HEAD, never the
    // current branch (the L17 bug: `git pull` merges into HEAD).
    const pull = report.migration?.pull?.command;
    expect(pull).toBe("git pull --ff-only 'origin' 'main'");
    expect(pull).not.toContain("HEAD");
    expect(pull).not.toContain("feature/topic");
    // Read-only proof: the analyzer emitted the commands, it did not execute them.
    expect(gitOut(["symbolic-ref", "--quiet", "--short", "HEAD"], repo)).toBe(before.head);
    expect(gitOut(["rev-parse", "HEAD"], repo)).toBe(before.headSha);
    expect(gitOut(["rev-parse", "main"], repo)).toBe(before.mainSha);
    expect(gitOut(["for-each-ref", "--format=%(refname) %(objectname)", "refs/heads"], repo)).toBe(before.heads);
    expect(gitOut(["stash", "list"], repo)).toBe(before.stashes);
    expect(gitOut(["status", "--porcelain"], repo)).toBe(before.status);
    expect(stdout).toContain('"migration"');
  });

  test("refusals: the dirty worktree is refused, every queued removal pairs with its branch delete, and protection runs before triage", () => {
    const { stdout, report } = flow();
    // Premises of this document: default and pre-migration current branch are main,
    // and the fetch banner surfaced in the same emitted plan as the pairing data.
    expect(report.defaultBranch).toBe("main");
    expect(report.report?.previousBranch).toBe("main");
    expect(Object.hasOwn(report, "fetchStatus")).toBe(true);
    expect(report.fetchStatus).toBe("ok");
    expect(stdout).toContain('"fetchStatus"');

    const batch = report.batch ?? [];
    const worktrees = report.worktrees ?? [];
    // Protection before triage (R3): the batch holds exactly the two deletable
    // branches — no default, no PROTECTED name, no dirty-worktree-held branch.
    expect(names(batch).sort()).toEqual(["feature/clean-wt", "feature/merged"]);
    const protection: Record<string, string> = {
      main: "DEFAULT_BRANCH",
      develop: "PROTECTED",
      "release/2026.09": "PROTECTED",
    };
    for (const [branch, reason] of Object.entries(protection)) {
      expect(names(batch)).not.toContain(branch);
      expect(entryFor(report.keep, branch)?.reason).toBe(reason);
    }
    // A KEEP entry never carries a command: only the batch does.
    for (const entry of report.keep ?? []) {
      expect(entry.reason).toBeString();
      expect((entry as BatchEntry).command).toBeUndefined();
    }

    // Dirty worktree: refused outright — the data-loss acknowledgment flag is set,
    // nothing queues, and its branch drops to KEEP even though it sits on main's tip
    // (the refusal outranks the ordering).
    const dirty = worktrees.find((worktree) => worktree.branch === "feature/dirty-wt");
    expect(dirty).toBeDefined();
    expect(dirty?.dirty).toBe(true);
    expect(dirty?.dirtyFiles?.join("\n")).toContain("uncommitted.md");
    expect(dirty?.requiresAcknowledgment).toBe(true);
    expect(dirty?.stale).not.toBe(true);
    expect(dirty?.command).toBeUndefined();
    expect(entryFor(report.keep, "feature/dirty-wt")?.reason).toBe("WORKTREE_HELD");

    // Clean linked worktree: queued, with an exactly quoted path.
    const clean = worktrees.find((worktree) => worktree.branch === "feature/clean-wt");
    expect(clean).toBeDefined();
    expect(clean?.dirty).toBe(false);
    expect(clean?.stale).toBe(true);
    expect(clean?.command).toBe(`git worktree remove '${clean?.path}'`);

    // Ordering data the ask executes (L14): every queued removal belongs to a branch
    // the plan will delete, and the candidate points back at the holding worktree —
    // so removals always run before their branch delete. Conversely every batched
    // branch held by a worktree has its removal queued, and a dirty hold never queues.
    for (const worktree of worktrees.filter((entry) => entry.command)) {
      const candidate = entryFor(batch, worktree.branch ?? "");
      expect(candidate).toBeDefined();
      expect(candidate?.worktreePath).toBe(worktree.path);
      const expected =
        candidate?.action === "-d"
          ? `git merge-base --is-ancestor 'refs/heads/${worktree.branch}' 'main' && git branch -d '${worktree.branch}'`
          : `git branch -D '${worktree.branch}'`;
      expect(candidate?.command).toBe(expected);
    }
    for (const candidate of batch) {
      if (!candidate.worktreePath) continue;
      const held = worktrees.find((worktree) => worktree.path === candidate.worktreePath);
      expect(held).toBeDefined();
      if (!held) throw new Error(`worktree entry missing for ${candidate.worktreePath}`);
      if (held.dirty) {
        expect(held.command).toBeUndefined();
      } else {
        expect(held.command).toBe(`git worktree remove '${held.path}'`);
      }
    }
    // Post-cleanup joins the same document (kept claim): a removal IS queued here, so
    // the exact prune command must be present.
    expect(Object.hasOwn(report, "postCleanup")).toBe(true);
    expect(report.postCleanup?.prune).toBe("git worktree prune");
    expect(commandStrings(report).filter((command) => command.includes("worktree prune"))).toEqual([
      "git worktree prune",
    ]);
  });

  test("one ask: exactly one batch array carries every delete command, with the phase sections in phase order", () => {
    const { stdout, report } = flow();
    // The ONE batch: a single array, not per-branch gates — everything the one ask
    // renders and executes comes from it.
    expect(Array.isArray(report.batch)).toBe(true);
    const batch = report.batch ?? [];
    expect(batch.length).toBeGreaterThan(0);
    // No second confirmation source: every branch-delete command anywhere in the
    // document lives inside that one array, one per entry (R2).
    const deleteCommands = commandStrings(report).filter((command) => /git branch -[dD] /.test(command));
    expect(deleteCommands.sort()).toEqual(batch.map((entry) => entry.command ?? "").sort());
    // Phase 0 is ask-free because it is reversible: its section carries no
    // destructive command of any kind.
    expect(commandStrings(report.migration).filter((command) => /git branch -[dD]/.test(command))).toEqual([]);
    // One ask's worth of data: every entry carries the branch, category, action,
    // evidence, and the exact single-quoted command — the merge-base guard bundled
    // into the -d command (R4), a plain -D for the tree-identical shape.
    for (const entry of batch) {
      expect(entry.branch).toBeString();
      expect(entry.category).toBeString();
      expect(entry.action).toMatch(/^-d$|^-D$/);
      expect(entry.evidence).toBeString();
      expect(entry.evidence).not.toBe("");
      if (entry.action === "-d") {
        expect(entry.command).toBe(
          `git merge-base --is-ancestor 'refs/heads/${entry.branch}' 'main' && git branch -d '${entry.branch}'`,
        );
      } else {
        expect(entry.command).toBe(`git branch -D '${entry.branch}'`);
      }
      if (entry.worktreePath) {
        const held = (report.worktrees ?? []).find((worktree) => worktree.path === entry.worktreePath);
        expect(held?.branch).toBe(entry.branch);
      }
    }
    // Phase data arrives in phase order: migration (phase 0) before the batch
    // (phase 2) before the report (phase 3) — the document encodes the flow order
    // in its top-level key order.
    const keys = Object.keys(report);
    expect(keys.indexOf("migration")).toBeGreaterThanOrEqual(0);
    expect(keys.indexOf("migration")).toBeLessThan(keys.indexOf("batch"));
    expect(keys.indexOf("batch")).toBeLessThan(keys.indexOf("report"));
    expect(stdout).toContain('"batch"');
    expect(stdout).toContain('"report"');
  });

  test("push: no command field anywhere in the emitted document contains push", () => {
    const { stdout, report } = flow();
    // The scan is non-vacuous: the document really carries commands to scan.
    const commands = commandStrings(report);
    expect(commands.length).toBeGreaterThan(0);
    expect(commands.filter((command) => command.includes("push"))).toEqual([]);
    // Command-shaped push never surfaces in the printed document either; the bare
    // word "push" only appears inside branch names like feature/unpushed.
    expect(stdout).not.toContain("git push");
    expect(stdout).not.toContain("push --delete");
  });

  test("unanalyzed: the bucket always surfaces in the emitted plan and every fixture branch is accounted for", () => {
    const { stdout, report } = flow();
    // Presence in the printed document: JSON.parse drops absent keys, so own-property
    // on the parsed object plus the raw key both come from what the script emitted.
    expect(Object.hasOwn(report, "unanalyzed")).toBe(true);
    expect(stdout).toContain('"unanalyzed"');
    // Contents, not type (L11): this fixture classifies every branch, so empty is the
    // expected content — and it is only truthful if the accounting below holds.
    expect(report.unanalyzed).toEqual([]);
    const classified = [
      ...names(report.batch),
      ...names(report.keep),
      ...names(report.unanalyzed),
    ].sort();
    expect(classified).toEqual([...fixtureBranches].sort());
  });

  test("report: the run ends with default and previous branch, stash state and a complete row for every branch", () => {
    const { stdout, report } = flow();
    // Contract head: the default and the pre-migration branch the report names back.
    expect(report.defaultBranch).toBe("main");
    expect(Object.hasOwn(report, "report")).toBe(true);
    expect(stdout).toContain('"report"');
    const doc = report.report;
    expect(doc).toBeDefined();
    expect(doc?.previousBranch).toBe("main");
    // Fixture premise: the main worktree is clean, so this run plans no auto-stash —
    // and the report says exactly that instead of a fabricated stash name.
    expect(report.migration?.stash).toBeUndefined();
    expect(doc?.stashState).toBe("none");

    // One row per branch, every field asserted, nothing extra on the row (R2):
    // action (-d/-D/keep), reason, upstream, ahead, behind — exact fixture truth.
    const rows = doc?.branches ?? [];
    expect(rows.map((row) => row.branch).sort()).toEqual([...fixtureBranches].sort());
    const expected: Record<
      string,
      { action: string; reason: string; upstream: string; ahead: number | null; behind: number | null }
    > = {
      main: { action: "keep", reason: "DEFAULT_BRANCH", upstream: "", ahead: null, behind: null },
      develop: { action: "keep", reason: "PROTECTED", upstream: "", ahead: null, behind: null },
      "release/2026.09": { action: "keep", reason: "PROTECTED", upstream: "", ahead: null, behind: null },
      "feature/merged": { action: "-d", reason: "MERGED", upstream: "", ahead: null, behind: null },
      "feature/squashed": { action: "keep", reason: "LOCAL_WORK", upstream: "", ahead: null, behind: null },
      "feature/gone": {
        action: "keep",
        reason: "REMOTE_GONE",
        upstream: "origin/feature/gone",
        ahead: null,
        behind: null,
      },
      "feature/unpushed": {
        action: "keep",
        reason: "UNPUSHED_WORK",
        upstream: "origin/feature/unpushed",
        ahead: 1,
        behind: 0,
      },
      "feature/clean-wt": { action: "-D", reason: "EMPTY_DIFF", upstream: "", ahead: null, behind: null },
      "feature/dirty-wt": { action: "keep", reason: "WORKTREE_HELD", upstream: "", ahead: null, behind: null },
    };
    expect(Object.keys(expected).sort()).toEqual([...fixtureBranches].sort());
    for (const row of rows) {
      expect(row).toEqual({ branch: row.branch, ...expected[row.branch] });
    }

    // Decision linkage (refusal/skip visibility): every bucketed branch's row carries
    // the same decision the batch/keep/unanalyzed entry carries — a refused delete
    // (the dirty worktree) surfaces as keep+reason in the report, never a silent drop.
    for (const entry of report.keep ?? []) {
      const row = rows.find((candidate) => candidate.branch === entry.branch);
      expect(row?.action).toBe("keep");
      expect(row?.reason).toBe(entry.reason);
    }
    for (const entry of report.unanalyzed ?? []) {
      const row = rows.find((candidate) => candidate.branch === entry.branch);
      expect(row?.action).toBe("keep");
      expect(row?.reason).toBe(entry.reason);
    }
    for (const entry of report.batch ?? []) {
      const row = rows.find((candidate) => candidate.branch === entry.branch);
      expect(row?.action).toBe(entry.action);
      expect(row?.reason).toBe(entry.category);
    }
    expect(rows.find((row) => row.branch === "feature/dirty-wt")?.reason).toBe("WORKTREE_HELD");
    // Ahead is report-only: the count lands in the row, no command anywhere acts on it.
    expect(rows.find((row) => row.branch === "feature/unpushed")?.ahead).toBe(1);
    expect(commandStrings(report).filter((command) => command.includes("push"))).toEqual([]);

    // Stash-state identity in the exact configuration that has one: with a dirty main
    // worktree the plan carries a stash step, and stashState names THAT stash — the
    // name phase 3 reads back off `git stash list` (R2 linkage, not a constant).
    const stashRepo = join(sandboxRoot, "report-stash-repo");
    mkdirSync(stashRepo, { recursive: true });
    git(["init", "-q", "-b", "main"], stashRepo);
    git(["config", "user.name", "Ada Lovelace"], stashRepo);
    git(["config", "user.email", "ada@example.com"], stashRepo);
    git(["config", "commit.gpgsign", "false"], stashRepo);
    commit(stashRepo, "notes.md", "# stash report fixture\n");
    writeFileSync(join(stashRepo, "wip.md"), "uncommitted\n");
    const stashRun = runAnalyze(stashRepo);
    const stashCommand = stashRun.report.migration?.stash?.command ?? "";
    expect(stashCommand.startsWith("git stash push -m ")).toBe(true);
    expect(stashRun.report.report?.stashState).toBe(stashCommand.slice("git stash push -m ".length));
    expect(stashRun.report.report?.stashState).toMatch(/^cleanup-auto-stash-\d+$/);
    expect(stashRun.report.report?.previousBranch).toBe("main");
  });
});

// Forbidden operations as concrete command shapes (R3): a violation is one of these
// patterns sitting on a line that does not negate it — the skill's safety prose names
// the forbidden commands verbatim ("no `git gc`, ever"), an instruction line does not.
// The probe at the bottom of the test keeps the filter honest: a bare command line
// must trip the same sweep that passes the folder.
const forbiddenPatterns: [RegExp, string][] = [
  [/git push/, "git push"],
  [/push --delete/, "push --delete"],
  [/git reflog|reflog --expire|reflog expire/, "reflog GC"],
  [/git gc/, "git gc"],
  [/branch -rd|branch -dr/, "remote branch deletion"],
  [/gh workflow|gh run |workflow_dispatch|\.github\/workflows/, "CI invocation"],
];

function forbiddenOnLine(line: string): string[] {
  if (/\b(no|never|not|without|forbidden|refuse[sd]?)\b/i.test(line)) return [];
  return forbiddenPatterns.filter(([pattern]) => pattern.test(line)).map(([, name]) => name);
}

function skillTextFiles(dir: string): string[] {
  const files: string[] = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) files.push(...skillTextFiles(full));
    else if (entry.isFile()) files.push(full);
  }
  return files;
}

describe("forbidden command sweep", () => {
  test("forbidden: no push, reflog GC, git gc, remote deletion or CI command exists in the skill folder or emitted fields", () => {
    const { report } = flow();
    // Emitted side: executable strings, zero tolerance — no negation room for a command.
    const commands = commandStrings(report);
    expect(commands.length).toBeGreaterThan(0);
    for (const command of commands) {
      expect(forbiddenPatterns.filter(([pattern]) => pattern.test(command)).map(([, name]) => name)).toEqual([]);
    }
    // Folder side: every text file under the skill folder, line by line; hits are
    // reported relative to the folder so the failure names file and line, never a
    // machine-absolute path.
    const skillRoot = join(import.meta.dir, "..", "skills", "ai-git-cleanup");
    const files = skillTextFiles(skillRoot);
    expect(files.length).toBeGreaterThan(0);
    const hits: string[] = [];
    for (const file of files) {
      const lines = readFileSync(file, "utf8").split("\n");
      for (const [index, line] of lines.entries()) {
        for (const name of forbiddenOnLine(line)) {
          hits.push(`${file.slice(skillRoot.length + 1)}:${index + 1}: ${name}`);
        }
      }
    }
    expect(hits).toEqual([]);
    // Non-vacuity: the sweep fails an un-negated command line and passes a prohibition.
    expect(forbiddenOnLine("Run `git push origin main` to sync.")).toEqual(["git push"]);
    expect(forbiddenOnLine("- **No push, no `git gc`, ever.**")).toEqual([]);
  });
});
