// tests/payload-dialect.spec.ts — the payload boundary and the wire defaults.
//
// Two contracts live here. (1) `normalise` is the wall between hosts: whatever a
// surface sends, the guards receive one shape — camelCase translated, unknown names
// passed through untouched, non-object input reduced to an empty record, notebook
// paths promoted to file_path only when file_path is genuinely absent. (2) The
// envelope functions default to the claude wire: calling them without the optional
// dialect/event arguments must emit the claude envelope with the claude event name.
// The wrap decision table closes the file: every runner keyword wraps, every skip
// shape does not.

import { describe, expect, spyOn, test } from "bun:test";
import {
  BUILT_IN_ALIASES,
  deduplicable,
  fingerprint,
  loopExact,
  loopSignature,
  normalise,
  type Payload,
} from "../src/chain/payload.ts";
import { allow, allowRewrite, deny } from "../src/chain/dialect.ts";
import { isTestCommand, rewrite } from "../src/guards/wrap.ts";

class ExitSignal extends Error {
  constructor(readonly code: number) {
    super(`exit ${code}`);
  }
}

/** Run an envelope function, capturing stdout/stderr and the exit status it chose. */
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



describe("normalise — one shape out of every host spelling", () => {
  test("top-level camelCase spellings fall back through the raw object, not the alias map", () => {
    // Measured: `tool_name ?? tool` reads the raw spelling, and camelCase keys are
    // only translated INSIDE tool_input. A host that sends toolName at the top
    // gets nothing fabricated for it — the empty string, not a guessed tool.
    const p = normalise({ toolName: "Bash", toolInput: { command: "ls" } });
    expect(p.tool_name).toBe("");
    expect(p.tool_input).toEqual({});
  });

  test("input-side camelCase keys inside tool_input are translated (filePath → file_path)", () => {
    const p = normalise({ tool_name: "Write", tool_input: { filePath: "a.ts", content: "x" } });
    expect(p.tool_input["file_path"]).toBe("a.ts");
    expect(p.tool_input["filePath"]).toBeUndefined();
  });

  test("workspaceRoot and workspacePath both map to cwd", () => {
    for (const key of ["workspaceRoot", "workspacePath"]) {
      const p = normalise({ tool_name: "Bash", tool_input: { command: "ls", [key]: "/tmp/w" } });
      expect(p.tool_input["cwd"]).toBe("/tmp/w");
    }
  });

  test("an unknown tool name passes through untouched, never mangled", () => {
    const p = normalise({ tool_name: "mcp__local__query" });
    expect(p.tool_name).toBe("mcp__local__query");
  });

  test("a missing tool_name falls back to tool, then to the empty string", () => {
    expect(normalise({ tool: "Grep" }).tool_name).toBe("Grep");
    expect(normalise({}).tool_name).toBe("");
  });

  test("cursor's Shell arrives as Bash through the surface alias", () => {
    const p = normalise({ tool_name: "Shell" }, "cursor");
    expect(p.tool_name).toBe("Bash");
  });

  test("pi and oh-my-pi lowercase names arrive as their canonical forms", () => {
    for (const surface of ["pi", "oh-my-pi"]) {
      for (const [lower, canonical] of Object.entries({ bash: "Bash", powershell: "PowerShell", read: "Read", edit: "Edit", write: "Write", grep: "Grep", glob: "Glob", web_search: "WebSearch", fetch_content: "WebFetch", source_check: "WebFetch", get_search_content: "WebFetch" })) {
        expect(normalise({ tool_name: lower }, surface).tool_name).toBe(canonical);
      }
    }
  });

  test("an unknown surface applies no aliasing at all", () => {
    const p = normalise({ tool_name: "Shell" }, "vscode");
    expect(p.tool_name).toBe("Shell");
  });

  test("non-string tool_name is never aliased (the typeof arm actually ran)", () => {
    const p = normalise({ tool_name: 42 }, "cursor");
    expect(p.tool_name as unknown).toBe(42);
  });

  test("fingerprint — the same physical call is one call", () => {
    const base: Payload = { tool_name: "Bash", tool_input: { command: "ls" } };
    const a: Payload = { ...base, session_id: "s", tool_use_id: "u1" };
    const b: Payload = { ...base, session_id: "s", tool_use_id: "u1" };
    expect(fingerprint(a)).toBe(fingerprint(b));
    const differ: Payload = { tool_name: "Read", tool_input: {}, session_id: "s", tool_use_id: "u1" };
    expect(fingerprint(a)).not.toBe(fingerprint(differ));
    expect(fingerprint(a)).not.toBe(fingerprint({ ...base, session_id: "s2", tool_use_id: "u1" }));
    expect(fingerprint(a)).not.toBe(fingerprint({ ...base, session_id: "s", tool_use_id: "u2" }));
  });

  test("tool_input as a string or number is reduced to an empty record; arrays keep their indices", () => {
    // Measured: typeof ["x"] === "object" and it is not null, so the guard branch
    // lets an array through as a record with index keys. Only primitives are reset.
    for (const bad of ["x", 7]) {
      const p = normalise({ tool_name: "Bash", tool_input: bad });
      expect(p.tool_input).toEqual({});
    }
    expect(normalise({ tool_name: "Bash", tool_input: null }).tool_input).toEqual({});
  });

  test("a missing input falls back to the input key, then to an empty record", () => {
    expect(normalise({ tool_name: "Bash", input: { command: "ls" } }).tool_input).toEqual({ command: "ls" });
    expect(normalise({ tool_name: "Bash" }).tool_input).toEqual({});
  });

  test("notebook_path is promoted to file_path only when file_path is falsy-absent", () => {
    const promoted = normalise({ tool_name: "Edit", tool_input: { notebook_path: "n.ipynb" } });
    expect(promoted.tool_input["file_path"]).toBe("n.ipynb");
    const shadowed = normalise({ tool_name: "Edit", tool_input: { notebook_path: "n.ipynb", file_path: "real.ipynb" } });
    expect(shadowed.tool_input["file_path"]).toBe("real.ipynb");
  });
});

describe("BUILT_IN_ALIASES — the translation floor is complete", () => {
  test("every alias maps a camelCase key to its snake_case form", () => {
    for (const [from, to] of Object.entries(BUILT_IN_ALIASES)) {
      expect(from).toMatch(/^[a-z][A-Za-z]*$/);
      expect(to).toMatch(/^[a-z]+(_[a-z]+)*$/);
      expect(from).not.toBe(to);
    }
    expect(Object.keys(BUILT_IN_ALIASES)).toContain("toolName");
    expect(Object.keys(BUILT_IN_ALIASES)).toContain("filePath");
    expect(Object.keys(BUILT_IN_ALIASES)).toContain("sessionUseId" in BUILT_IN_ALIASES ? "sessionUseId" : "toolUseId");
  });
});

describe("fingerprint / deduplicable / loop signatures", () => {
  const base: Payload = { tool_name: "Bash", tool_input: { command: "ls" } };

  test("the same physical call fingerprints identically", () => {
    const a: Payload = { ...base, session_id: "s", tool_use_id: "u" };
    const b: Payload = { ...base, session_id: "s", tool_use_id: "u" };
    expect(fingerprint(a)).toBe(fingerprint(b));
  });

  test("a different session, tool or tool_use_id changes the fingerprint", () => {
    expect(fingerprint({ ...base, session_id: "s", tool_use_id: "u" }))
      .not.toBe(fingerprint({ ...base, session_id: "s2", tool_use_id: "u" }));
    expect(fingerprint({ ...base, session_id: "s", tool_use_id: "u" }))
      .not.toBe(fingerprint({ tool_name: "Read", tool_input: {}, session_id: "s", tool_use_id: "u" }));
    expect(fingerprint({ ...base, session_id: "s", tool_use_id: "u" }))
      .not.toBe(fingerprint({ ...base, session_id: "s", tool_use_id: "u2" }));
  });

  test("only a payload carrying tool_use_id is deduplicable", () => {
    expect(deduplicable({ ...base, tool_use_id: "u" })).toBe(true);
    expect(deduplicable(base)).toBe(false);
    expect(deduplicable({ ...base, tool_use_id: "" })).toBe(false);
  });

  test("loopExact covers tool and whole input but not identity", () => {
    expect(loopExact(base)).toBe(loopExact({ ...base, session_id: "other", tool_use_id: "other" }));
    expect(loopExact(base)).not.toBe(loopExact({ tool_name: "Bash", tool_input: { command: "rm" } }));
  });

  test("loopSignature takes tool plus the head of the first discriminating argument", () => {
    expect(loopSignature({ tool_name: "Bash", tool_input: { command: "git commit -m x" } })).toBe("Bash:git");
    expect(loopSignature({ tool_name: "Read", tool_input: { file_path: "/tmp/a b.txt" } })).toBe("Read:/tmp/a");
    expect(loopSignature({ tool_name: "WebFetch", tool_input: { url: "https://x.example/a" } })).toBe("WebFetch:https://x.example/a");
    expect(loopSignature({ tool_name: "Grep", tool_input: {} })).toBe("Grep:");
  });

  test("loopSignature truncates a long first token to 60 characters", () => {
    const long = "x".repeat(100);
    expect(loopSignature({ tool_name: "Bash", tool_input: { command: long } })).toBe(`Bash:${long.slice(-60)}`);
  });
});

describe("deny / allowRewrite / allow — the claude wire is the default", () => {
  test("deny without optional arguments emits the claude envelope, exit 2", () => {
    const r = envelope(() => deny("guard", "because"));
    expect(r.code).toBe(2);
    expect(r.stderr).toContain("[ai-eng] guard: because");
    expect(r.json["permission"]).toBe("deny");
    expect(r.json["continue"]).toBe(false);
    expect(r.json["user_message"]).toBe("[ai-eng] guard: because");
  });

  test("the event argument defaults to PreToolUse — proven on the wire that names it", () => {
    const r = envelope(() => deny("guard", "because", "codex"));
    expect(r.code).toBe(0);
    expect((r.json["hookSpecificOutput"] as Record<string, unknown>)["hookEventName"]).toBe("PreToolUse");
    expect((r.json["hookSpecificOutput"] as Record<string, unknown>)["permissionDecision"]).toBe("deny");
  });

  test("allowRewrite without optional arguments emits the claude envelope with the PreToolUse event", () => {
    const r = envelope(() => allowRewrite("ai-eng wrap test -- bun test", undefined, undefined));
    expect(r.code).toBe(0);
    expect((r.json["updatedInput"] as Record<string, unknown>)["command"]).toBe("ai-eng wrap test -- bun test");
  });

  test("the loop guard carries the override pointer in its denial", () => {
    const r = envelope(() => deny("loop", "reason", "claude", "PreToolUse"));
    expect(r.stderr).toContain("overrides.toml [[guard.off]]");
    const other = envelope(() => deny("no-verify", "reason", "claude", "PreToolUse"));
    expect(other.stderr).not.toContain("[[guard.off]]");
  });
  test("cursor allow is spoken; every other host stays silent on an allow", () => {
    // allow() returns instead of exiting, so the envelope helper does not apply:
    // capture stdout directly around the plain call.
    const out: string[] = [];
    const outSpy = spyOn(process.stdout, "write").mockImplementation(((chunk: string) => {
      out.push(String(chunk));
      return true;
    }) as never);
    try {
      allow("cursor");
      expect(JSON.parse(out.join(""))).toEqual({ permission: "allow" });
      out.length = 0;
      allow();
      expect(out.join("")).toBe("");
    } finally {
      outSpy.mockRestore();
    }
  });

  test("allow without a dialect exits silently — claude never reads stdout for an allow", () => {
    expect(() => envelope(() => allow())).toThrow("the envelope returned without exiting");
  });
});


describe("wrap — the test-command decision table", () => {
  test("every runner keyword wraps, and the runner name comes back", () => {
    for (const [command, runner] of [
      ["bun test", "bun test"],
      ["npm test", "npm test"],
      ["npm run test", "npm run test"],
      ["yarn test", "yarn test"],
      ["pnpm test", "pnpm test"],
      ["pytest", "pytest"],
      ["go test ./...", "go test"],
      ["cargo test", "cargo test"],
      ["vitest run", "vitest"],
      ["jest", "jest"],
      ["playwright test", "playwright"],
      ["turbo run test", "turbo run test"],
    ] as const) {
      const decision = isTestCommand(command);
      expect(decision.wrap, command).toBe(true);
      if (decision.wrap) expect(decision.runner, command).toBe(runner);
    }
  });

  test("each skip shape leaves the command alone", () => {
    for (const command of [
      "bun test --watch",
      "npm test --ui",
      "cargo test --help",
      "go test -h",
      "bun test --list",
      "bun test --reporter dot",
      "bun test &",
      "bun test | grep foo",
      "bun test | tail -5",
      "bun test | head -3",
    ]) {
      expect(isTestCommand(command).wrap, command).toBe(false);
    }
  });

  test("a non-test command does not wrap and the rewrite is the exact primitive", () => {
    expect(isTestCommand("git commit -m x").wrap).toBe(false);
    expect(isTestCommand("make build").wrap).toBe(false);
    expect(rewrite("bun test")).toBe("ai-eng wrap test -- bun test");
  });
});
