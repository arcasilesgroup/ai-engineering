// tests/chain-dispatch.spec.ts — the dispatcher's own wire: routing, the verdict
// cache, fail-closed, and the outcome shape.
//
// The guards have their own suites. This file is about the table between them and
// the host: which guard runs for which tool on which event (TABLE is what emits),
// what comes back when several run (ran order, first deny wins), what a cached
// verdict does to a second delivery of the same physical call, and the two
// fail-closed boundaries (unreadable payload, crashing guard).

import { describe, expect, test, afterAll, beforeEach } from "bun:test";
import { mkdtempSync, mkdirSync, rmSync, writeFileSync, existsSync, readFileSync, readdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { runChain, TABLE, type ChainOutcome } from "../src/chain/mod.ts";

let scratch: string;
let cwdBefore: string;
beforeEach(() => {
  if (!scratch) {
    scratch = mkdtempSync(join(tmpdir(), "ai-eng-dispatch-"));
    cwdBefore = process.cwd();
    // The gate resolves the repo from the process cwd when the payload carries no
    // cwd of its own — chdir once into the scratch repo, restore in afterAll.
    process.chdir(scratch);
  }
  rmSync(join(scratch, ".ai-engineering"), { recursive: true, force: true });
  mkdirSync(join(scratch, ".ai-engineering"), { recursive: true });
  writeFileSync(join(scratch, ".ai-engineering", "config.toml"), '[surfaces]\nenabled = ["claude-code"]\n');
});
afterAll(() => {
  if (cwdBefore) process.chdir(cwdBefore);
  if (scratch) rmSync(scratch, { recursive: true, force: true });
});

const RUN = (payload: Record<string, unknown>, event = "PreToolUse"): ChainOutcome =>
  runChain(payload, event, { inProcess: true });
const bash = (command: string, id = "u1"): Record<string, unknown> =>
  ({ tool_name: "Bash", tool_input: { command }, tool_use_id: id, session_id: "dispatch" });
const writeTool = (path: string, id = "u1"): Record<string, unknown> =>
  ({ tool_name: "Write", tool_input: { file_path: path, content: "x" }, tool_use_id: id, session_id: "dispatch" });

describe("TABLE — the routing invariants the outcomes cannot show", () => {
  test("every matcher is anchored: a prefix of a tool name must not sneak through", () => {
    for (const rows of [TABLE.PreToolUse!, TABLE.PostToolUse!]) {
      for (const row of rows) {
        expect(row.matcher.source.startsWith("^")).toBe(true);
        expect(row.matcher.source.endsWith("$")).toBe(true);
      }
    }
  });
});

describe("runChain — routing observed through outcomes", () => {
  test("an unknown event has no rows: nothing runs", () => {
    const outcome = RUN(bash("git commit -n -m x"), "SessionStart");
    expect(outcome.action).toBe("allow");
    if (outcome.action === "allow") expect(outcome.guards).toEqual([]);
  });

  test("a governed allow names every guard that ran", () => {
    const outcome = RUN(bash("git commit -m 'feat: ok'"));
    expect(outcome.action).toBe("allow");
    if (outcome.action === "allow") {
      expect(outcome.guards).toContain("self-protect");
      expect(outcome.guards).toContain("no-verify");
      expect(outcome.guards).toContain("injection");
      expect(outcome.guards).toContain("wrap");
      expect(outcome.guards).toContain("loop");
    }
  });

  test("a Write routes to self-protect and no-verify but never wrap", () => {
    const outcome = RUN(writeTool(join(scratch, "notes.md")));
    expect(outcome.action).toBe("allow");
    if (outcome.action === "allow") {
      expect(outcome.guards).toContain("self-protect");
      expect(outcome.guards).toContain("no-verify");
      expect(outcome.guards).not.toContain("wrap");
    }
  });

  test("a Read runs injection and loop only — the write guards never see a read", () => {
    const outcome = RUN({ tool_name: "Read", tool_input: { file_path: "notes.md" }, tool_use_id: "r1", session_id: "dispatch" });
    expect(outcome.action).toBe("allow");
    if (outcome.action === "allow") {
      expect(outcome.guards).toEqual(["injection", "loop"]);
    }
  });

  test("a first deny stops the chain: ran carries the guards up to and including the denier", () => {
    const outcome = RUN(bash("git commit --no-verify -m x"));
    expect(outcome.action).toBe("deny");
    if (outcome.action === "deny") {
      expect(outcome.by).toBe("no-verify");
      expect(outcome.guards).toContain("self-protect");
      expect(outcome.guards).toContain("no-verify");
      expect(outcome.guards).not.toContain("loop");
      expect(outcome.reason).toContain("no-verify");
    }
  });

  test("wrap rewrites a test command instead of denying", () => {
    const outcome = RUN(bash("bun test"));
    expect(outcome.action).toBe("rewrite");
    if (outcome.action === "rewrite") {
      expect(outcome.command).toBe("ai-eng wrap test -- bun test");
      expect(outcome.guards).toContain("wrap");
    }
  });

  test("a redelivered wrapped call rewrites again — a rewrite is never cached as a deny", () => {
    // Pre-fix, rememberVerdict stored wrap's deny:true shape and the second delivery
    // of the same physical call replayed it as a hard deny (audit run-1).
    const first = RUN(bash("bun test", "u-rewrite"));
    expect(first.action).toBe("rewrite");
    const second = RUN(bash("bun test", "u-rewrite"));
    expect(second.action).toBe("rewrite");
  });

  test("a tool no row matches runs loop only", () => {
    const outcome = RUN({ tool_name: "mcp__local__query", tool_input: { q: "x" }, tool_use_id: "m1", session_id: "dispatch" });
    expect(outcome.action).toBe("allow");
    if (outcome.action === "allow") expect(outcome.guards).toEqual(["loop"]);
  });

  test("an ungoverned repo allows with no guards, no receipt — the one bounded fail-open", () => {
    const bare = mkdtempSync(join(tmpdir(), "ai-eng-ungoverned-"));
    try {
      mkdirSync(join(bare, ".git"));
      const outcome = runChain({ ...bash("rm -rf /"), cwd: bare }, "PreToolUse", { inProcess: true });
      expect(outcome.action).toBe("allow");
      if (outcome.action === "allow") {
        expect(outcome.guards).toEqual([]);
        expect(outcome.receiptId).toBeNull();
      }
    } finally {
      rmSync(bare, { recursive: true, force: true });
    }
  });
});

describe("runChain — fail-closed boundaries", () => {
  test("a null payload is denied by chain, with the exact blocked message", () => {
    const outcome = runChain(null as unknown as Record<string, unknown>, "PreToolUse", { inProcess: true });
    expect(outcome.action).toBe("deny");
    if (outcome.action === "deny") {
      expect(outcome.by).toBe("chain");
      expect(outcome.reason).toBe("BLOCKED: the hook payload could not be read, so nothing here can say whether this action is safe.");
    }
  });

  test("an array payload is not an object the guards can read: denied", () => {
    const outcome = runChain([bash("x")] as unknown as Record<string, unknown>, "PreToolUse", { inProcess: true });
    expect(outcome.action).toBe("deny");
    if (outcome.action === "deny") expect(outcome.by).toBe("chain");
  });

  test("a payload that throws while being normalized is denied, never escaped", () => {
    const hostile = { get tool_name(): string { throw new Error("getter boom"); } };
    const outcome = runChain(hostile as unknown as Record<string, unknown>, "PreToolUse", { inProcess: true });
    expect(outcome.action).toBe("deny");
  });

  test("a missing tool_name normalises to empty and still routes loop", () => {
    const outcome = RUN({ tool_use_id: "e1", session_id: "dispatch" });
    expect(outcome.action).toBe("allow");
    if (outcome.action === "allow") expect(outcome.guards).toEqual(["loop"]);
  });

  test("a deny carries a receipt id; the receipt lands under .ai-engineering/receipts", () => {
    const outcome = RUN(bash("git commit -n -m x"));
    expect(outcome.action).toBe("deny");
    if (outcome.action === "deny") {
      expect(outcome.receiptId).not.toBeNull();
      const dir = join(scratch, ".ai-engineering", "receipts");
      expect(existsSync(dir)).toBe(true);
    }
  });
});

describe("runChain — the verdict cache", () => {
  test("a second delivery of the same physical call replays the verdict, not the guards", () => {
    const first = RUN(bash("git commit --no-verify -m x"));
    const dir = join(scratch, ".ai-engineering", "cache", "verdicts");
    expect(existsSync(dir)).toBe(true);
    const files = readdirSync(dir);
    expect(files.length).toBe(1);
    const book = JSON.parse(readFileSync(join(dir, files[0]!), "utf8")) as Record<string, { deny: boolean; by?: string }>;
    const entries = Object.values(book);
    expect(entries.length).toBe(1);
    expect(entries[0]!.deny).toBe(true);
    expect(entries[0]!.by).toBe("no-verify");

    // Second delivery: same session, same tool_use_id → the cached verdict replays:
    // same guard, same words, but the guards list is empty (nothing re-ran) and a
    // fresh receipt still lands.
    const second = RUN(bash("git commit --no-verify -m x"));
    expect(second.action).toBe("deny");
    if (second.action === "deny" && first.action === "deny") {
      expect(second.by).toBe(first.by);
      expect(second.reason).toBe(first.reason);
      expect(second.guards).toEqual([]);
      expect(second.receiptId).not.toBeNull();
    }
    expect(readdirSync(dir).length).toBe(1);
  });

  test("a cached allow is a verdict too: the second delivery skips the guards", () => {
    RUN(bash("git status"));
    const dir = join(scratch, ".ai-engineering", "cache", "verdicts");
    const book = JSON.parse(
      readFileSync(join(dir, readdirSync(dir)[0]!), "utf8"),
    ) as Record<string, { deny: boolean }>;
    expect(Object.values(book)[0]!.deny).toBe(false);
    const second = RUN(bash("git status"));
    expect(second.action).toBe("allow");
  });

  test("a call without tool_use_id is never cached: it is not addressable", () => {
    RUN({ tool_name: "Bash", tool_input: { command: "git status" }, session_id: "anon" });
    const dir = join(scratch, ".ai-engineering", "cache", "verdicts");
    expect(existsSync(dir)).toBe(false);
  });

  test("different sessions get different cache files named by a hash, never the raw id", () => {
    RUN({ tool_name: "Bash", tool_input: { command: "git status" }, tool_use_id: "u", session_id: "session/../evil" });
    const dir = join(scratch, ".ai-engineering", "cache", "verdicts");
    for (const file of readdirSync(dir)) {
      expect(file).toMatch(/^[0-9a-f]{32}\.json$/);
    }
  });

  test("the cache lives inside .ai-engineering, the directory the lock owns", () => {
    RUN(bash("git status"));
    expect(existsSync(join(scratch, ".ai-engineering", "cache", "verdicts"))).toBe(true);
  });
  test("a malformed cache file is not a crash: the chain re-decides", () => {
    RUN(bash("git status"));
    const dir = join(scratch, ".ai-engineering", "cache", "verdicts");
    writeFileSync(join(dir, readdirSync(dir)[0]!), "{not json");
    // A fresh call: the corrupted fingerprint's loop window may already be hot.
    const outcome = RUN(bash("git status --long", "u-fresh"));
    expect(outcome.action).toBe("allow");
  });
});

describe("runChain — overrides and context", () => {
  test("a loop override silences only the loop guard: other guards still run", () => {
    writeFileSync(
      join(scratch, ".ai-engineering", "overrides.toml"),
      '[[guard.off]]\nname = "loop"\nreason = "nightly"\nuntil = "2030-01-01"\n',
    );
    // no-verify is not overridden: it still denies.
    const outcome = RUN(bash("git commit --no-verify -m x"));
    expect(outcome.action).toBe("deny");
  });

  test("the payload's cwd is what resolves the repo, not the process cwd", () => {
    const governed = scratch;
    const other = mkdtempSync(join(tmpdir(), "ai-eng-othercwd-"));
    try {
      const outcome = RUN({ ...bash("git status"), cwd: other });
      expect(outcome.action).toBe("allow");
      if (outcome.action === "allow") expect(outcome.guards).toEqual([]);
    } finally {
      rmSync(other, { recursive: true, force: true });
      void governed;
    }
  });
});
