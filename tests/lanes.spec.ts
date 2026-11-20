// tests/lanes.spec.ts — the lane model: one task, one branch, one folder, one PR, and
// three doors out (land, park, drop). The classifier is pure and tested on facts; the
// board, its doors, the lane limit and the session-start line run against real repos.
// No network: the forge answer is a cache file the test writes.

import { afterEach, describe, expect, test } from "bun:test";
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { azurePulls, classify, forgeOf, forgePulls, laneSummary, lanes, type BranchFacts } from "../src/git/lanes.ts";
import { runNoStash } from "../src/guards/no-stash.ts";
import { normalise } from "../src/payload.ts";

const DAY = 24 * 60 * 60 * 1000;
const NOW = Date.UTC(2026, 10, 19, 12);
const cli = join(import.meta.dir, "..", "src", "cli.ts");
const roots: string[] = [];

afterEach(() => {
  for (const root of roots.splice(0)) rmSync(root, { recursive: true, force: true });
});

function facts(overrides: Partial<BranchFacts>): BranchFacts {
  return {
    branch: "feat/x",
    tip: "a".repeat(40),
    lastCommitMs: NOW - DAY,
    path: null,
    isCurrent: false,
    dirty: 0,
    upstreamGone: false,
    inBase: false,
    landing: null,
    pr: null,
    parked: null,
    ...overrides,
  };
}

describe("classify — a lane's state, from what git and the forge say (pure)", () => {
  test("landed only on proof: the forge merged this exact tip, or the base holds it and its remote is gone", () => {
    const tip = "a".repeat(40);
    expect(classify(facts({ pr: { number: 7, state: "MERGED", headRefName: "feat/x", headRefOid: tip } }), NOW, 3).state).toBe("landed");
    // Merged at another tip: the local branch carries work the PR never had.
    expect(classify(facts({ pr: { number: 7, state: "MERGED", headRefName: "feat/x", headRefOid: "b".repeat(40) } }), NOW, 3).state).toBe("active");
    expect(classify(facts({ inBase: true, upstreamGone: true, lastCommitMs: NOW - 9 * DAY }), NOW, 3).state).toBe("landed");
    // In the base but never pushed anywhere: a branch made a minute ago looks the same.
    expect(classify(facts({ inBase: true }), NOW, 3).state).toBe("active");
  });

  test("an open PR is ready; a recent, current or dirty branch is active; silence past the limit is an orphan", () => {
    expect(classify(facts({ pr: { number: 9, state: "OPEN", headRefName: "feat/x", headRefOid: "c".repeat(40) } }), NOW, 3).state).toBe("ready");
    expect(classify(facts({ lastCommitMs: NOW - 2 * DAY }), NOW, 3).state).toBe("active");
    expect(classify(facts({ lastCommitMs: NOW - 9 * DAY, isCurrent: true }), NOW, 3).state).toBe("active");
    expect(classify(facts({ lastCommitMs: NOW - 9 * DAY, dirty: 4 }), NOW, 3)).toMatchObject({ state: "active", detail: expect.stringContaining("4 uncommitted") });
    expect(classify(facts({ lastCommitMs: NOW - 9 * DAY }), NOW, 3)).toMatchObject({ state: "orphan", ageDays: 9 });
  });

  test("parked holds until its date; past it, the lane asks for a decision again", () => {
    const old = NOW - 30 * DAY;
    expect(classify(facts({ lastCommitMs: old, parked: { reason: "waiting for the API", until: "2026-12-01" } }), NOW, 3)).toMatchObject({ state: "parked", detail: "waiting for the API · until 2026-12-01" });
    expect(classify(facts({ lastCommitMs: old, parked: { reason: "waiting", until: null } }), NOW, 3).state).toBe("parked");
    expect(classify(facts({ lastCommitMs: old, parked: { reason: "waiting", until: "2026-11-01" } }), NOW, 3).state).toBe("orphan");
  });

  test("the session line names only what needs a decision", () => {
    const board = (states: Array<"active" | "landed" | "orphan" | "ghost">) => ({
      repo: "/r",
      base: "main",
      maxActive: 3,
      forgeNote: null,
      lanes: states.map((state, index) => ({ state, name: `b${index}`, path: null, detail: "", ageDays: state === "orphan" ? 54 : 0 })),
    });
    expect(laneSummary(board(["active"]))).toBeNull();
    expect(laneSummary(board(["landed", "landed", "orphan", "ghost"]))).toBe("lanes: 2 landed to tidy, 1 orphan (oldest 54 d), 1 ghost worktree → ai-eng work");
    expect(laneSummary(board(["active", "active", "active", "active"]))).toBe("lanes: 4 active lanes, over the limit of 3 → ai-eng work");
  });
});

/** A governed repo whose remote already has `main`, with no hook template: fixture
 *  commits never run this machine's own floor. */
function repo(): string {
  const parent = mkdtempSync(join(tmpdir(), "ai-eng-lanes-"));
  roots.push(parent);
  const dir = join(parent, "repo");
  mkdirSync(dir);
  git(dir, ["init", "-q", "--template=", "-b", "main"]);
  git(dir, ["config", "user.email", "lanes@example.com"]);
  git(dir, ["config", "user.name", "lanes"]);
  git(dir, ["config", "commit.gpgsign", "false"]);
  mkdirSync(join(dir, ".ai-engineering"));
  writeFileSync(join(dir, ".ai-engineering", "config.toml"), '[surfaces]\nenabled = ["claude-code"]\n');
  commit(dir, "README.md", "base\n");
  git(dir, ["remote", "add", "origin", join(parent, "unused.git")]);
  git(dir, ["update-ref", "refs/remotes/origin/main", "HEAD"]);
  git(dir, ["symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main"]);
  return dir;
}

function git(dir: string, args: string[]): string {
  const done = spawnSync("git", args, { cwd: dir, encoding: "utf8" });
  if (done.status !== 0) throw new Error(`git ${args.join(" ")}: ${done.stderr}`);
  return done.stdout.trim();
}

function commit(dir: string, name: string, content: string): string {
  writeFileSync(join(dir, name), content);
  git(dir, ["add", name]);
  git(dir, ["commit", "-q", "-m", `test: ${name}`]);
  return git(dir, ["rev-parse", "HEAD"]);
}

function ai(dir: string, args: string[]): { status: number | null; out: string } {
  const run = spawnSync(process.execPath, [cli, ...args], { cwd: dir, encoding: "utf8", env: { ...process.env, NO_COLOR: "1", AI_ENG_NO_UPDATE_NOTICES: "1" } });
  return { status: run.status, out: `${run.stdout}${run.stderr}` };
}

/** The forge answer as `ai-eng work` would have cached it, fresh. */
function forgeSays(dir: string, pulls: unknown[]): void {
  const common = git(dir, ["rev-parse", "--path-format=absolute", "--git-common-dir"]);
  mkdirSync(join(common, "ai-eng"), { recursive: true });
  writeFileSync(join(common, "ai-eng", "forge.json"), JSON.stringify({ ts: Date.now(), pulls }));
}

describe("the board — every lane, from git and the cached forge answer", () => {
  test("a stash, a branch the forge merged, and the work in progress each get their lane", () => {
    const dir = repo();
    git(dir, ["checkout", "-q", "-b", "feat/landed"]);
    const tip = commit(dir, "landed.txt", "done\n");
    git(dir, ["checkout", "-q", "main"]);
    git(dir, ["checkout", "-q", "-b", "feat/wip"]);
    commit(dir, "wip.txt", "going\n");
    writeFileSync(join(dir, "README.md"), "changed\n");
    git(dir, ["stash", "push", "-q", "-m", "parked by hand"]);
    forgeSays(dir, [{ number: 12, state: "MERGED", headRefName: "feat/landed", headRefOid: tip }]);

    const board = lanes(dir, { refresh: false });
    expect(board.base).toBe("main");
    expect(board.lanes.find((lane) => lane.name === "feat/landed")).toMatchObject({ state: "landed", detail: "PR #12 merged" });
    expect(board.lanes.find((lane) => lane.name === "feat/wip")?.state).toBe("active");
    expect(board.lanes.find((lane) => lane.name.startsWith("stash@{0}"))).toMatchObject({ state: "orphan" });
    expect(ai(dir, ["work", "--json"]).out).toContain('"state": "landed"');
  });

  test("git proves a landing with no forge: a merge, a squash, a worktree merge; a fresh branch is not one", () => {
    const dir = repo();
    // Merged into main by a merge commit, never pushed: no upstream, no forge.
    git(dir, ["checkout", "-q", "-b", "feat/merged"]);
    commit(dir, "merged.txt", "merged\n");
    git(dir, ["checkout", "-q", "main"]);
    commit(dir, "main-moves.txt", "main moved\n");
    git(dir, ["merge", "-q", "--no-ff", "-m", "merge feat/merged", "feat/merged"]);
    // Squash-merged: main holds its change as one new commit, the branch tip is not in main.
    git(dir, ["checkout", "-q", "-b", "feat/squashed"]);
    commit(dir, "squash-a.txt", "a\n");
    commit(dir, "squash-b.txt", "b\n");
    git(dir, ["checkout", "-q", "main"]);
    git(dir, ["merge", "-q", "--squash", "feat/squashed"]);
    git(dir, ["commit", "-q", "-m", "squash feat/squashed"]);
    // Partly in main: one of its two changes was squashed in, the other was not.
    git(dir, ["checkout", "-q", "-b", "feat/partial"]);
    commit(dir, "partial-a.txt", "a\n");
    git(dir, ["checkout", "-q", "main"]);
    git(dir, ["merge", "-q", "--squash", "feat/partial"]);
    git(dir, ["commit", "-q", "-m", "squash half of feat/partial"]);
    git(dir, ["checkout", "-q", "feat/partial"]);
    commit(dir, "partial-b.txt", "b\n");
    git(dir, ["checkout", "-q", "main"]);
    // Created on main a minute ago, nothing of its own: on main's own line.
    git(dir, ["branch", "feat/fresh"]);
    // A worktree merge recorded the tip it merged.
    git(dir, ["checkout", "-q", "-b", "feat/recorded"]);
    const recorded = commit(dir, "recorded.txt", "r\n");
    git(dir, ["checkout", "-q", "main"]);
    git(dir, ["config", "branch.feat/recorded.aiengmerged", recorded]);
    git(dir, ["update-ref", "refs/remotes/origin/main", "main"]);
    forgeSays(dir, []);

    const byName = (board: ReturnType<typeof lanes>, name: string) => board.lanes.find((lane) => lane.name === name);
    const asked = lanes(dir, { refresh: true });
    expect(byName(asked, "feat/merged")).toMatchObject({ state: "landed", detail: "merged into main" });
    expect(byName(asked, "feat/squashed")).toMatchObject({ state: "landed", detail: "squash-merged into main" });
    expect(byName(asked, "feat/recorded")).toMatchObject({ state: "landed", detail: "merged by ai-eng worktree merge" });
    expect(byName(asked, "feat/partial")?.state).toBe("active");
    expect(byName(asked, "feat/fresh")?.state).toBe("active");
    // A session start writes nothing: the squash proof waits for a human verb.
    const started = lanes(dir, { refresh: false });
    expect(byName(started, "feat/merged")?.state).toBe("landed");
    expect(byName(started, "feat/squashed")?.state).toBe("active");
    // A tip the worktree merge did not record is not the one it merged.
    git(dir, ["config", "branch.feat/recorded.aiengmerged", "f".repeat(40)]);
    expect(byName(lanes(dir, { refresh: false }), "feat/recorded")?.state).toBe("active");
  });

  test("ai-eng work prunes remote branches first, so one deleted upstream reads as gone", () => {
    const parent = mkdtempSync(join(tmpdir(), "ai-eng-lanes-remote-"));
    roots.push(parent);
    const remote = join(parent, "remote.git");
    git(parent, ["init", "-q", "--bare", "-b", "main", remote]);
    const dir = repo();
    git(dir, ["remote", "set-url", "origin", remote]);
    git(dir, ["push", "-q", "origin", "main"]);
    git(dir, ["checkout", "-q", "-b", "feat/pushed"]);
    commit(dir, "pushed.txt", "p\n");
    git(dir, ["push", "-q", "-u", "origin", "feat/pushed"]);
    git(dir, ["checkout", "-q", "main"]);
    git(dir, ["merge", "-q", "--ff-only", "feat/pushed"]);
    git(dir, ["push", "-q", "origin", "main"]);
    // The forge deletes the branch on merge; this checkout has not fetched since.
    git(parent, ["--git-dir", remote, "branch", "-D", "feat/pushed"]);
    forgeSays(dir, []);
    expect(lanes(dir, { refresh: false }).lanes.find((lane) => lane.name === "feat/pushed")?.state).toBe("active");
    expect(lanes(dir, { refresh: true }).lanes.find((lane) => lane.name === "feat/pushed")).toMatchObject({ state: "landed", detail: "in the base, remote branch gone" });
  });

  test("tidy removes a provably landed lane and keeps the one checked out here", () => {
    const dir = repo();
    git(dir, ["checkout", "-q", "-b", "feat/gone"]);
    commit(dir, "gone.txt", "merged\n");
    git(dir, ["checkout", "-q", "main"]);
    git(dir, ["merge", "-q", "--ff-only", "feat/gone"]);
    git(dir, ["update-ref", "refs/remotes/origin/main", "HEAD"]);
    // Its remote branch was deleted on merge: the upstream is configured and gone.
    git(dir, ["config", "branch.feat/gone.remote", "origin"]);
    git(dir, ["config", "branch.feat/gone.merge", "refs/heads/feat/gone"]);
    forgeSays(dir, []);

    const run = ai(dir, ["work", "tidy"]);
    expect(run.status).toBe(0);
    expect(run.out).toContain("✓ feat/gone removed");
    expect(spawnSync("git", ["rev-parse", "--verify", "--quiet", "refs/heads/feat/gone"], { cwd: dir }).status).not.toBe(0);
  });

  test("park records a reason and a date; resume clears it; uncommitted work refuses to park", () => {
    const dir = repo();
    git(dir, ["branch", "feat/later"]);
    forgeSays(dir, []);
    expect(ai(dir, ["work", "park", "feat/later", "waiting for the API", "--until", "2099-01-01"]).status).toBe(0);
    expect(lanes(dir, { refresh: false }).lanes.find((lane) => lane.name === "feat/later")).toMatchObject({ state: "parked", detail: "waiting for the API · until 2099-01-01" });
    expect(ai(dir, ["work", "resume", "feat/later"]).status).toBe(0);
    expect(lanes(dir, { refresh: false }).lanes.find((lane) => lane.name === "feat/later")?.state).toBe("active");

    git(dir, ["checkout", "-q", "feat/later"]);
    const worktree = join(dir, "..", "later-tree");
    git(dir, ["checkout", "-q", "main"]);
    git(dir, ["worktree", "add", "-q", worktree, "feat/later"]);
    writeFileSync(join(worktree, "draft.txt"), "not committed\n");
    const refused = ai(dir, ["work", "park", "feat/later", "waiting"]);
    expect(refused.status).toBe(2);
    expect(refused.out).toContain("uncommitted work");
  });

  test("drop keeps the tip in refs/archive and removes the branch; the branch checked out here is refused", () => {
    const dir = repo();
    git(dir, ["checkout", "-q", "-b", "feat/abandon"]);
    const tip = commit(dir, "idea.txt", "maybe\n");
    expect(ai(dir, ["work", "drop", "feat/abandon"]).status).toBe(2);
    git(dir, ["checkout", "-q", "main"]);
    const dropped = ai(dir, ["work", "drop", "feat/abandon"]);
    expect(dropped.status).toBe(0);
    expect(dropped.out).toContain("git branch feat/abandon refs/archive/feat/abandon");
    expect(git(dir, ["rev-parse", "refs/archive/feat/abandon"])).toBe(tip);
    expect(spawnSync("git", ["rev-parse", "--verify", "--quiet", "refs/heads/feat/abandon"], { cwd: dir }).status).not.toBe(0);
  });
});

describe("the lane limit — a fourth active lane is refused", () => {
  test("worktree new names the active lanes and the three doors", () => {
    const dir = repo();
    for (const name of ["feat/a", "feat/b"]) {
      git(dir, ["checkout", "-q", "-b", name]);
      commit(dir, `${name.slice(5)}.txt`, "work\n");
    }
    // feat/b is checked out: with feat/a and one more, three lanes are active.
    git(dir, ["checkout", "-q", "-b", "feat/c"]);
    commit(dir, "c.txt", "work\n");
    const refused = ai(dir, ["worktree", "new", "d"]);
    expect(refused.status).toBe(2);
    expect(refused.out).toContain("3 lanes are active");
    expect(refused.out).toContain("[work] max_active");
    writeFileSync(join(dir, ".ai-engineering", "config.toml"), '[surfaces]\nenabled = ["claude-code"]\n\n[work]\nmax_active = 4\n');
    expect(ai(dir, ["worktree", "new", "d"]).status).toBe(0);
  });
});

describe("the forge — GitHub through gh, Azure DevOps through az", () => {
  test("the remote URL names the forge", () => {
    for (const url of [
      "https://dev.azure.com/org/project/_git/repo",
      "https://org@dev.azure.com/org/project/_git/repo",
      "git@ssh.dev.azure.com:v3/org/project/repo",
      "https://org.visualstudio.com/project/_git/repo",
    ]) expect(forgeOf(url), url).toBe("azure");
    for (const url of ["https://github.com/org/repo.git", "git@github.com:org/repo.git", "", "https://example.com/dev.azure.com.git"]) {
      expect(forgeOf(url), url).toBe("github");
    }
  });

  test("az's PR list becomes gh's shape; an entry missing a field is skipped", () => {
    const tip = "d".repeat(40);
    expect(azurePulls([
      { pullRequestId: 4, status: "completed", sourceRefName: "refs/heads/feat/a", lastMergeSourceCommit: { commitId: tip } },
      { pullRequestId: 5, status: "active", sourceRefName: "refs/heads/feat/b", lastMergeSourceCommit: { commitId: tip } },
      { pullRequestId: 6, status: "abandoned", sourceRefName: "refs/heads/feat/c", lastMergeSourceCommit: { commitId: tip } },
      { pullRequestId: 7, status: "completed", sourceRefName: "refs/tags/v1", lastMergeSourceCommit: { commitId: tip } },
      { pullRequestId: 8, status: "notSet", sourceRefName: "refs/heads/feat/d", lastMergeSourceCommit: { commitId: tip } },
      { pullRequestId: 9, status: "completed", sourceRefName: "refs/heads/feat/e", lastMergeSourceCommit: null },
    ])).toEqual([
      { number: 4, state: "MERGED", headRefName: "feat/a", headRefOid: tip },
      { number: 5, state: "OPEN", headRefName: "feat/b", headRefOid: tip },
      { number: 6, state: "CLOSED", headRefName: "feat/c", headRefOid: tip },
    ]);
    expect(() => azurePulls({ value: [] })).toThrow();
  });

  // A shell script stands in for az; Windows would need an .exe on PATH.
  test.skipIf(process.platform === "win32")("an Azure DevOps remote is asked through az, and a merged PR lands its lane", () => {
    const dir = repo();
    git(dir, ["remote", "set-url", "origin", "https://dev.azure.com/org/project/_git/repo"]);
    git(dir, ["checkout", "-q", "-b", "feat/azure"]);
    const tip = commit(dir, "azure.txt", "a\n");
    git(dir, ["checkout", "-q", "main"]);
    const bin = mkdtempSync(join(tmpdir(), "ai-eng-fake-az-"));
    roots.push(bin);
    const answer = JSON.stringify([{ pullRequestId: 31, status: "completed", sourceRefName: "refs/heads/feat/azure", lastMergeSourceCommit: { commitId: tip } }]);
    writeFileSync(join(bin, "az"), `#!/bin/sh\n[ "$1 $2 $3" = "repos pr list" ] || exit 9\nprintf '%s' '${answer}'\n`, { mode: 0o755 });
    const pathBefore = process.env["PATH"];
    process.env["PATH"] = `${bin}:${pathBefore ?? ""}`;
    try {
      // The forge directly: a board refresh would also fetch from the Azure URL over the network.
      expect(forgePulls(dir, true)).toEqual({ pulls: [{ number: 31, state: "MERGED", headRefName: "feat/azure", headRefOid: tip }], note: null });
      expect(lanes(dir, { refresh: false }).lanes.find((lane) => lane.name === "feat/azure")).toMatchObject({ state: "landed", detail: "PR #31 merged" });
    } finally {
      process.env["PATH"] = pathBefore;
    }
  });
});

describe("SessionStart — the lane line beside the version lines", () => {
  test("a stash is named as an orphan when the session starts", () => {
    const dir = repo();
    writeFileSync(join(dir, "README.md"), "changed\n");
    git(dir, ["stash", "push", "-q"]);
    const run = spawnSync(process.execPath, [cli, "chain", "SessionStart"], {
      cwd: dir,
      input: JSON.stringify({ cwd: dir }),
      encoding: "utf8",
      env: { ...process.env, AI_ENG_NO_UPDATE_NOTICES: "1" },
    });
    expect(run.status).toBe(0);
    const context = (JSON.parse(run.stdout) as { hookSpecificOutput: { additionalContext: string } }).hookSpecificOutput.additionalContext;
    expect(context).toContain("lanes: 1 orphan");
    expect(existsSync(join(dir, ".ai-engineering", "work.json"))).toBe(false);
  });

  test("a proven landing closes on its own at session start; dirty, current and held lanes stay (D-015)", () => {
    const dir = repo();
    const sessionStart = (session: string): string => {
      const run = spawnSync(process.execPath, [cli, "chain", "SessionStart"], {
        cwd: dir,
        input: JSON.stringify({ cwd: dir, session_id: session }),
        encoding: "utf8",
        env: { ...process.env, AI_ENG_NO_UPDATE_NOTICES: "1" },
      });
      expect(run.status).toBe(0);
      return run.stdout === "" ? "" : (JSON.parse(run.stdout) as { hookSpecificOutput: { additionalContext: string } }).hookSpecificOutput.additionalContext;
    };
    // Three branches merged into main by a merge commit: proof without the forge.
    for (const name of ["feat/done", "feat/dirty", "feat/held"]) {
      git(dir, ["checkout", "-q", "-b", name]);
      commit(dir, `${name.slice(5)}.txt`, `${name}\n`);
      git(dir, ["checkout", "-q", "main"]);
      git(dir, ["merge", "-q", "--no-ff", "-m", `merge ${name}`, name]);
    }
    git(dir, ["update-ref", "refs/remotes/origin/main", "main"]);
    const doneTip = git(dir, ["rev-parse", "feat/done"]);
    const dirtyTree = join(dir, "..", "dirty-tree");
    const heldTree = join(dir, "..", "held-tree");
    git(dir, ["worktree", "add", "-q", dirtyTree, "feat/dirty"]);
    git(dir, ["worktree", "add", "-q", heldTree, "feat/held"]);
    writeFileSync(join(dirtyTree, "unsaved.txt"), "not committed\n");
    // Another session is writing in the held folder right now.
    const heldGitDir = git(heldTree, ["rev-parse", "--path-format=absolute", "--git-dir"]);
    mkdirSync(join(heldGitDir, "ai-eng"), { recursive: true });
    writeFileSync(join(heldGitDir, "ai-eng", "lease.json"), JSON.stringify({ session: "other-session", ts: Date.now() }));

    const context = sessionStart("this-session");
    expect(context).toContain("lanes: closed feat/done (landed; each tip kept in refs/archive/<branch>");
    expect(git(dir, ["rev-parse", "refs/archive/feat/done"])).toBe(doneTip);
    expect(spawnSync("git", ["rev-parse", "--verify", "--quiet", "refs/heads/feat/done"], { cwd: dir }).status).not.toBe(0);
    // Uncommitted work and another session's folder are never touched.
    expect(existsSync(join(dirtyTree, "unsaved.txt"))).toBe(true);
    expect(git(dir, ["rev-parse", "feat/dirty"])).not.toBe("");
    expect(existsSync(heldTree)).toBe(true);
    expect(context).toContain("2 landed to tidy");
    // The holding session itself may close its own folder.
    expect(sessionStart("other-session")).toContain("lanes: closed feat/held");
    expect(existsSync(heldTree)).toBe(false);
  });
});

describe("tidy — archive first, then close; the base catches up", () => {
  test("tidy keeps every tip it removes in refs/archive and fast-forwards a clean base", () => {
    const parent = mkdtempSync(join(tmpdir(), "ai-eng-lanes-ff-"));
    roots.push(parent);
    const remote = join(parent, "remote.git");
    git(parent, ["init", "-q", "--bare", "-b", "main", remote]);
    const dir = repo();
    git(dir, ["remote", "set-url", "origin", remote]);
    git(dir, ["push", "-q", "-u", "origin", "main"]);
    git(dir, ["checkout", "-q", "-b", "feat/tidied"]);
    const tip = commit(dir, "tidied.txt", "t\n");
    git(dir, ["checkout", "-q", "main"]);
    git(dir, ["merge", "-q", "--no-ff", "-m", "merge feat/tidied", "feat/tidied"]);
    git(dir, ["push", "-q", "origin", "main"]);
    // The remote moves on: someone else landed a commit main has not fetched yet.
    const other = join(parent, "other");
    git(parent, ["clone", "-q", remote, other]);
    git(other, ["config", "user.email", "o@example.com"]);
    git(other, ["config", "user.name", "o"]);
    git(other, ["config", "commit.gpgsign", "false"]);
    commit(other, "elsewhere.txt", "e\n");
    git(other, ["push", "-q", "origin", "main"]);
    forgeSays(dir, []);

    const run = ai(dir, ["work", "tidy"]);
    expect(run.status).toBe(0);
    expect(run.out).toContain("feat/tidied removed — merged into main");
    expect(run.out).toContain("kept at refs/archive/feat/tidied");
    expect(git(dir, ["rev-parse", "refs/archive/feat/tidied"])).toBe(tip);
    expect(run.out).toContain("main fast-forwarded 1 commit");
    expect(existsSync(join(dir, "elsewhere.txt"))).toBe(true);

    // With local changes the base is never moved.
    commit(other, "later.txt", "l\n");
    git(other, ["push", "-q", "origin", "main"]);
    writeFileSync(join(dir, "README.md"), "local edit\n");
    expect(ai(dir, ["work", "tidy"]).out).not.toContain("fast-forwarded");
    expect(existsSync(join(dir, "later.txt"))).toBe(false);
  });
});

describe("no-stash — work never leaves its branch for the stash", () => {
  const verdict = (command: string) => runNoStash(normalise({ tool_name: "Bash", tool_input: { command } }, undefined, "PreToolUse"));

  test("making a stash is denied, with the two alternatives", () => {
    for (const command of ["git stash", "git stash push -m wip", "git stash -u", "git -C repo stash save x", "cd repo && git stash"]) {
      const result = verdict(command);
      expect(result?.deny, command).toBe(true);
      expect(result?.deny === true ? result.reason : "").toContain("ai-eng work park");
    }
  });

  test("reading or restoring a stash, and every other git command, passes", () => {
    for (const command of ["git stash list", "git stash show -p stash@{0}", "git stash pop", "git stash apply", "git stash branch rescue", "git status", "echo git stash"]) {
      expect(verdict(command)?.deny ?? false, command).toBe(false);
    }
  });
});
