// tests/config-command.spec.ts — `ai-eng config` (surfaces rewritten in place, carriers
// written and taken back out) plus the frame layer every human verb presents through.
// Both are driven as behavior: what lands in .ai-engineering/config.toml and in the
// carrier files, the exit code, and the lines printed — never an internal.
// Env hygiene: AI_ENG_HOME/PI_CODING_AGENT_DIR point into a mkdtemp home and the cwd is
// put back after every test, so nothing here can reach the real ~/.claude or ~/.omp.
// The interactive prompt is fed through ui.ts's own scripted-input replay (a bare Enter
// or a real TTY would hang the suite).

import { afterEach, describe, expect, test } from "bun:test";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import type { PassThrough } from "node:stream";
import { stripVTControlCharacters } from "node:util";
import { configMain } from "../src/commands/config.ts";
import { isGoverned } from "../src/env.ts";
import { cancelled, confirmDefault, end, fail, frame, info, ok, pathList, scriptedInput, section, spinner, summary, warn } from "../src/ui.ts";

// scriptedInput() adds a data listener to the real stdin on every call; a file that
// drives several prompts crosses Node's cap of 10 and prints a leak warning in the middle
// of the assertions. The listeners are all consumed by their own queue.
process.stdin.setMaxListeners(0);

const roots: string[] = [];
const savedCwd = process.cwd();

afterEach(() => {
  process.chdir(savedCwd);
  for (const root of roots.splice(0)) rmSync(root, { recursive: true, force: true });
  delete process.env["AI_ENG_HOME"];
  delete process.env["PI_CODING_AGENT_DIR"];
});

function tempDir(prefix: string): string {
  const dir = mkdtempSync(join(tmpdir(), prefix));
  roots.push(dir);
  return dir;
}

const plain = (text: string): string => stripVTControlCharacters(text);

/** Everything written to stdout while `fn` runs (`out` ANSI-stripped, `raw` verbatim),
 *  plus what it returned. */
async function capture<T>(fn: () => Promise<T> | T): Promise<{ result: T; out: string; raw: string }> {
  const chunks: string[] = [];
  const original = process.stdout.write;
  process.stdout.write = ((chunk: string | Uint8Array): boolean => {
    chunks.push(typeof chunk === "string" ? chunk : Buffer.from(chunk).toString("utf8"));
    return true;
  }) as typeof process.stdout.write;
  try {
    return { result: await fn(), out: plain(chunks.join("")), raw: chunks.join("") };
  } finally {
    process.stdout.write = original;
  }
}

const SOURCE = '[surfaces]\nenabled = ["claude-code"]\n';

/** A repo that declared itself — .git plus the [surfaces] table the gate reads — with a
 *  sandboxed machine home beside it, which is where the machine carriers land. */
function governedRepo(config = SOURCE): { repo: string; home: string } {
  const repo = tempDir("ai-eng-config-repo-");
  mkdirSync(join(repo, ".git"));
  mkdirSync(join(repo, ".ai-engineering"), { recursive: true });
  writeFileSync(join(repo, ".ai-engineering", "config.toml"), config);
  const home = tempDir("ai-eng-config-home-");
  process.env["AI_ENG_HOME"] = home;
  process.env["PI_CODING_AGENT_DIR"] = join(home, "agent-dir");
  return { repo, home };
}

const configOf = (repo: string): string => readFileSync(join(repo, ".ai-engineering", "config.toml"), "utf8");

/** `configMain` resolves the repo from the cwd: the test owns the cwd for the call. */
function runConfig(repo: string, flags: { add?: string; remove?: string }): Promise<{ result: number; out: string }> {
  process.chdir(repo);
  return capture(() => configMain(flags));
}

/** Type a real pipe of keys into the prompt: scriptedInput() replays process.stdin as
 *  one keypress per tick, so the whole line can arrive as a single chunk. */
function type(text: string, afterMs = 20): void {
  setTimeout(() => process.stdin.emit("data", text), afterMs);
}

const tick = (ms: number): Promise<void> => new Promise((resolve) => setTimeout(resolve, ms));

async function until(check: () => boolean, budgetMs = 2000): Promise<void> {
  const deadline = Date.now() + budgetMs;
  while (!check() && Date.now() < deadline) await tick(10);
}

describe("ai-eng config · --add and --remove", () => {
  test("refuses outside a governed repo and invents nothing", async () => {
    const bare = tempDir("ai-eng-config-bare-");
    mkdirSync(join(bare, ".git"));

    const { result: code, out } = await runConfig(bare, { add: "cursor" });

    expect(code).toBe(2);
    expect(out).toContain("✗  you are not in a governed repo — run ai-eng init first");
    expect(out).toContain("└  Nothing changed.");
    expect(existsSync(join(bare, ".ai-engineering"))).toBe(false);
  });

  test("--add declares the surface and writes its adapter, leaving the user's blocks alone", async () => {
    const config = '# keep me\n[surfaces]\nenabled = ["claude-code"]\n\n[models]\ndecide = "x"\n';
    const { repo } = governedRepo(config);

    const { result: code, out } = await runConfig(repo, { add: "cursor" });

    expect(code).toBe(0);
    expect(configOf(repo)).toBe('# keep me\n[surfaces]\nenabled = ["claude-code", "cursor"]\n\n[models]\ndecide = "x"\n');
    expect(out).toContain("◆  Surfaces changed  ·  2 enabled: claude-code, cursor");
    expect(out).toContain("│  ✓ + cursor · adapter + skill mirror written");
    expect(out).toContain("└  Done. Run ai-eng doctor to verify.");

    // The adapter itself, not just the claim: a declaration nobody enforces is the bug
    // this verb exists to end.
    const carrier = JSON.parse(readFileSync(join(repo, ".cursor", "hooks.json"), "utf8")) as {
      hooks: { preToolUse: Array<{ command: string }> };
    };
    expect(carrier.hooks.preToolUse.map((hook) => hook.command)).toContain("ai-eng chain PreToolUse --surface cursor");
    expect(isGoverned(repo)).toBe(true);
  });

  test("--add refuses a surface with no adapter and leaves the config byte-identical", async () => {
    const { repo } = governedRepo();

    const { result: code, out } = await runConfig(repo, { add: "zed" });

    expect(code).toBe(2);
    expect(out).toContain('✗  "zed" has no adapter in this release — nothing would enforce its guards.');
    expect(configOf(repo)).toBe(SOURCE);
    expect(existsSync(join(repo, ".zed"))).toBe(false);
  });

  test("--add of an already-enabled surface is reported as unchanged and writes nothing", async () => {
    const { repo, home } = governedRepo();

    const { result: code, out } = await runConfig(repo, { add: "claude-code" });

    expect(code).toBe(0);
    expect(out).toContain("◆  surfaces unchanged  ·  1 enabled");
    expect(out).toContain("│  claude-code");
    expect(configOf(repo)).toBe(SOURCE);
    // Its carriers were the machine's business already: nothing is re-written behind the
    // user's back, and no adapter appears claiming it was.
    expect(existsSync(join(home, ".claude", "settings.json"))).toBe(false);
  });

  test("--add writes both carriers of a surface that reads the repo and the machine", async () => {
    const { repo, home } = governedRepo();

    const { result: code, out } = await runConfig(repo, { add: "copilot" });

    expect(code).toBe(0);
    expect(out).toContain("✓  ~/.copilot/hooks/ai-eng.json written (machine carrier)");
    expect(out).toContain("✓  .github/hooks/ai-eng.json written (repo carrier)");
    expect(existsSync(join(repo, ".github", "hooks", "ai-eng.json"))).toBe(true);
    expect(existsSync(join(home, ".copilot", "hooks", "ai-eng.json"))).toBe(true);
  });

  test("--remove takes our entries out of a shared settings file and keeps the user's", async () => {
    const { repo } = governedRepo('[surfaces]\nenabled = ["claude-code", "cursor"]\n');
    mkdirSync(join(repo, ".cursor"), { recursive: true });
    writeFileSync(
      join(repo, ".cursor", "hooks.json"),
      `${JSON.stringify({ version: 1, mine: [{ command: "my-own-hook.sh" }], hooks: { preToolUse: [{ command: "ai-eng chain PreToolUse --surface cursor" }] } }, null, 2)}\n`,
    );

    const { result: code, out } = await runConfig(repo, { remove: "cursor" });

    expect(code).toBe(0);
    expect(out).toContain("✓  .cursor/hooks.json: ai-eng entries removed, yours kept");
    expect(out).toContain("│  ✓ - cursor · off in this repo");
    expect(configOf(repo)).toBe(SOURCE);
    const kept = readFileSync(join(repo, ".cursor", "hooks.json"), "utf8");
    expect(kept).not.toContain("ai-eng chain");
    expect(JSON.parse(kept)).toEqual({ version: 1, mine: [{ command: "my-own-hook.sh" }] });
  });

  test("--remove deletes a carrier that held only ai-eng entries", async () => {
    const { repo } = governedRepo('[surfaces]\nenabled = ["claude-code", "cursor"]\n');
    mkdirSync(join(repo, ".cursor"), { recursive: true });
    writeFileSync(join(repo, ".cursor", "hooks.json"), `${JSON.stringify({ hooks: { preToolUse: [{ command: "ai-eng chain PreToolUse --surface cursor" }] } }, null, 2)}\n`);

    const { result: code, out } = await runConfig(repo, { remove: "cursor" });

    expect(code).toBe(0);
    expect(out).toContain("✓  .cursor/hooks.json removed (it held only ai-eng entries)");
    expect(existsSync(join(repo, ".cursor", "hooks.json"))).toBe(false);
    expect(configOf(repo)).toBe(SOURCE);
  });

  test("--remove leaves alone a carrier it cannot parse and says why", async () => {
    const { repo } = governedRepo('[surfaces]\nenabled = ["claude-code", "cursor"]\n');
    mkdirSync(join(repo, ".cursor"), { recursive: true });
    writeFileSync(join(repo, ".cursor", "hooks.json"), "{ not json\n");

    const { result: code, out } = await runConfig(repo, { remove: "cursor" });

    expect(code).toBe(0);
    expect(out).toContain("▲  .cursor/hooks.json left alone — not JSON this installer can rewrite without reformatting it");
    expect(readFileSync(join(repo, ".cursor", "hooks.json"), "utf8")).toBe("{ not json\n");
  });

  test("--remove of a repo-less surface rewrites the declaration and leaves the disk alone", async () => {
    const { repo, home } = governedRepo('[surfaces]\nenabled = ["claude-code", "pi"]\n');

    const pi = await runConfig(repo, { remove: "pi" });
    expect(pi.result).toBe(0);
    expect(pi.out).toContain("◆  Surfaces changed  ·  1 enabled: claude-code");
    expect(configOf(repo)).toBe(SOURCE);
    expect(existsSync(join(repo, ".pi"))).toBe(false);
    expect(existsSync(join(home, "agent-dir"))).toBe(false);

    // An id that is not a surface at all is a no-op, not a crash.
    const unknown = await runConfig(repo, { remove: "nope" });
    expect(unknown.result).toBe(0);
    expect(unknown.out).toContain("◆  surfaces unchanged  ·  1 enabled");
    expect(configOf(repo)).toBe(SOURCE);
  });

  test("the picker's cancel leaves the declaration and the carriers as they were", async () => {
    const { repo } = governedRepo('[surfaces]\nenabled = ["claude-code", "cursor"]\n');
    mkdirSync(join(repo, ".cursor"), { recursive: true });
    writeFileSync(join(repo, ".cursor", "hooks.json"), '{ "mine": true }\n');

    process.chdir(repo);
    const answer = capture(() => configMain({}));
    type("\x03");

    const { result: code, out } = await answer;
    expect(code).toBe(0);
    expect(out).toContain("Which agent surfaces is this project governed on? (ticked = installed)");
    expect(out).toContain("└  Nothing changed.");
    expect(configOf(repo)).toBe('[surfaces]\nenabled = ["claude-code", "cursor"]\n');
    expect(readFileSync(join(repo, ".cursor", "hooks.json"), "utf8")).toBe('{ "mine": true }\n');
  });

  test("the picker's submission removes the surface that was unticked", async () => {
    const { repo, home } = governedRepo('[surfaces]\nenabled = ["claude-code", "cursor"]\n');
    mkdirSync(join(repo, ".cursor"), { recursive: true });
    writeFileSync(join(repo, ".cursor", "hooks.json"), '{ "mine": true }\n');

    process.chdir(repo);
    const answer = capture(() => configMain({}));
    // Space untick the row under the cursor (the first surface), Enter submits.
    type(" \n");

    const { result: code, out } = await answer;
    expect(code).toBe(0);
    expect(out).toContain("◆  Surfaces changed  ·  1 enabled: cursor");
    expect(out).toContain("│  ✓ - claude-code · off in this repo");
    expect(configOf(repo)).toBe('[surfaces]\nenabled = ["cursor"]\n');
    // Cursor stayed declared, so its carrier was neither rewritten nor taken away.
    expect(readFileSync(join(repo, ".cursor", "hooks.json"), "utf8")).toBe('{ "mine": true }\n');
    expect(existsSync(join(home, ".claude", "settings.json"))).toBe(false);
  });

  test("the picker's submission installs the surface that was ticked", async () => {
    const { repo, home } = governedRepo('[surfaces]\nenabled = ["claude-code", "cursor"]\n');

    process.chdir(repo);
    const answer = capture(() => configMain({}));
    // Down to the second row (Oh My Pi, in-process: no repo carrier), space, Enter.
    type("\x1b[B \n");

    const { result: code, out } = await answer;
    expect(code).toBe(0);
    expect(out).toContain("│  ✓ + oh-my-pi · adapter + skill mirror written");
    expect(out).toContain("✓  ~/.omp/agent/hooks/pre/ai-eng.ts written (machine carrier)");
    expect(configOf(repo)).toBe('[surfaces]\nenabled = ["claude-code", "cursor", "oh-my-pi"]\n');
    // An in-process host is installed where the host reads it: its agent dir, not ours.
    expect(existsSync(join(home, "agent-dir", "hooks", "pre", "ai-eng.ts"))).toBe(true);
  });
});

describe("ui · the frame layer", () => {
  test("a second frame rides the open one as a line instead of opening another", async () => {
    const { out } = await capture(() => {
      frame("Configuration · ai-eng 2.1.0");
      frame("Update");
      end("Done.");
      frame("Doctor");
      end("Done.");
      return 0;
    });

    expect(out.match(/┌/g)).toHaveLength(2);
    expect(out).toContain("┌  Configuration · ai-eng 2.1.0");
    expect(out).toContain("◆  Update");
    expect(out).toContain("└  Done.");
    expect(out.indexOf("┌  Doctor")).toBeGreaterThan(out.indexOf("└  Done."));
  });

  test("cancelling closes the frame, with the default message or a caller's", async () => {
    const { out } = await capture(() => {
      frame("Configuration · ai-eng 2.1.0");
      cancelled();
      frame("Configuration · ai-eng 2.1.0");
      cancelled("Nothing changed.");
      frame("Doctor");
      end("Done.");
      return 0;
    });

    expect(out).toContain("└  Cancelled.");
    expect(out).toContain("└  Nothing changed.");
    expect(out.match(/┌/g)).toHaveLength(3);
  });

  test("a section renders the mark grammar, the gray tail and the note", async () => {
    const { out } = await capture(() => {
      section(
        "Surfaces changed",
        [
          { mark: "ok", text: "+ cursor", dim: "adapter + skill mirror written" },
          { mark: "info", text: "neutral" },
          { mark: "warn", text: "attention" },
          { mark: "fail", text: "blocked" },
          { mark: "muted", text: "bulk row" },
          { mark: "sub", text: ".cursor/hooks.json" },
        ],
        "2 enabled: claude-code, cursor",
      );
      return 0;
    });
    const lines = out.split("\n");

    expect(lines).toContain("◆  Surfaces changed  ·  2 enabled: claude-code, cursor");
    expect(lines).toContain("│  ✓ + cursor · adapter + skill mirror written");
    expect(lines).toContain("│  ◆ neutral");
    expect(lines).toContain("│  ▲ attention");
    expect(lines).toContain("│  ✗ blocked");
    // Muted carries no mark at all: a bulk row is not a fact about the step.
    expect(lines).toContain("│  bulk row");
    expect(lines).toContain("│      ↳ .cursor/hooks.json");
  });

  test("a section without rows or note is just its title", async () => {
    const { out } = await capture(() => {
      section("Mirrors verified");
      return 0;
    });

    expect(out.split("\n")).toContain("◆  Mirrors verified");
  });

  test("pathList groups the files of a directory onto one line", async () => {
    const { result: value } = await capture(() => pathList([".git/hooks/pre-commit", ".git/hooks/commit-msg", ".git/hooks/pre-push", ".cursor/hooks.json"]));

    expect(value).toBe(".git/hooks/pre-commit · commit-msg · pre-push  ·  .cursor/hooks.json");
    expect(pathList([])).toBe("");
    // A path with no directory of its own still comes back named.
    expect(pathList(["AGENTS.md"])).toContain("AGENTS.md");
  });

  test("the line helpers print one marked line each", async () => {
    const { out } = await capture(() => {
      ok("adapter written");
      info("nothing to do");
      warn("left alone");
      fail("not a governed repo");
      return 0;
    });

    expect(out).toContain("✓  adapter written");
    expect(out).toContain("◆  nothing to do");
    expect(out).toContain("▲  left alone");
    expect(out).toContain("✗  not a governed repo");
  });

  test("summary counts the checks and says check in the singular", async () => {
    const single = await capture(() => {
      summary(1, 0, 0);
      return 0;
    });
    const many = await capture(() => {
      summary(3, 1, 2);
      return 0;
    });

    expect(single.out).toContain("◆  1 check: 1 OK · 0 WARN · 0 FAIL");
    expect(many.out).toContain("◆  6 checks: 3 OK · 1 WARN · 2 FAIL");
  });

  test("the spinner is silent off a TTY until it is stopped with a message", async () => {
    const silent = await capture(() => {
      const spin = spinner();
      spin.start("installing");
      spin.stop();
      return 0;
    });
    const spoken = await capture(() => {
      spinner().stop("installed");
      return 0;
    });

    expect(silent.raw).toBe("");
    expect(spoken.out).toContain("◆  installed");
  });

  test("the spinner on a TTY is clack's, cursor codes and all", async () => {
    const descriptor = Object.getOwnPropertyDescriptor(process.stdout, "isTTY");
    Object.defineProperty(process.stdout, "isTTY", { value: true, configurable: true });
    try {
      const { raw } = await capture(() => {
        const spin = spinner();
        spin.start("installing");
        spin.stop("installed");
        return 0;
      });

      expect(raw).toContain("\u001b[?25l");
      expect(raw).toContain("\u001b[?25h");
      expect(plain(raw)).toContain("installed");
    } finally {
      if (descriptor) Object.defineProperty(process.stdout, "isTTY", descriptor);
      else delete (process.stdout as unknown as Record<string, unknown>)["isTTY"];
    }
  });

  test("scriptedInput replays a piped chunk as one keypress per key", async () => {
    const script = scriptedInput() as PassThrough;
    const keys: Array<{ sequence: string; name: string }> = [];
    script.on("keypress", (sequence: string, key: { name: string }) => keys.push({ sequence, name: key.name }));

    type("\x1b[A\x1b[B\n \t\x03q");
    await until(() => keys.length === 7);

    expect(keys).toEqual([
      { sequence: "\x1b[A", name: "up" },
      { sequence: "\x1b[B", name: "down" },
      { sequence: "\n", name: "return" },
      { sequence: " ", name: "space" },
      { sequence: "\t", name: "tab" },
      { sequence: "\x03", name: "cancel" },
      { sequence: "q", name: "q" },
    ]);
  });

  test("scriptedInput emits nothing once the queue is exhausted", async () => {
    const script = scriptedInput() as PassThrough;
    const keys: string[] = [];
    script.on("keypress", (sequence: string) => keys.push(sequence));

    process.stdin.emit("data", Buffer.from("a\n"));
    await until(() => keys.length === 2);
    await tick(60);

    expect(keys).toEqual(["a", "\n"]);
  });

  test("scriptedInput hands back the real stdin when stdin is a TTY", async () => {
    const descriptor = Object.getOwnPropertyDescriptor(process.stdin, "isTTY");
    Object.defineProperty(process.stdin, "isTTY", { value: true, configurable: true });
    try {
      const { result: value } = await capture(() => scriptedInput());
      expect(value).toBe(process.stdin);
      expect(process.stdin.getMaxListeners()).toBe(0);
    } finally {
      if (descriptor) Object.defineProperty(process.stdin, "isTTY", descriptor);
      else delete (process.stdin as unknown as Record<string, unknown>)["isTTY"];
    }
  });

  test("confirmDefault answers with the choice, and with the initial value on Enter or cancel", async () => {
    const script = scriptedInput() as PassThrough;
    const answers: boolean[] = [];
    const ask = async (): Promise<void> => {
      answers.push(await confirmDefault("Install the git hooks?", true, script));
    };

    const onEnter = ask();
    type("\n");
    await onEnter;

    const onNo = ask();
    type("n");
    await onNo;

    const onCancel = ask();
    type("\x03");
    await onCancel;

    expect(answers).toEqual([true, false, true]);
  });
});

describe("the rewrite never turns a governed repo ungoverned (§09.2 regression)", () => {
  // A second [surfaces] table appended to a file that already had one is not cosmetic:
  // the file stops parsing, declaration() reports the repo undeclared, and the verb whose
  // whole job is the declaration switches governance off at exit 0 — a fail-open.
  test("an enabled key indented under [surfaces] is rewritten in place, and the table stays single", async () => {
    const { repo } = governedRepo('[surfaces]\n  enabled = ["claude-code"]\n');
    const { result } = await runConfig(repo, { add: "cursor" });

    expect(result).toBe(0);
    const config = configOf(repo);
    expect(config.match(/^\[surfaces\]$/gm)).toHaveLength(1);
    expect(config).toContain('enabled = ["claude-code", "cursor"]');
    expect(isGoverned(repo)).toBe(true);
  });

  test("the [notices] key of the same name is not the key this verb manages", async () => {
    const { repo } = governedRepo('[notices]\nenabled = true\n\n[surfaces]\nenabled = ["claude-code"]\n');
    const { result } = await runConfig(repo, { add: "cursor" });

    expect(result).toBe(0);
    expect(configOf(repo)).toBe('[notices]\nenabled = true\n\n[surfaces]\nenabled = ["claude-code", "cursor"]\n');
    expect(isGoverned(repo)).toBe(true);
  });

  test("a table after [surfaces] keeps its own enabled key", async () => {
    const { repo } = governedRepo('[surfaces]\nenabled = ["claude-code"]\n\n[notices]\nenabled = false\n');
    const { result } = await runConfig(repo, { add: "cursor" });

    expect(result).toBe(0);
    expect(configOf(repo)).toBe('[surfaces]\nenabled = ["claude-code", "cursor"]\n\n[notices]\nenabled = false\n');
    expect(isGoverned(repo)).toBe(true);
  });
});
