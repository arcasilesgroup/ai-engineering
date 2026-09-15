// tests/uninstall-command.spec.ts — behaviour gates for `ai-eng uninstall`
// (src/commands/uninstall.ts). The product's promise is "revert ai-eng's files, keep
// yours", so every claim here is about the disk afterwards: the files that are gone, the
// files still there with their original bytes, the restored `git config
// init.templateDir`, the machine record, and the number uninstallMain() returns.
//
// The starting states are built with the real installers — `install()` over
// planEntries()/contractEntries() plus lockText(), exactly init's shape;
// installMachineCarriers(); installTemplateDir() — and only the end state is asserted.
// The interactive path is driven through src/ui.ts's scriptedInput: keys are fed only
// after the prompt that reads them has rendered, so nothing here can block on a TTY.
//
// Sandbox: AI_ENG_HOME and PI_CODING_AGENT_DIR point into a mkdtemp() per test, and the
// global git config is the sandbox's own file (GIT_CONFIG_GLOBAL, which template.ts honours
// over the developer's), so ~/.claude, ~/.ai-engineering, ~/.pi and ~/.gitconfig are never
// read or written.

import { afterAll, afterEach, describe, expect, test } from "bun:test";
import { spawnSync } from "node:child_process";
import { chmodSync, existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, symlinkSync, unlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { uninstallMain } from "../src/commands/uninstall.ts";
import { contractEntries, planEntries } from "../src/commands/init-shared.ts";
import { buildLock, install, lockText, sha256 } from "../src/install.ts";
import { SHIMS, installTemplateDir } from "../src/floor/template.ts";
import { installMachineCarriers, machineStateFile, readMachineState, rememberTemplateDir } from "../src/surfaces/adapters.ts";
import { VERSION } from "../src/version.ts";

const cwdBefore = process.cwd();
process.env["NO_COLOR"] = "1";
process.env["CI"] = "1";
// scriptedInput adds one data listener per call and a question chain crosses Node's default
// cap of 10; the wrapper raises it for its own stream, not for the real stdin it listens on.
process.stdin.setMaxListeners(0);

/** The prompt fragments. Each one is text that appears for the FIRST time at the prompt
 *  it belongs to — a fragment already on screen would match instantly and the key would
 *  be fed before clack's listener exists. */
const SELECT = "What do you want to remove?";
const CONFIRM = "Confirm?";
const CONTRACT = "Delete this project's";
const MACHINE = "Delete the machine side";
const PROJECT_KEYS = "\r";
const EVERYTHING_KEYS = "\x1b[B\r";
const CANCEL_KEYS = "\x1b[B\x1b[B\r";

let sandbox: string | undefined;

/** A repo-shaped project and a machine of its own. Nothing outside this directory is
 *  written: AI_ENG_HOME redirects the canon, the carrier base and — through template.ts —
 *  the global git config; PI_CODING_AGENT_DIR redirects the two relocatable agent dirs
 *  OUTSIDE the canon home, so a carrier removed there is removed by the sweep and not by
 *  the rmSync of the canon home. */
function sandboxed(): { cwd: string; machine: string; agentDir: string } {
  sandbox = mkdtempSync(join(tmpdir(), "ai-eng-uninstall-"));
  const cwd = join(sandbox, "project");
  const machine = join(sandbox, "machine");
  const agentDir = join(sandbox, "pi-agent");
  mkdirSync(cwd, { recursive: true });
  mkdirSync(machine, { recursive: true });
  process.env["AI_ENG_HOME"] = machine;
  process.env["PI_CODING_AGENT_DIR"] = agentDir;
  // template.ts honours a caller that brought its own global git config, and this one is
  // deliberately OUTSIDE the canon home: the Everything scope deletes that home, so a
  // config kept inside it could not show whether the setting was restored.
  process.env["GIT_CONFIG_GLOBAL"] = join(sandbox, "gitconfig");
  process.chdir(cwd);
  return { cwd, machine, agentDir };
}

function gitInit(cwd: string): void {
  const done = spawnSync("git", ["init", "-q"], { cwd, encoding: "utf8" });
  if (done.status !== 0) throw new Error(`git init failed: ${done.stderr}`);
}

/** The global `init.templateDir` exactly as git sees it for this sandbox — the file
 *  template.ts writes into, read back with the same variable. */
function globalTemplateDir(): string | null {
  const done = spawnSync("git", ["config", "--global", "--get", "init.templateDir"], {
    encoding: "utf8",
    env: { ...process.env, GIT_CONFIG_GLOBAL: process.env["GIT_CONFIG_GLOBAL"] ?? "" },
  });
  const value = (done.stdout ?? "").trim();
  return done.status === 0 && value.length > 0 ? value : null;
}

function setGlobalTemplateDir(dir: string): void {
  spawnSync("git", ["config", "--global", "init.templateDir", dir], {
    env: { ...process.env, GIT_CONFIG_GLOBAL: process.env["GIT_CONFIG_GLOBAL"] ?? "" },
  });
}

/** A real init-shaped install: the contract files once, the plan's files, the shims made
 *  executable, and the lock built from the same entries — src/commands/init.ts's
 *  scaffoldProject(), with the human's lines left out. Returns the paths it owns. */
function initShaped(surfaces: string[]): string[] {
  const cwd = process.cwd();
  install(cwd, contractEntries("2026-09-14"));
  try {
    symlinkSync("AGENTS.md", join(cwd, "CLAUDE.md"));
  } catch {
    writeFileSync(join(cwd, "CLAUDE.md"), "@AGENTS.md\n");
  }
  const entries = planEntries(surfaces);
  install(cwd, entries);
  for (const shim of SHIMS) {
    const path = join(cwd, ".git", "hooks", shim);
    if (existsSync(path)) chmodSync(path, 0o755);
  }
  writeFileSync(join(cwd, ".ai-engineering", "ai-eng.lock"), lockText(buildLock(entries, VERSION)));
  return entries.map((entry) => entry.path);
}

/** Capture everything the frame writes. clack resolves `process.stdout` at call time, so
 *  patching its write is enough — and the patch is restored in `stop()`. */
function startCapture(): { chunks: string[]; stop: () => string } {
  const chunks: string[] = [];
  const out = process.stdout as unknown as { write: (chunk: unknown) => boolean };
  const original = out.write;
  out.write = (chunk: unknown) => {
    chunks.push(typeof chunk === "string" ? chunk : Buffer.from(chunk as Uint8Array).toString("utf8"));
    return true;
  };
  let stopped = false;
  return {
    chunks,
    stop: () => {
      if (!stopped) {
        stopped = true;
        out.write = original;
      }
      return chunks.join("");
    },
  };
}

const sleep = (ms: number): Promise<void> => {
  const { promise, resolve } = Promise.withResolvers<void>();
  setTimeout(resolve, ms);
  return promise;
};

/** A single word: clack wraps prompt text on spaces, so a short word is exactly the
 *  fragment that cannot be split across two lines. */
async function until(cap: { chunks: string[] }, fragment: string, ms = 4000): Promise<void> {
  const deadline = Date.now() + ms;
  while (!cap.chunks.join("").includes(fragment)) {
    if (Date.now() > deadline) throw new Error(`prompt "${fragment}" never appeared:\n${cap.chunks.join("")}`);
    await sleep(5);
  }
  await sleep(20); // the render that showed the message and the listener that reads the key are the same tick
}

/** Run uninstallMain(), answering each prompt when it appears. */
async function uninstall(steps: Array<[string, string]>): Promise<{ result: number; out: string }> {
  const cap = startCapture();
  const run = uninstallMain();
  try {
    for (const [fragment, keys] of steps) {
      await until(cap, fragment);
      process.stdin.emit("data", Buffer.from(keys));
    }
    return { result: await run, out: cap.stop() };
  } finally {
    cap.stop();
  }
}

/** The "Everything" scope: scope, Confirm?, the contract question, the machine question. */
function everythingScope(contract: string, machine: string): Array<[string, string]> {
  return [
    [SELECT, EVERYTHING_KEYS],
    [CONFIRM, "y"],
    [CONTRACT, contract],
    [MACHINE, machine],
  ];
}

afterEach(() => {
  process.chdir(cwdBefore);
  delete process.env["AI_ENG_HOME"];
  delete process.env["PI_CODING_AGENT_DIR"];
  delete process.env["GIT_CONFIG_GLOBAL"];
  if (sandbox) rmSync(sandbox, { recursive: true, force: true });
  sandbox = undefined;
});

afterAll(() => {
  // scriptedInput attaches a data listener to the real stdin on every call; leaving the
  // stream flowing keeps the process alive after the last test.
  process.stdin.pause();
  process.stdin.removeAllListeners("data");
});

describe("uninstall · this project (the lock is the ownership register)", () => {
  test("an init-shaped install is swept: the contract, the spec and the plan stay", async () => {
    const { cwd } = sandboxed();
    gitInit(cwd);
    const owned = initShaped(["claude-code", "cursor"]);
    const agents = readFileSync(join(cwd, "AGENTS.md"), "utf8");
    const decisions = readFileSync(join(cwd, "DECISIONS.md"), "utf8");
    const plan = "# the milestone plan\nstill ours to finish\n";
    mkdirSync(join(cwd, ".ai-engineering", "spec"), { recursive: true });
    writeFileSync(join(cwd, ".ai-engineering", "spec", "plan.md"), plan);

    for (const rel of owned) expect(existsSync(join(cwd, rel))).toBe(true);
    expect(existsSync(join(cwd, ".ai-engineering", "ai-eng.lock"))).toBe(true);
    expect(owned).toContain(".cursor/hooks.json");

    const { result, out } = await uninstall([
      [SELECT, PROJECT_KEYS],
      [CONFIRM, "y"],
    ]);

    expect(result).toBe(0);
    // Everything the lock declared ours is gone — hooks, adapters, CI workflow, config, lock.
    for (const rel of owned) expect(existsSync(join(cwd, rel))).toBe(false);
    // The dirs ai-eng created went with the files it put in them.
    expect(existsSync(join(cwd, ".cursor"))).toBe(false);
    expect(existsSync(join(cwd, ".github"))).toBe(false);
    // The contract and the user's own spec are not ai-eng's to delete.
    expect(readFileSync(join(cwd, "AGENTS.md"), "utf8")).toBe(agents);
    expect(readFileSync(join(cwd, "DECISIONS.md"), "utf8")).toBe(decisions);
    expect(readFileSync(join(cwd, ".ai-engineering", "spec", "plan.md"), "utf8")).toBe(plan);
    expect(existsSync(join(cwd, ".ai-engineering"))).toBe(true); // the spec keeps it alive
    expect(out).toContain("✓ .cursor/hooks.json removed · still the template ai-eng installed");
    expect(out).toContain("✓ ai-eng.lock deleted · 8 owned files swept");
    expect(out).toContain("ai-eng is no longer active in this repo. Your contract files remain.");
  });

  test("a settings file the user already owned: their hook entries survive verbatim, ours do not", async () => {
    const { cwd } = sandboxed();
    gitInit(cwd);
    const mine = {
      version: 1,
      hooks: { preToolUse: [{ type: "command", command: "echo my own guard", timeout: 5 }] },
    };
    const before = `${JSON.stringify(mine, null, 2)}\n`;
    const settings = join(cwd, ".cursor", "hooks.json");
    mkdirSync(join(cwd, ".cursor"), { recursive: true });
    writeFileSync(settings, before);

    initShaped(["cursor"]);
    const merged = readFileSync(settings, "utf8");
    expect(merged).toContain("ai-eng chain"); // ours went in
    expect(merged).toContain("echo my own guard"); // theirs was kept
    expect(merged).not.toBe(before);

    const { result, out } = await uninstall([
      [SELECT, PROJECT_KEYS],
      [CONFIRM, "y"],
    ]);

    expect(result).toBe(0);
    // Their own entry is back verbatim, and the container that existed only to hold ours
    // went with it — the merge's inverse is exact for entries (install.ts:79-100).
    const restored = JSON.parse(readFileSync(settings, "utf8")) as { hooks: Record<string, unknown> };
    expect(restored.hooks["preToolUse"]).toEqual(mine.hooks.preToolUse);
    expect(Object.keys(restored.hooks)).toEqual(["preToolUse"]);
    expect(readFileSync(settings, "utf8")).not.toContain("ai-eng");
    // The template's own top-level scalars stay, on purpose: a key whose value happens to
    // equal ours could be one the user wrote (a `version` their host requires), and telling
    // the two apart would need a ledger of what each merge added (install.ts:73-77).
    expect(restored).toMatchObject({ failClosed: true });
    expect(existsSync(join(cwd, ".cursor"))).toBe(true); // their file keeps the dir
    expect(out).toContain("✓ .cursor/hooks.json: removed the ai-eng hook entries, kept yours");
  });

  test("a settings file this installer cannot reproduce is left alone, and said", async () => {
    const { cwd } = sandboxed();
    gitInit(cwd);
    initShaped(["cursor"]);
    const settings = join(cwd, ".cursor", "hooks.json");
    // The user re-saved it as a one-liner: a shape we cannot rewrite without reformatting
    // what they wrote. Ours go nowhere near it.
    const compact = '{"hooks":{"stop":[{"command":"echo mine"}],"preToolUse":[{"command":"ai-eng chain PreToolUse --surface cursor"}]}}\n';
    writeFileSync(settings, compact);

    const { result, out } = await uninstall([
      [SELECT, PROJECT_KEYS],
      [CONFIRM, "y"],
    ]);

    expect(result).toBe(0);
    expect(readFileSync(settings, "utf8")).toBe(compact);
    expect(out).toContain(".cursor/hooks.json not rewritten — not JSON this installer can rewrite without reformatting it (review by hand)");
  });

  test("a file you edited after install is kept, and named", async () => {
    const { cwd } = sandboxed();
    gitInit(cwd);
    initShaped(["claude-code"]);
    const rules = join(cwd, ".ai-engineering", "arch.rules.json");
    const edited = `${readFileSync(rules, "utf8")}\n`;
    writeFileSync(rules, edited);

    const { result, out } = await uninstall([
      [SELECT, PROJECT_KEYS],
      [CONFIRM, "y"],
    ]);

    expect(result).toBe(0);
    expect(readFileSync(rules, "utf8")).toBe(edited);
    expect(out).toContain("▲ .ai-engineering/arch.rules.json kept · you edited it after install — it is yours now");
    expect(existsSync(join(cwd, ".git", "hooks", "pre-commit"))).toBe(false);
  });

  test("a git hook someone else wrote is never deleted; ours are removed", async () => {
    const { cwd } = sandboxed();
    gitInit(cwd);
    initShaped(["claude-code"]);
    const theirs = "#!/bin/sh\necho my own commit-msg check\n";
    writeFileSync(join(cwd, ".git", "hooks", "commit-msg"), theirs);

    const { result, out } = await uninstall([
      [SELECT, PROJECT_KEYS],
      [CONFIRM, "y"],
    ]);

    expect(result).toBe(0);
    // Ours are judged by their marker, never by their name.
    expect(existsSync(join(cwd, ".git", "hooks", "pre-commit"))).toBe(false);
    expect(existsSync(join(cwd, ".git", "hooks", "pre-push"))).toBe(false);
    expect(readFileSync(join(cwd, ".git", "hooks", "commit-msg"), "utf8")).toBe(theirs);
    expect(out).toContain("▲ .git/hooks/commit-msg kept · no ai-eng marker: it is yours now");
  });

  test("with no lock, the binary's own file list still sweeps what it installed", async () => {
    const { cwd } = sandboxed();
    gitInit(cwd);
    initShaped(["claude-code"]); // a half-finished uninstall: the sweep ran, the lock was already gone
    unlinkSync(join(cwd, ".ai-engineering", "ai-eng.lock"));

    const { result, out } = await uninstall([
      [SELECT, PROJECT_KEYS],
      [CONFIRM, "y"],
    ]);

    expect(result).toBe(0);
    expect(existsSync(join(cwd, ".git", "hooks", "pre-commit"))).toBe(false);
    expect(existsSync(join(cwd, ".ai-engineering", "config.toml"))).toBe(false);
    expect(existsSync(join(cwd, ".ai-engineering", "ai-eng.lock"))).toBe(false);
    expect(existsSync(join(cwd, "AGENTS.md"))).toBe(true);
    expect(out).toContain("no lock — swept by the binary's own file list");
  });

  test("a lock key that escapes the repo is refused: the file outside is untouched", async () => {
    const { cwd } = sandboxed();
    gitInit(cwd);
    mkdirSync(join(cwd, ".ai-engineering"), { recursive: true });
    writeFileSync(join(cwd, ".ai-engineering", "config.toml"), '[surfaces]\nenabled = ["claude-code"]\n');
    const victim = join(sandbox!, "victim.txt"); // deliberately OUTSIDE the repo, inside the sandbox
    const payload = "you-are-the-victim\n";
    writeFileSync(victim, payload);
    writeFileSync(join(cwd, ".ai-engineering", "ai-eng.lock"), lockText({ version: VERSION, assets: { "../victim.txt": sha256(payload) } }));

    const { result, out } = await uninstall([
      [SELECT, PROJECT_KEYS],
      [CONFIRM, "y"],
    ]);

    expect(result).toBe(0);
    expect(readFileSync(victim, "utf8")).toBe(payload);
    expect(out).toContain("▲ ../victim.txt kept · lock path escapes this repo — not ai-eng's");
  });

  test("Cancel at the scope question removes nothing", async () => {
    const { cwd } = sandboxed();
    gitInit(cwd);
    initShaped(["claude-code"]);

    const { result, out } = await uninstall([[SELECT, CANCEL_KEYS]]);

    expect(result).toBe(0);
    expect(existsSync(join(cwd, ".ai-engineering", "ai-eng.lock"))).toBe(true);
    expect(existsSync(join(cwd, ".git", "hooks", "pre-commit"))).toBe(true);
    expect(out).toContain("Nothing removed.");
  });

  test("a bare Enter at Confirm? is No: uninstall is destructive by default", async () => {
    const { cwd } = sandboxed();
    gitInit(cwd);
    initShaped(["claude-code"]);

    const { result, out } = await uninstall([
      [SELECT, PROJECT_KEYS],
      [CONFIRM, "\r"],
    ]);

    expect(result).toBe(0);
    expect(existsSync(join(cwd, ".ai-engineering", "ai-eng.lock"))).toBe(true);
    expect(existsSync(join(cwd, ".ai-engineering", "config.toml"))).toBe(true);
    expect(existsSync(join(cwd, ".git", "hooks", "pre-commit"))).toBe(true);
    expect(out).toContain("Nothing removed.");
  });
});

describe("uninstall · the machine side (Everything scope)", () => {
  test("a module carrier and its chain bundle are removed whole, and the record goes too", async () => {
    const { cwd, machine, agentDir } = sandboxed();
    gitInit(cwd);
    initShaped(["claude-code"]);
    // The state `ai-eng config --add pi` leaves: config.toml declares a surface the lock
    // predates, so the project sweep keeps it as the user's and the declaration is still
    // readable when the machine side runs.
    writeFileSync(join(cwd, ".ai-engineering", "config.toml"), '[surfaces]\nenabled = ["pi"]\n');

    const report = installMachineCarriers(["pi"]);
    expect(report.written).toEqual(["~/.pi/agent/extensions/ai-eng.ts"]);
    const entry = join(agentDir, "extensions", "ai-eng.ts");
    const chain = join(agentDir, "extensions", ".ai-eng-chain.ts");
    expect(existsSync(entry)).toBe(true);
    expect(existsSync(chain)).toBe(true);
    expect(existsSync(machineStateFile())).toBe(true);
    // The record names the surface and the sha256 of the definition written beside the bundle.
    expect(readMachineState().carriers["pi"]).toBe(sha256(readFileSync(entry, "utf8")));

    const { result, out } = await uninstall(everythingScope("n", "y"));

    expect(result).toBe(0);
    // The reported line is the carriers step's own: these two files live in the HOST's agent
    // dir, outside the canon home this scope deletes, so an orphan is exactly what is left
    // if the sweep misses them.
    expect(out).toContain("✓ ~/.pi/agent/extensions/ai-eng.ts removed");
    expect(existsSync(entry)).toBe(false);
    expect(existsSync(chain)).toBe(false);
    expect(existsSync(machineStateFile())).toBe(false);
    expect(existsSync(machine)).toBe(false); // the global canon and mirrors are gone
    expect(existsSync(join(cwd, ".ai-engineering", "config.toml"))).toBe(true); // "no" kept the project's files
    expect(existsSync(join(cwd, "AGENTS.md"))).toBe(true);
  });

  test("saying yes to the project question deletes the contract files, and the canon stays", async () => {
    const { cwd, machine } = sandboxed();
    gitInit(cwd);
    initShaped(["claude-code"]);

    const { result, out } = await uninstall(everythingScope("y", "n"));

    expect(result).toBe(0);
    expect(existsSync(join(cwd, "AGENTS.md"))).toBe(false);
    expect(existsSync(join(cwd, "DECISIONS.md"))).toBe(false);
    expect(existsSync(join(cwd, "CLAUDE.md"))).toBe(false);
    expect(existsSync(join(cwd, ".ai-engineering"))).toBe(false);
    // The full line may wrap in a narrow terminal (e.g. stryker's sandbox), so check
    // the prefix and the file list separately — both must appear, order is irrelevant.
    expect(out).toContain("▲ project contract files removed (your choice)");
    expect(out).toContain("AGENTS.md · DECISIONS.md · CLAUDE.md · .ai-engineering/");
    expect(out).toContain(`✓ kept: ${machine} · global skills stay installed`); // the second question is separate
    expect(existsSync(machine)).toBe(true);
  });

  test("a machine settings carrier is stripped of our entries, and said", async () => {
    const { cwd, machine } = sandboxed();
    gitInit(cwd);
    initShaped(["claude-code"]);
    // The state `ai-eng config --add copilot` leaves: config.toml declares a surface the
    // lock predates, so the project sweep keeps it as the user's and the declaration is
    // still readable when the machine side runs.
    writeFileSync(join(cwd, ".ai-engineering", "config.toml"), '[surfaces]\nenabled = ["copilot"]\n');
    expect(installMachineCarriers(["copilot"]).written).toEqual(["~/.copilot/hooks/ai-eng.json"]);

    const { result, out } = await uninstall(everythingScope("n", "y"));

    expect(result).toBe(0);
    // Our entries came out of the user-scope file the CLI reads and never the repo copy.
    expect(out).toContain("✓ ~/.copilot/hooks/ai-eng.json: ai-eng entries removed, yours kept");
    expect(out).toContain(`▲ ${machine} deleted`);
    expect(existsSync(machine)).toBe(false);
    expect(existsSync(join(cwd, ".ai-engineering", "config.toml"))).toBe(true); // "no" kept the project's files
  });

  test("the project scope stops at the repo: carriers and their record stay", async () => {
    const { cwd, machine, agentDir } = sandboxed();
    gitInit(cwd);
    initShaped(["claude-code"]);
    writeFileSync(join(cwd, ".ai-engineering", "config.toml"), '[surfaces]\nenabled = ["pi"]\n');
    installMachineCarriers(["pi"]);
    const entry = join(agentDir, "extensions", "ai-eng.ts");
    const chain = join(agentDir, "extensions", ".ai-eng-chain.ts");
    const definition = readMachineState().carriers["pi"];

    const { result } = await uninstall([
      [SELECT, PROJECT_KEYS],
      [CONFIRM, "y"],
    ]);

    expect(result).toBe(0);
    // Every repo that declares this surface shares these files: one repo's uninstall has
    // no business taking them out of the user's editor.
    expect(existsSync(entry)).toBe(true);
    expect(existsSync(chain)).toBe(true);
    expect(readMachineState().carriers["pi"]).toBe(definition);
    expect(existsSync(machineStateFile())).toBe(true);
    expect(existsSync(machine)).toBe(true);
  });

  test("saying no to the machine sweep keeps the canon and says so", async () => {
    const { cwd, machine } = sandboxed();
    gitInit(cwd);
    initShaped(["claude-code"]);
    mkdirSync(join(machine, "skills", "a-skill"), { recursive: true });
    writeFileSync(join(machine, "skills", "a-skill", "SKILL.md"), "# a skill\n");

    const { result, out } = await uninstall(everythingScope("n", "n"));

    expect(result).toBe(0);
    expect(existsSync(join(machine, "skills", "a-skill", "SKILL.md"))).toBe(true);
    expect(out).toContain(`✓ kept: ${machine} · global skills stay installed`);
    expect(out).toContain("✓ kept: AGENTS.md, DECISIONS.md, .ai-engineering/");
    expect(existsSync(join(cwd, ".ai-engineering", "config.toml"))).toBe(false); // the repo side still ran
    expect(existsSync(join(cwd, "AGENTS.md"))).toBe(true);
  });

  test("a templateDir we created is removed and the setting goes back to unset", async () => {
    const { cwd } = sandboxed();
    gitInit(cwd);
    initShaped(["claude-code"]);

    const floor = installTemplateDir();
    expect(floor.status).toBe("created");
    const ours = floor.ours ?? "";
    for (const shim of SHIMS) expect(existsSync(join(ours, "hooks", shim))).toBe(true);
    expect(globalTemplateDir()).toBe(ours);
    rememberTemplateDir(floor.previous, floor.ours);

    const { result, out } = await uninstall(everythingScope("n", "y"));

    expect(result).toBe(0);
    expect(globalTemplateDir()).toBeNull(); // it was unset before, so it is unset after
    expect(existsSync(ours)).toBe(false);
    expect(out).toContain("✓ git init.templateDir unset (it was unset before)");
  });

  test("a templateDir the user owned keeps their setting and loses only our shims", async () => {
    const { cwd } = sandboxed();
    gitInit(cwd);
    initShaped(["claude-code"]);
    const userDir = join(sandbox!, "user-template");
    mkdirSync(join(userDir, "hooks"), { recursive: true });
    const theirs = "#!/bin/sh\necho my own pre-push\n";
    writeFileSync(join(userDir, "hooks", "pre-push"), theirs);
    setGlobalTemplateDir(userDir);

    const floor = installTemplateDir();
    expect(floor.status).toBe("joined");
    expect(floor.ours).toBeNull(); // we joined their directory; we own no directory here
    expect(floor.previous).toBe(userDir);
    expect(existsSync(join(userDir, "hooks", "pre-commit"))).toBe(true);
    expect(existsSync(userDir)).toBe(true);
    rememberTemplateDir(floor.previous, floor.ours);

    const { result, out } = await uninstall(everythingScope("n", "y"));

    expect(result).toBe(0);
    expect(globalTemplateDir()).toBe(userDir); // a setting the user owns is never simply deleted
    expect(readFileSync(join(userDir, "hooks", "pre-push"), "utf8")).toBe(theirs);
    expect(existsSync(join(userDir, "hooks", "pre-commit"))).toBe(false);
    expect(existsSync(join(userDir, "hooks", "commit-msg"))).toBe(false);
    expect(existsSync(userDir)).toBe(true);
    expect(out).toContain(`✓ git init.templateDir kept yours (${userDir}) · 2 ai-eng shim(s) removed from it`);
  });
});

describe("uninstall · outside a governed repo", () => {
  test("a directory that declared nothing: reported, and nothing changed", async () => {
    const { cwd } = sandboxed();
    gitInit(cwd); // a repo, but no .ai-engineering/config.toml: it never asked for policy
    writeFileSync(join(cwd, "keep.txt"), "mine\n");
    mkdirSync(join(cwd, ".git", "hooks"), { recursive: true });
    writeFileSync(join(cwd, ".git", "hooks", "pre-commit"), "#!/bin/sh\necho mine\n");

    const { result, out } = await uninstall([]);

    expect(result).toBe(2);
    expect(readFileSync(join(cwd, "keep.txt"), "utf8")).toBe("mine\n");
    expect(readFileSync(join(cwd, ".git", "hooks", "pre-commit"), "utf8")).toBe("#!/bin/sh\necho mine\n");
    expect(out).toContain("you are not in a governed repo — nothing of this project to remove");
    expect(out).toContain("Nothing done.");
  });

  test("a directory that is not a repo at all: the same answer, no exception", async () => {
    sandbox = mkdtempSync(join(tmpdir(), "ai-eng-uninstall-"));
    const bare = join(sandbox, "bare");
    mkdirSync(bare, { recursive: true });
    process.env["AI_ENG_HOME"] = join(sandbox, "machine");
    process.chdir(bare);
    writeFileSync(join(bare, "keep.txt"), "mine\n");

    const { result, out } = await uninstall([]);

    expect(result).toBe(2);
    expect(readFileSync(join(bare, "keep.txt"), "utf8")).toBe("mine\n");
    expect(out).toContain("you are not in a governed repo — nothing of this project to remove");
  });
});

describe("the machine sweep reads the declaration before the sweep deletes it", () => {
  test("a surface declared in a LOCKED config.toml still loses its machine carrier", async () => {
    // config.toml is an owned asset, so the project side unlinks it — and the machine side
    // used to ask `enabledSurfaces()` afterwards, which then reported the no-config
    // fallback (["claude-code"]). A repo declaring pi kept `~/.pi/agent/extensions/`
    // behind: an orphan whose marker points at a chain nothing serves, which is exactly
    // what this scope exists to prevent.
    const { cwd, agentDir } = sandboxed();
    gitInit(cwd);
    initShaped(["pi"]); // the lock owns config.toml, declared enabled = ["pi"]
    installMachineCarriers(["pi"]);
    const entry = join(agentDir, "extensions", "ai-eng.ts");
    const chain = join(agentDir, "extensions", "ai-eng-chain.ts");
    expect(existsSync(entry)).toBe(true);

    const { result, out } = await uninstall(everythingScope("y", "y"));

    expect(result).toBe(0);
    expect(existsSync(join(cwd, ".ai-engineering", "config.toml"))).toBe(false); // the sweep took it
    expect(out).toContain("✓ ~/.pi/agent/extensions/ai-eng.ts removed");
    expect(existsSync(entry)).toBe(false);
    expect(existsSync(chain)).toBe(false);
  });
});
