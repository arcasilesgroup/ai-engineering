// tests/git-context.spec.ts — the one Git runner (src/git/run.ts) and the one Git
// context resolver (src/git/context.ts), floating-core checkpoint 3 (U8, U9, I9–I19).
// Brainstorm 6.7 fixes the base order: explicit, then `[git] base`, then the default
// branch of the current branch's upstream remote (or origin) read from local refs, else
// ask — and a base equal to the current branch also asks. The forge step lives in ai-pr.
//
// Every case runs real git in a throwaway repo under os.tmpdir(). GIT_CONFIG_GLOBAL and
// GIT_CONFIG_SYSTEM point at an empty file for the whole suite (and are handed back as
// found), so the machine's own config can never decide what a case sees (R8). Each case
// proves its fixture first — branch, HEAD, remote HEAD — before it asserts what the
// resolver derives from it (R5).

import { afterAll, beforeAll, describe, expect, test } from "bun:test";
import { spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, realpathSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { embeddedTemplate } from "../src/embed.ts";
import { loadConfig } from "../src/env.ts";
import { resolveContext } from "../src/git/context.ts";
import { runGit } from "../src/git/run.ts";
import { restoreSandboxEnv, snapshotSandboxEnv } from "./fixtures/sandbox-env.ts";

const sandboxEnv = snapshotSandboxEnv();
const priorSystemConfig = process.env["GIT_CONFIG_SYSTEM"];
const priorTerminalPrompt = process.env["GIT_TERMINAL_PROMPT"];
const sandboxRoot = realpathSync(mkdtempSync(join(tmpdir(), "ai-eng-git-context-")));
const emptyGitConfig = join(sandboxRoot, "empty-gitconfig");
writeFileSync(emptyGitConfig, "");

function restoreVar(name: string, prior: string | undefined): void {
  if (prior === undefined) delete process.env[name];
  else process.env[name] = prior;
}

beforeAll(() => {
  process.env.GIT_CONFIG_GLOBAL = emptyGitConfig;
  process.env["GIT_CONFIG_SYSTEM"] = emptyGitConfig;
  process.env["GIT_TERMINAL_PROMPT"] = "0";
});

afterAll(() => {
  restoreSandboxEnv(sandboxEnv);
  restoreVar("GIT_CONFIG_SYSTEM", priorSystemConfig);
  restoreVar("GIT_TERMINAL_PROMPT", priorTerminalPrompt);
  rmSync(sandboxRoot, { recursive: true, force: true });
});

// ---------------------------------------------------------------------------------------
// Fixture git: the developer's real binary with an isolated config, never the code under test.

function fixtureEnv(): NodeJS.ProcessEnv {
  return {
    ...process.env,
    GIT_CONFIG_GLOBAL: emptyGitConfig,
    GIT_CONFIG_SYSTEM: emptyGitConfig,
    GIT_TERMINAL_PROMPT: "0",
    GIT_AUTHOR_NAME: "Fixture",
    GIT_AUTHOR_EMAIL: "fixture@example.invalid",
    GIT_COMMITTER_NAME: "Fixture",
    GIT_COMMITTER_EMAIL: "fixture@example.invalid",
  };
}

function gitRaw(cwd: string, args: string[]): { status: number; stdout: string; stderr: string } {
  const done = spawnSync("git", args, { cwd, encoding: "utf8", env: fixtureEnv() });
  return { status: done.status ?? 1, stdout: done.stdout ?? "", stderr: done.stderr ?? "" };
}

function git(cwd: string, ...args: string[]): string {
  const done = gitRaw(cwd, args);
  if (done.status !== 0) throw new Error(`fixture git ${args.join(" ")} failed in ${cwd}: ${done.stderr}`);
  return done.stdout.trim();
}

function freshDir(prefix: string): string {
  return realpathSync(mkdtempSync(join(sandboxRoot, prefix)));
}

/** A repo with one commit on `branch` and no remote. */
function initRepo(branch: string): string {
  const repo = freshDir("repo-");
  git(repo, "init", "--quiet", "-b", branch);
  git(repo, "commit", "--quiet", "--allow-empty", "-m", "init");
  return repo;
}

/** A bare remote whose HEAD is `defaultBranch` and which holds exactly `branches`. */
function bareRemote(defaultBranch: string, branches: string[]): string {
  const seed = initRepo(defaultBranch);
  for (const branch of branches) if (branch !== defaultBranch) git(seed, "branch", branch);
  const bare = freshDir("bare-");
  git(bare, "init", "--quiet", "--bare", "-b", defaultBranch);
  git(seed, "push", "--quiet", bare, ...branches.map((branch) => `refs/heads/${branch}:refs/heads/${branch}`));
  return bare;
}

function cloneOf(bare: string): string {
  const work = join(freshDir("clone-"), "work");
  git(sandboxRoot, "clone", "--quiet", bare, work);
  return realpathSync(work);
}

function writeConfig(root: string, toml: string): void {
  mkdirSync(join(root, ".ai-engineering"), { recursive: true });
  writeFileSync(join(root, ".ai-engineering", "config.toml"), toml);
}

// ---------------------------------------------------------------------------------------
// The case table.

type BaseSource = "explicit" | "config" | "remote-head" | "ask";

interface ContextView {
  root: string;
  branch: string | null;
  isDetached: boolean;
  isLinkedWorktree: boolean;
  base: string | null;
  baseSource: BaseSource;
  baseRemote: string | null;
}

/** One fixture fact: `git args` run at `at` prints `out` (trimmed), or fails when `out` is null. */
interface GitPremise {
  at: string;
  args: string[];
  out: string | null;
}

interface Arranged {
  cwd: string;
  explicitBase?: string;
  premises: GitPremise[];
  /** What loadConfig must read as `[git] base` at this root before the resolver runs. */
  configBase: { root: string; value: string | undefined };
  expected: ContextView;
}

interface ContextCase {
  id: string;
  name: string;
  arrange: () => Arranged;
}

const onBranch = (at: string, branch: string): GitPremise => ({ at, args: ["symbolic-ref", "--quiet", "--short", "HEAD"], out: branch });
const remoteHead = (at: string, remote: string, target: string | null): GitPremise => ({
  at,
  args: ["symbolic-ref", "--quiet", `refs/remotes/${remote}/HEAD`],
  out: target === null ? null : `refs/remotes/${remote}/${target}`,
});
const noRemotes = (at: string): GitPremise => ({ at, args: ["remote"], out: "" });
const noRef = (at: string, ref: string): GitPremise => ({ at, args: ["rev-parse", "--verify", "--quiet", ref], out: null });
const toplevel = (at: string, root: string): GitPremise => ({ at, args: ["rev-parse", "--show-toplevel"], out: root });

/** A clone of a remote whose default branch is develop and which has no main anywhere. */
function developClone(): { bare: string; work: string } {
  const bare = bareRemote("develop", ["develop"]);
  return { bare, work: cloneOf(bare) };
}

const cases: ContextCase[] = [
  {
    id: "I9",
    name: "normal checkout, called from a subdirectory: root is the toplevel, the current branch, not a linked worktree",
    arrange: () => {
      const { work } = developClone();
      git(work, "checkout", "--quiet", "-b", "feature");
      const deep = join(work, "src", "deep");
      mkdirSync(deep, { recursive: true });
      return {
        cwd: deep,
        premises: [
          onBranch(work, "feature"),
          toplevel(deep, work),
          { at: work, args: ["rev-parse", "--path-format=absolute", "--git-dir"], out: join(work, ".git") },
          remoteHead(work, "origin", "develop"),
        ],
        configBase: { root: work, value: undefined },
        expected: { root: work, branch: "feature", isDetached: false, isLinkedWorktree: false, base: "develop", baseSource: "remote-head", baseRemote: "origin" },
      };
    },
  },
  {
    id: "I10",
    name: "linked worktree: root is the worktree path, its own branch, isLinkedWorktree true, remote HEAD read through the common dir",
    arrange: () => {
      const { work } = developClone();
      const tree = join(freshDir("wt-"), "feat-x");
      git(work, "worktree", "add", "--quiet", "-b", "feat/x", tree);
      const wt = realpathSync(tree);
      return {
        cwd: wt,
        premises: [
          onBranch(work, "develop"),
          onBranch(wt, "feat/x"),
          toplevel(wt, wt),
          { at: wt, args: ["rev-parse", "--path-format=absolute", "--git-common-dir"], out: join(work, ".git") },
          { at: wt, args: ["rev-parse", "--path-format=absolute", "--git-dir"], out: join(work, ".git", "worktrees", "feat-x") },
          remoteHead(wt, "origin", "develop"),
        ],
        configBase: { root: wt, value: undefined },
        expected: { root: wt, branch: "feat/x", isDetached: false, isLinkedWorktree: true, base: "develop", baseSource: "remote-head", baseRemote: "origin" },
      };
    },
  },
  {
    id: "I11 (S16)",
    name: "detached HEAD is reported as detached with no branch, never as a branch name",
    arrange: () => {
      const { work } = developClone();
      git(work, "checkout", "--quiet", "--detach");
      return {
        cwd: work,
        premises: [
          { at: work, args: ["symbolic-ref", "--quiet", "HEAD"], out: null },
          { at: work, args: ["rev-parse", "--abbrev-ref", "HEAD"], out: "HEAD" },
          remoteHead(work, "origin", "develop"),
        ],
        configBase: { root: work, value: undefined },
        expected: { root: work, branch: null, isDetached: true, isLinkedWorktree: false, base: "develop", baseSource: "remote-head", baseRemote: "origin" },
      };
    },
  },
  {
    id: "I12a (S15)",
    name: "no remote with [git] base: the base comes from config",
    arrange: () => {
      const repo = initRepo("trunk");
      git(repo, "checkout", "--quiet", "-b", "feature");
      writeConfig(repo, '[git]\nbase = "trunk"\n');
      return {
        cwd: repo,
        premises: [onBranch(repo, "feature"), noRemotes(repo)],
        configBase: { root: repo, value: "trunk" },
        expected: { root: repo, branch: "feature", isDetached: false, isLinkedWorktree: false, base: "trunk", baseSource: "config", baseRemote: null },
      };
    },
  },
  {
    id: "I12b (S15)",
    name: "no remote and no [git] base: the result asks, with no base and no guessed main",
    arrange: () => {
      const repo = initRepo("main");
      git(repo, "checkout", "--quiet", "-b", "feature");
      return {
        cwd: repo,
        premises: [onBranch(repo, "feature"), noRemotes(repo), { at: repo, args: ["rev-parse", "--verify", "--quiet", "refs/heads/main"], out: git(repo, "rev-parse", "HEAD") }],
        configBase: { root: repo, value: undefined },
        expected: { root: repo, branch: "feature", isDetached: false, isLinkedWorktree: false, base: null, baseSource: "ask", baseRemote: null },
      };
    },
  },
  {
    id: "I13 (S6)",
    name: "an explicit base (release/2.6) beats [git] base and origin/HEAD",
    arrange: () => {
      const { work } = developClone();
      git(work, "checkout", "--quiet", "-b", "feature");
      writeConfig(work, '[git]\nbase = "trunk"\n');
      return {
        cwd: work,
        explicitBase: "release/2.6",
        premises: [onBranch(work, "feature"), remoteHead(work, "origin", "develop")],
        configBase: { root: work, value: "trunk" },
        expected: { root: work, branch: "feature", isDetached: false, isLinkedWorktree: false, base: "release/2.6", baseSource: "explicit", baseRemote: null },
      };
    },
  },
  {
    id: "I14",
    name: "[git] base beats refs/remotes/origin/HEAD (6.7 step 2 before step 3)",
    arrange: () => {
      const { work } = developClone();
      git(work, "checkout", "--quiet", "-b", "feature");
      writeConfig(work, '[git]\nbase = "trunk"\n');
      return {
        cwd: work,
        premises: [onBranch(work, "feature"), remoteHead(work, "origin", "develop")],
        configBase: { root: work, value: "trunk" },
        expected: { root: work, branch: "feature", isDetached: false, isLinkedWorktree: false, base: "trunk", baseSource: "config", baseRemote: null },
      };
    },
  },
  {
    id: "I15 (S7)",
    name: "clone of a remote whose default is develop and which has no main: base develop from remote-head",
    arrange: () => {
      const { bare, work } = developClone();
      git(work, "checkout", "--quiet", "-b", "feature");
      return {
        cwd: work,
        premises: [
          // A bare repo is addressed with --git-dir: git may refuse to discover one (safe.bareRepository).
          { at: sandboxRoot, args: ["--git-dir", bare, "symbolic-ref", "HEAD"], out: "refs/heads/develop" },
          { at: sandboxRoot, args: ["--git-dir", bare, "for-each-ref", "--format=%(refname)", "refs/heads"], out: "refs/heads/develop" },
          onBranch(work, "feature"),
          remoteHead(work, "origin", "develop"),
          noRef(work, "refs/heads/main"),
          noRef(work, "refs/remotes/origin/main"),
        ],
        configBase: { root: work, value: undefined },
        expected: { root: work, branch: "feature", isDetached: false, isLinkedWorktree: false, base: "develop", baseSource: "remote-head", baseRemote: "origin" },
      };
    },
  },
  {
    id: "I16a (S18)",
    name: "the remote default equals the current branch: the result asks",
    arrange: () => {
      const { work } = developClone();
      return {
        cwd: work,
        premises: [onBranch(work, "develop"), remoteHead(work, "origin", "develop")],
        configBase: { root: work, value: undefined },
        expected: { root: work, branch: "develop", isDetached: false, isLinkedWorktree: false, base: null, baseSource: "ask", baseRemote: null },
      };
    },
  },
  {
    id: "I16b (S18)",
    name: "[git] base equals the current branch: the result asks rather than falling through to origin/HEAD",
    arrange: () => {
      const { work } = developClone();
      git(work, "checkout", "--quiet", "-b", "feature");
      writeConfig(work, '[git]\nbase = "feature"\n');
      return {
        cwd: work,
        premises: [onBranch(work, "feature"), remoteHead(work, "origin", "develop")],
        configBase: { root: work, value: "feature" },
        expected: { root: work, branch: "feature", isDetached: false, isLinkedWorktree: false, base: null, baseSource: "ask", baseRemote: null },
      };
    },
  },
  {
    id: "I17",
    name: "the current branch's upstream remote is preferred over origin: upstream/HEAD=release, origin/HEAD=develop → release",
    arrange: () => {
      const { work } = developClone();
      const upstream = bareRemote("release", ["release"]);
      git(work, "remote", "add", "upstream", upstream);
      git(work, "fetch", "--quiet", "upstream");
      git(work, "remote", "set-head", "upstream", "release");
      git(work, "checkout", "--quiet", "-b", "feature");
      git(work, "push", "--quiet", "-u", "upstream", "feature");
      return {
        cwd: work,
        premises: [
          onBranch(work, "feature"),
          { at: work, args: ["config", "--get", "branch.feature.remote"], out: "upstream" },
          { at: work, args: ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"], out: "upstream/feature" },
          remoteHead(work, "upstream", "release"),
          remoteHead(work, "origin", "develop"),
        ],
        configBase: { root: work, value: undefined },
        expected: { root: work, branch: "feature", isDetached: false, isLinkedWorktree: false, base: "release", baseSource: "remote-head", baseRemote: "upstream" },
      };
    },
  },
  {
    id: "I17b",
    name: "a branch with no upstream falls back to origin even when another remote exists",
    arrange: () => {
      const { work } = developClone();
      const upstream = bareRemote("release", ["release"]);
      git(work, "remote", "add", "upstream", upstream);
      git(work, "fetch", "--quiet", "upstream");
      git(work, "remote", "set-head", "upstream", "release");
      git(work, "checkout", "--quiet", "-b", "feature");
      return {
        cwd: work,
        premises: [
          onBranch(work, "feature"),
          { at: work, args: ["config", "--get", "branch.feature.remote"], out: null },
          remoteHead(work, "upstream", "release"),
          remoteHead(work, "origin", "develop"),
        ],
        configBase: { root: work, value: undefined },
        expected: { root: work, branch: "feature", isDetached: false, isLinkedWorktree: false, base: "develop", baseSource: "remote-head", baseRemote: "origin" },
      };
    },
  },
  {
    id: "I18",
    name: "no network: origin points at an unreachable URL and the base still resolves from local refs",
    arrange: () => {
      const repo = initRepo("develop");
      // 192.0.2.0/24 is TEST-NET-1: any attempt to reach it hangs until a network timeout.
      git(repo, "remote", "add", "origin", "https://192.0.2.1/unreachable.git");
      git(repo, "update-ref", "refs/remotes/origin/develop", "HEAD");
      git(repo, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/develop");
      git(repo, "checkout", "--quiet", "-b", "feature");
      return {
        cwd: repo,
        premises: [
          onBranch(repo, "feature"),
          { at: repo, args: ["remote", "get-url", "origin"], out: "https://192.0.2.1/unreachable.git" },
          remoteHead(repo, "origin", "develop"),
        ],
        configBase: { root: repo, value: undefined },
        expected: { root: repo, branch: "feature", isDetached: false, isLinkedWorktree: false, base: "develop", baseSource: "remote-head", baseRemote: "origin" },
      };
    },
  },
  {
    id: "I20",
    name: "a local upstream (branch.<name>.remote = .) has no remote default: the base comes from origin",
    arrange: () => {
      const { work } = developClone();
      git(work, "checkout", "--quiet", "--track", "-b", "feature", "develop");
      return {
        cwd: work,
        premises: [
          onBranch(work, "feature"),
          { at: work, args: ["config", "--get", "branch.feature.remote"], out: "." },
          remoteHead(work, "origin", "develop"),
        ],
        configBase: { root: work, value: undefined },
        expected: { root: work, branch: "feature", isDetached: false, isLinkedWorktree: false, base: "develop", baseSource: "remote-head", baseRemote: "origin" },
      };
    },
  },
  {
    id: "I21",
    name: "a dangling refs/remotes/origin/HEAD (its target ref is gone) names no base: the result asks",
    arrange: () => {
      const { work } = developClone();
      git(work, "checkout", "--quiet", "-b", "feature");
      git(work, "update-ref", "-d", "refs/remotes/origin/develop");
      return {
        cwd: work,
        premises: [onBranch(work, "feature"), remoteHead(work, "origin", "develop"), noRef(work, "refs/remotes/origin/develop")],
        configBase: { root: work, value: undefined },
        expected: { root: work, branch: "feature", isDetached: false, isLinkedWorktree: false, base: null, baseSource: "ask", baseRemote: null },
      };
    },
  },
];

function view(context: ContextView): ContextView {
  const { root, branch, isDetached, isLinkedWorktree, base, baseSource, baseRemote } = context;
  return { root, branch, isDetached, isLinkedWorktree, base, baseSource, baseRemote };
}

const MAX_RESOLVE_MS = 5_000;

describe("resolveContext — root, branch, worktree and base in the 6.7 order", () => {
  for (const contextCase of cases) {
    test(`${contextCase.id}: ${contextCase.name}`, () => {
      const arranged = contextCase.arrange();

      for (const premise of arranged.premises) {
        const done = gitRaw(premise.at, premise.args);
        const label = `premise git ${premise.args.join(" ")} at ${premise.at}`;
        if (premise.out === null) expect(done.status, label).not.toBe(0);
        else {
          expect(done.status, `${label}: ${done.stderr}`).toBe(0);
          expect(done.stdout.trim(), label).toBe(premise.out);
        }
      }
      // The config file must parse, or a missing base would only mean "unreadable".
      expect(loadConfig(arranged.configBase.root)["git"]?.["base"]).toBe(arranged.configBase.value);

      const started = performance.now();
      const context =
        arranged.explicitBase === undefined ? resolveContext(arranged.cwd) : resolveContext(arranged.cwd, { explicitBase: arranged.explicitBase });
      expect(performance.now() - started).toBeLessThan(MAX_RESOLVE_MS);

      expect(view(context)).toEqual(arranged.expected);
      if (context.baseSource === "ask") expect(context.base).toBeNull();
      expect(context.baseRemote === null).toBe(context.baseSource !== "remote-head");
    });
  }

  test("I19: outside a Git repository resolveContext fails closed with a message naming the path", () => {
    const outside = freshDir("no-repo-");
    // Premise: git itself finds no repository above this directory.
    expect(gitRaw(outside, ["rev-parse", "--show-toplevel"]).status).not.toBe(0);
    expect(() => resolveContext(outside)).toThrow(outside);
  });
});

/** A clone on feature whose origin/HEAD names develop: falling through to the remote would answer develop. */
function featureClone(): string {
  const { work } = developClone();
  git(work, "checkout", "--quiet", "-b", "feature");
  return work;
}

const configFile = (root: string): string => join(root, ".ai-engineering", "config.toml");

describe("resolveContext — every refusal fails closed and names the next step (R8, P8)", () => {
  test("F1: a config.toml that declares [git] base but does not parse throws naming the file, never falls through to remote-head", () => {
    const work = featureClone();
    writeConfig(work, '[git]\nbase = "release"\n\n[broken\n');
    // Premise: the lenient reader answers {} for this file, and origin/HEAD would answer develop.
    expect(loadConfig(work)).toEqual({});
    expect(gitRaw(work, ["symbolic-ref", "--quiet", "refs/remotes/origin/HEAD"]).stdout.trim()).toBe("refs/remotes/origin/develop");

    expect(() => resolveContext(work)).toThrow(`cannot read ${configFile(work)}`);
    expect(() => resolveContext(work)).toThrow("fix the TOML so it parses, or remove the file");
  });

  test("F1: git that is not a [git] table throws instead of reading as no base", () => {
    const work = featureClone();
    writeConfig(work, 'git = "release"\n');
    // Premise: the file parses, and git is a plain string rather than a table.
    const loaded: unknown = loadConfig(work);
    expect(loaded).toEqual({ git: "release" });
    expect(() => resolveContext(work)).toThrow(`git in ${configFile(work)} must be a [git] table`);
  });

  test("a non-string [git] base throws naming the file and the fix", () => {
    const work = featureClone();
    writeConfig(work, "[git]\nbase = 5\n");
    expect(loadConfig(work)["git"]?.["base"]).toBe(5);
    expect(() => resolveContext(work)).toThrow(`[git] base in ${configFile(work)} must be a string; set [git] base to a branch name in ${configFile(work)}`);
  });

  for (const name of ["-x", "HEAD", "a..b"]) {
    test(`an explicit base ${JSON.stringify(name)} that git rejects as a branch name throws`, () => {
      const work = featureClone();
      expect(gitRaw(work, ["check-ref-format", "--branch", name]).status).not.toBe(0);
      expect(() => resolveContext(work, { explicitBase: name })).toThrow(
        `the explicit base is not a valid branch name: ${JSON.stringify(name)}; pass a plain branch name such as release/2.6`,
      );
    });
  }

  test("an explicit or configured @{-1} that git expands to another branch is refused, never followed", () => {
    const work = featureClone();
    git(work, "checkout", "--quiet", "develop");
    git(work, "checkout", "--quiet", "feature");
    // Premise: git accepts @{-1} here and expands it to develop — only the name check stands between it and a base.
    expect(gitRaw(work, ["check-ref-format", "--branch", "@{-1}"])).toEqual({ status: 0, stdout: "develop\n", stderr: "" });

    expect(() => resolveContext(work, { explicitBase: "@{-1}" })).toThrow('the explicit base is not a valid branch name: "@{-1}"');
    writeConfig(work, '[git]\nbase = "@{-1}"\n');
    expect(() => resolveContext(work)).toThrow(`[git] base in ${configFile(work)} is not a valid branch name: "@{-1}"; set [git] base`);
  });

  test("outside a repository the refusal names the next step", () => {
    const outside = freshDir("no-repo-");
    expect(() => resolveContext(outside)).toThrow("run from inside the repository or one of its worktrees");
  });
});

describe("isolated runs ignore the repository-discovery environment a hook inherits (R8)", () => {
  function withEnv(vars: Record<string, string>, run: () => void): void {
    const prior = Object.fromEntries(Object.keys(vars).map((name) => [name, process.env[name]]));
    Object.assign(process.env, vars);
    try {
      run();
    } finally {
      for (const [name, value] of Object.entries(prior)) restoreVar(name, value);
    }
  }

  test("F2: GIT_DIR and GIT_WORK_TREE naming another repo change nothing — root, branch and base all come from cwd", () => {
    const work = featureClone();
    const other = initRepo("other");
    const foreign = { GIT_DIR: join(other, ".git"), GIT_WORK_TREE: other, GIT_INDEX_FILE: join(other, ".git", "index") };
    withEnv(foreign, () => {
      // Premise: an ordinary git in this environment reads the other repo.
      expect(spawnSync("git", ["symbolic-ref", "--short", "HEAD"], { cwd: work, encoding: "utf8", env: process.env }).stdout.trim()).toBe("other");
      expect(runGit(["symbolic-ref", "--short", "HEAD"], { cwd: work }).stdout.trim()).toBe("other");

      expect(runGit(["rev-parse", "--show-toplevel"], { cwd: work, isolated: true })).toEqual({ status: 0, stdout: `${work}\n`, stderr: "" });
      expect(view(resolveContext(work))).toEqual({
        root: work,
        branch: "feature",
        isDetached: false,
        isLinkedWorktree: false,
        base: "develop",
        baseSource: "remote-head",
        baseRemote: "origin",
      });
    });
  });

  test("F2: a relative GIT_DIR=.git from a subdirectory does not break discovery", () => {
    const work = featureClone();
    const deep = join(work, "src", "deep");
    mkdirSync(deep, { recursive: true });
    withEnv({ GIT_DIR: ".git" }, () => {
      expect(spawnSync("git", ["rev-parse", "--show-toplevel"], { cwd: deep, encoding: "utf8", env: process.env }).status).not.toBe(0);
      expect(view(resolveContext(deep))).toMatchObject({ root: work, branch: "feature", base: "develop", baseSource: "remote-head" });
    });
  });
});

describe("runGit — one runner, status and output, never a throw", () => {
  test("U8: a failing command returns a non-zero status and its stderr instead of throwing", () => {
    const repo = initRepo("trunk");
    expect(gitRaw(repo, ["rev-parse", "--verify", "no-such-ref"]).status).not.toBe(0);

    const failed = runGit(["rev-parse", "--verify", "no-such-ref"], { cwd: repo });
    expect(failed.status).not.toBe(0);
    expect(typeof failed.status).toBe("number");
    expect(failed.stderr.trim()).not.toBe("");
    expect(failed.stdout).toBe("");

    const succeeded = runGit(["rev-parse", "--abbrev-ref", "HEAD"], { cwd: repo });
    expect(succeeded).toEqual({ status: 0, stdout: "trunk\n", stderr: "" });
  });

  test("I19: isolated mode sees no value that only the global or system config sets (R8)", () => {
    const repo = initRepo("trunk");
    const globalFile = join(freshDir("global-"), "gitconfig");
    const systemFile = join(freshDir("system-"), "gitconfig");
    writeFileSync(globalFile, "[aiengtest]\n\tfromglobal = leaked-global\n");
    writeFileSync(systemFile, "[aiengtest]\n\tfromsystem = leaked-system\n");
    process.env.GIT_CONFIG_GLOBAL = globalFile;
    process.env["GIT_CONFIG_SYSTEM"] = systemFile;
    try {
      // Premise: an ordinary git in this environment does read both files.
      const plain = (key: string) => spawnSync("git", ["config", "--get", key], { cwd: repo, encoding: "utf8", env: process.env });
      expect(plain("aiengtest.fromglobal").stdout.trim()).toBe("leaked-global");
      expect(plain("aiengtest.fromsystem").stdout.trim()).toBe("leaked-system");

      for (const key of ["aiengtest.fromglobal", "aiengtest.fromsystem"]) {
        const isolated = runGit(["config", "--get", key], { cwd: repo, isolated: true });
        expect(isolated.stdout, key).toBe("");
        expect(isolated.status, key).not.toBe(0);
      }
      // The repo's own config still reaches an isolated run.
      git(repo, "config", "aiengtest.fromrepo", "local-value");
      expect(runGit(["config", "--get", "aiengtest.fromrepo"], { cwd: repo, isolated: true })).toEqual({ status: 0, stdout: "local-value\n", stderr: "" });
    } finally {
      process.env.GIT_CONFIG_GLOBAL = emptyGitConfig;
      process.env["GIT_CONFIG_SYSTEM"] = emptyGitConfig;
    }
  });
});

describe("[git] config keys — read through loadConfig, shipped commented out", () => {
  test("U9: loadConfig reads [git] base and [git] worktrees_dir; absent keys are undefined", () => {
    const withKeys = freshDir("cfg-");
    writeConfig(withKeys, '[git]\nbase = "develop"\nworktrees_dir = "../trees"\n');
    expect(loadConfig(withKeys)["git"]).toEqual({ base: "develop", worktrees_dir: "../trees" });

    const withoutKeys = freshDir("cfg-");
    writeConfig(withoutKeys, "[gc]\nmax_files = 25\n");
    const loaded = loadConfig(withoutKeys);
    // Premise: the file parsed — loadConfig answers {} for a TOML it cannot read.
    expect(loaded["gc"]?.["max_files"]).toBe(25);
    expect(loaded["git"]?.["base"]).toBeUndefined();
    expect(loaded["git"]?.["worktrees_dir"]).toBeUndefined();
  });

  test("U9: the rendered config.toml template defines neither key and documents both commented out", () => {
    const rendered = embeddedTemplate("config.toml.tpl", { surfaces: '"claude-code"' });
    const repo = freshDir("cfg-");
    writeConfig(repo, rendered);
    const loaded = loadConfig(repo);
    expect(loaded["gc"]?.["max_files"]).toBe(25);
    expect(loaded["git"]?.["base"]).toBeUndefined();
    expect(loaded["git"]?.["worktrees_dir"]).toBeUndefined();
    expect(rendered).toMatch(/^#\s*base\s*=/m);
    expect(rendered).toMatch(/^#\s*worktrees_dir\s*=/m);
  });
});
