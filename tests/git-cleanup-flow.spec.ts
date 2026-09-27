// tests/git-cleanup-flow.spec.ts — unit layer of the ai-git-cleanup test plan (checkpoint 2):
// one fixture repository run end to end through analyze.mjs, asserting the WHOLE emitted
// command plan (U15-U17): single-quoting, an ancestry guard on every git branch -d, no
// protected/current/default branch in any delete, dirty-worktree refusal with removals
// paired before branch deletes, and the always-present unanalyzed bucket. The script builds
// its own survey from git plumbing, so the fixture is the spec. GIT_CONFIG_GLOBAL points at
// an empty file so the machine's ~/.gitconfig cannot decide what any child git does; remotes
// are local paths, so nothing here touches a network.

import { afterAll, describe, expect, test } from "bun:test";
import { spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
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

interface BranchEntry {
  branch?: string;
  reason?: string;
  evidence?: string;
  command?: string;
  verifyWith?: string;
  worktreePath?: string;
}

interface WorktreeEntry {
  path?: string;
  branch?: string;
  dirty?: boolean;
  dirtyFiles?: string[];
  stale?: boolean;
  command?: string;
}

interface Report {
  defaultBranch?: string;
  currentBranch?: string;
  deleteCandidates?: BranchEntry[];
  needsReview?: BranchEntry[];
  keep?: BranchEntry[];
  worktrees?: WorktreeEntry[];
  unanalyzed?: BranchEntry[];
}

// Every branch the fixture creates; U17 proves each lands in exactly one bucket.
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

// One fixture, one spawn, shared read-only by the three cases: each asserts a different
// slice of the same emitted plan. Raw stdout is kept so document-level claims (keys that
// must surface, strings that must never appear) run against what the script actually printed.
let cached: { stdout: string; report: Report } | null = null;
let buildError: Error | null = null;

function flow(): { stdout: string; report: Report } {
  if (cached) return cached;
  // A half-built fixture must not rebuild on the next case: re-running would hit
  // "remote already exists" and mask the original failure behind a second one.
  if (buildError) throw buildError;
  try {
    return buildFixture();
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

  // Merged into main: the canonical SAFE_TO_DELETE delete.
  git(["checkout", "-q", "-b", "feature/merged"], repo);
  commit(repo, "m.md", "merged work");
  git(["checkout", "-q", "main"], repo);
  git(["merge", "-q", "--no-ff", "feature/merged"], repo);

  // Squash-merged: tip not an ancestor with unique work — must stay keep, never delete.
  git(["checkout", "-q", "-b", "feature/squashed"], repo);
  commit(repo, "s.md", "squashed work");
  git(["checkout", "-q", "main"], repo);
  git(["merge", "-q", "--squash", "feature/squashed"], repo);
  git(["commit", "-q", "-m", "squash s.md"], repo);

  // Pushed then deleted on the remote: [gone] upstream, needs review, never a command.
  git(["checkout", "-q", "-b", "feature/gone"], repo);
  commit(repo, "g.md", "gone work");
  git(["push", "-q", "-u", "origin", "feature/gone"], repo);
  git(["push", "-q", "origin", "--delete", "feature/gone"], repo);
  git(["checkout", "-q", "main"], repo);

  // Unpushed: one commit landed after the push.
  git(["checkout", "-q", "-b", "feature/unpushed"], repo);
  commit(repo, "u.md", "pushed work");
  git(["push", "-q", "-u", "origin", "feature/unpushed"], repo);
  commit(repo, "u2.md", "unpushed work");
  git(["checkout", "-q", "main"], repo);

  // Protected siblings sit on the main tip with no extra work: only the PROTECTED rule
  // can keep them out of the delete plan. Worktree branches are created without being
  // checked out here — git never allows one branch in two worktrees.
  git(["branch", "develop"], repo);
  git(["branch", "release/2026.09"], repo);
  git(["branch", "feature/clean-wt"], repo);
  git(["branch", "feature/dirty-wt"], repo);
  const cleanPath = join(sandboxRoot, "wt-clean");
  const dirtyPath = join(sandboxRoot, "wt-dirty");
  git(["worktree", "add", "-q", cleanPath, "feature/clean-wt"], repo);
  git(["worktree", "add", "-q", dirtyPath, "feature/dirty-wt"], repo);
  // Uncommitted change: this worktree must be refused, never queued for removal.
  writeFileSync(join(dirtyPath, "uncommitted.md"), "work in progress\n");

  const done = spawnSync(process.execPath, [script, repo], {
    cwd: sandboxRoot,
    encoding: "utf8",
    env: childEnv,
  });
  if (done.status !== 0) {
    throw new Error(`analyze.mjs failed (${done.status}): ${done.stderr}\n${done.stdout}`);
  }
  // JSON.parse doubles as the "one document" check: stray output fails to parse.
  const report = JSON.parse(done.stdout) as Report;
  cached = { stdout: done.stdout, report };
  return cached;
}

describe("analyze.mjs flow fixture", () => {
  test("command plan: every emitted command is single-quoted with an ancestry guard, and no protected, current, or default branch is deleted", () => {
    const { stdout, report } = flow();
    expect(report.defaultBranch).toBe("main");
    expect(report.currentBranch).toBe("main");
    const deletes = report.deleteCandidates ?? [];
    // The plan is non-vacuous: both deletion shapes really reached the bucket.
    expect(names(deletes)).toContain("feature/merged");
    expect(names(deletes)).toContain("feature/clean-wt");
    // Exclusions: default/protected branches never appear in any delete.
    expect(names(deletes)).not.toContain("main");
    expect(names(deletes)).not.toContain("develop");
    expect(names(deletes)).not.toContain("release/2026.09");
    expect(entryFor(report.keep, "main")?.reason).toBe("PROTECTED");
    expect(entryFor(report.keep, "develop")?.reason).toBe("PROTECTED");
    expect(entryFor(report.keep, "release/2026.09")?.reason).toBe("PROTECTED");
    // Squash-merged, unpushed and [gone] work never reaches a command.
    expect(entryFor(report.keep, "feature/squashed")?.reason).toBe("LOCAL_WORK");
    expect(entryFor(report.keep, "feature/unpushed")?.reason).toBe("UNPUSHED_WORK");
    expect(entryFor(report.needsReview, "feature/gone")?.reason).toBe("REMOTE_GONE");
    for (const entry of [...(report.keep ?? []), ...(report.needsReview ?? [])]) {
      expect(entry.command).toBeUndefined();
    }
    // Exact fields a consumer executes (L13): quoted -d command plus the merge-base
    // guard naming refs/heads/<branch> and the default branch, one per delete.
    for (const entry of deletes) {
      expect(entry.reason).toBe("SAFE_TO_DELETE");
      expect(entry.command).toBe(`git branch -d '${entry.branch}'`);
      expect(entry.verifyWith).toBe(`git merge-base --is-ancestor 'refs/heads/${entry.branch}' 'main'`);
    }
    expect(entryFor(deletes, "feature/merged")?.command).toBe("git branch -d 'feature/merged'");
    expect(entryFor(deletes, "feature/merged")?.verifyWith).toBe(
      "git merge-base --is-ancestor 'refs/heads/feature/merged' 'main'",
    );
    // Worktree removals quote their path the same way.
    for (const worktree of report.worktrees ?? []) {
      if (worktree.command) expect(worktree.command).toBe(`git worktree remove '${worktree.path}'`);
    }
    // SAFE_TO_DELETE is pinned to -d; -D never appears in the document.
    expect(stdout).not.toContain("branch -D");
  });

  test("refusals: the dirty worktree is refused, and every queued worktree removal pairs with the branch delete it must precede", () => {
    const { report } = flow();
    const worktrees = report.worktrees ?? [];
    const deletes = report.deleteCandidates ?? [];
    const dirty = worktrees.find((worktree) => worktree.branch === "feature/dirty-wt");
    expect(dirty).toBeDefined();
    expect(dirty?.dirty).toBe(true);
    expect(dirty?.dirtyFiles?.join("\n")).toContain("uncommitted.md");
    expect(dirty?.stale).not.toBe(true);
    expect(dirty?.command).toBeUndefined(); // refused: never queued for removal
    // The clean linked worktree is queued, with an exactly quoted path.
    const clean = worktrees.find((worktree) => worktree.branch === "feature/clean-wt");
    expect(clean).toBeDefined();
    expect(clean?.dirty).toBe(false);
    expect(clean?.stale).toBe(true);
    expect(clean?.command).toBe(`git worktree remove '${clean?.path}'`);
    // Ordering data gate 2 executes: every queued removal belongs to a branch the plan
    // will delete, and the candidate points back at the holding worktree — so removals
    // are always available to print (and run) before their branch delete. Conversely,
    // every delete candidate held by a worktree has its removal queued unless the
    // worktree is dirty, where the refusal outranks the ordering.
    for (const worktree of worktrees.filter((entry) => entry.command)) {
      const candidate = entryFor(deletes, worktree.branch ?? "");
      expect(candidate).toBeDefined();
      expect(candidate?.worktreePath).toBe(worktree.path);
      expect(candidate?.command).toBe(`git branch -d '${worktree.branch}'`);
    }
    for (const candidate of deletes) {
      if (!candidate.worktreePath) continue;
      const held = worktrees.find((worktree) => worktree.path === candidate.worktreePath);
      expect(held).toBeDefined();
      if (!held) continue;
      if (held.dirty) {
        expect(held.command).toBeUndefined();
      } else {
        expect(held.command).toBe(`git worktree remove '${held.path}'`);
      }
    }
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
      ...names(report.deleteCandidates),
      ...names(report.needsReview),
      ...names(report.keep),
      ...names(report.unanalyzed),
    ].sort();
    expect(classified).toEqual([...fixtureBranches].sort());
  });
});
