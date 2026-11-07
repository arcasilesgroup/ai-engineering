// `ai-eng doctor` is twelve checks and one real test, and every check is a state
// machine whose branches are different worlds. Each test builds the world its branch
// needs, runs the real doctorMain against it, and asserts what a caller can observe:
// the number it returns and the rows it prints. Nothing here reaches inside a check —
// the row text IS the contract (§14.2).
//
// Every sandbox is a mkdtemp(): AI_ENG_HOME points into one, the repo into another,
// and neither is ever the developer's real home.

import { afterEach, describe, expect, spyOn, test } from "bun:test";
import { spawnSync } from "node:child_process";
import { chmodSync, existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, symlinkSync, utimesSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { delimiter, join } from "node:path";
import { doctorMain } from "../src/commands/doctor.ts";
import { canonSkills } from "../src/embed.ts";
import { lockText, sha256 } from "../src/install.ts";
import * as receiptsModule from "../src/receipts.ts";
import { carrierFiles, carrierPath, installCanon, machineCarrier, SURFACES } from "../src/surfaces/adapters.ts";
import * as uiModule from "../src/ui.ts";
import { VERSION } from "../src/version.ts";
import { writeFakeCommand } from "./fixtures/fake-command.ts";
import { restoreSandboxEnv, snapshotSandboxEnv } from "./fixtures/sandbox-env.ts";

const GOVERNED = '[surfaces]\nenabled = ["claude-code"]\n';
const ORIGINAL = { cwd: process.cwd(), path: process.env.PATH ?? "", sandbox: snapshotSandboxEnv() };
const temps: string[] = [];

function tempDir(prefix: string): string {
  const dir = mkdtempSync(join(tmpdir(), prefix));
  temps.push(dir);
  return dir;
}

afterEach(() => {
  process.chdir(ORIGINAL.cwd);
  restoreSandboxEnv(ORIGINAL.sandbox);
  process.env.PATH = ORIGINAL.path;
  for (const dir of temps.splice(0)) rmSync(dir, { recursive: true, force: true });
});

type Run = { code: number; out: string };

/** doctorMain writes through clack, which writes to process.stdout — so both the
 *  stream and console.log are captured, and the ANSI a real terminal would show is
 *  stripped: the assertion is about the words, not the paint. */
async function doctor(flags: { gc?: boolean; cwd?: string } = {}): Promise<Run> {
  const chunks: string[] = [];
  const stdout = spyOn(process.stdout, "write").mockImplementation(((chunk: unknown) => {
    chunks.push(String(chunk));
    return true;
  }) as never);
  const log = spyOn(console, "log").mockImplementation(((...args: unknown[]) => {
    chunks.push(`${args.map(String).join(" ")}\n`);
  }) as never);
  try {
    const code = await doctorMain(flags);
    return { code, out: chunks.join("").replace(/\u001b\[[0-9;]*[A-Za-z]/g, "") };
  } finally {
    stdout.mockRestore();
    log.mockRestore();
  }
}

/** The whole printed line for one check — mark included. */
function row(run: Run, name: string): string {
  return run.out.split("\n").find((line) => line.includes(`${name} ·`)) ?? `(no row for ${name})`;
}

/** Everything the check said, with the name and the mark taken off. */
function detail(run: Run, name: string): string {
  const line = row(run, name);
  const at = line.indexOf(`${name} · `);
  return at === -1 ? line : line.slice(at + name.length + 3);
}

/** A sandbox repository: a checkout directory and a machine home, both temp. The
 *  caller adds what the branch under test needs and nothing else, so an ok row can
 *  only come from what the test wrote. */
function sandbox(config: string | null = GOVERNED): { home: string; root: string } {
  const home = tempDir("ai-eng-doc-home-");
  const root = tempDir("ai-eng-doc-repo-");
  process.env.AI_ENG_HOME = home;
  mkdirSync(join(root, ".git", "hooks"), { recursive: true });
  if (config !== null) {
    mkdirSync(join(root, ".ai-engineering"), { recursive: true });
    writeFileSync(join(root, ".ai-engineering", "config.toml"), config);
  }
  process.chdir(root);
  return { home, root };
}

/** `rules` rule-bearing lines followed by filler, so the ceiling and the rule count
 *  can be moved independently. */
const agentsMd = (rules: number, lines: number): string =>
  Array.from({ length: lines }, (_, index) => (index < rules ? `${index + 1}. rule ${index + 1}` : `prose line ${index}`)).join("\n");

const FLOOR_HOOKS = ["pre-commit", "commit-msg", "pre-push"];

function writeFloor(root: string): void {
  for (const name of FLOOR_HOOKS) writeFileSync(join(root, ".git", "hooks", name), "#!/bin/sh\n# ai-eng git floor shim\n");
}

/** A `gitleaks` the test owns, so the check never depends on the machine. */
function gitleaks(status: number): void {
  const dir = tempDir("ai-eng-doc-bin-");
  writeFakeCommand(dir, "gitleaks", { exitCode: status });
  process.env.PATH = `${dir}${delimiter}${ORIGINAL.path}`;
}

function receipt(latency: number, outcome: "allow" | "deny", event = "PreToolUse"): string {
  return JSON.stringify({
    schema: "urn:ai-eng:receipt:2",
    operation_id: "abcdef12",
    event,
    surface: "claude-code",
    tool: "Bash",
    guards: { ran: [], denied_by: null },
    latency_ms: latency,
    outcome,
    ts: "2026-09-14T00:00:00.000Z",
  });
}

/** Write the machine carrier this binary ships for claude-code, where the host reads it. */
function shipClaudeCarrier(_home: string): void {
  const placement = machineCarrier(SURFACES.find((surface) => surface.id === "claude-code")!)!;
  const target = carrierPath(placement);
  mkdirSync(join(target, ".."), { recursive: true });
  writeFileSync(target, carrierFiles("claude-code")!.main);
}

/** A repo where every check the caller did not deliberately break is green: the
 *  contract installed, the canon materialized, the floor wired, the carrier shipped. */
function healthy(config = GOVERNED): { home: string } {
  const box = sandbox(config);
  writeFileSync(join(box.root, "AGENTS.md"), agentsMd(6, 20));
  writeFloor(box.root);
  gitleaks(0);
  installCanon(VERSION);
  writeFileSync(join(box.root, ".ai-engineering", "ai-eng.lock"), lockText({ version: VERSION, assets: {} }));
  mkdirSync(join(box.root, "src"));
  writeFileSync(join(box.root, ".ai-engineering", "arch.rules.json"), "{}");
  shipClaudeCarrier(box.home);
  return box;
}

function commit(root: string, message: string, env: Record<string, string> = {}): void {
  const options = { encoding: "utf8" as const, env: { ...process.env, ...env } };
  const add = spawnSync("git", ["-C", root, "add", "-A"], options);
  if (add.status !== 0) throw new Error(`git add failed: ${add.stderr}`);
  const made = spawnSync(
    "git",
    ["-C", root, "-c", "user.email=doctor@test", "-c", "user.name=doctor", "-c", "commit.gpgsign=false", "commit", "-m", message, "--no-verify"],
    options,
  );
  if (made.status !== 0) throw new Error(`git commit failed: ${made.stderr}`);
}

function gitInit(root: string): string {
  const init = spawnSync("git", ["-C", root, "init", "-q"], { encoding: "utf8" });
  if (init.status !== 0) throw new Error(`git init failed: ${init.stderr}`);
  const head = spawnSync("git", ["-C", root, "rev-parse", "HEAD"], { encoding: "utf8" });
  return head.stdout.trim();
}

describe("doctor · a repo where everything is green", () => {
  test("reports chain, canon, carriers and receipts without retired reports", async () => {
    healthy();
    const run = await doctor();
    expect(run.code).toBe(0);
    expect(run.out).toContain("Health check ·");
    expect(run.out).toContain(`ai-eng ${VERSION}`);
    expect(run.out).toContain("Checks passed");
    expect(run.out).not.toContain("FAIL — the chain is broken here");
    expect(run.out).toContain("Chain verified. Next: keep working.");
    expect(detail(run, "AGENTS.md")).toBe("6 rules · 20 lines");
    expect(detail(run, "config.toml")).toBe("governed · surfaces: claude-code");
    expect(detail(run, "mirrors")).toBe("3/3 mirrors carry linked skills");
    expect(detail(run, "canon")).toMatch(/^\d+\/\d+ files verified · 0 drift · 0 missing$/);
    expect(detail(run, "assets")).toBe(`installed by ${VERSION}`);
    expect(detail(run, "git floor")).toBe("marker hooks in .git/hooks/ · gitleaks present");
    expect(detail(run, "chain test")).toMatch(/^adversarial payload \(git commit -n\) → DENY in \d+ms$/);
    expect(detail(run, "receipts")).toMatch(/^last 14d: \d+ runs · \d+ denies · p50 \d+ms · p95 \d+ms \(ceiling 50\)( · top [^ ]+)?$/);
    expect(detail(run, "overrides")).toBe("none active");
    expect(detail(run, "arch")).toBe("active — src/ present");
    expect(detail(run, "surface claude-code")).toBe("machine carrier ~/.claude/settings.json carries the ai-eng entries");
    expect(detail(run, "behaviors")).toBe("no behaviors declared");
    expect(run.out).not.toContain("checkpoint gate");
    expect(run.out).not.toContain("checkpoint-gate-report");
    expect(run.out).not.toContain("plant-workflow");
  });

  test("a warn is not a failure: warnings alone return 0 under an Attention block", async () => {
    const { home, root } = sandbox();
    writeFileSync(join(root, "AGENTS.md"), agentsMd(6, 20));
    writeFloor(root);
    gitleaks(0);
    shipClaudeCarrier(home);
    const run = await doctor();
    expect(run.code).toBe(0);
    expect(run.out).toContain("Attention");
    expect(run.out).not.toContain("FAIL — the chain is broken here");
    expect(row(run, "mirrors")).toContain("▲");
    expect(detail(run, "mirrors")).toBe("3/3 mirrors empty or missing → ai-eng init --global");
    expect(detail(run, "canon")).toContain("files verified · 0 drift");
    expect(detail(run, "canon")).toContain("missing");
  });

  test("a mirror whose links dangle is broken: the canon the links point at is gone", async () => {
    const { home } = healthy();
    rmSync(join(home, "skills"), { recursive: true, force: true });
    const run = await doctor();
    expect(row(run, "mirrors")).toContain("▲");
    expect(detail(run, "mirrors")).toBe("3/3 mirrors empty or missing → ai-eng init --global");
    expect(detail(run, "canon")).toContain("missing");
  });
});

describe("doctor · AGENTS.md", () => {
  test("no AGENTS.md is a FAIL, and the frame says the chain is broken", async () => {
    sandbox();
    const run = await doctor();
    expect(run.code).toBe(2);
    expect(row(run, "AGENTS.md")).toContain("✗");
    expect(detail(run, "AGENTS.md")).toBe("missing — the contract was never installed");
    expect(run.out).toContain("FAIL — the chain is broken here");
    expect(run.out).toContain("FAIL present — fix before trusting the chain.");
  });

  test("an AGENTS.md inside the ceiling with enough rules is ok; too many lines warns", async () => {
    const { root } = sandbox();
    const contract = join(root, "AGENTS.md");
    writeFileSync(contract, agentsMd(6, 20));
    let run = await doctor();
    expect(row(run, "AGENTS.md")).toContain("✓");
    expect(detail(run, "AGENTS.md")).toBe("6 rules · 20 lines");

    writeFileSync(contract, agentsMd(6, 125));
    run = await doctor();
    expect(row(run, "AGENTS.md")).toContain("▲");
    expect(detail(run, "AGENTS.md")).toBe("6 rules · 125 lines (over the context ceiling)");

    writeFileSync(contract, agentsMd(3, 40));
    run = await doctor();
    expect(row(run, "AGENTS.md")).toContain("▲");
    expect(detail(run, "AGENTS.md")).toBe("3 rules · 40 lines");
  });
});

describe("doctor · config.toml is the gate", () => {
  test("absent, unparseable and declaration-less are three different FAILs", async () => {
    sandbox(null);
    let run = await doctor();
    expect(row(run, "config.toml")).toContain("✗");
    expect(detail(run, "config.toml")).toBe("absent — the gate reads this file; without it this repo is not governed");
    expect(detail(run, "chain test")).toBe("not governed (no-config) — the chain applies no policy here, so an allow is the gate working");
    expect(detail(run, "receipts")).toContain("last 14d: 0 runs · 0 denies");
    expect(run.code).toBe(2);

    sandbox("this is not = toml = at all\n");
    run = await doctor();
    expect(row(run, "config.toml")).toContain("✗");
    expect(detail(run, "config.toml")).toBe("unparseable — the chain treats this repo as ungoverned; fix the TOML or re-run ai-eng init");
    expect(detail(run, "chain test")).toContain("not governed (corrupt-config)");

    sandbox('[gc]\nmax_files = 25\n');
    run = await doctor();
    expect(row(run, "config.toml")).toContain("✗");
    expect(detail(run, "config.toml")).toBe("no [surfaces] enabled list — the gate needs the declaration, not just the file");
  });

  test("with no repository above the directory, doctor says exactly that", async () => {
    process.env.AI_ENG_HOME = tempDir("ai-eng-doc-home-");
    process.chdir(tempDir("ai-eng-doc-bare-"));
    const run = await doctor();
    expect(detail(run, "config.toml")).toBe("no repository above this directory");
    expect(detail(run, "arch")).toBe("no arch.rules.json — nothing enforces the layer rules");
    expect(detail(run, "chain test")).toContain("not governed (no-repo)");
    expect(run.code).toBe(2);
  });
});

describe("doctor · the canon and the lock", () => {
  test("F26: a stale page ai-eng proved its own but could not remove stays stale across runs, keeps its hash, and is named as removal refused", async () => {
    // Windows chmod cannot deny a delete, and root ignores the mode: nothing to refuse there.
    if (process.platform === "win32" || process.getuid?.() === 0) return;
    const { home } = healthy();
    const key = "skills/ai-verify/evals/README.md";
    const folder = join(home, "skills", "ai-verify", "evals");
    const page = "# Evals — an outdated page this binary no longer ships\n";
    mkdirSync(folder, { recursive: true });
    writeFileSync(join(home, key), page);
    const recordPath = join(home, "canon-owned.json");
    const before = JSON.parse(readFileSync(recordPath, "utf8")) as { files: Record<string, string> };
    writeFileSync(recordPath, JSON.stringify({ files: { ...before.files, [key]: sha256(page) } }));
    const refusedText = `1 stale file(s) ai-eng shipped earlier — removal refused by the filesystem (a read-only, locked or busy folder), kept and retried by the next ai-eng update: ${key}. Make the folder writable, then run ai-eng update`;

    chmodSync(folder, 0o555);
    try {
      for (let pass = 0; pass < 2; pass += 1) {
        const lines = installCanon(VERSION);
        expect(lines).toContain(`⚠ ${refusedText}`);
        expect(lines.join("\n")).not.toContain("user file");
        const record = JSON.parse(readFileSync(recordPath, "utf8")) as { files: Record<string, string>; refused: string[] };
        expect(record.files[key]).toBe(sha256(page));
        expect(record.refused).toEqual([key]);
      }
      const run = await doctor();
      expect(row(run, "canon")).toContain("▲");
      expect(detail(run, "canon")).toContain(`1 stale, removal refused: ${key} — make the folder writable, then ai-eng update`);
      expect(detail(run, "canon")).not.toContain("kept user file");
    } finally {
      chmodSync(folder, 0o755);
    }

    // Once the folder lets it, the next run removes it: it was ours all along.
    installCanon(VERSION);
    expect(existsSync(join(home, key))).toBe(false);
    expect(row(await doctor(), "canon")).toContain("✓");
  });

  test("an intact canon is ok; an edited skill drifts; a file we do not ship is named but not held against it", async () => {
    const { home } = healthy();
    let run = await doctor();
    expect(row(run, "canon")).toContain("✓");
    expect(detail(run, "canon")).toContain("0 drift · 0 missing");

    mkdirSync(join(home, "skills", "my-own-skill"), { recursive: true });
    writeFileSync(join(home, "skills", "my-own-skill", "SKILL.md"), "# somebody else's\n");
    run = await doctor();
    expect(row(run, "canon")).toContain("✓");
    expect(detail(run, "canon")).toContain("1 not ours (left alone)");
    expect(detail(run, "canon")).toContain("0 drift");

    writeFileSync(join(home, "skills", "ai-debug", "SKILL.md"), "# edited by hand\n");
    run = await doctor();
    expect(row(run, "canon")).toContain("▲");
    expect(detail(run, "canon")).toContain("1 drift");

    writeFileSync(join(home, "skills", "ai-debug", "orphan.md"), "a file this binary no longer ships\n");
    run = await doctor();
    expect(row(run, "canon")).toContain("▲");
    expect(detail(run, "canon")).toContain("1 kept user file(s) in shipped skill folders (never deleted)");
    expect(detail(run, "canon")).toContain("1 not ours (left alone)");
  });

  test("F20: a user file in a shipped skill folder is reported as kept and never warned about; a recorded one is stale", async () => {
    const { home } = healthy();
    const key = "skills/ai-debug/my-notes.md";
    writeFileSync(join(home, key), "mine\n");
    let run = await doctor();
    expect(row(run, "canon")).toContain("✓");
    expect(detail(run, "canon")).toContain("1 kept user file(s) in shipped skill folders (never deleted)");
    expect(detail(run, "canon")).not.toContain("stale");

    const recordPath = join(home, "canon-owned.json");
    const record = JSON.parse(readFileSync(recordPath, "utf8")) as { files: Record<string, string> };
    writeFileSync(recordPath, JSON.stringify({ files: { ...record.files, [key]: sha256("mine\n") } }));
    run = await doctor();
    expect(row(run, "canon")).toContain("▲");
    expect(detail(run, "canon")).toContain("1 stale (ai-eng update sweeps what we shipped)");
  });

  test("F23: pages an install left before ownership was recorded are unproven, never a user file: warned with the manual step, kept, and cleared only by hand", async () => {
    const { home } = healthy();
    // A v2.6.0 install: it shipped these pages and wrote no canon-owned.json.
    rmSync(join(home, "canon-owned.json"));
    const readme = "skills/ai-verify/evals/README.md";
    const catalog = "skills/ai-verify/evals/bug-catalog.md";
    mkdirSync(join(home, "skills", "ai-verify", "evals"), { recursive: true });
    writeFileSync(join(home, readme), "# Evals — test the reviewer, not just the code\n");
    writeFileSync(join(home, catalog), "# Bug catalog\n");
    const unprovenText = (paths: string[]) =>
      `${paths.length} file(s) in shipped skill folders that ai-eng cannot prove it wrote (left from before ownership was recorded: an outdated page of ours or a file of yours) — never deleted: ${paths.join(", ")}. Review each: delete it by hand, or move a file you keep out of the skill folder`;

    let run = await doctor();
    expect(row(run, "canon")).toContain("✓");
    expect(detail(run, "canon")).not.toContain("kept user file");
    expect(row(run, "canon unproven")).toContain("▲");
    expect(detail(run, "canon unproven")).toBe(unprovenText([catalog, readme]));

    // The repair update runs keeps them and carries them into the new record, so a second
    // run does not mistake them for files the user added after it.
    for (let pass = 0; pass < 2; pass += 1) expect(installCanon(VERSION)).toContain(`⚠ ${unprovenText([catalog, readme])}`);
    expect(readFileSync(join(home, readme), "utf8")).toBe("# Evals — test the reviewer, not just the code\n");
    expect((JSON.parse(readFileSync(join(home, "canon-owned.json"), "utf8")) as { unproven: string[] }).unproven).toEqual([catalog, readme]);
    run = await doctor();
    expect(detail(run, "canon unproven")).toBe(unprovenText([catalog, readme]));

    rmSync(join(home, catalog));
    expect(detail(await doctor(), "canon unproven")).toBe(unprovenText([readme]));
    rmSync(join(home, readme));
    run = await doctor();
    expect(row(run, "canon unproven")).toBe("(no row for canon unproven)");
    expect(row(run, "canon")).toContain("✓");
  });

  test("the full installed skill inventory is verified despite a legacy pack filter", async () => {
    const legacyConfig = `${GOVERNED}\n[canon]\npacks = ["triage"]\n`;
    const { home } = healthy(legacyConfig);
    const sourceSkills = join(import.meta.dir, "..", "skills");
    const expectedSkillNames = readdirSync(sourceSkills, { withFileTypes: true })
      .filter((entry) => entry.isDirectory() && existsSync(join(sourceSkills, entry.name, "SKILL.md")))
      .map((entry) => entry.name)
      .sort();
    const installedSkillNames = readdirSync(join(home, "skills"), { withFileTypes: true })
      .filter((entry) => entry.isDirectory() && existsSync(join(home, "skills", entry.name, "SKILL.md")))
      .map((entry) => entry.name)
      .sort();
    expect(installedSkillNames).toEqual(expectedSkillNames);

    const run = await doctor();
    const expectedFiles = canonSkills().size;
    expect(detail(run, "canon")).toBe(`${expectedFiles}/${expectedFiles} files verified · 0 drift · 0 missing`);
    expect(row(run, "canon")).toContain("✓");
  });

  // A legacy pack list once narrowed what doctor looked at: a skill outside it could be
  // gone and the canon row still read green. Every shape the old key took must be ignored.
  test.each([
    ["absent", ""],
    ["empty", "\n[canon]\npacks = []\n"],
    ["partial", '\n[canon]\npacks = ["ai-debug"]\n'],
    ["an unknown pack name", '\n[canon]\npacks = ["no-such-pack"]\n'],
    ["not a list", '\n[canon]\npacks = "everything"\n'],
  ])("a skill missing outside the legacy pack list (%s) is still reported missing", async (_shape, legacy) => {
    const { home } = healthy(`${GOVERNED}${legacy}`);
    rmSync(join(home, "skills", "ai-verify", "SKILL.md"));

    const run = await doctor();
    const expectedFiles = canonSkills().size;
    expect(detail(run, "canon")).toBe(`${expectedFiles - 1}/${expectedFiles} files verified · 0 drift · 1 missing`);
    expect(row(run, "canon")).toContain("▲");
    expect(row(run, "config.toml")).toContain("✓");
  });

  test("assets: a matching lock is ok, a stale one names both versions, no lock and no version warn", async () => {
    const { root } = sandbox();
    const lock = join(root, ".ai-engineering", "ai-eng.lock");

    writeFileSync(lock, lockText({ version: VERSION, assets: {} }));
    let run = await doctor();
    expect(row(run, "assets")).toContain("✓");
    expect(detail(run, "assets")).toBe(`installed by ${VERSION}`);

    writeFileSync(lock, lockText({ version: "0.0.1", assets: {} }));
    run = await doctor();
    expect(row(run, "assets")).toContain("▲");
    expect(detail(run, "assets")).toBe(`binary ${VERSION} · files installed by 0.0.1 → ai-eng update`);

    writeFileSync(lock, "# no version here\n[assets]\n");
    run = await doctor();
    expect(detail(run, "assets")).toBe("lock has no version — run ai-eng update");

    rmSync(lock);
    run = await doctor();
    expect(row(run, "assets")).toContain("▲");
    expect(detail(run, "assets")).toBe("no ai-eng.lock — governance files were never (re)installed: run ai-eng init");
  });

  test("machine state: a downgrade warns, a changed definition names the host, unchanged is ok", async () => {
    const { home } = sandbox();
    const state = join(home, "machine.json");

    writeFileSync(state, JSON.stringify({ version: "99.0.0", carriers: { "claude-code": "deadbeef" } }));
    let run = await doctor();
    expect(row(run, "machine state")).toContain("▲");
    expect(detail(run, "machine state")).toContain("a DOWNGRADE");

    writeFileSync(state, JSON.stringify({ version: VERSION, carriers: { "claude-code": "deadbeef" } }));
    run = await doctor();
    expect(detail(run, "machine state")).toBe(`carrier definition changed since ${VERSION}: claude-code → ai-eng update`);

    // A version that differs as a string but not segment by segment is not newer.
    writeFileSync(state, JSON.stringify({ version: `${VERSION}.0`, carriers: { "claude-code": "deadbeef" } }));
    run = await doctor();
    expect(detail(run, "machine state")).toBe(`carrier definition changed since ${VERSION}.0: claude-code → ai-eng update`);

    const shipped = carrierFiles("claude-code")!;
    writeFileSync(state, JSON.stringify({ version: VERSION, carriers: { "claude-code": sha256(shipped.main) } }));
    run = await doctor();
    expect(row(run, "machine state")).toContain("✓");
    expect(detail(run, "machine state")).toBe(`carriers written by ${VERSION} · definitions unchanged`);
  });

  test("F18: machine state held by a lock or left under a claim name is named, never read as no state", async () => {
    const { home } = sandbox();
    const state = join(home, "machine.json");
    const recorded = JSON.stringify({ version: VERSION, carriers: { "claude-code": sha256(carrierFiles("claude-code")!.main) } });
    writeFileSync(state, recorded);
    const lock = join(home, ".machine.json.lock");
    writeFileSync(lock, JSON.stringify({ pid: 1, hostname: "another-host", startedAt: "2026-01-01T00:00:00.000Z" }));
    let run = await doctor();
    expect(row(run, "machine state")).toContain("▲");
    expect(detail(run, "machine state")).toBe(
      `${lock} — held by another ai-eng run, one on another host, or one this run cannot prove has stopped; machine state left untouched. If no ai-eng run is using this home, delete ${lock} and run again`,
    );

    rmSync(lock);
    rmSync(state);
    const claim = join(home, ".machine.json.4242.abcdef012345.claim");
    writeFileSync(claim, recorded);
    run = await doctor();
    expect(row(run, "machine state")).toContain("▲");
    expect(detail(run, "machine state")).toBe(
      `machine.json is missing; an interrupted ai-eng run left its previous contents at ${claim} — move the right copy back to machine.json by hand; machine state left untouched`,
    );
  });
});

describe("doctor · the git floor", () => {
  test("the three marker shims plus a working gitleaks are ok", async () => {
    const { root } = sandbox();
    writeFloor(root);
    gitleaks(0);
    const run = await doctor();
    expect(row(run, "git floor")).toContain("✓");
    expect(detail(run, "git floor")).toBe("marker hooks in .git/hooks/ · gitleaks present");
  });

  test("missing shims FAIL; shims without gitleaks only WARN", async () => {
    const { root } = sandbox();
    let run = await doctor();
    expect(row(run, "git floor")).toContain("✗");
    expect(detail(run, "git floor")).toBe("marker hooks missing from .git/hooks/ — run ai-eng init");
    expect(run.code).toBe(2);

    writeFloor(root);
    gitleaks(1);
    run = await doctor();
    expect(row(run, "git floor")).toContain("▲");
    expect(detail(run, "git floor")).toBe("marker hooks in .git/hooks/ · gitleaks MISSING (HARD FAIL)");
  });
});

describe("doctor · receipts and overrides", () => {
  test("doctor opens its frame before reusing one raw receipt summary", async () => {
    sandbox();
    const events: string[] = [];
    const originalSummary = receiptsModule.summarizeReceipts;
    const summarize = spyOn(receiptsModule, "summarizeReceipts").mockImplementation((dir) => {
      events.push("summary");
      return originalSummary(dir);
    });
    const frame = spyOn(uiModule, "frame").mockImplementation(() => {
      events.push("frame");
    });

    // A spy on a module export outlives the file: in one `bun test` process the
    // next suite's frame() would stay this silent stub (the mutation dry run on Linux).
    try {
      await doctor();

      expect(summarize).toHaveBeenCalledTimes(1);
      expect(events.slice(0, 2)).toEqual(["frame", "summary"]);
    } finally {
      summarize.mockRestore();
      frame.mockRestore();
    }
  });

  test("receipts under the ceiling are ok; a slow one warns with the p95 that says so", async () => {
    const { root } = sandbox();
    const receipts = join(root, ".ai-engineering", "receipts");
    mkdirSync(receipts, { recursive: true });
    writeFileSync(join(receipts, "fast.json"), receipt(2, "allow"));
    let run = await doctor();
    expect(row(run, "receipts")).toContain("✓");
    expect(detail(run, "receipts")).toMatch(/^last 14d: 2 runs · 1 denies · p50 \d+ms · p95 \d+ms \(ceiling 50\) · top no-verify\/Bash$/);

    writeFileSync(join(receipts, "slow.json"), receipt(400, "deny"));
    run = await doctor();
    expect(row(run, "receipts")).toContain("▲");
    expect(detail(run, "receipts")).toMatch(/^last 14d: \d+ runs · \d+ denies · p50 \d+ms · p95 400ms \(ceiling 50\)( · top .*)?$/);
  });

  test("deviation: the receipts row WARNs with the spike named when 7-day denies pass 3x the prior week", async () => {
    const { root } = sandbox();
    const receipts = join(root, ".ai-engineering", "receipts");
    mkdirSync(receipts, { recursive: true });
    const day = (offset: number) => new Date(Date.now() - offset * 86_400_000).toISOString();
    // A real baseline: last week happened, with one deny in the prior 7-day window.
    // The raw trail, not a summary file: the rule's baseline must be something the
    // adversary cannot rewrite (audit run-1 F1).
    writeFileSync(join(receipts, "p1.json"), denyReceipt("injection", day(9)));
    writeFileSync(join(receipts, "p2.json"), allowReceipt(day(9)));
    for (let i = 0; i < 4; i++) writeFileSync(join(receipts, `d${i}.json`), denyReceipt("injection"));
    const run = await doctor();
    expect(row(run, "receipts")).toContain("▲");
    // last7 counts the fixture's 4 plus this doctor run's own adversarial deny.
    expect(detail(run, "receipts")).toMatch(/spike [2-9]\d* vs 1 the week before \(injection\)/);
  });

  test("deviation: a forged summary.json can neither silence nor fake the spike the way receipts can", async () => {
    const { root } = sandbox();
    const receipts = join(root, ".ai-engineering", "receipts");
    mkdirSync(receipts, { recursive: true });
    const day = (offset: number) => new Date(Date.now() - offset * 86_400_000).toISOString();
    writeFileSync(join(receipts, "p1.json"), denyReceipt("injection", day(9)));
    for (let i = 0; i < 4; i++) writeFileSync(join(receipts, `d${i}.json`), denyReceipt("injection"));
    // The old attack: inflate the prior window in the aggregate the rule read.
    writeFileSync(join(receipts, "summary.json"), JSON.stringify({ daily: { [day(9).slice(0, 10)]: { runs: 5, denies: 100_000_000 } } }));
    let run = await doctor();
    expect(detail(run, "receipts")).toContain("spike"); // summary.json is not the baseline
    // And it cannot manufacture a spike either: empty today + giant string in summary.
    rmSync(join(receipts, "summary.json"));
    for (const f of ["p1.json", "d0.json", "d1.json", "d2.json", "d3.json"]) rmSync(join(receipts, f), { force: true });
    writeFileSync(join(receipts, "summary.json"), JSON.stringify({ daily: { [day(3).slice(0, 10)]: { runs: 0, denies: "999999" } } }));
    run = await doctor();
    expect(detail(run, "receipts")).not.toContain("spike"); // only the chain's own receipts count
  });

  test("the receipts line strips forged control bytes from attacker-written receipt keys", async () => {
    // Build a minimal governed repo with a receipt — no sandbox(), no process.chdir().
    // doctorMain({ cwd }) passes cwd to runChecks which passes it to repoRoot.
    const root = tempDir("ai-eng-canary-");
    mkdirSync(join(root, ".git", "hooks"), { recursive: true });
    mkdirSync(join(root, ".ai-engineering", "receipts"), { recursive: true });
    writeFileSync(join(root, ".ai-engineering", "config.toml"), GOVERNED);
    writeFileSync(join(root, ".ai-engineering", "receipts", "x.json"), JSON.stringify({
      schema: "urn:ai-eng:receipt:2", operation_id: "deadbe01", event: "PreToolUse", surface: "claude-code",
      tool: "Write", guards: { ran: [], denied_by: "self-protect\n│  ✗ CANARY-injected-row" },
      outcome: "deny", latency_ms: 1, ts: new Date().toISOString(),
    }));
    const chunks: string[] = [];
    const stdout = spyOn(process.stdout, "write").mockImplementation(((chunk: unknown) => {
      chunks.push(String(chunk));
      return true;
    }) as never);
    const log = spyOn(console, "log").mockImplementation(((...args: unknown[]) => {
      chunks.push(`${args.map(String).join(" ")}\n`);
    }) as never);
    try {
      const code = await doctorMain({ cwd: root });
      const out = chunks.join("").replace(/\u001b\[[0-9;]*[A-Za-z]/g, "");
      const canary = out.split("\n").filter((l) => l.includes("CANARY-injected-row"));
      expect(canary.length).toBe(1);
      expect(canary[0]).toContain("receipts ·");
    } finally {
      stdout.mockRestore();
      log.mockRestore();
    }
  });

  test("repeats: the ledger count rides the line, and forged shapes coerce to zero not NaN", async () => {
    const { root } = sandbox();
    const receipts = join(root, ".ai-engineering", "receipts");
    mkdirSync(receipts, { recursive: true });
    writeFileSync(join(receipts, "denies.json"), JSON.stringify({
      a: { n: 3, last_seen: new Date().toISOString() },
      b: { n: "999", last_seen: new Date().toISOString() },
      c: { n: {}, last_seen: new Date().toISOString() },
    }));
    const run = await doctor();
    expect(detail(run, "receipts")).toContain("repeats 2"); // only the well-formed entry counts
  });

  test("no prior series means the deviation rule is silent: a repo that never collected still reports ok", async () => {
    const { root } = sandbox();
    const receipts = join(root, ".ai-engineering", "receipts");
    mkdirSync(receipts, { recursive: true });
    writeFileSync(join(receipts, "d0.json"), denyReceipt("injection"));
    const run = await doctor();
    expect(row(run, "receipts")).toContain("✓");
    expect(detail(run, "receipts")).not.toContain("spike");
  });
  function denyReceipt(by: string, ts = new Date().toISOString()): string {
    return JSON.stringify({
      schema: "urn:ai-eng:receipt:2",
      operation_id: "deny0001",
      event: "PreToolUse",
      surface: "claude-code",
      tool: "Bash",
      guards: { ran: [by], denied_by: by },
      latency_ms: 2,
      outcome: "deny",
      ts,
    });
  }

  function allowReceipt(ts = new Date().toISOString()): string {
    return JSON.stringify({
      schema: "urn:ai-eng:receipt:2", operation_id: "allow01", event: "PreToolUse", surface: "claude-code",
      tool: "Bash", guards: { ran: [], denied_by: null }, latency_ms: 2, outcome: "allow", ts,
    });
  }
  test("overrides: none is ok, and active, dateless and expired entries are each named", async () => {
    const { home, root } = sandbox();
    writeFileSync(join(root, "AGENTS.md"), agentsMd(6, 20));
    writeFloor(root);
    gitleaks(0);
    shipClaudeCarrier(home);
    let run = await doctor();
    expect(row(run, "overrides")).toContain("✓");
    expect(detail(run, "overrides")).toBe("none active");

    const future = new Date(Date.now() + 5 * 86_400_000).toISOString().slice(0, 10);
    const past = new Date(Date.now() - 10 * 86_400_000).toISOString().slice(0, 10);
    writeFileSync(
      join(root, ".ai-engineering", "overrides.toml"),
      [
        "[[guard.off]]",
        'name = "no-verify"',
        'reason = "migration window"',
        `until = "${future}"`,
        "",
        "[[guard.off]]",
        'name = "loop"',
        'reason = "long refactor"',
        "",
        "[[guard.off]]",
        'name = "injection"',
        'reason = "old exception"',
        `until = "${past}"`,
        "",
      ].join("\n"),
    );
    run = await doctor();
    expect(row(run, "overrides")).toContain("▲");
    expect(detail(run, "overrides")).toContain("no-verify — migration window (expires in ");
    expect(detail(run, "overrides")).toContain("loop — long refactor (no expiry — add an until)");
    expect(detail(run, "overrides")).toContain(`injection — expired ${past} → remove it from .ai-engineering/overrides.toml`);
    expect(run.code).toBe(0);
  });
});

describe("doctor · arch", () => {
  test("arch is active with src/ present and bootstrap without it", async () => {
    const { root } = sandbox();
    writeFileSync(join(root, ".ai-engineering", "arch.rules.json"), "{}");
    let run = await doctor();
    expect(row(run, "arch")).toContain("▲");
    expect(detail(run, "arch")).toBe("bootstrap mode — src/ empty");

    mkdirSync(join(root, "src"));
    run = await doctor();
    expect(row(run, "arch")).toContain("✓");
    expect(detail(run, "arch")).toBe("active — src/ present");
  });

  test("arch active when code lives outside src", async () => {
    const { root } = sandbox();
    writeFileSync(join(root, ".ai-engineering", "arch.rules.json"), "{}");
    mkdirSync(join(root, "kit", "src"), { recursive: true });
    writeFileSync(join(root, "kit", "src", "Button.tsx"), "export {}\n");
    const run = await doctor();
    expect(row(run, "arch")).toContain("✓");
    expect(detail(run, "arch")).toBe("active — source outside src/");
    expect(detail(run, "arch")).not.toBe("bootstrap mode — src/ empty");
  });

});

describe("doctor · surface carriers", () => {
  test("a core machine carrier missing is a FAIL; the bytes this binary ships are ok", async () => {
    const { home } = sandbox();
    let run = await doctor();
    expect(row(run, "surface claude-code")).toContain("✗");
    expect(detail(run, "surface claude-code")).toBe("machine carrier ~/.claude/settings.json missing → ai-eng update");
    expect(run.code).toBe(2);

    const placement = machineCarrier(SURFACES.find((surface) => surface.id === "claude-code")!)!;
    mkdirSync(join(home, ".claude"), { recursive: true });
    writeFileSync(carrierPath(placement), carrierFiles("claude-code")!.main);
    run = await doctor();
    expect(row(run, "surface claude-code")).toContain("✓");
    expect(detail(run, "surface claude-code")).toBe("machine carrier ~/.claude/settings.json carries the ai-eng entries");
  });

  test("a module carrier resolves through its agent dir, drifts on other bytes and matches its own", async () => {
    const agentDir = tempDir("ai-eng-doc-agentdir-");
    process.env.PI_CODING_AGENT_DIR = agentDir;
    sandbox('[surfaces]\nenabled = ["oh-my-pi"]\n');
    const placement = machineCarrier(SURFACES.find((surface) => surface.id === "oh-my-pi")!)!;
    const files = carrierFiles("oh-my-pi")!;
    const entry = carrierPath(placement);
    const chain = carrierPath(placement, placement.chain!);
    expect(entry.startsWith(agentDir)).toBe(true);
    mkdirSync(join(agentDir, "hooks", "pre"), { recursive: true });

    writeFileSync(entry, "# not what this binary ships\n");
    let run = await doctor();
    expect(row(run, "surface oh-my-pi")).toContain("▲");
    expect(detail(run, "surface oh-my-pi")).toBe("machine carrier ~/.omp/agent/hooks/pre/ai-eng.ts is NOT the one this binary ships → ai-eng update");

    writeFileSync(entry, files.main);
    writeFileSync(chain, files.chain!);
    run = await doctor();
    expect(row(run, "surface oh-my-pi")).toContain("✓");
    expect(detail(run, "surface oh-my-pi")).toBe("machine carrier ~/.omp/agent/hooks/pre/ai-eng.ts matches the binary");
  });

  test("a repo carrier is required for cursor, best-effort for copilot, and absent for zed", async () => {
    const { root } = sandbox('[surfaces]\nenabled = ["cursor", "copilot-cli", "zed"]\n');
    let run = await doctor();
    expect(row(run, "surface cursor")).toContain("✗");
    expect(detail(run, "surface cursor")).toContain("repo carrier .cursor/hooks.json missing → ai-eng update");
    expect(row(run, "surface copilot-cli")).toContain("▲");
    expect(detail(run, "surface copilot-cli")).toContain("machine carrier ~/.copilot/hooks/ai-eng.json missing → ai-eng update");
    expect(detail(run, "surface copilot-cli")).toContain("repo carrier .github/hooks/ai-eng.json missing → ai-eng update");
    // The note says VS Code shares this surface's hook files, so nobody wires it twice.
    expect(detail(run, "surface copilot-cli")).toContain("the CLI and VS Code share — the same hook files");
    expect(row(run, "surface zed")).toContain("✓");
    expect(detail(run, "surface zed")).toContain("no carrier: guard wiring is not implemented for this host");
    expect(run.code).toBe(2);

    mkdirSync(join(root, ".cursor"), { recursive: true });
    writeFileSync(join(root, ".cursor", "hooks.json"), "{}");
    run = await doctor();
    expect(row(run, "surface cursor")).toContain("✓");
    expect(detail(run, "surface cursor")).toContain("repo carrier .cursor/hooks.json present");
  });
});

describe("doctor · behaviors", () => {
  test("none declared is ok, a frontmatter that does not match its folder FAILs", async () => {
    const { root } = sandbox();
    let run = await doctor();
    expect(row(run, "behaviors")).toContain("✓");
    expect(detail(run, "behaviors")).toBe("no behaviors declared");

    const dir = join(root, ".agents", "behaviors", "verify-before-yield");
    mkdirSync(dir, { recursive: true });
    writeFileSync(join(dir, "BEHAVIOR.md"), "---\nname: wrong-name\ndescription: A behavior.\n---\nbody\n");
    run = await doctor();
    expect(row(run, "behaviors")).toContain("✗");
    expect(detail(run, "behaviors")).toBe("verify-before-yield: name=wrong-name ≠ folder verify-before-yield");
    expect(run.code).toBe(2);

    const other = join(root, ".agents", "behaviors", "no-frontmatter");
    mkdirSync(other, { recursive: true });
    writeFileSync(join(other, "BEHAVIOR.md"), "no frontmatter here\n");
    run = await doctor();
    expect(detail(run, "behaviors")).toContain("no-frontmatter: no frontmatter");

    writeFileSync(join(dir, "BEHAVIOR.md"), "---\nname: verify-before-yield\ndescription: A behavior.\n---\nbody\n");
    rmSync(other, { recursive: true, force: true });
    run = await doctor();
    expect(row(run, "behaviors")).toContain("✓");
    expect(detail(run, "behaviors")).toBe("frontmatter ok");
  });
});

describe("doctor --gc", () => {
  test("an empty repo collects nothing, and outside a repo it says there is no repo", async () => {
    sandbox();
    let run = await doctor({ gc: true });
    expect(run.code).toBe(0);
    expect(run.out).toContain("gc: nothing to collect");

    const bare = tempDir("ai-eng-doc-bare-");
    process.env.AI_ENG_HOME = tempDir("ai-eng-doc-home-");
    process.chdir(bare);
    run = await doctor({ gc: true });
    expect(run.code).toBe(0);
    expect(run.out).toContain("no repo: nothing to collect");
  });

  test("receipts past their ttl are aggregated into summary.json and deleted", async () => {
    const { root } = sandbox(`${GOVERNED}\n[gc]\nreceipts_ttl = "30d"\n`);
    const receipts = join(root, ".ai-engineering", "receipts");
    mkdirSync(receipts, { recursive: true });
    const stale = join(receipts, "2026-01-01T00-00-00-000Z-PreToolUse-abcdef12.json");
    const fresh = join(receipts, "fresh.json");
    writeFileSync(stale, receipt(12, "allow"));
    writeFileSync(fresh, receipt(9, "allow"));
    const old = new Date(Date.now() - 60 * 86_400_000);
    utimesSync(stale, old, old);

    const run = await doctor({ gc: true });
    expect(run.out).toContain("receipts: 1 aggregated into summary.json and deleted (ttl 30d)");
    expect(existsSync(stale)).toBe(false);
    expect(existsSync(fresh)).toBe(true);
    const summary = JSON.parse(readFileSync(join(receipts, "summary.json"), "utf8")) as { total: number; gc?: unknown };
    expect(summary.total).toBe(2);
    expect(typeof summary.gc).toBe("string");
  });

  test("a receipts folder that is a link is named in a warning and nothing at its target is deleted", async () => {
    const { root } = sandbox(`${GOVERNED}\n[gc]\nreceipts_ttl = "0d"\n`);
    const outside = tempDir("ai-eng-doc-outside-");
    const stale = join(outside, "2026-01-01T00-00-00-000Z-PreToolUse-abcdef12.json");
    writeFileSync(stale, receipt(12, "allow"));
    const old = new Date(Date.now() - 60 * 86_400_000);
    utimesSync(stale, old, old);
    symlinkSync(outside, join(root, ".ai-engineering", "receipts"), "dir");

    const run = await doctor({ gc: true });

    expect(run.code).toBe(0);
    expect(run.out).toContain("⚠ receipts: .ai-engineering/receipts is a link or resolves outside the repository — retention skipped, nothing deleted");
    expect(readdirSync(outside)).toEqual(["2026-01-01T00-00-00-000Z-PreToolUse-abcdef12.json"]);
    expect(readFileSync(stale, "utf8")).toBe(receipt(12, "allow"));
  });

  test("old artifacts are archived in git, cited ones stay, a full folder is flagged", async () => {
    const { root } = sandbox(`${GOVERNED}\n[gc]\nmax_files = 1\nkeep_runs = 5\nolder_than = "90d"\n`);
    const ai = join(root, ".ai-engineering");
    mkdirSync(join(ai, "research"), { recursive: true });
    writeFileSync(join(ai, "research", "001-old.html"), "<html>old</html>");
    writeFileSync(join(ai, "research", "002-cited.html"), "<html>cited</html>");
    writeFileSync(join(root, "DECISIONS.md"), "D-002 cites research/002-cited.html.\n");
    for (let n = 1; n <= 6; n += 1) {
      mkdirSync(join(ai, "security", `run-${n}`), { recursive: true });
      writeFileSync(join(ai, "security", `run-${n}`, "findings.json"), "{}");
    }
    gitInit(root);
    commit(root, "old", { GIT_AUTHOR_DATE: "2026-01-01T00:00:00Z", GIT_COMMITTER_DATE: "2026-01-01T00:00:00Z" });
    mkdirSync(join(ai, "reports"), { recursive: true });
    for (const name of ["a.md", "b.md", "c.md"]) writeFileSync(join(ai, "reports", name), "young\n");
    commit(root, "young");

    const run = await doctor({ gc: true });
    expect(run.out).toContain("research/: archived 1 in git and deleted (research/001-old.html)");
    expect(run.out).toContain("research/: 1 cited by a permanent governor — immune");
    expect(run.out).toContain("reports/: 3 > max_files=1 — review before the next pass");
    expect(run.out).toContain("security/: archived 1 in git and deleted (keeping the last 5)");
    expect(existsSync(join(ai, "research", "001-old.html"))).toBe(false);
    expect(existsSync(join(ai, "research", "002-cited.html"))).toBe(true);
    expect(existsSync(join(ai, "security", "run-1"))).toBe(false);
    expect(existsSync(join(ai, "security", "run-6"))).toBe(true);
  });
});

describe("a half-installed module host is a report, not a crash", () => {
  test("a current entry with its chain bundle missing warns instead of rejecting", async () => {
    // The entry can be byte-perfect while the bundle beside it is gone — the state an
    // interrupted install leaves, and the state check 11 exists to name. It used to throw
    // ENOENT out of the read, so the whole health report died on the one host it had
    // something to say about.
    const agentDir = tempDir("ai-eng-doc-halfbundle-");
    process.env.PI_CODING_AGENT_DIR = agentDir;
    sandbox('[surfaces]\nenabled = ["oh-my-pi"]\n');
    const placement = machineCarrier(SURFACES.find((surface) => surface.id === "oh-my-pi")!)!;
    const files = carrierFiles("oh-my-pi")!;
    mkdirSync(join(agentDir, "hooks", "pre"), { recursive: true });
    writeFileSync(carrierPath(placement), files.main); // the bundle is deliberately absent

    const run = await doctor();

    // It reports at all — the read used to throw ENOENT out of doctorMain — and the row
    // it produced is the drift warning, not the crash.
    expect(run.out).toContain("surface oh-my-pi");
    expect(row(run, "surface oh-my-pi")).toContain("▲");
    expect(detail(run, "surface oh-my-pi")).toContain("is NOT the one this binary ships");
  });
});
