// The install side of the carriers, driven in-process so the coverage is the module's and
// not a spawned CLI's: shared settings merges, machine carriers and their machine.json
// record, legacy template cleanup, and artifacts installCanon leaves outside the canon.
//
// Every test owns a machine of its own: AI_ENG_HOME isolates the canon, the mirrors and
// the carriers, and GIT_CONFIG_GLOBAL isolates legacy template restoration.
//
// Settings templates that cannot be reproduced remain refused by mergeSharedText.
// Machine settings are also refused when mutation is needed: portable path-based
// rename/unlink cannot bind the syscall to the identity that was just validated.

import { afterAll, afterEach, beforeAll, describe, expect, spyOn, test } from "bun:test";
import { spawnSync } from "node:child_process";
import { CANON_OWNERSHIP_NAME, embeddedPath, embeddedTemplate, embeddedUnder } from "../src/embed.ts";
import * as fs from "node:fs";
import {
  existsSync,
  lstatSync,
  linkSync,
  mkdirSync,
  mkdtempSync,
  realpathSync,
  readdirSync,
  readFileSync,
  readlinkSync,
  renameSync,
  rmSync,
  symlinkSync,
  writeFileSync,
} from "node:fs";
import { hostname, tmpdir } from "node:os";
import { basename, dirname, join } from "node:path";
import { buildLock, install, lockText, mergeSharedText, parseLock, sha256, stripSharedText, type PlanEntry } from "../src/install.ts";
import {
  SURFACES,
  carrierBase,
  carrierFiles,
  carrierPath,
  installAgentsCanon,
  installCanon,
  installMachineCarriers,
  machineCarrier,
  machineStateFile,
  machineStateLockFile,
  machineStateLockScope,
  mirrorTargets,
  readMachineState,
  repoCarrier,
  removeMachineArtifacts,
  removeMachineCarriers,
  surfaceCanGovern,
  surfaceDialect,
  sweepMovedRepoCarriers,
} from "../src/surfaces/adapters.ts";
import { restoreTemplateDir } from "../src/floor/template.ts";
import { planEntries, refuseLine } from "../src/commands/init-shared.ts";
import { VERSION } from "../src/version.ts";

const SHIM_MARKER = "ai-eng git floor shim";
const LEGACY_SHIMS = ["pre-commit", "commit-msg", "pre-push"] as const;
const CHAIN = "ai-eng chain";

let sandbox: string;
const OWNED_ENV = ["AI_ENG_HOME", "PI_CODING_AGENT_DIR", "GIT_CONFIG_GLOBAL"] as const;
let inherited: Record<string, string | undefined> = {};

type SkillInventory = { name: string; sourceDir: string; files: Map<string, string> };

function skillsInInventory(prefix: string, directOnly = false): SkillInventory[] {
  const assets = [...embeddedUnder(prefix)];
  return assets
    .filter(([path]) => path.endsWith("/SKILL.md"))
    .filter(([path]) => !directOnly || path.slice(prefix.length).split("/").length === 2)
    .map(([skillFile, skillRef]) => {
      const sourceDir = skillFile.slice(0, -"/SKILL.md".length);
      const skillText = readFileSync(embeddedPath(skillRef), "utf8");
      const name = /^name:\s*(\S+)/m.exec(skillText)?.[1];
      if (name === undefined) throw new Error(`skill inventory has no name: ${skillFile}`);
      const files = new Map(
        assets
          .filter(([path]) => path === `${sourceDir}/SKILL.md` || path.startsWith(`${sourceDir}/`))
          .map(([path, ref]) => [path.slice(sourceDir.length + 1), readFileSync(embeddedPath(ref), "utf8")]),
      );
      return { name, sourceDir, files };
    });
}

const allSkillInventory = (): SkillInventory[] => skillsInInventory("skills/", true);

function installedSkillNames(home: string): string[] {
  return readdirSync(join(home, "skills"), { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && !entry.name.startsWith("."))
    .map((entry) => entry.name)
    .sort();
}

function expectInventoryInstalled(home: string, skills: SkillInventory[]): void {
  for (const skill of skills) {
    for (const [relative, content] of skill.files) {
      expect(readFileSync(join(home, "skills", skill.name, relative), "utf8")).toBe(content);
    }
  }
}

function collectTemplateCommands(value: unknown, commands: Set<string>): void {
  if (Array.isArray(value)) {
    for (const entry of value) collectTemplateCommands(entry, commands);
    return;
  }
  if (value === null || typeof value !== "object") return;
  const record = value as Record<string, unknown>;
  if (typeof record["command"] === "string") commands.add(record["command"]);
  for (const entry of Object.values(record)) collectTemplateCommands(entry, commands);
}

beforeAll(() => {
  sandbox = mkdtempSync(join(tmpdir(), "ai-eng-carriers-"));
  inherited = Object.fromEntries(OWNED_ENV.map((key) => [key, process.env[key]]));
});

afterEach(() => {
  for (const key of OWNED_ENV) {
    const value = inherited[key];
    if (value === undefined) delete process.env[key];
    else process.env[key] = value;
  }
});

afterAll(() => {
  rmSync(sandbox, { recursive: true, force: true });
});

function write(path: string, content: string): void {
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, content);
}

function replaceLinkOnChdir(
  parent: string,
  link: string,
  replacement: string,
): { wasTriggered: () => boolean; restore: () => void } {
  const originalChdir = process.chdir.bind(process);
  let wasTriggered = false;
  process.chdir = (directory: string) => {
    if (!wasTriggered && directory === parent) {
      wasTriggered = true;
      renameSync(link, `${link}-before-race`);
      symlinkSync(replacement, link, "dir");
    }
    originalChdir(directory);
  };
  return {
    wasTriggered: () => wasTriggered,
    restore: () => { process.chdir = originalChdir; },
  };
}

/** A machine of its own: the canon home, the mirrors, the carriers and the git floor's
 *  global setting all resolve inside it, and none of them can leak into the next test. */
/** Run `onStateSyscall` once, at the first filesystem mutation that names machine.json —
 *  whichever syscall the writer uses — so a test can race the state commit itself. */
function onMachineStateSyscall(onStateSyscall: () => void): { wasTriggered: () => boolean; restore: () => void } {
  let wasTriggered = false;
  const fire = (...paths: unknown[]) => {
    if (wasTriggered || !paths.some((path) => typeof path === "string" && basename(path) === "machine.json")) return;
    wasTriggered = true;
    onStateSyscall();
  };
  const originalWriteFileSync = fs.writeFileSync;
  const originalUnlinkSync = fs.unlinkSync;
  const originalRenameSync = fs.renameSync;
  const originalLinkSync = fs.linkSync;
  const spies = [
    spyOn(fs, "writeFileSync").mockImplementation((...args) => {
      fire(args[0]);
      return originalWriteFileSync(...args);
    }),
    spyOn(fs, "unlinkSync").mockImplementation((path) => {
      fire(path);
      return originalUnlinkSync(path);
    }),
    spyOn(fs, "renameSync").mockImplementation((from, to) => {
      fire(from, to);
      return originalRenameSync(from, to);
    }),
    spyOn(fs, "linkSync").mockImplementation((existing, created) => {
      fire(existing, created);
      return originalLinkSync(existing, created);
    }),
  ];
  return {
    wasTriggered: () => wasTriggered,
    restore: () => {
      for (const spy of spies) spy.mockRestore();
    },
  };
}

function useHome(name: string): string {
  const dir = join(sandbox, name);
  mkdirSync(join(dir, "skills"), { recursive: true });
  process.env["AI_ENG_HOME"] = dir;
  process.env["GIT_CONFIG_GLOBAL"] = join(dir, "gitconfig");
  delete process.env["PI_CODING_AGENT_DIR"];
  return dir;
}

function setGlobalTemplateDir(dir: string | null): void {
  const args = dir === null ? ["--unset", "init.templateDir"] : ["init.templateDir", dir];
  spawnSync("git", ["config", "--global", ...args], { env: process.env, encoding: "utf8" });
}

function getGlobalTemplateDir(): string | null {
  const result = spawnSync("git", ["config", "--global", "--get", "init.templateDir"], {
    env: process.env,
    encoding: "utf8",
  });
  return result.status === 0 ? result.stdout.trim() : null;
}

function writeLegacyShims(dir: string, names: readonly string[] = LEGACY_SHIMS): void {
  for (const name of names) write(join(dir, "hooks", name), `#!/bin/sh\n# ${SHIM_MARKER}\n`);
}

const byId = (id: string) => SURFACES.find((surface) => surface.id === id)!;

type StopSurface = (typeof SURFACES)[number] & {
  readonly stopHook?: { readonly supported: boolean; readonly event?: string };
};

function emitsStop(surface: StopSurface): boolean {
  return surface.stopHook?.supported === true && typeof surface.stopHook.event === "string";
}

function hasStopHook(content: string, kind: "settings" | "module", event: string): boolean {
  if (kind === "settings") {
    const parsed = JSON.parse(content) as { hooks?: Record<string, unknown> };
    return Array.isArray(parsed.hooks?.[event]);
  }
  return new RegExp(`\\.on\\(\\s*["']${event}["']`).test(content);
}

/** A settings file a person has been keeping: their env, their hook, their indentation. */
const USER_SETTINGS = `{
  "env": {
    "MY_FLAG": "1"
  },
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "my-own-audit.sh",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
`;

describe("legacy git template cleanup", () => {
  test("restore removes only recorded ai-eng shims and prunes empty hooks", () => {
    useHome("tpl-prune");
    const theirs = join(sandbox, "tpl-prune-dir");
    writeLegacyShims(theirs);
    setGlobalTemplateDir(theirs);

    const line = restoreTemplateDir(theirs, null);
    expect(line).toInclude(`kept yours (${theirs})`);
    expect(line).toInclude("3 ai-eng shim(s) removed from it");
    expect(getGlobalTemplateDir()).toBe(theirs);
    expect(existsSync(join(theirs, "hooks"))).toBe(false);
  });

  test("restore leaves a directory we joined holding the user's own hook", () => {
    useHome("tpl-restore-joined");
    const theirs = join(sandbox, "tpl-restore-joined-dir");
    const theirHook = "#!/bin/sh\n# mine\nexit 0\n";
    write(join(theirs, "hooks", "pre-commit"), theirHook);
    writeLegacyShims(theirs, ["commit-msg", "pre-push"]);
    setGlobalTemplateDir(theirs);

    const line = restoreTemplateDir(theirs, null);
    expect(line).toInclude("2 ai-eng shim(s) removed from it");
    expect(readFileSync(join(theirs, "hooks", "pre-commit"), "utf8")).toBe(theirHook);
    for (const shim of ["commit-msg", "pre-push"]) expect(existsSync(join(theirs, "hooks", shim))).toBe(false);
    expect(getGlobalTemplateDir()).toBe(theirs);
  });

  test("restore leaves a changed setting and its old directory alone", () => {
    useHome("tpl-restore-elsewhere");
    const first = join(sandbox, "legacy-owned-template");
    writeLegacyShims(first);
    const third = join(sandbox, "tpl-restore-elsewhere-third");
    mkdirSync(third, { recursive: true });
    setGlobalTemplateDir(third);

    const line = restoreTemplateDir(null, first);
    expect(line).toInclude("left as it is (it is not the one this install set)");
    expect(getGlobalTemplateDir()).toBe(third);
    expect(existsSync(first)).toBe(true);
  });

  test("restore unsets and removes a directory recorded by an older version", () => {
    useHome("tpl-restore-ours");
    const ours = join(sandbox, "legacy-owned-template");
    writeLegacyShims(ours);
    setGlobalTemplateDir(ours);

    const line = restoreTemplateDir(null, ours);
    expect(line).toBe("git init.templateDir unset (it was unset before)");
    expect(getGlobalTemplateDir()).toBeNull();
    expect(existsSync(ours)).toBe(false);
  });

  test("restore: the setting the user moved while we were installed is put back", () => {
    useHome("tpl-restore-previous");
    const a = join(sandbox, "tpl-restore-previous-a");
    const b = join(sandbox, "tpl-restore-previous-b");
    mkdirSync(a, { recursive: true });
    mkdirSync(b, { recursive: true });
    setGlobalTemplateDir(b);

    const line = restoreTemplateDir(a, null);
    expect(line).toBe(`git init.templateDir restored to ${a}`);
    expect(getGlobalTemplateDir()).toBe(a);
  });

  test("restore with nothing set says so instead of inventing a restore", () => {
    useHome("tpl-restore-none");
    expect(restoreTemplateDir(null, null)).toBe("git init.templateDir was not set — nothing to restore");
  });
});

describe("installer: the files a user shares with us", () => {
  test("each refusal is named: not-json, not-object, reformat", () => {
    expect(mergeSharedText('{\n  // my notes\n  "model": "opus"\n}\n', "{}")).toEqual({ refused: "not-json" });
    expect(mergeSharedText('[\n  "not",\n  "an object"\n]\n', "{}")).toEqual({ refused: "not-object" });
    expect(mergeSharedText('"a scalar"\n', "{}")).toEqual({ refused: "not-object" });
    expect(mergeSharedText("null\n", "{}")).toEqual({ refused: "not-object" });
    // Valid JSON this code cannot reproduce byte for byte: the layout is the user's.
    expect(mergeSharedText('{"env":{"A":"1"}}\n', '{"hooks":{}}')).toEqual({ refused: "reformat" });
    expect(stripSharedText('{\n  // my notes\n}\n')).toBeNull();
    expect(stripSharedText('{"hooks":{}}')).toBeNull();
  });

  test("the merge keeps the file's own shape: CRLF and four spaces included", () => {
    const ours = '{"hooks":{"PreToolUse":[{"hooks":[{"command":"ai-eng chain PreToolUse"}]}]}}';
    const crlf = '{\r\n  "env": {\r\n    "A": "1"\r\n  }\r\n}\r\n';
    const merged = mergeSharedText(crlf, ours);
    expect("refused" in merged).toBe(false);
    if ("refused" in merged) return;
    expect(merged.text.replace(/\r\n/g, "")).not.toInclude("\n");
    expect(merged.text).toInclude('\r\n  "hooks": {\r\n');
    // Their block untouched, and out again the file is the one they wrote.
    expect(merged.text).toInclude('  "env": {\r\n    "A": "1"\r\n  },');
    expect(stripSharedText(merged.text)).toBe(crlf);

    const four = mergeSharedText('{\n    "env": {\n        "A": "1"\n    }\n}\n', ours);
    expect("refused" in four).toBe(false);
    if ("refused" in four) return;
    expect(four.text).toInclude('\n    "hooks"');
    expect(four.text.endsWith("}\n")).toBe(true);
  });

  test("install merges into a file the user owns, and the round trip restores it byte for byte", () => {
    const repo = join(sandbox, "install-merge");
    mkdirSync(repo, { recursive: true });
    const settings = join(repo, ".claude", "settings.json");
    write(settings, USER_SETTINGS);
    const entry: PlanEntry = { path: ".claude/settings.json", ours: carrierFiles("claude-code", "machine")!.main, merge: true };

    const first = install(repo, [entry]);
    expect(first.written).toEqual([".claude/settings.json"]);
    const merged = readFileSync(settings, "utf8");
    expect(merged).toInclude("my-own-audit.sh");
    expect(merged).toInclude(`${CHAIN} PreToolUse`);
    // Nothing foreign was reformatted: their block is verbatim, and out again it is the
    // file they had before we existed.
    expect(merged).toInclude('  "env": {\n    "MY_FLAG": "1"\n  }');
    expect(stripSharedText(merged)).toBe(USER_SETTINGS);

    // A second install is not a second copy.
    const second = install(repo, [entry]);
    expect(second.untouched).toEqual([".claude/settings.json"]);
    expect(readFileSync(settings, "utf8")).toBe(merged);
  });

  test("an update replaces the exact managed command but preserves a wrapper containing it", () => {
    const repo = join(sandbox, "update-managed-chain");
    mkdirSync(repo, { recursive: true });
    const settings = join(repo, "settings.json");
    const oldManaged = "ai-eng chain PreToolUse";
    const wrappedUser = `my-audit.sh && ${oldManaged}`;
    write(settings, `${JSON.stringify({
      hooks: { preToolUse: [{ command: oldManaged }, { command: wrappedUser }] },
    }, null, 2)}\n`);
    const updatedCommand = "ai-eng chain PreToolUse --surface cursor";
    const entry: PlanEntry = {
      path: "settings.json",
      ours: `${JSON.stringify({ hooks: { preToolUse: [{ command: updatedCommand }] } }, null, 2)}\n`,
      merge: true,
    };

    expect(install(repo, [entry]).refused).toEqual([]);
    const commands = (JSON.parse(readFileSync(settings, "utf8")) as {
      hooks: { preToolUse: Array<{ command: string }> };
    }).hooks.preToolUse.map(({ command }) => command);
    expect(commands).not.toContain(oldManaged);
    expect(commands).toContain(updatedCommand);
    expect(commands).toContain(wrappedUser);
  });

  test("stripping a managed hook keeps its user's sibling wrapper that mentions ai-eng", () => {
    const wrappedUser = "command -v ai-eng >/dev/null 2>&1 && ai-eng chain PreToolUse || exit 0";
    const current = `${JSON.stringify({
      hooks: {
        PreToolUse: [{
          hooks: [
            { command: wrappedUser },
            { command: "ai-eng chain PreToolUse" },
          ],
        }],
      },
    }, null, 2)}\n`;
    const restored = `${JSON.stringify({
      hooks: {
        PreToolUse: [{
          hooks: [{ command: wrappedUser }],
        }],
      },
    }, null, 2)}\n`;

    expect(stripSharedText(current)).toBe(restored);
  });

  test("recognizes every exact hook command from the embedded settings templates", () => {
    const generatedCommands = new Set<string>();
    for (const path of embeddedUnder("templates/settings.").keys()) {
      if (!path.endsWith(".json.tpl")) continue;
      const settings = JSON.parse(embeddedTemplate(path.slice("templates/".length))) as { hooks?: unknown };
      collectTemplateCommands(settings.hooks, generatedCommands);
    }

    expect(generatedCommands.size).toBeGreaterThan(0);
    for (const command of generatedCommands) {
      const current = `${JSON.stringify({
        hooks: { PreToolUse: [{ hooks: [{ command }] }] },
      }, null, 2)}\n`;
      expect(stripSharedText(current)).toBe("{}\n");
    }
  });

  test("install refuses a settings file it cannot merge, and leaves every byte of it", () => {
    const repo = join(sandbox, "install-refused");
    mkdirSync(repo, { recursive: true });
    const settings = join(repo, "settings.json");
    const comments = '{\n  // mine\n  "model": "opus"\n}\n';
    write(settings, comments);
    const entry: PlanEntry = { path: "settings.json", ours: '{"hooks":{}}', merge: true };

    expect(install(repo, [entry])).toEqual({
      written: [],
      untouched: [],
      conflicts: [],
      refused: [{ path: "settings.json", reason: "not-json" }],
    });
    expect(readFileSync(settings, "utf8")).toBe(comments);
  });

  test("install: a file already ours is a no-op, and one we never installed is the user's", () => {
    const repo = join(sandbox, "install-noop");
    mkdirSync(repo, { recursive: true });
    const target = join(repo, "hooks.json");
    const entry: PlanEntry = { path: "hooks.json", ours: '{"v":2}\n' };
    write(target, entry.ours);
    expect(install(repo, [entry])).toEqual({ written: [], untouched: ["hooks.json"], conflicts: [], refused: [] });

    const theirs = '{"hooks":{"PreToolUse":[{"command":"my-wrapper.sh -- ai-eng chain"}]}}\n';
    write(target, theirs);
    expect(install(repo, [entry], () => null)).toEqual({ written: [], untouched: ["hooks.json"], conflicts: [], refused: [] });
    expect(readFileSync(target, "utf8")).toBe(theirs);
  });

  test("install: the recorded version updates, an edit conflicts, and force is the only way over it", () => {
    const repo = join(sandbox, "install-three-way");
    mkdirSync(repo, { recursive: true });
    const target = join(repo, "hooks.json");
    const entry: PlanEntry = { path: "hooks.json", ours: '{"v":2}\n' };
    const recorded = '{"v":1.5}\n';
    const previousOurs = (): string => `sha256:${sha256(recorded)}`;

    write(target, recorded);
    expect(install(repo, [entry], previousOurs).written).toEqual(["hooks.json"]);
    expect(readFileSync(target, "utf8")).toBe(entry.ours);

    const edited = '{"v":1}\n';
    write(target, edited);
    expect(install(repo, [entry], previousOurs)).toEqual({
      written: [],
      untouched: [],
      conflicts: ["hooks.json"],
      refused: [],
    });
    expect(readFileSync(target, "utf8")).toBe(edited);

    expect(install(repo, [entry], previousOurs, () => true).written).toEqual(["hooks.json"]);
    expect(readFileSync(target, "utf8")).toBe(entry.ours);
  });

  test("install creates a missing file, parents and all", () => {
    const repo = join(sandbox, "install-fresh");
    mkdirSync(repo, { recursive: true });
    const entry: PlanEntry = { path: join("deep", "nested", "hooks.json"), ours: "{}\n" };
    expect(install(repo, [entry]).written).toEqual([entry.path]);
    expect(readFileSync(join(repo, entry.path), "utf8")).toBe("{}\n");
  });

  test("the lock: assets by sha256, the contract fields carried, an injected base_sha refused", () => {
    const entries: PlanEntry[] = [{ path: ".cursor/hooks.json", ours: '{"version":1}\n' }];
    const bare = buildLock(entries, "2.2.0");
    expect(bare).toEqual({ version: "2.2.0", assets: { ".cursor/hooks.json": sha256('{"version":1}\n') } });

    const base_sha = "a".repeat(40);
    const lock = buildLock(entries, "2.2.0", { spec_sha256: "abc123", base_sha });
    const text = lockText(lock);
    expect(text).toInclude('spec_sha256 = "abc123"');
    expect(text).toInclude(`base_sha = "${base_sha}"`);
    expect(text).toInclude(`".cursor/hooks.json" = "${sha256('{"version":1}\n')}"`);
    expect(text).toInclude("[assets]");
    expect(parseLock(text)).toEqual(lock);

    // A commit id, or nothing: a value beginning with `-` reaches `git diff` as an option.
    const injected = parseLock('version = "1"\nbase_sha = "--output=/tmp/pwn"\n[assets]\n"a" = "b"\n');
    expect(injected.base_sha).toBeUndefined();
    expect(injected.assets).toEqual({ a: "b" });
    expect(parseLock("# an empty lock\n")).toEqual({ version: "", assets: {} });
  });
});

describe("carriers on the machine", () => {
  test("install registers Stop only on surfaces declared to emit it", () => {
    useHome("machine-stop-scope");
    const surfaces = SURFACES as StopSurface[];
    expect(surfaces.some(emitsStop)).toBe(true);
    expect(surfaces.some((surface) => !emitsStop(surface))).toBe(true);

    const machineSurfaces = surfaces.filter((surface) => machineCarrier(surface) !== null);
    const report = installMachineCarriers(machineSurfaces.map((surface) => surface.id));
    const settingsSurfaces = machineSurfaces.filter((surface) => machineCarrier(surface)?.kind === "settings");
    expect(report.refused).toEqual(settingsSurfaces.map((surface) => ({
      path: `~/${machineCarrier(surface)!.path}`,
      reason: "identity-bound-settings-mutation-unavailable",
    })));
    for (const surface of machineSurfaces) {
      const placement = machineCarrier(surface)!;
      if (placement.kind === "settings") {
        expect(existsSync(carrierPath(placement))).toBe(false);
        continue;
      }
      const content = readFileSync(carrierPath(placement), "utf8");
      expect(hasStopHook(content, placement.kind, (surface as StopSurface).stopHook?.event ?? "Stop")).toBe(emitsStop(surface));
    }

    const repoRoot = join(sandbox, "repo-stop-scope");
    mkdirSync(repoRoot, { recursive: true });
    const repoSurfaces = surfaces.filter((surface) => repoCarrier(surface) !== null);
    expect(install(repoRoot, planEntries(repoSurfaces.map((surface) => surface.id))).refused).toEqual([]);
    for (const surface of repoSurfaces) {
      const placement = repoCarrier(surface)!;
      const content = readFileSync(join(repoRoot, placement.path), "utf8");
      expect(hasStopHook(content, placement.kind, (surface as StopSurface).stopHook?.event ?? "Stop")).toBe(emitsStop(surface));
    }

    const cursor = byId("cursor") as StopSurface;
    expect(cursor.stopHook?.event).toBe("stop");
    const cursorHooks = JSON.parse(carrierFiles("cursor", "repo")!.main) as {
      hooks: { stop: Array<{ command: string }> };
    };
    expect(cursorHooks.hooks.stop[0]?.command).toBe("ai-eng chain Stop --surface cursor");
  });

  test("an update refuses a machine settings rewrite and keeps the user's hook", () => {
    const base = useHome("machine-update-old-gate");
    const settings = join(base, ".claude", "settings.json");
    const oldPythonGate = '[ -f "$HOME/.ai-engineering/scripts/checkpoint-gate.py" ] || exit 0; python3 "$HOME/.ai-engineering/scripts/checkpoint-gate.py" --surface claude-code';
    const wrappedUserHook = `my-own-audit.sh && ${oldPythonGate}`;
    write(
      settings,
      `${JSON.stringify({
        env: { MY_FLAG: "1" },
        hooks: {
          PreToolUse: [
            { matcher: "Write|Edit|Task|Bash", hooks: [{ type: "command", command: oldPythonGate, timeout: 5 }] },
            { matcher: "Bash", hooks: [{ type: "command", command: wrappedUserHook, timeout: 5 }] },
            { matcher: "Bash", hooks: [{ type: "command", command: "my-own-audit.sh", timeout: 5 }] },
          ],
        },
      }, null, 2)}\n`,
    );

    const before = readFileSync(settings);
    expect(installMachineCarriers(["claude-code"]).refused).toEqual([{
      path: "~/.claude/settings.json",
      reason: "identity-bound-settings-mutation-unavailable",
    }]);
    expect(readFileSync(settings)).toEqual(before);
  });

  test("carrierBase follows the host's agent dir env, and carrierPath rebases onto it", () => {
    const base = useHome("carrier-base");
    const omp = machineCarrier(byId("oh-my-pi"))!;
    const agentDir = join(sandbox, "carrier-base-omp");
    process.env["PI_CODING_AGENT_DIR"] = agentDir;
    expect(carrierBase(omp)).toBe(agentDir);
    // The host's agent dir IS the `.omp/agent` the path names: it is not repeated.
    expect(carrierPath(omp)).toBe(join(agentDir, "hooks", "pre", "ai-eng.ts"));
    expect(carrierPath(omp, omp.chain)).toBe(join(agentDir, "hooks", "pre", ".ai-eng-chain.ts"));

    // An empty override is not a relocation, it is an unset variable.
    process.env["PI_CODING_AGENT_DIR"] = "";
    expect(carrierBase(omp)).toBe(base);
    expect(carrierPath(omp)).toBe(join(base, ".omp", "agent", "hooks", "pre", "ai-eng.ts"));

    // A host with no agent dir env lands on the machine base.
    const claude = machineCarrier(byId("claude-code"))!;
    expect(carrierBase(claude)).toBe(base);
    expect(carrierPath(claude)).toBe(join(base, ".claude", "settings.json"));
    // The chain of a carrier that has none resolves to the entry itself.
    expect(carrierPath(claude, undefined)).toBe(join(base, ".claude", "settings.json"));
  });

  test("surfaceDialect falls back to claude; surfaceCanGovern refuses a host with nowhere for a guard", () => {
    expect(surfaceDialect("cursor")).toBe("cursor");
    expect(surfaceDialect("codex")).toBe("codex");
    expect(surfaceDialect("copilot-cli")).toBe("copilot");
    // In-process hosts run the chain themselves: no dialect, so claude's is the default.
    expect(surfaceDialect("oh-my-pi")).toBe("claude");
    expect(surfaceDialect("pi")).toBe("claude");
    expect(surfaceDialect("no-such-host")).toBe("claude");
    expect(surfaceDialect(undefined)).toBe("claude");

    expect(surfaceCanGovern(byId("codex"))).toBe(true);
    expect(surfaceCanGovern(byId("opencode"))).toBe(true); // deny: "throw"
    expect(surfaceCanGovern(byId("zed"))).toBe(false); // denies through its own permissions, never by running us
  });

  test("installMachineCarriers: missing and changed settings fail closed, garbage remains refused", () => {
    const base = useHome("machine-install");
    const carrier = join(base, ".claude", "settings.json");

    expect(installMachineCarriers(["claude-code", "zed", "no-such-host"])).toEqual({
      written: [],
      untouched: [],
      refused: [{
        path: "~/.claude/settings.json",
        reason: "identity-bound-settings-mutation-unavailable",
      }],
    });
    expect(existsSync(carrier)).toBe(false);
    const state = readMachineState();
    expect(state.version).toBe(VERSION);
    expect(state.carriers["claude-code"]).toBeUndefined();

    // A settings file belongs to the person; the machine carrier is not written into it.
    write(carrier, USER_SETTINGS);
    const originalBytes = readFileSync(carrier);
    expect(installMachineCarriers(["claude-code"]).refused).toEqual([{
      path: "~/.claude/settings.json",
      reason: "identity-bound-settings-mutation-unavailable",
    }]);
    expect(readFileSync(carrier)).toEqual(originalBytes);

    // Not JSON: still refused with the parser's specific reason.
    const comments = '{\n  // my notes\n  "model": "opus"\n}\n';
    write(carrier, comments);
    const refused = installMachineCarriers(["claude-code"]);
    expect(refused.refused).toEqual([{ path: "~/.claude/settings.json", reason: "not-json" }]);
    expect(refused.written).toEqual([]);
    expect(readFileSync(carrier, "utf8")).toBe(comments);
  });

  test("I73: machine settings updates fail closed and preserve the original bytes", () => {
    const base = useHome("machine-write-failure");
    const settings = join(base, ".claude", "settings.json");
    write(settings, USER_SETTINGS);
    const originalBytes = readFileSync(settings);
    const originalRenameSync = fs.renameSync;
    let didAttemptSettingsRename = false;
    const renameSpy = spyOn(fs, "renameSync").mockImplementation((...args) => {
      if (String(args[1]) === settings) didAttemptSettingsRename = true;
      return originalRenameSync(...args);
    });

    try {
      expect(installMachineCarriers(["claude-code"]).refused).toEqual([{
        path: "~/.claude/settings.json",
        reason: "identity-bound-settings-mutation-unavailable",
      }]);
    } finally {
      renameSpy.mockRestore();
    }

    expect(didAttemptSettingsRename).toBe(false);
    expect(readFileSync(settings).equals(originalBytes)).toBe(true);
  });

  test("I74: settings aliases to machine.json are refused without changing or deleting either path", () => {
    for (const aliasType of ["symlink", "hard-link"] as const) {
      const base = useHome(`machine-state-alias-${aliasType}`);
      const statePath = machineStateFile();
      const settings = join(base, ".claude", "settings.json");
      const originalBytes = Buffer.from('{\n  "version": "user-owned",\n  "carriers": {}\n}\n');
      writeFileSync(statePath, originalBytes);
      mkdirSync(dirname(settings), { recursive: true });
      if (aliasType === "symlink") symlinkSync("../machine.json", settings);
      else linkSync(statePath, settings);

      const linkText = aliasType === "symlink" ? readlinkSync(settings) : null;
      const installed = installMachineCarriers(["claude-code"]);
      expect(installed.refused).toEqual([{
        path: "~/.claude/settings.json",
        reason: "identity-bound-settings-mutation-unavailable",
      }]);
      expect(refuseLine(installed.refused[0]!)).toBe(
        "⚠ ~/.claude/settings.json — safe machine-settings replacement/removal is unavailable on this platform; left untouched",
      );
      expect(readFileSync(statePath)).toEqual(originalBytes);

      expect(removeMachineCarriers(["claude-code"])).toEqual({
        lines: [],
        refused: [{ path: "~/.claude/settings.json", reason: "identity-bound-settings-mutation-unavailable" }],
      });
      expect(existsSync(statePath)).toBe(true);
      expect(readFileSync(statePath)).toEqual(originalBytes);
      expect(existsSync(settings)).toBe(true);
      if (linkText !== null) expect(readlinkSync(settings)).toBe(linkText);
      else expect(lstatSync(settings).ino).toBe(lstatSync(statePath).ino);
    }
  });

  test("machine state is preserved when an unselected settings surface aliases it", () => {
    for (const aliasType of ["symlink", "hard-link"] as const) {
      const base = useHome(`unselected-machine-state-alias-${aliasType}`);
      const statePath = machineStateFile();
      const settings = join(base, ".codex", "hooks.json");
      const originalBytes = Buffer.from('{"version":"prior","carriers":{"claude-code":"owned"}}\n');
      writeFileSync(statePath, originalBytes);
      mkdirSync(dirname(settings), { recursive: true });
      if (aliasType === "symlink") symlinkSync("../machine.json", settings);
      else linkSync(statePath, settings);

      const installed = installMachineCarriers(["claude-code"]);
      expect(installed.refused).toContainEqual({
        path: "~/.codex/hooks.json",
        reason: "identity-bound-settings-mutation-unavailable",
      });
      expect(readFileSync(statePath)).toEqual(originalBytes);

      expect(removeMachineCarriers(["claude-code"]).refused.map((entry) => entry.path)).toContain("~/.codex/hooks.json");
      expect(existsSync(statePath)).toBe(true);
      expect(readFileSync(statePath)).toEqual(originalBytes);
      expect(existsSync(settings)).toBe(true);
    }
  });

  test("an unselected settings alias added after validation blocks machine-state mutation", () => {
    for (const operation of ["install", "remove"] as const) {
      for (const aliasType of ["symlink", "hard-link"] as const) {
        const base = useHome(`machine-state-alias-race-${operation}-${aliasType}`);
        const statePath = machineStateFile();
        const selectedSettings = join(base, ".claude", "settings.json");
        const unselectedSettings = join(base, ".codex", "hooks.json");
        const moduleCarrier = join(base, ".config", "opencode", "plugins", "ai-eng.ts");
        const originalBytes = Buffer.from('{"version":"prior","carriers":{"claude-code":"owned"}}\n');
        write(selectedSettings, USER_SETTINGS);
        mkdirSync(dirname(unselectedSettings), { recursive: true });
        writeFileSync(statePath, originalBytes);

        let didAddAlias = false;
        const addAlias = () => {
          if (!didAddAlias) {
            if (aliasType === "symlink") symlinkSync("../machine.json", unselectedSettings);
            else linkSync(statePath, unselectedSettings);
            didAddAlias = true;
          }
        };
        if (operation === "install") {
          const originalOpenSync = fs.openSync;
          const writeSpy = spyOn(fs, "openSync").mockImplementation((...args) => {
            if (String(args[0]) === moduleCarrier) addAlias();
            return originalOpenSync(...args);
          });
          try {
            expect(installMachineCarriers(["claude-code", "opencode"]).refused).toContainEqual({
              path: "~/.codex/hooks.json",
              reason: "identity-bound-settings-mutation-unavailable",
            });
          } finally {
            writeSpy.mockRestore();
          }
        } else {
          mkdirSync(dirname(moduleCarrier), { recursive: true });
          writeFileSync(moduleCarrier, carrierFiles("opencode", "machine")!.main);
          const originalUnlinkSync = fs.unlinkSync;
          const unlinkSpy = spyOn(fs, "unlinkSync").mockImplementation((path) => {
            if (String(path) === moduleCarrier || String(path) === basename(moduleCarrier)) addAlias();
            return originalUnlinkSync(path);
          });
          try {
            expect(removeMachineCarriers(["claude-code", "opencode"]).refused.map((entry) => entry.path)).toContain("~/.codex/hooks.json");
          } finally {
            unlinkSpy.mockRestore();
          }
        }

        expect(didAddAlias).toBe(true);
        expect(readFileSync(statePath)).toEqual(originalBytes);
        expect(existsSync(unselectedSettings)).toBe(true);
      }
    }
  });

  test("F8: a settings alias made at the machine-state syscall leaves both paths' bytes untouched", () => {
    for (const operation of ["install", "remove"] as const) {
      for (const aliasType of ["symlink", "hard-link"] as const) {
        const base = useHome(`machine-state-syscall-alias-${operation}-${aliasType}`);
        const statePath = machineStateFile();
        const unselectedSettings = join(base, ".codex", "hooks.json");
        const originalBytes = Buffer.from('{"version":"prior","carriers":{"opencode":"owned"}}\n');
        writeFileSync(statePath, originalBytes);
        mkdirSync(dirname(unselectedSettings), { recursive: true });
        const race = onMachineStateSyscall(() => {
          if (aliasType === "symlink") symlinkSync("../machine.json", unselectedSettings);
          else linkSync(statePath, unselectedSettings);
        });

        let refusedPaths: string[];
        try {
          refusedPaths = operation === "install"
            ? installMachineCarriers(["opencode"]).refused.map((entry) => entry.path)
            : removeMachineCarriers(["opencode"]).refused.map((entry) => entry.path);
        } finally {
          race.restore();
        }

        expect(race.wasTriggered()).toBe(true);
        expect(readFileSync(statePath)).toEqual(originalBytes);
        expect(readFileSync(unselectedSettings)).toEqual(originalBytes);
        expect(refusedPaths).toEqual([statePath]);
        expect(readdirSync(base).filter((name) => name.startsWith(".machine.json."))).toEqual([]);
      }
    }
  });

  test("F8: a symlinked machine.json is never written or removed through", () => {
    for (const operation of ["install", "remove"] as const) {
      const base = useHome(`machine-state-symlinked-${operation}`);
      const statePath = machineStateFile();
      const userFile = join(base, "user-state.json");
      const userBytes = Buffer.from('{"version":"user","carriers":{}}\n');
      writeFileSync(userFile, userBytes);
      symlinkSync("user-state.json", statePath);

      if (operation === "install") {
        const refused = installMachineCarriers(["opencode"]).refused;
        expect(refused).toEqual([{ path: statePath, reason: "machine-state-identity-unverified" }]);
        expect(refuseLine(refused[0]!)).toBe(
          `⚠ ${statePath} — machine state is linked, changed, or shared with another path; left untouched`,
        );
      } else {
        expect(removeMachineCarriers(["opencode"]).refused).toEqual([{ path: statePath, reason: "machine-state-identity-unverified" }]);
      }
      expect(lstatSync(statePath).isSymbolicLink()).toBe(true);
      expect(readlinkSync(statePath)).toBe("user-state.json");
      expect(readFileSync(userFile)).toEqual(userBytes);
    }
  });

  test("a settings replacement at the commit boundary is preserved because no identity-bound syscall runs", () => {
    const base = useHome("machine-commit-boundary");
    const settings = join(base, ".claude", "settings.json");
    write(settings, USER_SETTINGS);
    const replacementBytes = Buffer.from('{"model":"replacement"}\n');
    const originalWriteFileSync = fs.writeFileSync;
    const originalUnlinkSync = fs.unlinkSync;
    const originalRenameSync = fs.renameSync;
    const originalLinkSync = fs.linkSync;
    let replacedBeforeInstallReturned = false;
    let replacedBeforeRemovalReturned = false;
    let didAttemptSettingsPathMutation = false;
    const isStateSyscall = (...paths: unknown[]) =>
      paths.some((path) => typeof path === "string" && basename(path) === "machine.json");
    const writeFileSpy = spyOn(fs, "writeFileSync").mockImplementation((...args) => {
      if (String(args[0]) === settings) didAttemptSettingsPathMutation = true;
      return originalWriteFileSync(...args);
    });
    const linkSpy = spyOn(fs, "linkSync").mockImplementation((existing, created) => {
      if (String(created) === settings) didAttemptSettingsPathMutation = true;
      if (!replacedBeforeInstallReturned && isStateSyscall(created)) {
        replacedBeforeInstallReturned = true;
        originalRenameSync(settings, `${settings}.before-install`);
        originalWriteFileSync(settings, replacementBytes);
      }
      return originalLinkSync(existing, created);
    });
    const unlinkSpy = spyOn(fs, "unlinkSync").mockImplementation((path, ...args) => {
      if (String(path) === settings) didAttemptSettingsPathMutation = true;
      return originalUnlinkSync(path, ...args);
    });
    const renameSpy = spyOn(fs, "renameSync").mockImplementation((...args) => {
      if (String(args[1]) === settings) didAttemptSettingsPathMutation = true;
      if (!replacedBeforeRemovalReturned && isStateSyscall(args[0])) {
        replacedBeforeRemovalReturned = true;
        originalRenameSync(settings, `${settings}.before-removal`);
        originalWriteFileSync(settings, Buffer.from('{"model":"second replacement"}\n'));
      }
      return originalRenameSync(...args);
    });

    try {
      expect(installMachineCarriers(["claude-code"]).refused).toHaveLength(1);
      expect(readFileSync(settings)).toEqual(replacementBytes);
      expect(removeMachineCarriers(["claude-code"]).refused).toEqual([{ path: "~/.claude/settings.json", reason: "identity-bound-settings-mutation-unavailable" }]);
    } finally {
      renameSpy.mockRestore();
      unlinkSpy.mockRestore();
      linkSpy.mockRestore();
      writeFileSpy.mockRestore();
    }

    expect(replacedBeforeInstallReturned).toBe(true);
    expect(replacedBeforeRemovalReturned).toBe(true);
    expect(didAttemptSettingsPathMutation).toBe(false);
    expect(readFileSync(settings)).toEqual(Buffer.from('{"model":"second replacement"}\n'));
  });

  test("carrierFiles: the machine copy and the repo copy are different files, and the in-process hosts ship a bundle", () => {
    // Copilot's CLI combines repo and machine hooks and fails CLOSED on a missing binary,
    // so the machine template guards the call; the repo copy has no such guard.
    const cli = carrierFiles("copilot-cli", "machine")!;
    expect(cli.main).toInclude("command -v ai-eng");
    expect(cli.main).toInclude("--surface copilot-cli");
    expect(cli.main).toInclude('"preToolUse"');
    expect(cli.main).toInclude('"postToolUse"');
    expect(cli.chain).toBeNull();
    const repo = carrierFiles("copilot-cli", "repo")!;
    expect(repo.main).not.toInclude("command -v ai-eng");
    expect(repo.main).toInclude('"preToolUse"');
    expect(repo.main).toInclude('"postToolUse"');

    // An in-process host is imported by the host itself: the chain bundle must sit beside
    // the entry, and the entry imports it by name.
    const pi = carrierFiles("pi", "machine")!;
    expect(pi.chain).toInclude("ai-eng-chain");
    expect(pi.main).toInclude('from "./.ai-eng-chain.ts"');
    expect(carrierFiles("cursor", "repo")!.main).toInclude('"failClosed": true');
  });

  test("installMachineCarriers: a machine settings definition is not written without identity-bound replacement", () => {
    const base = useHome("machine-current");
    const carrier = join(base, ".codex", "hooks.json");
    expect(installMachineCarriers(["codex"]).refused).toEqual([{
      path: "~/.codex/hooks.json",
      reason: "identity-bound-settings-mutation-unavailable",
    }]);
    expect(existsSync(carrier)).toBe(false);
  });

  test("installMachineCarriers: a module carrier is written whole, with its chain bundle beside it", () => {
    const base = useHome("machine-module");
    const files = carrierFiles("opencode", "machine")!;
    expect(installMachineCarriers(["opencode"]).written).toEqual(["~/.config/opencode/plugins/ai-eng.ts"]);

    const main = join(base, ".config", "opencode", "plugins", "ai-eng.ts");
    const chain = join(base, ".config", "opencode", "plugins", "ai-eng-chain.ts");
    expect(readFileSync(main, "utf8")).toBe(files.main);
    expect(readFileSync(chain, "utf8")).toBe(files.chain!);
    expect(readMachineState().carriers["opencode"]).toBe(sha256(files.main));

    // Ours whole means ours whole: a reinstall never merges into it, and a file a hand
    // edits is written over. Bytes already ours are not a write at all — the count is
    // what update's report prints, and a no-op reported as a write is a lie the frame
    // cannot afford (cli-ux-14).
    writeFileSync(main, `${files.main}\n// patched by hand\n`);
    expect(installMachineCarriers(["opencode"]).written).toEqual(["~/.config/opencode/plugins/ai-eng.ts"]);
    expect(readFileSync(main, "utf8")).toBe(files.main);

    expect(installMachineCarriers(["opencode"])).toEqual({ written: [], untouched: ["~/.config/opencode/plugins/ai-eng.ts"], refused: [] });
    // A missing chain bundle beside an identical main is still a write: half a carrier is
    // not current.
    rmSync(chain);
    expect(installMachineCarriers(["opencode"]).written).toEqual(["~/.config/opencode/plugins/ai-eng.ts"]);
    expect(readFileSync(chain, "utf8")).toBe(files.chain!);
  });

  test("installMachineCarriers honors PI_CODING_AGENT_DIR: the host's directory, not the default one", () => {
    const base = useHome("machine-agentdir");
    const agentDir = join(sandbox, "machine-agentdir-omp");
    process.env["PI_CODING_AGENT_DIR"] = agentDir;

    expect(installMachineCarriers(["oh-my-pi"]).written).toEqual(["~/.omp/agent/hooks/pre/ai-eng.ts"]);
    expect(readFileSync(join(agentDir, "hooks", "pre", "ai-eng.ts"), "utf8")).toBe(carrierFiles("oh-my-pi", "machine")!.main);
    expect(existsSync(join(agentDir, "hooks", "pre", ".ai-eng-chain.ts"))).toBe(true);
    // A carrier the host would never read is the bug this table exists to end.
    expect(existsSync(join(base, ".omp"))).toBe(false);
  });

  test("removeMachineCarriers: modules and files that held only our entries go whole", () => {
    const base = useHome("machine-remove");
    installMachineCarriers(["opencode"]);
    const plugin = join(base, ".config", "opencode", "plugins", "ai-eng.ts");
    const bundle = join(base, ".config", "opencode", "plugins", "ai-eng-chain.ts");
    // A settings carrier holding our entry and nothing else, in a shape this code can
    // reproduce: out it comes at uninstall, whole.
    const carrier = join(base, ".claude", "settings.json");
    write(
      carrier,
      `${JSON.stringify({ hooks: { PreToolUse: [{ hooks: [{ command: `${CHAIN} PreToolUse` }] }] } }, null, 2)}\n`,
    );

    const swept = removeMachineCarriers(["claude-code", "opencode", "zed", "no-such-host"]);
    expect(swept.refused).toEqual([{ path: "~/.claude/settings.json", reason: "identity-bound-settings-mutation-unavailable" }]);
    expect(swept.lines).toEqual([
      "~/.config/opencode/plugins/ai-eng.ts removed",
    ]);
    expect(existsSync(carrier)).toBe(true);
    expect(existsSync(plugin)).toBe(false);
    expect(existsSync(bundle)).toBe(false);
    // Nothing left to remember: an empty machine.json would be a stale record.
    expect(existsSync(machineStateFile())).toBe(false);
  });

  test("removeMachineCarriers: an existing user's settings file is refused unchanged", () => {
    const base = useHome("machine-remove-keeps");
    const carrier = join(base, ".claude", "settings.json");
    write(carrier, USER_SETTINGS);

    const swept = removeMachineCarriers(["claude-code"]);
    expect(swept.refused).toEqual([{ path: "~/.claude/settings.json", reason: "identity-bound-settings-mutation-unavailable" }]);
    expect(swept.lines).toEqual([]);
    expect(readFileSync(carrier, "utf8")).toBe(USER_SETTINGS);
  });

  test("removeMachineCarriers: a file it cannot rewrite is refused by name, and left alone", () => {
    const base = useHome("machine-remove-refused");
    const carrier = join(base, ".claude", "settings.json");
    const comments = '{\n  // mine\n  "model": "opus"\n}\n';
    write(carrier, comments);

    expect(removeMachineCarriers(["claude-code"])).toEqual({ lines: [], refused: [{ path: "~/.claude/settings.json", reason: "identity-bound-settings-mutation-unavailable" }] });
    expect(readFileSync(carrier, "utf8")).toBe(comments);
  });

  test("F11: an unreadable, dangling or directory settings path is refused, not thrown, and left as it was", () => {
    const unreadable = { path: "~/.claude/settings.json", reason: "settings-unreadable" };
    const kinds = process.getuid?.() === 0 ? (["dangling", "directory"] as const) : (["unreadable", "dangling", "directory"] as const);
    for (const kind of kinds) {
      const base = useHome(`machine-settings-${kind}`);
      const settings = join(base, ".claude", "settings.json");
      const danglingTarget = join(base, "dotfiles", "settings.json");
      mkdirSync(dirname(settings), { recursive: true });
      if (kind === "unreadable") {
        writeFileSync(settings, USER_SETTINGS);
        fs.chmodSync(settings, 0o000);
      }
      if (kind === "dangling") symlinkSync(danglingTarget, settings);
      if (kind === "directory") mkdirSync(settings);

      let installed: ReturnType<typeof installMachineCarriers>;
      let removed: ReturnType<typeof removeMachineCarriers>;
      try {
        installed = installMachineCarriers(["claude-code"]);
        removed = removeMachineCarriers(["claude-code"]);
      } finally {
        if (kind === "unreadable") fs.chmodSync(settings, 0o644);
      }

      expect(installed.refused).toEqual([unreadable]);
      expect(refuseLine(installed.refused[0]!)).toBe(
        "⚠ ~/.claude/settings.json — unreadable, a dangling link, not a regular file, or changing while read; left untouched",
      );
      expect(removed).toEqual({ lines: [], refused: [unreadable] });
      if (kind === "unreadable") expect(readFileSync(settings, "utf8")).toBe(USER_SETTINGS);
      if (kind === "dangling") {
        expect(readlinkSync(settings)).toBe(danglingTarget);
        expect(existsSync(danglingTarget)).toBe(false);
      }
      if (kind === "directory") expect(lstatSync(settings).isDirectory()).toBe(true);
      expect(existsSync(machineStateFile())).toBe(false);
    }
  });

  test("F13: a second run inside the commit window is refused, and a state that appears there wins without losing ours", () => {
    const base = useHome("machine-state-concurrent");
    const statePath = machineStateFile();
    const original = Buffer.from(
      `${JSON.stringify({ version: "prior", carriers: { pi: "owned" }, templateDir: { previous: "/theirs", ours: null } }, null, 2)}\n`,
    );
    const privateNames = () => readdirSync(base).filter((name) => name.startsWith(".machine.json."));
    const duringClaim = (action: () => void) => {
      const originalRenameSync = fs.renameSync;
      let wasTriggered = false;
      const spy = spyOn(fs, "renameSync").mockImplementation((from, to) => {
        originalRenameSync(from, to);
        if (!wasTriggered && String(to).endsWith(".claim")) {
          wasTriggered = true;
          action();
        }
      });
      return { wasTriggered: () => wasTriggered, restore: () => spy.mockRestore() };
    };

    writeFileSync(statePath, original);
    let second: ReturnType<typeof installMachineCarriers> | undefined;
    const concurrentRun = duringClaim(() => { second = installMachineCarriers(["opencode"]); });
    let first: ReturnType<typeof installMachineCarriers>;
    try {
      first = installMachineCarriers(["opencode"]);
    } finally {
      concurrentRun.restore();
    }
    expect(concurrentRun.wasTriggered()).toBe(true);
    expect(second!.refused).toEqual([{ path: machineStateLockFile(), reason: "machine-state-busy" }]);
    expect(first.refused).toEqual([]);
    const committed = readMachineState();
    expect(committed.carriers).toEqual({ pi: "owned", opencode: sha256(carrierFiles("opencode", "machine")!.main) });
    expect(committed.templateDir).toEqual({ previous: "/theirs", ours: null });
    expect(privateNames()).toEqual([]);

    writeFileSync(statePath, original);
    const foreign = Buffer.from('{"version":"written meanwhile","carriers":{}}\n');
    const appearingState = duringClaim(() => writeFileSync(statePath, foreign));
    let refused: ReturnType<typeof installMachineCarriers>["refused"];
    try {
      refused = installMachineCarriers(["opencode"]).refused;
    } finally {
      appearingState.restore();
    }
    expect(appearingState.wasTriggered()).toBe(true);
    expect(readFileSync(statePath)).toEqual(foreign);
    const keptAside = privateNames().filter((name) => name.endsWith(".claim"));
    expect(keptAside).toHaveLength(1);
    const keptPath = join(realpathSync(base), keptAside[0]!);
    expect(readFileSync(keptPath)).toEqual(original);
    expect(refused).toEqual([{ path: keptPath, reason: "machine-state-kept-aside" }]);
    expect(refuseLine(refused[0]!)).toBe(
      `⚠ machine.json changed while this run was replacing it; its previous contents are kept at ${keptPath} — move them back by hand`,
    );
  });

  test("F18: a lock left by a dead run on this host is reclaimed; a live, foreign-host or unreadable lock stays and is named", () => {
    const base = useHome("machine-state-stale-lock");
    const lockPath = machineStateLockFile();
    const deadPid = spawnSync("true").pid;
    const lockOf = (pid: number, host: string) => `${JSON.stringify({ pid, hostname: host, startedAt: "2026-01-01T00:00:00.000Z", ...machineStateLockScope() })}\n`;

    writeFileSync(lockPath, lockOf(deadPid, hostname()));
    expect(installMachineCarriers(["opencode"]).refused).toEqual([]);
    expect(existsSync(lockPath)).toBe(false);
    expect(readMachineState().carriers["opencode"]).toBe(sha256(carrierFiles("opencode", "machine")!.main));

    for (const held of [lockOf(process.pid, hostname()), lockOf(deadPid, `${hostname()}-elsewhere`), "", "{not json"]) {
      writeFileSync(lockPath, held);
      const { refused } = installMachineCarriers(["opencode"]);
      expect(refused).toEqual([{ path: lockPath, reason: "machine-state-busy" }]);
      expect(readFileSync(lockPath, "utf8")).toBe(held);
      expect(refuseLine(refused[0]!)).toBe(
        `⚠ ${lockPath} — held by another ai-eng run, one on another host, or one this run cannot prove has stopped; machine state left untouched. If no ai-eng run is using this home, delete ${lockPath} and run again`,
      );
    }
    rmSync(lockPath);
    expect(readdirSync(base).filter((name) => name.startsWith(".machine.json."))).toEqual([]);
  });

  test("F24: a dead pid proves nothing from another boot or pid namespace: that lock stays held and named", () => {
    const base = useHome("machine-state-foreign-scope");
    const lockPath = machineStateLockFile();
    const deadPid = spawnSync("true").pid;
    const scope = machineStateLockScope();
    const owner = { pid: deadPid, hostname: hostname(), startedAt: "2026-01-01T00:00:00.000Z" };
    for (const foreign of [{ ...scope, bootId: "another-boot" }, { ...scope, pidNamespace: "pid:[4026531836-container]" }]) {
      const held = `${JSON.stringify({ ...owner, ...foreign })}\n`;
      writeFileSync(lockPath, held);
      expect(installMachineCarriers(["opencode"]).refused).toEqual([{ path: lockPath, reason: "machine-state-busy" }]);
      expect(readFileSync(lockPath, "utf8")).toBe(held);
    }
    rmSync(lockPath);
    expect(readdirSync(base).filter((name) => name.startsWith(".machine.json."))).toEqual([]);
  });

  test("F18: an interrupted commit's claim goes back under machine.json; beside an existing machine.json both are kept and named", () => {
    const base = useHome("machine-state-claim-recovery");
    const original = `${JSON.stringify({ version: "prior", carriers: { pi: "owned" }, templateDir: { previous: "/theirs", ours: null } }, null, 2)}\n`;
    const claim = join(base, ".machine.json.4242.abcdef012345.claim");
    writeFileSync(claim, original);

    expect(installMachineCarriers(["opencode"]).refused).toEqual([]);
    expect(existsSync(claim)).toBe(false);
    const recovered = readMachineState();
    expect(recovered.templateDir).toEqual({ previous: "/theirs", ours: null });
    expect(recovered.carriers).toEqual({ pi: "owned", opencode: sha256(carrierFiles("opencode", "machine")!.main) });

    writeFileSync(claim, original);
    const { refused } = installMachineCarriers(["opencode"]);
    const keptPath = join(realpathSync(base), basename(claim));
    expect(refused).toEqual([{ path: keptPath, reason: "machine-state-copy-kept" }]);
    expect(readFileSync(claim, "utf8")).toBe(original);
    expect(readMachineState().templateDir).toEqual({ previous: "/theirs", ours: null });
    expect(refuseLine(refused[0]!)).toBe(
      `⚠ ${keptPath} — an earlier copy of machine.json left by an interrupted ai-eng run; kept beside the current one — compare them and delete the one you do not need`,
    );
  });

  test("F16: an edited module carrier and its bundle are kept, and a directory there does not abort removal", () => {
    const base = useHome("machine-remove-edited-module");
    installMachineCarriers(["opencode"]);
    const plugin = join(base, ".config", "opencode", "plugins", "ai-eng.ts");
    const bundle = join(base, ".config", "opencode", "plugins", "ai-eng-chain.ts");
    const edited = `${readFileSync(plugin, "utf8")}// my own tweak\n`;
    writeFileSync(plugin, edited);
    const omp = carrierPath(machineCarrier(byId("oh-my-pi"))!);
    mkdirSync(omp, { recursive: true });

    const swept = removeMachineCarriers(["opencode", "oh-my-pi"]);

    expect(swept.lines).toEqual([]);
    expect(swept.refused).toEqual([
      { path: "~/.config/opencode/plugins/ai-eng.ts", reason: "carrier-edited" },
      { path: `~/${machineCarrier(byId("oh-my-pi"))!.path}`, reason: "carrier-edited" },
    ]);
    expect(readFileSync(plugin, "utf8")).toBe(edited);
    expect(readFileSync(bundle, "utf8")).toBe(carrierFiles("opencode", "machine")!.chain!);
    expect(lstatSync(omp).isDirectory()).toBe(true);
    expect(readMachineState().carriers["opencode"]).toBe(sha256(carrierFiles("opencode", "machine")!.main));
  });

  test("machine.json keeps legacy restore state, and reads as nothing when it is garbage", () => {
    useHome("machine-state");
    writeFileSync(
      machineStateFile(),
      JSON.stringify({
        version: "2.5.0",
        carriers: {},
        templateDir: { previous: "/some/other/templateDir", ours: null },
      }),
    );
    expect(readMachineState()).toEqual({
      version: "2.5.0",
      carriers: {},
      templateDir: { previous: "/some/other/templateDir", ours: null },
    });

    // A refused carrier update must preserve restore data from an older version.
    installMachineCarriers(["claude-code"]);
    const state = readMachineState();
    expect(state.carriers["claude-code"]).toBeUndefined();
    expect(state.templateDir).toEqual({ previous: "/some/other/templateDir", ours: null });

    // Uninstall still needs the legacy record after the carriers are removed.
    removeMachineCarriers(["claude-code"]);
    expect(existsSync(machineStateFile())).toBe(true);
    expect(readMachineState()).toEqual({
      version: VERSION,
      carriers: {},
      templateDir: { previous: "/some/other/templateDir", ours: null },
    });

    // Garbage on disk reads as "nothing remembered", never as somebody else's record.
    writeFileSync(machineStateFile(), "{ not json");
    expect(readMachineState()).toEqual({ version: "", carriers: {} });
    writeFileSync(
      machineStateFile(),
      JSON.stringify({ version: 9, carriers: { codex: "abc", bogus: 7 }, templateDir: { previous: 3, ours: "/o" } }),
    );
    expect(readMachineState()).toEqual({ version: "", carriers: { codex: "abc" }, templateDir: { previous: null, ours: "/o" } });
  });
});

describe("what 2.2.0 moved out of the repo", () => {
  test("sweepMovedRepoCarriers takes ours out and keeps a file that is not ours", () => {
    const root = join(sandbox, "moved-basic");
    const onlyOurs = `${JSON.stringify({ hooks: { PreToolUse: [{ hooks: [{ command: `${CHAIN} PreToolUse` }] }] } }, null, 2)}\n`;
    write(join(root, ".claude", "settings.json"), onlyOurs);
    write(join(root, ".agents", "hooks", "ai-eng.ts"), carrierFiles("oh-my-pi", "machine")!.main);
    const theirs = "// a plugin of theirs that mentions nothing\nconsole.log('mine');\n";
    write(join(root, ".opencode", "plugins", "ai-eng.ts"), theirs);

    const { removed, kept } = sweepMovedRepoCarriers(root);
    expect(removed.sort()).toEqual([".agents/hooks/ai-eng.ts", ".claude/settings.json"]);
    expect(kept).toEqual([".opencode/plugins/ai-eng.ts"]);
    // A hook file nobody reads with our marker in it is a ghost; a file without one is theirs.
    expect(existsSync(join(root, ".claude", "settings.json"))).toBe(false);
    expect(existsSync(join(root, ".agents", "hooks", "ai-eng.ts"))).toBe(false);
    expect(readFileSync(join(root, ".opencode", "plugins", "ai-eng.ts"), "utf8")).toBe(theirs);
  });

  test("sweepMovedRepoCarriers strips a shared settings file and keeps the user's keys", () => {
    const root = join(sandbox, "moved-shared");
    const shared = `${JSON.stringify(
      { env: { MINE: "1" }, hooks: { PreToolUse: [{ hooks: [{ command: `${CHAIN} PreToolUse` }] }] } },
      null,
      2,
    )}\n`;
    write(join(root, ".claude", "settings.json"), shared);

    expect(sweepMovedRepoCarriers(root).removed).toEqual([".claude/settings.json"]);
    const after = readFileSync(join(root, ".claude", "settings.json"), "utf8");
    expect(after).not.toInclude(CHAIN);
    expect(JSON.parse(after)).toEqual({ env: { MINE: "1" } });
  });

  test("sweepMovedRepoCarriers keeps a file it cannot parse, and one that never carried us", () => {
    const root = join(sandbox, "moved-kept");
    const comments = '{\n  // mine\n  "model": "opus"\n}\n';
    const extension = "// their extension, no marker anywhere\n";
    write(join(root, ".codex", "hooks.json"), comments);
    write(join(root, ".pi", "extensions", "ai-eng.ts"), extension);

    expect(sweepMovedRepoCarriers(root)).toEqual({ removed: [], kept: [".codex/hooks.json", ".pi/extensions/ai-eng.ts"], refused: [] });
    expect(readFileSync(join(root, ".codex", "hooks.json"), "utf8")).toBe(comments);
    expect(readFileSync(join(root, ".pi", "extensions", "ai-eng.ts"), "utf8")).toBe(extension);
  });

  test("F21: a repo settings file that never held an ai-eng entry is the repo's own: no row, bytes untouched", () => {
    const root = join(sandbox, "moved-never-ours");
    const projectSettings = '{"permissions":{"allow":["Bash(ls)"]}}';
    const codexHooks = `${JSON.stringify({ hooks: { Stop: [{ hooks: [{ command: "my-own-script.sh" }] }] } }, null, 2)}\n`;
    write(join(root, ".claude", "settings.json"), projectSettings);
    write(join(root, ".codex", "hooks.json"), codexHooks);

    expect(sweepMovedRepoCarriers(root)).toEqual({ removed: [], kept: [], refused: [] });
    expect(readFileSync(join(root, ".claude", "settings.json"), "utf8")).toBe(projectSettings);
    expect(readFileSync(join(root, ".codex", "hooks.json"), "utf8")).toBe(codexHooks);
  });

  test("F12: a repo settings file linked to the user's home settings is kept, and the home file is never rewritten", () => {
    for (const aliasType of ["symlink", "hard-link"] as const) {
      const root = join(sandbox, `moved-linked-${aliasType}`);
      const homeSettings = join(sandbox, `moved-linked-${aliasType}-home`, ".claude", "settings.json");
      const merged = `${JSON.stringify(
        { env: { MINE: "1" }, hooks: { PreToolUse: [{ hooks: [{ command: `${CHAIN} PreToolUse` }] }] } },
        null,
        2,
      )}\n`;
      write(homeSettings, merged);
      const repoSettings = join(root, ".claude", "settings.json");
      mkdirSync(dirname(repoSettings), { recursive: true });
      if (aliasType === "symlink") symlinkSync(homeSettings, repoSettings);
      else linkSync(homeSettings, repoSettings);
      const plugin = join(root, ".opencode", "plugins", "ai-eng.ts");
      write(plugin, `${carrierFiles("opencode", "machine")!.main}// my own line\n`);

      expect(sweepMovedRepoCarriers(root)).toEqual({
        removed: [],
        kept: [".claude/settings.json", ".opencode/plugins/ai-eng.ts"],
        refused: [],
      });
      expect(readFileSync(homeSettings, "utf8")).toBe(merged);
      if (aliasType === "symlink") expect(readlinkSync(repoSettings)).toBe(homeSettings);
      else expect(lstatSync(repoSettings).ino).toBe(lstatSync(homeSettings).ino);
      expect(readFileSync(plugin, "utf8")).toEndWith("// my own line\n");
    }
  });
});

describe("installCanon and what leaves with it", () => {
  test("installCanon refuses a symlinked skill directory instead of writing outside the canon, and says so", () => {
    const base = useHome("canon-symlink");
    const nestedAsset = [...embeddedUnder("skills/")].find(([path]) => {
      const parts = path.slice("skills/".length).split("/");
      return parts.length > 2 && !parts[0]!.startsWith(".");
    });
    if (!nestedAsset) throw new Error("the skills inventory has no nested resource for symlink coverage");

    const parts = nestedAsset[0].slice("skills/".length).split("/");
    const skillDir = join(base, "skills", parts[0]!);
    const escaped = join(sandbox, "canon-symlink-target");
    mkdirSync(skillDir, { recursive: true });
    mkdirSync(escaped);
    symlinkSync(escaped, join(skillDir, parts[1]!), "dir");

    const lines = installCanon("2.2.0");
    expect(lines).toContain(`⚠ 1 path(s) where ai-eng installs are links or not its own folders or files — never written through, left as they are (the link and what it points at untouched): ${join(realpathSync(skillDir), parts[1]!)}. Move one aside to let ai-eng install there`);
    expect(readdirSync(escaped)).toEqual([]);
  });

  test("F30: the agents mirror never overwrites a same-named file of the user's, nor repoints a link of theirs", () => {
    const base = useHome("agents-mirror-user");
    const mirror = join(base, ".claude", "agents");
    const agent = readdirSync(join(import.meta.dir, "..", "agents")).filter((name) => name.endsWith(".md")).sort()[0]!;
    write(join(mirror, agent), "# my own agent of the same name\n");

    const lines = installAgentsCanon();
    expect(readFileSync(join(mirror, agent), "utf8")).toBe("# my own agent of the same name\n");
    expect(lines).toContain(`⚠ 1 file(s) in ~/.claude/agents are yours (they differ from ai-eng's agent of the same name) — kept: ${agent}. Delete or rename one to receive ai-eng's version`);

    rmSync(mirror, { recursive: true });
    const dotfiles = join(base, "dotfiles-agents");
    write(join(dotfiles, "mine.md"), "mine\n");
    symlinkSync(dotfiles, mirror, "dir");
    expect(installAgentsCanon()).toContain(`⚠ ~/.claude/agents is a link of yours (→ ${dotfiles}), not ai-eng's — left as it is; ai-eng's agents are not mirrored there`);
    expect(readlinkSync(mirror)).toBe(dotfiles);
    expect(readdirSync(dotfiles)).toEqual(["mine.md"]);
  });

  test("installCanon writes the canon, the three mirrors and one slash command per skill", () => {
    const base = useHome("canon");
    // A skill of our own, whose description is folded YAML, and one with a description long
    // enough to be cut at a word boundary.
    write(
      join(base, "skills", "ai-folded", "SKILL.md"),
      "---\nname: ai-folded\ndescription: >-\n  First line of the palette.\n  And the second one, folded onto it.\n---\n\nbody\n",
    );
    const long = Array.from({ length: 40 }, (_, i) => `palabra${i}`).join(" ");
    write(join(base, "skills", "ai-long", "SKILL.md"), `---\nname: ai-long\ndescription: ${long}\n---\n\nbody\n`);
    // A real directory a person put in a mirror is not ours to replace.
    write(join(base, ".claude", "skills", "kept-skill", "SKILL.md"), "mine\n");

    const lines = installCanon("2.2.0");
    const canonDirs = readdirSync(join(base, "skills"), { withFileTypes: true })
      .filter((entry) => entry.isDirectory() && !entry.name.startsWith("."))
      .map((entry) => entry.name);
    const withSkillFile = canonDirs.filter((name) => existsSync(join(base, "skills", name, "SKILL.md")));

    expect(lines).toContain(`✓ ${base}/skills/ — ${canonDirs.length} skills installed`);
    expect(lines).toContain(`✓ Symlink → ~/.claude/skills (${canonDirs.length} skills)`);
    expect(lines).toContain(`✓ Symlink → ~/.agents/skills (${canonDirs.length} skills)`);
    expect(lines).toContain(`✓ Symlink → ~/.config/opencode/skill (${canonDirs.length} skills)`);
    expect(lines).toContain(`✓ ~/.config/opencode/commands/ — ${withSkillFile.length} slash commands (/<skill-name>)`);

    // The version cache the 24h notice reads, stamped with this binary's version.
    const cached = JSON.parse(readFileSync(join(base, "version.json"), "utf8")) as { version: string; ts: number };
    expect(cached.version).toBe("2.2.0");
    expect(Math.abs(Date.now() - cached.ts)).toBeLessThan(60_000);

    for (const target of mirrorTargets()) {
      expect(lstatSync(join(target.dir, "ai-debug")).isSymbolicLink()).toBe(true);
    }
    // Their real directory survives the mirror, file and all.
    expect(readFileSync(join(base, ".claude", "skills", "kept-skill", "SKILL.md"), "utf8")).toBe("mine\n");

    // One command per skill, out of the canon: a folded description collapsed to one line…
    const folded = readFileSync(join(base, ".config", "opencode", "commands", "ai-folded.md"), "utf8");
    expect(folded).toInclude("description: First line of the palette. And the second one, folded onto it.\n");
    expect(folded).not.toInclude(">-");
    expect(folded).toInclude("Load the `ai-folded` skill");
    expect(folded).toInclude("$ARGUMENTS");
    // …and a long one cut at a word boundary, never mid-word.
    const longLine = /^description: (.*)$/m.exec(readFileSync(join(base, ".config", "opencode", "commands", "ai-long.md"), "utf8"))![1]!;
    expect(longLine.endsWith("…")).toBe(true);
    expect(longLine.length).toBeLessThanOrEqual(202);
    expect(/[^\s]…$/.test(longLine)).toBe(true);
    expect(longLine.length).toBeLessThan(long.length);
  });

  test("installCanon and every skill mirror receive the complete skills inventory", () => {
    const base = useHome("canon-all-skills");
    const skills = allSkillInventory();

    installCanon("2.2.0");

    expect(skills.length).toBeGreaterThan(0);
    expect(installedSkillNames(base)).toEqual(skills.map((skill) => skill.name).sort());
    expectInventoryInstalled(base, skills);
    for (const target of mirrorTargets()) {
      for (const skill of skills) {
        for (const [relative, content] of skill.files) {
          expect(readFileSync(join(target.dir, skill.name, relative), "utf8")).toBe(content);
        }
      }
    }
  });

  test("installCanon sweeps a page it recorded writing and keeps one it cannot prove", () => {
    const base = useHome("canon-sweep");
    const renamed = "skills/ai-brainstorm/a-page-that-was-renamed.md";
    const notes = "skills/ai-brainstorm/my-notes.md";
    write(join(base, renamed), "old\n");
    write(join(base, notes), "mine\n");
    writeFileSync(join(base, CANON_OWNERSHIP_NAME), JSON.stringify({ files: { [renamed]: sha256("old\n") } }));

    const lines = installCanon("2.2.0");
    expect(lines).toContain(`✓ swept 1 file(s) this binary no longer ships: ${renamed}`);
    expect(lines).toContain(`✓ kept 1 user file(s) — not shipped by this binary and not provably written by ai-eng, so never deleted: ${notes}`);
    expect(existsSync(join(base, renamed))).toBe(false);
    expect(readFileSync(join(base, notes), "utf8")).toBe("mine\n");
    expect(existsSync(join(base, "skills", "ai-brainstorm", "SKILL.md"))).toBe(true);
    // The new record is this payload: the kept page is not in it, so it stays the user's.
    const record = JSON.parse(readFileSync(join(base, CANON_OWNERSHIP_NAME), "utf8")) as { files: Record<string, string> };
    expect(record.files[notes]).toBeUndefined();
    expect(record.files["skills/ai-brainstorm/SKILL.md"]).toBe(sha256(readFileSync(join(base, "skills", "ai-brainstorm", "SKILL.md"), "utf8")));
  });

  test("removeMachineArtifacts removes only what points into the canon, and prunes what it emptied", () => {
    const base = useHome("canon-remove");
    // Nothing installed: every mirror is absent, and the command still answers zero.
    expect(removeMachineArtifacts()).toBe(0);

    installCanon("2.2.0");
    write(join(base, ".claude", "skills", "mine", "SKILL.md"), "mine\n");
    const opencodeSkills = mirrorTargets().find((target) => target.dir.endsWith("skill"))!;
    const backupTarget = join(base, "skills-backup", "ai-debug");
    write(join(backupTarget, "SKILL.md"), "backup\n");
    const backupLink = join(opencodeSkills.dir, "backup-skill");
    symlinkSync(backupTarget, backupLink, "dir");
    // A symlink whose target is gone: not evidence of ours, so it stays.
    const ghost = join(base, ".config", "opencode", "skill", "ghost");
    mkdirSync(dirname(ghost), { recursive: true });
    symlinkSync(join(sandbox, "canon-remove-nowhere"), ghost);

    const canonDirs = readdirSync(join(base, "skills"), { withFileTypes: true }).filter(
      (entry) => entry.isDirectory() && !entry.name.startsWith("."),
    );
    const commands = readdirSync(join(base, ".config", "opencode", "commands")).length;
    // Every skill in the canon is linked into each of the three mirrors — the real
    // directory of theirs in `.claude/skills` is neither replaced nor counted — and every
    // skill also left one slash command.
    expect(removeMachineArtifacts()).toBe(canonDirs.length * 3 + commands);

    for (const target of mirrorTargets()) {
      const left = existsSync(target.dir) ? readdirSync(target.dir) : [];
      expect(left.filter((name) => lstatSync(join(target.dir, name)).isSymbolicLink()).sort()).toEqual(
        target.dir.endsWith("skill") ? ["backup-skill", "ghost"] : [],
      );
    }
    expect(readFileSync(join(base, ".claude", "skills", "mine", "SKILL.md"), "utf8")).toBe("mine\n");
    expect(lstatSync(backupLink).isSymbolicLink()).toBe(true);
    expect(readlinkSync(backupLink)).toBe(backupTarget);
    expect(readFileSync(join(backupTarget, "SKILL.md"), "utf8")).toBe("backup\n");
    // A symlink whose target is gone is not evidence of ours: it is still there, pointing
    // where it did.
    expect(lstatSync(ghost).isSymbolicLink()).toBe(true);
    expect(readlinkSync(ghost)).toBe(join(sandbox, "canon-remove-nowhere"));
    // The dirs we emptied are gone; the two holding somebody else's work are not.
    expect(existsSync(join(base, ".agents", "skills"))).toBe(false);
    expect(existsSync(join(base, ".config", "opencode", "commands"))).toBe(false);
    expect(existsSync(join(base, ".claude", "skills"))).toBe(true);
  });

  test("F10: removeMachineArtifacts keeps a user's own alias into the canon", () => {
    const base = useHome("canon-remove-user-alias");
    installCanon("2.2.0");
    const target = mirrorTargets()[0]!;
    const canonSkill = join(base, "skills", "ai-debug");
    const shortcut = join(target.dir, "my-shortcut");
    symlinkSync(canonSkill, shortcut, "dir");
    const relativeAlias = join(target.dir, "ai-explore");
    rmSync(relativeAlias);
    symlinkSync(join("..", "..", "skills", "ai-explore"), relativeAlias, "dir");

    removeMachineArtifacts();

    expect(lstatSync(shortcut).isSymbolicLink()).toBe(true);
    expect(readlinkSync(shortcut)).toBe(canonSkill);
    expect(lstatSync(relativeAlias).isSymbolicLink()).toBe(true);
    expect(readlinkSync(relativeAlias)).toBe(join("..", "..", "skills", "ai-explore"));
    expect(existsSync(join(target.dir, "ai-debug"))).toBe(false);
  });

  test("F14: removeMachineArtifacts keeps an edited slash command and removes the untouched ones", () => {
    const base = useHome("canon-remove-edited-command");
    installCanon("2.2.0");
    const commands = join(base, ".config", "opencode", "commands");
    const edited = join(commands, "ai-debug.md");
    const editedBytes = `${readFileSync(edited, "utf8")}\nMy own notes for this command.\n`;
    writeFileSync(edited, editedBytes);

    removeMachineArtifacts();

    expect(readdirSync(commands)).toEqual(["ai-debug.md"]);
    expect(readFileSync(edited, "utf8")).toBe(editedBytes);
  });

  test("removeMachineArtifacts preserves a mirror link replaced after validation", () => {
    const base = useHome("canon-remove-race");
    installCanon("2.2.0");
    const target = mirrorTargets()[0]!;
    const link = join(target.dir, "ai-debug");
    const replacement = join(base, "skills-backup", "ai-debug");
    write(join(replacement, "SKILL.md"), "user skill\n");
    const race = replaceLinkOnChdir(realpathSync(target.dir), link, replacement);

    try {
      removeMachineArtifacts();
    } finally {
      race.restore();
    }

    expect(race.wasTriggered()).toBe(true);
    expect(lstatSync(link).isSymbolicLink()).toBe(true);
    expect(readlinkSync(link)).toBe(replacement);
    expect(readFileSync(join(replacement, "SKILL.md"), "utf8")).toBe("user skill\n");
  });
});
