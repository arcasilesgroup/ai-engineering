// Adversarial: settings files can be user-owned. Repo and machine settings both merge by
// marker; a machine settings file is replaced through a staged rename, never rewritten in
// place, and its user keys survive install and uninstall.

import { describe, test, expect, beforeAll, afterAll } from "bun:test";
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { mergeSharedText, sha256, stripSharedText } from "../../src/install.ts";
import { carrierDefinition, carrierFiles } from "../../src/surfaces/adapters.ts";
import { removeMachineCarriers } from "../../src/surfaces/carriers-install.ts";
import { readMachineState } from "../../src/surfaces/machine-state.ts";

type HookGroup = { matcher?: string; hooks?: Array<{ command?: string }> };
type Settings = { permissions?: unknown; env?: unknown; hooks?: Record<string, HookGroup[]>; $comment?: string };

const cli = join(import.meta.dir, "..", "..", "src", "cli.ts");
let sandbox: string;
let home: string;

const ENV = () => ({ ...process.env, AI_ENG_HOME: home, NO_COLOR: "1", CI: "1", AI_ENG_NO_UPDATE_NOTICES: "1" });

function run(args: string[], cwd: string, input = ""): { status: number; stdout: string; stderr: string } {
  const r = spawnSync(process.execPath, [cli, ...args], { cwd, encoding: "utf8", env: ENV(), input });
  return { status: r.status ?? 0, stdout: r.stdout ?? "", stderr: r.stderr ?? "" };
}

/** In-process reads of machine state need the same AI_ENG_HOME the spawned CLIs got: the
 *  helpers resolve their base from the environment at call time, and unset means the
 *  developer's real home. */
function withHome<T>(fn: () => T): T {
  const previous = process.env["AI_ENG_HOME"];
  process.env["AI_ENG_HOME"] = home;
  try {
    return fn();
  } finally {
    if (previous === undefined) delete process.env["AI_ENG_HOME"];
    else process.env["AI_ENG_HOME"] = previous;
  }
}

/** A repo whose MACHINE already has a settings file the user has been keeping for a
 *  while: `~/.claude/settings.json` is where Claude Code reads, and it belongs to the
 *  person, not to the install. */
function repoWithUserSettings(settings: string): string {
  const repo = join(sandbox, `repo-${Math.random().toString(36).slice(2)}`);
  mkdirSync(repo, { recursive: true });
  spawnSync("git", ["init", "-q"], { cwd: repo });
  mkdirSync(join(home, ".claude"), { recursive: true });
  writeFileSync(join(home, ".claude", "settings.json"), settings);
  return repo;
}

const USER_SETTINGS = `{
  "permissions": {
    "allow": [
      "Bash(bun test:*)",
      "Read"
    ],
    "deny": [
      "Bash(rm -rf:*)"
    ]
  },
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
    ],
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "echo hello"
          }
        ]
      }
    ]
  }
}
`;

let gitConfigBefore: string | undefined;

beforeAll(() => {
  sandbox = mkdtempSync(join(tmpdir(), "ai-eng-merge-"));
  // Every git fixture reads a config of our own, so git init cannot inherit real hooks.
  gitConfigBefore = process.env["GIT_CONFIG_GLOBAL"];
  process.env["GIT_CONFIG_GLOBAL"] = join(sandbox, "gitconfig");
  writeFileSync(process.env["GIT_CONFIG_GLOBAL"], "");
});

/** A home of its own per test: these tests write MACHINE state, and a shared home would
 *  let one test's carrier decide what the next one finds. */
function useHome(): string {
  home = join(sandbox, `home-${Math.random().toString(36).slice(2)}`);
  mkdirSync(join(home, "skills", "ai-demo"), { recursive: true });
  return home;
}

afterAll(() => {
  if (gitConfigBefore === undefined) delete process.env["GIT_CONFIG_GLOBAL"];
  else process.env["GIT_CONFIG_GLOBAL"] = gitConfigBefore;
  rmSync(sandbox, { recursive: true, force: true });
});

describe("adversarial · carrier merge (a settings file is the user's)", () => {
  test("two repo carriers: a governed repo keeps Cursor's and Copilot's and nothing else", () => {
    useHome();
    const repo = join(sandbox, "two-carriers");
    mkdirSync(repo, { recursive: true });
    spawnSync("git", ["init", "-q"], { cwd: repo });
    expect(run(["init", "--yes", "--surface", "claude-code,oh-my-pi,opencode,cursor,copilot,codex,pi"], repo).status).toBe(0);
    // Host-owned modules are installed; settings carriers nobody had are created from the
    // template, because an exclusive create cannot replace anything of the user's.
    const machine: string[] = [
      join(home, ".omp", "agent", "hooks", "pre", "ai-eng.ts"),
      join(home, ".config", "opencode", "plugins", "ai-eng.ts"),
      join(home, ".pi", "agent", "extensions", "ai-eng.ts"),
    ];
    for (const path of machine) expect(existsSync(path)).toBe(true);
    for (const [id, path] of [
      ["claude-code", join(home, ".claude", "settings.json")],
      ["codex", join(home, ".codex", "hooks.json")],
      ["copilot-cli", join(home, ".copilot", "hooks", "ai-eng.json")],
    ] as const) {
      expect(readFileSync(path, "utf8")).toBe(carrierFiles(id)!.main);
    }
    // The OMP carrier is a hook FACTORY (default export, pi.on) at the path omp's own
    // loader scans. The module it used to ship exported beforeToolCall and lived in
    // `.agents/hooks/`, which no OMP code path reads.
    const ompCarrier = readFileSync(join(home, ".omp", "agent", "hooks", "pre", "ai-eng.ts"), "utf8");
    expect(ompCarrier).toInclude("export default function");
    expect(ompCarrier).toInclude('pi.on("tool_call"');
    expect(readFileSync(join(home, ".omp", "agent", "hooks", "pre", ".ai-eng-chain.ts"), "utf8")).toInclude("ai-eng-chain");
    // The repo keeps exactly the two whose readers only exist in the checkout.
    expect(existsSync(join(repo, ".cursor", "hooks.json"))).toBe(true);
    expect(existsSync(join(repo, ".github", "hooks", "ai-eng.json"))).toBe(true);
    for (const gone of [".claude", ".codex", ".agents", ".opencode", ".pi"]) {
      expect(existsSync(join(repo, gone))).toBe(false);
    }
  });

  test("config --remove takes our entries out of a shared file and keeps the user's", () => {
    useHome();
    const repo = join(sandbox, "config-remove");
    mkdirSync(join(repo, ".cursor"), { recursive: true });
    spawnSync("git", ["init", "-q"], { cwd: repo });
    const mine = `${JSON.stringify({ version: 1, hooks: { beforeShellExecution: [{ command: "my-own-check.sh" }] } }, null, 2)}\n`;
    writeFileSync(join(repo, ".cursor", "hooks.json"), mine);
    expect(run(["init", "--yes", "--surface", "cursor"], repo).status).toBe(0);
    expect(readFileSync(join(repo, ".cursor", "hooks.json"), "utf8")).toInclude("ai-eng chain");
    // `config --remove` used to unlink the whole file while printing "ai-eng entries only".
    expect(run(["config", "--remove", "cursor"], repo).status).toBe(0);
    const after = readFileSync(join(repo, ".cursor", "hooks.json"), "utf8");
    const parsed = JSON.parse(after) as { version?: number; hooks?: { beforeShellExecution?: Array<{ command?: string }> } };
    expect(after).not.toInclude("ai-eng chain");
    // Their entry, byte for byte, and nothing of ours left in the hooks.
    expect(parsed.hooks?.beforeShellExecution).toEqual([{ command: "my-own-check.sh" }]);
    // The top-level scalars our template declares stay: removing a key whose value equals
    // ours would delete a `version` the user wrote themselves.
    expect(parsed.version).toBe(1);
  });

  test("init leaves a user's global template setting and hooks untouched", () => {
    useHome();
    const theirs = join(sandbox, "their-template");
    mkdirSync(join(theirs, "hooks"), { recursive: true });
    const theirHook = "#!/bin/sh\n# mine, do not touch\necho hello\n";
    writeFileSync(join(theirs, "hooks", "pre-commit"), theirHook);
    spawnSync("git", ["config", "--global", "init.templateDir", theirs], { env: process.env });
    const configBefore = spawnSync("git", ["config", "--global", "--get", "init.templateDir"], { encoding: "utf8", env: process.env }).stdout.trim();
    const repo = join(sandbox, "join-repo");
    mkdirSync(repo, { recursive: true });
    spawnSync("git", ["init", "-q"], { cwd: repo });
    expect(run(["init", "--yes", "--surface", "cursor"], repo).status).toBe(0);
    expect(readFileSync(join(theirs, "hooks", "pre-commit"), "utf8")).toBe(theirHook);
    expect(existsSync(join(theirs, "hooks", "commit-msg"))).toBe(false);
    expect(existsSync(join(theirs, "hooks", "pre-push"))).toBe(false);
    expect(spawnSync("git", ["config", "--global", "--get", "init.templateDir"], { encoding: "utf8", env: process.env }).stdout.trim()).toBe(configBefore);
  });

  test("codex: a missing machine settings file is created once, recorded, and left alone after", () => {
    useHome();
    const repo = join(sandbox, "codex-repo");
    mkdirSync(repo, { recursive: true });
    spawnSync("git", ["init", "-q"], { cwd: repo });
    const initialized = run(["init", "--yes", "--surface", "codex"], repo);
    expect(initialized.status).toBe(0);
    expect(initialized.stdout + initialized.stderr).not.toInclude("safe machine-settings replacement/removal is unavailable");
    const carrier = join(home, ".codex", "hooks.json");
    const ours = carrierFiles("codex")!.main;
    expect(readFileSync(carrier, "utf8")).toBe(ours);
    const updated = run(["update", "--yes"], repo);
    expect(updated.status).toBe(0);
    expect(updated.stdout + updated.stderr).toInclude("~/.codex/hooks.json · machine carrier already current");
    expect(readFileSync(carrier, "utf8")).toBe(ours);
    const state = withHome(() => readMachineState());
    expect(state.carriers["codex"]).toBe(carrierDefinition(ours));
    const doctor = run(["doctor"], repo);
    expect(doctor.stdout + doctor.stderr).toInclude("machine carrier ~/.codex/hooks.json carries the ai-eng entries");
  });

  test("doctor splits the machine carrier from the repo declaration, and its remedy for a lost one works", () => {
    useHome();
    const repo = join(sandbox, "doctor-split");
    mkdirSync(repo, { recursive: true });
    spawnSync("git", ["init", "-q"], { cwd: repo });
    const initialized = run(["init", "--yes", "--surface", "claude-code,cursor"], repo);
    expect(initialized.status).toBe(0);
    const carrier = join(home, ".claude", "settings.json");
    rmSync(carrier);
    const missing = run(["doctor"], repo);
    const missingOut = missing.stdout + missing.stderr;
    // The repo declaration is present; the machine carrier is a separate row.
    expect(missingOut).toInclude("machine carrier ~/.claude/settings.json missing → ai-eng update");
    expect(missingOut).toInclude("repo carrier .cursor/hooks.json present");
    expect(missing.status).toBe(2);
    // The command doctor names is the one that fixes it.
    expect(run(["update", "--yes"], repo).status).toBe(0);
    expect(readFileSync(carrier, "utf8")).toBe(carrierFiles("claude-code")!.main);
    const fixed = run(["doctor"], repo);
    const fixedOut = fixed.stdout + fixed.stderr;
    expect(fixedOut).toInclude("machine carrier ~/.claude/settings.json carries the ai-eng entries");
    expect(fixedOut).not.toInclude("~/.claude/settings.json missing");
  });

  test("machine round trip: uninstall's everything scope takes our carriers out and says so", () => {
    useHome();
    const repo = join(sandbox, "round-trip");
    mkdirSync(repo, { recursive: true });
    spawnSync("git", ["init", "-q"], { cwd: repo });
    mkdirSync(join(home, ".claude"), { recursive: true });
    const userSettings = { env: { KEEP: "yes" } };
    writeFileSync(join(home, ".claude", "settings.json"), `${JSON.stringify(userSettings, null, 2)}\n`);
    const initialized = run(["init", "--yes", "--surface", "claude-code,cursor"], repo);
    expect(initialized.status).toBe(0);
    expect(initialized.stdout + initialized.stderr).toInclude("~/.claude/settings.json — machine carrier");
    const settings = join(home, ".claude", "settings.json");
    const userBytes = `${JSON.stringify(userSettings, null, 2)}\n`;
    const merged = readFileSync(settings, "utf8");
    expect(merged).toMatch(/ai-eng(?:\.cmd|\.exe)? chain/);
    expect((JSON.parse(merged) as Settings).env).toEqual(userSettings.env);
    expect(existsSync(join(home, "machine.json"))).toBe(true);
    // Everything scope: down-arrow to it, then a bare `y` per confirmation (clack answers
    // on the key, not on Enter).
    const out = run(["uninstall"], repo, "\u001b[B\ryyy");
    const text = out.stdout + out.stderr;
    expect(text).toInclude("~/.claude/settings.json: ai-eng entries removed, yours kept");
    expect(existsSync(settings)).toBe(true);
    expect(readFileSync(settings, "utf8")).toBe(userBytes);
  });

  test("update recreates a lost machine settings carrier", () => {
    useHome();
    const repo = join(sandbox, "lost-carrier");
    mkdirSync(repo, { recursive: true });
    spawnSync("git", ["init", "-q"], { cwd: repo });
    const initialized = run(["init", "--yes", "--surface", "claude-code"], repo);
    expect(initialized.status).toBe(0);
    const carrier = join(home, ".claude", "settings.json");
    rmSync(carrier);
    const out = run(["update", "--yes"], repo);
    expect(out.status, out.stdout + out.stderr).toBe(0);
    expect(out.stdout + out.stderr).toInclude("~/.claude/settings.json · machine carrier · written");
    expect(readFileSync(carrier, "utf8")).toBe(carrierFiles("claude-code")!.main);
  });

  test("user hooks survive init, update and uninstall, and ours leave with us", () => {
    useHome();
    const repo = repoWithUserSettings(USER_SETTINGS);
    const settings = join(home, ".claude", "settings.json");
    const before = JSON.parse(USER_SETTINGS) as Settings;
    const beforeBytes = readFileSync(settings, "utf8");

    const initialized = run(["init", "--yes", "--surface", "claude-code"], repo);
    expect(initialized.status).toBe(0);
    const afterInit = JSON.parse(readFileSync(settings, "utf8")) as Settings;
    // Theirs survive the merge, key for key and hook for hook; ours sit beside them.
    expect(afterInit.permissions).toEqual(before.permissions);
    expect(afterInit.env).toEqual(before.env);
    for (const [event, groups] of Object.entries(before.hooks ?? {})) {
      for (const group of groups) expect(afterInit.hooks?.[event]).toContainEqual(group);
    }
    const ourCommands = Object.values(afterInit.hooks ?? {}).flat().flatMap((group) => group.hooks ?? []).map((hook) => hook.command ?? "");
    expect(ourCommands.some((command) => /^ai-eng(?:\.cmd|\.exe)? chain/.test(command))).toBe(true);

    // Idempotent: a second install is not a second copy.
    const once = readFileSync(settings, "utf8");
    expect(run(["update", "--yes"], repo).status).toBe(0);
    expect(readFileSync(settings, "utf8")).toBe(once);

    // Project scope sweeps the REPO and stops there: the machine carrier is shared by
    // every repo that declares this surface, so one repo's uninstall has no business
    // taking the hooks out of the user's editor.
    run(["uninstall", "--project"], repo, "\ry");
    expect(readFileSync(settings, "utf8")).toBe(once);

    // Machine scope takes ours out and gives the user back their file, byte for byte.
    const swept = withHome(() => removeMachineCarriers(["claude-code"]));
    expect(swept).toEqual({ lines: ["~/.claude/settings.json: ai-eng entries removed, yours kept"], refused: [] });
    const afterUninstall = readFileSync(settings, "utf8");
    expect(afterUninstall).toBe(beforeBytes);
    expect(JSON.parse(afterUninstall)).toEqual(before);
  });

  test("a settings file that is not JSON is not touched, and the line says so", () => {
    useHome();
    const repo = repoWithUserSettings('{\n  // my notes\n  "model": "opus"\n}\n');
    const settings = join(home, ".claude", "settings.json");
    const before = readFileSync(settings, "utf8");
    const result = run(["init", "--yes", "--surface", "claude-code"], repo);
    expect(result.status).toBe(0);
    expect(readFileSync(settings, "utf8")).toBe(before); // not one byte
    expect(result.stdout + result.stderr).toInclude("not valid JSON");
  });

  test("a file this installer would have to reformat is refused, not reformatted", () => {
    // Compact JSON is valid and mergeable in principle — but merging it means
    // re-serializing the user's own lines, and the rule is that nothing foreign is
    // touched OR reformatted (§03). So it is refused, and the refusal names the cost.
    useHome();
    const repo = repoWithUserSettings('{"env":{"A":"1"},"hooks":{}}\n');
    const settings = join(home, ".claude", "settings.json");
    const before = readFileSync(settings, "utf8");
    const result = run(["init", "--yes", "--surface", "claude-code"], repo);
    expect(result.status).toBe(0);
    expect(readFileSync(settings, "utf8")).toBe(before);
    expect(result.stdout + result.stderr).toInclude("reformat");
  });

  test("the merge leaves every foreign byte of a file it does accept", () => {
    // The claim G6 asks for, stated exactly: the user's own lines come through byte
    // for byte, the only bytes added outside our entry are the JSON punctuation that
    // inserting a key requires, and a full round trip returns the file untouched.
    const current = '{\n  "env": {\n    "A": "1"\n  }\n}\n';
    const merged = mergeSharedText(current, '{"hooks":{"PreToolUse":[{"hooks":[{"command":"ai-eng chain PreToolUse"}]}]}}');
    expect("refused" in merged).toBe(false);
    if ("refused" in merged) return;
    expect(merged.text).toInclude('  "env": {\n    "A": "1"\n  }'); // their block, verbatim
    expect(stripSharedText(merged.text)).toBe(current); // and out again, byte for byte
  });

  test("a file no layer of ours ever wrote keeps its own hooks that merely mention ai-eng", () => {
    // The marker is the command, not the word: a user hook that WRAPS our chain is
    // theirs, and stripping it would take away something we never installed.
    const canonical = (command: string) =>
      `{\n  "hooks": {\n    "PreToolUse": [\n      {\n        "hooks": [\n          {\n            "command": "${command}"\n          }\n        ]\n      }\n    ]\n  }\n}\n`;
    expect(stripSharedText(canonical("ai-eng chain PreToolUse"))).toBe("{}\n");
    const wrappers = [
      "my-wrapper.sh -- ai-eng chain PreToolUse",
      "command -v ai-eng >/dev/null 2>&1 && ai-eng chain PreToolUse || exit 0",
    ];
    for (const wrapper of wrappers) expect(stripSharedText(canonical(wrapper))).toBe(canonical(wrapper));
  });



  test("a fresh repo gets its missing machine settings carrier on the machine, not in the repo", () => {
    useHome();
    const repo = join(sandbox, "fresh");
    mkdirSync(repo, { recursive: true });
    spawnSync("git", ["init", "-q"], { cwd: repo });
    const initialized = run(["init", "--yes", "--surface", "claude-code"], repo);
    expect(initialized.status).toBe(0);
    expect(readFileSync(join(home, ".claude", "settings.json"), "utf8")).toBe(carrierFiles("claude-code")!.main);
    expect(existsSync(join(repo, ".claude"))).toBe(false); // the carrier is not the repo's copy
  });
});
