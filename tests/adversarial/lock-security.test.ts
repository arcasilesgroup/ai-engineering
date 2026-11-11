// Adversarial: the lock is untrusted input and the ownership ledger.
// 1. Path traversal: `uninstall` sweeps every file the lock's [assets] table
//    declares, keyed by repo-relative path. A crafted lock can key a file OUTSIDE
//    the repo ("../../../Users/x/victim.txt") — TOML keys may be quoted, and
//    when the on-disk file's sha256 matches the recorded one the sweep unlinks it.
//    The sweep must refuse any path that escapes repoRoot.
// 2. Ownership ledger: with no prior lock (the recovery state), update must rebuild
//    the lock only from files this run actually made ours — rebuilding it from the
//    FULL plan records our template hash for files install() classified as the
//    user's, and the next update reports a false conflict while uninstall strips a
//    file the binary never owned.
import { test, expect, spyOn } from "bun:test";
import { spawnSync } from "node:child_process";
import { existsSync, linkSync, lstatSync, mkdirSync, mkdtempSync, readFileSync, readlinkSync, rmSync, symlinkSync, writeFileSync } from "node:fs";
import * as fs from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, relative, sep } from "node:path";
import { createHash } from "node:crypto";
import { installMachineCarriers } from "../../src/surfaces/carriers-install.ts";
import { refuseLine } from "../../src/commands/init-shared.ts";

const cli = join(import.meta.dir, "..", "..", "src", "cli.ts");

/** Every spawned verb gets a home of its own. ai-eng now writes CARRIERS outside the
 *  repo (that is the point of the milestone), so a test that lets a child inherit the
 *  real environment installs hooks into the developer's own ~/.claude — which is exactly
 *  what happened once, and why this constant exists. */
function envWithHome(home: string): Record<string, string> {
  return { ...(process.env as Record<string, string>), AI_ENG_HOME: home, NO_COLOR: "1", CI: "1", AI_ENG_NO_UPDATE_NOTICES: "1" };
}

type AliasType = "symlink" | "hard-link";

type MachineAlias = {
  statePath: string;
  settingsPath: string;
  stateBytes: Buffer;
  aliasType: AliasType;
};

const MACHINE_STATE_BYTES = Buffer.from('{\n  "version": "user-owned",\n  "carriers": { "opencode": "previous" }\n}\n');
// Windows stores a relative symlink target with backslashes, whatever separator it was given.
const MACHINE_LINK_TARGET = join("..", "machine.json");

function createMachineAlias(home: string, aliasType: AliasType, stateBytes = MACHINE_STATE_BYTES): MachineAlias {
  const statePath = join(home, "machine.json");
  const settingsPath = join(home, ".claude", "settings.json");
  mkdirSync(dirname(settingsPath), { recursive: true });
  writeFileSync(statePath, stateBytes);
  if (aliasType === "symlink") symlinkSync(MACHINE_LINK_TARGET, settingsPath);
  else linkSync(statePath, settingsPath);
  return { statePath, settingsPath, stateBytes, aliasType };
}

function expectMachineAliasPreserved(alias: MachineAlias): void {
  const stateExists = existsSync(alias.statePath);
  const settingsExists = existsSync(alias.settingsPath);
  const settingsEntryExists = (() => {
    try {
      lstatSync(alias.settingsPath);
      return true;
    } catch {
      return false;
    }
  })();
  const settingsIsSymlink = settingsEntryExists && lstatSync(alias.settingsPath).isSymbolicLink();
  const preserved: {
    stateExists: boolean;
    stateBytes: Buffer | null;
    settingsEntryExists: boolean;
    settingsIsSymlink: boolean;
    settingsLinkText: string | null;
    settingsBytes: Buffer | null;
    sharesInode: boolean;
  } = {
    stateExists,
    stateBytes: stateExists ? readFileSync(alias.statePath) : null,
    settingsEntryExists,
    settingsIsSymlink,
    settingsLinkText: settingsIsSymlink ? readlinkSync(alias.settingsPath) : null,
    settingsBytes: settingsExists ? readFileSync(alias.settingsPath) : null,
    sharesInode: stateExists && settingsEntryExists
      ? lstatSync(alias.statePath).ino === lstatSync(alias.settingsPath).ino
      : false,
  };
  expect(preserved).toEqual({
    stateExists: true,
    stateBytes: alias.stateBytes,
    settingsEntryExists: true,
    settingsIsSymlink: alias.aliasType === "symlink",
    settingsLinkText: alias.aliasType === "symlink" ? MACHINE_LINK_TARGET : null,
    settingsBytes: alias.aliasType === "hard-link" || settingsExists ? alias.stateBytes : null,
    sharesInode: alias.aliasType === "hard-link",
  });
}

function createRepo(sandbox: string, isGoverned: boolean): string {
  const repo = join(sandbox, "repo");
  mkdirSync(repo, { recursive: true });
  spawnSync("git", ["init", "-q"], { cwd: repo });
  if (isGoverned) {
    mkdirSync(join(repo, ".ai-engineering"), { recursive: true });
    writeFileSync(join(repo, ".ai-engineering", "config.toml"), '[surfaces]\nenabled = ["opencode"]\n');
  }
  return repo;
}

test("uninstall refuses lock keys that escape the repo", () => {
  const sandbox = mkdtempSync(join(tmpdir(), "ai-eng-traversal-"));
  const repo = join(sandbox, "repo");
  const victim = join(sandbox, "victim.txt"); // deliberately OUTSIDE the repo
  try {
    mkdirSync(join(repo, ".ai-engineering"), { recursive: true });
    mkdirSync(repo, { recursive: true });
    spawnSync("git", ["init", "-q"], { cwd: repo });
    // The gate reads a declaration, not a directory: without config.toml this repo
    // never asked for policy and uninstall refuses before it reads the lock.
    writeFileSync(join(repo, ".ai-engineering", "config.toml"), '[surfaces]\nenabled = ["claude-code"]\n');
    writeFileSync(victim, "you-are-the-victim\n");
    // The malicious lock: a quoted TOML key that escapes root, keyed with the
    // victim's real sha256. Lock keys are "/"-separated; a Windows backslash would be an
    // invalid TOML escape and fail the parse before the sweep is ever reached.
    const escapeKey = relative(repo, victim).split(sep).join("/");
    writeFileSync(
      join(repo, ".ai-engineering", "ai-eng.lock"),
      `version = "2.0.0"\n\n[assets]\n"${escapeKey}" = "${createHash("sha256").update(readFileSync(victim)).digest("hex")}"\n`,
    );
    const run = spawnSync(process.execPath, [cli, "uninstall", "--project"], {
      cwd: repo,
      encoding: "utf8",
      env: envWithHome(join(sandbox, "home")),
      input: "\ry", // scope select + confirm
    });
    expect(run.status).toBe(0);
    // The whole point: the file outside the repo survives.
    expect(existsSync(victim)).toBe(true);
    // And the sweep says why, in plain words.
    expect(run.stdout + run.stderr).toInclude("escapes this repo");
  } finally {
    rmSync(sandbox, { recursive: true, force: true });
  }
});

for (const aliasType of ["symlink", "hard-link"] as const) {
  for (const operation of ["init", "update", "uninstall"] as const) {
    test(`I76: ${operation} preserves an unselected ${aliasType} to machine.json`, () => {
      const sandbox = mkdtempSync(join(tmpdir(), `ai-eng-i76-${operation}-${aliasType}-`));
      const repo = createRepo(sandbox, operation !== "init");
      const home = join(sandbox, "home");
      const alias = createMachineAlias(home, aliasType);
      try {
        const args = operation === "init"
          ? ["init", "--yes", "--surface", "opencode"]
          : operation === "update"
            ? ["update", "--yes"]
            : ["uninstall"];
        const run = spawnSync(process.execPath, [cli, ...args], {
          cwd: repo,
          encoding: "utf8",
          env: envWithHome(home),
          input: operation === "uninstall" ? "\u001b[B\ryyy" : "\r",
        });
        const output = run.stdout + run.stderr;
        expect(run.status, output).toBe(0);
        expectMachineAliasPreserved(alias);
        // The refusal is named, in init/update's words and in uninstall's.
        expect(output).toInclude("~/.claude/settings.json");
        expect(output).toInclude("or it is a hard link with a second name");
      } finally {
        rmSync(sandbox, { recursive: true, force: true });
      }
    });
  }
}

test("I76: an unselected settings link replaced before the machine-state commit is preserved", () => {
  const sandbox = mkdtempSync(join(tmpdir(), "ai-eng-i76-replacement-"));
  const repo = createRepo(sandbox, false);
  const home = join(sandbox, "home");
  const statePath = join(home, "machine.json");
  const settingsPath = join(home, ".claude", "settings.json");
  mkdirSync(dirname(settingsPath), { recursive: true });
  writeFileSync(statePath, MACHINE_STATE_BYTES);
  writeFileSync(settingsPath, '{"user":"keep"}\n');

  const previousCwd = process.cwd();
  const previousHome = process.env["AI_ENG_HOME"];
  const originalWriteFileSync = fs.writeFileSync;
  let wasReplaced = false;
  let report: ReturnType<typeof installMachineCarriers> | undefined;
  process.chdir(repo);
  process.env["AI_ENG_HOME"] = home;
  const writeSpy = spyOn(fs, "writeFileSync").mockImplementation((...args) => {
    if (!wasReplaced && String(args[0]) !== statePath) {
      wasReplaced = true;
      fs.renameSync(settingsPath, `${settingsPath}.before-replacement`);
      fs.symlinkSync(MACHINE_LINK_TARGET, settingsPath);
    }
    return originalWriteFileSync(...args);
  });
  try {
    report = installMachineCarriers(["opencode"]);
    expect(wasReplaced).toBe(true);
    expect(report.refused.map(refuseLine)).toContain(
      "⚠ ~/.claude/settings.json — changed while ai-eng was writing it, or it is a hard link with a second name; left untouched, so this surface runs without guards — run ai-eng init again",
    );
    expectMachineAliasPreserved({ statePath, settingsPath, stateBytes: MACHINE_STATE_BYTES, aliasType: "symlink" });
  } finally {
    writeSpy.mockRestore();
    process.chdir(previousCwd);
    if (previousHome === undefined) delete process.env["AI_ENG_HOME"];
    else process.env["AI_ENG_HOME"] = previousHome;
    rmSync(sandbox, { recursive: true, force: true });
  }
});

test("update rebuilds the lock without claiming user-owned files (recovery state)", () => {
  const sandbox = mkdtempSync(join(tmpdir(), "ai-eng-ledger-"));
  const repo = join(sandbox, "repo");
  try {
    mkdirSync(join(repo, ".ai-engineering"), { recursive: true });
    mkdirSync(join(repo, ".claude"), { recursive: true });
    spawnSync("git", ["init", "-q"], { cwd: repo });
    // A user settings file that is NOT the ai-eng template: no $comment, no hooks.
    writeFileSync(join(repo, ".claude", "settings.json"), '{\n  "editor": "vim"\n}\n');
    // A user-owned floor: husky's own pre-commit. install() never makes this ours, so
    // the lock must never claim it — that is the invariant this test exists for, and a
    // settings file can no longer carry it: ours are MERGED into those by marker now,
    // which makes them ours by entry (see carrier-merge.test.ts).
    mkdirSync(join(repo, ".git", "hooks"), { recursive: true });
    const husky = "#!/bin/sh\n# husky: my own hook\nnpx lint-staged\n";
    writeFileSync(join(repo, ".git", "hooks", "pre-commit"), husky);
    writeFileSync(join(repo, ".ai-engineering", "config.toml"), '[surfaces]\nenabled = ["claude-code"]\n');
    const machineSettings = join(sandbox, "home", ".claude", "settings.json");
    const machineSettingsBefore = '{\n  "user": "keep"\n}\n';
    mkdirSync(join(sandbox, "home", ".claude"), { recursive: true });
    writeFileSync(machineSettings, machineSettingsBefore);
    // NO lock: the recovery state. update must install what is absent and leave
    // the user's files alone — and the rebuilt lock must NOT claim them.
    const first = spawnSync(process.execPath, [cli, "update", "--yes"], {
      cwd: repo,
      encoding: "utf8",
      env: envWithHome(join(sandbox, "home")),
      input: "\r",
    });
    expect(first.status).toBe(0);
    expect(existsSync(join(repo, ".ai-engineering", "overrides.toml"))).toBe(true);
    expect(existsSync(join(repo, ".github", "workflows", "ai-eng-check.yml"))).toBe(true);
    // The user's hook is untouched, byte for byte.
    expect(readFileSync(join(repo, ".git", "hooks", "pre-commit"), "utf8")).toBe(husky);
    // The repo settings are not a plan entry; the machine settings take our entries by
    // marker and keep the user's key.
    expect(readFileSync(join(repo, ".claude", "settings.json"), "utf8")).toBe('{\n  "editor": "vim"\n}\n');
    expect(first.stdout + first.stderr).toInclude("~/.claude/settings.json · machine carrier · written");
    const machineSettingsMerged = readFileSync(machineSettings, "utf8");
    expect(JSON.parse(machineSettingsMerged).user).toBe("keep");
    expect(machineSettingsMerged).toMatch(/ai-eng(?:\.cmd|\.exe)? chain/);
    const lock = readFileSync(join(repo, ".ai-engineering", "ai-eng.lock"), "utf8");
    expect(lock).toInclude('".ai-engineering/overrides.toml"');
    expect(lock).toInclude('".github/workflows/ai-eng-check.yml"');
    // The lock must not carry the user's hook at all.
    expect(lock).not.toInclude(".git/hooks/pre-commit");
    expect(lock).not.toInclude(".claude/settings.json");
    // The second update must not report a false conflict over the user's hook.
    const second = spawnSync(process.execPath, [cli, "update", "--yes"], {
      cwd: repo,
      encoding: "utf8",
      env: envWithHome(join(sandbox, "home")),
      input: "\r",
    });
    expect(second.status).toBe(0);
    expect(second.stdout + second.stderr).not.toInclude("edited since ai-eng wrote it");
    expect(readFileSync(join(repo, ".git", "hooks", "pre-commit"), "utf8")).toBe(husky);
    // A second update is a no-op on the merged machine settings.
    expect(readFileSync(machineSettings, "utf8")).toBe(machineSettingsMerged);
  } finally {
    rmSync(sandbox, { recursive: true, force: true });
  }
  // Two spawned updates: windows-latest needs more than bun's 5 s default, which kills the child (status null).
}, 30_000);
