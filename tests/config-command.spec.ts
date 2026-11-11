// tests/config-command.spec.ts — `ai-eng config` (surfaces rewritten in place, carriers
// written and taken back out) plus the frame layer every human verb presents through.
// Both are driven as behavior: what lands in .ai-engineering/config.toml and in the
// carrier files, the exit code, and the lines printed — never an internal.
// Env hygiene: AI_ENG_HOME/PI_CODING_AGENT_DIR point into a mkdtemp home and the cwd is
// put back after every test, so nothing here can reach the real ~/.claude or ~/.omp.
// The interactive prompt is fed through ui.ts's own scripted-input replay (a bare Enter
// or a real TTY would hang the suite).

import { afterAll, afterEach, describe, expect, test } from "bun:test";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, realpathSync, renameSync, rmSync, symlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import type { PassThrough } from "node:stream";
import { stripVTControlCharacters } from "node:util";
import { configMain } from "../src/commands/config.ts";
import { canonSkills, embeddedPath } from "../src/embed.ts";
import { isGoverned } from "../src/env.ts";
import { installCanon } from "../src/surfaces/canon-install.ts";
import { cancelled, confirmDefault, end, fail, frame, info, ok, pathList, scriptedInput, section, spinner, summary, warn } from "../src/ui.ts";
import { restoreSandboxEnv, snapshotSandboxEnv } from "./fixtures/sandbox-env.ts";
import { usePrivateStdin } from "./fixtures/private-stdin.ts";
import { VERSION } from "../src/version.ts";

// The keys go through a stdin only this suite writes to: on the runner's real one, a stray
// byte from whatever launched `bun test` lands in the open picker (tests/fixtures/private-stdin.ts).
const stdin = usePrivateStdin();
afterAll(() => stdin.restore());

const roots: string[] = [];
const savedCwd = process.cwd();
const savedEnv = snapshotSandboxEnv();

afterEach(() => {
  process.chdir(savedCwd);
  for (const root of roots.splice(0)) rmSync(root, { recursive: true, force: true });
  restoreSandboxEnv(savedEnv);
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

function expectFullCanonInstalled(home: string): void {
  const inventory = canonSkills();
  expect(inventory.size).toBeGreaterThan(0);
  for (const [path, ref] of inventory) {
    expect(readFileSync(join(home, path), "utf8")).toBe(readFileSync(embeddedPath(ref), "utf8"));
  }
}

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

  test("--add changes only the surface setting and preserves a legacy pack block and full canon", async () => {
    const config =
      '# keep me\n[surfaces]\nenabled = ["claude-code"]\n\n[canon]\npacks = ["triage"]\n\n[models]\ndecide = "x"\n';
    const { repo, home } = governedRepo(config);
    installCanon(VERSION);

    const { result } = await runConfig(repo, { add: "cursor" });

    expect(result).toBe(0);
    expect(configOf(repo)).toBe(
      '# keep me\n[surfaces]\nenabled = ["claude-code", "cursor"]\n\n[canon]\npacks = ["triage"]\n\n[models]\ndecide = "x"\n',
    );
    expectFullCanonInstalled(home);
  });

  // Every byte outside the one list survives, whatever shape the legacy pack key had.
  test.each([
    ["no legacy pack block", ""],
    ["an empty pack list", "[canon]\npacks = []\n\n"],
    ["a commented multi-line pack list", '[canon] # legacy, ignored now\n# packs once filtered the canon\npacks = [\n  "triage", # keep\n  "debug",\n]\n\n'],
    ["a pack value that is not a list", '[canon]\npacks = "everything"\n\n'],
  ])("--add then --remove change only the surface list beside %s", async (_shape, legacy) => {
    const layout = (list: string): string =>
      `# keep me\n\n${legacy}[surfaces]  # the gate\n# enabled = ["old"]\nenabled = ${list}\n\n[models]\ndecide = "x" # mine\n`;
    const { repo, home } = governedRepo(layout('["claude-code"]'));
    installCanon(VERSION);

    expect((await runConfig(repo, { add: "cursor" })).result).toBe(0);
    expect(configOf(repo)).toBe(layout('["claude-code", "cursor"]'));

    expect((await runConfig(repo, { remove: "cursor" })).result).toBe(0);
    expect(configOf(repo)).toBe(layout('["claude-code"]'));
    expect(isGoverned(repo)).toBe(true);
    expectFullCanonInstalled(home);
  });

  test("F28: what the canon install could not do is shown as a warning, never dropped or marked ✓", async () => {
    const { repo, home } = governedRepo();
    installCanon(VERSION);
    const skill = join(home, "skills", "ai-debug");
    const dotfiles = join(home, "dotfiles-ai-debug");
    renameSync(skill, dotfiles);
    symlinkSync(dotfiles, skill, "dir");

    const { result, out } = await runConfig(repo, { add: "cursor" });

    expect(result).toBe(0);
    expect(out).toContain(`▲ 1 path(s) where ai-eng installs are links or not its own folders or files — never written through, left as they are (the link and what it points at untouched): ${join(realpathSync(join(home, "skills")), "ai-debug")}`);
    expect(out).not.toContain("✓ ⚠");
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

  test("--add writes the repo carrier and merges ours into the user's machine settings", async () => {
    const { repo, home } = governedRepo();
    installCanon(VERSION);
    const machineSettings = join(home, ".copilot", "hooks", "ai-eng.json");
    const machineSettingsBefore = '{\n  "user": "keep"\n}\n';
    mkdirSync(join(home, ".copilot", "hooks"), { recursive: true });
    writeFileSync(machineSettings, machineSettingsBefore);

    const { result: code, out } = await runConfig(repo, { add: "copilot" });

    expect(code).toBe(0);
    expect(out).toContain("✓  .github/hooks/ai-eng.json written (repo carrier)");
    expect(out).toContain("✓  ~/.copilot/hooks/ai-eng.json written (machine carrier)");
    expect(existsSync(join(repo, ".github", "hooks", "ai-eng.json"))).toBe(true);
    expect(readFileSync(join(repo, ".github", "hooks", "ai-eng.json"), "utf8")).toContain("ai-eng chain PreToolUse --surface copilot-cli");
    expect(configOf(repo)).toBe('[surfaces]\nenabled = ["claude-code", "copilot-cli"]\n');
    const machineSettingsAfter = readFileSync(machineSettings, "utf8");
    expect(machineSettingsAfter).not.toBe(machineSettingsBefore);
    expect(machineSettingsAfter).toContain("--surface copilot-cli");
    expect((JSON.parse(machineSettingsAfter) as { user?: unknown }).user).toBe("keep");
    expectFullCanonInstalled(home);
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
    expect(out).toContain("Which agent surfaces is this project governed on?");
    expect(out).not.toContain("core — deny");
    expect(out).not.toContain("experimental —");
    expect(out).not.toContain("best-effort —");
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
    expect(configOf(repo)).toBe('[surfaces]\n  enabled = ["claude-code", "cursor"]\n');
    expect(isGoverned(repo)).toBe(true);
  });

  // F4: the key line is the user's — its indentation and the spacing around `=` survive.
  test("the key's indentation and spacing around = are kept when the list changes", async () => {
    const layout = (list: string): string => `[surfaces]\n\tenabled\t=\t${list}\n`;
    const { repo } = governedRepo(layout('["claude-code"]'));

    expect((await runConfig(repo, { add: "cursor" })).result).toBe(0);
    expect(configOf(repo)).toBe(layout('["claude-code", "cursor"]'));
    expect((await runConfig(repo, { remove: "claude-code" })).result).toBe(0);
    expect(configOf(repo)).toBe(layout('["cursor"]'));
  });

  test("a commented [surfaces] header is rewritten without adding a duplicate", async () => {
    const source = '# keep me\n[surfaces] # keep this comment\nenabled = ["claude-code"]\n';
    const { repo } = governedRepo(source);
    const { result } = await runConfig(repo, { add: "cursor" });

    expect(result).toBe(0);
    expect(configOf(repo)).toBe('# keep me\n[surfaces] # keep this comment\nenabled = ["claude-code", "cursor"]\n');
    expect(configOf(repo).match(/^\[surfaces\]/gm)).toHaveLength(1);
    expect(isGoverned(repo)).toBe(true);
  });

  // A commented header is a comment, not a table: the real [surfaces] below or around it
  // is the one rewritten, in place, and no second table is appended.
  test.each([
    ["a commented header above the real one", '# [surfaces]\n# enabled = ["old"]\n[surfaces]\nenabled = LIST\n\n[models]\ndecide = "x"\n'],
    ["a commented header with no space after the hash", '#[surfaces]\n[surfaces]\nenabled = LIST\n'],
    ["a commented header inside another table", '[models]\ndecide = "x"\n# [surfaces] lives below\n\n[surfaces] # the gate\nenabled = LIST\n'],
    ["a commented header of another table before the key", '[surfaces]\n# [models] moved below\n  # [notices]\nenabled = LIST\n\n[models]\ndecide = "x"\n'],
    ["a header comment that itself holds brackets", '[surfaces] # see [models] and [notices]\nenabled = LIST\n\n[notices]\nenabled = true\n'],
  ])("%s: the valid [surfaces] table is updated in place", async (_layout, template) => {
    const { repo } = governedRepo(template.replace("LIST", '["claude-code"]'));
    const { result } = await runConfig(repo, { add: "cursor" });

    expect(result).toBe(0);
    expect(configOf(repo)).toBe(template.replace("LIST", '["claude-code", "cursor"]'));
    expect(isGoverned(repo)).toBe(true);
  });

  test("a comment after the enabled list is kept when the list is rewritten", async () => {
    const { repo } = governedRepo('[surfaces]\nenabled = ["claude-code"] # the hosts this repo governs\n');
    const { result } = await runConfig(repo, { add: "cursor" });

    expect(result).toBe(0);
    expect(configOf(repo)).toBe('[surfaces]\nenabled = ["claude-code", "cursor"] # the hosts this repo governs\n');
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

  test("a multi-line enabled list gains a line in its own style, keeping its comments", async () => {
    const { repo } = governedRepo('[surfaces]\nenabled = [\n  "claude-code", # the main one\n]\n\n[models]\ndecide = "x"\n');
    const { result } = await runConfig(repo, { add: "cursor" });

    expect(result).toBe(0);
    expect(configOf(repo)).toBe('[surfaces]\nenabled = [\n  "claude-code", # the main one\n  "cursor",\n]\n\n[models]\ndecide = "x"\n');
    expect(isGoverned(repo)).toBe(true);
  });

  // F3: every comment in a multi-line list is the user's. An item comes and goes as one
  // line in the existing style; the opening-line comment, the comments between items and
  // the one after `]` all stay.
  test("a commented multi-line list is edited item by item, every other comment kept", async () => {
    const { repo } = governedRepo('[surfaces]\nenabled = [ # hosts\n  "claude-code", # main\n  # cursor later\n] # end\n');

    expect((await runConfig(repo, { add: "cursor" })).result).toBe(0);
    expect(configOf(repo)).toBe('[surfaces]\nenabled = [ # hosts\n  "claude-code", # main\n  "cursor",\n  # cursor later\n] # end\n');

    expect((await runConfig(repo, { remove: "claude-code" })).result).toBe(0);
    expect(configOf(repo)).toBe('[surfaces]\nenabled = [ # hosts\n  "cursor",\n  # cursor later\n] # end\n');
    expect(isGoverned(repo)).toBe(true);
  });

  test("a multi-line list written without a trailing comma keeps that style", async () => {
    const { repo } = governedRepo("[surfaces]\nenabled = [\n    'claude-code'\n]\n");

    expect((await runConfig(repo, { add: "cursor" })).result).toBe(0);
    expect(configOf(repo)).toBe("[surfaces]\nenabled = [\n    'claude-code',\n    'cursor'\n]\n");
  });

  // F1: a CRLF file stays CRLF everywhere — no line loses its `\r`, no new line lacks one.
  test.each([
    ["a one-line list", '[surfaces]\r\nenabled = LIST\r\n\r\n[models]\r\ndecide = "x"\r\n', '["claude-code"]', '["claude-code", "cursor"]'],
    ["a one-line list with a comment", "[surfaces]\r\nenabled = LIST # hosts\r\n", '["claude-code"]', '["claude-code", "cursor"]'],
    ["a multi-line list", "[surfaces]\r\nenabled = LIST\r\n", '[\r\n  "claude-code", # main\r\n]', '[\r\n  "claude-code", # main\r\n  "cursor",\r\n]'],
  ])("a CRLF config with %s keeps its line endings", async (_layout, template, before, after) => {
    const { repo } = governedRepo(template.replace("LIST", before));

    expect((await runConfig(repo, { add: "cursor" })).result).toBe(0);
    expect(configOf(repo)).toBe(template.replace("LIST", after));
    expect((await runConfig(repo, { remove: "cursor" })).result).toBe(0);
    expect(configOf(repo)).toBe(template.replace("LIST", before));
  });

  // F2: under CRLF the header's comment runs up to `\r`, and the table is still found.
  test("a commented [surfaces] header in a CRLF file is rewritten in place", async () => {
    const { repo } = governedRepo('[surfaces] # gate\r\nenabled = ["claude-code"]\r\n');
    const { result } = await runConfig(repo, { add: "cursor" });

    expect(result).toBe(0);
    expect(configOf(repo)).toBe('[surfaces] # gate\r\nenabled = ["claude-code", "cursor"]\r\n');
    expect(isGoverned(repo)).toBe(true);
  });

  test("a [ surfaces ] header written with spaces is the same table, rewritten in place", async () => {
    const { repo } = governedRepo('[ surfaces ]\nenabled = ["claude-code"]\n');
    const { result } = await runConfig(repo, { add: "cursor" });

    expect(result).toBe(0);
    expect(configOf(repo)).toBe('[ surfaces ]\nenabled = ["claude-code", "cursor"]\n');
    expect(isGoverned(repo)).toBe(true);
  });

  // Layouts the line edit cannot rewrite: refused before any write, file byte-identical.
  test.each([
    ["a dotted surfaces.enabled key", 'surfaces.enabled = ["claude-code"]\n\n[models]\ndecide = "x"\n'],
    ["an inline surfaces table", 'surfaces = { enabled = ["claude-code"] }\n\n[models]\ndecide = "x"\n'],
  ])("%s is refused and left byte-identical", async (_layout, source) => {
    const { repo } = governedRepo(source);
    const { result, out } = await runConfig(repo, { add: "cursor" });

    expect(result).toBe(2);
    expect(out).toContain("✗  .ai-engineering/config.toml is laid out in a way this command cannot rewrite");
    expect(out).toContain('Edit it by hand: under [surfaces], set enabled = ["claude-code", "cursor"]');
    expect(out).toContain("└  Nothing changed.");
    expect(configOf(repo)).toBe(source);
    expect(isGoverned(repo)).toBe(true);
    expect(existsSync(join(repo, ".cursor"))).toBe(false);
  });

  test("a refused --remove leaves the surface's carrier in place too", async () => {
    const source = 'surfaces = { enabled = ["claude-code", "cursor"] }\n';
    const { repo } = governedRepo(source);
    mkdirSync(join(repo, ".cursor"), { recursive: true });
    writeFileSync(join(repo, ".cursor", "hooks.json"), '{ "hooks": {} }\n');

    const { result } = await runConfig(repo, { remove: "cursor" });

    expect(result).toBe(2);
    expect(configOf(repo)).toBe(source);
    expect(readFileSync(join(repo, ".cursor", "hooks.json"), "utf8")).toBe('{ "hooks": {} }\n');
  });
});
