// tests/lease.spec.ts — lane rule 2, one folder, one writer. The first session that writes
// holds the folder; another session's write is sent to a worktree; the hold lapses after
// [work] lease_minutes without a write, ends with SessionEnd, or is released by hand.

import { afterEach, describe, expect, spyOn, test } from "bun:test";
import { sessionEnd, sessionStart } from "../src/chain/mod.ts";
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { gitDirOf, readLease, releaseLease, runLease } from "../src/guards/lease.ts";
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
      sessionStart("not json");
      sessionStart(JSON.stringify({ cwd: tmpdir() }));
    } finally {
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
