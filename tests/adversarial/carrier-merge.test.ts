// Adversarial: the files ai-eng shares with the user. Every carrier that is a settings
// file can be one the user already owns — their hooks, permissions, env — and the one
// thing a governance tool may never do is write our policy over their configuration.
// Merge in by marker, take out by marker, and never touch what cannot be read.

import { describe, test, expect, beforeAll, afterAll } from "bun:test";
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { mergeSharedText, stripSharedText } from "../../src/install.ts";
import { removeMachineCarriers, readMachineState, carrierFiles } from "../../src/surfaces/adapters.ts";
import { sha256 } from "../../src/install.ts";

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

beforeAll(() => {
  sandbox = mkdtempSync(join(tmpdir(), "ai-eng-merge-"));
  // Every git this file spawns — including the fixtures' `git init` — reads a config of
  // our own: the floor's templateDir is a GLOBAL setting, and a test that lets a child
  // write the developer's git config (or read it) is a test that changes the machine.
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
  rmSync(sandbox, { recursive: true, force: true });
});

describe("adversarial · carrier merge (a settings file is the user's)", () => {
  test("two repo carriers: a governed repo keeps Cursor's and Copilot's and nothing else", () => {
    useHome();
    const repo = join(sandbox, "two-carriers");
    mkdirSync(repo, { recursive: true });
    spawnSync("git", ["init", "-q"], { cwd: repo });
    expect(run(["init", "--yes", "--surface", "claude-code,oh-my-pi,opencode,cursor,copilot,codex,pi"], repo).status).toBe(0);
    // Every host that reads from the user's home got its carrier there.
    const machine: string[] = [
      join(home, ".claude", "settings.json"),
      join(home, ".omp", "agent", "hooks", "pre", "ai-eng.ts"),
      join(home, ".config", "opencode", "plugins", "ai-eng.ts"),
      join(home, ".pi", "agent", "extensions", "ai-eng.ts"),
      join(home, ".codex", "hooks.json"),
      join(home, ".copilot", "hooks", "ai-eng.json"),
    ];
    for (const path of machine) expect(existsSync(path)).toBe(true);
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

  test("a template dir the user already had keeps its own hooks, and gets ours beside them", () => {
    useHome();
    const theirs = join(sandbox, "their-template");
    mkdirSync(join(theirs, "hooks"), { recursive: true });
    const theirHook = "#!/bin/sh\n# mine, do not touch\necho hello\n";
    writeFileSync(join(theirs, "hooks", "pre-commit"), theirHook);
    spawnSync("git", ["config", "--global", "init.templateDir", theirs], { env: process.env });
    const repo = join(sandbox, "join-repo");
    mkdirSync(repo, { recursive: true });
    spawnSync("git", ["init", "-q"], { cwd: repo });
    expect(run(["init", "--yes", "--surface", "cursor"], repo).status).toBe(0);
    // The one thing this must never do: overwrite a hook a person wrote. It used to —
    // a directory holding THEIR pre-commit was read as "empty" and force-written.
    expect(readFileSync(join(theirs, "hooks", "pre-commit"), "utf8")).toBe(theirHook);
    // And our floor still arrives: the other two shims are ours, marked.
    for (const shim of ["commit-msg", "pre-push"]) {
      expect(readFileSync(join(theirs, "hooks", shim), "utf8")).toInclude("ai-eng git floor shim");
    }
    expect(spawnSync("git", ["config", "--global", "--get", "init.templateDir"], { encoding: "utf8", env: process.env }).stdout.trim()).toBe(theirs);
  });

  test("codex carrier: an unchanged definition is never rewritten, and a changed one is named", () => {
    useHome();
    const repo = join(sandbox, "codex-repo");
    mkdirSync(repo, { recursive: true });
    spawnSync("git", ["init", "-q"], { cwd: repo });
    expect(run(["init", "--yes", "--surface", "codex"], repo).status).toBe(0);
    const carrier = join(home, ".codex", "hooks.json");
    const first = readFileSync(carrier, "utf8");
    // Two more updates over the same binary: Codex's trust is a hash of this definition,
    // so rewriting it identical bytes would ask a human to re-approve for nothing.
    expect(run(["update", "--yes"], repo).status).toBe(0);
    expect(run(["update", "--yes"], repo).status).toBe(0);
    expect(readFileSync(carrier, "utf8")).toBe(first);
    const state = withHome(() => readMachineState());
    expect(state.carriers["codex"]).toBe(sha256(carrierFiles("codex", "machine")?.main ?? ""));
    // A definition that changed since the record is the one that re-asks for trust, and
    // doctor has to name /hooks — the place the human has to go.
    writeFileSync(join(home, "machine.json"), `${JSON.stringify({ version: "2.0.0", carriers: { codex: "0".repeat(64) } }, null, 2)}\n`);
    const doctor = run(["doctor"], repo);
    const out = doctor.stdout + doctor.stderr;
    expect(out).toInclude("/hooks");
    expect(out).toInclude("carrier definition changed");
    // And a DOWNGRADE is its own line: the carriers are the newer binary's, the chain they
    // call would be the older one, which has no gate.
    writeFileSync(join(home, "machine.json"), `${JSON.stringify({ version: "99.0.0", carriers: { codex: sha256(carrierFiles("codex", "machine")?.main ?? "") } }, null, 2)}\n`);
    const downgraded = run(["doctor"], repo);
    expect((downgraded.stdout + downgraded.stderr)).toInclude("DOWNGRADE");
  });

  test("doctor splits the machine carrier from the repo declaration and from the version state", () => {
    useHome();
    const repo = join(sandbox, "doctor-split");
    mkdirSync(repo, { recursive: true });
    spawnSync("git", ["init", "-q"], { cwd: repo });
    expect(run(["init", "--yes", "--surface", "claude-code,cursor"], repo).status).toBe(0);
    const ok = run(["doctor"], repo);
    const okOut = ok.stdout + ok.stderr;
    // Three separate lines, because they are three separate questions. One "surfaces ok"
    // would let a machine carrier that loads nowhere read as a governed repo.
    expect(okOut).toInclude("machine carrier ~/.claude/settings.json");
    expect(okOut).toInclude("repo carrier .cursor/hooks.json present");
    expect(okOut).toInclude("machine state");
    expect(okOut).toInclude("definitions unchanged");
    // A machine carrier that is gone is a FAIL for a core surface, and it says the action.
    rmSync(join(home, ".claude", "settings.json"));
    const missing = run(["doctor"], repo);
    expect((missing.stdout + missing.stderr)).toInclude("machine carrier ~/.claude/settings.json missing → ai-eng update");
    expect(missing.status).toBe(2);
  });

  test("machine round trip: uninstall's everything scope takes our carriers out and says so", () => {
    useHome();
    const repo = join(sandbox, "round-trip");
    mkdirSync(repo, { recursive: true });
    spawnSync("git", ["init", "-q"], { cwd: repo });
    mkdirSync(join(home, ".claude"), { recursive: true });
    writeFileSync(join(home, ".claude", "settings.json"), '{\n  "env": {\n    "KEEP": "yes"\n  }\n}\n');
    expect(run(["init", "--yes", "--surface", "claude-code,cursor"], repo).status).toBe(0);
    expect(readFileSync(join(home, ".claude", "settings.json"), "utf8")).toInclude("ai-eng chain");
    expect(existsSync(join(home, "machine.json"))).toBe(true);
    // Everything scope: down-arrow to it, then a bare `y` per confirmation (clack answers
    // on the key, not on Enter).
    const out = run(["uninstall"], repo, "\u001b[B\ryyy");
    const text = out.stdout + out.stderr;
    expect(text).toInclude("ai-eng entries removed, yours kept");
    // The sandbox's canon home IS the machine base here, so this scope deletes the whole
    // base — the byte-exact restoration of the user's file is the round trip proven in the
    // test above, which is the one that can measure it.
    expect(existsSync(join(home, ".claude", "settings.json"))).toBe(false);
    expect(existsSync(join(home, "machine.json"))).toBe(false);
  });

  test("user hooks survive init, update and uninstall, and ours leave with us", () => {
    useHome();
    const repo = repoWithUserSettings(USER_SETTINGS);
    const settings = join(home, ".claude", "settings.json");
    const before = JSON.parse(USER_SETTINGS) as Settings;

    expect(run(["init", "--yes", "--surface", "claude-code"], repo).status).toBe(0);
    const afterInit = JSON.parse(readFileSync(settings, "utf8")) as Settings;
    // Everything the user had is still there, value for value.
    expect(afterInit.permissions).toEqual(before.permissions);
    expect(afterInit.env).toEqual(before.env);
    expect(afterInit.hooks?.["SessionStart"]).toEqual(before.hooks?.["SessionStart"]);
    // Their hook, and ours, in the same event, without theirs being eaten.
    const preToolUse = JSON.stringify(afterInit.hooks?.["PreToolUse"]);
    expect(preToolUse).toInclude("my-own-audit.sh");
    expect(preToolUse).toInclude("ai-eng chain PreToolUse");

    // Idempotent: a second install is not a second copy.
    const once = readFileSync(settings, "utf8");
    expect(run(["update", "--yes"], repo).status).toBe(0);
    expect(readFileSync(settings, "utf8")).toBe(once);

    // Project scope sweeps the REPO and stops there: the machine carrier is shared by
    // every repo that declares this surface, so one repo's uninstall has no business
    // taking the hooks out of the user's editor.
    run(["uninstall", "--project"], repo, "\ry");
    expect(readFileSync(settings, "utf8")).toBe(once);

    // The machine scope is the one that takes ours back out, and it leaves exactly what
    // the user had before init touched the file.
    const swept = withHome(() => removeMachineCarriers(["claude-code"]));
    expect(swept.lines.length).toBeGreaterThan(0);
    const afterUninstall = readFileSync(settings, "utf8");
    expect(afterUninstall).not.toInclude("ai-eng chain");
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
    expect(stripSharedText(canonical("my-wrapper.sh -- ai-eng chain PreToolUse"))).toInclude("my-wrapper.sh");
    expect(stripSharedText(canonical("command -v ai-eng >/dev/null 2>&1 && ai-eng chain PreToolUse || exit 0"))).toBe("{}\n");
  });

  test("a compact one-liner is refused rather than reformatted, at strip time too", () => {
    const compact = '{"hooks":{"PreToolUse":[{"hooks":[{"command":"ai-eng chain PreToolUse"}]}]}}';
    expect(stripSharedText(compact)).toBeNull(); // uninstall leaves it alone, said out loud
  });

  test("the merge keeps the file's own indentation and trailing newline", () => {
    const four = mergeSharedText('{\n    "env": {\n        "A": "1"\n    }\n}\n', '{"hooks":{"PreToolUse":[]}}');
    expect("refused" in four).toBe(false);
    if ("refused" in four) return;
    expect(four.text).toInclude('\n    "hooks"');
    expect(four.text.endsWith("}\n")).toBe(true);
  });

  test("a settings file that is valid JSON but not an object is refused, not rewritten", () => {
    useHome();
    const repo = repoWithUserSettings('["not", "an", "object"]\n');
    const settings = join(home, ".claude", "settings.json");
    const result = run(["init", "--yes", "--surface", "claude-code"], repo);
    expect(result.status).toBe(0);
    expect(readFileSync(settings, "utf8")).toBe('["not", "an", "object"]\n');
    expect(result.stdout + result.stderr).toInclude("not a JSON object");
  });

  test("a fresh repo still gets the whole template, banner and all", () => {
    useHome();
    const repo = join(sandbox, "fresh");
    mkdirSync(repo, { recursive: true });
    spawnSync("git", ["init", "-q"], { cwd: repo });
    expect(run(["init", "--yes", "--surface", "claude-code"], repo).status).toBe(0);
    const settings = JSON.parse(readFileSync(join(home, ".claude", "settings.json"), "utf8")) as { $comment?: string; hooks?: unknown };
    expect(settings.$comment).toInclude("ai-eng");
    expect(JSON.stringify(settings.hooks)).toInclude("ai-eng chain PreToolUse");
    expect(existsSync(join(repo, ".claude"))).toBe(false); // the carrier is not the repo's copy
  });
});
