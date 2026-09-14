// tests/update-command.spec.ts — the two verbs the CLI delegates to and no test
// measured end to end: `update` (re-install this repo's assets from the installed
// binary, zero network) and `upgrade` (frame, inline changelog, hand the install to
// bun/npm).
//
// Every run is sandboxed in a mkdtemp tree: AI_ENG_HOME and PI_CODING_AGENT_DIR so the
// machine half (canon, mirrors, carriers, git templateDir) lands in the temp dir and
// never in the developer's real home, and GIT_CONFIG_GLOBAL so the templateDir write
// never reaches ~/.gitconfig. `upgrade`'s registry read and its install hand-off are
// served by a fake `bun`/`npm` first on PATH — deterministic, offline, and no real
// `bun add -g`. The fake writes down its argv, so what the verb spawned is asserted,
// not inferred.
//
// syncPlan is pure — a directory of prepared files plus a lock's asset map in, the
// verdict out. updateMain runs in-process (its lines are what coverage counts). The
// `--yes` runs need nobody; the prompt runs carry a scripted stdin — the key queue
// tests/cli-ux.test.ts documents and scripts/proof-cli-ux.sh drives through the real CLI.

import { afterAll, afterEach, beforeEach, describe, expect, test } from "bun:test";
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { PassThrough } from "node:stream";
import { syncPlan, updateMain } from "../src/commands/update.ts";
import { changelogSection, installCommand, upgradeMain } from "../src/commands/upgrade.ts";
import { planEntries } from "../src/commands/init-shared.ts";
import { mergeSharedText, sha256 } from "../src/install.ts";
import { VERSION } from "../src/version.ts";
import type { PlanEntry } from "../src/install.ts";

const SANDBOX = mkdtempSync(join(tmpdir(), "ai-eng-update-cmd-"));
const ENG_HOME = join(SANDBOX, "home");
const CWD = process.cwd();
/** A version the registry does not have, so upgrade takes its long path. */
const NEWER = "99.0.0";
const KEYS = ["AI_ENG_HOME", "PI_CODING_AGENT_DIR", "GIT_CONFIG_GLOBAL", "NO_COLOR", "CI", "AI_ENG_NO_UPDATE_NOTICES", "FAKE_MANAGER_LOG", "PATH"] as const;
const saved: Partial<Record<(typeof KEYS)[number], string | undefined>> = {};
let savedStdin: PropertyDescriptor | undefined;

beforeEach(() => {
  for (const key of KEYS) saved[key] = process.env[key];
  mkdirSync(ENG_HOME, { recursive: true });
  process.env.AI_ENG_HOME = ENG_HOME;
  process.env.PI_CODING_AGENT_DIR = join(SANDBOX, "pi-agent");
  process.env.GIT_CONFIG_GLOBAL = join(ENG_HOME, "gitconfig");
  process.env.FAKE_MANAGER_LOG = join(SANDBOX, "manager.log");
  rmSync(process.env.FAKE_MANAGER_LOG, { force: true }); // one log per test, or the argv of the last one lies about this one
  process.env.NO_COLOR = "1";
  process.env.CI = "true";
  process.env.AI_ENG_NO_UPDATE_NOTICES = "1";
});

afterEach(() => {
  process.chdir(CWD);
  if (savedStdin) {
    Object.defineProperty(process, "stdin", savedStdin);
    savedStdin = undefined;
  }
  for (const key of KEYS) {
    const value = saved[key];
    if (value === undefined) delete process.env[key];
    else process.env[key] = value;
  }
});

afterAll(() => {
  rmSync(SANDBOX, { recursive: true, force: true });
});

/** Run something that prints through src/ui.ts and keep what it printed. clack writes
 *  through process.stdout/stderr, so the swap is the whole seam. */
async function captured<T>(run: () => Promise<T>): Promise<{ value: T; out: string; err: string }> {
  const out: string[] = [];
  const err: string[] = [];
  const stdout = process.stdout.write;
  const stderr = process.stderr.write;
  process.stdout.write = ((chunk: string | Uint8Array) => (out.push(String(chunk)), true)) as never;
  process.stderr.write = ((chunk: string | Uint8Array) => (err.push(String(chunk)), true)) as never;
  try {
    return { value: await run(), out: out.join(""), err: err.join("") };
  } finally {
    process.stdout.write = stdout;
    process.stderr.write = stderr;
  }
}

const tick = (ms: number): Promise<void> => {
  const { promise, resolve } = Promise.withResolvers<void>();
  setTimeout(resolve, ms);
  return promise;
};

/** `update`'s prompts get the stream src/ui.ts's scriptedInput() builds from
 *  `process.stdin`. A PassThrough that is NOT a TTY makes it build that wrapper, whose
 *  whole job is replaying the bytes written to it as discrete keypresses, one per tick —
 *  the same queue scripts/proof-cli-ux.sh feeds through the real CLI. */
function pipeStdin(): PassThrough {
  const stream = new PassThrough();
  const descriptor = Object.getOwnPropertyDescriptor(process, "stdin");
  if (descriptor) savedStdin = descriptor;
  Object.defineProperty(process, "stdin", { value: stream, configurable: true, writable: true });
  return stream;
}

/** A keypress as clack reads it. `upgrade` hands its prompt `process.stdin` itself — the
 *  binding inside @clack/core is taken at import, so replacing process.stdin after the
 *  fact does not reach it — and the event is emitted on that stream, which is exactly
 *  what the reader would do with a key pressed in a terminal. */
function press(name: string, sequence: string): void {
  process.stdin.emit("keypress", sequence, { name, sequence, ctrl: name === "cancel" });
}

const DOWN = "\x1b[B";
const ENTER = "\n";
const CANCEL = "\x03";

/** A governed repo: config.toml declares the surface, and .git exists the way any repo
 *  the user actually has one does. The declaration is the MINIMAL one on purpose — it is
 *  the user's bytes, not the template's, which is a state update has to leave alone. */
function governedRepo(name: string): string {
  const repo = join(SANDBOX, name);
  mkdirSync(join(repo, ".ai-engineering"), { recursive: true });
  writeFileSync(join(repo, ".ai-engineering", "config.toml"), '[surfaces]\nenabled = ["claude-code"]\n');
  spawnSync("git", ["init", "-q"], { cwd: repo });
  return repo;
}

/** A repo the binary has already installed into, with one hook patched by hand: the one
 *  state that leaves a decision for the human. */
async function patchedRepo(name: string): Promise<{ repo: string; shim: string; lockPath: string }> {
  const repo = governedRepo(name);
  process.chdir(repo);
  await captured(() => updateMain({ yes: true }));
  const shim = join(repo, ".git", "hooks", "pre-commit");
  writeFileSync(shim, `${readFileSync(shim, "utf8")}\n# my custom bit: pnpm install --frozen\n`);
  return { repo, shim, lockPath: join(repo, ".ai-engineering", "ai-eng.lock") };
}

/** The plan entry for a path, or a loud failure: a fixture that cannot find what the
 *  payload ships is a broken test, not an empty assertion. */
function entryFor(entries: PlanEntry[], path: string): PlanEntry {
  const found = entries.find((entry) => entry.path === path);
  if (!found) throw new Error(`the payload has no entry for ${path}`);
  return found;
}

/** A `bun` and an `npm` first on PATH that answer `pm view`/`view` with a version, record
 *  their argv, and exit with the code the manager would. No registry is ever reached. */
function fakeManagers(name: string): string {
  const bin = join(SANDBOX, name);
  mkdirSync(bin, { recursive: true });
  const script = [
    "#!/bin/sh",
    'printf "%s\\n" "$*" >> "$FAKE_MANAGER_LOG"',
    'case "$1" in',
    "  pm|view) echo " + NEWER + " ;;",
    "  install) exit 4 ;;",
    "  *) exit 0 ;;",
    "esac",
    "",
  ].join("\n");
  for (const manager of ["bun", "npm"]) writeFileSync(join(bin, manager), script, { mode: 0o755 });
  process.env.PATH = `${bin}:${process.env.PATH}`;
  return bin;
}

function managerLog(): string {
  const path = join(SANDBOX, "manager.log");
  return existsSync(path) ? readFileSync(path, "utf8").trimEnd() : "";
}

describe("syncPlan · what the binary decides to write, keep or refuse", () => {
  const entries = planEntries(["claude-code"]);
  const paths = entries.map((entry) => entry.path).sort();

  test("nothing on disk yet is fresh — the whole payload", () => {
    const root = join(SANDBOX, "plan-empty");
    mkdirSync(root, { recursive: true });
    const plan = syncPlan(entries, root, {});
    expect([...plan.fresh].sort()).toEqual(paths);
    expect(plan.current).toEqual([]);
    expect(plan.updates).toEqual([]);
    expect(plan.conflicts).toEqual([]);
    expect(plan.verbatim).toEqual([]);
  });

  test("files byte-identical to ours are current and provably ours (verbatim)", () => {
    const root = join(SANDBOX, "plan-current");
    for (const entry of entries) {
      mkdirSync(dirname(join(root, entry.path)), { recursive: true });
      writeFileSync(join(root, entry.path), entry.ours);
    }
    // A lock from the previous install records DIFFERENT bytes: the file on disk is ours
    // as this binary writes it, so the recorded hash is irrelevant and nothing is planned.
    const previous = Object.fromEntries(entries.map((entry) => [entry.path, sha256(`${entry.ours}\nstale\n`)]));
    const plan = syncPlan(entries, root, previous);
    expect([...plan.current].sort()).toEqual(paths);
    expect([...plan.verbatim].sort()).toEqual(paths);
    expect(plan.updates).toEqual([]);
    expect(plan.fresh).toEqual([]);
    expect(plan.conflicts).toEqual([]);
  });

  test("a file we never installed is the user's own, not a conflict to resolve", () => {
    const root = join(SANDBOX, "plan-users");
    mkdirSync(join(root, ".github", "workflows"), { recursive: true });
    writeFileSync(join(root, ".github/workflows/ai-eng-check.yml"), "name: mine\n");
    const plan = syncPlan(entries, root, {});
    // No lock entry: we have no evidence we ever wrote it, so an edit is not ours to judge.
    expect(plan.current).toEqual([".github/workflows/ai-eng-check.yml"]);
    expect(plan.conflicts).toEqual([]);
    expect(plan.updates).toEqual([]);
  });

  test("the recorded hash decides update from conflict", () => {
    const root = join(SANDBOX, "plan-updates");
    const target = ".github/workflows/ai-eng-check.yml";
    mkdirSync(join(root, ".github", "workflows"), { recursive: true });
    const previousOurs = "on: [push]\n# v previous\n";
    writeFileSync(join(root, target), previousOurs);
    const untouched = syncPlan(entries, root, { [target]: sha256(previousOurs) });
    expect(untouched.updates).toEqual([target]);
    expect(untouched.conflicts).toEqual([]);

    // Same lock, one edit by hand: now the human owns the decision.
    writeFileSync(join(root, target), `${previousOurs}# mine too\n`);
    const edited = syncPlan(entries, root, { [target]: sha256(previousOurs) });
    expect(edited.conflicts).toEqual([target]);
    expect(edited.updates).toEqual([]);
  });

  test("a shared settings file is updated by its merge, never called a conflict", () => {
    const cursor = planEntries(["cursor"]);
    const settings = entryFor(cursor, ".cursor/hooks.json");
    expect(settings.merge).toBe(true);
    const root = join(SANDBOX, "plan-merge");
    mkdirSync(join(root, ".cursor"), { recursive: true });
    const path = join(root, ".cursor/hooks.json");

    // The merge is the update: the file has the user's own keys and no hooks of ours.
    writeFileSync(path, '{\n  "version": 1\n}\n');
    expect(syncPlan(cursor, root, {}).updates).toEqual([settings.path]);

    // Our entries in and a second sync sees nothing left to do — idempotent by merge.
    const merged = mergeSharedText(readFileSync(path, "utf8"), settings.ours);
    if ("refused" in merged) throw new Error(`expected a merge, got ${merged.refused}`);
    writeFileSync(path, merged.text);
    const again = syncPlan(cursor, root, {});
    expect(again.updates).toEqual([]);
    expect(again.current).toEqual([settings.path]);

    // A file that is not JSON is left exactly as it is: not ours to rewrite, not a
    // conflict — the surface simply runs unguarded and the installer says so elsewhere.
    writeFileSync(path, "// hand-written settings\n");
    const refused = syncPlan(cursor, root, {});
    expect(refused.updates).toEqual([]);
    expect(refused.conflicts).toEqual([]);
    expect(refused.current).toEqual([settings.path]);
  });
});

describe("updateMain · rewriting this repo's assets from the binary", () => {
  test("outside a governed repo it refuses with exit 2 and writes nothing", async () => {
    const foreign = join(SANDBOX, "foreign");
    mkdirSync(foreign, { recursive: true });
    process.chdir(foreign);
    const run = await captured(() => updateMain({ yes: true }));
    expect(run.value).toBe(2);
    expect(run.err).toInclude("not in a governed repo");
    expect(existsSync(join(foreign, ".ai-engineering"))).toBe(false);
  });

  test("a governed repo gets its assets, an executable git floor, and a second run changes nothing", async () => {
    const repo = governedRepo("repo-fresh");
    writeFileSync(join(repo, "AGENTS.md"), "# my contract, never yours\n");
    const declaration = '[surfaces]\nenabled = ["claude-code"]\n';
    process.chdir(repo);

    const first = await captured(() => updateMain({ yes: true }));
    expect(first.value).toBe(0);
    expect(first.out).toInclude("assets synced");

    const lockPath = join(repo, ".ai-engineering", "ai-eng.lock");
    const lock = readFileSync(lockPath, "utf8");
    expect(lock).toInclude(`version = "${VERSION}"`);
    expect(lock).toInclude('".git/hooks/pre-commit"');
    expect(lock).toInclude('".github/workflows/ai-eng-check.yml"');
    // What is the user's stays the user's: the declaration is not template-shaped, so the
    // binary has no evidence it ever wrote it and claims nothing in its ledger.
    expect(readFileSync(join(repo, ".ai-engineering", "config.toml"), "utf8")).toBe(declaration);
    expect(lock).not.toInclude(".ai-engineering/config.toml");
    expect(readFileSync(join(repo, "AGENTS.md"), "utf8")).toBe("# my contract, never yours\n");
    // A git shim that is not executable is a git hook that silently never runs.
    expect(statSync(join(repo, ".git", "hooks", "pre-commit")).mode & 0o111).not.toBe(0);
    // The machine half went to the sandbox home — the canon, and claude-code's carrier,
    // which no longer belongs in the repo.
    expect(existsSync(join(ENG_HOME, ".claude", "settings.json"))).toBe(true);
    expect(existsSync(join(repo, ".claude", "settings.json"))).toBe(false);

    const bytes = readFileSync(lockPath, "utf8");
    const mtime = statSync(lockPath).mtimeMs;
    const second = await captured(() => updateMain({ yes: true }));
    expect(second.value).toBe(0);
    expect(second.out).toInclude("assets current");
    expect(second.out).not.toInclude("assets synced");
    expect(readFileSync(lockPath, "utf8")).toBe(bytes);
    expect(statSync(lockPath).mtimeMs).toBe(mtime);
  });

  test("--yes keeps a patched hook: nothing written and the lock left as it was", async () => {
    const { shim, lockPath } = await patchedRepo("repo-patched");
    const bytes = readFileSync(lockPath, "utf8");

    const run = await captured(() => updateMain({ yes: true }));
    expect(run.value).toBe(0);
    expect(run.out).toInclude("your patches stay");
    expect(run.out).toInclude("nothing written");
    // The kept file is named, not silently skipped.
    expect(run.out).toInclude("hooks/pre-commit");
    expect(readFileSync(shim, "utf8")).toInclude("# my custom bit");
    // Nothing written means the ownership ledger is not rewritten either: a run that takes
    // no decision leaves the lock exactly as the previous install left it.
    expect(readFileSync(lockPath, "utf8")).toBe(bytes);
  });

  test("a human who takes the new version gets it written over the patch, and the lock follows", async () => {
    const { shim, lockPath } = await patchedRepo("repo-take");
    const stdin = pipeStdin();

    const run = await captured(async () => {
      const running = updateMain();
      await tick(20);
      // The question reaches the human with the file named inside it: one decision, not N.
      stdin.write(DOWN + ENTER); // down: "Take the new version everywhere"
      await tick(60);
      stdin.write(ENTER); // Apply? — the initial value is yes
      return running;
    });

    expect(run.value).toBe(0);
    expect(run.out).toInclude("What wins?");
    expect(run.out).toInclude("1 conflict resolved");
    expect(readFileSync(shim, "utf8")).toBe(entryFor(planEntries(["claude-code"]), ".git/hooks/pre-commit").ours);
    // Taken by an explicit human decision is owned again: the ledger says so, so the next
    // unattended update compares against the version actually on disk.
    expect(readFileSync(lockPath, "utf8")).toInclude('".git/hooks/pre-commit"');
  });

  test("cancelling Apply writes nothing, even after choosing to keep yours", async () => {
    const { repo, shim, lockPath } = await patchedRepo("repo-cancel");
    const bytes = readFileSync(lockPath, "utf8");
    // Something IS pending, or the keep decision short-circuits and Apply is never asked.
    const missing = join(repo, ".github", "workflows", "ai-eng-check.yml");
    rmSync(missing);
    const stdin = pipeStdin();

    const run = await captured(async () => {
      const running = updateMain();
      await tick(20);
      stdin.write(ENTER); // Enter on the first option: keep mine
      await tick(60);
      stdin.write(CANCEL); // ctrl-c at "Apply?"
      return running;
    });

    expect(run.value).toBe(0);
    expect(run.out).toInclude("Nothing written.");
    expect(readFileSync(shim, "utf8")).toInclude("# my custom bit");
    expect(existsSync(missing)).toBe(false); // the pending asset was not written either
    expect(readFileSync(lockPath, "utf8")).toBe(bytes);
  });

  test("cancelling the conflict question writes nothing at all", async () => {
    const { shim, lockPath } = await patchedRepo("repo-conflict-cancel");
    const bytes = readFileSync(lockPath, "utf8");
    const stdin = pipeStdin();

    const run = await captured(async () => {
      const running = updateMain();
      await tick(20);
      stdin.write(CANCEL); // ctrl-c at "What wins?"
      return running;
    });

    expect(run.value).toBe(0);
    expect(run.out).toInclude("Nothing written.");
    // Not one byte of the patched hook, and not one byte of the ledger.
    expect(readFileSync(shim, "utf8")).toInclude("# my custom bit");
    expect(readFileSync(lockPath, "utf8")).toBe(bytes);
  });

  test("carriers that moved out of the repo are swept, and one we cannot claim is kept and named", async () => {
    const repo = governedRepo("repo-moved");
    mkdirSync(join(repo, ".agents", "hooks"), { recursive: true });
    mkdirSync(join(repo, ".pi", "extensions"), { recursive: true });
    writeFileSync(join(repo, ".agents/hooks/ai-eng.ts"), "#!/usr/bin/env bun\n// ai-eng chain\n");
    writeFileSync(join(repo, ".pi/extensions/ai-eng.ts"), "// hand-written by a person, nothing to do with the product\n");
    process.chdir(repo);

    const run = await captured(() => updateMain({ yes: true }));
    expect(run.value).toBe(0);
    expect(existsSync(join(repo, ".agents/hooks/ai-eng.ts"))).toBe(false);
    expect(run.out).toInclude("moved to the machine");
    // Its bytes are not ours, so it is not ours to delete — and the line says so.
    expect(readFileSync(join(repo, ".pi/extensions/ai-eng.ts"), "utf8")).toInclude("hand-written");
    expect(run.out).toInclude("kept");
  });
});

describe("upgrade · the frame, the changelog, and the hand-off", () => {
  test("the print-command helper chooses by the manager the user picked", () => {
    expect(installCommand("bun", "2.1.0")).toBe("bun add -g ai-engineering@2.1.0");
    expect(installCommand("npm", "2.1.0")).toBe("npm install -g ai-engineering@2.1.0");
  });

  test("the inline changelog section is found, and its absence is answered honestly", () => {
    const root = join(SANDBOX, "changelog");
    mkdirSync(root, { recursive: true });
    const path = join(root, "CHANGELOG.md");
    writeFileSync(path, "# Changes\n\n## 9.9.9\n\n### Added\n\n- a thing\n\n## 9.9.8\n\n- an older thing\n");

    // The section the file actually carries, headings and all — the bug this pins is
    // fixed: `$` under the `m` flag used to close the group on the blank line under the
    // heading, so a real section came back as "" and upgrade printed the URL instead.
    const section = changelogSection(root, "9.9.9");
    expect(section).toBe("### Added\n\n- a thing");

    // A body on the very next line is one section too, not one line of it.
    writeFileSync(path, "# Changes\n\n## 9.9.9\n- the first line of the release notes\n- the second\n\n## 9.9.8\n- old\n");
    expect(changelogSection(root, "9.9.9")).toBe("- the first line of the release notes\n- the second");

    writeFileSync(path, "# Changes\n\n## 9.9.9\n\n### Added\n\n- a thing\n\n## 9.9.8\n\n- an older thing\n");
    expect(changelogSection(root, "9.9.7")).toBeNull();
    // The dots are literal: a version is not a regex, and 9x9x9 is not 9.9.9.
    writeFileSync(path, "## 9x9x9\n\n- nothing to do with that release\n");
    expect(changelogSection(root, "9.9.9")).toBeNull();
    rmSync(path);
    expect(changelogSection(root, "9.9.9")).toBeNull();
  });

  test("offline: the registry read fails, so upgrade says nothing and returns 0", async () => {
    const bin = join(SANDBOX, "bin-offline");
    mkdirSync(bin, { recursive: true });
    for (const manager of ["bun", "npm"]) writeFileSync(join(bin, manager), "#!/bin/sh\nexit 1\n", { mode: 0o755 });
    process.env.PATH = `${bin}:${process.env.PATH}`;

    const run = await captured(() => upgradeMain());
    expect(run.value).toBe(0);
    expect(run.out).toInclude("could not read the registry version");
    expect(run.out).toInclude("Nothing done.");
  });

  test("already the latest: no prompt, no command, nothing done", async () => {
    const bin = join(SANDBOX, "bin-latest");
    mkdirSync(bin, { recursive: true });
    for (const manager of ["bun", "npm"]) writeFileSync(join(bin, manager), `#!/bin/sh\necho ${VERSION}\n`, { mode: 0o755 });
    process.env.PATH = `${bin}:${process.env.PATH}`;

    const run = await captured(() => upgradeMain());
    expect(run.value).toBe(0);
    expect(run.out).toInclude("already the latest");
    expect(run.out).toInclude("Nothing to upgrade.");
  });

  test("a local changelog section renders inline instead of the URL", async () => {
    // The shape matters: the regex only returns a body that starts on the line right under
    // the heading, and only its first line (see the bug pinned in the changelog test), so
    // this is the one input that takes the inline branch at all.
    const cwd = join(SANDBOX, "inline-changelog");
    mkdirSync(cwd, { recursive: true });
    writeFileSync(join(cwd, "CHANGELOG.md"), `# Changes\n\n## ${NEWER}\n- the inline body\n- never rendered\n\n## 1.0.0\n- old\n`);
    process.chdir(cwd);
    fakeManagers("bin-inline");

    const run = await captured(async () => {
      const running = upgradeMain();
      await tick(20);
      press("cancel", CANCEL); // the frame is what is under test, not the choice
      return running;
    });

    expect(run.value).toBe(0);
    expect(run.out).toInclude(`What's new in ${NEWER}`);
    expect(run.out).toInclude("· the inline body"); // the `- ` bullet becomes the frame's mark
    expect(run.out).not.toInclude("blob/main/CHANGELOG.md");
  });

  test("bun chosen: the frame shows what's new and the hand-off runs the command it printed", async () => {
    fakeManagers("bin-bun");

    const run = await captured(async () => {
      const running = upgradeMain();
      await tick(20);
      press("return", ENTER); // the highlighted option: bun
      return running;
    });

    expect(run.value).toBe(0);
    expect(run.out).toInclude(`What's new in ${NEWER}`);
    expect(run.out).toInclude(`bun add -g ai-engineering@${NEWER}`);
    expect(run.out).toInclude("Upgraded");
    expect(run.out).toInclude("ai-eng update");
    expect(managerLog().split("\n")).toEqual(["pm view ai-engineering version", `add -g ai-engineering@${NEWER}`]);
  });

  test("print chosen: the command is printed and nothing is spawned", async () => {
    fakeManagers("bin-print");

    const run = await captured(async () => {
      const running = upgradeMain();
      await tick(20);
      press("down", DOWN);
      press("down", DOWN); // "Just print the command, I'll run it myself"
      press("return", ENTER);
      return running;
    });

    expect(run.value).toBe(0);
    expect(run.out).toInclude(`Run: bun add -g ai-engineering@${NEWER} (or the npm equivalent)`);
    // The registry read is all that ran: no install was handed to any manager.
    expect(managerLog()).toBe("pm view ai-engineering version");
  });

  test("npm chosen and the manager fails: its exit code is the verb's", async () => {
    fakeManagers("bin-npm");

    const run = await captured(async () => {
      const running = upgradeMain();
      await tick(20);
      press("down", DOWN); // npm
      press("return", ENTER);
      return running;
    });

    expect(run.value).toBe(4);
    expect(managerLog().split("\n")).toEqual(["pm view ai-engineering version", `install -g ai-engineering@${NEWER}`]);
  });

  test("a cancelled prompt upgrades nothing", async () => {
    fakeManagers("bin-cancel");

    const run = await captured(async () => {
      const running = upgradeMain();
      await tick(20);
      press("cancel", CANCEL);
      return running;
    });

    expect(run.value).toBe(0);
    expect(run.out).toInclude("Nothing done — upgrade proposes, the human disposes.");
    expect(managerLog()).toBe("pm view ai-engineering version");
  });
});
