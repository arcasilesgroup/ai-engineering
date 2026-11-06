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
import { chmodSync, existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, readlinkSync, realpathSync, renameSync, rmSync, statSync, symlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { basename, delimiter, join, dirname, relative, resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { PassThrough } from "node:stream";
import { syncPlan, updateMain } from "../src/commands/update.ts";
import { planEntries } from "../src/commands/init-shared.ts";
import { carrierFiles } from "../src/surfaces/adapters.ts";
import { mergeSharedText, sha256 } from "../src/install.ts";
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

const DOWN = "\x1b[B";
const ENTER = "\n";
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

/** A repo the binary has already installed into, with one hook patched by hand: the one
 *  state that leaves a decision for the human. */
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
    expect(plan.conflicts).toEqual([]);
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
    expect(plan.conflicts).toEqual([]);
  });

  test("a file we never installed is the user's own, not a conflict to resolve", () => {
    const root = join(SANDBOX, "plan-users");
    mkdirSync(join(root, ".github", "workflows"), { recursive: true });
    writeFileSync(join(root, ".github/workflows/ai-eng-check.yml"), "name: mine\n");
    const plan = syncPlan(entries, root, {});
    // No lock entry: we have no evidence we ever wrote it, so an edit is not ours to judge.
    expect(plan.current).toEqual([".github/workflows/ai-eng-check.yml"]);
    expect(plan.conflicts).toEqual([]);
    expect(plan.updates).toEqual([]);
  });

  test("the recorded hash decides update from conflict", () => {
    const root = join(SANDBOX, "plan-updates");
    const target = ".github/workflows/ai-eng-check.yml";
    mkdirSync(join(root, ".github", "workflows"), { recursive: true });
    const previousOurs = "on: [push]\n# v previous\n";
    writeFileSync(join(root, target), previousOurs);
    const untouched = syncPlan(entries, root, { [target]: sha256(previousOurs) });
    expect(untouched.updates).toEqual([target]);
    expect(untouched.conflicts).toEqual([]);

    // Same lock, one edit by hand: now the human owns the decision.
    writeFileSync(join(root, target), `${previousOurs}# mine too\n`);
    const edited = syncPlan(entries, root, { [target]: sha256(previousOurs) });
    expect(edited.conflicts).toEqual([target]);
    expect(edited.updates).toEqual([]);
  });

  test("a locally edited skill stays protected by its recorded hash", () => {
    const skillPath = "skills/ai-debug/SKILL.md";
    const ours = readFileSync(join(REPO_ROOT, skillPath), "utf8");
    const root = join(SANDBOX, "plan-edited-skill");
    const absolute = join(root, skillPath);
    const localEdit = `${ours}\n# local edit\n`;
    mkdirSync(dirname(absolute), { recursive: true });
    writeFileSync(absolute, localEdit);

    const plan = syncPlan([{ path: skillPath, ours }], root, { [skillPath]: sha256(ours) });

    expect(plan.conflicts).toEqual([skillPath]);
    expect(plan.updates).toEqual([]);
    expect(readFileSync(absolute, "utf8")).toBe(localEdit);
  });

  test("a shared settings file is updated by its merge, never called a conflict", () => {
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

    // A file that is not JSON is left exactly as it is: not ours to rewrite, not a
    // conflict — the surface simply runs unguarded and the installer says so elsewhere.
    writeFileSync(path, "// hand-written settings\n");
    const refused = syncPlan(cursor, root, {});
    expect(refused.updates).toEqual([]);
    expect(refused.conflicts).toEqual([]);
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
    // The local canon still installs completely; unsafe machine-settings mutation is refused.
    expect(first.out).toInclude("~/.claude/settings.json");
    expect(first.out).toInclude("safe machine-settings replacement/removal is unavailable on this platform; left untouched");
    expect(readFileSync(machineSettings, "utf8")).toBe(machineSettingsBefore);
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
    expect(second.out).toInclude("safe machine-settings replacement/removal is unavailable on this platform; left untouched");
    expect(second.out).toInclude("Nothing written");
    // A refused settings registration is never reported as a successful write.
    expect(second.out).not.toInclude("machine carrier · written");
    expect(readFileSync(machineSettings, "utf8")).toBe(machineSettingsBefore);
    expect(readFileSync(lockPath, "utf8")).toBe(bytes);
    expect(statSync(lockPath).mtimeMs).toBe(mtime);
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

  test("update repairs a missing skill resource and preserves edited and user-owned skills", async () => {
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

    const sourceFiles = sourceSkillFiles();
    // A shipped sibling of the edited file: preserving one edited file must not stop the
    // rest of its skill folder from being repaired.
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
    expect(repair.out).toInclude("global canon repaired · local changes kept");
    expect(repair.out).toInclude(`skills/${editedSource.skill}/${editedSource.relativePath} · local change kept`);
    expect(readFileSync(skill)).toEqual(localEdit);
    expect(readFileSync(missingPath)).toEqual(missingSource.bytes);
    expect(readFileSync(missingSiblingPath)).toEqual(missingSibling.bytes);
    expect(readFileSync(userOwnedSkill, "utf8")).toBe("# mine\n");
    expect(readFileSync(userOwnedResource, "utf8")).toBe("my notes\n");
    expect(readFileSync(configPath)).toEqual(Buffer.from(legacyConfig));
    // Machine settings are not part of the canon: the repair neither writes nor removes them.
    expect(readFileSync(machineSettings, "utf8")).toBe(machineSettingsBefore);
    assertAllSkillsInstalled(["my-local-skill"], [`${editedSource.skill}/${editedSource.relativePath}`]);
  });

  test("F20: a user file kept in a shipped skill folder does not make every update re-run the canon repair", async () => {
    rmSync(join(ENG_HOME, "skills"), { recursive: true, force: true });
    const repo = governedRepo("repo-kept-user-file");
    process.chdir(repo);
    expect((await captured(() => updateMain({ yes: true }))).value).toBe(0);
    const notes = join(ENG_HOME, "skills", "ai-debug", "my-notes.md");
    writeFileSync(notes, "mine\n");
    try {
      const second = await captured(() => updateMain({ yes: true }));
      expect(second.value).toBe(0);
      expect(second.out).not.toInclude("re-installed");
      expect(second.out).not.toInclude("global canon repaired");
      expect(second.out).toInclude("global canon ·");
      expect(readFileSync(notes, "utf8")).toBe("mine\n");
    } finally {
      rmSync(notes);
    }
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

  test("--yes keeps a patched hook: nothing written and the lock left as it was", async () => {
    const { shim, lockPath } = await patchedRepo("repo-patched");
    const bytes = readFileSync(lockPath, "utf8");

    const run = await captured(() => updateMain({ yes: true }));
    expect(run.value).toBe(0);
    expect(run.out).toInclude("your patches stay");
    expect(run.out).toInclude("nothing written");
    // The kept file is named, not silently skipped.
    expect(run.out).toInclude("hooks/pre-commit");
    expect(readFileSync(shim, "utf8")).toInclude("# my custom bit");
    // Nothing written means the ownership ledger is not rewritten either: a run that takes
    // no decision leaves the lock exactly as the previous install left it.
    expect(readFileSync(lockPath, "utf8")).toBe(bytes);
  });

  test("a human who takes the new version gets it written over the patch, and the lock follows", async () => {
    const { shim, lockPath } = await patchedRepo("repo-take");
    const stdin = pipeStdin();

    const run = await captured(async () => {
      const running = updateMain();
      await tick(20);
      // The question reaches the human with the file named inside it: one decision, not N.
      stdin.write(DOWN + ENTER); // down: "Take the new version everywhere"
      await tick(60);
      stdin.write(ENTER); // Apply? — the initial value is yes
      return running;
    });

    expect(run.value).toBe(0);
    expect(run.out).toInclude("What wins?");
    expect(run.out).toInclude("1 conflict resolved");
    expect(readFileSync(shim, "utf8")).toBe(entryFor(planEntries(["claude-code"]), ".git/hooks/pre-commit").ours);
    // Taken by an explicit human decision is owned again: the ledger says so, so the next
    // unattended update compares against the version actually on disk.
    expect(readFileSync(lockPath, "utf8")).toInclude('".git/hooks/pre-commit"');
  });

  test("cancelling Apply writes nothing, even after choosing to keep yours", async () => {
    const { repo, shim, lockPath } = await patchedRepo("repo-cancel");
    const bytes = readFileSync(lockPath, "utf8");
    // Something IS pending, or the keep decision short-circuits and Apply is never asked.
    const missing = join(repo, ".github", "workflows", "ai-eng-check.yml");
    rmSync(missing);
    const stdin = pipeStdin();

    const run = await captured(async () => {
      const running = updateMain();
      await tick(20);
      stdin.write(ENTER); // Enter on the first option: keep mine
      await tick(60);
      stdin.write(CANCEL); // ctrl-c at "Apply?"
      return running;
    });

    expect(run.value).toBe(0);
    expect(run.out).toInclude("Nothing written.");
    expect(readFileSync(shim, "utf8")).toInclude("# my custom bit");
    expect(existsSync(missing)).toBe(false); // the pending asset was not written either
    expect(readFileSync(lockPath, "utf8")).toBe(bytes);
  });

  test("cancelling the conflict question writes nothing at all", async () => {
    const { shim, lockPath } = await patchedRepo("repo-conflict-cancel");
    const bytes = readFileSync(lockPath, "utf8");
    const stdin = pipeStdin();

    const run = await captured(async () => {
      const running = updateMain();
      await tick(20);
      stdin.write(CANCEL); // ctrl-c at "What wins?"
      return running;
    });

    expect(run.value).toBe(0);
    expect(run.out).toInclude("Nothing written.");
    // Not one byte of the patched hook, and not one byte of the ledger.
    expect(readFileSync(shim, "utf8")).toInclude("# my custom bit");
    expect(readFileSync(lockPath, "utf8")).toBe(bytes);
  });

  test("carriers that moved out of the repo are swept, and one we cannot claim is kept and named", async () => {
    const repo = governedRepo("repo-moved");
    mkdirSync(join(repo, ".agents", "hooks"), { recursive: true });
    mkdirSync(join(repo, ".pi", "extensions"), { recursive: true });
    writeFileSync(join(repo, ".agents/hooks/ai-eng.ts"), carrierFiles("oh-my-pi", "repo")!.main);
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

  // Windows has no unreadable mode: chmod 0o000 only clears the write bit, so the file stays readable.
  test.skipIf(process.platform === "win32")("F11: an unreadable machine settings file is refused, and the lock is still written", async () => {
    if (process.getuid?.() === 0) return; // root reads a mode-000 file, so there is nothing to refuse
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

  test("F25: a recorded stale page the filesystem will not delete is kept and named, and the lock is still written", async () => {
    // Windows chmod cannot deny a delete, and root ignores the mode: nothing to refuse there.
    if (process.platform === "win32" || process.getuid?.() === 0) return;
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
      expect(run.out).toInclude(`removal refused by the filesystem (a read-only, locked or busy folder), kept and retried by the next ai-eng update: ${key}`);
      expect(run.out).not.toInclude("user file");
      expect(readFileSync(join(ENG_HOME, key), "utf8")).toBe(page);
      expect(readFileSync(lockPath, "utf8")).toInclude(`version = "${VERSION}"`);
    } finally {
      rmSync(folder, { recursive: true, force: true });
    }
  });
});
