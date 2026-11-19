// tests/work-command.spec.ts — `ai-eng work` in process: the board, its doors (tidy,
// park, resume, drop, release) and every refusal, against real repos. lanes.spec.ts
// drives the same verb through the CLI; this file runs it where coverage can see it.

import { afterEach, describe, expect, spyOn, test } from "bun:test";
import { spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { stripVTControlCharacters } from "node:util";
import { workMain } from "../src/commands/work.ts";
import { readLease, runLease } from "../src/guards/lease.ts";
import { normalise } from "../src/payload.ts";

const roots: string[] = [];
const savedCwd = process.cwd();

afterEach(() => {
  process.chdir(savedCwd);
  for (const root of roots.splice(0)) rmSync(root, { recursive: true, force: true });
});

function git(dir: string, args: string[]): string {
  const done = spawnSync("git", args, { cwd: dir, encoding: "utf8" });
  if (done.status !== 0) throw new Error(`git ${args.join(" ")}: ${done.stderr}`);
  return done.stdout.trim();
}

function commit(dir: string, name: string): string {
  writeFileSync(join(dir, name), `${name}\n`);
  git(dir, ["add", name]);
  git(dir, ["commit", "-q", "-m", `test: ${name}`]);
  return git(dir, ["rev-parse", "HEAD"]);
}

/** A governed repo whose remote has `main`, with the forge answer cached and empty. */
function repo(): string {
  const parent = mkdtempSync(join(tmpdir(), "ai-eng-work-"));
  roots.push(parent);
  const dir = join(parent, "repo");
  mkdirSync(join(dir, ".ai-engineering"), { recursive: true });
  git(dir, ["init", "-q", "--template=", "-b", "main"]);
  git(dir, ["config", "user.email", "work@example.com"]);
  git(dir, ["config", "user.name", "work"]);
  git(dir, ["config", "commit.gpgsign", "false"]);
  writeFileSync(join(dir, ".ai-engineering", "config.toml"), '[surfaces]\nenabled = ["claude-code"]\n');
  commit(dir, "README.md");
  git(dir, ["remote", "add", "origin", join(parent, "unused.git")]);
  git(dir, ["update-ref", "refs/remotes/origin/main", "HEAD"]);
  git(dir, ["symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main"]);
  forge(dir, []);
  return dir;
}

function forge(dir: string, pulls: unknown[]): void {
  const common = git(dir, ["rev-parse", "--path-format=absolute", "--git-common-dir"]);
  mkdirSync(join(common, "ai-eng"), { recursive: true });
  writeFileSync(join(common, "ai-eng", "forge.json"), JSON.stringify({ ts: Date.now(), pulls }));
}

/** Run the verb in `dir`; what it printed, both streams, colours stripped. */
function work(dir: string, args: string[], flags: { json?: boolean; until?: string } = {}): { code: number; out: string } {
  process.chdir(dir);
  const chunks: string[] = [];
  const write = ((chunk: unknown) => {
    chunks.push(String(chunk));
    return true;
  }) as never;
  const out = spyOn(process.stdout, "write").mockImplementation(write);
  const err = spyOn(process.stderr, "write").mockImplementation(write);
  try {
    return { code: workMain(args, flags), out: stripVTControlCharacters(chunks.join("")) };
  } finally {
    out.mockRestore();
    err.mockRestore();
  }
}

describe("ai-eng work — the board", () => {
  test("names the base, each lane with its state, the active count and the next step", () => {
    const dir = repo();
    git(dir, ["checkout", "-q", "-b", "feat/landed"]);
    const tip = commit(dir, "landed.txt");
    git(dir, ["checkout", "-q", "main"]);
    forge(dir, [{ number: 4, state: "MERGED", headRefName: "feat/landed", headRefOid: tip }]);
    git(dir, ["checkout", "-q", "-b", "feat/now"]);
    commit(dir, "now.txt");

    const board = work(dir, []);
    expect(board.code).toBe(0);
    expect(board.out).toContain("· base main ·");
    expect(board.out).toMatch(/active\s+feat\/now/);
    expect(board.out).toMatch(/landed\s+feat\/landed\s+0 d\s+PR #4 merged/);
    expect(board.out).toContain("active lanes: 1/3");
    expect(board.out).toContain("next: ai-eng work tidy");
  });

  test("--json is the board as data, no colour and no spinner", () => {
    const dir = repo();
    const board = work(dir, [], { json: true });
    expect(board.code).toBe(0);
    expect(JSON.parse(board.out)).toMatchObject({ base: "main", maxActive: 3, lanes: [] });
  });

  test("an orphan asks for a decision", () => {
    const dir = repo();
    writeFileSync(join(dir, "README.md"), "changed\n");
    git(dir, ["stash", "push", "-q"]);
    expect(work(dir, []).out).toContain("next: decide each orphan");
  });

  test("outside a repository it says so", () => {
    const outside = mkdtempSync(join(tmpdir(), "ai-eng-work-outside-"));
    roots.push(outside);
    const run = work(outside, []);
    expect(run.code).toBe(2);
    expect(run.out).toContain("not inside a git repository");
  });

  test("an unknown door, or a door with the wrong arguments, prints the usage", () => {
    const dir = repo();
    for (const args of [["merge"], ["tidy", "extra"], ["park", "feat/x"], ["resume"], ["drop"], ["release", "extra"]]) {
      const run = work(dir, args);
      expect(run.code, args.join(" ")).toBe(2);
      expect(run.out, args.join(" ")).toContain("usage: ai-eng work");
    }
  });
});

describe("ai-eng work tidy", () => {
  test("removes a landed lane and its clean folder, keeps the one checked out here", () => {
    const dir = repo();
    const tree = join(dir, "..", "landed-tree");
    git(dir, ["worktree", "add", "-q", "-b", "feat/landed", tree]);
    const tip = commit(tree, "landed.txt");
    git(dir, ["checkout", "-q", "-b", "feat/here"]);
    const here = commit(dir, "here.txt");
    forge(dir, [
      { number: 1, state: "MERGED", headRefName: "feat/landed", headRefOid: tip },
      { number: 2, state: "MERGED", headRefName: "feat/here", headRefOid: here },
    ]);

    const run = work(dir, ["tidy"]);
    expect(run.code).toBe(0);
    expect(run.out).toContain("✓ feat/landed removed — PR #1 merged, and its folder");
    expect(run.out).toContain("· feat/here kept — it is checked out here");
    expect(spawnSync("git", ["rev-parse", "--verify", "--quiet", "refs/heads/feat/landed"], { cwd: dir }).status).not.toBe(0);
  });

  test("keeps a landed lane whose folder has uncommitted work", () => {
    const dir = repo();
    const tree = join(dir, "..", "dirty-tree");
    git(dir, ["worktree", "add", "-q", "-b", "feat/dirty", tree]);
    const tip = commit(tree, "dirty.txt");
    writeFileSync(join(tree, "draft.txt"), "not committed\n");
    forge(dir, [{ number: 3, state: "MERGED", headRefName: "feat/dirty", headRefOid: tip }]);
    expect(work(dir, ["tidy"]).out).toContain("feat/dirty kept — its folder");
  });

  test("prunes a ghost worktree, and says when nothing landed", () => {
    const dir = repo();
    expect(work(dir, ["tidy"]).out).toContain("nothing has landed — nothing to tidy");
    const tree = join(dir, "..", "ghost-tree");
    git(dir, ["worktree", "add", "-q", "-b", "feat/ghost", tree]);
    rmSync(tree, { recursive: true, force: true });
    expect(work(dir, ["tidy"]).out).toContain("✓ ghost worktrees pruned");
  });
});

describe("ai-eng work park · resume · drop · release", () => {
  test("park records the reason and the date; resume clears them", () => {
    const dir = repo();
    git(dir, ["branch", "feat/later"]);
    const parked = work(dir, ["park", "feat/later", "waiting for the API"], { until: "2099-01-01" });
    expect(parked.code).toBe(0);
    expect(parked.out).toContain("✓ feat/later parked — waiting for the API · until 2099-01-01");
    expect(git(dir, ["config", "branch.feat/later.aiengparked"])).toBe("waiting for the API|2099-01-01");
    expect(work(dir, ["resume", "feat/later"]).out).toContain("✓ feat/later is active again");
    expect(spawnSync("git", ["config", "branch.feat/later.aiengparked"], { cwd: dir }).status).not.toBe(0);
  });

  test("park refuses a missing branch, an empty reason, a bad date and uncommitted work", () => {
    const dir = repo();
    expect(work(dir, ["park", "feat/none", "why"]).out).toContain("there is no branch feat/none");
    git(dir, ["branch", "feat/x"]);
    expect(work(dir, ["park", "feat/x", " "]).out).toContain("park needs a reason");
    expect(work(dir, ["park", "feat/x", "why"], { until: "soon" }).out).toContain("--until takes a date");
    const tree = join(dir, "..", "x-tree");
    git(dir, ["worktree", "add", "-q", tree, "feat/x"]);
    writeFileSync(join(tree, "draft.txt"), "draft\n");
    expect(work(dir, ["park", "feat/x", "why"]).out).toContain("uncommitted work");
    expect(work(dir, ["resume", "feat/none"]).out).toContain("there is no branch feat/none");
  });

  test("drop archives the tip, removes the clean folder and the branch, and a second drop gets a dated name", () => {
    const dir = repo();
    const tree = join(dir, "..", "idea-tree");
    git(dir, ["worktree", "add", "-q", "-b", "feat/idea", tree]);
    const tip = commit(tree, "idea.txt");
    const dropped = work(dir, ["drop", "feat/idea"]);
    expect(dropped.code).toBe(0);
    expect(dropped.out).toContain("✓ feat/idea dropped — kept at refs/archive/feat/idea");
    expect(git(dir, ["rev-parse", "refs/archive/feat/idea"])).toBe(tip);

    git(dir, ["branch", "feat/idea"]);
    expect(work(dir, ["drop", "feat/idea"]).out).toMatch(/kept at refs\/archive\/feat\/idea-\d{4}-\d{2}-\d{2}/);
  });

  test("drop refuses a missing branch, the branch checked out here, and uncommitted work", () => {
    const dir = repo();
    expect(work(dir, ["drop", "feat/none"]).out).toContain("there is no branch feat/none");
    expect(work(dir, ["drop", "main"]).out).toContain("main is checked out here");
    const tree = join(dir, "..", "busy-tree");
    git(dir, ["worktree", "add", "-q", "-b", "feat/busy", tree]);
    writeFileSync(join(tree, "draft.txt"), "draft\n");
    expect(work(dir, ["drop", "feat/busy"]).out).toContain("uncommitted work");
  });

  test("release frees a held folder, and says when nothing holds it", () => {
    const dir = repo();
    expect(work(dir, ["release"]).out).toContain("nothing to release");
    runLease(normalise({ tool_name: "Edit", tool_input: { file_path: join(dir, "README.md"), old_string: "a", new_string: "b" }, cwd: dir, session_id: "session-a" }, undefined, "PreToolUse"), dir);
    expect(readLease(dir)?.session).toBe("session-a");
    const released = work(dir, ["release"]);
    expect(released.out).toContain("released — it was held by session session-");
    expect(readLease(dir)).toBeNull();
  });
});
