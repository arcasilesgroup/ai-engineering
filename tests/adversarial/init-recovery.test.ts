// Adversarial: the uninstall→init recovery path.
// `uninstall` (scope "This project") deletes .ai-engineering/ai-eng.lock but keeps
// config.toml; init then reads config.toml as "already governed", hands off to
// update, and update aborts with "no ai-eng.lock — run ai-eng init first".
// So: init --yes must re-install from that state and exit 0. Second check: a canon
// without version.json is intact-looking — health must be proven, not guessed from
// one marker file. Third check: mirrors on a clean machine must receive the links
// (a mirror dir whose PARENT is mkdir'd but not the dir itself makes every
// symlinkSync fail into the silent catch). Fourth check: version.json also holds
// the REGISTRY version from the notice cache, so health is canonDrift(), a byte
// comparison init and doctor share, never a version marker. Fifth: the picker
// offers only surfaces that have a generator — a declaration in config.toml with
// nothing to enforce it is a governance claim, not a surface.
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

/** Same run, another repo and another machine home — for the tests whose state is a
 *  missing canon, which the shared home cannot be (every other test needs it there).
 *  `input` is the scripted keypress queue src/ui.ts replays into clack's prompts. */
function engAt(cwd: string, engHomeDir: string, args: string[], input: string): { status: number; stdout: string; stderr: string } {
  const r = spawnSync(process.execPath, [cli, ...args], {
    cwd,
    encoding: "utf8",
    env: { ...process.env, AI_ENG_HOME: engHomeDir, NO_COLOR: "1", CI: "1", AI_ENG_NO_UPDATE_NOTICES: "1" },
    input,
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
  // The claude-code carrier is the MACHINE's now: the repo keeps only the two hosts whose
  // readers live in the checkout, and this one reads from the user's home.
  expect(existsSync(join(engHome, ".claude", "settings.json"))).toBe(true);
  expect(existsSync(join(repo, ".claude", "settings.json"))).toBe(false);
});

test("an intact-looking canon without version.json is repaired, not skipped", () => {
  // A canon with its marker files intact but an empty version.json must be
  // repaired and given the real version, never reported as "unknown".
  const marker = join(engHome, "skills", "ai-brainstorm", "SKILL.md");
  expect(existsSync(marker)).toBe(true); // intact-looking
  expect(existsSync(join(engHome, "version.json"))).toBe(true); // repaired by run #1
  const doc = JSON.parse(readFileSync(join(engHome, "version.json"), "utf8")) as { version: string };
  expect(doc.version).not.toBe("");
  expect(doc.version).not.toBe("unknown");
});

test("a canon missing payload files is repaired, not called intact", () => {
  // A canon missing payload files must be repaired, not called intact: one marker
  // file is not a measurement, and health is a byte comparison against the payload.
  rmSync(join(engHome, "skills", "ai-goal"), { recursive: true, force: true });
  const run = eng(["init", "--yes"]);
  expect(run.stdout + run.stderr).toInclude("re-installing");
  expect(existsSync(join(engHome, "skills", "ai-goal", "SKILL.md"))).toBe(true);
  expect(run.status).toBe(0);
});

test("the intact line never reports a version the canon does not have", () => {
  // version.json doubles as the notice cache, so it can hold the REGISTRY
  // version. init must report the installed canon's version, never the registry's:
  // printing the registry version is a lie that also hides drift.
  writeFileSync(join(engHome, "version.json"), JSON.stringify({ version: "9.9.9", ts: Date.now() }));
  const run = eng(["init", "--yes"]);
  const out = run.stdout + run.stderr;
  expect(out).toInclude("global canon intact");
  expect(out).not.toInclude("9.9.9");
});

test("update in the recovery state tells the truth: no 'unknown', no garden jargon", () => {
  // The recovery state: config.toml, no lock, nothing on disk.
  rmSync(join(repo, ".ai-engineering", "ai-eng.lock"), { force: true });
  rmSync(join(repo, ".git", "hooks", "pre-commit"), { force: true });
  rmSync(join(repo, ".claude"), { recursive: true, force: true });
  const run = eng(["update"]);
  const out = run.stdout + run.stderr;
  // Nothing recorded yet must not read as 'unknown': that names a broken install,
  // not an empty record.
  expect(out).not.toInclude("unknown");
  expect(out).toInclude("no ai-eng.lock");
  expect(run.status).toBe(0);
});

test("a clean machine gets real skill mirrors, not zero-count ghosts", () => {
  // Mirror dirs must exist before each symlink is created: a missing parent makes
  // symlinkSync fail silently.
  const link = join(engHome, ".claude", "skills", "ai-debug");
  expect(existsSync(link)).toBe(true);
  expect(lstatSync(link).isSymbolicLink()).toBe(true);
});

test("a surface that cannot deny tools is refused, never declared in config.toml", () => {
  // Zed ships skills and no hot-path hook; declaring it would be a governance claim
  // with nothing to enforce it (§13). Pi is NOT in this club —
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
  // A repo with only .git counts as a repo, so the missing .ai-engineering/ must
  // produce "run ai-eng init first", not a raw ENOENT.
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
// "previous ours" (update.ts:147). install() must understand it — treating it as a
// literal hash makes "Take the new version everywhere" write 0 files, turns safe
// version-bump updates into false "patched by you" conflicts, and records hashes
// that exist nowhere on disk.
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
  // actually reads. A repo whose own assets are current must not report "all assets
  // current — nothing to sync" over a drifted canon: `update` repairs the global
  // canon too, not only the repo's assets.
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

test("a repo with no machine-side canon is offered it, never handed it (§14.5b)", () => {
  // `uninstall` scope "Everything" removes ~/.ai-engineering and leaves the repo
  // governed. Running `ai-eng init` inside that repo then installed the machine side
  // in silence — a whole-home write the human never asked for. §14.5b path 2:
  // «no global canon — install it now and I continue with the repo, ok?»: offered,
  // and a "no" leaves the machine untouched.
  const freshHome = join(sandbox, "offered-home");
  const freshRepo = join(sandbox, "offered-repo");
  mkdirSync(freshHome, { recursive: true });
  mkdirSync(join(freshRepo, ".ai-engineering"), { recursive: true });
  spawnSync("git", ["init", "-q"], { cwd: freshRepo });
  writeFileSync(join(freshRepo, ".ai-engineering", "config.toml"), '[surfaces]\nenabled = ["claude-code"]\n');
  // Governed and current (installed from the shared home), so the repo phase after a
  // "yes" has nothing to write and cannot stall on a second question.
  expect(engAt(freshRepo, engHome, ["init", "--yes", "--surface", "claude-code"], "").status).toBe(0);

  const refused = engAt(freshRepo, freshHome, ["init"], "n\n");
  // clack wraps the prompt at the terminal width and draws a gutter where it breaks,
  // so the wrap point moves with the length of the sandbox path: in CI the break fell
  // between "install it" and "now", and the assertion passed or failed by where tmpdir
  // happens to be. Read the sentence, not the frame: the box characters and the
  // wrapping are presentation, so strip them before matching.
  const rendered = (refused.stdout + refused.stderr).replace(/[│┌└◇◆●○─]/g, " ").replace(/\s+/g, " ");
  expect(rendered).toInclude("install it now");
  expect(existsSync(join(freshHome, "skills"))).toBe(false);

  const accepted = engAt(freshRepo, freshHome, ["init"], "y\n");
  expect(existsSync(join(freshHome, "skills", "ai-debug", "SKILL.md"))).toBe(true);
  expect(accepted.status).toBe(0);
});

test("the canon is swept of what we no longer ship, and nothing else is touched", () => {
  // The line is the skill folder: inside one we ship, a path the payload does not
  // have is stale and gets swept, and doctor names it. Anything else in the canon
  // home is somebody's.
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
