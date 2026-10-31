// tests/init-command.spec.ts — behaviour gates for `ai-eng init`: the pure plan seams
// in src/commands/init-shared.ts and the two phases of initMain (§14.0a).
//
// Every claim here is observable: the exit code initMain returns, a file that now
// exists and its bytes, the global git config the floor wrote, and the lines a human
// reads. Prompt paths are driven through src/ui.ts's scriptedInput — the wrapper replays
// the pipe as keypress events, so a test feeds keys and synchronises on the prompt's own
// message appearing on stdout instead of guessing at timings.
//
// Sandbox: AI_ENG_HOME and PI_CODING_AGENT_DIR point into a mkdtemp() per test, so the
// canon, the machine carriers and — through template.ts's gitEnv — the global git config
// of the developer running the suite are never touched.

import { describe, test, expect, afterEach, afterAll, spyOn } from "bun:test";
import * as childProcess from "node:child_process";
import { spawnSync } from "node:child_process";
import {
  chmodSync,
  existsSync,
  mkdirSync,
  mkdtempSync,
  readdirSync,
  readFileSync,
  readlinkSync,
  realpathSync,
  rmSync,
  statSync,
  symlinkSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { basename, delimiter, dirname, join, relative, resolve } from "node:path";
import { initMain, surfaceHint } from "../src/commands/init.ts";
import {
  contractEntries,
  detectCommands,
  gitHookEntries,
  hasAdapter,
  planEntries,
  refuseLine,
  repoTemplateRoot,
  surfaceOptions,
} from "../src/commands/init-shared.ts";
import { SURFACES, type Surface } from "../src/surfaces/adapters.ts";
import { parseLock } from "../src/install.ts";
import { VERSION } from "../src/version.ts";
import { restoreSandboxEnv, snapshotSandboxEnv } from "./fixtures/sandbox-env.ts";
import { usePrivateStdin } from "./fixtures/private-stdin.ts";

const cwdBefore = process.cwd();
const envBefore = snapshotSandboxEnv();
// The keys go through a stdin only this suite writes to: on the runner's real one, a stray
// byte from whatever launched `bun test` answers the open prompt (tests/fixtures/private-stdin.ts).
const stdin = usePrivateStdin();
const GIT_IDENTITY = ["GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL"] as const;

process.env["NO_COLOR"] = "1";
process.env["CI"] = "1";
process.env["AI_ENG_NO_UPDATE_NOTICES"] = "1";

let sandbox: string | undefined;

/** A repo-shaped sandbox of its own and a machine of its own. Nothing outside it is
 *  written: AI_ENG_HOME redirects the canon and the carrier base, and template.ts puts
 *  the global git config under the same override — only while GIT_CONFIG_GLOBAL is
 *  unset, so the sandbox owns that variable too instead of writing to an inherited one. */
function sandboxed(): { cwd: string; machine: string } {
  sandbox = mkdtempSync(join(tmpdir(), "ai-eng-init-"));
  const cwd = join(sandbox, "project");
  const machine = join(sandbox, "machine");
  mkdirSync(cwd, { recursive: true });
  mkdirSync(machine, { recursive: true });
  process.env["AI_ENG_HOME"] = machine;
  process.env["PI_CODING_AGENT_DIR"] = join(machine, "pi-agent");
  delete process.env["GIT_CONFIG_GLOBAL"];
  process.chdir(cwd);
  return { cwd, machine };
}

function gitIn(args: string[], cwd: string, env: Record<string, string> = {}): string {
  const r = spawnSync("git", args, { cwd, encoding: "utf8", env: { ...process.env, ...env } });
  return r.stdout ?? "";
}

function recordGitCommands(directory: string): { path: string; log: string } {
  const git = spawnSync("which", ["git"], { encoding: "utf8" }).stdout?.trim();
  if (!git) throw new Error("git is not on PATH");
  const bin = join(directory, "git-bin");
  const log = join(bin, "commands");
  const quote = (value: string) => `'${value.replaceAll("'", "'\\''")}'`;
  mkdirSync(bin, { recursive: true });
  writeFileSync(join(bin, "git"), `#!/bin/sh\nprintf '%s\\n' "$*" >> ${quote(log)}\nexec ${quote(git)} "$@"\n`);
  chmodSync(join(bin, "git"), 0o755);
  return { path: `${bin}${delimiter}${process.env["PATH"] ?? ""}`, log };
}

const sleep = (ms: number): Promise<void> => {
  const { promise, resolve } = Promise.withResolvers<void>();
  setTimeout(resolve, ms);
  return promise;
};

/** Capture everything the frame writes. clack resolves `process.stdout` at call time,
 *  so patching its write is enough — and the patch is restored in `stop()`. */
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

async function capture<T>(run: () => Promise<T>): Promise<{ result: T; out: string }> {
  const cap = startCapture();
  try {
    return { result: await run(), out: cap.stop() };
  } finally {
    cap.stop();
  }
}

/** A single word: clack wraps prompt text on spaces, so a short word is exactly the
 *  fragment that cannot be split across two lines. */
async function until(cap: { chunks: string[] }, fragment: string, ms = 3000): Promise<void> {
  const deadline = Date.now() + ms;
  while (!cap.chunks.join("").includes(fragment)) {
    if (Date.now() > deadline) throw new Error(`prompt "${fragment}" never appeared:\n${cap.chunks.join("")}`);
    await sleep(5);
  }
  await sleep(20); // the render that showed the message and the listener that reads the key are the same tick
}

/** Run initMain with no --yes, answering each prompt when it appears. */
async function driven(flags: Parameters<typeof initMain>[0], steps: Array<[string, string]>): Promise<{ result: number; out: string }> {
  const cap = startCapture();
  const run = initMain(flags);
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

afterEach(() => {
  process.chdir(cwdBefore);
  restoreSandboxEnv(envBefore);
  for (const name of GIT_IDENTITY) delete process.env[name];
  // scriptedInput attaches one data listener per call; a suite that runs the verb a
  // dozen times would otherwise cross Node's cap of 10 and print a leak warning.
  process.stdin.removeAllListeners("data");
  if (sandbox) rmSync(sandbox, { recursive: true, force: true });
  sandbox = undefined;
});

afterAll(() => {
  stdin.restore();
});

const byId = (id: string): Surface => {
  const found = SURFACES.find((s) => s.id === id);
  if (!found) throw new Error(`surface ${id} is not declared in surfaces.json`);
  return found;
};

const REPO_ROOT = resolve(import.meta.dir, "..");

function skillNames(root: string): string[] {
  if (!existsSync(root)) return [];
  return readdirSync(root, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && !entry.name.startsWith(".") && existsSync(join(root, entry.name, "SKILL.md")))
    .map((entry) => entry.name)
    .sort();
}

function filesBelow(directory: string): string[] {
  if (!existsSync(directory)) return [];
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    return entry.isDirectory() ? filesBelow(path) : [path];
  });
}

type Execution = { command: string; args: string[]; cwd: string; isShell: boolean };

const INTERPRETERS = new Set(["sh", "bash", "zsh", "dash", "fish", "node", "bun", "bunx", "npx", "deno", "tsx", "python", "python3", "perl", "ruby", "pwsh", "powershell", "cmd", "env"]);

/** Every process the code under test starts, through node:child_process or Bun's own
 *  spawn, recorded and then run as asked. */
function recordExecutions(): { executions: Execution[]; restore: () => void } {
  const executions: Execution[] = [];
  const asStrings = (value: unknown): string[] => (Array.isArray(value) ? value.map(String) : []);
  const optionsOf = (values: unknown[]): { cwd?: unknown; shell?: unknown } =>
    (values.find((value) => value !== null && typeof value === "object" && !Array.isArray(value)) ?? {}) as { cwd?: unknown; shell?: unknown };
  const recordNode = (command: unknown, rest: unknown[], isShellCommand: boolean) => {
    const options = optionsOf(rest);
    executions.push({
      command: String(command),
      args: asStrings(rest.find(Array.isArray)),
      cwd: typeof options.cwd === "string" ? options.cwd : process.cwd(),
      isShell: isShellCommand || Boolean(options.shell),
    });
  };
  const spies: Array<{ mockRestore: () => void }> = [];
  for (const name of ["spawn", "spawnSync", "execFile", "execFileSync", "fork"] as const) {
    const original = childProcess[name] as (...values: unknown[]) => unknown;
    spies.push(spyOn(childProcess, name).mockImplementation(((...values: unknown[]) => {
      recordNode(values[0], values.slice(1), false);
      return original(...values);
    }) as never));
  }
  for (const name of ["exec", "execSync"] as const) {
    const original = childProcess[name] as (...values: unknown[]) => unknown;
    spies.push(spyOn(childProcess, name).mockImplementation(((...values: unknown[]) => {
      recordNode(values[0], values.slice(1), true);
      return original(...values);
    }) as never));
  }
  for (const name of ["spawn", "spawnSync"] as const) {
    const original = Bun[name].bind(Bun) as (...values: unknown[]) => unknown;
    spies.push(spyOn(Bun, name).mockImplementation(((...values: unknown[]) => {
      const first = values[0] as { cmd?: unknown; cwd?: unknown } | unknown[];
      const command = Array.isArray(first) ? asStrings(first) : asStrings(first.cmd);
      const options = (Array.isArray(first) ? values[1] : first) as { cwd?: unknown } | undefined;
      executions.push({ command: command[0] ?? "", args: command.slice(1), cwd: typeof options?.cwd === "string" ? options.cwd : process.cwd(), isShell: false });
      return original(...values);
    }) as never));
  }
  return { executions, restore: () => { for (const spy of spies) spy.mockRestore(); } };
}

/** Proof that installing the canon ran nothing out of it: no started process names,
 *  or runs inside, the machine home, and none is a shell or an interpreter. */
function assertExecutedNothingFrom(machine: string, executions: Execution[]): void {
  const machinePaths = [machine, realpathSync(machine)];
  const isUnderMachine = (value: string) => machinePaths.some((path) => value === path || value.includes(`${path}/`));
  const touchingCanon = executions.filter((run) => [run.command, run.cwd, ...run.args].some(isUnderMachine));
  const interpreters = executions.filter((run) => run.isShell || run.command === process.execPath || INTERPRETERS.has(basename(run.command)));
  expect({ touchingCanon, interpreters }).toEqual({ touchingCanon: [], interpreters: [] });
}

/** The [canon].packs value as TOML itself reads it, or null when the document has none.
 *  Parsing instead of matching text means every layout TOML allows counts, so "writes no
 *  [canon].packs" cannot pass because the key was spelled in a shape a regex missed. */
function canonPacks(config: string): unknown[] | null {
  const document = Bun.TOML.parse(config) as Record<string, unknown>;
  const canon = document["canon"];
  if (typeof canon !== "object" || canon === null || !("packs" in canon)) return null;
  const packs: unknown = canon.packs;
  return Array.isArray(packs) ? packs : [packs];
}

function assertCanon(home: string): void {
  const sourceSkills = join(REPO_ROOT, "skills");
  const installedSkills = join(home, "skills");
  const names = skillNames(sourceSkills);
  expect(names.length).toBeGreaterThan(0);
  expect(skillNames(installedSkills)).toEqual(names);
  for (const name of names) {
    const source = join(sourceSkills, name);
    const installed = join(installedSkills, name);
    for (const path of filesBelow(source).filter((file) => basename(file) !== ".DS_Store")) {
      expect(readFileSync(join(installed, relative(source, path)), "utf8")).toBe(readFileSync(path, "utf8"));
    }
  }

  const sourceAgents = join(REPO_ROOT, "agents");
  const installedAgents = join(home, "agents");
  const agentNames = readdirSync(sourceAgents).filter((name) => name.endsWith(".md")).sort();
  expect(existsSync(installedAgents)).toBe(true);
  expect(readdirSync(installedAgents).filter((name) => name.endsWith(".md")).sort()).toEqual(agentNames);
  for (const name of agentNames) {
    expect(readFileSync(join(installedAgents, name), "utf8")).toBe(readFileSync(join(sourceAgents, name), "utf8"));
  }
}

describe("init · the [canon].packs probe the no-pack assertions rely on", () => {
  const surfaces = '[surfaces]\nenabled = ["claude-code"]\n';
  for (const { layout, config } of [
    { layout: "standard table", config: `${surfaces}\n[canon]\npacks = ["triage", "review"]\n` },
    { layout: "standard table with spacing and a comment", config: `${surfaces}\n[canon]   # legacy\n  packs   =   [ "triage" , "review" ]  # chosen\n` },
    { layout: "inline table", config: `canon = { packs = ["triage", "review"] }\n${surfaces}` },
    { layout: "dotted key", config: `canon.packs = ["triage", "review"]\n${surfaces}` },
    { layout: "quoted dotted key", config: `"canon"."packs" = ["triage", "review"]\n${surfaces}` },
    { layout: "multiline array", config: `${surfaces}\n[canon]\npacks = [\n  "triage", # first\n  "review",\n]\n` },
    { layout: "CRLF line endings", config: `${surfaces}\n[canon]\npacks = ["triage", "review"]\n`.replaceAll("\n", "\r\n") },
  ]) {
    test(`detects [canon].packs in the ${layout} layout`, () => {
      expect(canonPacks(config)).toEqual(["triage", "review"]);
    });
  }

  test("detects an explicitly empty or non-array packs value, and reports only a truly absent key as null", () => {
    expect(canonPacks(`${surfaces}\n[canon]\npacks = []\n`)).toEqual([]);
    expect(canonPacks(`${surfaces}\n[canon]\npacks = "all"\n`)).toEqual(["all"]);
    expect(canonPacks(surfaces)).toBeNull();
    expect(canonPacks(`${surfaces}\n[canon]\n# packs = ["triage"]\n`)).toBeNull();
    expect(canonPacks(`${surfaces}\n[other]\npacks = ["triage"]\n`)).toBeNull();
  });
});

describe("init · the plan seams (src/commands/init-shared.ts)", () => {
  test("detectCommands reads the target tree", () => {
    const dir = mkdtempSync(join(tmpdir(), "ai-eng-py-"));
    try {
      writeFileSync(join(dir, "pyproject.toml"), "[project]\nname = \"sample\"\n");
      const line = detectCommands(dir);
      expect(line).toContain("pytest");
      expect(line).not.toContain("oxlint");
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  test("repoTemplateRoot is this checkout, and detectCommands names its commands", () => {
    const root = repoTemplateRoot();
    expect(root).toBe(resolve(root));
    expect(existsSync(join(root, "package.json"))).toBe(true);
    expect(detectCommands()).toBe("typecheck: tsc --noEmit · lint: oxlint · test: bun test · arch: bun test arch.spec.ts");
  });

  test("refuseLine names the reason and what the refusal costs", () => {
    const line = (reason: string) => refuseLine({ path: ".cursor/hooks.json", reason });
    expect(line("not-json")).toContain("not valid JSON");
    expect(line("reformat")).toContain("laid out in a style this installer would have to reformat");
    expect(line("not-object")).toContain("not a JSON object");
    for (const reason of ["not-json", "reformat", "not-object"]) {
      expect(line(reason)).toContain("⚠ .cursor/hooks.json — ");
      expect(line(reason)).toContain("left exactly as it is");
      expect(line(reason)).toContain("runs without guards");
    }
  });

  test("gitHookEntries lands the three marker-managed shims in .git/hooks", () => {
    const entries = gitHookEntries();
    expect(entries.map((e) => e.path)).toEqual([".git/hooks/pre-commit", ".git/hooks/commit-msg", ".git/hooks/pre-push"]);
    for (const entry of entries) expect(entry.ours).toContain("ai-eng");
  });

  test("planEntries installs the floor and only the carriers read from the checkout", () => {
    const entries = planEntries(["claude-code", "cursor"]);
    const paths = entries.map((e) => e.path);
    expect(paths).toContain(".ai-engineering/overrides.toml");
    expect(paths).toContain(".ai-engineering/arch.rules.json");
    expect(paths).toContain(".ai-engineering/config.toml");
    expect(paths).toContain(".github/workflows/ai-eng-check.yml");
    expect(paths).toContain(".git/hooks/pre-commit");
    expect(paths).toContain(".cursor/hooks.json"); // repo-scoped carrier
    expect(paths).not.toContain(".claude/settings.json"); // machine-scoped: installMachineCarriers owns it
    expect(paths).not.toContain("AGENTS.md"); // contractEntries owns the contract, once

    const config = entries.find((e) => e.path === ".ai-engineering/config.toml");
    expect(config?.ours).toContain('enabled = ["claude-code", "cursor"]');
    // A settings file the user may already own goes in by marker, never whole.
    expect(entries.find((e) => e.path === ".cursor/hooks.json")?.merge).toBe(true);
    // A surface with nothing to enforce in the checkout adds no files at all.
    expect(planEntries(["zed"]).map((e) => e.path)).toEqual(paths.filter((p) => p !== ".cursor/hooks.json"));
  });

  test("surfaceOptions offers only surfaces with an adapter behind them", () => {
    const options = surfaceOptions();
    const ids = options.map((s) => s.id);
    expect([...ids].sort()).toEqual(["claude-code", "codex", "copilot-cli", "cursor", "oh-my-pi", "opencode", "pi"]);
    expect(ids).not.toContain("zed"); // declared, but nothing generates for it
    for (const surface of options) expect(hasAdapter(surface.id)).toBe(true);
    expect(hasAdapter("zed")).toBe(false);
    expect(hasAdapter("nothing-by-that-name")).toBe(false);
  });

  test("contractEntries renders the contract files and leaves no placeholder behind", () => {
    const entries = contractEntries("2026-01-02");
    expect(entries.map((e) => e.path)).toEqual(["AGENTS.md", "DECISIONS.md", ".gitignore"]);
    const agents = entries[0]?.ours ?? "";
    expect(agents).toContain(`governed by {ai} Engineering (${VERSION})`);
    expect(agents).toContain("typecheck: tsc --noEmit");
    expect(agents).not.toContain("{{");
    const decisions = entries[1]?.ours ?? "";
    expect(decisions).toContain("Date: 2026-01-02");
    expect(decisions).toContain(VERSION);
    expect(decisions).not.toContain("{{");
    // The runtime state the chain creates must not dirty the user's git status (§08).
    const gitignore = entries[2]?.ours ?? "";
    expect(gitignore).toContain(".DS_Store");
    expect(gitignore).toContain(".ai-engineering/receipts/");
    expect(gitignore).toContain(".ai-engineering/cache/");
    // Never ignore what ai-eng installs INTO the checkout.
    expect(gitignore).not.toContain(".github/");
    expect(gitignore).not.toContain(".cursor/");
  });
});

describe("init · surfaceHint states the row's own delta", () => {
  test("a surface hint describes only its own capabilities", () => {
    expect(surfaceHint(byId("claude-code"))).toContain("can't rewrite output");
  });

  test("each deny class is named in the row's own words", () => {
    expect(surfaceHint(byId("opencode"))).toContain("blocks by throwing");
    expect(surfaceHint(byId("zed"))).toContain("the host denies through its own permissions; no hook for us to run");
    const cannotBlock = { ...byId("claude-code"), can: { ...byId("claude-code").can, deny: false, rewriteOut: true }, note: undefined } as unknown as Surface;
    expect(surfaceHint(cannotBlock)).toBe("can't block tool calls");
  });

  test("a rewrite that is absent, wholesale or total is stated", () => {
    expect(surfaceHint(byId("zed"))).toContain("can't rewrite output");
    expect(surfaceHint(byId("cursor"))).not.toContain("can't rewrite output");
    expect(surfaceHint(byId("codex"))).toContain("rewrites output wholesale");
  });

  test("the row's own note rides with the hint rather than hiding in the header", () => {
    const note = byId("codex").note ?? "";
    expect(note.length).toBeGreaterThan(0);
    expect(surfaceHint(byId("codex"))).toContain(note);
    const hint = surfaceHint(byId("cursor"));
    expect(hint).toContain("research/003");
    expect(hint).toContain("a shell's output is not replaced");
  });
});

describe("init · initMain, phase 1 and phase 2", () => {
  test("--global installs the canon, leaves the repo alone, and a rerun is idempotent", async () => {
    const { cwd, machine: home } = sandboxed();
    const first = await capture(() => initMain({ yes: true, global: true }));
    expect(first.result).toBe(0);
    expect(existsSync(join(home, "skills"))).toBe(true);
    expect(existsSync(join(cwd, "AGENTS.md"))).toBe(false); // --global is the machine side only
    expect(first.out).toContain("global canon (the machine side)");

    // --global is the explicit ask, so a rerun re-installs: the point is that it stays
    // green and leaves the repo alone, not that it skips the work.
    const second = await capture(() => initMain({ yes: true, global: true }));
    expect(second.result).toBe(0);
    expect(existsSync(join(home, "skills"))).toBe(true);
    expect(existsSync(join(cwd, "AGENTS.md"))).toBe(false);
  });

  test("--yes in a bare folder creates the repo and leaves the whole contract for review", async () => {
    const { cwd, machine: home } = sandboxed();
    // OS droppings present before init stay ignored while project files await review.
    mkdirSync(join(cwd, "node_modules", "dep"), { recursive: true });
    writeFileSync(join(cwd, ".DS_Store"), "junk");
    writeFileSync(join(cwd, "node_modules", "dep", "index.js"), "junk");
    const globalConfig = join(home, "isolated-gitconfig");
    const globalConfigBefore = "[user]\n\tname = Isolated test\n";
    writeFileSync(globalConfig, globalConfigBefore);
    const machineSettings = join(home, ".claude", "settings.json");
    const machineSettingsBefore = '{\n  "user": "keep"\n}\n';
    mkdirSync(join(home, ".claude"), { recursive: true });
    writeFileSync(machineSettings, machineSettingsBefore);
    process.env["GIT_CONFIG_GLOBAL"] = globalConfig;
    for (const name of GIT_IDENTITY) process.env[name] = name === "GIT_AUTHOR_EMAIL" || name === "GIT_COMMITTER_EMAIL" ? "test@example.com" : "Test";
    const { result, out } = await capture(() => initMain({ yes: true }));
    expect(result).toBe(0);
    expect(existsSync(join(cwd, ".gitignore"))).toBe(true); // written once, like AGENTS.md
    expect(gitIn(["ls-files"], cwd)).not.toContain(".DS_Store");
    expect(gitIn(["ls-files"], cwd)).not.toContain("node_modules/dep/index.js");
    // The chain's runtime state, dropped after install, stays out of git status too.
    mkdirSync(join(cwd, ".ai-engineering", "receipts"), { recursive: true });
    writeFileSync(join(cwd, ".ai-engineering", "receipts", "r.json"), "{}");
    const status = gitIn(["status", "--porcelain"], cwd);
    expect(status).toContain("?? AGENTS.md");
    expect(status).toContain("?? .ai-engineering/");
    expect(status).not.toContain(".DS_Store");
    expect(status).not.toContain("node_modules");
    expect(status).not.toContain("receipts");

    expect(existsSync(join(cwd, ".git"))).toBe(true); // it created the repo itself (§14.1)
    expect(gitIn(["rev-parse", "--verify", "HEAD"], cwd)).toBe("");
    expect(readFileSync(globalConfig, "utf8")).toBe(globalConfigBefore);
    expect(existsSync(join(cwd, "AGENTS.md"))).toBe(true);
    const decisions = readFileSync(join(cwd, "DECISIONS.md"), "utf8");
    expect(decisions).toContain(`Date: ${new Date().toISOString().slice(0, 10)}`);
    const config = readFileSync(join(cwd, ".ai-engineering", "config.toml"), "utf8");
    expect(config).toContain('enabled = ["claude-code"]');
    expect(canonPacks(config)).toBeNull();
    assertCanon(home);

    // Claude Code reads AGENTS.md natively now — no CLAUDE.md shim is written.
    expect(existsSync(join(cwd, "CLAUDE.md"))).toBe(false);

    // The lock is the ownership ledger: the floor and the carriers, never the contract.
    const lock = parseLock(readFileSync(join(cwd, ".ai-engineering", "ai-eng.lock"), "utf8"));
    expect(lock.version).toBe(VERSION);
    expect(Object.keys(lock.assets)).toContain(".git/hooks/pre-commit");
    expect(Object.keys(lock.assets)).not.toContain("AGENTS.md");

    // git silently ignores a hook that is not executable.
    for (const shim of ["pre-commit", "commit-msg", "pre-push"]) {
      const path = join(cwd, ".git", "hooks", shim);
      expect(statSync(path).mode & 0o111).toBeGreaterThan(0);
      expect(readFileSync(path, "utf8")).toContain("ai-eng");
    }

    expect(out).toContain("~/.claude/settings.json");
    expect(out).toContain("safe machine-settings replacement/removal is unavailable on this platform; left untouched");
    expect(readFileSync(machineSettings, "utf8")).toBe(machineSettingsBefore);
    expect(out).toContain("Bootstrap mode"); // no src/ yet, so arch-tests hold off
  });

  test("init leaves the existing commit alone, spawns no commit, and leaves global config untouched", async () => {
    const { cwd, machine: home } = sandboxed();
    const globalConfig = join(home, "isolated-gitconfig");
    const globalConfigBefore = "[user]\n\tname = Isolated test\n";
    writeFileSync(globalConfig, globalConfigBefore);
    process.env["GIT_CONFIG_GLOBAL"] = globalConfig;

    gitIn(["init", "-q"], cwd);
    gitIn(["config", "user.name", "CP10 test"], cwd);
    gitIn(["config", "user.email", "cp10@example.com"], cwd);
    writeFileSync(join(cwd, "baseline.txt"), "review me\n");
    gitIn(["add", "baseline.txt"], cwd);
    gitIn(["commit", "-qm", "baseline"], cwd);

    const headBefore = gitIn(["rev-parse", "HEAD"], cwd).trim();
    const countBefore = gitIn(["rev-list", "--count", "HEAD"], cwd).trim();
    expect(headBefore).not.toBe("");
    const recorder = recordGitCommands(sandbox!);
    const pathBefore = process.env["PATH"];
    let result: number;
    try {
      process.env["PATH"] = recorder.path;
      result = (await capture(() => initMain({ yes: true }))).result;
    } finally {
      if (pathBefore === undefined) delete process.env["PATH"];
      else process.env["PATH"] = pathBefore;
    }

    const commands = readFileSync(recorder.log, "utf8").trim().split(/\r?\n/).filter(Boolean);
    expect({
      result,
      head: gitIn(["rev-parse", "HEAD"], cwd).trim(),
      commitCount: gitIn(["rev-list", "--count", "HEAD"], cwd).trim(),
      hasUncommittedChanges: gitIn(["status", "--porcelain"], cwd).trim().length > 0,
      spawnedCommit: commands.some((args) => /(^|\s)commit(\s|$)/.test(args)),
      spawnedNoVerify: commands.some((args) => /(^|\s)--no-verify(\s|$)/.test(args)),
      globalConfig: readFileSync(globalConfig, "utf8"),
    }).toEqual({
      result: 0,
      head: headBefore,
      commitCount: countBefore,
      hasUncommittedChanges: true,
      spawnedCommit: false,
      spawnedNoVerify: false,
      globalConfig: globalConfigBefore,
    });
  });

  test("a second --yes run hands off to update and never touches the contract", async () => {
    const { cwd } = sandboxed();
    expect(await initMain({ yes: true })).toBe(0);
    const agents = readFileSync(join(cwd, "AGENTS.md"), "utf8");
    const decisions = readFileSync(join(cwd, "DECISIONS.md"), "utf8");

    const { result, out } = await capture(() => initMain({ yes: true, surface: ["cursor"] }));
    expect(result).toBe(0);
    expect(readFileSync(join(cwd, "AGENTS.md"), "utf8")).toBe(agents);
    expect(readFileSync(join(cwd, "DECISIONS.md"), "utf8")).toBe(decisions);
    expect(out).toMatch(/nothing to sync|nothing written/); // the declared surfaces are already current or patches kept
  });

  test("--yes keeps an AGENTS.md the project already had, byte for byte", async () => {
    const { cwd } = sandboxed();
    const mine = "# my own rules\n\nI decide what agents do here.\n";
    writeFileSync(join(cwd, "AGENTS.md"), mine);
    const { result, out } = await capture(() => initMain({ yes: true }));
    expect(result).toBe(0);
    expect(readFileSync(join(cwd, "AGENTS.md"), "utf8")).toBe(mine);
    expect(out).toContain("yours, untouched");
  });

  test("a first init names an existing AGENTS.md and a decline keeps it", async () => {
    const { cwd } = sandboxed();
    const mine = "# my own rules\n";
    writeFileSync(join(cwd, "AGENTS.md"), mine);
    const { result, out } = await driven({}, [
      ["Create", "y"],
      ["governed", " \n"],
      ["AGENTS.md already exists", "n"],
    ]);
    expect(result).toBe(0);
    expect(readFileSync(join(cwd, "AGENTS.md"), "utf8")).toBe(mine);
    expect(out).toContain("yours, untouched");
  });

  test("answering yes replaces the existing AGENTS.md with the contract file", async () => {
    const { cwd } = sandboxed();
    writeFileSync(join(cwd, "AGENTS.md"), "# my own rules\n");
    const { result, out } = await driven({}, [
      ["Create", "y"],
      ["governed", " \n"],
      ["AGENTS.md already exists", "y"],
    ]);
    expect(result).toBe(0);
    const agents = readFileSync(join(cwd, "AGENTS.md"), "utf8");
    expect(agents).toContain("governed by {ai} Engineering");
    expect(agents).not.toContain("# my own rules");
    expect(out).toContain("replaced the file that was there");
  });

  test("a surface that cannot deny aborts before anything is promised", async () => {
    const { cwd } = sandboxed();
    mkdirSync(join(cwd, ".git"));
    const { result, out } = await capture(() => initMain({ yes: true, surface: ["zed"] }));
    expect(result).toBe(2);
    expect(out).toContain('"zed" cannot deny tools');
    expect(existsSync(join(cwd, "AGENTS.md"))).toBe(false);
    expect(existsSync(join(cwd, ".ai-engineering", "config.toml"))).toBe(false);
  });

  test("a --surface id that nothing declares is refused, and nothing is written", async () => {
    const { cwd } = sandboxed();
    mkdirSync(join(cwd, ".git"));
    const { result, out } = await capture(() => initMain({ yes: true, surface: ["claud-code"] }));

    // The declaration is what the gate reads, so a typo declared there — with no carrier
    // behind it — is a repo governed by nothing. It used to be written at exit 0.
    expect(result).toBe(2);
    expect(out).toContain('"claud-code" is not a surface this release knows');
    expect(existsSync(join(cwd, ".ai-engineering", "config.toml"))).toBe(false);
  });

  test("a repo file the installer cannot merge is left byte-identical and named", async () => {
    const { cwd } = sandboxed();
    mkdirSync(join(cwd, ".git"));
    mkdirSync(join(cwd, ".cursor"), { recursive: true });
    const userFile = "{ hooks: this is mine, not json }\n";
    writeFileSync(join(cwd, ".cursor", "hooks.json"), userFile);

    const { result, out } = await capture(() => initMain({ yes: true, surface: ["cursor"] }));
    expect(result).toBe(0);
    expect(readFileSync(join(cwd, ".cursor", "hooks.json"), "utf8")).toBe(userFile);
    expect(out).toContain("not valid JSON");
    expect(out).toContain("left exactly as it is");
  });

  test("a machine settings file that cannot be merged is named, not overwritten", async () => {
    const { cwd, machine: home } = sandboxed();
    mkdirSync(join(cwd, ".git"));
    mkdirSync(join(home, ".claude"), { recursive: true });
    const userSettings = "{ \"permissions\": torn }\n";
    writeFileSync(join(home, ".claude", "settings.json"), userSettings);

    const { result, out } = await capture(() => initMain({ yes: true, surface: ["claude-code"] }));
    expect(result).toBe(0);
    expect(readFileSync(join(home, ".claude", "settings.json"), "utf8")).toBe(userSettings);
    expect(out).toContain("not valid JSON");
  });

  test("F11: a dangling machine settings link is refused and init still records its lock", async () => {
    const { cwd, machine: home } = sandboxed();
    mkdirSync(join(cwd, ".git"));
    const settings = join(home, ".claude", "settings.json");
    const dotfilesTarget = join(home, "dotfiles", "claude-settings.json");
    mkdirSync(dirname(settings), { recursive: true });
    symlinkSync(dotfilesTarget, settings);

    const { result, out } = await capture(() => initMain({ yes: true, surface: ["claude-code"] }));

    expect(result).toBe(0);
    expect(out).toContain("~/.claude/settings.json — unreadable, a dangling link, not a regular file, or changing while read; left untouched");
    expect(readlinkSync(settings)).toBe(dotfilesTarget);
    expect(existsSync(dotfilesTarget)).toBe(false);
    expect(parseLock(readFileSync(join(cwd, ".ai-engineering", "ai-eng.lock"), "utf8")).version).toBe(VERSION);
  });

  test("closing line names /ai-config-to-project", async () => {
    const { cwd } = sandboxed();
    gitIn(["init", "-q"], cwd);
    const { result, out } = await capture(() => initMain({ yes: true }));
    expect(result).toBe(0);
    expect(out).toContain("/ai-config-to-project");
  });
});

describe("init · the git floor's own housekeeping", () => {
  test("a core.hooksPath we set ourselves is cleaned up, because it is ours", async () => {
    const { cwd } = sandboxed();
    gitIn(["init", "-q"], cwd);
    gitIn(["config", "core.hooksPath", ".ai-engineering/git-template/hooks"], cwd);

    const { result, out } = await capture(() => initMain({ yes: true }));
    expect(result).toBe(0);
    expect(out).toContain("unset — it pointed at ai-eng's own floor");
    // git only reads .git/hooks while the setting is unset, so the floor runs again.
    expect(gitIn(["config", "--get", "core.hooksPath"], cwd).trim()).toBe("");
    expect(statSync(join(cwd, ".git", "hooks", "pre-commit")).mode & 0o111).toBeGreaterThan(0);
  });

  test("a core.hooksPath the user set is named and never deleted", async () => {
    const { cwd } = sandboxed();
    gitIn(["init", "-q"], cwd);
    gitIn(["config", "core.hooksPath", ".husky/_"], cwd);

    const { result, out } = await capture(() => initMain({ yes: true }));
    expect(result).toBe(0);
    expect(gitIn(["config", "--get", "core.hooksPath"], cwd).trim()).toBe(".husky/_");
    expect(out).toContain("core.hooksPath is yours");
  });

});

describe("init · non-interactive default skill installation", () => {
  test("fresh init installs every skill and resource without a pack prompt or config key, and runs none of them", async () => {
    const { cwd, machine: home } = sandboxed();
    const recorder = recordExecutions();
    let run: { result: number; out: string };
    try {
      run = await capture(() => initMain({ yes: true }));
    } finally {
      recorder.restore();
    }

    expect(run.result).toBe(0);
    expect(run.out).not.toMatch(/(?:which|select|choose)[^\n]*packs?/i);
    const config = readFileSync(join(cwd, ".ai-engineering", "config.toml"), "utf8");
    expect(canonPacks(config)).toBeNull();
    assertCanon(home);
    // The recorder sees what init really starts: it created the repo with git itself.
    expect(recorder.executions.some((execution) => basename(execution.command) === "git" && execution.args.includes("init"))).toBe(true);
    assertExecutedNothingFrom(home, recorder.executions);
  });

  test("init --global installs the complete canon, runs none of it, and leaves an existing machine hook file alone", async () => {
    const { machine: home } = sandboxed();
    const settings = join(home, ".claude", "settings.json");
    const settingsBefore = '{\n  "user": "keep"\n}\n';
    mkdirSync(dirname(settings), { recursive: true });
    writeFileSync(settings, settingsBefore);
    const recorder = recordExecutions();
    let run: { result: number; out: string };
    try {
      run = await capture(() => initMain({ yes: true, global: true }));
    } finally {
      recorder.restore();
    }

    expect(run.result).toBe(0);
    expect(run.out).not.toMatch(/(?:which|select|choose)[^\n]*packs?/i);
    assertCanon(home);
    expect(readFileSync(settings, "utf8")).toBe(settingsBefore);
    assertExecutedNothingFrom(home, recorder.executions);
  });

  test("declining the canon offer installs nothing at all", async () => {
    const { cwd, machine: home } = sandboxed();
    mkdirSync(join(cwd, ".git"));
    const { result, out } = await driven({}, [["install", "n"]]);
    expect(result).toBe(0);
    expect(existsSync(join(home, "skills"))).toBe(false);
    expect(existsSync(join(cwd, "AGENTS.md"))).toBe(false);
    expect(out).toContain("Nothing installed");
  });

  test("declining git init ends the verb with the folder untouched", async () => {
    const { cwd } = sandboxed();
    const { result, out } = await driven({}, [["Create", "n"]]);
    expect(result).toBe(0);
    expect(existsSync(join(cwd, ".git"))).toBe(false);
    expect(existsSync(join(cwd, "AGENTS.md"))).toBe(false);
    expect(out).toContain("Inside a repo, ai-eng init governs it too");
  });

  test("a bare folder answered yes creates the repo, takes the surface the human picks, and asks nothing about packs", async () => {
    const { cwd, machine: home } = sandboxed();
    // Only the repo and surface questions are answered: any further prompt leaves init waiting.
    const { result, out } = await driven({}, [
      ["Create", "y"],
      ["governed", " \n"],
    ]);
    expect(result).toBe(0);
    expect(out).not.toMatch(/packs?\b/i);
    assertCanon(home);
    expect(existsSync(join(cwd, ".git"))).toBe(true);
    const config = readFileSync(join(cwd, ".ai-engineering", "config.toml"), "utf8");
    expect(config).toContain('enabled = ["claude-code"]');
    expect(canonPacks(config)).toBeNull();
  });

  test("detected surfaces are ticked by default, and the machine writes can be declined", async () => {
    const { cwd, machine: home } = sandboxed();
    await initMain({ yes: true, global: true }); // a machine that already has the canon: no canon question
    for (const marker of [".claude", ".cursor", ".opencode", join(".agents", "hooks")]) mkdirSync(join(cwd, marker), { recursive: true });
    gitIn(["init", "-q"], cwd);

    const { result, out } = await driven({}, [
      ["governed", "\n"],
      ["carriers", "n"],
    ]);
    expect(result).toBe(0);
    expect(out).toContain("global canon intact"); // a healthy machine is never re-written without a question

    const config = readFileSync(join(cwd, ".ai-engineering", "config.toml"), "utf8");
    const enabled = JSON.parse(`[${/enabled = \[(.*)\]/.exec(config)?.[1] ?? ""}]`) as string[];
    expect(new Set(enabled)).toEqual(new Set(["claude-code", "oh-my-pi", "opencode", "cursor"]));
    // Cursor reads its carrier from the checkout, so that one is installed whatever the answer.
    expect(readFileSync(join(cwd, ".cursor", "hooks.json"), "utf8")).toContain("ai-eng chain");
    // The three whose readers live in the home are exactly what "n" refused.
    expect(existsSync(join(home, ".claude", "settings.json"))).toBe(false);
    expect(existsSync(join(home, ".omp", "agent", "hooks", "pre", "ai-eng.ts"))).toBe(false);
    expect(existsSync(join(home, ".config", "opencode", "plugins", "ai-eng.ts"))).toBe(false);
    expect(existsSync(join(home, "gitconfig"))).toBe(false); // init does not write global Git config
    expect(out).toContain("machine carriers not written");
    expect(out).toContain("4 surfaces");
  });

  test("an already-governed repo: choosing Exit changes nothing", async () => {
    const { cwd } = sandboxed();
    expect(await initMain({ yes: true })).toBe(0);
    const agents = readFileSync(join(cwd, "AGENTS.md"), "utf8");
    const config = readFileSync(join(cwd, ".ai-engineering", "config.toml"), "utf8");

    // Two downs land on "Exit — change nothing"; the select starts on "update".
    const { result, out } = await driven({}, [["governed", "\x1b[B\x1b[B\n"]]);
    expect(result).toBe(0);
    expect(out).toContain("Nothing changed.");
    expect(readFileSync(join(cwd, "AGENTS.md"), "utf8")).toBe(agents);
    expect(readFileSync(join(cwd, ".ai-engineering", "config.toml"), "utf8")).toBe(config);
  });

  test("cancelling the surface picker installs nothing", async () => {
    const { cwd } = sandboxed();
    await initMain({ yes: true, global: true }); // a healthy machine: straight to the picker
    mkdirSync(join(cwd, ".git"));
    const { result, out } = await driven({}, [["governed", "\x03"]]); // ctrl-c on the multiselect
    expect(result).toBe(0);
    expect(out).toContain("Cancelled");
    expect(existsSync(join(cwd, "AGENTS.md"))).toBe(false);
    expect(existsSync(join(cwd, ".ai-engineering"))).toBe(false);
  });

  test("git init failing is a hard stop, not a silent half-install", async () => {
    const { cwd } = sandboxed();
    chmodSync(cwd, 0o555);
    try {
      const { result, out } = await capture(() => initMain({ yes: true }));
      expect(result).toBe(2);
      expect(out).toContain("git init failed");
      expect(existsSync(join(cwd, ".ai-engineering"))).toBe(false);
    } finally {
      chmodSync(cwd, 0o755);
    }
  });
});
