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
// Fourth check (2026-09-10): that marker file also carried the REGISTRY version from
// the notice cache, and nothing measured the canon — "intact · nothing to install"
// printed over 34 deleted files. Health is now canonDrift(), a byte comparison init
// and doctor share. Fifth (2026-09-10): the picker offered seven surfaces while only
// three had a generator — a declaration in config.toml with nothing to enforce it.
import { test, expect, beforeAll, afterAll } from "bun:test";
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, rmSync, writeFileSync, lstatSync, readFileSync } from "node:fs";
import { dirname } from "node:path";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { surfaceOptions } from "../../src/commands/init-shared.ts";

const cli = join(import.meta.dir, "..", "..", "src", "cli.ts");
let sandbox: string;
let engHome: string;
let repo: string;

function eng(args: string[]): { status: number; stdout: string; stderr: string } {
  const r = spawnSync(process.execPath, [cli, ...args], {
    cwd: repo,
    encoding: "utf8",
    env: { ...process.env, AI_ENG_HOME: engHome, NO_COLOR: "1", CI: "1", AI_ENG_NO_UPDATE_NOTICES: "1" },
    input: "",
  });
  return { status: r.status ?? 0, stdout: r.stdout ?? "", stderr: r.stderr ?? "" };
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

test("a canon missing payload files is repaired, not called intact", () => {
  // The 2026-09-10 symptom: init printed "global canon intact · nothing to
  // install" over a canon with 34 files deleted — it probed one marker file
  // instead of measuring. Health is now a byte comparison against the payload.
  rmSync(join(engHome, "skills", "ai-goal"), { recursive: true, force: true });
  const run = eng(["init", "--yes"]);
  expect(run.stdout + run.stderr).toInclude("re-installing");
  expect(existsSync(join(engHome, "skills", "ai-goal", "SKILL.md"))).toBe(true);
  expect(run.status).toBe(0);
});

test("the intact line never reports a version the canon does not have", () => {
  // version.json doubles as the notice cache, so it can hold the REGISTRY
  // version. init used to print it as the installed canon's ("ai-eng 3.1.4"
  // over a 2.0.0 canon, 2026-09-10) and the lie also hid drift.
  writeFileSync(join(engHome, "version.json"), JSON.stringify({ version: "9.9.9", ts: Date.now() }));
  const run = eng(["init", "--yes"]);
  const out = run.stdout + run.stderr;
  expect(out).toInclude("global canon intact");
  expect(out).not.toInclude("9.9.9");
});

test("update in the recovery state tells the truth: no 'unknown', no garden jargon", () => {
  // Re-enter the state the deadlock created: config.toml, no lock, nothing on disk.
  rmSync(join(repo, ".ai-engineering", "ai-eng.lock"), { force: true });
  rmSync(join(repo, ".git", "hooks", "pre-commit"), { force: true });
  rmSync(join(repo, ".claude"), { recursive: true, force: true });
  const run = eng(["update"]);
  const out = run.stdout + run.stderr;
  // 'unknown' came from previous.version || "unknown": it read as a broken install
  // when the truth was "nothing recorded yet".
  expect(out).not.toInclude("unknown");
  expect(out).toInclude("no ai-eng.lock");
  expect(run.status).toBe(0);
});

test("a clean machine gets real skill mirrors, not zero-count ghosts", () => {
  // P0-1: mirror dirs were never created; every symlink failed silently.
  const link = join(engHome, ".claude", "skills", "ai-debug");
  expect(existsSync(link)).toBe(true);
  expect(lstatSync(link).isSymbolicLink()).toBe(true);
});

test("a surface that cannot deny tools is refused, never declared in config.toml", () => {
  // Zed ships skills and no hot-path hook; declaring it would be a governance claim
  // with nothing to enforce it (§13, measured 2026-09-10). Pi is NOT in this club —
  // its tool_call event can block, so it has an adapter.
  const fresh = join(sandbox, "no-adapter-repo");
  mkdirSync(fresh, { recursive: true });
  spawnSync("git", ["init", "-q"], { cwd: fresh });
  const r = spawnSync(process.execPath, [cli, "init", "--yes", "--surface", "zed"], {
    cwd: fresh,
    encoding: "utf8",
    env: { ...process.env, AI_ENG_HOME: engHome, NO_COLOR: "1", CI: "1", AI_ENG_NO_UPDATE_NOTICES: "1" },
    input: "",
  });
  expect((r.stdout ?? "") + (r.stderr ?? "")).toInclude("cannot deny tools");
  expect(r.status).toBe(2);
  expect(existsSync(join(fresh, ".ai-engineering", "config.toml"))).toBe(false);
});

test("init offers only the surfaces that generate files", () => {
  const offered = surfaceOptions().flatMap((group) => group.items.map((s) => s.id));
  expect(offered).toEqual(["claude-code", "oh-my-pi", "opencode", "pi", "cursor", "codex", "copilot"]);
});

test("config --add in a bare repo says 'run ai-eng init first', not ENOENT", () => {
  // Measured 2026-09-10: repoRoot() answered yes for a repo with only .git, and
  // writeFileSync died on the missing .ai-engineering/ with a raw ENOENT.
  const bare = join(sandbox, "bare-repo");
  mkdirSync(bare, { recursive: true });
  spawnSync("git", ["init", "-q"], { cwd: bare });
  const r = spawnSync(process.execPath, [cli, "config", "--add", "oh-my-pi"], {
    cwd: bare,
    encoding: "utf8",
    env: { ...process.env, AI_ENG_HOME: engHome, NO_COLOR: "1", CI: "1", AI_ENG_NO_UPDATE_NOTICES: "1" },
    input: "",
  });
  const out = (r.stdout ?? "") + (r.stderr ?? "");
  expect(out).toInclude("run ai-eng init first");
  expect(out).not.toInclude("ENOENT");
  expect(r.status).toBe(2);
});

// The protocol seam: update.ts hands install() a `sha256:<hex>` sentinel as
// "previous ours" (update.ts:147). install() must understand it — when it didn't,
// "Take the new version everywhere" wrote 0 files, safe version-bump updates
// became false "patched by you" conflicts, and the rebuilt lock recorded hashes
// that were never on disk (measured tests2 2026-09-03).
import { install, sha256 as sha } from "../../src/install.ts";
import type { PlanEntry } from "../../src/install.ts";

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

test("update repairs a drifted global canon, not only the repo's assets", () => {
  // The machine side is half of what ai-eng installed, and it is the half a surface
  // actually reads. A repo whose own assets were current reported "all assets
  // current — nothing to sync" over a canon with twenty drifted skills; repairing
  // it was `init --global`'s job alone, which nobody should have to know.
  const installed = join(engHome, "skills", "ai-plan", "SKILL.md");
  expect(eng(["init", "--yes"]).status).toBe(0);
  expect(existsSync(installed)).toBe(true);
  const original = readFileSync(installed, "utf8");

  writeFileSync(installed, "# drifted by hand\n");
  const run = eng(["update", "--yes"]);
  expect(run.stdout + run.stderr).toContain("global canon outdated or incomplete");
  expect(readFileSync(installed, "utf8")).toBe(original);

  const doctor = eng(["doctor"]);
  expect(doctor.stdout + doctor.stderr).toContain("0 drift");
});

test("the canon is swept of what we no longer ship, and nothing else is touched", () => {
  // Renaming an asset inside a skill left the old file in every installed canon
  // forever: canonDrift only walked the payload, so an orphan was invisible and
  // doctor reported 101/101 clean with it sitting there (measured 2026-09-11).
  // The line is the skill folder: inside one we ship, a path the payload no longer
  // has is stale and gets swept. Anything else in the canon home is somebody's.
  expect(eng(["init", "--yes"]).status).toBe(0);
  const staleFile = join(engHome, "skills", "ai-visual-recap", "assets", "highlight.js");
  const foreignFile = join(engHome, "skills", "my-own-skill", "SKILL.md");
  mkdirSync(dirname(staleFile), { recursive: true });
  mkdirSync(dirname(foreignFile), { recursive: true });
  writeFileSync(staleFile, "// a file this binary no longer ships\n");
  writeFileSync(foreignFile, "# mine\n");

  const dirty = eng(["doctor"]);
  expect(dirty.stdout + dirty.stderr).toContain("stale");

  const run = eng(["update", "--yes"]);
  expect(run.status).toBe(0);
  expect(existsSync(staleFile)).toBe(false);   // ours: swept
  expect(existsSync(foreignFile)).toBe(true);  // theirs: never touched

  const clean = eng(["doctor"]);
  expect(clean.stdout + clean.stderr).not.toContain("stale");
  expect(clean.stdout + clean.stderr).toContain("0 drift");
});
