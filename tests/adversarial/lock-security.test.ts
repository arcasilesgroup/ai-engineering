// Adversarial: the lock is untrusted input and the ownership ledger (measured
// 2026-09-03, DeepSeek review + PoC).
// 1. Path traversal: `uninstall` sweeps every file the lock's [assets] table
//    declares, keyed by repo-relative path. A crafted lock can key a file OUTSIDE
//    the repo ("../../../Users/x/victim.txt") — parseToml accepts quoted keys, and
//    when the on-disk file's sha256 matches the recorded one the sweep unlinked it.
//    Measured PoC: a lock entry escaped to $HOME and deleted a file outside the
//    repo. The sweep must refuse any path that escapes repoRoot.
// 2. Ownership ledger: with no prior lock (the recovery state), update rebuilt the
//    lock from the FULL plan — recording our template hash for files install()
//    classified as the user's. The next update then reported a false conflict and
//    uninstall would strip a file the binary never owned. The rebuilt lock may
//    only claim files this run actually made ours.
import { test, expect } from "bun:test";
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, rmSync, writeFileSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, relative } from "node:path";
import { createHash } from "node:crypto";

const cli = join(import.meta.dir, "..", "..", "src", "cli.ts");

test("uninstall refuses lock keys that escape the repo (PoC regression)", () => {
  const sandbox = mkdtempSync(join(tmpdir(), "ai-eng-traversal-"));
  const repo = join(sandbox, "repo");
  const victim = join(sandbox, "victim.txt"); // deliberately OUTSIDE the repo
  try {
    mkdirSync(join(repo, ".ai-engineering"), { recursive: true });
    mkdirSync(repo, { recursive: true });
    spawnSync("git", ["init", "-q"], { cwd: repo });
    writeFileSync(victim, "you-are-the-victim\n");
    // The malicious lock: a quoted TOML key that escapes root, keyed with the
    // victim's real sha256 — the exact shape the PoC deleted a file with.
    const escapeKey = relative(repo, victim);
    writeFileSync(
      join(repo, ".ai-engineering", "ai-eng.lock"),
      `version = "2.0.0"\n\n[assets]\n"${escapeKey}" = "${createHash("sha256").update(readFileSync(victim)).digest("hex")}"\n`,
    );
    const run = spawnSync(process.execPath, [cli, "uninstall", "--project"], {
      cwd: repo,
      encoding: "utf8",
      env: { ...process.env, NO_COLOR: "1", CI: "1", AI_ENG_NO_UPDATE_NOTICES: "1" },
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
    writeFileSync(join(repo, ".ai-engineering", "config.toml"), '[surfaces]\nenabled = ["claude-code"]\n');
    // NO lock: the recovery state. update must install what is absent and leave
    // the user's file alone — and the rebuilt lock must NOT claim it.
    const first = spawnSync(process.execPath, [cli, "update", "--yes"], {
      cwd: repo,
      encoding: "utf8",
      env: { ...process.env, NO_COLOR: "1", CI: "1", AI_ENG_NO_UPDATE_NOTICES: "1" },
      input: "\r",
    });
    expect(first.status).toBe(0);
    // The user's file is untouched.
    expect(readFileSync(join(repo, ".claude", "settings.json"), "utf8")).toBe('{\n  "editor": "vim"\n}\n');
    const lock = readFileSync(join(repo, ".ai-engineering", "ai-eng.lock"), "utf8");
    // The lock must not carry the user's file at all.
    expect(lock).not.toInclude(".claude/settings.json");
    // The second update must not report a false conflict over the user's file.
    const second = spawnSync(process.execPath, [cli, "update", "--yes"], {
      cwd: repo,
      encoding: "utf8",
      env: { ...process.env, NO_COLOR: "1", CI: "1", AI_ENG_NO_UPDATE_NOTICES: "1" },
      input: "\r",
    });
    expect(second.status).toBe(0);
    expect(second.stdout + second.stderr).not.toInclude("patched by you");
  } finally {
    rmSync(sandbox, { recursive: true, force: true });
  }
});
