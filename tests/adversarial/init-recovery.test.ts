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
import { CANON_OWNERSHIP_NAME, canonDrift } from "../../src/embed.ts";
import { sha256 } from "../../src/install.ts";

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
  const machineSettings = join(engHome, ".claude", "settings.json");
  const machineSettingsBefore = '{\n  "editor": "vim"\n}\n';
  mkdirSync(join(engHome, ".claude"), { recursive: true });
  writeFileSync(machineSettings, machineSettingsBefore);
  const run = eng(["init", "--yes"]);
  const output = run.stdout + run.stderr;
  expect(output).not.toInclude("run ai-eng init first");
  expect(run.status).toBe(0);
  expect(existsSync(join(repo, ".ai-engineering", "ai-eng.lock"))).toBe(true);
  expect(existsSync(join(repo, ".git", "hooks", "pre-commit"))).toBe(true);
  expect(existsSync(join(engHome, "skills", "ai-brainstorm", "SKILL.md"))).toBe(true);
  // The recovered init still reaches the machine side: ours merged in, the user's key kept.
  expect(output).toInclude("~/.claude/settings.json · machine carrier · written");
  const machineSettingsAfter = readFileSync(machineSettings, "utf8");
  expect(machineSettingsAfter).not.toBe(machineSettingsBefore);
  expect(machineSettingsAfter).toMatch(/ai-eng(?:\.cmd|\.exe)? chain/);
  expect((JSON.parse(machineSettingsAfter) as { editor?: unknown }).editor).toBe("vim");
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
  rmSync(join(engHome, "skills", "ai-orchestrator"), { recursive: true, force: true });
  const run = eng(["init", "--yes"]);
  expect(run.stdout + run.stderr).toInclude("re-installing");
  expect(existsSync(join(engHome, "skills", "ai-orchestrator", "SKILL.md"))).toBe(true);
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
  const offered = surfaceOptions().map((surface) => surface.id);
  expect(offered).toEqual(["claude-code", "oh-my-pi", "opencode", "cursor", "codex", "copilot-cli", "pi"]);
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
// "previous ours". A recorded file is ai-eng's and takes the new template, edited or
// not; only seeded config the project edited stays the project's. Treating the
// sentinel as a literal hash would misjudge every seeded config file.
import { install, sha256 as sha } from "../../src/install.ts";
import type { PlanEntry } from "../../src/install.ts";

test('install honors the "sha256:" sentinel: a recorded file takes ours, edited or not; edited seeded config stays', () => {
  const root = join(sandbox, "protocol");
  mkdirSync(join(root, ".claude"), { recursive: true });
  const oldTpl = '{"hooks": "old"}\n';
  const newTpl = '{"hooks": "new"}\n';
  const entry: PlanEntry = { path: ".claude/settings.json", ours: newTpl };
  const prevOld = (path: string) => (path === entry.path ? `sha256:${sha(oldTpl)}` : null);

  // Case A — recorded and edited: ai-eng's file, so it takes the new template.
  writeFileSync(join(root, ".claude", "settings.json"), oldTpl + "// user tweak\n");
  let report = install(root, [entry], prevOld);
  expect(report.written).toEqual([".claude/settings.json"]);
  expect(readFileSync(join(root, ".claude", "settings.json"), "utf8")).toBe(newTpl);

  // Case B — exactly the recorded old version: a plain update.
  writeFileSync(join(root, ".claude", "settings.json"), oldTpl);
  report = install(root, [entry], prevOld);
  expect(report.written).toEqual([".claude/settings.json"]);
  expect(readFileSync(join(root, ".claude", "settings.json"), "utf8")).toBe(newTpl);

  // Case C — never recorded: the project's own file, untouched.
  const unrecorded = oldTpl + "// a different edit\n";
  writeFileSync(join(root, ".claude", "settings.json"), unrecorded);
  report = install(root, [entry], () => null);
  expect(report.yours).toEqual([".claude/settings.json"]);
  expect(readFileSync(join(root, ".claude", "settings.json"), "utf8")).toBe(unrecorded);

  // Case D — seeded config: follows the sentinel while unedited, the project's once edited.
  const config: PlanEntry = { path: [".ai-engineering", "arch.rules.json"].join("/"), ours: "{}\n" };
  mkdirSync(join(root, ".ai-engineering"), { recursive: true });
  writeFileSync(join(root, config.path), "[]\n");
  expect(install(root, [config], () => `sha256:${sha("[]\n")}`).written).toEqual([config.path]);
  writeFileSync(join(root, config.path), '{"mine": 1}\n');
  expect(install(root, [config], () => `sha256:${sha("{}\n")}`).yours).toEqual([config.path]);
  expect(readFileSync(join(root, config.path), "utf8")).toBe('{"mine": 1}\n');
});

test("update repairs missing global canon files and rewrites an edited shipped page", () => {
  const locallyEdited = join(engHome, "skills", "ai-brainstorm", "SKILL.md");
  const shippedBrainstorm = readFileSync(join(import.meta.dir, "../../skills/ai-brainstorm/SKILL.md"));
  const missing = join(engHome, "skills", "ai-debug", "SKILL.md");
  const expectedPayload = readFileSync(join(import.meta.dir, "../../skills/ai-debug/SKILL.md"), "utf8");
  expect(eng(["init", "--yes"]).status).toBe(0);
  expect(existsSync(locallyEdited)).toBe(true);
  expect(existsSync(missing)).toBe(true);

  writeFileSync(locallyEdited, "# locally edited\n");
  rmSync(missing);
  const run = eng(["update", "--yes"]);
  expect(run.stdout + run.stderr).toContain("global canon outdated or incomplete — re-installed");
  expect(run.stdout + run.stderr).not.toContain("local change");
  // The shipped page is ai-eng's: the edit is replaced, the missing file comes back.
  expect(readFileSync(locallyEdited)).toEqual(shippedBrainstorm);
  expect(readFileSync(missing, "utf8")).toBe(expectedPayload);

  // A second update has nothing to repair and leaves zero drift.
  const clean = eng(["update", "--yes"]);
  const cleanOut = clean.stdout + clean.stderr;
  expect(clean.status).toBe(0);
  expect(cleanOut).not.toContain("local change kept");
  expect(cleanOut).not.toContain("global canon repaired");
  expect(cleanOut).not.toContain("re-installed");
  expect(canonDrift(engHome)).toMatchObject({ drift: 0, missing: 0, stale: 0 });
  const doctor = eng(["doctor"]);
  expect(doctor.stdout + doctor.stderr).toContain("0 drift · 0 missing");
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
  // have is stale and doctor names it; update sweeps it only while its bytes match the
  // hash an earlier install recorded writing. Anything else in the canon home is somebody's.
  expect(eng(["init", "--yes"]).status).toBe(0);
  const staleFile = join(engHome, "skills", "ai-visual-recap", "assets", "highlight.js");
  const foreignFile = join(engHome, "skills", "my-own-skill", "SKILL.md");
  mkdirSync(dirname(staleFile), { recursive: true });
  mkdirSync(dirname(foreignFile), { recursive: true });
  writeFileSync(staleFile, "// a file this binary no longer ships\n");
  writeFileSync(foreignFile, "# mine\n");
  // An earlier binary shipped this page and recorded its hash when it wrote it.
  const ownershipPath = join(engHome, CANON_OWNERSHIP_NAME);
  const ownership = existsSync(ownershipPath)
    ? (JSON.parse(readFileSync(ownershipPath, "utf8")) as { files: Record<string, string> })
    : { files: {} as Record<string, string> };
  ownership.files["skills/ai-visual-recap/assets/highlight.js"] = sha256("// a file this binary no longer ships\n");
  writeFileSync(ownershipPath, JSON.stringify(ownership));

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
