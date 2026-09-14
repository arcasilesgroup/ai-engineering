// tests/chain-dialect.spec.ts — the wire contract of a denial, per host.
// A denial whose text never arrives reads as permission, so these tests assert the
// exact envelope and the exact exit status each host's validator accepts — not that
// "the function was called". The overrides switch is here too: it is the ONLY way a
// guard turns off (§09.1), and a parsing bug in it leaves the switch silently dead.

import { describe, expect, test, afterAll, spyOn } from "bun:test";
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { deny, allowRewrite, allow, readOverrides, overrideDaysLeft, overrideActive } from "../src/chain/dialect.ts";

class ExitSignal extends Error {
  constructor(readonly code: number) {
    super(`exit ${code}`);
  }
}

/** Run an envelope function, capturing stdout, stderr and the exit status it chose. */
function envelope(fn: () => void): { json: Record<string, unknown>; stderr: string; code: number } {
  const out: string[] = [];
  const err: string[] = [];
  const outSpy = spyOn(process.stdout, "write").mockImplementation(((chunk: string) => {
    out.push(String(chunk));
    return true;
  }) as never);
  const errSpy = spyOn(process.stderr, "write").mockImplementation(((chunk: string) => {
    err.push(String(chunk));
    return true;
  }) as never);
  const exitSpy = spyOn(process, "exit").mockImplementation(((code?: number) => {
    throw new ExitSignal(code ?? 0);
  }) as never);
  try {
    fn();
  } catch (error) {
    if (error instanceof ExitSignal) {
      return { json: out.length > 0 ? (JSON.parse(out.join("")) as Record<string, unknown>) : {}, stderr: err.join(""), code: error.code };
    }
    throw error;
  } finally {
    outSpy.mockRestore();
    errSpy.mockRestore();
    exitSpy.mockRestore();
  }
  throw new Error("the envelope returned without exiting — a denial that never exits reads as permission");
}

const roots: string[] = [];
function repoWithOverrides(toml: string): string {
  const root = mkdtempSync(join(tmpdir(), "ai-eng-overrides-"));
  roots.push(root);
  mkdirSync(join(root, ".ai-engineering"), { recursive: true });
  writeFileSync(join(root, ".ai-engineering", "overrides.toml"), toml);
  return root;
}
afterAll(() => {
  for (const root of roots) rmSync(root, { recursive: true, force: true });
});

describe("deny — one envelope per host, chosen by what that host's validator reads", () => {
  test("claude gets the byte-for-byte blob on stdout and exit 2, with the reason on stderr", () => {
    const { json, stderr, code } = envelope(() => deny("no-verify", "the hooks were skipped", "claude"));
    expect(code).toBe(2);
    expect(json).toEqual({
      permission: "deny",
      continue: false,
      user_message: "[ai-eng] no-verify: the hooks were skipped",
      userMessage: "[ai-eng] no-verify: the hooks were skipped",
      stop_reason: "[ai-eng] no-verify: the hooks were skipped",
      stopReason: "[ai-eng] no-verify: the hooks were skipped",
    });
    expect(stderr).toContain("[ai-eng] no-verify: the hooks were skipped");
  });

  test("codex denies through hookSpecificOutput and exits 0 — a non-zero exit is not its contract", () => {
    const { json, code } = envelope(() => deny("injection", "payload in the file", "codex", "PreToolUse"));
    expect(code).toBe(0);
    expect(json).toEqual({
      hookSpecificOutput: { hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: "[ai-eng] injection: payload in the file" },
    });
  });

  test("cursor reads permission + the two messages and exits 0", () => {
    const { json, code } = envelope(() => deny("self-protect", "that file governs you", "cursor"));
    expect(code).toBe(0);
    expect(json).toEqual({ permission: "deny", user_message: "[ai-eng] self-protect: that file governs you", agent_message: "[ai-eng] self-protect: that file governs you" });
  });

  test("copilot carries the reason in the JSON and exits 0", () => {
    const { json, code } = envelope(() => deny("no-verify", "no --no-verify", "copilot"));
    expect(code).toBe(0);
    expect(json).toEqual({ permissionDecision: "deny", permissionDecisionReason: "[ai-eng] no-verify: no --no-verify" });
  });

  test("a denied loop names the only thing that unblocks it: an override with a reason and a date", () => {
    const { stderr } = envelope(() => deny("loop", "the same call five times", "claude"));
    expect(stderr).toContain("[[guard.off]] with reason + until");
  });
});

describe("allowRewrite — the rewrite reaches the host in the field that host reads", () => {
  test("claude", () => {
    const { json, code } = envelope(() => allowRewrite("bun test", "claude"));
    expect(code).toBe(0);
    expect(json).toEqual({ permission: "allow", updatedInput: { command: "bun test" } });
  });
  test("codex nests it under hookSpecificOutput", () => {
    const { json, code } = envelope(() => allowRewrite("bun test", "codex", "PreToolUse"));
    expect(code).toBe(0);
    expect(json).toEqual({ hookSpecificOutput: { hookEventName: "PreToolUse", permissionDecision: "allow", updatedInput: { command: "bun test" } } });
  });
  test("cursor wants updated_input, copilot wants modifiedArgs", () => {
    expect(envelope(() => allowRewrite("bun test", "cursor")).json).toEqual({ permission: "allow", updated_input: { command: "bun test" } });
    expect(envelope(() => allowRewrite("bun test", "copilot")).json).toEqual({ permissionDecision: "allow", modifiedArgs: { command: "bun test" } });
  });
});

describe("allow — silence, except where an empty stdout is a policy error", () => {
  test("claude gets nothing at all: writing an allow it never reads is the noise this avoids", () => {
    const out: string[] = [];
    const spy = spyOn(process.stdout, "write").mockImplementation(((chunk: string) => {
      out.push(String(chunk));
      return true;
    }) as never);
    try {
      allow("claude");
      allow("codex");
    } finally {
      spy.mockRestore();
    }
    expect(out).toEqual([]);
  });

  test("cursor's failClosed template reads an empty stdout as a refusal, so it gets the allow", () => {
    const out: string[] = [];
    const spy = spyOn(process.stdout, "write").mockImplementation(((chunk: string) => {
      out.push(String(chunk));
      return true;
    }) as never);
    try {
      allow("cursor");
    } finally {
      spy.mockRestore();
    }
    expect(JSON.parse(out.join(""))).toEqual({ permission: "allow" });
  });
});

describe("the override switch (the only mechanism that turns a guard off)", () => {
  test("a repo with no overrides file has no overrides, and neither does no repo at all", () => {
    expect(readOverrides(null)).toEqual([]);
    expect(readOverrides(mkdtempSync(join(tmpdir(), "ai-eng-bare-")))).toEqual([]);
  });

  test("[[guard.off]] nests as a dotted key — the literal is dead config and must read as empty", () => {
    const root = repoWithOverrides('[[guard.off]]\nname = "no-verify"\nreason = "hotfix"\nuntil = "2030-01-01"\n');
    expect(readOverrides(root)).toEqual([{ name: "no-verify", reason: "hotfix", until: "2030-01-01" }]);
  });

  test("an entry without a name is dropped, and a file that does not parse is not a crash", () => {
    expect(readOverrides(repoWithOverrides('[[guard.off]]\nreason = "no name here"\n'))).toEqual([]);
    expect(readOverrides(repoWithOverrides("this is not = = toml\n"))).toEqual([]);
  });

  test("an override without a date is reported as never expiring instead of reading as neutral", () => {
    expect(overrideDaysLeft({ name: "loop", reason: "why" })).toBeNull();
    expect(overrideDaysLeft({ name: "loop", reason: "why", until: "2030" })).toBeNull();
    expect(overrideDaysLeft({ name: "loop", reason: "why", until: "not-a-date" })).toBeNull();
  });

  test("days left counts whole days, today is 0, and a past date is negative — the guard re-arms itself", () => {
    const now = Date.parse("2026-01-10T12:00:00Z");
    expect(overrideDaysLeft({ name: "g", reason: "r", until: "2026-01-10" }, now)).toBe(0);
    expect(overrideDaysLeft({ name: "g", reason: "r", until: "2026-01-12" }, now)).toBeGreaterThan(0);
    expect(overrideDaysLeft({ name: "g", reason: "r", until: "2026-01-05" }, now)).toBeLessThan(0);
  });

  test("an expired entry stops matching, so the guard is live again until the human deletes it", () => {
    const expired = { name: "no-verify", reason: "hotfix", until: "2000-01-01" };
    const live = { name: "no-verify", reason: "release window", until: "2099-12-31" };
    expect(overrideActive([expired], "no-verify")).toBeNull();
    expect(overrideActive([expired, live], "no-verify")).toBe(live);
    expect(overrideActive([live], "loop")).toBeNull();
    expect(overrideActive([{ name: "loop", reason: "no date" }], "loop")).toEqual({ name: "loop", reason: "no date" });
  });
});
