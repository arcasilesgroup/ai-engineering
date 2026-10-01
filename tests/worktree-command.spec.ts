// tests/worktree-command.spec.ts — CLI contract of `ai-eng worktree new|rm|list`
// (git-worktree-flow test plan, unit layer, checkpoint 2). Every case drives the
// real CLI as a subprocess inside a throwaway git repository in a temp dir: the
// verb owns the filesystem and the git state, so only its observable effects count
// and no implementation module is imported.
// GIT_CONFIG_GLOBAL/GIT_CONFIG_SYSTEM point at empty files so the machine's real
// ~/.gitconfig (hooks, signing, identity) can never decide what a child git does.
// One test swaps a logging `git` shim onto PATH to read back the exact argv the
// verb emits; the shim delegates to the real binary, so behaviour is unchanged.

import { afterAll, afterEach, beforeEach, describe, expect, test } from "bun:test";
import { spawnSync } from "node:child_process";
import {
  chmodSync,
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  readdirSync,
  realpathSync,
  rmSync,
  symlinkSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { basename, dirname, join } from "node:path";

const CLI = join(import.meta.dir, "..", "src", "cli.ts");
const REAL_GIT = Bun.which("git") ?? "git";
const sandboxRoot = mkdtempSync(join(tmpdir(), "ai-eng-worktree-"));
const emptyGitConfig = join(sandboxRoot, "empty-gitconfig");
writeFileSync(emptyGitConfig, "");

// A `git` that records one line per argv element (so argument boundaries survive)
// and then execs the real binary. Only tests that set GIT_INVOCATION_LOG produce a
// log; every other child sees the unmodified PATH.
const shimDir = join(sandboxRoot, "bin");
const shim = join(shimDir, "git");
mkdirSync(shimDir, { recursive: true });
writeFileSync(
  shim,
  [
    "#!/bin/sh",
    'if [ -n "$GIT_INVOCATION_LOG" ]; then',
    "  {",
    "    printf 'ARG\\t%s\\n' \"$@\"",
    "    printf 'END\\n'",
    '  } >> "$GIT_INVOCATION_LOG"',
    "fi",
    `exec "${REAL_GIT}" "$@"`,
    "",
  ].join("\n"),
);
chmodSync(shim, 0o755);

const childEnv: NodeJS.ProcessEnv = {
  ...process.env,
  GIT_CONFIG_GLOBAL: emptyGitConfig,
  GIT_CONFIG_SYSTEM: "/dev/null",
  GIT_TERMINAL_PROMPT: "0",
};

afterAll(() => {
  rmSync(sandboxRoot, { recursive: true, force: true });
});

interface Run {
  status: number;
  stdout: string;
  stderr: string;
}

/** Fixture git: never the shim, always the developer's real binary. */
function gitOut(args: string[], cwd: string): Run {
  const done = spawnSync("git", args, { cwd, encoding: "utf8", env: childEnv });
  return { status: done.status ?? 1, stdout: done.stdout ?? "", stderr: done.stderr ?? "" };
}

function git(args: string[], cwd: string): string {
  const done = gitOut(args, cwd);
  if (done.status !== 0) throw new Error(`git ${args.join(" ")} failed in ${cwd}: ${done.stderr}`);
  return done.stdout;
}

/** The verb under test, spawned exactly as a script would run it. */
function runCli(args: string[], cwd: string, env: NodeJS.ProcessEnv = {}): Run {
  const done = spawnSync(process.execPath, [CLI, ...args], { cwd, encoding: "utf8", env: { ...childEnv, ...env } });
  return { status: done.status ?? 1, stdout: done.stdout ?? "", stderr: done.stderr ?? "" };
}

function shimEnv(log: string): NodeJS.ProcessEnv {
  return { PATH: `${shimDir}:${process.env.PATH ?? ""}`, GIT_INVOCATION_LOG: log };
}

function loggedArgs(log: string): string[] {
  if (!existsSync(log)) return [];
  return readFileSync(log, "utf8")
    .split("\n")
    .filter((line) => line.startsWith("ARG\t"))
    .map((line) => line.slice("ARG\t".length));
}

interface Entry {
  path: string;
  branch: string | undefined;
}

function worktreeEntries(repo: string): Entry[] {
  const blocks = git(["worktree", "list", "--porcelain"], repo).split("\n\n");
  return blocks
    .map((block) => {
      const lines = block.split("\n");
      const pathLine = lines.find((line) => line.startsWith("worktree "));
      if (!pathLine) return undefined;
      const branchLine = lines.find((line) => line.startsWith("branch "));
      return { path: pathLine.slice("worktree ".length), branch: branchLine?.slice("branch ".length) };
    })
    .filter((entry): entry is Entry => entry !== undefined);
}

function branchNames(repo: string): string[] {
  return git(["branch", "--format=%(refname:short)"], repo)
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

/** Every git surface a read-only verb could plausibly disturb. */
function repoState(repo: string): string {
  return [
    git(["status", "--porcelain"], repo),
    git(["worktree", "list", "--porcelain"], repo),
    git(["branch", "--format=%(refname:short)"], repo),
  ].join("\n===\n");
}

/** The canonical default root: a sibling of the repo's real path. */
const defaultRoot = (repo: string): string => `${realpathSync(repo)}.worktrees`;

let cleanups: string[] = [];

beforeEach(() => {
  cleanups = [];
});

afterEach(() => {
  for (const path of cleanups) rmSync(path, { recursive: true, force: true });
  cleanups = [];
});

function initRepo(dir: string): string {
  mkdirSync(dir, { recursive: true });
  git(["init", "-q", "-b", "main"], dir);
  git(["config", "user.name", "Ada Lovelace"], dir);
  git(["config", "user.email", "ada@example.com"], dir);
  git(["config", "commit.gpgsign", "false"], dir);
  writeFileSync(join(dir, "README.md"), "# fixture\n");
  git(["add", "-A"], dir);
  git(["commit", "-q", "-m", "fixture base"], dir);
  return dir;
}

function tempRepo(): string {
  const root = mkdtempSync(join(tmpdir(), "ai-eng-worktree-repo-"));
  cleanups.push(root);
  return initRepo(root);
}

/** APFS/HFS+ fold case, ext4 does not: probe by writing the same name in two cases. */
function isCaseInsensitiveFs(): boolean {
  const probe = mkdtempSync(join(tmpdir(), "ai-eng-case-probe-"));
  try {
    writeFileSync(join(probe, "probe"), "a");
    writeFileSync(join(probe, "PROBE"), "b");
    return readdirSync(probe).length === 1; // both names collapsed onto one file
  } finally {
    rmSync(probe, { recursive: true, force: true });
  }
}

const IS_CASE_INSENSITIVE_FS = isCaseInsensitiveFs();

describe("ai-eng worktree verb (checkpoint 2)", () => {
  test("canonical: new <slug> lands at the realpathed sibling root, even from a symlinked cwd", () => {
    const base = mkdtempSync(join(tmpdir(), "ai-eng-worktree-base-"));
    cleanups.push(base);
    initRepo(join(base, "repo"));
    const alias = join(base, "alias");
    symlinkSync(base, alias);
    // The repository is reached through a symlink: a naive implementation would
    // carry the alias in the root; the contract is the canonical sibling.
    const viaAlias = join(alias, "repo");
    const canonicalRepo = realpathSync(viaAlias);
    const root = `${canonicalRepo}.worktrees`;
    cleanups.push(root);

    const run = runCli(["worktree", "new", "alpha"], viaAlias);
    expect(run.status).toBe(0);

    const created = join(root, "alpha");
    expect(existsSync(created)).toBe(true);
    expect(dirname(created)).toBe(root);
    expect(dirname(root)).toBe(dirname(canonicalRepo));
    expect(basename(root)).toBe(`${basename(canonicalRepo)}.worktrees`);
    // The registered path is its own realpath: no symlinked alias slipped through.
    expect(realpathSync(created)).toBe(created);
    expect(worktreeEntries(viaAlias).map((entry) => entry.path)).toContain(created);
  });

  test("upstream: the branch is cut from local main with remote '.' and merge refs/heads/main", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);
    expect(runCli(["worktree", "new", "alpha"], repo).status).toBe(0);

    const remote = gitOut(["config", "--get", "branch.feat/alpha.remote"], repo);
    const merge = gitOut(["config", "--get", "branch.feat/alpha.merge"], repo);
    expect(remote.status).toBe(0);
    expect(remote.stdout.trim()).toBe(".");
    expect(merge.status).toBe(0);
    expect(merge.stdout.trim()).toBe("refs/heads/main");

    expect(branchNames(repo)).toContain("feat/alpha");
    // Cut from the local main, not from a remote-tracking ref: same commit.
    expect(git(["rev-parse", "feat/alpha"], repo).trim()).toBe(git(["rev-parse", "main"], repo).trim());
  });

  test("design slot: an uncommitted slot file makes new refuse and create nothing", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);
    const slot = join(repo, ".ai-engineering", "brainstorm.html");
    mkdirSync(dirname(slot), { recursive: true });
    writeFileSync(slot, "<html>committed</html>\n");
    git(["add", "-A"], repo);
    git(["commit", "-q", "-m", "add design slot"], repo);
    writeFileSync(slot, "<html>uncommitted edit</html>\n");

    const run = runCli(["worktree", "new", "alpha"], repo);
    expect(run.status).not.toBe(0);
    expect(run.stderr).toContain("brainstorm.html");
    expect(existsSync(join(root, "alpha"))).toBe(false);
    expect(branchNames(repo)).not.toContain("feat/alpha");
    expect(worktreeEntries(repo)).toHaveLength(1);
  });

  test("fallback: with no [git] worktrees_dir the root is <repo>.worktrees", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);
    expect(existsSync(join(repo, ".ai-engineering", "config.toml"))).toBe(false);

    const run = runCli(["worktree", "new", "beta"], repo);
    expect(run.status).toBe(0);
    expect(existsSync(join(root, "beta"))).toBe(true);
    expect(existsSync(join(repo, "beta"))).toBe(false);
  });

  test("worktrees_dir: [git] worktrees_dir in config.toml moves the root", () => {
    const repo = tempRepo();
    const custom = mkdtempSync(join(tmpdir(), "ai-eng-worktrees-dir-"));
    cleanups.push(custom);
    mkdirSync(join(repo, ".ai-engineering"), { recursive: true });
    writeFileSync(join(repo, ".ai-engineering", "config.toml"), `[git]\nworktrees_dir = ${JSON.stringify(custom)}\n`);

    const run = runCli(["worktree", "new", "gamma"], repo);
    expect(run.status).toBe(0);
    expect(existsSync(join(custom, "gamma"))).toBe(true);
    expect(existsSync(join(defaultRoot(repo), "gamma"))).toBe(false);
  });

  test("overlap: a second worktree declaring a file an open one declared warns without blocking", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);

    const first = runCli(["worktree", "new", "alpha", "docs/shared.md"], repo);
    expect(first.status).toBe(0);
    const second = runCli(["worktree", "new", "beta", "docs/shared.md"], repo);
    expect(second.status).toBe(0);
    expect(second.stderr).toContain("shared.md");
    expect(existsSync(join(root, "beta"))).toBe(true);
    expect(branchNames(repo)).toContain("feat/beta");
  });

  test("list: reports every open worktree with its slug and path and mutates nothing", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);
    expect(runCli(["worktree", "new", "alpha"], repo).status).toBe(0);
    expect(runCli(["worktree", "new", "beta"], repo).status).toBe(0);

    const before = repoState(repo);
    const run = runCli(["worktree", "list"], repo);
    expect(run.status).toBe(0);

    const lines = run.stdout.split("\n");
    const alphaLine = lines.find((line) => line.includes("alpha"));
    const betaLine = lines.find((line) => line.includes("beta"));
    expect(alphaLine).toBeDefined();
    expect(alphaLine).toContain(join(root, "alpha"));
    expect(betaLine).toBeDefined();
    expect(betaLine).toContain(join(root, "beta"));

    expect(repoState(repo)).toBe(before);
  });

  test("remove: rm <slug> deletes the worktree and its branch", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);
    expect(runCli(["worktree", "new", "alpha"], repo).status).toBe(0);
    const created = realpathSync(join(root, "alpha"));

    const run = runCli(["worktree", "rm", "alpha"], repo);
    expect(run.status).toBe(0);
    expect(existsSync(join(root, "alpha"))).toBe(false);
    expect(worktreeEntries(repo).map((entry) => entry.path)).not.toContain(created);
    expect(worktreeEntries(repo)).toHaveLength(1);
    expect(branchNames(repo)).not.toContain("feat/alpha");
  });

  test("no push: no git command the verb emits ever pushes", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);
    const log = join(repo, "invocations.log");
    const env = shimEnv(log);
    const runs = [
      runCli(["worktree", "new", "alpha"], repo, env),
      runCli(["worktree", "list"], repo, env),
      runCli(["worktree", "rm", "alpha"], repo, env),
    ];
    for (const run of runs) expect(run.status).toBe(0);

    const args = loggedArgs(log);
    // The shim saw the verb's own commands: guards against a green pass over an empty log.
    expect(args.length).toBeGreaterThan(0);
    expect(args.some((arg) => arg.includes("push"))).toBe(false);
    for (const run of runs) {
      expect(run.stdout).not.toContain("git push");
      expect(run.stderr).not.toContain("git push");
    }
  });

  test("invalid slug: a space or a slash is refused before anything is created", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);

    for (const slug of ["bad slug", "bad/slug"]) {
      const run = runCli(["worktree", "new", slug], repo);
      expect(run.status).not.toBe(0);
      expect(run.stderr.trim().length).toBeGreaterThan(0);
      expect(run.stderr).toMatch(/slug/i);
      expect(existsSync(join(root, slug))).toBe(false);
    }
    // Nothing was created: main is still the only branch and the only worktree.
    expect(branchNames(repo)).toEqual(["main"]);
    expect(worktreeEntries(repo)).toHaveLength(1);
  });

  test("valid slug: a kebab-case slug and a mixed slug both succeed", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);
    for (const slug of ["git-worktree-flow", "mix.ed-1"]) {
      const run = runCli(["worktree", "new", slug], repo);
      expect(run.status).toBe(0);
      expect(existsSync(join(root, slug))).toBe(true);
      expect(branchNames(repo)).toContain(`feat/${slug}`);
    }
  });

  test("no unquoted: every value reaches git as its own argv element", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);
    const log = join(repo, "invocations.log");
    const run = runCli(["worktree", "new", "alpha"], repo, shimEnv(log));
    expect(run.status).toBe(0);

    const args = loggedArgs(log);
    expect(args.length).toBeGreaterThan(0);
    for (const arg of args) {
      // A value that had travelled through a shell string would arrive split or
      // carry one of these; separate argv elements cannot.
      expect(arg).not.toMatch(/[;|&`$()<>*?[\]{}]/);
      expect(arg).not.toContain("\n");
    }
  });

  test("stale: a worktree whose directory vanished is listed and pruned by rm", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);
    expect(runCli(["worktree", "new", "alpha"], repo).status).toBe(0);

    rmSync(join(root, "alpha"), { recursive: true, force: true });

    const listed = runCli(["worktree", "list"], repo);
    expect(listed.status).toBe(0);
    expect(listed.stdout).toContain("alpha");

    const removed = runCli(["worktree", "rm", "alpha"], repo);
    expect(removed.status).toBe(0);
    expect(worktreeEntries(repo)).toHaveLength(1);
    expect(branchNames(repo)).not.toContain("feat/alpha");
  });

  test("untracked design slot: a never-committed .ai-engineering slot still makes new refuse", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);
    // `.ai-engineering/` has never been committed, so git status collapses the whole
    // directory to `?? .ai-engineering/` unless the guard asks for untracked files.
    const slot = join(repo, ".ai-engineering", "brainstorm.html");
    mkdirSync(dirname(slot), { recursive: true });
    writeFileSync(slot, "<html>untracked slot</html>\n");

    const run = runCli(["worktree", "new", "alpha"], repo);
    expect(run.status).not.toBe(0);
    expect(run.stderr).toContain("brainstorm.html");
    expect(existsSync(join(root, "alpha"))).toBe(false);
    expect(branchNames(repo)).not.toContain("feat/alpha");
    expect(worktreeEntries(repo)).toHaveLength(1);
  });

  test("recap does not block: a dirty recap.html leaves new succeeding", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);
    const recap = join(repo, ".ai-engineering", "recap.html");
    mkdirSync(dirname(recap), { recursive: true });
    writeFileSync(recap, "<html>committed recap</html>\n");
    git(["add", "-A"], repo);
    git(["commit", "-q", "-m", "add recap"], repo);
    // Dirty, but recap is generated at the app review and reaches the primary tree
    // with the merge, so it must never block cutting a worktree.
    writeFileSync(recap, "<html>dirty recap</html>\n");

    const run = runCli(["worktree", "new", "alpha"], repo);
    expect(run.status).toBe(0);
    expect(existsSync(join(root, "alpha"))).toBe(true);
  });

  test("list omits the primary checkout: only open sessions are printed", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);
    expect(runCli(["worktree", "new", "alpha"], repo).status).toBe(0);
    expect(runCli(["worktree", "new", "beta"], repo).status).toBe(0);

    const run = runCli(["worktree", "list"], repo);
    expect(run.status).toBe(0);
    const primary = realpathSync(repo);
    // The primary checkout must not carry a line, but its worktrees (paths that extend
    // it with `.worktrees/`) are exactly what must.
    const mentionsPrimary = run.stdout
      .split("\n")
      .some((line) => line.includes(primary) && !line.includes(`${primary}.worktrees`));
    expect(mentionsPrimary).toBe(false);
    expect(run.stdout).toContain("alpha");
    expect(run.stdout).toContain("beta");
  });

  test("slot as a directory: brainstorm.html turned into a directory still makes new refuse", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);
    // A directory named like the slot never committed: porcelain -uall reports the
    // file inside it, so a whole-string comparison against the slot name misses it.
    const slotDir = join(repo, ".ai-engineering", "brainstorm.html");
    mkdirSync(slotDir, { recursive: true });
    writeFileSync(join(slotDir, "inner.txt"), "not the slot\n");

    const run = runCli(["worktree", "new", "alpha"], repo);
    expect(run.status).not.toBe(0);
    expect(run.stderr).toContain("brainstorm.html");
    expect(existsSync(join(root, "alpha"))).toBe(false);
    expect(branchNames(repo)).not.toContain("feat/alpha");
    expect(worktreeEntries(repo)).toHaveLength(1);
  });

  test("renamed slot: git mv of a committed design slot still makes new refuse", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);
    const slot = join(repo, ".ai-engineering", "brainstorm.html");
    mkdirSync(dirname(slot), { recursive: true });
    writeFileSync(slot, "<html>slot</html>\n");
    git(["add", "-A"], repo);
    git(["commit", "-q", "-m", "add slot"], repo);
    // A rename line `R  brainstorm.html -> brainstorm2.html` hides that the slot left.
    git(["mv", ".ai-engineering/brainstorm.html", ".ai-engineering/brainstorm2.html"], repo);

    const run = runCli(["worktree", "new", "alpha"], repo);
    expect(run.status).not.toBe(0);
    expect(run.stderr).toContain("brainstorm");
    expect(existsSync(join(root, "alpha"))).toBe(false);
    expect(branchNames(repo)).not.toContain("feat/alpha");
    expect(worktreeEntries(repo)).toHaveLength(1);
  });

  test("deleted slot: git rm of a committed design slot still makes new refuse", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);
    const slot = join(repo, ".ai-engineering", "plan.html");
    mkdirSync(dirname(slot), { recursive: true });
    writeFileSync(slot, "<html>plan</html>\n");
    git(["add", "-A"], repo);
    git(["commit", "-q", "-m", "add plan"], repo);
    git(["rm", "-q", ".ai-engineering/plan.html"], repo);

    const run = runCli(["worktree", "new", "alpha"], repo);
    expect(run.status).not.toBe(0);
    expect(run.stderr).toContain("plan.html");
    expect(existsSync(join(root, "alpha"))).toBe(false);
    expect(branchNames(repo)).not.toContain("feat/alpha");
  });

  // On a case-insensitive filesystem `brainstorm.HTML` is the same file as
  // `brainstorm.html`, but porcelain reports it in the written case.
  test.skipIf(!IS_CASE_INSENSITIVE_FS)(
    "case-alias slot: brainstorm.HTML dirty still makes new refuse (case-insensitive fs only)",
    () => {
      const repo = tempRepo();
      const root = defaultRoot(repo);
      cleanups.push(root);
      const slot = join(repo, ".ai-engineering", "brainstorm.HTML");
      mkdirSync(dirname(slot), { recursive: true });
      writeFileSync(slot, "dirt\n");

      const run = runCli(["worktree", "new", "alpha"], repo);
      expect(run.status).not.toBe(0);
      expect(run.stderr).toMatch(/brainstorm\.html/i);
      expect(existsSync(join(root, "alpha"))).toBe(false);
      expect(branchNames(repo)).not.toContain("feat/alpha");
      expect(worktreeEntries(repo)).toHaveLength(1);
    },
  );

  test("non-ascii inside a slot directory: escape-decorated porcelain still makes new refuse", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);
    // git quotes the path as `"?? .ai-engineering/brainstorm.html/caf\303\251.txt"`,
    // so a parser that keeps the C escapes never matches the slot prefix.
    const slotDir = join(repo, ".ai-engineering", "brainstorm.html");
    mkdirSync(slotDir, { recursive: true });
    writeFileSync(join(slotDir, "café.txt"), "dirt\n");

    const run = runCli(["worktree", "new", "alpha"], repo);
    expect(run.status).not.toBe(0);
    expect(run.stderr).toMatch(/brainstorm\.html/);
    expect(existsSync(join(root, "alpha"))).toBe(false);
    expect(branchNames(repo)).not.toContain("feat/alpha");
    expect(worktreeEntries(repo)).toHaveLength(1);
  });

  test("from inside a worktree: list lists sessions and new cuts from the primary main", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);
    expect(runCli(["worktree", "new", "alpha"], repo).status).toBe(0);
    const inside = join(root, "alpha");
    const primary = realpathSync(repo);

    const listed = runCli(["worktree", "list"], inside);
    expect(listed.status).toBe(0);
    expect(listed.stdout).toContain("alpha");
    const mentionsPrimary = listed.stdout
      .split("\n")
      .some((line) => line.includes(primary) && !line.includes(`${primary}.worktrees`));
    expect(mentionsPrimary).toBe(false);

    // The intended use: a new session opened from inside an open worktree still
    // belongs to the primary repository, not to a nested `<worktree>.worktrees`.
    const created = runCli(["worktree", "new", "otra"], inside);
    expect(created.status).toBe(0);
    expect(existsSync(join(root, "otra"))).toBe(true);
    expect(existsSync(join(root, "alpha.worktrees", "otra"))).toBe(false);
    expect(git(["rev-parse", "feat/otra"], repo).trim()).toBe(git(["rev-parse", "main"], repo).trim());
  });

  test("newline slug: a control character is refused and leaves nothing behind", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);

    const run = runCli(["worktree", "new", "alpha\n"], repo);
    expect(run.status).not.toBe(0);
    expect(run.stderr).toMatch(/slug/i);
    expect(existsSync(join(root, "alpha\n"))).toBe(false);
    expect(branchNames(repo)).toEqual(["main"]);
    expect(worktreeEntries(repo)).toHaveLength(1);
  });

  test("declaration file with the worktrees: invalid null is rejected, rm drops the slug, primary stays clean", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);
    // The declaration file lives beside the worktrees, never in the primary tree.
    mkdirSync(root, { recursive: true });
    const declarations = join(root, ".ai-eng-worktrees.json");
    writeFileSync(declarations, "null");
    const clean = git(["status", "--porcelain"], repo);

    // A malformed declaration file must be a refusal, not an uncaught throw.
    const bad = runCli(["worktree", "new", "alpha", "docs/shared.md"], repo);
    expect(bad.status).not.toBe(0);
    expect(bad.stderr.trim().length).toBeGreaterThan(0);
    expect(existsSync(join(root, "alpha"))).toBe(false);
    expect(git(["status", "--porcelain"], repo)).toBe(clean);

    rmSync(declarations, { force: true });
    expect(runCli(["worktree", "new", "alpha", "docs/shared.md"], repo).status).toBe(0);
    expect(existsSync(declarations)).toBe(true);
    expect(readFileSync(declarations, "utf8")).toContain("alpha");
    // A session never touches the primary tree.
    expect(git(["status", "--porcelain"], repo)).toBe(clean);

    expect(runCli(["worktree", "rm", "alpha"], repo).status).toBe(0);
    const after = existsSync(declarations) ? readFileSync(declarations, "utf8") : "";
    expect(after).not.toContain("alpha");
    expect(git(["status", "--porcelain"], repo)).toBe(clean);
  });

  test("relative worktrees_dir: the same root from the primary tree and from inside a worktree", () => {
    const repo = tempRepo();
    const root = join(realpathSync(repo), ".wt");
    cleanups.push(root);
    mkdirSync(join(repo, ".ai-engineering"), { recursive: true });
    writeFileSync(join(repo, ".ai-engineering", "config.toml"), `[git]\nworktrees_dir = ".wt"\n`);

    expect(runCli(["worktree", "new", "alpha"], repo).status).toBe(0);
    const created = join(root, "alpha");
    expect(existsSync(created)).toBe(true);
    // A relative root must hang off the primary tree, not off the current directory.
    expect(existsSync(join(created, ".wt", "alpha"))).toBe(false);

    const fromPrimary = runCli(["worktree", "list"], repo);
    const fromWorktree = runCli(["worktree", "list"], created);
    expect(fromPrimary.status).toBe(0);
    expect(fromWorktree.status).toBe(0);
    const alphaLine = (out: string): string | undefined => out.split("\n").find((line) => line.includes("alpha"));
    expect(alphaLine(fromPrimary.stdout)).toContain(realpathSync(created));
    expect(alphaLine(fromWorktree.stdout)).toBe(alphaLine(fromPrimary.stdout));
  });
});
