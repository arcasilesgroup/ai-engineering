// tests/floor-hooks.spec.ts — the git floor, driven through its public surface.
//
// The floor is what the 3-line shims exec into, and it runs for a person committing
// from Vim as much as for an agent (§13.2). What a hook decides is only observable
// three ways: the `{ ok, lines }` it returns, the files it writes (a receipt, the
// amended commit message), and the exit code `floor()` hands back to git. Every test
// below asserts one of those three — never an internal, never "did not throw".
//
// No network, no real repo, no real home: throwaway `git init` repos in mkdtemp(), a
// sandboxed AI_ENG_HOME, and a `gitleaks` shim on PATH whose exit code and output are
// the only thing that varies (the real gitleaks is not a dependency of this suite).

import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, spyOn, test } from "bun:test";
import { spawnSync } from "node:child_process";
import * as fs from "node:fs";
import { chmodSync, cpSync, existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, utimesSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { commitMsg, preCommit, prePush } from "../src/floor/index.ts";
import { floor } from "../src/floor/entry.ts";
import { resolveContext } from "../src/git/context.ts";
import { compileGitleaksShim, gitleaksInstallHint, pathWithOnlyGit, useGitleaksShim } from "./fixtures/gitleaks-shim.ts";

const SECRET = "AKIAIOSFODNN7EXAMPLE";
const roots: string[] = [];
const HOME_BEFORE = process.env.AI_ENG_HOME;
const PATH_BEFORE = process.env.PATH ?? "";
const CWD_BEFORE = process.cwd();
let templateRoot = "";
let shimDir = "";
const repoTemplates = new Map<boolean, string>();

beforeAll(() => {
  process.env.AI_ENG_HOME = mkdtempSync(join(tmpdir(), "ai-eng-floor-home-"));
  shimDir = compileGitleaksShim();
  templateRoot = mkdtempSync(join(tmpdir(), "ai-eng-floor-template-"));
  for (const governed of [false, true]) {
    const dir = join(templateRoot, governed ? "governed" : "foreign");
    mkdirSync(dir);
    run("git", dir, ["init", "-q"]);
    run("git", dir, ["config", "user.email", "floor@example.com"]);
    run("git", dir, ["config", "user.name", "floor test"]);
    run("git", dir, ["config", "commit.gpgsign", "false"]);
    if (governed) {
      mkdirSync(join(dir, ".ai-engineering"), { recursive: true });
      writeFileSync(join(dir, ".ai-engineering", "config.toml"), '[surfaces]\nenabled = ["claude-code"]\n');
    }
    repoTemplates.set(governed, dir);
  }
});
afterAll(() => {
  if (HOME_BEFORE === undefined) delete process.env.AI_ENG_HOME;
  else process.env.AI_ENG_HOME = HOME_BEFORE;
  if (templateRoot) rmSync(templateRoot, { recursive: true, force: true });
  if (shimDir) rmSync(shimDir, { recursive: true, force: true });
});
beforeEach(() => {
  process.env.PATH = PATH_BEFORE;
});
afterEach(() => {
  process.chdir(CWD_BEFORE);
  process.env.PATH = PATH_BEFORE;
  for (const root of roots.splice(0)) rmSync(root, { recursive: true, force: true });
});

function tempDir(prefix: string): string {
  const dir = mkdtempSync(join(tmpdir(), prefix));
  roots.push(dir);
  return dir;
}

function run(bin: string, cwd: string, args: string[]): { status: number; stdout: string; stderr: string } {
  const done = spawnSync(bin, args, { cwd, encoding: "utf8" });
  if (done.status !== 0 && bin === "git") throw new Error(`git ${args.join(" ")} failed: ${done.stderr}`);
  return { status: done.status ?? 1, stdout: done.stdout ?? "", stderr: done.stderr ?? "" };
}

/** A throwaway repo. `governed` writes the declaration `.ai-engineering/config.toml`
 *  — the only thing that makes the floor judge a commit at all (§A). */
function tempRepo(governed: boolean): string {
  const parent = tempDir(governed ? "ai-eng-floor-repo-" : "ai-eng-floor-foreign-");
  const dir = join(parent, "repo");
  const template = repoTemplates.get(governed);
  if (!template) throw new Error(`missing ${governed ? "governed" : "foreign"} Git fixture template`);
  cpSync(template, dir, { recursive: true });
  return dir;
}

function write(root: string, name: string, content: string): string {
  const path = join(root, name);
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, content);
  return path;
}

/** Declares `[git] base` so pre-push, which denies when no base resolves, reaches the scan. */
function declareBase(root: string): void {
  write(root, ".ai-engineering/config.toml", '[surfaces]\nenabled = ["claude-code"]\n\n[git]\nbase = "main"\n');
}

function stage(root: string, files: Record<string, string>): void {
  for (const [name, content] of Object.entries(files)) write(root, name, content);
  run("git", root, ["add", ...Object.keys(files)]);
}

/** A `gitleaks` stand-in: `version` is what the floor probes for, and the scan finds
 *  the marker token only when the scanned surface actually carries it. Both outcomes
 *  come from this shim's exit code and output, so the suite runs with or without the
 *  real binary installed. */
function installGitleaksShim(): void {
  useGitleaksShim(shimDir, { mode: "grep" }, PATH_BEFORE);
}

/** The stand-in that reads history the way `gitleaks git` does: the --log-opts range, or
 *  every ref when none is given. `record` captures the argv the floor handed it. */
function installHistoryShim(record?: string): void {
  useGitleaksShim(shimDir, record === undefined ? { mode: "history" } : { mode: "history", record }, PATH_BEFORE);
}

const ZERO = "0".repeat(40);

/** A repo whose remote already has its base: origin/main tracks the first commit and is
 *  the remote's default branch, and the work happens on `feature`. The fixture carries no
 *  hooks, so its commits never run whatever floor this machine has installed. */
function publishedRepo(): { repo: string; base: string } {
  const repo = tempRepo(true);
  rmSync(join(repo, ".git", "hooks"), { recursive: true, force: true });
  const base = commitFile(repo, "README.md", "base\n");
  run("git", repo, ["remote", "add", "origin", join(repo, "unused-remote.git")]);
  run("git", repo, ["update-ref", "refs/remotes/origin/main", base]);
  run("git", repo, ["symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main"]);
  run("git", repo, ["checkout", "-q", "-b", "feature"]);
  return { repo, base };
}

function commitFile(repo: string, name: string, content: string): string {
  write(repo, name, content);
  run("git", repo, ["add", name]);
  run("git", repo, ["commit", "-q", "-m", `test: add ${name}`]);
  return run("git", repo, ["rev-parse", "HEAD"]).stdout.trim();
}

/** Sets the lines git would hand pre-push for the duration of `body`. */
function pushing<T>(lines: string[], body: () => T): T {
  const previous = process.env.AI_ENG_PUSH_REFS;
  process.env.AI_ENG_PUSH_REFS = lines.join("\n");
  try {
    return body();
  } finally {
    if (previous === undefined) delete process.env.AI_ENG_PUSH_REFS;
    else process.env.AI_ENG_PUSH_REFS = previous;
  }
}

/** A PATH with git and nothing else — how "gitleaks is not installed" is proved
 *  without depending on what this machine happens to have in /opt/homebrew. */
function pathWithoutGitleaks(): void {
  process.env.PATH = pathWithOnlyGit();
}

function captureStderr(): { text: () => string; restore: () => void } {
  const chunks: string[] = [];
  const spy = spyOn(process.stderr, "write").mockImplementation(((chunk: string) => {
    chunks.push(String(chunk));
    return true;
  }) as never);
  return { text: () => chunks.join(""), restore: () => spy.mockRestore() };
}

describe("preCommit — diff --check, then the staged-secret scan, then DECISIONS.md", () => {
  test("refuses a staged trailing-whitespace diff and names the file", () => {
    const repo = tempRepo(true);
    installGitleaksShim();
    stage(repo, { "note.txt": "line with trailing spaces   \n" });

    const result = preCommit(repo);

    expect(result.ok).toBe(false);
    expect(result.lines[0]).toBe("diff --check found whitespace problems:");
    expect(result.lines[1]).toContain("note.txt");
    expect(result.lines[1]).toContain("trailing whitespace.");
  });

  test("refuses a staged leftover conflict marker", () => {
    const repo = tempRepo(true);
    installGitleaksShim();
    stage(repo, { "conflict.txt": "a\n<<<<<<< HEAD\nb\n=======\nc\n>>>>>>> other\n" });

    const result = preCommit(repo);

    expect(result.ok).toBe(false);
    expect(result.lines[1]).toContain("leftover conflict marker");
  });

  test("passes a clean commit once the staged blobs scan clean", () => {
    const repo = tempRepo(true);
    installGitleaksShim();
    stage(repo, { "clean.txt": "nothing to see here\n" });

    expect(preCommit(repo)).toEqual({ ok: true, lines: [] });
  });

  test("passes an empty index — nothing staged, nothing to judge", () => {
    const repo = tempRepo(true);
    installGitleaksShim();

    expect(preCommit(repo)).toEqual({ ok: true, lines: [] });
  });

  test("refuses a staged secret and reports the finding, not the scratch path", () => {
    const repo = tempRepo(true);
    installGitleaksShim();
    stage(repo, { "config.env": `AWS_ACCESS_KEY_ID=${SECRET}\n` });

    const result = preCommit(repo);

    expect(result.ok).toBe(false);
    expect(result.lines[0]).toBe("gitleaks: secret in the staged files → BLOCKED.");
    expect(result.lines[1]).toContain("RuleID:");
    expect(result.lines[1]).toContain("aws-access-token");
    expect(result.lines[1]).toContain("<staged>");
  });

  test("HARD FAILS when gitleaks is not on PATH — never silent degradation (§12.1)", () => {
    const repo = tempRepo(true);
    stage(repo, { "clean.txt": "clean\n" });
    pathWithoutGitleaks();

    const result = preCommit(repo);

    expect(result.ok).toBe(false);
    expect(result.lines).toContain("gitleaks is not installed — HARD FAIL, never silent degradation (§12.1).");
    expect(result.lines).toContain(`Install it: ${gitleaksInstallHint()}`);
  });

  test("requires a DECISIONS.md block when the commit is wider than 10 files", () => {
    const repo = tempRepo(true);
    installGitleaksShim();
    const many: Record<string, string> = {};
    for (let i = 1; i <= 11; i += 1) many[`file-${i}.txt`] = `content ${i}\n`;
    stage(repo, many);

    const result = preCommit(repo);

    expect(result.ok).toBe(false);
    expect(result.lines[0]).toContain("this commit touches 11 files");
    expect(result.lines[0]).toContain("requires a DECISIONS.md block (§9.2) — none exists.");
  });

  test("requires a DECISIONS.md block when a dependency is staged, even alone", () => {
    const repo = tempRepo(true);
    installGitleaksShim();
    stage(repo, { "package.json": '{ "name": "fixture" }\n' });

    const result = preCommit(repo);

    expect(result.ok).toBe(false);
    expect(result.lines[0]).toContain("this commit touches 1 files (or a dependency)");
  });

  test("refuses a DECISIONS.md that carries no D-block", () => {
    const repo = tempRepo(true);
    installGitleaksShim();
    stage(repo, { "package.json": '{ "name": "fixture" }\n', "DECISIONS.md": "# Decisions\n\nnothing to see here\n" });

    const result = preCommit(repo);

    expect(result.ok).toBe(false);
    expect(result.lines[0]).toBe("DECISIONS.md exists but carries no ## D-NNN block — add one (≤6 lines) or shrink the commit.");
  });

  test("accepts a wide commit that carries a DECISIONS.md block", () => {
    const repo = tempRepo(true);
    installGitleaksShim();
    stage(repo, { "package.json": '{ "name": "fixture" }\n', "DECISIONS.md": "# Decisions\n\n## D-001 keep it boring\n" });

    expect(preCommit(repo)).toEqual({ ok: true, lines: [] });
  });
});

describe("commitMsg — the convention and the Receipt-Id trailer", () => {
  test("refuses a message that breaks Conventional Commits", () => {
    const msg = write(tempDir("ai-eng-floor-msg-"), "COMMIT_EDITMSG", "just some words\n");

    const result = commitMsg(msg, "abc12345");

    expect(result.ok).toBe(false);
    expect(result.lines[0]).toBe('the message does not follow the Conventional Commits convention: "just some words"');
    expect(result.lines[1]).toBe("Format: type(scope): description");
    expect(readFileSync(msg, "utf8")).toBe("just some words\n");
  });

  test("accepts a conventional message and appends the Receipt-Id trailer", () => {
    const msg = write(tempDir("ai-eng-floor-msg-"), "COMMIT_EDITMSG", "feat(floor): block staged secrets\n\nThe body.\n");

    const result = commitMsg(msg, "7f3a0000");

    expect(result.ok).toBe(true);
    expect(readFileSync(msg, "utf8")).toBe("feat(floor): block staged secrets\n\nThe body.\n\nReceipt-Id: 7f3a0000\n");
  });

  test("leaves an already-trailered message byte-identical", () => {
    const before = "fix: keep the trailer\n\nReceipt-Id: deadbeef\n";
    const msg = write(tempDir("ai-eng-floor-msg-"), "COMMIT_EDITMSG", before);

    const result = commitMsg(msg, "newvalue");

    expect(result.ok).toBe(true);
    expect(result.lines).toEqual([]);
    expect(readFileSync(msg, "utf8")).toBe(before);
  });

  test("stamps no Override-Reason even under a live override — no false exceptions in history", () => {
    const msg = write(tempDir("ai-eng-floor-msg-"), "COMMIT_EDITMSG", "chore: land it\n");

    const result = commitMsg(msg, "abc12345");

    expect(result.ok).toBe(true);
    expect(readFileSync(msg, "utf8")).toBe("chore: land it\n\nReceipt-Id: abc12345\n");
  });

  test("refuses a message file it cannot read", () => {
    const result = commitMsg(join(tempDir("ai-eng-floor-msg-"), "absent"), "abc12345");

    expect(result.ok).toBe(false);
    expect(result.lines).toEqual(["commit-msg: cannot read the commit message."]);
  });
});

describe("prePush — exactly the commits the push sends, and dated overrides", () => {
  // The refs arrive through AI_ENG_PUSH_REFS: the shim captures pre-push stdin before
  // exec eats it (src/floor/index.ts:167). No gitleaks on PATH here on purpose — if the
  // branch check ever moves behind the scan, this test fails on the HARD FAIL line.
  test("blocks a push targeting the physically present detected base before any scan runs", () => {
    const repo = tempRepo(true);
    const branch = "feature/direct-push";
    run("git", repo, ["checkout", "-b", branch]);
    write(repo, "fixture.txt", "fixture\n");
    run("git", repo, ["add", "fixture.txt"]);
    run("git", repo, ["commit", "-q", "-m", "test: create push fixture"]);
    const sha = run("git", repo, ["rev-parse", "HEAD"]).stdout.trim();
    run("git", repo, ["branch", "main", sha]);
    expect(run("git", repo, ["show-ref", "--verify", "--hash", "refs/heads/main"]).stdout.trim()).toBe(sha);
    expect(resolveContext(repo)).toMatchObject({ base: null, baseSource: "ask" });

    write(repo, ".ai-engineering/config.toml", '[surfaces]\nenabled = ["claude-code"]\n\n[git]\nbase = "main"\n');

    expect(resolveContext(repo)).toMatchObject({ branch, base: "main", baseSource: "config" });

    pathWithoutGitleaks();
    const previousRefs = process.env.AI_ENG_PUSH_REFS;
    process.env.AI_ENG_PUSH_REFS = `refs/heads/${branch} ${sha} refs/heads/main ${"0".repeat(40)}`;
    try {
      expect(prePush(repo)).toEqual({
        ok: false,
        lines: ["direct push to detected base refs/heads/main is not allowed — open a PR instead."],
      });
    } finally {
      if (previousRefs === undefined) delete process.env.AI_ENG_PUSH_REFS;
      else process.env.AI_ENG_PUSH_REFS = previousRefs;
    }
  });

  test("fails closed with a repair step when base configuration cannot be resolved", () => {
    const repo = tempRepo(true);
    const branch = "feature/unreadable-base";
    run("git", repo, ["checkout", "-b", branch]);
    write(repo, ".ai-engineering/config.toml", '[git\nbase = "main"\n');
    pathWithoutGitleaks();
    const previousRefs = process.env.AI_ENG_PUSH_REFS;
    process.env.AI_ENG_PUSH_REFS = `refs/heads/${branch} ${"0".repeat(40)} refs/heads/main ${"0".repeat(40)}`;
    try {
      const result = prePush(repo);

      expect(result.ok).toBe(false);
      expect(result.lines[0]).toContain("pre-push: cannot resolve detected base:");
      expect(result.lines[0]).toContain("fix the TOML so it parses");
    } finally {
      if (previousRefs === undefined) delete process.env.AI_ENG_PUSH_REFS;
      else process.env.AI_ENG_PUSH_REFS = previousRefs;
    }
  });

  test("a base written as a remote or full ref still guards the local branch it names", () => {
    const repo = tempRepo(true);
    const branch = "feature/spelled-base";
    run("git", repo, ["checkout", "-b", branch]);
    run("git", repo, ["remote", "add", "origin", join(repo, "no-such-remote.git")]);
    expect(run("git", repo, ["remote"]).stdout).toBe("origin\n");
    pathWithoutGitleaks();
    const previousRefs = process.env.AI_ENG_PUSH_REFS;
    process.env.AI_ENG_PUSH_REFS = `refs/heads/${branch} ${"0".repeat(40)} refs/heads/main ${"0".repeat(40)}`;
    try {
      for (const spelling of ["main", "origin/main", "refs/heads/main", "refs/remotes/origin/main"]) {
        write(repo, ".ai-engineering/config.toml", `[git]\nbase = "${spelling}"\n`);
        expect(resolveContext(repo), spelling).toMatchObject({ branch, base: "main", baseSource: "config" });
        expect(prePush(repo), spelling).toEqual({
          ok: false,
          lines: ["direct push to detected base refs/heads/main is not allowed — open a PR instead."],
        });
      }
      // A remote-tracking spelling whose remote does not exist names no local branch: deny.
      write(repo, ".ai-engineering/config.toml", '[git]\nbase = "refs/remotes/nosuch/main"\n');
      const unknown = prePush(repo);
      expect(unknown.ok).toBe(false);
      expect(unknown.lines[0]).toStartWith("pre-push: cannot resolve detected base:");
      expect(unknown.lines[0]).toContain("no remote named");
    } finally {
      if (previousRefs === undefined) delete process.env.AI_ENG_PUSH_REFS;
      else process.env.AI_ENG_PUSH_REFS = previousRefs;
    }
  });

  test("any other ref keeps the gate on the scan, not the branch", () => {
    const { repo } = publishedRepo();
    installHistoryShim();
    const tip = commitFile(repo, "app.ts", "export const name = 'clean';\n");
    expect(pushing([`refs/heads/feature ${tip} refs/heads/feature ${ZERO}`], () => prePush(repo))).toEqual({ ok: true, lines: [] });
  });

  test("a push that sends no commit passes without a scan", () => {
    const { repo } = publishedRepo();
    const record = join(dirname(repo), "argv.json");
    installHistoryShim(record);
    expect(pushing([], () => prePush(repo))).toEqual({ ok: true, lines: [] });
    expect(existsSync(record)).toBe(false);
  });

  test("blocks the push when an outgoing commit carries a secret, and the finding stays redacted", () => {
    const { repo } = publishedRepo();
    installHistoryShim();
    const tip = commitFile(repo, "leak.env", `AWS_ACCESS_KEY_ID=${SECRET}\n`);

    const result = pushing([`refs/heads/feature ${tip} refs/heads/feature ${ZERO}`], () => prePush(repo));

    expect(result.ok).toBe(false);
    expect(result.lines[0]).toBe("gitleaks in pre-push: secret in the unpushed history → BLOCKED.");
    expect(result.lines[1]).toContain("RuleID:");
    expect(result.lines[1]).toContain("aws-access-token");
    expect(result.lines.join("\n")).not.toContain(SECRET);
  });

  // The false positive this scope exists for: Figma exports parked on refs/archive/* and
  // in the stash were scanned on every push although no push ever sent them.
  test("a secret only an archive ref and the stash reach does not block a push that never sends them", () => {
    const { repo, base } = publishedRepo();
    const record = join(dirname(repo), "argv.json");
    installHistoryShim(record);
    const archived = commitFile(repo, "figma-export.json", `{"token":"${SECRET}"}\n`);
    run("git", repo, ["update-ref", "refs/archive/figma", archived]);
    run("git", repo, ["reset", "-q", "--hard", base]);
    write(repo, "wip.env", `KEY=${SECRET}\n`);
    run("git", repo, ["add", "wip.env"]);
    run("git", repo, ["stash", "-q"]);
    // The fixture really leaks — just not on this branch.
    expect(run("git", repo, ["log", "-p", "--all"]).stdout).toContain(SECRET);
    const tip = commitFile(repo, "app.ts", "export const name = 'clean';\n");

    expect(pushing([`refs/heads/feature ${tip} refs/heads/feature ${ZERO}`], () => prePush(repo))).toEqual({ ok: true, lines: [] });
    const { args } = JSON.parse(readFileSync(record, "utf8")) as { args: string[] };
    expect(args).toContain(`--log-opts=${tip} --not ${base}`);
  });

  test("a new remote ref is measured from the base the remote already has", () => {
    const { repo } = publishedRepo();
    const record = join(dirname(repo), "argv.json");
    installHistoryShim(record);
    // The base on the remote moves past the branch point: those commits are published.
    run("git", repo, ["checkout", "-q", "-b", "elsewhere"]);
    const published = commitFile(repo, "published.txt", "already on the remote\n");
    run("git", repo, ["update-ref", "refs/remotes/origin/main", published]);
    run("git", repo, ["checkout", "-q", "feature"]);
    const tip = commitFile(repo, "app.ts", "clean\n");

    expect(pushing([`refs/heads/feature ${tip} refs/heads/feature ${ZERO}`], () => prePush(repo)).ok).toBe(true);
    const { args } = JSON.parse(readFileSync(record, "utf8")) as { args: string[] };
    expect(args).toContain(`--log-opts=${tip} --not ${published}`);
  });

  test("a configured base is measured on its remote-tracking ref, never on a guessed main", () => {
    const { repo } = publishedRepo();
    const record = join(dirname(repo), "argv.json");
    installHistoryShim(record);
    const develop = commitFile(repo, "develop.txt", "develop\n");
    run("git", repo, ["update-ref", "refs/remotes/origin/develop", develop]);
    write(repo, ".ai-engineering/config.toml", '[surfaces]\nenabled = ["claude-code"]\n\n[git]\nbase = "develop"\n');
    const tip = commitFile(repo, "app.ts", "clean\n");

    expect(pushing([`refs/heads/feature ${tip} refs/heads/feature ${ZERO}`], () => prePush(repo)).ok).toBe(true);
    const { args } = JSON.parse(readFileSync(record, "utf8")) as { args: string[] };
    expect(args).toContain(`--log-opts=${tip} --not ${develop}`);
  });

  test("an existing remote ref is measured from its old tip: what the remote has is not rescanned", () => {
    const { repo } = publishedRepo();
    installHistoryShim();
    // Already on the remote's copy of the branch (a leak cleaned up elsewhere is CI's scan).
    const old = commitFile(repo, "old.env", `AWS_ACCESS_KEY_ID=${SECRET}\n`);
    const tip = commitFile(repo, "app.ts", "clean\n");

    expect(pushing([`refs/heads/feature ${tip} refs/heads/feature ${old}`], () => prePush(repo))).toEqual({ ok: true, lines: [] });
    // The same secret in the moved range blocks.
    const leak = commitFile(repo, "again.env", `AWS_ACCESS_KEY_ID=${SECRET}\n`);
    expect(pushing([`refs/heads/feature ${leak} refs/heads/feature ${tip}`], () => prePush(repo)).ok).toBe(false);
  });

  test("several refs are one scan of their shared commits, and a deletion sends nothing", () => {
    const { repo, base } = publishedRepo();
    const record = join(dirname(repo), "argv.json");
    installHistoryShim(record);
    const tip = commitFile(repo, "app.ts", "clean\n");

    const result = pushing(
      [
        `refs/heads/feature ${tip} refs/heads/feature ${ZERO}`,
        `refs/heads/feature ${tip} refs/heads/feature-copy ${ZERO}`,
        `(delete) ${ZERO} refs/heads/gone ${base}`,
      ],
      () => prePush(repo),
    );

    expect(result).toEqual({ ok: true, lines: [] });
    const { args } = JSON.parse(readFileSync(record, "utf8")) as { args: string[] };
    expect(args).toContain(`--log-opts=${tip} --not ${base}`);
  });

  test("a push of deletions only runs no scan", () => {
    const { repo, base } = publishedRepo();
    const record = join(dirname(repo), "argv.json");
    installHistoryShim(record);
    expect(pushing([`(delete) ${ZERO} refs/heads/gone ${base}`], () => prePush(repo))).toEqual({ ok: true, lines: [] });
    expect(existsSync(record)).toBe(false);
  });

  test("a new ref whose base this clone never fetched fails closed and names the ref", () => {
    const { repo } = publishedRepo();
    installHistoryShim();
    write(repo, ".ai-engineering/config.toml", '[surfaces]\nenabled = ["claude-code"]\n\n[git]\nbase = "develop"\n');
    const tip = commitFile(repo, "app.ts", "clean\n");

    const result = pushing([`refs/heads/feature ${tip} refs/heads/feature ${ZERO}`], () => prePush(repo));

    expect(result.ok).toBe(false);
    expect(result.lines[0]).toContain("refs/remotes/origin/develop is not in this clone");
    expect(result.lines[0]).toContain("git fetch");
  });

  test("a remote tip this clone does not have fails closed instead of scanning everything", () => {
    const { repo } = publishedRepo();
    installHistoryShim();
    const tip = commitFile(repo, "app.ts", "clean\n");

    const result = pushing([`refs/heads/feature ${tip} refs/heads/feature ${"a".repeat(40)}`], () => prePush(repo));

    expect(result.ok).toBe(false);
    expect(result.lines[0]).toContain("which this clone does not have");
  });

  test("a ref line it cannot read fails closed", () => {
    const { repo } = publishedRepo();
    installHistoryShim();
    const result = pushing(["refs/heads/feature not-a-sha refs/heads/feature also-not"], () => prePush(repo));
    expect(result.ok).toBe(false);
    expect(result.lines[0]).toContain("cannot read the pushed ref");
  });

  test("the project's .gitleaksrc.toml is used when it exists, and a missing one is never named", () => {
    const { repo } = publishedRepo();
    const record = join(dirname(repo), "argv.json");
    installHistoryShim(record);
    const tip = commitFile(repo, "app.ts", "clean\n");
    const line = [`refs/heads/feature ${tip} refs/heads/feature ${ZERO}`];
    const previousConfig = process.env.GITLEAKS_CONFIG;
    // What the pre-push shim exports, whether or not the file is there.
    process.env.GITLEAKS_CONFIG = join(repo, ".gitleaksrc.toml");
    try {
      expect(pushing(line, () => prePush(repo)).ok).toBe(true);
      const missing = JSON.parse(readFileSync(record, "utf8")) as { args: string[]; config: string | null };
      expect(missing.args).not.toContain("-c");
      expect(missing.config).toBeNull();

      write(repo, ".gitleaksrc.toml", "[extend]\nuseDefault = true\n");
      expect(pushing(line, () => prePush(repo)).ok).toBe(true);
      const present = JSON.parse(readFileSync(record, "utf8")) as { args: string[] };
      expect(present.args.slice(-2)).toEqual(["-c", join(repo, ".gitleaksrc.toml")]);
    } finally {
      if (previousConfig === undefined) delete process.env.GITLEAKS_CONFIG;
      else process.env.GITLEAKS_CONFIG = previousConfig;
    }
  });

  test("HARD FAILS when gitleaks is not on PATH", () => {
    const repo = tempRepo(true);
    declareBase(repo);
    pathWithoutGitleaks();

    const result = prePush(repo);

    expect(result.ok).toBe(false);
    expect(result.lines).toEqual([`gitleaks is not installed — HARD FAIL (§12.1). ${gitleaksInstallHint()}`]);
  });

  test("an expired dated override leaves the gate live again (§09.1)", () => {
    const { repo } = publishedRepo();
    installHistoryShim();
    write(repo, ".ai-engineering/overrides.toml", '[[guard.off]]\nname = "floor"\nreason = "pushed under duress"\nuntil = "2020-01-01"\n');
    const tip = commitFile(repo, "leak.env", `AWS_ACCESS_KEY_ID=${SECRET}\n`);

    expect(pushing([`refs/heads/feature ${tip} refs/heads/feature ${ZERO}`], () => prePush(repo)).ok).toBe(false);
  });
});

describe("floor — the dispatcher the shims exec into", () => {
  test("pre-commit: allow runs to exit 0 and leave an allow receipt behind", async () => {
    const repo = tempRepo(true);
    installGitleaksShim();
    stage(repo, { "clean.txt": "clean\n" });
    process.chdir(repo);
    const err = captureStderr();
    let code: number;
    try {
      code = await floor("pre-commit");
    } finally {
      err.restore();
    }

    expect(code).toBe(0);
    const receipts = readdirSync(join(repo, ".ai-engineering", "receipts")).filter((n) => n.includes("git-pre-commit"));
    expect(receipts).toHaveLength(1);
    const receipt = JSON.parse(readFileSync(join(repo, ".ai-engineering", "receipts", receipts[0]!), "utf8")) as {
      event: string;
      outcome: string;
      guards: { ran: string[]; denied_by: string | null };
    };
    expect(receipt.event).toBe("git-pre-commit");
    expect(receipt.outcome).toBe("allow");
    expect(receipt.guards).toEqual({ ran: ["floor"], denied_by: null });
  });

  test("pre-commit: a refusing hook returns non-zero and writes a deny receipt", async () => {
    const repo = tempRepo(true);
    installGitleaksShim();
    stage(repo, { "note.txt": "trailing spaces   \n" });
    process.chdir(repo);
    const err = captureStderr();
    let code: number;
    try {
      code = await floor("pre-commit");
    } finally {
      err.restore();
    }

    expect(code).toBe(1);
    expect(err.text()).toContain("diff --check found whitespace problems:");
    expect(err.text()).toContain("[git floor] pre-commit: BLOCKED — what the hooks would say is what needs fixing.");
    const receipts = readdirSync(join(repo, ".ai-engineering", "receipts")).filter((n) => n.includes("git-pre-commit"));
    const receipt = JSON.parse(readFileSync(join(repo, ".ai-engineering", "receipts", receipts[0]!), "utf8")) as {
      outcome: string;
      guards: { denied_by: string | null };
    };
    expect(receipt.outcome).toBe("deny");
    expect(receipt.guards.denied_by).toBe("floor");
  });

  test("commit-msg: a conventional message exits 0 and the file carries the Receipt-Id", async () => {
    const repo = tempRepo(true);
    process.chdir(repo);
    const msg = write(repo, "COMMIT_EDITMSG", "docs: explain the floor\n");
    const err = captureStderr();
    let code: number;
    try {
      code = await floor("commit-msg", msg);
    } finally {
      err.restore();
    }

    expect(code).toBe(0);
    expect(readFileSync(msg, "utf8")).toMatch(/^docs: explain the floor\n\nReceipt-Id: [0-9a-f]{8}\n$/);
  });

  test("commit-msg: a message that breaks the convention exits 1", async () => {
    const repo = tempRepo(true);
    process.chdir(repo);
    const msg = write(repo, "COMMIT_EDITMSG", "did some stuff\n");
    const err = captureStderr();
    let code: number;
    try {
      code = await floor("commit-msg", msg);
    } finally {
      err.restore();
    }

    expect(code).toBe(1);
    expect(err.text()).toContain("does not follow the Conventional Commits convention");
    expect(readFileSync(msg, "utf8")).toBe("did some stuff\n");
  });

  test("commit-msg: called without a message file it answers with usage and exit 2", async () => {
    const repo = tempRepo(true);
    process.chdir(repo);
    const err = captureStderr();
    let code: number;
    try {
      code = await floor("commit-msg");
    } finally {
      err.restore();
    }

    expect(code).toBe(2);
    expect(err.text()).toBe("usage: ai-eng git commit-msg <msgfile>\n");
  });

  test("commit-msg: a live dated override stamps no Override-Reason trailer (T19)", async () => {
    const repo = tempRepo(true);
    write(repo, ".ai-engineering/overrides.toml", '[[guard.off]]\nname = "floor"\nreason = "sealed build window"\nuntil = "2999-01-01"\n');
    process.chdir(repo);
    const msg = write(repo, "COMMIT_EDITMSG", "chore: land during the freeze\n");
    const err = captureStderr();
    let code: number;
    try {
      code = await floor("commit-msg", msg);
    } finally {
      err.restore();
    }

    expect(code).toBe(0);
    expect(err.text()).toBe("");
    const content = readFileSync(msg, "utf8");
    expect(content).not.toContain("Override-Reason");
    expect(content).toMatch(/Receipt-Id: [0-9a-f]{8}\n$/);
  });

  test("commit-msg: an expired dated override no longer travels (§09.1)", async () => {
    const repo = tempRepo(true);
    write(repo, ".ai-engineering/overrides.toml", '[[guard.off]]\nname = "floor"\nreason = "sealed build window"\nuntil = "2020-01-01"\n');
    process.chdir(repo);
    const msg = write(repo, "COMMIT_EDITMSG", "chore: land after the freeze\n");
    const err = captureStderr();
    let code: number;
    try {
      code = await floor("commit-msg", msg);
    } finally {
      err.restore();
    }

    expect(code).toBe(0);
    expect(err.text()).not.toContain("active override");
    const content = readFileSync(msg, "utf8");
    expect(content).not.toContain("Override-Reason");
    expect(content).toMatch(/Receipt-Id: [0-9a-f]{8}\n$/);
  });

  test("pre-push: exit 0 on a clean surface, exit 1 when it leaks", async () => {
    const { repo } = publishedRepo();
    installHistoryShim();
    const clean = commitFile(repo, "app.ts", "export const name = 'clean';\n");
    process.chdir(repo);
    const err = captureStderr();
    try {
      expect(await pushing([`refs/heads/feature ${clean} refs/heads/feature ${ZERO}`], () => floor("pre-push"))).toBe(0);
      const leak = commitFile(repo, "leak.env", `AWS_ACCESS_KEY_ID=${SECRET}\n`);
      expect(await pushing([`refs/heads/feature ${leak} refs/heads/feature ${clean}`], () => floor("pre-push"))).toBe(1);
    } finally {
      err.restore();
    }
    expect(err.text()).toContain("secret in the unpushed history → BLOCKED.");
  });

  test("an unknown hook is answered with the usage line and exit 2", async () => {
    const repo = tempRepo(true);
    process.chdir(repo);
    const err = captureStderr();
    let code: number;
    try {
      code = await floor("post-rewrite");
    } finally {
      err.restore();
    }

    expect(code).toBe(2);
    expect(err.text()).toBe("usage: ai-eng git pre-commit|commit-msg|pre-push\n");
  });

  test("a repo that never declared itself passes in silence and writes nothing (G5)", async () => {
    const repo = tempRepo(false);
    stage(repo, { "note.txt": "trailing spaces   \n" });
    process.chdir(repo);
    const err = captureStderr();
    let code: number;
    try {
      code = await floor("pre-commit");
    } finally {
      err.restore();
    }

    expect(code).toBe(0);
    expect(err.text()).toBe("");
    expect(existsSync(join(repo, ".ai-engineering"))).toBe(false);
  });
});

describe("floor — F7: a green pre-commit is silent and never reads the receipts folder", () => {
  const SEEDED = 3000;
  // Far older than any [gc].receipts_ttl: if anything collected receipts from the floor,
  // these are the first files it would delete.
  const STALE = new Date("2000-01-01T00:00:00.000Z");

  function receiptsFolder(repo: string): string {
    return join(repo, ".ai-engineering", "receipts");
  }

  /** Thousands of well-formed receipts, named the way writeReceipt names them, so any
   *  summarizer that enumerated the folder would have to open every one. */
  function seedReceipts(repo: string, mtime: Date | null): string[] {
    const dir = receiptsFolder(repo);
    mkdirSync(dir, { recursive: true });
    const names: string[] = [];
    for (let i = 0; i < SEEDED; i++) {
      const ts = new Date(Date.UTC(2026, 9, 1) + i * 1000).toISOString();
      const id = i.toString(16).padStart(8, "0");
      const name = `${ts.replace(/[:.]/g, "-")}-PreToolUse-${id}.json`;
      const path = join(dir, name);
      writeFileSync(
        path,
        JSON.stringify({
          schema: "urn:ai-eng:receipt:2",
          operation_id: id,
          event: "PreToolUse",
          surface: "claude-code",
          tool: "Bash",
          guards: { ran: ["policy"], denied_by: null },
          latency_ms: 3,
          outcome: "allow",
          ts,
        }),
      );
      if (mtime) utimesSync(path, mtime, mtime);
      names.push(name);
    }
    return names;
  }

  function captureStdout(): { text: () => string; restore: () => void } {
    const chunks: string[] = [];
    const spy = spyOn(process.stdout, "write").mockImplementation(((chunk: string) => {
      chunks.push(String(chunk));
      return true;
    }) as never);
    return { text: () => chunks.join(""), restore: () => spy.mockRestore() };
  }

  /** Every directory listing the process asks for whose target is the receipts folder.
   *  The spies call through, so the floor behaves exactly as it would unobserved. */
  function watchReceiptListings(): { stop: () => string[] } {
    const spies = [spyOn(fs, "readdirSync"), spyOn(fs, "opendirSync"), spyOn(fs, "readdir"), spyOn(fs, "opendir")];
    return {
      // Read the calls before restoring: mockRestore() clears them.
      stop: () => {
        const targets = spies
          .flatMap((spy) => spy.mock.calls.map((call) => String((call as unknown[])[0])))
          .filter((target) => target.replaceAll("\\", "/").includes(".ai-engineering/receipts"));
        for (const spy of spies) spy.mockRestore();
        return targets;
      },
    };
  }

  test("with thousands of receipts present, a green pre-commit exits 0 and writes nothing to stdout or stderr", async () => {
    const repo = tempRepo(true);
    installGitleaksShim();
    const seeded = seedReceipts(repo, null);
    // Premise: the folder really holds thousands of receipts before the hook runs.
    expect(readdirSync(receiptsFolder(repo)).filter((n) => seeded.includes(n))).toHaveLength(SEEDED);
    stage(repo, { "clean.txt": "clean\n" });
    process.chdir(repo);

    const err = captureStderr();
    const out = captureStdout();
    let code: number;
    try {
      code = await floor("pre-commit");
    } finally {
      out.restore();
      err.restore();
    }

    expect(code).toBe(0);
    expect(err.text()).toBe("");
    expect(out.text()).toBe("");
  });

  test.skipIf(process.platform === "win32")(
    "never lists the receipts folder: unreadable, it still passes in silence and every stale receipt survives",
    async () => {
      const repo = tempRepo(true);
      installGitleaksShim();
      const seeded = seedReceipts(repo, STALE);
      stage(repo, { "clean.txt": "clean\n" });
      process.chdir(repo);
      const dir = receiptsFolder(repo);
      // Write and traverse, no read: a receipt can still land, a listing cannot.
      chmodSync(dir, 0o300);
      let denied = false;
      try {
        readdirSync(dir);
      } catch (error) {
        denied = (error as NodeJS.ErrnoException).code === "EACCES";
      }

      const err = captureStderr();
      const out = captureStdout();
      const listings = watchReceiptListings();
      let code: number;
      let listed: string[] = [];
      try {
        // Premise: this process really cannot list the folder (not true for root).
        expect(denied).toBe(true);
        code = await floor("pre-commit");
      } finally {
        listed = listings.stop();
        out.restore();
        err.restore();
        chmodSync(dir, 0o755);
      }

      expect(listed).toEqual([]);
      expect(code).toBe(0);
      expect(err.text()).toBe("");
      expect(out.text()).toBe("");
      const after = readdirSync(dir);
      expect(seeded.filter((name) => !after.includes(name))).toEqual([]);
    },
  );

  test("a denied pre-commit keeps today's deny output, byte for byte, and exits 1", async () => {
    const repo = tempRepo(true);
    installGitleaksShim();
    seedReceipts(repo, STALE);
    stage(repo, { "note.txt": "trailing spaces   \n" });
    const verdict = preCommit(repo);
    // Premise: the staged change really is refused, with the hook's own lines.
    expect(verdict.ok).toBe(false);
    expect(verdict.lines.length).toBeGreaterThan(0);
    process.chdir(repo);

    const err = captureStderr();
    let code: number;
    try {
      code = await floor("pre-commit");
    } finally {
      err.restore();
    }

    expect(code).toBe(1);
    expect(err.text()).toBe(
      `${verdict.lines.join("\n")}\n[git floor] pre-commit: BLOCKED — what the hooks would say is what needs fixing.\n`,
    );
  });
});
