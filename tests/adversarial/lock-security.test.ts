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
import { test, expect } from "bun:test";
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, rmSync, writeFileSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, relative } from "node:path";
import { createHash } from "node:crypto";

const cli = join(import.meta.dir, "..", "..", "src", "cli.ts");

/** Every spawned verb gets a home of its own. ai-eng now writes CARRIERS outside the
 *  repo (that is the point of the milestone), so a test that lets a child inherit the
 *  real environment installs hooks into the developer's own ~/.claude — which is exactly
 *  what happened once, and why this constant exists. */
function envWithHome(home: string): Record<string, string> {
  return { ...(process.env as Record<string, string>), AI_ENG_HOME: home, NO_COLOR: "1", CI: "1", AI_ENG_NO_UPDATE_NOTICES: "1" };
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
    // victim's real sha256.
    const escapeKey = relative(repo, victim);
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
    // NO lock: the recovery state. update must install what is absent and leave
    // the user's files alone — and the rebuilt lock must NOT claim them.
    const first = spawnSync(process.execPath, [cli, "update", "--yes"], {
      cwd: repo,
      encoding: "utf8",
      env: envWithHome(join(sandbox, "home")),
      input: "\r",
    });
    expect(first.status).toBe(0);
    // The user's hook is untouched, byte for byte.
    expect(readFileSync(join(repo, ".git", "hooks", "pre-commit"), "utf8")).toBe(husky);
    // A repo settings file is not a plan entry any more: claude-code reads from the
    // machine, so the repo copy — the user's — is not touched at all. The machine copy
    // is where our entries go (carrier-merge.test.ts proves the merge itself).
    expect(readFileSync(join(repo, ".claude", "settings.json"), "utf8")).toBe('{\n  "editor": "vim"\n}\n');
    expect(readFileSync(join(sandbox, "home", ".claude", "settings.json"), "utf8")).toInclude("ai-eng chain PreToolUse");
    const lock = readFileSync(join(repo, ".ai-engineering", "ai-eng.lock"), "utf8");
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
    expect(second.stdout + second.stderr).not.toInclude("patched by you");
    expect(readFileSync(join(repo, ".git", "hooks", "pre-commit"), "utf8")).toBe(husky);
  } finally {
    rmSync(sandbox, { recursive: true, force: true });
  }
});
