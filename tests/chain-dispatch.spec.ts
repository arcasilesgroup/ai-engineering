// tests/chain-dispatch.spec.ts — the dispatcher's own wire: routing, the verdict
// cache, fail-closed, and the outcome shape.
//
// The guards have their own suites. This file is about the table between them and
// the host: which guard runs for which tool on which event (TABLE is what emits),
// what comes back when several run (ran order, first deny wins), what a cached
// verdict does to a second delivery of the same physical call, and the two
// fail-closed boundaries (unreadable payload, crashing guard).

import { describe, expect, test, afterAll, beforeEach } from "bun:test";
import { randomUUID } from "node:crypto";
import { spawnSync } from "node:child_process";
import { mkdtempSync, mkdirSync, rmSync, writeFileSync, existsSync, readFileSync, readdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { runChain, TABLE, type ChainOutcome } from "../src/chain/mod.ts";

const cli = join(import.meta.dir, "..", "src", "cli.ts");
let scratch: string;
let machineHome: string;
let cwdBefore: string;
const homeBefore = process.env.AI_ENG_HOME;
beforeEach(() => {
  if (!scratch) {
    scratch = mkdtempSync(join(tmpdir(), "ai-eng-dispatch-"));
    // The loop guard keeps its per-session window under the machine home. Left on the
    // real one, the fixed "dispatch" session carries calls over from earlier and
    // concurrent runs, and a third `bun test` in the window is a loop deny, not a rewrite.
    // It sits outside the scratch repo: a home inside the repo would be ignored.
    machineHome = mkdtempSync(join(tmpdir(), "ai-eng-dispatch-home-"));
    process.env.AI_ENG_HOME = machineHome;
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
  if (homeBefore === undefined) delete process.env.AI_ENG_HOME;
  else process.env.AI_ENG_HOME = homeBefore;
  if (scratch) rmSync(scratch, { recursive: true, force: true });
  if (machineHome) rmSync(machineHome, { recursive: true, force: true });
});

const RUN = (payload: Record<string, unknown>, event = "PreToolUse"): ChainOutcome =>
  runChain(payload, event, { inProcess: true });
const bash = (command: string, id = "u1"): Record<string, unknown> =>
  ({ tool_name: "Bash", tool_input: { command }, tool_use_id: id, session_id: "dispatch" });
const writeTool = (path: string, id = "u1"): Record<string, unknown> =>
  ({ tool_name: "Write", tool_input: { file_path: path, content: "x" }, tool_use_id: id, session_id: "dispatch" });

function stopPlan(): Record<string, unknown> {
  const gate = (status: string, attempts: number) => ({ status, attempts, findings: [] });
  return {
    slug: "dispatch",
    feature: "Dispatch",
    summary: "Stop routing fixture",
    lifecycle: {
      phase: "implementation",
      plan_approval: "approved",
      app_review: "not-started",
      base_ref: null,
      reviewed_base: null,
      reviewed_feature: null,
    },
    halted: null,
    assumptions: [],
    notes: [],
    checkpoints: [{
      id: 1,
      title: "Active checkpoint",
      goal: "Keep Stop gated",
      tasks: [],
      files: [],
      acceptance: [],
      verify: [],
      ui: null,
      status: "in_progress",
      changed_files: [],
      gates: {
        behavior: gate("failed", 1),
        ui: gate("pending", 0),
        review: gate("pending", 0),
      },
    }],
  };
}

describe("TABLE — the routing invariants the outcomes cannot show", () => {
  test("every matcher is anchored: a prefix of a tool name must not sneak through", () => {
    for (const rows of [TABLE.PreToolUse!, TABLE.PostToolUse!, TABLE.UserPromptSubmit!]) {
      for (const row of rows) {
        expect(row.matcher.source.startsWith("^")).toBe(true);
        expect(row.matcher.source.endsWith("$")).toBe(true);
      }
    }
  });

  test("checkpoint guard routes every governed tool and the Stop event", () => {
    const preToolCheckpoint = (TABLE.PreToolUse ?? []).filter((row) => String(row.name) === "checkpoint");
    expect(preToolCheckpoint).toHaveLength(1);
    for (const tool of ["Write", "Edit", "MultiEdit", "Task", "Agent", "Bash"]) {
      expect(preToolCheckpoint[0]!.matcher.test(tool)).toBe(true);
    }

    const stopCheckpoint = (TABLE["Stop"] ?? []).filter((row) => String(row.name) === "checkpoint");
    expect(stopCheckpoint).toHaveLength(1);
    expect(stopCheckpoint[0]!.matcher.test("")).toBe(true);
  });
});

describe("UserPromptSubmit — the spoken-secret arm", () => {
  const promptRun = (prompt: string): ChainOutcome =>
    RUN({ prompt, session_id: "prompt-arm" }, "UserPromptSubmit");

  test("a prompt carrying a spoken credential is denied, by name and never by value", () => {
    const outcome = promptRun("my staging password is velvet-anchor-thistle-21");
    expect(outcome.action).toBe("deny");
    if (outcome.action === "deny") {
      expect(outcome.by).toBe("spoken-secret");
      expect(outcome.reason).toInclude("prompt-staging-password");
      expect(outcome.reason).not.toInclude("velvet-anchor-thistle-21");
    }
  });

  test("an ordinary prompt passes with the guard in the ran list", () => {
    const outcome = promptRun("add a dark mode toggle to the settings page");
    expect(outcome.action).toBe("allow");
    if (outcome.action === "allow") expect(outcome.guards).toEqual(["spoken-secret"]);
  });

  test("a payload with no prompt field is out of scope: nothing runs on it", () => {
    const outcome = RUN({ session_id: "no-prompt" }, "UserPromptSubmit");
    expect(outcome.action).toBe("allow");
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
      expect(outcome.command).toBe(`ai-eng wrap test --base64 ${Buffer.from("bun test").toString("base64url")}`);
      expect(outcome.guards).toContain("wrap");
      expect(outcome.guards).toContain("loop");
      expect(outcome.guards).toContain("checkpoint");
    }
  });

  test("a redelivered wrapped call rewrites again — a rewrite is never cached as a deny", () => {
    // Pre-fix, rememberVerdict stored wrap's deny:true shape and the second delivery
    // of the same physical call replayed it as a hard deny (audit run-1).
    const wrapped = { ...bash("bun test", "u-rewrite"), session_id: `rewrite-redelivery-${randomUUID()}` };
    const first = RUN(wrapped);
    expect(first.action).toBe("rewrite");
    const second = RUN(wrapped);
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

  test("a nested .git marker cannot escape a governed ancestor", () => {
    const nested = join(scratch, "nested");
    mkdirSync(join(nested, ".git"), { recursive: true });
    const target = join(scratch, ".ai-engineering", "config.toml");
    const outcome = RUN({ ...bash(`rm -f ${target}`), cwd: nested });
    expect(outcome.action).toBe("deny");
    if (outcome.action === "deny") expect(outcome.by).toBe("self-protect");
    const relative = RUN({ ...bash("rm -f ../.ai-engineering/config.toml", "u-nested-relative"), cwd: nested });
    expect(relative.action).toBe("deny");
    const hookBypass = RUN({ ...bash("git -C .. commit --no-verify -m x", "u-nested-no-verify"), cwd: nested });
    expect(hookBypass.action).toBe("deny");
    // Outermost governed wins, so a config written ABOVE the repo would move the root.
    const hijack = runChain(
      { sessionId: `copilot-hijack-${randomUUID()}`, toolName: "create", toolArgs: { path: "../.ai-engineering/config.toml", file_text: "[surfaces]\nenabled = []\n" }, cwd: scratch },
      "PreToolUse",
      { inProcess: true, surface: "copilot-cli" },
    );
    expect(hijack.action).toBe("deny");
  });

  test("Copilot apply_patch is judged per file: governed or ambiguous denies, plain source passes", () => {
    const run = randomUUID();
    const copilot = (toolArgs: unknown, id: string) => runChain(
      { sessionId: `copilot-patch-${id}-${run}`, toolName: "apply_patch", toolArgs, cwd: scratch },
      "PreToolUse",
      { inProcess: true, surface: "copilot-cli" },
    );
    const governed = copilot("*** Begin Patch\n*** Add File: notes.md\n+x\n*** Update File: src/a.ts\n*** Move to: .ai-engineering/config.toml\n*** End Patch", "governed");
    expect(governed.action).toBe("deny");
    if (governed.action === "deny") expect(governed.by).toBe("self-protect");
    const ambiguous = copilot("*** Begin Patch\n*** Add File: notes.md\n+x\n*** Rename File: .ai-engineering/config.toml\n*** End Patch", "ambiguous");
    expect(ambiguous.action).toBe("deny");
    if (ambiguous.action === "deny") expect(ambiguous.by).toBe("chain");
    expect(copilot({ input: "*** Begin Patch\n*** Add File: notes.md\n+x\n*** End Patch" }, "plain").action).toBe("allow");
  });

  test("Copilot camelCase Bash payloads reach the same write guard", () => {
    const target = join(scratch, ".ai-engineering", "config.toml");
    const outcome = runChain({
      sessionId: "copilot-session",
      toolName: "bash",
      toolArgs: JSON.stringify({ command: `echo x > ${target}` }),
      cwd: scratch,
    }, "PreToolUse", { inProcess: true, surface: "copilot-cli" });
    expect(outcome.action).toBe("deny");
    if (outcome.action === "deny") expect(outcome.by).toBe("self-protect");
  });

  test("Copilot interactive write and patch tools fail closed", () => {
    for (const toolName of ["write_bash", "apply_patch"]) {
      const outcome = runChain({
        sessionId: `copilot-${toolName}`,
        toolName,
        toolArgs: { input: "echo x > .ai-engineering/config.toml{enter}" },
        cwd: scratch,
      }, "PreToolUse", { inProcess: true, surface: "copilot-cli" });
      expect(outcome.action, toolName).toBe("deny");
      if (outcome.action === "deny") expect(outcome.by, toolName).toBe("chain");
    }
  });

  test("a PreToolUse payload without a tool name is denied", () => {
    const outcome = RUN({ tool_use_id: "e1", session_id: "dispatch" });
    expect(outcome.action).toBe("deny");
    if (outcome.action === "deny") expect(outcome.by).toBe("chain");
  });
});

describe("Copilot deliveries — one physical call, every registration", () => {
  // Copilot runs the chain once per registered carrier: the repo `.github/hooks` entry and
  // the machine `preToolUse` (copilot-cli) plus `PreToolUse` (copilot) entries. The shapes
  // below are the ones recorded in a real session's hook log.
  const vscodeName: Record<string, string> = { bash: "Bash", view: "Read", apply_patch: "Edit" };
  const deliver = (format: "cli" | "vscode", tool: string, args: unknown, session: string, at: number): ChainOutcome =>
    runChain(
      format === "cli"
        ? { sessionId: session, timestamp: at, cwd: scratch, toolName: tool, toolArgs: args }
        : { hook_event_name: "PreToolUse", session_id: session, timestamp: new Date(at).toISOString(), cwd: scratch, tool_name: vscodeName[tool] ?? tool, tool_input: args },
      "PreToolUse",
      { inProcess: true, surface: format === "cli" ? "copilot-cli" : "copilot" },
    );
  /** One call as the host delivers it: the same payload to all three registrations. */
  const call = (tool: string, args: unknown, session: string, at: number): ChainOutcome[] =>
    [deliver("cli", tool, args, session, at), deliver("cli", tool, args, session, at), deliver("vscode", tool, args, session, at)];
  const patch = "*** Begin Patch\n*** Update File: src/a.ts\n@@\n-a\n+b\n*** End Patch";
  const MINUTE = 60_000;

  test("a first call reaching three registrations is judged once, not as three attempts", () => {
    const run = randomUUID();
    const calls: Array<[string, unknown]> = [
      ["skill", { skill: "ai-explore" }],
      ["task_complete", { summary: "Read-only repository review is complete." }],
      ["ask_user", { message: "¿Cómo prefieres desbloquearlo?" }],
      ["view", { path: join(scratch, "src", "a.ts") }],
      ["bash", { command: "git --no-pager status --short --branch", description: "Check current worktree status" }],
      ["apply_patch", patch],
      ["codegraph-codegraph_explore", { projectPath: scratch, query: "Find runtime imports", maxFiles: 12 }],
    ];
    calls.forEach(([tool, args], index) => {
      for (const outcome of call(tool, args, `first-${run}-${index}`, 1_000_000)) expect(outcome.action, tool).not.toBe("deny");
    });
  });

  test("repeated read and control calls keep working", () => {
    const session = `read-control-${randomUUID()}`;
    for (let attempt = 0; attempt < 4; attempt++) {
      const at = 2_000_000 + attempt * MINUTE;
      for (const [tool, args] of [
        ["view", { path: join(scratch, "src", "a.ts") }],
        ["task_complete", { summary: "done" }],
        ["report_intent", { intent: "Reviewing" }],
        ["codegraph-codegraph_explore", { projectPath: scratch, query: "callers of runChain" }],
      ] as Array<[string, unknown]>) {
        for (const outcome of call(tool, args, session, at + 1)) expect(outcome.action, `${tool} #${attempt + 1}`).not.toBe("deny");
      }
    }
  });

  test("retrying the same action is still bounded", () => {
    for (const [tool, args] of [
      ["bash", { command: "rm -rf build", description: "Clean" }],
      ["apply_patch", patch],
    ] as Array<[string, unknown]>) {
      const session = `retry-${randomUUID()}`;
      expect(call(tool, args, session, 3_000_000).every((outcome) => outcome.action !== "deny"), tool).toBe(true);
      expect(call(tool, args, session, 3_000_000 + MINUTE).every((outcome) => outcome.action !== "deny"), tool).toBe(true);
      const third = call(tool, args, session, 3_000_000 + 2 * MINUTE);
      expect(third.some((outcome) => outcome.action === "deny" && outcome.by === "loop"), tool).toBe(true);
    }
  });

  test("unknown MCP tools and ambiguous patches still deny, and say why", () => {
    const run = randomUUID();
    const unknown = deliver("cli", "github-mcp-server-create_pull_request", { title: "x" }, `mcp-${run}`, 4_000_000);
    expect(unknown.action).toBe("deny");
    if (unknown.action === "deny") expect(unknown.reason).toContain("github-mcp-server-create_pull_request");
    const ambiguous = deliver("cli", "apply_patch", "*** Begin Patch\n***Update File: .ai-engineering/config.toml\n*** End Patch", `amb-${run}`, 4_000_000);
    expect(ambiguous.action).toBe("deny");
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
    if (outcome.action === "deny") {
      expect(outcome.by).toBe("chain");
      expect(outcome.reason).toBe("BLOCKED: the hook payload could not be read, so nothing here can say whether this action is safe.");
    }
  });

  test("a payload that throws while being normalized is denied, never escaped", () => {
    const hostile = { get tool_name(): string { throw new Error("getter boom"); } };
    const outcome = runChain(hostile as unknown as Record<string, unknown>, "PreToolUse", { inProcess: true });
    expect(outcome.action).toBe("deny");
    if (outcome.action === "deny") expect(outcome.reason).toBe("BLOCKED: the hook payload could not be read, so nothing here can say whether this action is safe.");
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

describe("Stop — the checkpoint guard reaches the harness event envelope", () => {
  test("an open checkpoint is denied with a Codex Stop envelope", () => {
    const emptyGitConfig = join(scratch, "empty-gitconfig");
    writeFileSync(emptyGitConfig, "");
    const gitEnv = {
      ...process.env,
      GIT_CONFIG_GLOBAL: emptyGitConfig,
      GIT_CONFIG_SYSTEM: emptyGitConfig,
      GIT_TERMINAL_PROMPT: "0",
    };
    const git = (args: string[]) => {
      const result = spawnSync("git", args, { cwd: scratch, encoding: "utf8", env: gitEnv });
      if (result.status !== 0) throw new Error(`git ${args.join(" ")} failed: ${result.stderr}`);
    };
    git(["init", "-q", "-b", "main"]);
    git(["config", "user.name", "Chain Dispatch Test"]);
    git(["config", "user.email", "chain-dispatch@example.invalid"]);
    writeFileSync(join(scratch, "base.txt"), "base\n");
    git(["add", "base.txt"]);
    git(["commit", "-q", "-m", "base"]);

    const planPath = join(scratch, ".ai-engineering", "workflow", "checkpoints", "dispatch.json");
    mkdirSync(join(scratch, ".ai-engineering", "workflow", "checkpoints"), { recursive: true });
    writeFileSync(planPath, JSON.stringify(stopPlan()));
    const transcriptPath = join(scratch, "transcript.jsonl");
    writeFileSync(
      transcriptPath,
      '{"name":"Skill","input":{"skill":"ai-orchestrator"}} read .ai-engineering/workflow/checkpoints/dispatch.json\n',
    );
    expect(readFileSync(planPath, "utf8")).toContain('"status":"failed"');
    expect(readFileSync(transcriptPath, "utf8")).toContain(".ai-engineering/workflow/checkpoints/dispatch.json");

    const result = spawnSync(
      process.execPath,
      [cli, "chain", "Stop", "--surface", "codex"],
      {
        cwd: scratch,
        encoding: "utf8",
        env: {
          ...gitEnv,
          AI_ENG_HOME: join(scratch, "ai-eng-home"),
          AI_ENG_NO_UPDATE_NOTICES: "1",
        },
        input: JSON.stringify({
          hook_event_name: "Stop",
          session_id: "dispatch-stop-envelope",
          transcript_path: transcriptPath,
          cwd: scratch,
        }),
      },
    );

    expect(result.status).toBe(0);
    expect(result.stdout.trim()).not.toBe("");
    expect(JSON.parse(result.stdout)).toEqual({
      hookSpecificOutput: {
        hookEventName: "Stop",
        permissionDecision: "deny",
        permissionDecisionReason: expect.stringContaining("checkpoint"),
      },
    });
  });
});
