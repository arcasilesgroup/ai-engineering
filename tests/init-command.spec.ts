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

import { describe, test, expect, afterEach, afterAll } from "bun:test";
import { spawnSync } from "node:child_process";
import {
  chmodSync,
  existsSync,
  lstatSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  readlinkSync,
  rmSync,
  statSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
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

const cwdBefore = process.cwd();
const GIT_IDENTITY = ["GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL"] as const;

process.env["NO_COLOR"] = "1";
process.env["CI"] = "1";
process.env["AI_ENG_NO_UPDATE_NOTICES"] = "1";

let sandbox: string | undefined;

/** A repo-shaped sandbox of its own and a machine of its own. Nothing outside it is
 *  written: AI_ENG_HOME redirects the canon and the carrier base, and template.ts puts
 *  the global git config under the same override. */
function sandboxed(): { cwd: string; machine: string } {
  sandbox = mkdtempSync(join(tmpdir(), "ai-eng-init-"));
  const cwd = join(sandbox, "project");
  const machine = join(sandbox, "machine");
  mkdirSync(cwd, { recursive: true });
  mkdirSync(machine, { recursive: true });
  process.env["AI_ENG_HOME"] = machine;
  process.env["PI_CODING_AGENT_DIR"] = join(machine, "pi-agent");
  process.chdir(cwd);
  return { cwd, machine };
}

function gitIn(args: string[], cwd: string, env: Record<string, string> = {}): string {
  const r = spawnSync("git", args, { cwd, encoding: "utf8", env: { ...process.env, ...env } });
  return r.stdout ?? "";
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
  delete process.env["AI_ENG_HOME"];
  delete process.env["PI_CODING_AGENT_DIR"];
  delete process.env["GIT_CONFIG_GLOBAL"];
  for (const name of GIT_IDENTITY) delete process.env[name];
  // scriptedInput attaches one data listener per call; a suite that runs the verb a
  // dozen times would otherwise cross Node's cap of 10 and print a leak warning.
  process.stdin.removeAllListeners("data");
  if (sandbox) rmSync(sandbox, { recursive: true, force: true });
  sandbox = undefined;
});

afterAll(() => {
  process.stdin.pause(); // a flowing stdin keeps the process alive past the last test
});

const byId = (id: string): Surface => {
  const found = SURFACES.find((s) => s.id === id);
  if (!found) throw new Error(`surface ${id} is not declared in surfaces.json`);
  return found;
};

describe("init · the plan seams (src/commands/init-shared.ts)", () => {
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

  test("surfaceOptions offers only surfaces with an adapter behind them, grouped by tier", () => {
    const groups = surfaceOptions();
    expect(groups.length).toBeGreaterThan(0);
    for (const group of groups) expect(group.items.length).toBeGreaterThan(0);
    const ids = groups.flatMap((g) => g.items.map((s) => s.id));
    expect([...ids].sort()).toEqual(["claude-code", "codex", "copilot", "cursor", "oh-my-pi", "opencode", "pi"]);
    expect(ids).not.toContain("zed"); // declared, but nothing generates for it
    for (const group of groups) for (const surface of group.items) expect(hasAdapter(surface.id)).toBe(true);
    expect(hasAdapter("zed")).toBe(false);
    expect(hasAdapter("nothing-by-that-name")).toBe(false);
  });

  test("contractEntries renders both contract files and leaves no placeholder behind", () => {
    const entries = contractEntries("2026-01-02");
    expect(entries.map((e) => e.path)).toEqual(["AGENTS.md", "DECISIONS.md"]);
    const agents = entries[0]?.ours ?? "";
    expect(agents).toContain(`governed by {ai} Engineering (${VERSION})`);
    expect(agents).toContain("typecheck: tsc --noEmit");
    expect(agents).not.toContain("{{");
    const decisions = entries[1]?.ours ?? "";
    expect(decisions).toContain("(2026-01-02)");
    expect(decisions).toContain(VERSION);
    expect(decisions).not.toContain("{{");
  });
});

describe("init · surfaceHint states the row's delta, not the group's promise", () => {
  test("a core surface with full guards adds nothing to the header", () => {
    expect(surfaceHint(byId("claude-code"))).toBe("");
  });

  test("each deny class is named in the row's own words", () => {
    expect(surfaceHint(byId("opencode"))).toContain("blocks by throwing");
    expect(surfaceHint(byId("zed"))).toContain("the host denies through its own permissions; no hook for us to run");
    const cannotBlock = { ...byId("claude-code"), can: { ...byId("claude-code").can, deny: false }, note: undefined } as unknown as Surface;
    expect(surfaceHint(cannotBlock)).toBe("can't block tool calls");
  });

  test("a rewrite that is absent, wholesale or total is stated", () => {
    expect(surfaceHint(byId("cursor"))).toContain("can't rewrite output");
    expect(surfaceHint(byId("codex"))).toContain("rewrites output wholesale");
  });

  test("the row's own note rides with the hint rather than hiding in the header", () => {
    const note = byId("codex").note ?? "";
    expect(note.length).toBeGreaterThan(0);
    expect(surfaceHint(byId("codex"))).toContain(note);
    const hint = surfaceHint(byId("cursor"));
    expect(hint.split(" · ").length).toBeGreaterThan(1);
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

  test("--yes in a bare folder creates the repo and scaffolds the whole contract", async () => {
    const { cwd, machine: home } = sandboxed();
    for (const name of GIT_IDENTITY) process.env[name] = name === "GIT_AUTHOR_EMAIL" || name === "GIT_COMMITTER_EMAIL" ? "test@example.com" : "Test";
    const { result, out } = await capture(() => initMain({ yes: true }));
    expect(result).toBe(0);

    expect(existsSync(join(cwd, ".git"))).toBe(true); // it created the repo itself (§14.1)
    expect(existsSync(join(cwd, "AGENTS.md"))).toBe(true);
    const decisions = readFileSync(join(cwd, "DECISIONS.md"), "utf8");
    expect(decisions).toContain(`(${new Date().toISOString().slice(0, 10)})`);
    const config = readFileSync(join(cwd, ".ai-engineering", "config.toml"), "utf8");
    expect(config).toContain('enabled = ["claude-code"]');

    // CLAUDE.md is a symlink where the OS allows one, an import line where it does not.
    const claude = join(cwd, "CLAUDE.md");
    if (lstatSync(claude).isSymbolicLink()) expect(readlinkSync(claude)).toBe("AGENTS.md");
    else expect(readFileSync(claude, "utf8")).toBe("@AGENTS.md\n");

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

    // The machine carrier and the git floor's second life, both under the sandbox home.
    expect(readFileSync(join(home, ".claude", "settings.json"), "utf8")).toContain("ai-eng chain");
    const templateDir = gitIn(["config", "--get", "init.templateDir"], cwd, { GIT_CONFIG_GLOBAL: join(home, "gitconfig") }).trim();
    expect(templateDir).toBe(join(home, "git-template"));
    expect(existsSync(join(templateDir, "hooks", "pre-commit"))).toBe(true);

    expect(gitIn(["log", "--oneline", "-1"], cwd)).toContain(`install governance ${VERSION}`);
    expect(out).toContain("machine carrier");
    expect(out).toContain("Bootstrap mode"); // no src/ yet, so arch-tests hold off
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
    expect(out).toContain("nothing to sync"); // the declared surfaces are already current
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

  test("git refusing the template dir is reported, not claimed", async () => {
    const { cwd, machine: home } = sandboxed();
    mkdirSync(join(cwd, ".git"));
    process.env["GIT_CONFIG_GLOBAL"] = join(home, "no-such-dir", "gitconfig"); // git cannot write here

    const { result, out } = await capture(() => initMain({ yes: true }));
    expect(result).toBe(0);
    expect(out).toContain("git init.templateDir not set");
    expect(existsSync(join(cwd, "AGENTS.md"))).toBe(true); // the repo install still happened
  });
});

describe("init · the prompt paths a non-TTY --yes run never reaches", () => {
  test("declining the canon offer installs nothing at all", async () => {
    const { cwd, machine: home } = sandboxed();
    mkdirSync(join(cwd, ".git"));
    const { result, out } = await driven({}, [["install it now", "n"]]);
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

  test("a bare folder answered yes creates the repo and takes the surface the human picks", async () => {
    const { cwd, machine: home } = sandboxed();
    const { result } = await driven({}, [
      ["Create", "y"],
      ["governed", " \n"],
    ]);
    expect(result).toBe(0);
    expect(existsSync(join(home, "skills"))).toBe(true);
    expect(existsSync(join(cwd, ".git"))).toBe(true);
    expect(readFileSync(join(cwd, ".ai-engineering", "config.toml"), "utf8")).toContain('enabled = ["claude-code"]');
  });

  test("detected surfaces are ticked by default, and the machine writes can be declined", async () => {
    const { cwd, machine: home } = sandboxed();
    await initMain({ yes: true, global: true }); // a machine that already has the canon: no canon question
    for (const marker of [".claude", ".cursor", ".opencode", join(".agents", "hooks")]) mkdirSync(join(cwd, marker), { recursive: true });
    gitIn(["init", "-q"], cwd);

    const { result, out } = await driven({}, [
      ["governed", "\n"],
      ["carriers", "n"],
      ["templateDir", "n"],
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
    expect(existsSync(join(home, "gitconfig"))).toBe(false); // the floor's templateDir was refused too
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
