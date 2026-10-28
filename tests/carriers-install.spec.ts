// The install side of the carriers, driven in-process so the coverage is the module's and
// not a spawned CLI's: shared settings merges, machine carriers and their machine.json
// record, legacy template cleanup, and artifacts installCanon leaves outside the canon.
//
// Every test owns a machine of its own: AI_ENG_HOME isolates the canon, the mirrors and
// the carriers, and GIT_CONFIG_GLOBAL isolates legacy template restoration.
//
// DEFECT found while writing these tests, reported and NOT fixed here (src is out of scope):
// `templates/settings.claude.json.tpl:7,13` write the hooks arrays inline, and `shapeOf`
// (src/install.ts:123) only accepts a file it can reproduce byte for byte. So the Claude
// machine carrier cannot be read back once written from our own template:
// `mergeSharedText` answers `refused: "reformat"` and `stripSharedText` answers null for
// exactly the bytes we produced. Consequences: a second `installMachineCarriers` /
// `ai-eng update` on an existing `~/.claude/settings.json` reports the carrier refused
// instead of current, a changed template never reaches that file by merge, and
// `removeMachineCarriers` cannot take the file back out at uninstall — it is left on the
// machine with our hooks in it. The other three settings templates round-trip and are
// asserted below; the tests here assert the contract that still holds for Claude (bytes
// unchanged on a second install) rather than freezing the refusal in place.

import { afterAll, afterEach, beforeAll, describe, expect, test } from "bun:test";
import { spawnSync } from "node:child_process";
import { embeddedTemplate, embeddedUnder } from "../src/embed.ts";
import {
  existsSync,
  lstatSync,
  mkdirSync,
  mkdtempSync,
  readdirSync,
  readFileSync,
  readlinkSync,
  rmSync,
  symlinkSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { buildLock, install, lockText, mergeSharedText, parseLock, sha256, stripSharedText, type PlanEntry } from "../src/install.ts";
import {
  SURFACES,
  carrierBase,
  carrierFiles,
  carrierPath,
  installCanon,
  installMachineCarriers,
  machineCarrier,
  machineStateFile,
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
import { planEntries } from "../src/commands/init-shared.ts";
import { VERSION } from "../src/version.ts";

const SHIM_MARKER = "ai-eng git floor shim";
const LEGACY_SHIMS = ["pre-commit", "commit-msg", "pre-push"] as const;
const CHAIN = "ai-eng chain";

let sandbox: string;
const OWNED_ENV = ["AI_ENG_HOME", "PI_CODING_AGENT_DIR", "GIT_CONFIG_GLOBAL"] as const;
let inherited: Record<string, string | undefined> = {};

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

/** A machine of its own: the canon home, the mirrors, the carriers and the git floor's
 *  global setting all resolve inside it, and none of them can leak into the next test. */
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
    expect(installMachineCarriers(machineSurfaces.map((surface) => surface.id)).refused).toEqual([]);
    for (const surface of machineSurfaces) {
      const placement = machineCarrier(surface)!;
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

  test("an update replaces the old Python gate and keeps the user's hook", () => {
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

    expect(installMachineCarriers(["claude-code"]).refused).toEqual([]);
    const installed = readFileSync(settings, "utf8");
    const installedCommands = (JSON.parse(installed) as {
      hooks: { PreToolUse: Array<{ hooks: Array<{ command: string }> }> };
    }).hooks.PreToolUse.flatMap(({ hooks }) => hooks.map(({ command }) => command));
    expect(installedCommands).not.toContain(oldPythonGate);
    expect(installedCommands).toContain(wrappedUserHook);
    expect(installed).toContain("my-own-audit.sh");
    expect(installed).toContain(`${CHAIN} PreToolUse`);
    expect(JSON.parse(installed).env.MY_FLAG).toBe("1");
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

  test("installMachineCarriers: missing is written, the user's file is merged, garbage is refused", () => {
    const base = useHome("machine-install");
    const carrier = join(base, ".claude", "settings.json");
    const definition = sha256(carrierFiles("claude-code", "machine")!.main);

    // A surface with no machine carrier, and a name no surface answers to, contribute nothing.
    expect(installMachineCarriers(["claude-code", "zed", "no-such-host"])).toEqual({
      written: ["~/.claude/settings.json"],
      untouched: [],
      refused: [],
    });
    expect(readFileSync(carrier, "utf8")).toInclude(`${CHAIN} PreToolUse`);
    const state = readMachineState();
    expect(state.version).toBe(VERSION);
    // The definition's hash is the record: Codex re-asks for trust on any byte change.
    expect(state.carriers["claude-code"]).toBe(definition);

    // Same definition again: not a byte rewritten (Codex re-asks for trust on any change).
    // It is refused rather than reported current — the defect noted at the top of this file:
    // `shapeOf` cannot reproduce this template's own inline arrays.
    const again = installMachineCarriers(["claude-code"]);
    expect(again.written).toEqual([]);
    expect(readFileSync(carrier, "utf8")).toBe(carrierFiles("claude-code", "machine")!.main);

    // The file belongs to the person: ours go in by marker, theirs stay.
    write(carrier, USER_SETTINGS);
    expect(installMachineCarriers(["claude-code"]).written).toEqual(["~/.claude/settings.json"]);
    const merged = readFileSync(carrier, "utf8");
    expect(merged).toInclude("my-own-audit.sh");
    expect(merged).toInclude(`${CHAIN} PreToolUse`);
    expect(stripSharedText(merged)).toBe(USER_SETTINGS);

    // Not JSON: untouched, and the reason is on the record.
    const comments = '{\n  // my notes\n  "model": "opus"\n}\n';
    write(carrier, comments);
    const refused = installMachineCarriers(["claude-code"]);
    expect(refused.refused).toEqual([{ path: "~/.claude/settings.json", reason: "not-json" }]);
    expect(refused.written).toEqual([]);
    expect(readFileSync(carrier, "utf8")).toBe(comments);
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

  test("installMachineCarriers: a definition already on the machine is reported current", () => {
    const base = useHome("machine-current");
    const carrier = join(base, ".codex", "hooks.json");
    const files = carrierFiles("codex", "machine")!;
    expect(installMachineCarriers(["codex"]).written).toEqual(["~/.codex/hooks.json"]);
    expect(readFileSync(carrier, "utf8")).toBe(files.main);

    const again = installMachineCarriers(["codex"]);
    expect(again.untouched).toEqual(["~/.codex/hooks.json"]);
    expect(again.written).toEqual([]);
    expect(again.refused).toEqual([]);
    expect(readFileSync(carrier, "utf8")).toBe(files.main);
    expect(readMachineState().carriers["codex"]).toBe(sha256(files.main));
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
    expect(swept.refused).toEqual([]);
    expect(swept.lines).toEqual([
      "~/.claude/settings.json removed (it held only ai-eng entries)",
      "~/.config/opencode/plugins/ai-eng.ts removed",
    ]);
    expect(existsSync(carrier)).toBe(false);
    expect(existsSync(plugin)).toBe(false);
    expect(existsSync(bundle)).toBe(false);
    // Nothing left to remember: an empty machine.json would be a stale record.
    expect(existsSync(machineStateFile())).toBe(false);
  });

  test("removeMachineCarriers: our entries out of the user's file, theirs back byte for byte", () => {
    const base = useHome("machine-remove-keeps");
    const carrier = join(base, ".claude", "settings.json");
    write(carrier, USER_SETTINGS);
    installMachineCarriers(["claude-code"]);
    expect(readFileSync(carrier, "utf8")).toInclude(CHAIN);

    const swept = removeMachineCarriers(["claude-code"]);
    expect(swept.refused).toEqual([]);
    expect(swept.lines).toEqual(["~/.claude/settings.json: ai-eng entries removed, yours kept"]);
    expect(readFileSync(carrier, "utf8")).toBe(USER_SETTINGS);
  });

  test("removeMachineCarriers: a file it cannot rewrite is refused by name, and left alone", () => {
    const base = useHome("machine-remove-refused");
    const carrier = join(base, ".claude", "settings.json");
    const comments = '{\n  // mine\n  "model": "opus"\n}\n';
    write(carrier, comments);

    expect(removeMachineCarriers(["claude-code"])).toEqual({ lines: [], refused: ["~/.claude/settings.json"] });
    expect(readFileSync(carrier, "utf8")).toBe(comments);
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

    // A current carrier install must preserve restore data from an older version.
    installMachineCarriers(["claude-code"]);
    const state = readMachineState();
    expect(state.carriers["claude-code"]).toBe(sha256(carrierFiles("claude-code", "machine")!.main));
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
    write(join(root, ".agents", "hooks", "ai-eng.ts"), "export default 1; // ai-eng\n");
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

    expect(sweepMovedRepoCarriers(root)).toEqual({ removed: [], kept: [".codex/hooks.json", ".pi/extensions/ai-eng.ts"] });
    expect(readFileSync(join(root, ".codex", "hooks.json"), "utf8")).toBe(comments);
    expect(readFileSync(join(root, ".pi", "extensions", "ai-eng.ts"), "utf8")).toBe(extension);
  });
});

describe("installCanon and what leaves with it", () => {
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

    expect(lines).toContain(`✓ ${base}/skills/ — ${canonDirs.length} ai-* skills installed`);
    expect(lines).toContain(`✓ Symlink → ~/.claude/skills (${canonDirs.length} skills)`);
    expect(lines).toContain(`✓ Symlink → ~/.agents/skills (${canonDirs.length} skills)`);
    expect(lines).toContain(`✓ Symlink → ~/.config/opencode/skill (${canonDirs.length} skills)`);
    expect(lines).toContain(`✓ ~/.config/opencode/commands/ — ${withSkillFile.length} slash commands (/ai-*)`);

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

  test("installCanon sweeps a page this binary no longer ships", () => {
    const base = useHome("canon-sweep");
    write(join(base, "skills", "ai-brainstorm", "a-page-that-was-renamed.md"), "old\n");

    const lines = installCanon("2.2.0");
    expect(lines).toContain("✓ swept 1 file(s) this binary no longer ships: skills/ai-brainstorm/a-page-that-was-renamed.md");
    expect(existsSync(join(base, "skills", "ai-brainstorm", "a-page-that-was-renamed.md"))).toBe(false);
    expect(existsSync(join(base, "skills", "ai-brainstorm", "SKILL.md"))).toBe(true);
  });

  test("removeMachineArtifacts removes only what points into the canon, and prunes what it emptied", () => {
    const base = useHome("canon-remove");
    // Nothing installed: every mirror is absent, and the command still answers zero.
    expect(removeMachineArtifacts()).toBe(0);

    installCanon("2.2.0");
    write(join(base, ".claude", "skills", "mine", "SKILL.md"), "mine\n");
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
      expect(left.filter((name) => lstatSync(join(target.dir, name)).isSymbolicLink())).toEqual(target.dir.endsWith("skill") ? ["ghost"] : []);
    }
    expect(readFileSync(join(base, ".claude", "skills", "mine", "SKILL.md"), "utf8")).toBe("mine\n");
    // A symlink whose target is gone is not evidence of ours: it is still there, pointing
    // where it did.
    expect(lstatSync(ghost).isSymbolicLink()).toBe(true);
    expect(readlinkSync(ghost)).toBe(join(sandbox, "canon-remove-nowhere"));
    // The dirs we emptied are gone; the two holding somebody else's work are not.
    expect(existsSync(join(base, ".agents", "skills"))).toBe(false);
    expect(existsSync(join(base, ".config", "opencode", "commands"))).toBe(false);
    expect(existsSync(join(base, ".claude", "skills"))).toBe(true);
  });
});
