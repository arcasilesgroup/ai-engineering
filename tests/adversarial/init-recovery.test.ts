// Adversarial: the uninstall→init deadlock (measured 2026-09-03, ~/repos/tests2).
// `uninstall` (scope "This project") deletes .ai-engineering/ai-eng.lock but keeps
// config.toml; init then reads config.toml as "already governed", hands off to
// update, and update aborts with "no ai-eng.lock — run ai-eng init first".
// Neither verb can recover the repo. Regression: init --yes must re-install from the
// recovery state and exit 0. Second check: a canon installed by an older binary has
// no version.json — the "intact" branch printed "ai-eng unknown" and refused to
// repair; health must be proven, not guessed from one marker file. Third check:
// mirrors on a clean machine must receive the links (P0-1: init mkdir'd the mirror
// PARENT, never the mirror dir, so every symlinkSync failed into the silent catch).
import { test, expect, beforeAll, afterAll } from "bun:test";
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, rmSync, writeFileSync, lstatSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const cli = join(import.meta.dir, "..", "..", "src", "cli.ts");
let sandbox: string;
let engHome: string;
let repo: string;

function eng(args: string[]): { status: number; stdout: string; stderr: string } {
  return spawnSync(process.execPath, [cli, ...args], {
    cwd: repo,
    encoding: "utf8",
    env: { ...process.env, AI_ENG_HOME: engHome, NO_COLOR: "1", CI: "1", AI_ENG_NO_UPDATE_NOTICES: "1" },
    input: "",
  });
}

beforeAll(() => {
  sandbox = mkdtempSync(join(tmpdir(), "ai-eng-recover-"));
  engHome = join(sandbox, "home");
  repo = join(sandbox, "repo");
  mkdirSync(engHome, { recursive: true });
  mkdirSync(repo, { recursive: true });
  spawnSync("git", ["init", "-q"], { cwd: repo });
});

afterAll(() => {
  rmSync(sandbox, { recursive: true, force: true });
});

test("init recovers a repo whose lock was uninstalled (no update↔init deadlock)", () => {
  // State `uninstall --scope project` leaves behind: config.toml without a lock.
  mkdirSync(join(repo, ".ai-engineering"), { recursive: true });
  writeFileSync(join(repo, ".ai-engineering", "config.toml"), '[surfaces]\nenabled = ["claude-code"]\n');
  const run = eng(["init", "--yes"]);
  expect(run.stdout + run.stderr).not.toInclude("run ai-eng init first");
  expect(run.status).toBe(0);
  expect(existsSync(join(repo, ".ai-engineering", "ai-eng.lock"))).toBe(true);
  expect(existsSync(join(repo, ".git", "hooks", "pre-commit"))).toBe(true);
  expect(existsSync(join(repo, ".claude", "settings.json"))).toBe(true);
});

test("an intact-looking canon without version.json is repaired, not skipped", () => {
  // The tests2 symptom: "global canon intact · ai-eng unknown · nothing to install".
  const marker = join(engHome, "skills", "ai-brainstorm", "SKILL.md");
  expect(existsSync(marker)).toBe(true); // intact-looking
  expect(existsSync(join(engHome, "version.json"))).toBe(true); // repaired by run #1
  const doc = JSON.parse(readFileSync(join(engHome, "version.json"), "utf8")) as { version: string };
  expect(doc.version).not.toBe("");
  expect(doc.version).not.toBe("unknown");
});

test("update in the recovery state tells the truth: no 'unknown', no garden jargon", () => {
  // Re-enter the state the deadlock created: config.toml, no lock, nothing on disk.
  rmSync(join(repo, ".ai-engineering", "ai-eng.lock"), { force: true });
  rmSync(join(repo, ".git", "hooks", "pre-commit"), { force: true });
  rmSync(join(repo, ".claude"), { recursive: true, force: true });
  const run = eng(["update"]);
  const out = run.stdout + run.stderr;
  // 'unknown' came from previous.version || "unknown": it read as a broken
  // install when the truth was "nothing recorded yet". 'planted' is the
  // internal install.ts metaphor; the user-facing word is installed.
  expect(out).not.toInclude("unknown");
  expect(out).not.toInclude("planted");
  expect(out).toInclude("no ai-eng.lock");
  expect(run.status).toBe(0);
});

test("a clean machine gets real skill mirrors, not zero-count ghosts", () => {
  // P0-1: mirror dirs were never created; every symlink failed silently.
  const link = join(engHome, ".claude", "skills", "ai-debug");
  expect(existsSync(link)).toBe(true);
  expect(lstatSync(link).isSymbolicLink()).toBe(true);
});

// The protocol seam: update.ts hands install() a `sha256:<hex>` sentinel as
// "previous ours" (update.ts:147). install() must understand it — when it didn't,
// "Take the new version everywhere" wrote 0 files, safe version-bump updates
// became false "patched by you" conflicts, and the rebuilt lock recorded hashes
// that were never on disk (measured tests2 2026-09-03).
import { install } from "../../src/install.ts";
import type { PlanEntry } from "../../src/install.ts";
import { createHash } from "node:crypto";

function sha(text: string): string {
  return createHash("sha256").update(text).digest("hex");
}

test('install honors the "sha256:" sentinel: take writes, unedited updates apply', () => {
  const root = join(sandbox, "protocol");
  mkdirSync(join(root, ".claude"), { recursive: true });
  const oldTpl = '{"hooks": "old"}\n';
  const newTpl = '{"hooks": "new"}\n';
  const entry: PlanEntry = { path: ".claude/settings.json", ours: newTpl };

  // Case A — the real take flow: lock holds the hash of the OLD template, disk
  // holds the user's edit (≠ old). install() sees a conflict; update.ts resolves
  // it as "take" and passes the force flag. The file must land as newTpl.
  const theirEdit = oldTpl + "// user tweak\n";
  writeFileSync(join(root, ".claude", "settings.json"), theirEdit);
  const prevOld = (path: string) => (path === entry.path ? `sha256:${sha(oldTpl)}` : null);
  let report = install(root, [entry], prevOld, (path) => path === entry.path);
  expect(report.written).toEqual([".claude/settings.json"]);
  expect(readFileSync(join(root, ".claude", "settings.json"), "utf8")).toBe(newTpl);

  // Case A2 — same conflict, no force (the human said keep / --yes): untouched.
  writeFileSync(join(root, ".claude", "settings.json"), theirEdit);
  report = install(root, [entry], prevOld);
  expect(report.conflicts).toEqual([".claude/settings.json"]);
  expect(readFileSync(join(root, ".claude", "settings.json"), "utf8")).toBe(theirEdit);

  // Case B — safe update: disk is exactly the recorded old version. install()
  // must update it, not raise a conflict.
  writeFileSync(join(root, ".claude", "settings.json"), oldTpl);
  report = install(root, [entry], prevOld);
  expect(report.written).toEqual([".claude/settings.json"]);
  expect(readFileSync(join(root, ".claude", "settings.json"), "utf8")).toBe(newTpl);

  // Case C — an edit NOT in the lock stays untouched: the sentinel must not
  // turn the overwrite into a blind clobber.
  const unrecorded = oldTpl + "// a different edit\n";
  writeFileSync(join(root, ".claude", "settings.json"), unrecorded);
  report = install(root, [entry], (path) => (path === entry.path ? `sha256:${sha("deadbeef".repeat(8))}` : null));
  expect(report.conflicts).toEqual([".claude/settings.json"]);
  expect(readFileSync(join(root, ".claude", "settings.json"), "utf8")).toBe(unrecorded);
});
