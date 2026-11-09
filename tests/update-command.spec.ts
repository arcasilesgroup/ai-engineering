// tests/update-command.spec.ts — `update` re-installs this repo's assets from the
// installed binary, with zero network.
//
// Every run is sandboxed in a mkdtemp tree: AI_ENG_HOME and PI_CODING_AGENT_DIR so the
// machine half (canon, mirrors and carriers) lands in the temp dir and never in the
// developer's real home.
//
// syncPlan is pure — a directory of prepared files plus a lock's asset map in, the
// verdict out. updateMain runs in-process (its lines are what coverage counts). The
// `--yes` runs need nobody; the prompt runs carry a scripted stdin — the key queue
// tests/cli-ux.test.ts documents and scripts/proof-cli-ux.sh drives through the real CLI.

import { afterAll, afterEach, beforeEach, describe, expect, test } from "bun:test";
import { spawnSync } from "node:child_process";
import { chmodSync, existsSync, linkSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, readlinkSync, realpathSync, renameSync, rmSync, statSync, symlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { basename, delimiter, join, dirname, relative, resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { PassThrough } from "node:stream";
import { syncPlan, updateMain } from "../src/commands/update.ts";
import { planEntries } from "../src/commands/init-shared.ts";
import { carrierDefinition, carrierFiles } from "../src/surfaces/adapters.ts";
import { mergeSharedText, sha256, stripSharedText } from "../src/install.ts";
import { VERSION } from "../src/version.ts";
import type { PlanEntry } from "../src/install.ts";
import { recordGitCommands } from "./fixtures/git-recorder.ts";

const SANDBOX = mkdtempSync(join(tmpdir(), "ai-eng-update-cmd-"));
const ENG_HOME = join(SANDBOX, "home");
const CWD = process.cwd();
const REPO_ROOT = resolve(import.meta.dir, "..");
const KEYS = ["AI_ENG_HOME", "PI_CODING_AGENT_DIR", "GIT_CONFIG_GLOBAL", "NO_COLOR", "CI", "AI_ENG_NO_UPDATE_NOTICES", "PATH"] as const;
const saved: Partial<Record<(typeof KEYS)[number], string | undefined>> = {};
let savedStdin: PropertyDescriptor | undefined;

beforeEach(() => {
  for (const key of KEYS) saved[key] = process.env[key];
  mkdirSync(ENG_HOME, { recursive: true });
  process.env.AI_ENG_HOME = ENG_HOME;
  process.env.PI_CODING_AGENT_DIR = join(SANDBOX, "pi-agent");
  process.env.GIT_CONFIG_GLOBAL = join(ENG_HOME, "gitconfig");
  process.env.NO_COLOR = "1";
  process.env.CI = "true";
  process.env.AI_ENG_NO_UPDATE_NOTICES = "1";
});

afterEach(() => {
  process.chdir(CWD);
  if (savedStdin) {
    Object.defineProperty(process, "stdin", savedStdin);
    savedStdin = undefined;
  }
  for (const key of KEYS) {
    const value = saved[key];
    if (value === undefined) delete process.env[key];
    else process.env[key] = value;
  }
});

afterAll(() => {
  rmSync(SANDBOX, { recursive: true, force: true });
});

/** Run something that prints through src/ui.ts and keep what it printed. clack writes
 *  through process.stdout/stderr, so the swap is the whole seam. */
async function captured<T>(run: () => Promise<T>): Promise<{ value: T; out: string; err: string }> {
  const out: string[] = [];
  const err: string[] = [];
  const stdout = process.stdout.write;
  const stderr = process.stderr.write;
  process.stdout.write = ((chunk: string | Uint8Array) => (out.push(String(chunk)), true)) as never;
  process.stderr.write = ((chunk: string | Uint8Array) => (err.push(String(chunk)), true)) as never;
  try {
    return { value: await run(), out: out.join(""), err: err.join("") };
  } finally {
    process.stdout.write = stdout;
    process.stderr.write = stderr;
  }
}

const tick = (ms: number): Promise<void> => {
  const { promise, resolve } = Promise.withResolvers<void>();
  setTimeout(resolve, ms);
  return promise;
};

/** `update`'s prompts get the stream src/ui.ts's scriptedInput() builds from
 *  `process.stdin`. A PassThrough that is NOT a TTY makes it build that wrapper, whose
 *  whole job is replaying the bytes written to it as discrete keypresses, one per tick —
 *  the same queue scripts/proof-cli-ux.sh feeds through the real CLI. */
function pipeStdin(): PassThrough {
  const stream = new PassThrough();
  const descriptor = Object.getOwnPropertyDescriptor(process, "stdin");
  if (descriptor) savedStdin = descriptor;
  Object.defineProperty(process, "stdin", { value: stream, configurable: true, writable: true });
  return stream;
}

const CANCEL = "\x03";

/** A governed repo: config.toml declares the surface, and .git exists the way any repo
 *  the user actually has one does. The declaration is the MINIMAL one on purpose — it is
 *  the user's bytes, not the template's, which is a state update has to leave alone. */
function governedRepo(name: string): string {
  const repo = join(SANDBOX, name);
  mkdirSync(join(repo, ".ai-engineering"), { recursive: true });
  writeFileSync(join(repo, ".ai-engineering", "config.toml"), '[surfaces]\nenabled = ["claude-code"]\n');
  spawnSync("git", ["init", "-q"], { cwd: repo });
  return repo;
}

function gitIn(repo: string, args: string[]): string {
  const result = spawnSync("git", args, { cwd: repo, encoding: "utf8" });
  if (result.status !== 0) throw new Error(`git ${args.join(" ")} failed: ${result.stderr}`);
  return result.stdout ?? "";
}

/** A repo the binary has already installed into, with one hook patched by hand: a file
 *  ai-eng wrote and the person edited. */
async function patchedRepo(name: string): Promise<{ repo: string; shim: string; lockPath: string }> {
  const repo = governedRepo(name);
  process.chdir(repo);
  await captured(() => updateMain({ yes: true }));
  const shim = join(repo, ".git", "hooks", "pre-commit");
  writeFileSync(shim, `${readFileSync(shim, "utf8")}\n# my custom bit: pnpm install --frozen\n`);
  return { repo, shim, lockPath: join(repo, ".ai-engineering", "ai-eng.lock") };
}

/** The plan entry for a path, or a loud failure: a fixture that cannot find what the
 *  payload ships is a broken test, not an empty assertion. */
function entryFor(entries: PlanEntry[], path: string): PlanEntry {
  const found = entries.find((entry) => entry.path === path);
  if (!found) throw new Error(`the payload has no entry for ${path}`);
  return found;
}

function filesBelow(directory: string): string[] {
  if (!existsSync(directory)) return [];
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    return entry.isDirectory() ? filesBelow(path) : [path];
  });
}

type SourceSkillFile = { skill: string; relativePath: string; content: string; bytes: Buffer<ArrayBuffer> };

function sourceSkillFiles(): SourceSkillFile[] {
  const skillsRoot = join(REPO_ROOT, "skills");
  return readdirSync(skillsRoot, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && existsSync(join(skillsRoot, entry.name, "SKILL.md")))
    .flatMap((entry) => {
      const skillRoot = join(skillsRoot, entry.name);
      return filesBelow(skillRoot).filter((path) => basename(path) !== ".DS_Store").map((path) => ({
        skill: entry.name,
        relativePath: relative(skillRoot, path),
        content: readFileSync(path, "utf8"),
        bytes: readFileSync(path),
      }));
    });
}

function assertAllSkillsInstalled(additionalNames: string[] = [], editedFiles: string[] = []): void {
  const files = sourceSkillFiles();
  const expectedNames = [...new Set(files.map((file) => file.skill)), ...additionalNames].sort();
  const installedRoot = join(ENG_HOME, "skills");
  const installedNames = readdirSync(installedRoot, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && existsSync(join(installedRoot, entry.name, "SKILL.md")))
    .map((entry) => entry.name)
    .sort();
  expect(files.length).toBeGreaterThan(0);
  expect(installedNames).toEqual(expectedNames);
  for (const file of files) {
    const installedPath = join(installedRoot, file.skill, file.relativePath);
    if (editedFiles.includes(`${file.skill}/${file.relativePath}`)) {
      expect(existsSync(installedPath)).toBe(true);
    } else {
      expect(readFileSync(installedPath)).toEqual(file.bytes);
    }
  }
}

describe("syncPlan · what the binary decides to write, keep or refuse", () => {
  const entries = planEntries(["claude-code"]);
  const paths = entries.map((entry) => entry.path).sort();

  test("nothing on disk yet is fresh — the whole payload", () => {
    const root = join(SANDBOX, "plan-empty");
    mkdirSync(root, { recursive: true });
    const plan = syncPlan(entries, root, {});
    expect([...plan.fresh].sort()).toEqual(paths);
    expect(plan.current).toEqual([]);
    expect(plan.updates).toEqual([]);
    expect(plan.yours).toEqual([]);
    expect(plan.verbatim).toEqual([]);
  });

  test("files byte-identical to ours are current and provably ours (verbatim)", () => {
    const root = join(SANDBOX, "plan-current");
    for (const entry of entries) {
      mkdirSync(dirname(join(root, entry.path)), { recursive: true });
      writeFileSync(join(root, entry.path), entry.ours);
    }
    // A lock from the previous install records DIFFERENT bytes: the file on disk is ours
    // as this binary writes it, so the recorded hash is irrelevant and nothing is planned.
    const previous = Object.fromEntries(entries.map((entry) => [entry.path, sha256(`${entry.ours}\nstale\n`)]));
    const plan = syncPlan(entries, root, previous);
    expect([...plan.current].sort()).toEqual(paths);
    expect([...plan.verbatim].sort()).toEqual(paths);
    expect(plan.updates).toEqual([]);
    expect(plan.fresh).toEqual([]);
    expect(plan.yours).toEqual([]);
  });

  test("a file ai-eng never wrote is the project's own, left alone", () => {
    const root = join(SANDBOX, "plan-users");
    mkdirSync(join(root, ".github", "workflows"), { recursive: true });
    writeFileSync(join(root, ".github/workflows/ai-eng-check.yml"), "name: mine\n");
    const plan = syncPlan(entries, root, {});
    // No lock entry: ai-eng never wrote it, so it is not ai-eng's to rewrite.
    expect(plan.yours).toEqual([".github/workflows/ai-eng-check.yml"]);
    expect(plan.current).toEqual([]);
    expect(plan.updates).toEqual([]);
  });

  test("a file ai-eng wrote is updated, edited or not; seeded config the project edited is the project's", () => {
    const root = join(SANDBOX, "plan-updates");
    const target = ".github/workflows/ai-eng-check.yml";
    mkdirSync(join(root, ".github", "workflows"), { recursive: true });
    const previousOurs = "on: [push]\n# v previous\n";
    writeFileSync(join(root, target), previousOurs);
    expect(syncPlan(entries, root, { [target]: sha256(previousOurs) }).updates).toEqual([target]);

    // The same file edited by hand is still ai-eng's: it takes this binary's bytes.
    writeFileSync(join(root, target), `${previousOurs}# mine too\n`);
    const edited = syncPlan(entries, root, { [target]: sha256(previousOurs) });
    expect(edited.updates).toEqual([target]);
    expect(edited.yours).toEqual([]);

    // Seeded config is the project's from its first edit, and while unedited it follows ai-eng.
    const config = ".ai-engineering/overrides.toml";
    mkdirSync(join(root, ".ai-engineering"), { recursive: true });
    writeFileSync(join(root, config), "# seeded by an older ai-eng\n");
    expect(syncPlan(entries, root, { [config]: sha256("# seeded by an older ai-eng\n") }).updates).toContain(config);
    writeFileSync(join(root, config), "# seeded by an older ai-eng\nmine = true\n");
    const tuned = syncPlan(entries, root, { [config]: sha256("# seeded by an older ai-eng\n") });
    expect(tuned.yours).toContain(config);
    expect(tuned.updates).not.toContain(config);
  });

  test("a shared settings file is updated by its merge, never written whole", () => {
    const cursor = planEntries(["cursor"]);
    const settings = entryFor(cursor, ".cursor/hooks.json");
    expect(settings.merge).toBe(true);
    const root = join(SANDBOX, "plan-merge");
    mkdirSync(join(root, ".cursor"), { recursive: true });
    const path = join(root, ".cursor/hooks.json");

    // The merge is the update: the file has the user's own keys and no hooks of ours.
    writeFileSync(path, '{\n  "version": 1\n}\n');
    expect(syncPlan(cursor, root, {}).updates).toEqual([settings.path]);

    // Our entries in and a second sync sees nothing left to do — idempotent by merge.
    const merged = mergeSharedText(readFileSync(path, "utf8"), settings.ours);
    if ("refused" in merged) throw new Error(`expected a merge, got ${merged.refused}`);
    writeFileSync(path, merged.text);
    const again = syncPlan(cursor, root, {});
    expect(again.updates).toEqual([]);
    expect(again.current).toEqual([settings.path]);

    // A file that is not JSON is left exactly as it is: not ours to rewrite — the surface
    // simply runs unguarded and the installer says so elsewhere.
    writeFileSync(path, "// hand-written settings\n");
    const refused = syncPlan(cursor, root, {});
    expect(refused.updates).toEqual([]);
    expect(refused.yours).toEqual([]);
    expect(refused.current).toEqual([settings.path]);
  });
});

describe("updateMain · rewriting this repo's assets from the binary", () => {
  test("outside a governed repo it refuses with exit 2 and writes nothing", async () => {
    const foreign = join(SANDBOX, "foreign");
    mkdirSync(foreign, { recursive: true });
    process.chdir(foreign);
    const run = await captured(() => updateMain({ yes: true }));
    expect(run.value).toBe(2);
    expect(run.err).toInclude("not in a governed repo");
    expect(existsSync(join(foreign, ".ai-engineering"))).toBe(false);
  });

  test("a governed repo gets its assets, an executable git floor, and a second run changes nothing", async () => {
    const repo = governedRepo("repo-fresh");
    writeFileSync(join(repo, "AGENTS.md"), "# my contract, never yours\n");
    const declaration = '[surfaces]\nenabled = ["claude-code"]\n';
    const machineSettings = join(ENG_HOME, ".claude", "settings.json");
    const machineSettingsBefore = '{\n  "user": "keep"\n}\n';
    mkdirSync(dirname(machineSettings), { recursive: true });
    writeFileSync(machineSettings, machineSettingsBefore);
    process.chdir(repo);

    const first = await captured(() => updateMain({ yes: true }));
    expect(first.value).toBe(0);
    expect(first.out).toInclude("assets synced");

    const lockPath = join(repo, ".ai-engineering", "ai-eng.lock");
    const lock = readFileSync(lockPath, "utf8");
    expect(lock).toInclude(`version = "${VERSION}"`);
    expect(lock).toInclude('".git/hooks/pre-commit"');
    expect(lock).toInclude('".github/workflows/ai-eng-check.yml"');
    // What is the user's stays the user's: the declaration is not template-shaped, so the
    // binary has no evidence it ever wrote it and claims nothing in its ledger.
    expect(readFileSync(join(repo, ".ai-engineering", "config.toml"), "utf8")).toBe(declaration);
    expect(lock).not.toInclude(".ai-engineering/config.toml");
    expect(readFileSync(join(repo, "AGENTS.md"), "utf8")).toBe("# my contract, never yours\n");
    // A git shim that is not executable is a git hook that silently never runs.
    // Windows has no execute bit; Git for Windows runs a hook whatever its mode.
    if (process.platform !== "win32") expect(statSync(join(repo, ".git", "hooks", "pre-commit")).mode & 0o111).not.toBe(0);
    // The local canon installs completely, and the user's machine settings take our entries
    // beside their own keys.
    expect(first.out).toInclude("~/.claude/settings.json · machine carrier · written");
    const machineSettingsMerged = readFileSync(machineSettings, "utf8");
    expect(JSON.parse(machineSettingsMerged).user).toBe("keep");
    expect(machineSettingsMerged).toMatch(/ai-eng(?:\.cmd|\.exe)? chain/);
    expect(machineSettingsMerged).not.toBe(machineSettingsBefore);
    expect(existsSync(join(repo, ".claude", "settings.json"))).toBe(false);
    assertAllSkillsInstalled();

    const bytes = readFileSync(lockPath, "utf8");
    const mtime = statSync(lockPath).mtimeMs;
    const second = await captured(() => updateMain({ yes: true }));
    expect(second.value).toBe(0);
    expect(second.out).toInclude("assets current");
    expect(second.out).not.toInclude("assets synced");
    // Both halves report on a run that changed nothing — an update that answers "all
    // assets current" and stops cannot be told from one that never looked at the canon,
    // the carriers or the git floor (cli-ux-14).
    expect(second.out).toInclude("Machine side");
    expect(second.out).toInclude("nothing to write");
    expect(second.out).toInclude("global canon");
    expect(second.out).toInclude("~/.claude/settings.json · machine carrier already current");
    expect(second.out).toInclude("Nothing written");
    // A carrier already merged is never reported as a second write.
    expect(second.out).not.toInclude("machine carrier · written");
    expect(readFileSync(machineSettings, "utf8")).toBe(machineSettingsMerged);
    expect(readFileSync(lockPath, "utf8")).toBe(bytes);
    expect(statSync(lockPath).mtimeMs).toBe(mtime);
  });

  test("a fresh machine gets the missing settings carriers doctor sends it here for", async () => {
    // The CI runner's shape: no ~/.claude/settings.json, no ~/.codex, no ~/.copilot.
    const freshHome = join(SANDBOX, "home-fresh-settings");
    mkdirSync(freshHome, { recursive: true });
    process.env.AI_ENG_HOME = freshHome;
    const repo = governedRepo("repo-fresh-settings");
    writeFileSync(join(repo, ".ai-engineering", "config.toml"), '[surfaces]\nenabled = ["claude-code", "codex", "copilot-cli"]\n');
    process.chdir(repo);
    const carriers: Array<[string, string]> = [
      ["claude-code", ".claude/settings.json"],
      ["codex", ".codex/hooks.json"],
      ["copilot-cli", ".copilot/hooks/ai-eng.json"],
    ];

    const first = await captured(() => updateMain({ yes: true }));
    expect(first.value).toBe(0);
    for (const [id, path] of carriers) {
      expect(readFileSync(join(freshHome, path), "utf8")).toBe(carrierFiles(id)!.main);
      expect(first.out).toInclude(`~/${path} · machine carrier · written`);
    }
    expect(first.out).not.toInclude("unavailable on this platform");
    const recorded = JSON.parse(readFileSync(join(freshHome, "machine.json"), "utf8")) as { carriers: Record<string, string> };
    for (const [id] of carriers) expect(recorded.carriers[id]).toBe(carrierDefinition(carrierFiles(id)!.main));

    const second = await captured(() => updateMain({ yes: true }));
    expect(second.value).toBe(0);
    for (const [, path] of carriers) expect(second.out).toInclude(`~/${path} · machine carrier already current`);
    expect(second.out).not.toInclude("machine carrier · written");
  });

  for (const { name, bytes } of [
    { name: "absent", bytes: '[surfaces]\nenabled = ["claude-code"]\n' },
    { name: "empty", bytes: '[surfaces]\nenabled = ["claude-code"]\n\n[canon]\npacks = []\n' },
    { name: "partial", bytes: '[surfaces]\nenabled = ["claude-code"]\n\n[canon]\npacks = ["triage"]\n' },
    { name: "legacy", bytes: '[surfaces]\nenabled = ["claude-code"]\n\n[canon]\npacks = ["triage", "removed-pack"]\n' },
    { name: "inline-table", bytes: 'canon = { packs = ["triage"] }\n[surfaces]\nenabled = ["claude-code"]\n' },
    { name: "dotted-key", bytes: 'canon.packs = ["triage"]\n\n[surfaces]\nenabled = ["claude-code"]\n' },
    { name: "multiline", bytes: '[surfaces]\nenabled = ["claude-code"]\n\n[canon]\npacks = [\n  "triage", # kept by hand\n  "review",\n]\n' },
    { name: "non-array", bytes: '[surfaces]\nenabled = ["claude-code"]\n\n[canon]\npacks = "all"\n' },
    { name: "crlf", bytes: '[surfaces]\r\nenabled = ["claude-code"]\r\n\r\n[canon]\r\npacks = ["triage"]   # legacy\r\n' },
  ]) {
    test(`update ignores ${name} legacy pack settings and installs all skills`, async () => {
      rmSync(join(ENG_HOME, "skills"), { recursive: true, force: true });
      const repo = governedRepo(`repo-legacy-packs-${name}`);
      const configPath = join(repo, ".ai-engineering", "config.toml");
      writeFileSync(configPath, bytes);
      const mtime = statSync(configPath).mtimeMs;
      process.chdir(repo);

      const run = await captured(() => updateMain({ yes: true }));

      expect(run.value).toBe(0);
      expect(readFileSync(configPath)).toEqual(Buffer.from(bytes));
      expect(statSync(configPath).mtimeMs).toBe(mtime);
      assertAllSkillsInstalled();
    });
  }

  test("a canon an earlier pack-filtered install left partial gains every missing skill, and config.toml keeps its bytes", async () => {
    rmSync(join(ENG_HOME, "skills"), { recursive: true, force: true });
    const repo = governedRepo("repo-legacy-partial-canon");
    const configPath = join(repo, ".ai-engineering", "config.toml");
    const legacyConfig = '[surfaces]\nenabled = ["claude-code"]\n\n[canon]\npacks = []\n';
    writeFileSync(configPath, legacyConfig);
    process.chdir(repo);
    expect((await captured(() => updateMain({ yes: true }))).value).toBe(0);
    const lockPath = join(repo, ".ai-engineering", "ai-eng.lock");
    const lockBefore = readFileSync(lockPath, "utf8");
    // The shape a core-only install left: whole skill folders absent, the lock in place.
    const skillNames = [...new Set(sourceSkillFiles().map((file) => file.skill))].sort();
    const removed = skillNames.filter((_, index) => index % 2 === 1);
    expect(removed.length).toBeGreaterThan(0);
    for (const name of removed) rmSync(join(ENG_HOME, "skills", name), { recursive: true });
    const mtime = statSync(configPath).mtimeMs;

    const run = await captured(() => updateMain({ yes: true }));

    expect(run.value).toBe(0);
    expect(run.out).toInclude("global canon outdated or incomplete — re-installed");
    expect(readFileSync(configPath)).toEqual(Buffer.from(legacyConfig));
    expect(statSync(configPath).mtimeMs).toBe(mtime);
    expect(readFileSync(lockPath, "utf8")).toBe(lockBefore);
    assertAllSkillsInstalled();
  });

  test("update repairs a missing skill resource, rewrites an edited shipped page, and keeps a skill of your own", async () => {
    rmSync(join(ENG_HOME, "skills"), { recursive: true, force: true });
    const repo = governedRepo("repo-skill-repair");
    const configPath = join(repo, ".ai-engineering", "config.toml");
    const legacyConfig = '[surfaces]\nenabled = ["claude-code"]\n\n[canon]\npacks = ["removed-pack"]\n';
    writeFileSync(configPath, legacyConfig);
    const machineSettings = join(ENG_HOME, ".claude", "settings.json");
    const machineSettingsBefore = '{\n  "user": "repair"\n}\n';
    mkdirSync(dirname(machineSettings), { recursive: true });
    writeFileSync(machineSettings, machineSettingsBefore);
    process.chdir(repo);
    expect((await captured(() => updateMain({ yes: true }))).value).toBe(0);
    // The first update merged our entries into the user's file; that is the baseline now.
    const machineSettingsMerged = readFileSync(machineSettings, "utf8");
    expect(machineSettingsMerged).toInclude('"user": "repair"');

    const sourceFiles = sourceSkillFiles();
    // A shipped sibling of the edited file: one skill folder with an edit and a gap at once.
    const missingSibling = sourceFiles.find((file) => file.relativePath !== "SKILL.md");
    const editedSource = sourceFiles.find((file) => file.skill === missingSibling?.skill && file.relativePath === "SKILL.md");
    const missingSource = sourceFiles.find((file) => file.skill !== editedSource?.skill && file.relativePath !== "SKILL.md");
    const missingSkill = sourceFiles.find((file) => file.skill !== editedSource?.skill && file.skill !== missingSource?.skill)?.skill;
    if (editedSource === undefined || missingSource === undefined || missingSibling === undefined || missingSkill === undefined) {
      throw new Error("the skills inventory needs a SKILL.md, nested resources and a third skill for repair coverage");
    }
    const skill = join(ENG_HOME, "skills", editedSource.skill, editedSource.relativePath);
    const localEdit = Buffer.concat([readFileSync(skill), Buffer.from("\nLocal change.\n")]);
    writeFileSync(skill, localEdit);
    const missingPath = join(ENG_HOME, "skills", missingSource.skill, missingSource.relativePath);
    rmSync(missingPath);
    const missingSiblingPath = join(ENG_HOME, "skills", missingSibling.skill, missingSibling.relativePath);
    rmSync(missingSiblingPath);
    rmSync(join(ENG_HOME, "skills", missingSkill), { recursive: true });
    const userOwnedSkill = join(ENG_HOME, "skills", "my-local-skill", "SKILL.md");
    const userOwnedResource = join(ENG_HOME, "skills", "my-local-skill", "references", "notes.md");
    mkdirSync(dirname(userOwnedResource), { recursive: true });
    writeFileSync(userOwnedSkill, "# mine\n");
    writeFileSync(userOwnedResource, "my notes\n");

    const repair = await captured(() => updateMain({ yes: true }));

    expect(repair.value).toBe(0);
    expect(repair.out).toInclude("global canon outdated or incomplete — re-installed");
    expect(repair.out).not.toInclude("local change kept");
    // The shipped page is ai-eng's: the edit is replaced by this binary's bytes.
    expect(readFileSync(skill)).toEqual(editedSource.bytes);
    expect(readFileSync(missingPath)).toEqual(missingSource.bytes);
    expect(readFileSync(missingSiblingPath)).toEqual(missingSibling.bytes);
    expect(readFileSync(userOwnedSkill, "utf8")).toBe("# mine\n");
    expect(readFileSync(userOwnedResource, "utf8")).toBe("my notes\n");
    expect(readFileSync(configPath)).toEqual(Buffer.from(legacyConfig));
    // Machine settings are not part of the canon: the repair neither writes nor removes them.
    expect(readFileSync(machineSettings, "utf8")).toBe(machineSettingsMerged);
    assertAllSkillsInstalled(["my-local-skill"]);
  });

  test("F20: a file added by hand inside a shipped skill folder is swept once, and the next update finds the canon clean", async () => {
    rmSync(join(ENG_HOME, "skills"), { recursive: true, force: true });
    const repo = governedRepo("repo-kept-user-file");
    process.chdir(repo);
    expect((await captured(() => updateMain({ yes: true }))).value).toBe(0);
    const notes = join(ENG_HOME, "skills", "ai-debug", "my-notes.md");
    writeFileSync(notes, "mine\n");

    const second = await captured(() => updateMain({ yes: true }));
    expect(second.value).toBe(0);
    expect(second.out).toInclude("re-installed");
    expect(second.out).toInclude("skills/ai-debug/my-notes.md");
    expect(existsSync(notes)).toBe(false);

    const third = await captured(() => updateMain({ yes: true }));
    expect(third.value).toBe(0);
    expect(third.out).not.toInclude("re-installed");
    expect(third.out).toInclude("global canon ·");
  });

  test("update leaves HEAD unchanged, spawns no commit, and leaves global config untouched", async () => {
    const globalConfig = join(SANDBOX, "isolated-gitconfig-update");
    const globalConfigBefore = "[user]\n\tname = Isolated test\n";
    writeFileSync(globalConfig, globalConfigBefore);
    process.env.GIT_CONFIG_GLOBAL = globalConfig;

    const repo = governedRepo("repo-no-commit");
    gitIn(repo, ["config", "user.name", "CP10 test"]);
    gitIn(repo, ["config", "user.email", "cp10@example.com"]);
    writeFileSync(join(repo, "baseline.txt"), "review me\n");
    gitIn(repo, ["add", "baseline.txt"]);
    gitIn(repo, ["commit", "-qm", "test: add CP10 baseline"]);

    const headBefore = gitIn(repo, ["rev-parse", "HEAD"]).trim();
    const countBefore = gitIn(repo, ["rev-list", "--count", "HEAD"]).trim();
    process.chdir(repo);
    const recorder = recordGitCommands(SANDBOX);
    let result: number;
    try {
      result = (await captured(() => updateMain({ yes: true }))).value;
    } finally {
      recorder.stop();
    }

    const commands = recorder.commands();
    expect({
      result,
      head: gitIn(repo, ["rev-parse", "HEAD"]).trim(),
      commitCount: gitIn(repo, ["rev-list", "--count", "HEAD"]).trim(),
      hasUncommittedChanges: gitIn(repo, ["status", "--porcelain"]).trim().length > 0,
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

  test("the update CLI does not fetch or enter the notice path", () => {
    const isolatedHome = join(SANDBOX, "no-notice-home");
    const noNoticeConfig = join(isolatedHome, "gitconfig");
    const shimDir = join(SANDBOX, "notice-bin");
    const noticeLog = join(SANDBOX, "notice-calls");
    const fetchLog = join(SANDBOX, "fetch-calls");
    const runner = join(SANDBOX, "run-update.ts");
    mkdirSync(isolatedHome, { recursive: true });
    writeFileSync(noNoticeConfig, "[user]\n\tname = Isolated test\n");
    process.env.GIT_CONFIG_GLOBAL = noNoticeConfig;
    const repo = governedRepo("repo-no-notice");
    mkdirSync(shimDir, { recursive: true });

    const quote = (value: string) => JSON.stringify(value);
    writeFileSync(join(shimDir, "bun"), `#!/bin/sh\nprintf '%s\\n' "$*" >> ${quote(noticeLog)}\nprintf '99.0.0\\n'\n`);
    writeFileSync(join(shimDir, "npm"), `#!/bin/sh\nprintf '%s\\n' "$*" >> ${quote(noticeLog)}\nprintf '99.0.0\\n'\n`);
    chmodSync(join(shimDir, "bun"), 0o755);
    chmodSync(join(shimDir, "npm"), 0o755);

    const cli = join(import.meta.dir, "..", "src", "cli.ts");
    const cliUrl = pathToFileURL(cli).href;
    writeFileSync(runner, `
      import { writeFileSync } from "node:fs";
      globalThis.fetch = () => {
        writeFileSync(${quote(fetchLog)}, "called");
        throw new Error("update unexpectedly fetched");
      };
      process.argv = [process.argv[0], ${quote(cli)}, "update", "--yes"];
      await import(${quote(cliUrl)});
    `);

    const env: NodeJS.ProcessEnv = {
      ...process.env,
      AI_ENG_HOME: isolatedHome,
      PI_CODING_AGENT_DIR: join(SANDBOX, "no-notice-pi"),
      GIT_CONFIG_GLOBAL: join(isolatedHome, "gitconfig"),
      PATH: `${shimDir}${delimiter}${process.env.PATH ?? ""}`,
    };
    delete env.AI_ENG_NO_UPDATE_NOTICES;
    const run = spawnSync(process.execPath, [runner], { cwd: repo, encoding: "utf8", env });

    expect(run.status).toBe(0);
    expect(existsSync(fetchLog)).toBe(false);
    expect(existsSync(noticeLog)).toBe(false);
  });

  test("the plan names a shared settings file as merged, never overwritten, and each ↳ list sits under its own heading", async () => {
    const repo = governedRepo("repo-plan-rows");
    writeFileSync(join(repo, ".ai-engineering", "config.toml"), '[surfaces]\nenabled = ["cursor"]\n');
    process.chdir(repo);
    expect((await captured(() => updateMain({ yes: true }))).value).toBe(0);
    // The project's own hooks file, without ai-eng's entries, under a lock that recorded
    // an older ai-eng write: the merge has work to do, and the file is edited.
    const lockPath = join(repo, ".ai-engineering", "ai-eng.lock");
    const hooks = join(repo, ".cursor", "hooks.json");
    const theirs = `${JSON.stringify({ version: 1, hooks: { stop: [{ command: "my-own-hook" }] } }, null, 2)}\n`;
    writeFileSync(hooks, theirs);
    writeFileSync(lockPath, readFileSync(lockPath, "utf8").replace(/^"\.cursor\/hooks\.json" = ".*"$/m, `".cursor/hooks.json" = "${sha256("older ai-eng bytes\n")}"`));

    const run = await captured(() => updateMain({ yes: true }));
    expect(run.value).toBe(0);
    const lines = run.out.split("\n");
    const row = lines.find((line) => line.includes(".cursor/hooks.json") && !line.includes("↳")) ?? "";
    expect(row).toInclude("your keys kept");
    expect(row).not.toInclude("overwritten");
    expect(readFileSync(hooks, "utf8")).toInclude("my-own-hook");
    // A ↳ list follows the heading it belongs to, never the row above it.
    const current = lines.findIndex((line) => line.includes("already current — untouched"));
    expect(current).toBeGreaterThan(-1);
    expect(lines[current + 1]).toInclude("↳");
    expect(lines[current - 1]).not.toInclude("↳");
  });

  test("--yes rewrites a patched hook: ai-eng's file takes this binary's bytes, named, and the lock follows", async () => {
    const { shim, lockPath } = await patchedRepo("repo-patched");

    const run = await captured(() => updateMain({ yes: true }));
    expect(run.value).toBe(0);
    expect(run.out).toInclude("hooks/pre-commit");
    expect(run.out).toInclude("edited since ai-eng wrote it");
    expect(run.out).not.toInclude("What wins?");
    expect(readFileSync(shim, "utf8")).toBe(entryFor(planEntries(["claude-code"]), ".git/hooks/pre-commit").ours);
    expect(readFileSync(lockPath, "utf8")).toInclude('".git/hooks/pre-commit"');
  });

  // Windows has no read-only mode a write respects here, and root ignores the mode.
  test.skipIf(process.platform === "win32" || process.getuid?.() === 0)("a recorded file the filesystem will not let update write is named, still ai-eng's, and keeps its lock entry for the retry", async () => {
    const { repo, lockPath } = await patchedRepo("repo-readonly-recorded");
    const workflow = join(repo, ".github", "workflows", "ai-eng-check.yml");
    writeFileSync(workflow, `${readFileSync(workflow, "utf8")}# my extra step\n`);
    const recorded = /"\.github\/workflows\/ai-eng-check\.yml" = "([0-9a-f]{64})"/.exec(readFileSync(lockPath, "utf8"))?.[1];
    expect(recorded).toBeDefined();
    chmodSync(workflow, 0o444);

    const run = await captured(() => updateMain({ yes: true })).finally(() => chmodSync(workflow, 0o644));

    expect(run.value).toBe(0);
    expect(run.out).toInclude("the filesystem refused the write");
    expect(readFileSync(workflow, "utf8")).toInclude("# my extra step");
    expect(readFileSync(lockPath, "utf8")).toInclude(`".github/workflows/ai-eng-check.yml" = "${recorded!}"`);
  });

  test("seeded config the project edited stays the project's: untouched, named, and no longer claimed by the lock", async () => {
    const repo = governedRepo("repo-tuned-config");
    process.chdir(repo);
    expect((await captured(() => updateMain({ yes: true }))).value).toBe(0);
    const overrides = join(repo, ".ai-engineering", "overrides.toml");
    const tuned = `${readFileSync(overrides, "utf8")}\n# tuned for this project\n`;
    writeFileSync(overrides, tuned);
    // Something else is pending, so the run reaches Apply and rewrites the lock.
    rmSync(join(repo, ".github", "workflows", "ai-eng-check.yml"));

    const run = await captured(() => updateMain({ yes: true }));
    expect(run.value).toBe(0);
    expect(run.out).toInclude("yours (not written by ai-eng, or config you edited)");
    expect(readFileSync(overrides, "utf8")).toBe(tuned);
    expect(readFileSync(join(repo, ".ai-engineering", "ai-eng.lock"), "utf8")).not.toInclude(".ai-engineering/overrides.toml");
  });

  test("cancelling Apply writes nothing: not the repo, and not the canon it would repair", async () => {
    const { shim, lockPath } = await patchedRepo("repo-cancel");
    const bytes = readFileSync(lockPath, "utf8");
    // A canon that needs repair too: the repair rewrites and sweeps, so it waits for Apply.
    const page = join(ENG_HOME, "skills", "ai-debug", "SKILL.md");
    const shippedPage = readFileSync(page, "utf8");
    const editedPage = `${shippedPage}\nLocal change.\n`;
    writeFileSync(page, editedPage);
    const notes = join(ENG_HOME, "skills", "ai-debug", "my-notes.md");
    writeFileSync(notes, "mine\n");
    const stdin = pipeStdin();

    try {
      const run = await captured(async () => {
        const running = updateMain();
        await tick(20);
        stdin.write(CANCEL); // ctrl-c at "Apply?"
        return running;
      });

      expect(run.value).toBe(0);
      expect(run.out).toInclude("Nothing written.");
      expect(readFileSync(shim, "utf8")).toInclude("# my custom bit");
      expect(readFileSync(lockPath, "utf8")).toBe(bytes);
      expect(readFileSync(page, "utf8")).toBe(editedPage);
      expect(existsSync(notes)).toBe(true);
    } finally {
      writeFileSync(page, shippedPage);
      rmSync(notes, { force: true });
    }
  });

  test("an edited seeded config alone is named as yours, and the lock stops claiming it with no Apply question", async () => {
    const repo = governedRepo("repo-tuned-config-alone");
    process.chdir(repo);
    expect((await captured(() => updateMain({ yes: true }))).value).toBe(0);
    const overrides = join(repo, ".ai-engineering", "overrides.toml");
    const tuned = `${readFileSync(overrides, "utf8")}\n# tuned for this project\n`;
    writeFileSync(overrides, tuned);
    pipeStdin(); // no key ever arrives: an Apply question would hang the run

    const run = await captured(() => updateMain());
    expect(run.value).toBe(0);
    expect(run.out).toInclude("yours (not written by ai-eng, or config you edited)");
    expect(run.out).not.toInclude("Apply?");
    expect(readFileSync(overrides, "utf8")).toBe(tuned);
    expect(readFileSync(join(repo, ".ai-engineering", "ai-eng.lock"), "utf8")).not.toInclude(".ai-engineering/overrides.toml");
  });

  test("a recorded file this binary no longer ships is ai-eng's: removed, edited or not, and dropped from the lock", async () => {
    const repo = governedRepo("repo-retired");
    process.chdir(repo);
    expect((await captured(() => updateMain({ yes: true }))).value).toBe(0);
    const lockPath = join(repo, ".ai-engineering", "ai-eng.lock");
    const retired = ".github/workflows/ai-eng-retired.yml";
    const config = ".ai-engineering/config.toml";
    const configHash = sha256(readFileSync(join(repo, config), "utf8"));
    writeFileSync(join(repo, retired), "name: retired\n# edited\n");
    // The lock's [assets] table is last, so an appended row joins it. config.toml is
    // recorded and untouched: ai-eng's, though update never rewrites it, so it stays recorded.
    writeFileSync(lockPath, `${readFileSync(lockPath, "utf8")}"${retired}" = "${sha256("name: retired\n")}"\n"${config}" = "${configHash}"\n`);

    const run = await captured(() => updateMain({ yes: true }));
    expect(run.value).toBe(0);
    expect(run.out).toInclude(retired);
    expect(existsSync(join(repo, retired))).toBe(false);
    const lock = readFileSync(lockPath, "utf8");
    expect(lock).not.toInclude(retired);
    expect(lock).toInclude(`"${config}" = "${configHash}"`);
  });

  test("an older lock's repo settings carrier is the project's file: only ai-eng's entries come out, its own keys stay", async () => {
    const repo = governedRepo("repo-retired-settings");
    process.chdir(repo);
    expect((await captured(() => updateMain({ yes: true }))).value).toBe(0);
    const lockPath = join(repo, ".ai-engineering", "ai-eng.lock");
    const settings = join(repo, ".claude", "settings.json");
    const ours = carrierFiles("claude-code", "repo")!.main;
    const theirs = `${JSON.stringify({ permissions: { allow: ["Bash(ls)"] } }, null, 2)}\n`;
    const merged = mergeSharedText(theirs, ours);
    if ("refused" in merged) throw new Error(`fixture merge refused: ${merged.refused}`);
    mkdirSync(dirname(settings), { recursive: true });
    writeFileSync(settings, merged.text);
    writeFileSync(lockPath, `${readFileSync(lockPath, "utf8")}".claude/settings.json" = "${sha256(ours)}"\n`);

    const run = await captured(() => updateMain({ yes: true }));
    expect(run.value).toBe(0);
    expect(readFileSync(settings, "utf8")).toBe(theirs);
    expect(readFileSync(lockPath, "utf8")).not.toInclude(".claude/settings.json");
  });

  test.skipIf(process.platform === "win32")("the Apply plan promises what the retired sweep does: a settings file is stripped, a linked path is not removed", async () => {
    const repo = governedRepo("repo-retired-plan");
    process.chdir(repo);
    expect((await captured(() => updateMain({ yes: true }))).value).toBe(0);
    const lockPath = join(repo, ".ai-engineering", "ai-eng.lock");
    const ours = carrierFiles("claude-code", "repo")!.main;
    const merged = mergeSharedText(`${JSON.stringify({ permissions: { allow: ["Bash(ls)"] } }, null, 2)}\n`, ours);
    if ("refused" in merged) throw new Error(`fixture merge refused: ${merged.refused}`);
    mkdirSync(join(repo, ".claude"), { recursive: true });
    writeFileSync(join(repo, ".claude", "settings.json"), merged.text);
    const linked = ".github/workflows/ai-eng-retired.yml";
    const outside = join(SANDBOX, "retired-plan-outside.yml");
    writeFileSync(outside, "mine\n");
    mkdirSync(join(repo, ".github", "workflows"), { recursive: true });
    symlinkSync(outside, join(repo, linked));
    writeFileSync(lockPath, `${readFileSync(lockPath, "utf8")}".claude/settings.json" = "${sha256(ours)}"\n"${linked}" = "${sha256("name: x\n")}"\n`);
    const bytes = readFileSync(lockPath, "utf8");
    const stdin = pipeStdin();

    const run = await captured(async () => {
      const running = updateMain();
      await tick(20);
      stdin.write(CANCEL); // ctrl-c at "Apply?": only the plan is printed
      return running;
    });
    expect(run.value).toBe(0);
    const planLine = (path: string): string => run.out.split("\n").find((line) => line.includes(path)) ?? "";
    expect(planLine(".claude/settings.json")).toInclude("your keys kept");
    expect(planLine(".claude/settings.json")).not.toInclude("removed");
    expect(planLine(linked)).toBe("");
    expect(run.out).toInclude("Apply? 1 write");
    expect(readFileSync(lockPath, "utf8")).toBe(bytes);
  });

  test.skipIf(process.platform === "win32")("a retired settings file with a second name (a hard link) is never planned as a strip, keeps its lock entry, and is stripped once it has one name", async () => {
    const repo = governedRepo("repo-retired-hardlink");
    process.chdir(repo);
    expect((await captured(() => updateMain({ yes: true }))).value).toBe(0);
    const lockPath = join(repo, ".ai-engineering", "ai-eng.lock");
    const settings = join(repo, ".claude", "settings.json");
    const ours = carrierFiles("claude-code", "repo")!.main;
    const merged = mergeSharedText(`${JSON.stringify({ permissions: { allow: ["Bash(ls)"] } }, null, 2)}\n`, ours);
    if ("refused" in merged) throw new Error(`fixture merge refused: ${merged.refused}`);
    mkdirSync(dirname(settings), { recursive: true });
    writeFileSync(settings, merged.text);
    const secondName = join(SANDBOX, "retired-hardlink-second-name.json");
    linkSync(settings, secondName);
    writeFileSync(lockPath, `${readFileSync(lockPath, "utf8")}".claude/settings.json" = "${sha256(ours)}"\n`);

    for (let attempt = 0; attempt < 2; attempt++) {
      const stdin = pipeStdin();
      const run = await captured(async () => {
        const running = updateMain();
        await tick(20);
        stdin.write(CANCEL); // an Apply question would be cancelled here: the run must not ask one
        return running;
      });
      expect(run.value).toBe(0);
      expect(run.out).not.toInclude("stripped");
      expect(run.out).not.toInclude("Apply?");
      expect(readFileSync(settings, "utf8")).toBe(merged.text);
      expect(readFileSync(lockPath, "utf8")).toInclude(".claude/settings.json");
    }

    rmSync(secondName);
    expect((await captured(() => updateMain({ yes: true }))).value).toBe(0);
    expect(readFileSync(settings, "utf8")).toBe(stripSharedText(merged.text)!);
    expect(readFileSync(settings, "utf8")).toInclude("Bash(ls)");
    expect(readFileSync(lockPath, "utf8")).not.toInclude(".claude/settings.json");
  });

  test("a lock key escaping the repo is never planned as a removal, and the file it names stays", async () => {
    const repo = governedRepo("repo-retired-escape");
    process.chdir(repo);
    expect((await captured(() => updateMain({ yes: true }))).value).toBe(0);
    const lockPath = join(repo, ".ai-engineering", "ai-eng.lock");
    const outside = join(SANDBOX, "outside-the-repo.txt");
    writeFileSync(outside, "not ai-eng's\n");
    writeFileSync(lockPath, `${readFileSync(lockPath, "utf8")}"../outside-the-repo.txt" = "${sha256("not ai-eng's\n")}"\n`);

    const run = await captured(() => updateMain({ yes: true }));
    expect(run.value).toBe(0);
    expect(run.out).not.toInclude("no longer shipped");
    expect(run.out).not.toInclude("retired");
    expect(readFileSync(outside, "utf8")).toBe("not ai-eng's\n");
  });

  // Windows chmod cannot deny a delete, and root ignores the mode: nothing to refuse there.
  test.skipIf(process.platform === "win32" || process.getuid?.() === 0)("a retired file the filesystem will not delete keeps its lock entry for the retry", async () => {
    const repo = governedRepo("repo-retired-refused");
    process.chdir(repo);
    expect((await captured(() => updateMain({ yes: true }))).value).toBe(0);
    const lockPath = join(repo, ".ai-engineering", "ai-eng.lock");
    const folder = join(repo, ".ai-eng-retired");
    const retired = ".ai-eng-retired/old.txt";
    mkdirSync(folder);
    writeFileSync(join(repo, retired), "old\n");
    writeFileSync(lockPath, `${readFileSync(lockPath, "utf8")}"${retired}" = "${sha256("old\n")}"\n`);
    chmodSync(folder, 0o555);

    const run = await captured(() => updateMain({ yes: true })).finally(() => chmodSync(folder, 0o755));
    expect(run.value).toBe(0);
    expect(existsSync(join(repo, retired))).toBe(true);
    expect(readFileSync(lockPath, "utf8")).toInclude(`"${retired}" = "${sha256("old\n")}"`);
  });

  test("carriers that moved out of the repo are swept, and one we cannot claim is kept and named", async () => {
    const repo = governedRepo("repo-moved");
    mkdirSync(join(repo, ".agents", "hooks"), { recursive: true });
    mkdirSync(join(repo, ".pi", "extensions"), { recursive: true });
    writeFileSync(join(repo, ".agents/hooks/ai-eng.ts"), carrierFiles("oh-my-pi")!.main);
    writeFileSync(join(repo, ".pi/extensions/ai-eng.ts"), "// hand-written by a person, nothing to do with the product\n");
    process.chdir(repo);

    const run = await captured(() => updateMain({ yes: true }));
    expect(run.value).toBe(0);
    expect(existsSync(join(repo, ".agents/hooks/ai-eng.ts"))).toBe(false);
    expect(run.out).toInclude("moved to the machine");
    // Its bytes are not ours, so it is not ours to delete — and the line says so.
    expect(readFileSync(join(repo, ".pi/extensions/ai-eng.ts"), "utf8")).toInclude("hand-written");
    expect(run.out).toInclude("kept");
  });

  // Windows has no unreadable mode: chmod 0o000 only clears the write bit, so the file stays
  // readable — and root reads a mode-000 file, so there is nothing to refuse there either.
  test.skipIf(process.platform === "win32" || process.getuid?.() === 0)("F11: an unreadable machine settings file is refused, and the lock is still written", async () => {
    const repo = governedRepo("repo-unreadable-machine-settings");
    const machineSettings = join(ENG_HOME, ".claude", "settings.json");
    const settingsBefore = '{\n  "user": "keep"\n}\n';
    mkdirSync(dirname(machineSettings), { recursive: true });
    writeFileSync(machineSettings, settingsBefore);
    chmodSync(machineSettings, 0o000);
    process.chdir(repo);

    const run = await captured(() => updateMain({ yes: true })).finally(() => chmodSync(machineSettings, 0o644));

    expect(run.value).toBe(0);
    expect(run.out).toInclude("~/.claude/settings.json — unreadable, a dangling link, not a regular file, or changing while read; left untouched");
    expect(readFileSync(machineSettings, "utf8")).toBe(settingsBefore);
    expect(readFileSync(join(repo, ".ai-engineering", "ai-eng.lock"), "utf8")).toInclude(`version = "${VERSION}"`);
  });

  for (const linked of ["skills/ai-verify", "skills"] as const) {
    test(`F27: a symlinked \`${linked}\` is a refusal, not a crash: the link and its target stay, the path is named, the lock is written`, async () => {
      process.chdir(governedRepo(`repo-linked-${linked.replace("/", "-")}-first`));
      expect((await captured(() => updateMain({ yes: true }))).value).toBe(0);
      // A dotfiles setup: the user's own copy, lacking one shipped page, linked in its place.
      const inCanon = join(ENG_HOME, linked);
      // A linked skill is found under the canon's resolved root; the linked root by its own name.
      const linkPath = linked === "skills" ? inCanon : join(realpathSync(dirname(inCanon)), basename(inCanon));
      const dotfiles = join(SANDBOX, `dotfiles-${linked.replace("/", "-")}`);
      renameSync(inCanon, dotfiles);
      const page = join(dotfiles, linked === "skills" ? "ai-verify" : "", "VERIFICATION-SETUP-GUIDE.md");
      const shipped = readFileSync(page);
      rmSync(page);
      symlinkSync(dotfiles, inCanon, "dir");
      const before = filesBelow(dotfiles).map((path) => [path, readFileSync(path)] as const);
      const repo = governedRepo(`repo-linked-${linked.replace("/", "-")}`);
      process.chdir(repo);

      try {
        const run = await captured(() => updateMain({ yes: true }));

        expect(run.value).toBe(0);
        expect(run.out).toInclude(`path(s) where ai-eng installs are links or not its own folders or files — never written through, left as they are (the link and what it points at untouched): ${linkPath}`);
        expect(readlinkSync(inCanon)).toBe(dotfiles);
        expect(existsSync(page)).toBe(false);
        expect(filesBelow(dotfiles).map((path) => [path, readFileSync(path)] as const)).toEqual(before);
        expect(readFileSync(join(repo, ".ai-engineering", "ai-eng.lock"), "utf8")).toInclude(`version = "${VERSION}"`);
      } finally {
        rmSync(inCanon);
        renameSync(dotfiles, inCanon);
        writeFileSync(join(inCanon, linked === "skills" ? "ai-verify" : "", "VERIFICATION-SETUP-GUIDE.md"), shipped);
      }
    });
  }

  // Windows chmod cannot deny a delete, and root ignores the mode: nothing to refuse there.
  test.skipIf(process.platform === "win32" || process.getuid?.() === 0)("F25: a stale page the filesystem will not delete is named for a retry, and the lock is still written", async () => {
    process.chdir(governedRepo("repo-undeletable-stale-page-first"));
    expect((await captured(() => updateMain({ yes: true }))).value).toBe(0);
    const key = "skills/ai-verify/evals/README.md";
    const folder = join(ENG_HOME, "skills", "ai-verify", "evals");
    const page = "# Evals — an outdated page this binary no longer ships\n";
    mkdirSync(folder, { recursive: true });
    writeFileSync(join(ENG_HOME, key), page);
    const recordPath = join(ENG_HOME, "canon-owned.json");
    const record = JSON.parse(readFileSync(recordPath, "utf8")) as { files: Record<string, string> };
    writeFileSync(recordPath, JSON.stringify({ files: { ...record.files, [key]: sha256(page) } }));
    // A repo with nothing installed yet: the run has repo assets to write and a lock to record.
    const repo = governedRepo("repo-undeletable-stale-page");
    const lockPath = join(repo, ".ai-engineering", "ai-eng.lock");
    process.chdir(repo);
    chmodSync(folder, 0o555);

    try {
      const run = await captured(() => updateMain({ yes: true })).finally(() => chmodSync(folder, 0o755));

      expect(run.value).toBe(0);
      expect(run.out).toInclude(`removal refused by the filesystem (a read-only, locked or busy folder), retried by the next ai-eng update: ${key}`);
      expect(run.out).not.toInclude("user file");
      expect(readFileSync(join(ENG_HOME, key), "utf8")).toBe(page);
      expect(readFileSync(lockPath, "utf8")).toInclude(`version = "${VERSION}"`);
    } finally {
      rmSync(folder, { recursive: true, force: true });
    }
  });
});
