// tests/uninstall-command.spec.ts — behaviour gates for `ai-eng uninstall`
// (src/commands/uninstall.ts). The product's promise is "revert ai-eng's files, keep
// yours", so every claim here is about the disk afterwards: the files that are gone, the
// files still there with their original bytes, the restored legacy `git config
// init.templateDir`, the machine record, and the number uninstallMain() returns.
//
// The starting states are built with the real installers — `install()` over
// planEntries()/contractEntries() plus lockText(), exactly init's shape;
// installMachineCarriers(); legacy template state is seeded as older versions wrote it.
// The interactive path is driven through src/ui.ts's scriptedInput: keys are fed only
// after the prompt that reads them has rendered, so nothing here can block on a TTY.
//
// Sandbox: AI_ENG_HOME and PI_CODING_AGENT_DIR point into a mkdtemp() per test, and the
// global git config is the sandbox's own file (GIT_CONFIG_GLOBAL, which template.ts honours
// over the developer's), so ~/.claude, ~/.ai-engineering, ~/.pi and ~/.gitconfig are never
// read or written.

import { afterAll, afterEach, describe, expect, spyOn, test } from "bun:test";
import { spawnSync } from "node:child_process";
import * as fs from "node:fs";
import { chmodSync, existsSync, lstatSync, mkdirSync, mkdtempSync, readFileSync, realpathSync, renameSync, rmSync, symlinkSync, unlinkSync, writeFileSync } from "node:fs";
import { hostname, tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { uninstallMain } from "../src/commands/uninstall.ts";
import { embeddedPath, embeddedUnder, recordCanonOwnership } from "../src/embed.ts";
import { contractEntries, planEntries } from "../src/commands/init-shared.ts";
import { buildLock, install, lockText, sha256 } from "../src/install.ts";
import { installCanon, installMachineCarriers, machineStateFile, machineStateLockFile, machineStateLockScope, readMachineState } from "../src/surfaces/adapters.ts";
import { VERSION } from "../src/version.ts";
import { restoreSandboxEnv, snapshotSandboxEnv } from "./fixtures/sandbox-env.ts";
import { usePrivateStdin } from "./fixtures/private-stdin.ts";

const cwdBefore = process.cwd();
const envBefore = snapshotSandboxEnv();
process.env["NO_COLOR"] = "1";
process.env["CI"] = "1";
// The keys go through a stdin only this suite writes to: on the runner's real one, a stray
// byte from whatever launched `bun test` answers the open prompt (tests/fixtures/private-stdin.ts).
const stdin = usePrivateStdin();

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
const LEGACY_SHIMS = ["pre-commit", "commit-msg", "pre-push"] as const;
const LEGACY_SHIM_MARKER = "ai-eng git floor shim";
const OPTIONAL_PACKS = [
  { id: "triage", skill: "ai-triage" },
  { id: "design-md-planner", skill: "ai-design-md-planner" },
  { id: "audit-design", skill: "ai-audit-design" },
  { id: "visual-recap", skill: "ai-visual-recap" },
  { id: "writing-behavior", skill: "ai-writing-behavior" },
  { id: "stress-test", skill: "ai-stress-test" },
] as const;

let sandbox: string | undefined;

/** A repo-shaped project and a machine of its own. Nothing outside this directory is
 *  written: AI_ENG_HOME redirects the canon, the carrier base and — through template.ts —
 *  the global git config; PI_CODING_AGENT_DIR redirects the two relocatable agent dirs
 *  OUTSIDE the canon home, so a carrier removed there is removed by the sweep rather than
 *  by deleting the machine home. */
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
  // deliberately OUTSIDE the canon home, so the test proves the setting is restored
  // independently of the selective machine-asset sweep.
  process.env["GIT_CONFIG_GLOBAL"] = join(sandbox, "gitconfig");
  process.chdir(cwd);
  return { cwd, machine, agentDir };
}

function gitInit(cwd: string): void {
  const done = spawnSync("git", ["init", "-q"], { cwd, encoding: "utf8" });
  if (done.status !== 0) throw new Error(`git init failed: ${done.stderr}`);
}

/** The global `init.templateDir` exactly as git sees it for this sandbox. */
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

function writeLegacyTemplateShims(dir: string, names: readonly string[] = LEGACY_SHIMS): void {
  for (const name of names) {
    const path = join(dir, "hooks", name);
    mkdirSync(join(dir, "hooks"), { recursive: true });
    writeFileSync(path, `#!/bin/sh\n# ${LEGACY_SHIM_MARKER}\n`, { mode: 0o755 });
  }
}

function recordLegacyTemplateDir(previous: string | null, ours: string | null): void {
  writeFileSync(
    machineStateFile(),
    `${JSON.stringify({ version: "2.5.0", carriers: {}, templateDir: { previous, ours } }, null, 2)}\n`,
  );
}

function sourceSkillFile(skillName: string): string {
  const repo = join(import.meta.dir, "..");
  const path = join(repo, "skills", skillName, "SKILL.md");
  if (!existsSync(path)) throw new Error(`the canonical inventory has no SKILL.md for ${skillName}`);
  return path;
}

/** A real init-shaped install: the contract files once, the plan's files, the shims made
 *  executable, and the lock built from the same entries — src/commands/init.ts's
 *  scaffoldProject(), with the human's lines left out. Returns the paths it owns. */
function initShaped(surfaces: string[]): string[] {
  const cwd = process.cwd();
  install(cwd, contractEntries("2026-09-14"));
  const entries = planEntries(surfaces);
  install(cwd, entries);
  for (const shim of LEGACY_SHIMS) {
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

function replaceParentOnChdir(parent: string, outside: string): { wasTriggered: () => boolean; restore: () => void } {
  const originalChdir = process.chdir.bind(process);
  let wasTriggered = false;
  process.chdir = (directory: string) => {
    if (!wasTriggered && String(directory) === parent) {
      wasTriggered = true;
      renameSync(parent, `${parent}-before-race`);
      symlinkSync(outside, parent, "dir");
    }
    originalChdir(directory);
  };
  return {
    wasTriggered: () => wasTriggered,
    restore: () => { process.chdir = originalChdir; },
  };
}

function mutateFileOnSecondChdir(parent: string, mutate: () => void): { wasTriggered: () => boolean; restore: () => void } {
  const originalChdir = process.chdir.bind(process);
  let parentChanges = 0;
  let wasTriggered = false;
  process.chdir = (directory: string) => {
    if (directory === parent && ++parentChanges === 2) {
      wasTriggered = true;
      mutate();
    }
    originalChdir(directory);
  };
  return {
    wasTriggered: () => wasTriggered,
    restore: () => { process.chdir = originalChdir; },
  };
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
  // Restore, never delete: a later suite in the same process must see the home it started with.
  restoreSandboxEnv(envBefore);
  if (sandbox) rmSync(sandbox, { recursive: true, force: true });
  sandbox = undefined;
});

afterAll(() => {
  stdin.restore();
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

  test("a byte on the runner's own stdin never answers a prompt: the sweep still runs", async () => {
    const { cwd } = sandboxed();
    gitInit(cwd);
    initShaped(["cursor"]);
    // Premise: the suite's prompts read a stream of their own, not the runner's.
    expect(process.stdin).not.toBe(stdin.runnerStdin);

    const cap = startCapture();
    const run = uninstallMain();
    try {
      await until(cap, SELECT);
      // A newline from the shell that launched the run — on a shared stdin it is Enter on
      // the scope picker, the scripted Enter then lands on "Confirm?" (default No), and
      // nothing is removed.
      stdin.runnerStdin.emit("data", Buffer.from("\n"));
      await sleep(40);
      process.stdin.emit("data", Buffer.from(PROJECT_KEYS));
      await until(cap, CONFIRM);
      process.stdin.emit("data", Buffer.from("y"));
      expect(await run).toBe(0);
    } finally {
      cap.stop();
    }
    expect(existsSync(join(cwd, ".ai-engineering", "ai-eng.lock"))).toBe(false);
    expect(existsSync(join(cwd, ".cursor", "hooks.json"))).toBe(false);
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

  test("a file ai-eng wrote goes even when edited; seeded config you edited is yours and stays", async () => {
    const { cwd } = sandboxed();
    gitInit(cwd);
    initShaped(["claude-code"]);
    const rules = join(cwd, ".ai-engineering", "arch.rules.json");
    const edited = `${readFileSync(rules, "utf8")}\n`;
    writeFileSync(rules, edited);
    const workflow = join(cwd, ".github", "workflows", "ai-eng-check.yml");
    writeFileSync(workflow, `${readFileSync(workflow, "utf8")}# my extra step\n`);

    const { result, out } = await uninstall([
      [SELECT, PROJECT_KEYS],
      [CONFIRM, "y"],
    ]);

    expect(result).toBe(0);
    expect(readFileSync(rules, "utf8")).toBe(edited);
    expect(out).toContain("✓ .ai-engineering/arch.rules.json kept · config you edited — yours");
    expect(existsSync(workflow)).toBe(false);
    expect(out).toContain("✓ .github/workflows/ai-eng-check.yml removed · edited since install — ai-eng's file all the same");
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

  test("with no lock, a file at a shipped path whose bytes are not ai-eng's is never deleted", async () => {
    const { cwd } = sandboxed();
    gitInit(cwd);
    initShaped(["claude-code"]);
    unlinkSync(join(cwd, ".ai-engineering", "ai-eng.lock"));
    // No lock records it, so a different file at this name may well be the project's own.
    const workflow = join(cwd, ".github", "workflows", "ai-eng-check.yml");
    const theirs = "name: our own check\non: push\n";
    writeFileSync(workflow, theirs);

    const { result, out } = await uninstall([
      [SELECT, PROJECT_KEYS],
      [CONFIRM, "y"],
    ]);

    expect(result).toBe(0);
    expect(readFileSync(workflow, "utf8")).toBe(theirs);
    expect(out).toContain("▲ .github/workflows/ai-eng-check.yml kept · no lock records it and its bytes are not ai-eng's — yours");
    expect(existsSync(join(cwd, ".ai-engineering", "config.toml"))).toBe(false);
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

  test("a linked parent in the project sweep is refused", async () => {
    const { cwd } = sandboxed();
    gitInit(cwd);
    mkdirSync(join(cwd, ".ai-engineering"), { recursive: true });
    writeFileSync(join(cwd, ".ai-engineering", "config.toml"), '[surfaces]\nenabled = ["cursor"]\n');
    const outside = join(sandbox!, "outside");
    mkdirSync(outside);
    const victim = join(outside, "hooks.json");
    const payload = "outside project\n";
    writeFileSync(victim, payload);
    symlinkSync(outside, join(cwd, ".cursor"), "dir");
    writeFileSync(
      join(cwd, ".ai-engineering", "ai-eng.lock"),
      lockText({ version: VERSION, assets: { ".cursor/hooks.json": sha256(payload) } }),
    );

    const { result, out } = await uninstall([
      [SELECT, PROJECT_KEYS],
      [CONFIRM, "y"],
    ]);

    expect(result).toBe(0);
    expect(readFileSync(victim, "utf8")).toBe(payload);
    expect(lstatSync(join(cwd, ".cursor")).isSymbolicLink()).toBe(true);
    expect(out).toContain("▲ .cursor/hooks.json kept · linked path — not ai-eng's");
  });

  test("a parent replaced by a symlink before unlink remains untouched", async () => {
    const { cwd } = sandboxed();
    gitInit(cwd);
    mkdirSync(join(cwd, ".ai-engineering"), { recursive: true });
    writeFileSync(join(cwd, ".ai-engineering", "config.toml"), '[surfaces]\nenabled = ["cursor"]\n');
    const parent = join(cwd, ".cursor");
    mkdirSync(parent);
    const outside = join(sandbox!, "outside");
    mkdirSync(outside);
    const payload = "same hash, outside the project\n";
    writeFileSync(join(parent, "hooks.json"), payload);
    const victim = join(outside, "hooks.json");
    writeFileSync(victim, payload);
    writeFileSync(
      join(cwd, ".ai-engineering", "ai-eng.lock"),
      lockText({ version: VERSION, assets: { ".cursor/hooks.json": sha256(payload) } }),
    );
    const race = replaceParentOnChdir(realpathSync(parent), outside);

    let out = "";
    try {
      ({ out } = await uninstall([
        [SELECT, PROJECT_KEYS],
        [CONFIRM, "y"],
      ]));
    } finally {
      race.restore();
    }

    expect(race.wasTriggered()).toBe(true);
    expect(readFileSync(victim, "utf8")).toBe(payload);
    expect(readFileSync(join(`${parent}-before-race`, "hooks.json"), "utf8")).toBe(payload);
    expect(out).toContain("▲ .cursor/hooks.json kept · file changed during this run, or the filesystem refused the change — preserved");
  });

  test("a parent replaced by a symlink before write remains untouched", async () => {
    const { cwd } = sandboxed();
    gitInit(cwd);
    const mine = {
      version: 1,
      hooks: { preToolUse: [{ type: "command", command: "echo my own guard", timeout: 5 }] },
    };
    const settings = join(cwd, ".cursor", "hooks.json");
    mkdirSync(join(cwd, ".cursor"), { recursive: true });
    writeFileSync(settings, `${JSON.stringify(mine, null, 2)}\n`);
    initShaped(["cursor"]);
    const originalSettings = readFileSync(settings, "utf8");
    const parent = realpathSync(join(cwd, ".cursor"));
    const outside = join(sandbox!, "outside");
    mkdirSync(outside);
    const victim = join(outside, "hooks.json");
    writeFileSync(victim, "outside settings\n");
    const race = replaceParentOnChdir(parent, outside);

    let out = "";
    try {
      ({ out } = await uninstall([
        [SELECT, PROJECT_KEYS],
        [CONFIRM, "y"],
      ]));
    } finally {
      race.restore();
    }

    expect(race.wasTriggered()).toBe(true);
    expect(readFileSync(victim, "utf8")).toBe("outside settings\n");
    expect(readFileSync(join(`${parent}-before-race`, "hooks.json"), "utf8")).toBe(originalSettings);
    expect(out).toContain("▲ .cursor/hooks.json kept · file changed during this run, or the filesystem refused the change — preserved");
  });

  test("a same-content file replacement before unlink is preserved", async () => {
    const { cwd } = sandboxed();
    gitInit(cwd);
    mkdirSync(join(cwd, ".ai-engineering"), { recursive: true });
    writeFileSync(join(cwd, ".ai-engineering", "config.toml"), '[surfaces]\nenabled = ["cursor"]\n');
    const parent = join(cwd, ".cursor");
    mkdirSync(parent);
    const file = join(parent, "hooks.json");
    const payload = "canon payload\n";
    writeFileSync(file, payload);
    writeFileSync(
      join(cwd, ".ai-engineering", "ai-eng.lock"),
      lockText({ version: VERSION, assets: { ".cursor/hooks.json": sha256(payload) } }),
    );
    const race = mutateFileOnSecondChdir(realpathSync(parent), () => {
      renameSync(file, `${file}-before-race`);
      writeFileSync(file, payload);
    });

    let out = "";
    try {
      ({ out } = await uninstall([
        [SELECT, PROJECT_KEYS],
        [CONFIRM, "y"],
      ]));
    } finally {
      race.restore();
    }

    expect(race.wasTriggered()).toBe(true);
    expect(readFileSync(file, "utf8")).toBe(payload);
    expect(readFileSync(`${file}-before-race`, "utf8")).toBe(payload);
    expect(out).toContain("▲ .cursor/hooks.json kept · file changed during this run, or the filesystem refused the change — preserved");
  });

  test("changed settings content before write is preserved", async () => {
    const { cwd } = sandboxed();
    gitInit(cwd);
    const mine = {
      version: 1,
      hooks: { preToolUse: [{ type: "command", command: "echo my own guard", timeout: 5 }] },
    };
    const settings = join(cwd, ".cursor", "hooks.json");
    mkdirSync(join(cwd, ".cursor"), { recursive: true });
    writeFileSync(settings, `${JSON.stringify(mine, null, 2)}\n`);
    initShaped(["cursor"]);
    const originalIdentity = lstatSync(settings).ino;
    const replacement = "replacement user content\n";
    const parent = realpathSync(join(cwd, ".cursor"));
    const race = mutateFileOnSecondChdir(parent, () => writeFileSync(settings, replacement));

    let out = "";
    try {
      ({ out } = await uninstall([
        [SELECT, PROJECT_KEYS],
        [CONFIRM, "y"],
      ]));
    } finally {
      race.restore();
    }

    expect(race.wasTriggered()).toBe(true);
    expect(lstatSync(settings).ino).toBe(originalIdentity);
    expect(readFileSync(settings, "utf8")).toBe(replacement);
    expect(out).toContain("▲ .cursor/hooks.json kept · file changed during this run, or the filesystem refused the change — preserved");
  });

  test("project pruning keeps a non-empty carrier directory", async () => {
    const { cwd } = sandboxed();
    gitInit(cwd);
    initShaped(["cursor"]);
    const userFile = join(cwd, ".cursor", "notes.txt");
    writeFileSync(userFile, "keep this\n");

    const { result } = await uninstall([
      [SELECT, PROJECT_KEYS],
      [CONFIRM, "y"],
    ]);

    expect(result).toBe(0);
    expect(readFileSync(userFile, "utf8")).toBe("keep this\n");
    expect(existsSync(join(cwd, ".cursor"))).toBe(true);
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
    // dir, outside the canon home this scope sweeps, so an orphan is exactly what is left
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
    expect(existsSync(join(cwd, "CLAUDE.md"))).toBe(false); // no shim is written anymore
    expect(existsSync(join(cwd, ".gitignore"))).toBe(false); // still the template we installed
    expect(existsSync(join(cwd, ".ai-engineering"))).toBe(false);
    // The full line may wrap in a narrow terminal (e.g. stryker's sandbox), so check
    // the prefix and the file list separately — both must appear, order is irrelevant.
    expect(out).toContain("▲ project contract files removed (your choice)");
    expect(out).toContain("AGENTS.md · DECISIONS.md · .gitignore · .ai-engineering/");
    expect(out).toContain(`✓ kept: ${machine} · global skills stay installed`); // the second question is separate
    expect(existsSync(machine)).toBe(true);
  });

  test("an edited .gitignore survives even the Everything scope", async () => {
    const { cwd } = sandboxed();
    gitInit(cwd);
    initShaped(["claude-code"]);
    writeFileSync(join(cwd, ".gitignore"), ".DS_Store\nmy-own-rule\n");

    const { result, out } = await uninstall(everythingScope("y", "n"));

    expect(result).toBe(0);
    expect(readFileSync(join(cwd, ".gitignore"), "utf8")).toBe(".DS_Store\nmy-own-rule\n");
    expect(out).toContain("▲ project contract files removed (your choice)");
    // The dim line names what went: .gitignore is not claimed while it carries the user's rule.
    expect(out).toContain("AGENTS.md · DECISIONS.md · .ai-engineering/");
  });

  test("a machine settings carrier merged into the user's file leaves it with ours out and theirs in, and said", async () => {
    const { cwd, machine } = sandboxed();
    gitInit(cwd);
    initShaped(["claude-code"]);
    // The state `ai-eng config --add copilot` leaves: config.toml declares a surface the
    // lock predates, so the project sweep keeps it as the user's and the declaration is
    // still readable when the machine side runs.
    writeFileSync(join(cwd, ".ai-engineering", "config.toml"), '[surfaces]\nenabled = ["copilot"]\n');
    const copilotSettings = join(machine, ".copilot", "hooks", "ai-eng.json");
    mkdirSync(join(machine, ".copilot", "hooks"), { recursive: true });
    const originalSettings = `${JSON.stringify({ user: "owned" }, null, 2)}\n`;
    writeFileSync(copilotSettings, originalSettings);
    expect(installMachineCarriers(["copilot-cli"])).toEqual({ written: ["~/.copilot/hooks/ai-eng.json"], untouched: [], retired: [], refused: [] });
    expect(readFileSync(copilotSettings, "utf8")).toMatch(/ai-eng(?:\.cmd|\.exe)? chain/);

    const { result, out } = await uninstall(everythingScope("n", "y"));

    expect(result).toBe(0);
    expect(out).toContain("~/.copilot/hooks/ai-eng.json: ai-eng entries removed, yours kept");
    expect(out).toContain(`✓ ${machine} kept · 0 ai-eng path(s) removed · 0 machine artifacts swept · other files kept`);
    // Every hook of ours is out and the user's key stays. Copilot's `version: 1` is a scalar
    // the merge set and the strip cannot tell from one the user wrote, so it stays too.
    expect(JSON.parse(readFileSync(copilotSettings, "utf8"))).toEqual({ user: "owned", version: 1 });
    expect(existsSync(machine)).toBe(true);
    expect(existsSync(join(cwd, ".ai-engineering", "config.toml"))).toBe(true); // "no" kept the project's files
  });

  // Windows has no unreadable mode: chmod 0o000 only clears the write bit, so the file stays readable.
  test.skipIf(process.platform === "win32")("F11: an unreadable machine settings file is refused and the canon sweep still runs", async () => {
    if (process.getuid?.() === 0) return; // root reads a mode-000 file, so there is nothing to refuse
    const { cwd, machine } = sandboxed();
    gitInit(cwd);
    initShaped(["claude-code"]);
    const [assetPath, assetRef] = [...embeddedUnder("skills/")].find(([path]) => path.endsWith("/SKILL.md"))!;
    mkdirSync(dirname(join(machine, assetPath)), { recursive: true });
    writeFileSync(join(machine, assetPath), readFileSync(embeddedPath(assetRef)));
    const settings = join(machine, ".claude", "settings.json");
    mkdirSync(dirname(settings), { recursive: true });
    writeFileSync(settings, '{\n  "user": "keep"\n}\n');
    chmodSync(settings, 0o000);

    const run = await uninstall(everythingScope("n", "y")).finally(() => chmodSync(settings, 0o644));

    expect(run.result).toBe(0);
    expect(run.out).toContain("~/.claude/settings.json — unreadable, a dangling link, not a regular file, or changing while read; left untouched");
    expect(existsSync(join(machine, assetPath))).toBe(false);
    expect(readFileSync(settings, "utf8")).toBe('{\n  "user": "keep"\n}\n');
  });

  test("F17: Everything removes the version cache and ownership record it wrote, so an otherwise empty home goes", async () => {
    const { cwd, machine } = sandboxed();
    gitInit(cwd);
    initShaped(["claude-code"]);
    writeFileSync(join(machine, "version.json"), JSON.stringify({ version: VERSION, ts: Date.now() }));
    recordCanonOwnership(machine);

    const { result, out } = await uninstall(everythingScope("n", "y"));

    expect(result).toBe(0);
    expect(out).toContain(`${machine} deleted`);
    expect(existsSync(machine)).toBe(false);
  });

  test("F29: a canon file and a slash command in read-only folders are kept and named, and the machine home stays", async () => {
    // Windows chmod cannot deny a delete, and root ignores the mode: nothing to refuse there.
    if (process.platform === "win32" || process.getuid?.() === 0) return;
    const { cwd, machine } = sandboxed();
    gitInit(cwd);
    initShaped(["claude-code"]);
    installCanon(VERSION);
    const skillFolder = join(machine, "skills", "ai-debug");
    const commands = join(machine, ".config", "opencode", "commands");
    const canonFile = join(realpathSync(machine), "skills", "ai-debug", "SKILL.md");
    const command = join(commands, "ai-debug.md");
    const canonBytes = readFileSync(canonFile, "utf8");
    const commandBytes = readFileSync(command, "utf8");
    chmodSync(skillFolder, 0o555);
    chmodSync(commands, 0o555);

    const run = await uninstall(everythingScope("n", "y")).finally(() => {
      chmodSync(skillFolder, 0o755);
      chmodSync(commands, 0o755);
    });

    const keptText = "kept · still ai-eng's, but it changed during uninstall or the filesystem refused the change — preserved";
    expect(run.result).toBe(0);
    expect(run.out).toContain(`${canonFile} ${keptText}`);
    expect(run.out).toContain(`${command} ${keptText}`);
    expect(readFileSync(canonFile, "utf8")).toBe(canonBytes);
    expect(readFileSync(command, "utf8")).toBe(commandBytes);
    expect(run.out).toContain(`${machine} kept`);
  });

  // Windows chmod cannot deny a delete, and root ignores the mode: nothing to refuse there.
  test.skipIf(process.platform === "win32" || process.getuid?.() === 0)("a retired skill's command the filesystem would not remove keeps the ownership record, and the next uninstall takes it", async () => {
    const { cwd, machine } = sandboxed();
    gitInit(cwd);
    initShaped(["claude-code"]);
    const commands = join(machine, ".config", "opencode", "commands");
    const command = join(commands, "ai-retired.md");
    mkdirSync(commands, { recursive: true });
    writeFileSync(command, "a command ai-eng wrote for a skill it no longer ships\n");
    writeFileSync(join(machine, "canon-owned.json"), JSON.stringify({ files: { "skills/ai-retired/SKILL.md": sha256("as shipped\n") } }));
    chmodSync(commands, 0o555);

    const first = await uninstall(everythingScope("n", "y")).finally(() => chmodSync(commands, 0o755));

    expect(first.out).toContain(`${command} kept`);
    expect(existsSync(join(machine, "canon-owned.json"))).toBe(true);

    gitInit(cwd);
    initShaped(["claude-code"]);
    const second = await uninstall(everythingScope("n", "y"));

    expect(second.result).toBe(0);
    expect(existsSync(command)).toBe(false);
  });

  test("F22: Everything removes ai-eng's skill folders whole, edited or not, and a retired one; a skill of your own and the record's other paths stay", async () => {
    const { cwd, machine } = sandboxed();
    gitInit(cwd);
    initShaped(["claude-code"]);
    const olderPage = "skills/ai-debug/a-page-an-older-version-shipped.md";
    mkdirSync(join(machine, "skills", "ai-debug"), { recursive: true });
    writeFileSync(join(machine, olderPage), "older payload\n");
    mkdirSync(join(machine, "skills", "ai-retired"), { recursive: true });
    writeFileSync(join(machine, "skills", "ai-retired", "SKILL.md"), "edited by hand\n");
    mkdirSync(join(machine, "skills", "my-own-skill"), { recursive: true });
    writeFileSync(join(machine, "skills", "my-own-skill", "SKILL.md"), "mine\n");
    writeFileSync(join(machine, "canon-owned.json"), JSON.stringify({ files: { "skills/ai-retired/SKILL.md": sha256("as shipped\n") } }));

    const { result, out } = await uninstall(everythingScope("n", "y"));

    expect(result).toBe(0);
    expect(existsSync(join(machine, "skills", "ai-debug"))).toBe(false);
    expect(existsSync(join(machine, "skills", "ai-retired"))).toBe(false);
    expect(readFileSync(join(machine, "skills", "my-own-skill", "SKILL.md"), "utf8")).toBe("mine\n");
    // Nothing the record vouches for is left, so the record goes with the payload.
    expect(existsSync(join(machine, "canon-owned.json"))).toBe(false);
    expect(out).toContain(`${machine} kept`);
  });

  test("Everything never deletes a folder of yours at a name ai-eng recorded as a file", async () => {
    const { cwd, machine } = sandboxed();
    gitInit(cwd);
    initShaped(["claude-code"]);
    // ai-eng wrote a file at agents/ai-retired.md; a folder there now is not what it wrote.
    writeFileSync(join(machine, "canon-owned.json"), JSON.stringify({ files: { "agents/ai-retired.md": sha256("as shipped\n") } }));
    const theirs = join(machine, "agents", "ai-retired.md", "notes.md");
    mkdirSync(dirname(theirs), { recursive: true });
    writeFileSync(theirs, "mine\n");

    const { result, out } = await uninstall(everythingScope("n", "y"));

    expect(result).toBe(0);
    expect(readFileSync(theirs, "utf8")).toBe("mine\n");
    expect(out).toContain(`${machine} kept`);
  });

  // Windows will not rename a directory that is a process's working directory, so the swap cannot be staged there.
  test.skipIf(process.platform === "win32")("F9: a canon parent swapped for a link at unlink time never redirects deletion outside the canon", async () => {
    const { cwd, machine } = sandboxed();
    gitInit(cwd);
    initShaped(["claude-code"]);
    const [assetPath, assetRef] = [...embeddedUnder("skills/")].find(([path]) => path.endsWith("/SKILL.md"))!;
    const payload = readFileSync(embeddedPath(assetRef));
    const canonFile = join(realpathSync(machine), assetPath);
    const canonParent = dirname(canonFile);
    mkdirSync(canonParent, { recursive: true });
    writeFileSync(canonFile, payload);
    const outside = join(sandbox!, "outside");
    mkdirSync(outside);
    const victim = join(outside, "SKILL.md");
    writeFileSync(victim, payload);

    const originalUnlinkSync = fs.unlinkSync;
    let wasSwapped = false;
    const unlinkSpy = spyOn(fs, "unlinkSync").mockImplementation((path) => {
      const isCanonUnlink = String(path) === canonFile || (String(path) === "SKILL.md" && process.cwd() === canonParent);
      if (!wasSwapped && isCanonUnlink) {
        wasSwapped = true;
        renameSync(canonParent, `${canonParent}-before-race`);
        symlinkSync(outside, canonParent, "dir");
      }
      return originalUnlinkSync(path);
    });
    try {
      await uninstall(everythingScope("n", "y"));
    } finally {
      unlinkSpy.mockRestore();
    }

    expect(wasSwapped).toBe(true);
    expect(readFileSync(victim)).toEqual(payload);
    expect(lstatSync(canonParent).isSymbolicLink()).toBe(true);
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
    expect(out).toContain("✓ kept: AGENTS.md, DECISIONS.md, .gitignore, .ai-engineering/");
    expect(existsSync(join(cwd, ".ai-engineering", "config.toml"))).toBe(false); // the repo side still ran
    expect(existsSync(join(cwd, "AGENTS.md"))).toBe(true);
  });

  test("an older version's templateDir is removed and the setting goes back to unset", async () => {
    const { cwd, machine } = sandboxed();
    gitInit(cwd);
    initShaped(["claude-code"]);

    const ours = join(machine, "git-template");
    writeLegacyTemplateShims(ours);
    recordLegacyTemplateDir(null, ours);
    setGlobalTemplateDir(ours);
    expect(globalTemplateDir()).toBe(ours);

    const { result, out } = await uninstall(everythingScope("n", "y"));

    expect(result).toBe(0);
    expect(globalTemplateDir()).toBeNull(); // it was unset before, so it is unset after
    expect(existsSync(ours)).toBe(false);
    expect(out).toContain("✓ git init.templateDir unset (it was unset before)");
  });

  test("F18: a dead run's lock and claim are recovered before the git floor is read", async () => {
    const { cwd, machine } = sandboxed();
    gitInit(cwd);
    initShaped(["claude-code"]);
    const ours = join(machine, "git-template");
    writeLegacyTemplateShims(ours);
    recordLegacyTemplateDir(null, ours);
    setGlobalTemplateDir(ours);
    const deadPid = spawnSync("true").pid;
    writeFileSync(machineStateLockFile(), JSON.stringify({ pid: deadPid, hostname: hostname(), startedAt: "2026-01-01T00:00:00.000Z", ...machineStateLockScope() }));
    renameSync(machineStateFile(), join(machine, ".machine.json.4242.abcdef012345.claim"));

    const { result, out } = await uninstall(everythingScope("n", "y"));

    expect(result).toBe(0);
    expect(globalTemplateDir()).toBeNull();
    expect(out).toContain("✓ git init.templateDir unset (it was unset before)");
    expect(existsSync(machineStateLockFile())).toBe(false);
  });

  test("F18: a lock this run cannot prove stale leaves git init.templateDir alone, and says so", async () => {
    const { cwd, machine } = sandboxed();
    gitInit(cwd);
    initShaped(["claude-code"]);
    const ours = join(machine, "git-template");
    writeLegacyTemplateShims(ours);
    recordLegacyTemplateDir(null, ours);
    setGlobalTemplateDir(ours);
    const lockPath = machineStateLockFile();
    const foreignLock = JSON.stringify({ pid: 1, hostname: "another-host", startedAt: "2026-01-01T00:00:00.000Z" });
    writeFileSync(lockPath, foreignLock);

    const { result, out } = await uninstall(everythingScope("n", "y"));

    expect(result).toBe(0);
    expect(globalTemplateDir()).toBe(ours);
    expect(out).toContain(`git init.templateDir not restored — ${lockPath} — held by another ai-eng run`);
    expect(readFileSync(lockPath, "utf8")).toBe(foreignLock);
  });

  test("an older templateDir is restored and legacy pack settings do not limit uninstall", async () => {
    const { cwd, machine } = sandboxed();
    gitInit(cwd);
    initShaped(["claude-code"]);
    writeFileSync(
      join(cwd, ".ai-engineering", "config.toml"),
      `[surfaces]\nenabled = ["claude-code"]\n\n[canon]\npacks = [${[...OPTIONAL_PACKS.map((pack) => pack.id), "verify-tiers"].map((pack) => `"${pack}"`).join(", ")}]\n`,
    );
    const coreSkill = join(machine, "skills", "ai-orchestrator", "SKILL.md");
    mkdirSync(join(machine, "skills", "ai-orchestrator"), { recursive: true });
    writeFileSync(coreSkill, readFileSync(join(import.meta.dir, "..", "skills", "ai-orchestrator", "SKILL.md"), "utf8"));
    const installedPackSkills = OPTIONAL_PACKS.map(({ skill }) => {
      const path = join(machine, "skills", skill, "SKILL.md");
      mkdirSync(join(machine, "skills", skill), { recursive: true });
      writeFileSync(path, readFileSync(sourceSkillFile(skill), "utf8"));
      return path;
    });
    const verifyTiersPack = join(machine, "skills", "ai-verify", "tiers", "installed-pack-check");
    mkdirSync(join(machine, "skills", "ai-verify", "tiers"), { recursive: true });
    writeFileSync(verifyTiersPack, "selected verify-tiers pack\n");
    const customSkill = join(machine, "skills", "my-local-skill", "SKILL.md");
    mkdirSync(join(machine, "skills", "my-local-skill"), { recursive: true });
    writeFileSync(customSkill, "my local skill\n");
    const editedSkill = join(machine, "skills", "ai-debug", "SKILL.md");
    mkdirSync(join(machine, "skills", "ai-debug"), { recursive: true });
    writeFileSync(editedSkill, "my edited skill\n");
    const unrelated = join(machine, "notes.txt");
    writeFileSync(unrelated, "keep this file\n");
    expect([...installedPackSkills, verifyTiersPack, customSkill, editedSkill, unrelated].every(existsSync)).toBe(true);

    const previous = join(sandbox!, "older-template");
    const ours = join(sandbox!, "legacy-owned-template");
    writeLegacyTemplateShims(ours);
    mkdirSync(join(previous, "hooks"), { recursive: true });
    const existingHook = "#!/bin/sh\necho older template\n";
    writeFileSync(join(previous, "hooks", "pre-commit"), existingHook);
    setGlobalTemplateDir(ours);
    recordLegacyTemplateDir(previous, ours);
    expect(globalTemplateDir()).toBe(ours);

    const { result, out } = await uninstall(everythingScope("n", "y"));

    expect(result).toBe(0);
    expect(existsSync(coreSkill)).toBe(false);
    for (const path of installedPackSkills) expect(existsSync(path)).toBe(false);
    // A shipped skill folder is ai-eng's whole: an extra file in it and an edited page go too.
    expect(existsSync(verifyTiersPack)).toBe(false);
    expect(readFileSync(customSkill, "utf8")).toBe("my local skill\n");
    expect(existsSync(editedSkill)).toBe(false);
    expect(readFileSync(unrelated, "utf8")).toBe("keep this file\n");
    expect(existsSync(machine)).toBe(true);
    expect(globalTemplateDir()).toBe(previous);
    expect(existsSync(ours)).toBe(false);
    expect(readFileSync(join(previous, "hooks", "pre-commit"), "utf8")).toBe(existingHook);
    expect(out).toContain(`✓ git init.templateDir restored to ${previous}`);
  });

  test("a templateDir the user owned keeps their setting and loses only our shims", async () => {
    const { cwd } = sandboxed();
    gitInit(cwd);
    initShaped(["claude-code"]);
    const userDir = join(sandbox!, "user-template");
    mkdirSync(join(userDir, "hooks"), { recursive: true });
    const theirs = "#!/bin/sh\necho my own pre-push\n";
    writeFileSync(join(userDir, "hooks", "pre-push"), theirs);
    writeLegacyTemplateShims(userDir, ["pre-commit", "commit-msg"]);
    setGlobalTemplateDir(userDir);
    recordLegacyTemplateDir(userDir, null);

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
