// tests/lease.spec.ts — lane rule 2, one folder, one writer. The first session that writes
// holds the folder; another session's write is sent to a worktree; the hold lapses after
// [work] lease_minutes without a write, ends with SessionEnd, or is released by hand.

import { afterEach, describe, expect, spyOn, test } from "bun:test";
import { sessionEnd, sessionStart } from "../src/chain/mod.ts";
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { gitDirOf, leaseMinutes, readLease, releaseLease, runLease } from "../src/guards/lease.ts";
import { normalise, type Payload } from "../src/payload.ts";

const MINUTE = 60 * 1000;
const NOW = Date.UTC(2026, 10, 19, 12);
const cli = join(import.meta.dir, "..", "src", "cli.ts");
const roots: string[] = [];

afterEach(() => {
  for (const root of roots.splice(0)) rmSync(root, { recursive: true, force: true });
});

function git(dir: string, args: string[]): string {
  const done = spawnSync("git", args, { cwd: dir, encoding: "utf8" });
  if (done.status !== 0) throw new Error(`git ${args.join(" ")}: ${done.stderr}`);
  return done.stdout.trim();
}

/** A governed repo with one commit and no hook template. */
function repo(config = '[surfaces]\nenabled = ["claude-code"]\n'): string {
  const parent = mkdtempSync(join(tmpdir(), "ai-eng-lease-"));
  roots.push(parent);
  const dir = join(parent, "repo");
  mkdirSync(join(dir, ".ai-engineering"), { recursive: true });
  git(dir, ["init", "-q", "--template=", "-b", "main"]);
  git(dir, ["config", "user.email", "lease@example.com"]);
  git(dir, ["config", "user.name", "lease"]);
  git(dir, ["config", "commit.gpgsign", "false"]);
  writeFileSync(join(dir, ".ai-engineering", "config.toml"), config);
  writeFileSync(join(dir, "README.md"), "base\n");
  git(dir, ["add", "."]);
  git(dir, ["commit", "-q", "-m", "test: base"]);
  return dir;
}

const edit = (dir: string, session: string | undefined): Payload =>
  normalise({ tool_name: "Edit", tool_input: { file_path: join(dir, "README.md"), old_string: "base", new_string: "next" }, cwd: dir, ...(session === undefined ? {} : { session_id: session }) }, undefined, "PreToolUse");
/** A path as a shell command spells it on every OS: `\` is an escape to the shell reader. */
const slash = (path: string): string => path.split("\\").join("/");
const bash = (dir: string, session: string, command: string): Payload =>
  normalise({ tool_name: "Bash", tool_input: { command }, cwd: dir, session_id: session }, undefined, "PreToolUse");

describe("runLease — one folder, one writer", () => {
  test("the first session to write holds the folder; another session's write is sent to a worktree", () => {
    const dir = repo();
    expect(runLease(edit(dir, "session-a"), dir, NOW)).toBeUndefined();
    expect(readLease(dir)).toEqual({ session: "session-a", ts: NOW });

    const blocked = runLease(edit(dir, "session-b"), dir, NOW + 5 * MINUTE);
    expect(blocked?.deny).toBe(true);
    const reason = blocked?.deny === true ? blocked.reason : "";
    expect(reason).toContain("another session (session-");
    expect(reason).toContain("last write 5 min ago");
    expect(reason).toContain("ai-eng worktree new <branch>");
    expect(reason).toContain("ai-eng work release");
    expect(reason).toContain("frees itself in 10 min");
    // The holder keeps writing, and every write moves its clock.
    expect(runLease(edit(dir, "session-a"), dir, NOW + 6 * MINUTE)).toBeUndefined();
    expect(readLease(dir)?.ts).toBe(NOW + 6 * MINUTE);
  });

  test("fifteen minutes without a write free the folder for the next session", () => {
    const dir = repo();
    runLease(edit(dir, "session-a"), dir, NOW);
    expect(runLease(edit(dir, "session-b"), dir, NOW + 14 * MINUTE)?.deny).toBe(true);
    expect(runLease(edit(dir, "session-b"), dir, NOW + 15 * MINUTE)).toBeUndefined();
    expect(readLease(dir)?.session).toBe("session-b");
  });

  test("[work] lease_minutes sets the window", () => {
    const dir = repo('[surfaces]\nenabled = ["claude-code"]\n\n[work]\nlease_minutes = 2\n');
    runLease(edit(dir, "session-a"), dir, NOW);
    expect(runLease(edit(dir, "session-b"), dir, NOW + 1 * MINUTE)?.deny).toBe(true);
    expect(runLease(edit(dir, "session-b"), dir, NOW + 2 * MINUTE)).toBeUndefined();
  });

  test("a git command that writes the index, a ref or the tree is a write; reading is not", () => {
    const dir = repo();
    runLease(edit(dir, "session-a"), dir, NOW);
    for (const command of ["git add -A", "git commit -m wip", "cd sub && git -C . checkout main", "git stash"]) {
      expect(runLease(bash(dir, "session-b", command), dir, NOW + MINUTE)?.deny, command).toBe(true);
    }
    for (const command of ["git status", "git log --oneline", "git diff", "bun test", "ls -la"]) {
      expect(runLease(bash(dir, "session-b", command), dir, NOW + MINUTE), command).toBeUndefined();
    }
    expect(readLease(dir)?.session).toBe("session-a");
  });

  test("a file written outside the folder is not held: a temp file or another checkout", () => {
    const dir = repo();
    runLease(edit(dir, "session-a"), dir, NOW);
    const outside = (path: string) =>
      normalise({ tool_name: "Write", tool_input: { file_path: path, content: "x" }, cwd: dir, session_id: "session-b" }, undefined, "PreToolUse");
    expect(runLease(outside(join(tmpdir(), "notes.txt")), dir, NOW + MINUTE)).toBeUndefined();
    expect(runLease(outside(join(dir, "..", "other-checkout", "a.ts")), dir, NOW + MINUTE)).toBeUndefined();
    // Inside the folder, by an absolute or a relative path, it is held.
    expect(runLease(outside(join(dir, "src", "a.ts")), dir, NOW + MINUTE)?.deny).toBe(true);
    expect(runLease(outside("src/a.ts"), dir, NOW + MINUTE)?.deny).toBe(true);
    expect(readLease(dir)?.session).toBe("session-a");
  });

  test("a host that names no session is never judged, and holds nothing", () => {
    const dir = repo();
    runLease(edit(dir, "session-a"), dir, NOW);
    expect(runLease(edit(dir, undefined), dir, NOW + MINUTE)).toBeUndefined();
    expect(readLease(dir)?.session).toBe("session-a");
  });

  test("a worktree is its own folder: a second session writes there while the first holds the checkout", () => {
    const dir = repo();
    const tree = join(dir, "..", "feature-tree");
    git(dir, ["worktree", "add", "-q", "-b", "feat/x", tree]);
    runLease(edit(dir, "session-a"), dir, NOW);
    expect(runLease(edit(tree, "session-b"), tree, NOW + MINUTE)).toBeUndefined();
    expect(gitDirOf(tree)).not.toBe(gitDirOf(dir));
    expect(readLease(dir)?.session).toBe("session-a");
    expect(readLease(tree)?.session).toBe("session-b");
  });

  test("a git write aimed at a worktree is the worktree's to hold, from wherever the session started", () => {
    const dir = repo();
    const tree = join(dir, "..", "lane-tree");
    git(dir, ["worktree", "add", "-q", "-b", "feat/lane", tree]);
    runLease(edit(dir, "session-a"), dir, NOW);
    // Session b started in the checkout session a holds, and commits into its own worktree.
    expect(runLease(bash(dir, "session-b", `git -C ${slash(tree)} commit -m x`), dir, NOW + MINUTE)).toBeUndefined();
    expect(runLease(bash(dir, "session-b", `cd ${slash(tree)} && git add -A`), dir, NOW + MINUTE)).toBeUndefined();
    expect(readLease(tree)?.session).toBe("session-b");
    expect(readLease(dir)?.session).toBe("session-a");
    // And the worktree is now held: session a cannot write there either.
    expect(runLease(bash(dir, "session-a", `git -C ${slash(tree)} commit -m y`), dir, NOW + 2 * MINUTE)?.deny).toBe(true);
  });

  test("pointing a git write back at the held checkout is still stopped", () => {
    const dir = repo();
    const tree = join(dir, "..", "back-tree");
    git(dir, ["worktree", "add", "-q", "-b", "feat/back", tree]);
    runLease(edit(dir, "session-a"), dir, NOW);
    const later = NOW + MINUTE;
    expect(runLease(bash(tree, "session-b", `git -C ${slash(dir)} commit -m x`), dir, later)?.deny).toBe(true);
    expect(runLease(bash(tree, "session-b", `cd ${slash(dir)} && git commit -m x`), dir, later)?.deny).toBe(true);
    expect(runLease(bash(dir, "session-b", "git commit -m x"), dir, later)?.deny).toBe(true);
    // A `cd` the shell may not have run first is not believed: judged where it started.
    expect(runLease(bash(dir, "session-b", `cd ${slash(tree)} || git commit -m x`), dir, later)?.deny).toBe(true);
    expect(runLease(bash(dir, "session-b", `(cd ${slash(tree)}) ; git commit -m x`), dir, later)?.deny).toBe(true);
    expect(runLease(bash(dir, "session-b", "cd /no/such/folder; git commit -m x"), dir, later)?.deny).toBe(true);
  });

  test("a worktree nested inside the checkout is its own folder too", () => {
    const dir = repo();
    const nested = join(dir, ".claude", "worktrees", "inner");
    git(dir, ["worktree", "add", "-q", "-b", "feat/inner", nested]);
    runLease(edit(dir, "session-a"), dir, NOW);
    expect(runLease(edit(nested, "session-b"), dir, NOW + MINUTE)).toBeUndefined();
    expect(runLease(bash(nested, "session-b", "git commit -m x"), dir, NOW + MINUTE)).toBeUndefined();
    expect(readLease(nested)?.session).toBe("session-b");
  });

  test("a git write into another repository is not this repository's to hold", () => {
    const dir = repo();
    const other = repo();
    runLease(edit(dir, "session-a"), dir, NOW);
    expect(runLease(bash(dir, "session-b", `git -C ${slash(other)} commit -m x`), dir, NOW + MINUTE)).toBeUndefined();
    expect(readLease(other)).toBeNull();
  });

  test("the git words the reader follows: -C, -c, a path to git, pushd; a cd it cannot name resets", () => {
    const dir = repo();
    const tree = join(dir, "..", "words-tree");
    git(dir, ["worktree", "add", "-q", "-b", "feat/words", tree]);
    runLease(edit(dir, "session-a"), dir, NOW);
    const later = NOW + MINUTE;
    const allowed = (command: string): boolean => runLease(bash(dir, "session-b", command), dir, later) === undefined;
    expect(allowed(`git -c core.x=1 -C ${slash(tree)} commit -m x`)).toBe(true);
    expect(allowed(`/usr/bin/git -C ${slash(tree)} commit -m x`)).toBe(true);
    expect(allowed(`pushd ${slash(tree)} && git commit -m x`)).toBe(true);
    // -C adds to the folder before it.
    expect(allowed(`git -C ${slash(join(dir, ".."))} -C words-tree commit -m x`)).toBe(true);
    // Reading never takes a lease, wherever it points.
    expect(allowed("git status")).toBe(true);
    expect(allowed("git -C . log")).toBe(true);
    // Not a plain path, two arguments, or `cd -`: the folder this reading cannot name.
    expect(allowed(`cd ${slash(tree)} && cd $HOME && git commit -m x`)).toBe(false);
    expect(allowed(`cd ${slash(tree)} other && git commit -m x`)).toBe(false);
    expect(allowed(`cd ${slash(tree)} && cd - && git commit -m x`)).toBe(false);
    expect(allowed(`cd ${slash(tree)}* && git commit -m x`)).toBe(false);
    // A leading `~` is the shell's; one inside a name is a letter (Windows: RUNNER~1).
    expect(allowed("cd ~ && git commit -m x")).toBe(false);
    const short = join(dir, "..", "LANE~1");
    git(dir, ["worktree", "add", "-q", "-b", "feat/short", short]);
    expect(allowed(`cd ${slash(short)} && git commit -m x`)).toBe(true);
    // A git with no subcommand after its options, and quoting the reader cannot follow: no write.
    expect(allowed("git -C")).toBe(true);
    expect(allowed('git commit -m "unterminated')).toBe(true);
    // A file written in the worktree is the worktree's.
    expect(runLease(edit(tree, "session-b"), dir, later)).toBeUndefined();
    expect(readLease(tree)?.session).toBe("session-b");
  });

  test("PowerShell is read like Bash; a tool that writes nothing is never judged", () => {
    const dir = repo();
    runLease(edit(dir, "session-a"), dir, NOW);
    const powershell = normalise({ tool_name: "PowerShell", tool_input: { command: "git commit -m x" }, cwd: dir, session_id: "session-b" }, undefined, "PreToolUse");
    expect(runLease(powershell, dir, NOW + MINUTE)?.deny).toBe(true);
    const read = normalise({ tool_name: "Read", tool_input: { file_path: join(dir, "README.md") }, cwd: dir, session_id: "session-b" }, undefined, "PreToolUse");
    expect(runLease(read, dir, NOW + MINUTE)).toBeUndefined();
    const noCommand = normalise({ tool_name: "Bash", tool_input: {}, cwd: dir, session_id: "session-b" }, undefined, "PreToolUse");
    expect(runLease(noCommand, dir, NOW + MINUTE)).toBeUndefined();
    // A session id of blanks names no session.
    expect(runLease(edit(dir, "   "), dir, NOW + MINUTE)).toBeUndefined();
    expect(runLease(edit(dir, "session-b"), null, NOW + MINUTE)).toBeUndefined();
  });

  test("the block names the folder held and the first eight characters of the session", () => {
    const dir = repo();
    runLease(edit(dir, "session-a-1234567890"), dir, NOW);
    const blocked = runLease(edit(dir, "session-b"), dir, NOW + 3 * MINUTE);
    const reason = blocked?.deny === true ? blocked.reason : "";
    expect(reason).toContain("another session (session-, last write 3 min ago) is writing in ");
    expect(reason).toContain(dir);
    expect(reason).toContain("frees itself in 12 min");
  });

  test("a lease_minutes that is not a whole positive number falls back to 15", () => {
    for (const value of ["0", "-5", "2.5", '"10"']) {
      const dir = repo(`[surfaces]\nenabled = ["claude-code"]\n[work]\nlease_minutes = ${value}\n`);
      expect(leaseMinutes(dir)).toBe(15);
    }
    expect(leaseMinutes(repo('[surfaces]\nenabled = ["claude-code"]\n[work]\nlease_minutes = 1\n'))).toBe(1);
  });

  test("a lease file that is not a lease is no lease; no git dir holds none", () => {
    const dir = repo();
    const file = join(dir, ".git", "ai-eng", "lease.json");
    mkdirSync(join(dir, ".git", "ai-eng"), { recursive: true });
    for (const text of ["not json", '{"session": 1, "ts": 2}', '{"session": "a", "ts": "2"}', '{"session": "a"}']) {
      writeFileSync(file, text);
      expect(readLease(dir)).toBeNull();
    }
    expect(releaseLease(dir)).toBe(false);
    const bare = mkdtempSync(join(tmpdir(), "ai-eng-lease-bare-"));
    roots.push(bare);
    expect(gitDirOf(bare)).toBeNull();
    expect(readLease(bare)).toBeNull();
    expect(releaseLease(bare)).toBe(false);
  });

  test("a .git file is read by its gitdir line: spacing, a trailing blank, or no such line", () => {
    const bare = mkdtempSync(join(tmpdir(), "ai-eng-lease-dotgit-"));
    roots.push(bare);
    const dotGit = join(bare, ".git");
    writeFileSync(dotGit, "gitdir:/somewhere/wt  \n");
    expect(gitDirOf(bare)).toBe(resolve(bare, "/somewhere/wt"));
    writeFileSync(dotGit, "gitdir:   rel/wt\n");
    expect(gitDirOf(bare)).toBe(join(bare, "rel", "wt"));
    writeFileSync(dotGit, "notgitdir: /x\n");
    expect(gitDirOf(bare)).toBeNull();
    writeFileSync(dotGit, "first line\ngitdir: /y\n");
    expect(gitDirOf(bare)).toBe(resolve(bare, "/y"));
  });

  test("a session releases only its own hold", () => {
    const dir = repo();
    runLease(edit(dir, "session-a"), dir, NOW);
    expect(releaseLease(dir, "session-b")).toBe(false);
    expect(readLease(dir)?.session).toBe("session-a");
    expect(releaseLease(dir, "session-a")).toBe(true);
    expect(readLease(dir)).toBeNull();
  });
});

describe("sessionStart and sessionEnd in process", () => {
  test("SessionEnd frees only its own session's hold, and an unreadable payload is silence", () => {
    const dir = repo();
    runLease(edit(dir, "session-a"), dir, Date.now());
    sessionEnd("not json");
    sessionEnd(JSON.stringify({ session_id: "session-b", cwd: dir }));
    expect(readLease(dir)?.session).toBe("session-a");
    sessionEnd(JSON.stringify({ session_id: "session-a", cwd: dir }));
    expect(readLease(dir)).toBeNull();
  });

  test("SessionStart answers with additionalContext in a governed repo, and nothing elsewhere", () => {
    const dir = repo();
    // A session that names no repo resolves it from the cwd, so the cwd is pinned outside any
    // repo: otherwise this case would read the lanes of whatever checkout the suite runs in.
    const outside = mkdtempSync(join(tmpdir(), "ai-eng-lease-outside-"));
    roots.push(outside);
    const cwdBefore = process.cwd();
    writeFileSync(join(dir, "README.md"), "changed\n");
    git(dir, ["stash", "push", "-q"]);
    const chunks: string[] = [];
    const spy = spyOn(process.stdout, "write").mockImplementation(((chunk: unknown) => {
      chunks.push(String(chunk));
      return true;
    }) as never);
    const optOut = process.env["AI_ENG_NO_UPDATE_NOTICES"];
    process.env["AI_ENG_NO_UPDATE_NOTICES"] = "1";
    try {
      sessionStart(JSON.stringify({ cwd: dir }));
      process.chdir(outside);
      sessionStart("not json");
      sessionStart(JSON.stringify({ cwd: tmpdir() }));
    } finally {
      process.chdir(cwdBefore);
      spy.mockRestore();
      if (optOut === undefined) delete process.env["AI_ENG_NO_UPDATE_NOTICES"];
      else process.env["AI_ENG_NO_UPDATE_NOTICES"] = optOut;
    }
    const answers = chunks.join("").trim().split("\n").filter((line) => line.length > 0);
    expect(answers).toHaveLength(1);
    expect(JSON.parse(answers[0]!).hookSpecificOutput.additionalContext).toContain("lanes: 1 orphan");
  });
});

describe("the lease through the CLI — the chain, SessionEnd and work release", () => {
  function chain(dir: string, event: string, body: Record<string, unknown>): { status: number | null; out: string } {
    const run = spawnSync(process.execPath, [cli, "chain", event], { cwd: dir, input: JSON.stringify(body), encoding: "utf8", env: { ...process.env, AI_ENG_NO_UPDATE_NOTICES: "1" } });
    return { status: run.status, out: `${run.stdout}${run.stderr}` };
  }
  const editBody = (dir: string, session: string) => ({ tool_name: "Edit", tool_input: { file_path: join(dir, "README.md"), old_string: "base", new_string: "next" }, cwd: dir, session_id: session, tool_use_id: `${session}-${Math.random()}` });

  test("the chain stops a second session's edit, and SessionEnd of the first frees the folder", () => {
    const dir = repo();
    expect(chain(dir, "PreToolUse", editBody(dir, "session-a")).status).toBe(0);
    const blocked = chain(dir, "PreToolUse", editBody(dir, "session-b"));
    expect(blocked.status).not.toBe(0);
    expect(blocked.out).toContain("another session");
    // Another session's end never frees a hold it does not own.
    expect(chain(dir, "SessionEnd", { session_id: "session-b", cwd: dir }).status).toBe(0);
    expect(readLease(dir)?.session).toBe("session-a");
    expect(chain(dir, "SessionEnd", { session_id: "session-a", cwd: dir }).status).toBe(0);
    expect(readLease(dir)).toBeNull();
    expect(chain(dir, "PreToolUse", editBody(dir, "session-b")).status).toBe(0);
  });

  test("ai-eng work release frees the folder by hand, and the lease never lands in the tree", () => {
    const dir = repo();
    chain(dir, "PreToolUse", editBody(dir, "session-a"));
    const released = spawnSync(process.execPath, [cli, "work", "release"], { cwd: dir, encoding: "utf8", env: { ...process.env, AI_ENG_NO_UPDATE_NOTICES: "1" } });
    expect(released.status).toBe(0);
    expect(released.stdout).toContain("released");
    expect(readLease(dir)).toBeNull();
    // The hold lives in the git directory: nothing in the tree, so nothing to commit by mistake.
    expect(existsSync(join(dir, ".git", "ai-eng"))).toBe(true);
    expect(git(dir, ["status", "--porcelain", "--untracked-files=all"])).not.toContain("lease");
  });
});
