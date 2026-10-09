// tests/worktree-command.spec.ts — CLI contract of `ai-eng worktree new|rm|list|rebase|merge`
// (git-worktree-flow test plan, unit layer, checkpoint 2). Every case drives the
// real CLI as a subprocess inside a throwaway git repository in a temp dir: the
// verb owns the filesystem and the git state, so only its observable effects count
// and no implementation module is imported.
// GIT_CONFIG_GLOBAL/GIT_CONFIG_SYSTEM point at empty files so the machine's real
// ~/.gitconfig (hooks, signing, identity) can never decide what a child git does.
// One test swaps a logging `git` shim onto PATH to read back the exact argv the
// verb emits; the shim delegates to the real binary, so behaviour is unchanged.

import { afterAll, afterEach, beforeEach, describe, expect, test } from "bun:test";
import { spawn, spawnSync } from "node:child_process";
import {
  chmodSync,
  existsSync,
  lstatSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  readdirSync,
  readlinkSync,
  realpathSync,
  rmSync,
  symlinkSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { basename, dirname, join, relative, resolve } from "node:path";

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
    'if [ "$GIT_TEST_FAIL_BRANCH_DELETE" = "1" ] && [ "$1" = "branch" ] && [ "$2" = "-d" ]; then',
    '  printf "injected branch-delete failure\\n" >&2',
    "  exit 1",
    "fi",
    'if [ "$GIT_TEST_FAIL_WORKTREE_REMOVE" = "1" ] && [ "$1" = "worktree" ] && [ "$2" = "remove" ]; then',
    '  printf "injected worktree-remove failure\\n" >&2',
    "  exit 1",
    "fi",
    'if [ "$GIT_TEST_FAIL_POST_REMOVE_LIST" = "1" ] && [ -f "$GIT_TEST_POST_REMOVE_MARKER" ] && [ "$1" = "worktree" ] && [ "$2" = "list" ]; then',
    '  printf "injected post-removal inventory failure\\n" >&2',
    "  exit 1",
    "fi",
    'if [ "$GIT_TEST_UNREADABLE_IGNORED_SCAN" = "1" ] && [ "$1" = "status" ]; then',
    "  for argument do",
    '    if [ "$argument" = "--ignored" ]; then',
    `      "${REAL_GIT}" "$@"`,
    "      status=$?",
    '      printf "injected unreadable ignored-path warning\\n" >&2',
    "      exit \"$status\"",
    "    fi",
    "  done",
    "fi",
    'if [ "$GIT_TEST_FAIL_POST_REMOVE_LIST" = "1" ] && [ "$1" = "branch" ] && [ "$2" = "-d" ]; then',
    `  "${REAL_GIT}" "$@"`,
    "  status=$?",
    '  if [ "$status" -eq 0 ]; then : > "$GIT_TEST_POST_REMOVE_MARKER"; fi',
    "  exit \"$status\"",
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

function runCliAsync(args: string[], cwd: string, env: NodeJS.ProcessEnv = {}): Promise<Run> {
  return new Promise((resolveRun, rejectRun) => {
    const child = spawn(process.execPath, [CLI, ...args], {
      cwd,
      env: { ...childEnv, ...env },
      stdio: ["ignore", "pipe", "pipe"],
    });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk: Buffer) => (stdout += chunk.toString()));
    child.stderr.on("data", (chunk: Buffer) => (stderr += chunk.toString()));
    child.on("error", rejectRun);
    child.on("close", (status) => resolveRun({ status: status ?? 1, stdout, stderr }));
  });
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

function loggedInvocations(log: string): string[][] {
  if (!existsSync(log)) return [];
  const invocations: string[][] = [];
  let current: string[] | undefined;
  for (const line of readFileSync(log, "utf8").split("\n")) {
    if (line.startsWith("ARG\t")) current?.push(line.slice("ARG\t".length));
    if (line === "END" && current) {
      invocations.push(current);
      current = undefined;
    }
    if (line === "END") continue;
    if (line.startsWith("ARG\t") && !current) current = [line.slice("ARG\t".length)];
  }
  return invocations;
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

function treeFiles(root: string): unknown {
  if (!existsSync(root)) return "missing";
  const entries: unknown[] = [];
  const visit = (directory: string): void => {
    for (const name of readdirSync(directory).sort()) {
      const path = join(directory, name);
      const pathFromRoot = relative(root, path);
      const info = lstatSync(path);
      if (info.isSymbolicLink()) {
        entries.push([pathFromRoot, "symlink", readlinkSync(path)]);
      } else if (info.isDirectory()) {
        if (pathFromRoot === ".git") continue;
        entries.push([pathFromRoot, "directory"]);
        visit(path);
      } else if (info.isFile()) {
        entries.push([pathFromRoot, "file", readFileSync(path).toString("base64")]);
      } else {
        entries.push([pathFromRoot, "other", info.mode]);
      }
    }
  };
  visit(root);
  return entries;
}

function checkpointBytes(path: string): unknown {
  if (!existsSync(path)) return [path, "missing"];
  const info = lstatSync(path);
  if (info.isDirectory()) return [path, "directory", treeFiles(path)];
  if (info.isSymbolicLink()) return [path, "symlink", readlinkSync(path)];
  return [path, "file", readFileSync(path).toString("base64")];
}

/** Includes repository refs, every registered index/status and all visible tree bytes. */
function fullRepoSnapshot(repo: string, extraTrees: string[], checkpoints: string[]): string {
  const registrations = worktreeEntries(repo);
  const worktrees = [realpathSync(repo), ...registrations.map((entry) => entry.path)];
  const uniqueWorktrees = [...new Set(worktrees)];
  const uniqueTrees = [...new Set([...uniqueWorktrees, ...extraTrees])];
  return JSON.stringify({
    refs: git(["for-each-ref", "--format=%(refname) %(objectname)"], repo),
    registrations: git(["worktree", "list", "--porcelain"], repo),
    worktrees: uniqueWorktrees.map((worktree) => ({
      path: worktree,
      head: git(["rev-parse", "HEAD"], worktree).trim(),
      branch: gitOut(["symbolic-ref", "--short", "-q", "HEAD"], worktree).stdout.trim() || "detached",
      status: git(["status", "--porcelain", "--untracked-files=all"], worktree),
      index: readFileSync(resolve(worktree, git(["rev-parse", "--git-path", "index"], worktree).trim())).toString("base64"),
    })),
    files: uniqueTrees.map((tree) => [tree, treeFiles(tree)]),
    checkpoints: checkpoints.map(checkpointBytes),
  });
}

function rebaseGate(status: string): { status: string; attempts: number; findings: string[] } {
  return { status, attempts: status === "passed" ? 1 : 0, findings: [] };
}

function rebaseLifecycle(
  phase = "implementation",
  planApproval = "approved",
  appReview = "not-started",
  reviewedMain: string | null = null,
): Record<string, unknown> {
  return { phase, plan_approval: planApproval, app_review: appReview, reviewed_main: reviewedMain };
}

function rebasePlan(
  slug: string,
  checkpointStatus = "passed",
  gateStatus = "passed",
  lifecycle: Record<string, unknown> = rebaseLifecycle(),
): Record<string, unknown> {
  const checkpoint = (id: number) => ({
    id,
    status: checkpointStatus,
    gates: {
      behavior: rebaseGate(gateStatus),
      ui: rebaseGate(gateStatus),
      review: rebaseGate(gateStatus),
    },
    tasks: [`checkpoint-${id} task`],
    acceptance: [`checkpoint-${id} acceptance`],
    files: [`src/checkpoint-${id}.ts`],
  });
  return { slug, checkpoints: [checkpoint(1), checkpoint(2)], lifecycle };
}

function mergeReadyPlan(slug: string, reviewedMain: string, reviewedFeature: string): Record<string, unknown> {
  return mergeLifecyclePlan(slug, reviewedMain, reviewedFeature, "ready-to-merge", "approved");
}

function mergeLifecyclePlan(
  slug: string,
  reviewedMain: string,
  reviewedFeature: string,
  phase: string,
  appReview: string,
): Record<string, unknown> {
  return rebasePlan(slug, "passed", "passed", {
    phase,
    plan_approval: "approved",
    app_review: appReview,
    reviewed_main: reviewedMain,
    reviewed_feature: reviewedFeature,
  });
}

function writeMergeCheckpoint(
  feature: string,
  slug: string,
  reviewedMain: string,
  reviewedFeature: string,
  phase = "ready-to-merge",
  appReview = "approved",
): string {
  const checkpoint = join(feature, ".ai-engineering", "workflow", "checkpoints", `${slug}.json`);
  mkdirSync(dirname(checkpoint), { recursive: true });
  writeFileSync(
    checkpoint,
    `${JSON.stringify(mergeLifecyclePlan(slug, reviewedMain, reviewedFeature, phase, appReview), null, 2)}\n`,
  );
  return checkpoint;
}

function writeReviewedMergeCheckpoint(feature: string, slug: string): string {
  const checkpoint = join(feature, ".ai-engineering", "workflow", "checkpoints", `${slug}.json`);
  mkdirSync(dirname(checkpoint), { recursive: true });
  const plan = rebasePlan(slug, "passed", "passed", {
    phase: "implementation",
    plan_approval: "approved",
    app_review: "not-started",
    reviewed_main: null,
    reviewed_feature: null,
  });
  const first = (plan.checkpoints as Array<{ gates: { ui: { status: string } } }>)[0];
  if (!first) throw new Error("reviewed merge fixture needs a checkpoint");
  first.gates.ui.status = "n/a";
  writeFileSync(checkpoint, `${JSON.stringify(plan, null, 2)}\n`);
  git(["add", checkpoint], feature);
  git(["commit", "-q", "-m", `${slug} approved implementation plan`], feature);
  return checkpoint;
}

function updateMergeRuntimeFields(checkpoint: string): void {
  const plan = JSON.parse(readFileSync(checkpoint, "utf8")) as {
    checkpoints: Array<{
      gates: { behavior: { attempts: number; findings: string[] } };
    }>;
  };
  const first = plan.checkpoints[0];
  if (!first) throw new Error("reviewed merge fixture needs a checkpoint");
  first.gates.behavior.attempts += 1;
  first.gates.behavior.findings.push("runtime gate rerun");
  writeFileSync(checkpoint, `${JSON.stringify(plan, null, 2)}\n`);
}

function installHook(repo: string, name: string, body: string): void {
  const hookDir = join(repo, "hooks");
  const hookPath = join(hookDir, name);
  mkdirSync(hookDir, { recursive: true });
  writeFileSync(hookPath, `#!/bin/sh\nset -eu\n${body}\n`);
  chmodSync(hookPath, 0o755);
  git(["config", "core.hooksPath", hookDir], repo);
}

function expectNoMergeLock(repo: string): void {
  const lockFiles: string[] = [];
  const inspect = (directory: string): void => {
    if (!existsSync(directory)) return;
    for (const name of readdirSync(directory)) {
      const path = join(directory, name);
      if (/lock/i.test(name)) lockFiles.push(path);
      if (lstatSync(path).isDirectory()) inspect(path);
    }
  };
  inspect(repo);
  inspect(defaultRoot(repo));
  expect(lockFiles).toEqual([]);
}

function expectWorktrees(repo: string, expectedPaths: string[]): void {
  const actualPaths = worktreeEntries(repo).map(({ path }) => realpathSync(path)).sort();
  expect(actualPaths).toEqual(expectedPaths.map((path) => realpathSync(path)).sort());
}

function addRebaseWorktree(repo: string, slug: string, branch = `feat/${slug}`, detached = false): string {
  const path = join(defaultRoot(repo), slug);
  mkdirSync(dirname(path), { recursive: true });
  git(
    detached
      ? ["worktree", "add", "--quiet", "--detach", path, "refs/heads/main"]
      : ["worktree", "add", "--quiet", "-b", branch, path, "refs/heads/main"],
    repo,
  );
  return path;
}

function writeRebasePlan(worktree: string, slug: string, plan: Record<string, unknown>): string {
  const path = join(worktree, ".ai-engineering", "workflow", "checkpoints", `${slug}.json`);
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, `${JSON.stringify(plan, null, 2)}\n`);
  git(["add", path], worktree);
  git(["commit", "-q", "-m", `plan ${slug}`], worktree);
  return path;
}

function commitRebaseFixtureFile(worktree: string, name: string, contents: string, message: string): string {
  const path = join(worktree, name);
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, contents);
  git(["add", name], worktree);
  git(["commit", "-q", "-m", message], worktree);
  return git(["rev-parse", "HEAD"], worktree).trim();
}

function advanceRebaseMain(repo: string): string {
  return commitRebaseFixtureFile(repo, "main-only.txt", "main\n", "advance local main");
}

interface MergeFixture {
  feature: string;
  slug: string;
  checkpoint: string;
  checkpointContents: string;
  reviewedMain: string;
  reviewedFeature: string;
  awaitingReviewCommit: string;
  featureTip: string;
}

function prepareMergeFixture(repo: string, slug: string): MergeFixture {
  const reviewedMain = git(["rev-parse", "refs/heads/main"], repo).trim();
  const feature = addRebaseWorktree(repo, slug);
  const checkpointPath = `.ai-engineering/workflow/checkpoints/${slug}.json`;
  const checkpoint = writeReviewedMergeCheckpoint(feature, slug);
  const reviewedFeature = commitRebaseFixtureFile(
    feature,
    "src/approved.ts",
    `${slug} approved feature\n`,
    `${slug} approved feature`,
  );
  writeMergeCheckpoint(
    feature,
    slug,
    reviewedMain,
    reviewedFeature,
    "awaiting-app-review",
    "pending",
  );
  updateMergeRuntimeFields(checkpoint);
  git(["add", checkpointPath], feature);
  git(["commit", "-q", "-m", `${slug} checkpoint awaiting app review`], feature);
  const awaitingReviewCommit = git(["rev-parse", "HEAD"], feature).trim();
  writeMergeCheckpoint(feature, slug, reviewedMain, reviewedFeature);
  updateMergeRuntimeFields(checkpoint);
  git(["add", checkpointPath], feature);
  git(["commit", "-q", "-m", `${slug} checkpoint approved`], feature);
  const featureTip = git(["rev-parse", "HEAD"], feature).trim();
  const checkpointContents = readFileSync(checkpoint, "utf8");
  if (git(["status", "--porcelain", "--untracked-files=all"], feature) !== "") {
    throw new Error(`merge fixture ${slug} must start clean`);
  }
  return {
    feature,
    slug,
    checkpoint,
    checkpointContents,
    reviewedMain,
    reviewedFeature,
    awaitingReviewCommit,
    featureTip,
  };
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

  test("new: extra positional file arguments fail with usage before creating the root or branch", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);

    const run = runCli(["worktree", "new", "alpha", "docs/shared.md"], repo);
    expect(run.status).not.toBe(0);
    expect(run.stderr.toLowerCase()).toContain("usage");
    expect(existsSync(root)).toBe(false);
    expect(branchNames(repo)).toEqual(["main"]);
    expect(worktreeEntries(repo)).toHaveLength(1);
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
    // The optional recap may already exist, but it must never block a worktree.
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

  test("new: does not create the legacy manifest", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);

    expect(runCli(["worktree", "new", "alpha"], repo).status).toBe(0);
    expect(existsSync(join(root, ".ai-eng-worktrees.json"))).toBe(false);
  });

  test("new: ignores and preserves malformed legacy manifest bytes", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);
    mkdirSync(root, { recursive: true });
    const declarations = join(root, ".ai-eng-worktrees.json");
    const malformedBytes = "{ legacy manifest is malformed\n";
    writeFileSync(declarations, malformedBytes);

    const run = runCli(["worktree", "new", "alpha"], repo);
    expect(run.status).toBe(0);
    expect(existsSync(join(root, "alpha"))).toBe(true);
    expect(readFileSync(declarations, "utf8")).toBe(malformedBytes);
  });

  test("rm: does not read, rewrite, or remove a malformed legacy manifest", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);
    expect(runCli(["worktree", "new", "alpha"], repo).status).toBe(0);

    const declarations = join(root, ".ai-eng-worktrees.json");
    const malformedBytes = "{ legacy manifest is malformed\n";
    writeFileSync(declarations, malformedBytes);

    const run = runCli(["worktree", "rm", "alpha"], repo);
    expect(run.status).toBe(0);
    expect(existsSync(join(root, "alpha"))).toBe(false);
    expect(branchNames(repo)).not.toContain("feat/alpha");
    expect(worktreeEntries(repo)).toHaveLength(1);
    expect(readFileSync(declarations, "utf8")).toBe(malformedBytes);
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

describe("ai-eng worktree rm (checkpoint 4)", () => {
  /** Put a commit on the open worktree's branch that local main does not have. */
  function commitInWorktree(repo: string, slug: string): void {
    git(["commit", "--allow-empty", "-q", "-m", `work in ${slug}`], join(defaultRoot(repo), slug));
  }

  test("unmerged: rm refuses, exits non-zero, says why, and leaves worktree and branch alive", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);
    expect(runCli(["worktree", "new", "alpha"], repo).status).toBe(0);
    const created = realpathSync(join(root, "alpha"));
    commitInWorktree(repo, "alpha");

    const run = runCli(["worktree", "rm", "alpha"], repo);
    expect(run.status).not.toBe(0);
    expect(run.stderr).toMatch(/not merged|unmerged|merge/i);
    // The refusal is total: neither side of the pair is touched.
    expect(existsSync(join(root, "alpha"))).toBe(true);
    expect(worktreeEntries(repo).map((entry) => entry.path)).toContain(created);
    expect(branchNames(repo)).toContain("feat/alpha");
  });

  test("force: rm --force removes an unmerged worktree and its branch", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);
    expect(runCli(["worktree", "new", "alpha"], repo).status).toBe(0);
    commitInWorktree(repo, "alpha");

    const run = runCli(["worktree", "rm", "alpha", "--force"], repo);
    expect(run.status).toBe(0);
    expect(existsSync(join(root, "alpha"))).toBe(false);
    expect(worktreeEntries(repo)).toHaveLength(1);
    expect(branchNames(repo)).not.toContain("feat/alpha");
  });

  test("merged: a branch merged into local main is removed without ceremony", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);
    expect(runCli(["worktree", "new", "alpha"], repo).status).toBe(0);
    commitInWorktree(repo, "alpha");
    // Bring main up to include the branch's work, so feat/alpha is genuinely merged.
    git(["merge", "--no-ff", "-q", "-m", "merge feat/alpha", "feat/alpha"], repo);

    const run = runCli(["worktree", "rm", "alpha"], repo);
    expect(run.status).toBe(0);
    expect(existsSync(join(root, "alpha"))).toBe(false);
    expect(branchNames(repo)).not.toContain("feat/alpha");
    expect(worktreeEntries(repo)).toHaveLength(1);
  });

  test("default path: no emitted command contains git branch -D", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);
    const log = join(repo, "invocations.log");
    expect(runCli(["worktree", "new", "alpha"], repo, shimEnv(log)).status).toBe(0);

    const run = runCli(["worktree", "rm", "alpha"], repo, shimEnv(log));
    expect(run.status).toBe(0);

    const args = loggedArgs(log);
    expect(args.length).toBeGreaterThan(0);
    expect(args).not.toContain("-D");
    expect(run.stdout).not.toContain("branch -D");
    expect(run.stderr).not.toContain("branch -D");
  });

  test("ignored content: rm removes the worktree and names the ignored path it dropped", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);
    // local.env is ignored in the repository, so it never shows as untracked.
    writeFileSync(join(repo, ".gitignore"), "local.env\n");
    git(["add", "-A"], repo);
    git(["commit", "-q", "-m", "ignore local.env"], repo);
    expect(runCli(["worktree", "new", "alpha"], repo).status).toBe(0);
    writeFileSync(join(root, "alpha", "local.env"), "SECRET=1\n");

    const run = runCli(["worktree", "rm", "alpha"], repo);
    expect(run.status).toBe(0);
    expect(existsSync(join(root, "alpha"))).toBe(false);
    // The removal says what it let go, so the person can see the ignored path lost.
    expect(`${run.stdout}${run.stderr}`).toContain("local.env");
  });

  test("failed removal reports scanned ignored content without claiming it was dropped", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);
    writeFileSync(join(repo, ".gitignore"), "local.env\n");
    git(["add", ".gitignore"], repo);
    git(["commit", "-q", "-m", "ignore local environment file"], repo);
    expect(runCli(["worktree", "new", "alpha"], repo).status).toBe(0);
    const feature = join(root, "alpha");
    writeFileSync(join(feature, "local.env"), "LOCAL_ONLY=1\n");

    const run = runCli(["worktree", "rm", "alpha"], repo, {
      ...shimEnv(join(repo, "remove-failure.log")),
      GIT_TEST_FAIL_WORKTREE_REMOVE: "1",
    });
    const output = `${run.stdout}${run.stderr}`;

    expect(run.status).not.toBe(0);
    expect(output).toContain("ignored content found before removal: local.env");
    expect(output).toContain("remaining state is unknown");
    expect(output).not.toContain("dropped ignored: local.env");
    expect(existsSync(feature)).toBe(true);
    expect(existsSync(join(feature, "local.env"))).toBe(true);
    expect(branchNames(repo)).toContain("feat/alpha");
  });

  test("U-CP4-d: rm forces its own status read and names the ignored path despite status.showUntrackedFiles=no", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);
    writeFileSync(join(repo, ".gitignore"), "local.env\n");
    git(["add", "-A"], repo);
    git(["commit", "-q", "-m", "ignore local.env"], repo);
    // A hostile local config must not hide the ignored file the verb is about to drop.
    git(["config", "status.showUntrackedFiles", "no"], repo);
    expect(runCli(["worktree", "new", "alpha"], repo).status).toBe(0);
    writeFileSync(join(root, "alpha", "local.env"), "SECRET=1\n");

    const run = runCli(["worktree", "rm", "alpha"], repo);
    expect(run.status).toBe(0);
    expect(existsSync(join(root, "alpha"))).toBe(false);
    expect(`${run.stdout}${run.stderr}`).toContain("local.env");
  });

  test("U-CP4-e: a worktree whose only ignored content is .DS_Store is removed and names it", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);
    writeFileSync(join(repo, ".gitignore"), ".DS_Store\n");
    git(["add", "-A"], repo);
    git(["commit", "-q", "-m", "ignore .DS_Store"], repo);
    expect(runCli(["worktree", "new", "alpha"], repo).status).toBe(0);
    writeFileSync(join(root, "alpha", ".DS_Store"), "junk\n");

    const run = runCli(["worktree", "rm", "alpha"], repo);
    expect(run.status).toBe(0);
    expect(existsSync(join(root, "alpha"))).toBe(false);
    expect(`${run.stdout}${run.stderr}`).toContain(".DS_Store");
  });
});

describe("ai-eng worktree rebase (checkpoint 5)", () => {
  function expectRefusalWithoutMutation(
    repo: string,
    slug: string,
    trees: string[],
    checkpoints: string[],
    args = ["worktree", "rebase", slug],
  ): Run {
    const before = fullRepoSnapshot(repo, trees, checkpoints);
    const run = runCli(args, repo);
    expect(run.status).not.toBe(0);
    expect(fullRepoSnapshot(repo, trees, checkpoints)).toBe(before);
    return run;
  }

  test("U20a: rebases only the registered feature onto local main and reports its full SHA", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);

    const remote = join(dirname(repo), `${basename(repo)}-origin.git`);
    cleanups.push(remote);
    git(["init", "--bare", "--quiet", remote], dirname(repo));
    git(["remote", "add", "origin", remote], repo);
    git(["push", "--quiet", "origin", "refs/heads/main:refs/heads/main"], repo);
    git(["fetch", "--quiet", "origin"], repo);
    const base = git(["rev-parse", "refs/heads/main"], repo).trim();
    const baseTree = git(["rev-parse", `${base}^{tree}`], repo).trim();
    const remoteTip = git(["commit-tree", baseTree, "-p", base, "-m", "remote-only update"], repo).trim();
    git(["push", "--quiet", "origin", `${remoteTip}:refs/heads/main`], repo);
    git(["fetch", "--quiet", "origin"], repo);
    const remoteMain = git(["rev-parse", "refs/remotes/origin/main"], repo).trim();
    expect(remoteMain).toBe(remoteTip);

    const feature = addRebaseWorktree(repo, "alpha");
    const sibling = addRebaseWorktree(repo, "sibling");
    const checkpoint = writeRebasePlan(feature, "alpha", rebasePlan("alpha"));
    const checkpointContents = readFileSync(checkpoint, "utf8");
    const featureBefore = commitRebaseFixtureFile(feature, "feature-only.txt", "feature\n", "feature change");
    const siblingBefore = commitRebaseFixtureFile(sibling, "sibling-only.txt", "sibling\n", "sibling change");
    const mainBefore = advanceRebaseMain(repo);
    expect(git(["rev-parse", `${mainBefore}^`], repo).trim()).toBe(base);

    const log = join(root, "rebase-invocations.log");
    const run = runCli(["worktree", "rebase", "alpha"], repo, shimEnv(log));
    expect(run.status).toBe(0);
    expect(run.stdout.trim().split(/\s+/)).toContain(mainBefore);

    const invocations = loggedInvocations(log);
    expect(invocations.length).toBeGreaterThan(0);
    expect(invocations.filter((args) => args[0] === "rebase")).toEqual([["rebase", "refs/heads/main"]]);
    expect(invocations.some((args) => ["fetch", "pull", "push", "remote", "merge"].includes(args[0] ?? ""))).toBe(false);
    expect(invocations.flat()).not.toContain("origin");
    expect(invocations.flat()).not.toContain("feat/sibling");

    const featureAfter = git(["rev-parse", "refs/heads/feat/alpha"], repo).trim();
    expect(featureAfter).not.toBe(featureBefore);
    expect(gitOut(["merge-base", "--is-ancestor", "refs/heads/main", featureAfter], repo).status).toBe(0);
    expect(git(["rev-parse", "refs/heads/main"], repo).trim()).toBe(mainBefore);
    expect(git(["rev-parse", "refs/remotes/origin/main"], repo).trim()).toBe(remoteMain);
    expect(git(["rev-parse", "refs/heads/feat/sibling"], repo).trim()).toBe(siblingBefore);
    expect(git(["status", "--porcelain", "--untracked-files=all"], feature)).toBe("");
    expect(git(["status", "--porcelain", "--untracked-files=all"], sibling)).toBe("");
    expect(readFileSync(checkpoint, "utf8")).toBe(checkpointContents);
    expect(worktreeEntries(repo).map((entry) => entry.path)).toContain(realpathSync(feature));
    expect(worktreeEntries(repo).map((entry) => entry.path)).toContain(realpathSync(sibling));
  });

  test("U20b: rejects extra base arguments before changing any Git or worktree state", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);
    const feature = addRebaseWorktree(repo, "extra-args");
    const checkpoint = writeRebasePlan(feature, "extra-args", rebasePlan("extra-args"));
    commitRebaseFixtureFile(feature, "feature-only.txt", "feature\n", "feature change");
    advanceRebaseMain(repo);

    const run = expectRefusalWithoutMutation(
      repo,
      "extra-args",
      [root],
      [checkpoint],
      ["worktree", "rebase", "extra-args", "refs/heads/main"],
    );
    expect(run.stderr.toLowerCase()).toContain("usage");
  });

  test("U20b: refuses dirty tracked and untracked feature content without mutation", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);
    const feature = addRebaseWorktree(repo, "dirty");
    const checkpoint = writeRebasePlan(feature, "dirty", rebasePlan("dirty"));
    commitRebaseFixtureFile(feature, "feature-only.txt", "feature\n", "feature change");
    advanceRebaseMain(repo);
    writeFileSync(join(feature, "README.md"), "# staged dirt\n");
    git(["add", "README.md"], feature);
    writeFileSync(join(feature, "untracked.txt"), "untracked dirt\n");

    expectRefusalWithoutMutation(repo, "dirty", [root], [checkpoint]);
  });

  test("U20b: refuses a missing registered worktree without creating or pruning anything", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);
    mkdirSync(root, { recursive: true });
    const slug = "missing-worktree";
    const base = git(["rev-parse", "refs/heads/main"], repo).trim();
    const baseTree = git(["rev-parse", `${base}^{tree}`], repo).trim();
    const featureCommit = git(["commit-tree", baseTree, "-p", base, "-m", "missing worktree feature"], repo).trim();
    git(["update-ref", `refs/heads/feat/${slug}`, featureCommit], repo);
    advanceRebaseMain(repo);
    const missingPath = join(root, slug);
    const checkpoint = join(missingPath, ".ai-engineering", "workflow", "checkpoints", `${slug}.json`);

    expectRefusalWithoutMutation(repo, slug, [root, missingPath], [checkpoint]);
  });

  test("U20b: refuses a registered feature without its checkpoint", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);
    const feature = addRebaseWorktree(repo, "missing-checkpoint");
    commitRebaseFixtureFile(feature, "feature-only.txt", "feature\n", "feature change");
    advanceRebaseMain(repo);
    const checkpoint = join(feature, ".ai-engineering", "workflow", "checkpoints", "missing-checkpoint.json");

    expectRefusalWithoutMutation(repo, "missing-checkpoint", [root], [checkpoint]);
  });

  test("U20b: refuses malformed checkpoint bytes without mutation", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);
    const feature = addRebaseWorktree(repo, "malformed");
    const checkpoint = join(feature, ".ai-engineering", "workflow", "checkpoints", "malformed.json");
    mkdirSync(dirname(checkpoint), { recursive: true });
    writeFileSync(checkpoint, "{ malformed lifecycle\n");
    git(["add", checkpoint], feature);
    git(["commit", "-q", "-m", "malformed checkpoint"], feature);
    commitRebaseFixtureFile(feature, "feature-only.txt", "feature\n", "feature change");
    advanceRebaseMain(repo);

    expectRefusalWithoutMutation(repo, "malformed", [root], [checkpoint]);
  });

  test("U20b: refuses a legacy checkpoint without lifecycle data and preserves its bytes", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);
    const feature = addRebaseWorktree(repo, "legacy");
    const plan = rebasePlan("legacy");
    delete plan.lifecycle;
    const checkpoint = writeRebasePlan(feature, "legacy", plan);
    commitRebaseFixtureFile(feature, "feature-only.txt", "feature\n", "feature change");
    advanceRebaseMain(repo);

    expectRefusalWithoutMutation(repo, "legacy", [root], [checkpoint]);
  });

  test("U20b: refuses an unknown lifecycle phase without mutation", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);
    const feature = addRebaseWorktree(repo, "unknown-phase");
    const checkpoint = writeRebasePlan(
      feature,
      "unknown-phase",
      rebasePlan("unknown-phase", "passed", "passed", rebaseLifecycle("not-a-phase")),
    );
    commitRebaseFixtureFile(feature, "feature-only.txt", "feature\n", "feature change");
    advanceRebaseMain(repo);

    expectRefusalWithoutMutation(repo, "unknown-phase", [root], [checkpoint]);
  });

  test("U20b: refuses a valid lifecycle outside implementation without mutation", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);
    const reviewedMain = git(["rev-parse", "refs/heads/main"], repo).trim();
    const feature = addRebaseWorktree(repo, "awaiting-review");
    const checkpoint = writeRebasePlan(
      feature,
      "awaiting-review",
      rebasePlan("awaiting-review", "passed", "passed", rebaseLifecycle("awaiting-app-review", "approved", "pending", reviewedMain)),
    );
    commitRebaseFixtureFile(feature, "feature-only.txt", "feature\n", "feature change");

    expectRefusalWithoutMutation(repo, "awaiting-review", [root], [checkpoint]);
  });

  test("U20b: refuses an incomplete planned checkpoint without mutation", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);
    const feature = addRebaseWorktree(repo, "incomplete-checkpoint");
    const checkpoint = writeRebasePlan(
      feature,
      "incomplete-checkpoint",
      rebasePlan("incomplete-checkpoint", "pending"),
    );
    commitRebaseFixtureFile(feature, "feature-only.txt", "feature\n", "feature change");
    advanceRebaseMain(repo);

    expectRefusalWithoutMutation(repo, "incomplete-checkpoint", [root], [checkpoint]);
  });

  test("U20b: refuses an incomplete planned gate without mutation", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);
    const feature = addRebaseWorktree(repo, "incomplete-gate");
    const checkpoint = writeRebasePlan(
      feature,
      "incomplete-gate",
      rebasePlan("incomplete-gate", "passed", "pending"),
    );
    commitRebaseFixtureFile(feature, "feature-only.txt", "feature\n", "feature change");
    advanceRebaseMain(repo);

    expectRefusalWithoutMutation(repo, "incomplete-gate", [root], [checkpoint]);
  });

  test("U20b: refuses a detached registered worktree without mutation", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);
    const feature = addRebaseWorktree(repo, "detached", "feat/detached", true);
    const checkpoint = writeRebasePlan(feature, "detached", rebasePlan("detached"));
    commitRebaseFixtureFile(feature, "feature-only.txt", "feature\n", "feature change");
    advanceRebaseMain(repo);

    expectRefusalWithoutMutation(repo, "detached", [root], [checkpoint]);
  });

  test("U20b: refuses a registered worktree on a mismatched feature branch without mutation", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);
    const feature = addRebaseWorktree(repo, "alpha", "feat/other");
    const checkpoint = writeRebasePlan(feature, "alpha", rebasePlan("alpha"));
    commitRebaseFixtureFile(feature, "feature-only.txt", "feature\n", "feature change");
    advanceRebaseMain(repo);

    expectRefusalWithoutMutation(repo, "alpha", [root], [checkpoint]);
  });

  test("U20b: refuses an unmanaged directory even when its matching branch and checkpoint exist", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);
    const slug = "unmanaged";
    const unmanaged = join(root, slug);
    const checkpoint = join(unmanaged, ".ai-engineering", "workflow", "checkpoints", `${slug}.json`);
    git(["branch", `feat/${slug}`, "refs/heads/main"], repo);
    mkdirSync(dirname(checkpoint), { recursive: true });
    writeFileSync(join(unmanaged, "README.md"), readFileSync(join(repo, "README.md")));
    writeFileSync(checkpoint, `${JSON.stringify(rebasePlan(slug), null, 2)}\n`);
    advanceRebaseMain(repo);

    expectRefusalWithoutMutation(repo, slug, [root, unmanaged], [checkpoint]);
  });

  test("U20c: leaves a conflicting CLI rebase active for agent handling without changing lifecycle bytes", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);
    const feature = addRebaseWorktree(repo, "conflict");
    const checkpoint = writeRebasePlan(feature, "conflict", rebasePlan("conflict"));
    const checkpointContents = readFileSync(checkpoint, "utf8");
    commitRebaseFixtureFile(feature, "README.md", "# feature change\n", "conflicting feature change");
    commitRebaseFixtureFile(repo, "README.md", "# main change\n", "conflicting main change");

    try {
      const log = join(root, "conflict-invocations.log");
      const run = runCli(["worktree", "rebase", "conflict"], repo, shimEnv(log));
      expect(run.status).not.toBe(0);
      expect(readFileSync(checkpoint, "utf8")).toBe(checkpointContents);
      expect(git(["status", "--porcelain", "--untracked-files=all"], feature)).toMatch(/README\.md/);
      expect(
        existsSync(resolve(feature, git(["rev-parse", "--git-path", "rebase-merge"], feature).trim())) ||
          existsSync(resolve(feature, git(["rev-parse", "--git-path", "rebase-apply"], feature).trim())),
      ).toBe(true);
      expect(loggedInvocations(log).filter((args) => args[0] === "rebase")).toEqual([
        ["rebase", "refs/heads/main"],
      ]);
    } finally {
      const mergeState = resolve(feature, git(["rev-parse", "--git-path", "rebase-merge"], feature).trim());
      const applyState = resolve(feature, git(["rev-parse", "--git-path", "rebase-apply"], feature).trim());
      if (existsSync(mergeState) || existsSync(applyState)) git(["rebase", "--abort"], feature);
    }
  });

  test("U20d: preserves rewritten work and reports a main advance during rebase", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);
    const feature = addRebaseWorktree(repo, "main-race");
    const checkpoint = writeRebasePlan(feature, "main-race", rebasePlan("main-race"));
    const checkpointContents = readFileSync(checkpoint, "utf8");
    const featureBefore = commitRebaseFixtureFile(feature, "feature-only.txt", "feature\n", "feature change");
    const mainBefore = advanceRebaseMain(repo);
    const mainTree = git(["rev-parse", `${mainBefore}^{tree}`], repo).trim();
    const mainAfter = git(
      ["commit-tree", mainTree, "-p", mainBefore, "-m", "advance local main during rebase"],
      repo,
    ).trim();
    const hookDir = join(repo, "hooks");
    const hook = join(hookDir, "post-rewrite");
    mkdirSync(hookDir, { recursive: true });
    writeFileSync(hook, `#!/bin/sh\ngit update-ref refs/heads/main ${mainAfter}\n`);
    chmodSync(hook, 0o755);
    git(["config", "core.hooksPath", hookDir], repo);

    const log = join(root, "main-race-invocations.log");
    const run = runCli(["worktree", "rebase", "main-race"], repo, shimEnv(log));
    const output = `${run.stdout}${run.stderr}`;
    const featureAfter = git(["rev-parse", "refs/heads/feat/main-race"], repo).trim();
    const invocations = loggedInvocations(log);

    expect(git(["rev-parse", "refs/heads/main"], repo).trim()).toBe(mainAfter);
    expect(run.status).not.toBe(0);
    expect(run.stdout).not.toContain("✓");
    expect(output).toContain(mainBefore);
    expect(output).toContain(mainAfter);
    expect(output.toLowerCase()).toContain("rerun sync");
    expect(featureAfter).not.toBe(featureBefore);
    expect(gitOut(["merge-base", "--is-ancestor", mainBefore, featureAfter], repo).status).toBe(0);
    expect(gitOut(["merge-base", "--is-ancestor", mainAfter, featureAfter], repo).status).not.toBe(0);
    expect(git(["rev-parse", "HEAD"], feature).trim()).toBe(featureAfter);
    expect(git(["show", "HEAD:feature-only.txt"], feature)).toBe("feature\n");
    expect(readFileSync(checkpoint, "utf8")).toBe(checkpointContents);
    expect(invocations.filter((args) => args[0] === "rebase")).toEqual([["rebase", "refs/heads/main"]]);
    expect(invocations.some((args) => args[0] === "reset" || (args[0] === "rebase" && args[1] === "--abort"))).toBe(false);
  });
});

describe("ai-eng worktree merge (checkpoint 6)", () => {
  test("U24-U25: app-review pending and approval are separate checkpoint-only commits with stable reviewed SHAs", () => {
    const repo = tempRepo();
    const approved = prepareMergeFixture(repo, "merge-review-commits");
    const checkpointPath = `.ai-engineering/workflow/checkpoints/${approved.slug}.json`;
    const awaitingState = JSON.parse(git(["show", `${approved.awaitingReviewCommit}:${checkpointPath}`], repo)) as {
      lifecycle: Record<string, unknown>;
    };
    const approvedState = JSON.parse(approved.checkpointContents) as { lifecycle: Record<string, unknown> };
    const awaitingParent = git(["rev-parse", `${approved.awaitingReviewCommit}^`], repo).trim();
    const approvedParent = git(["rev-parse", `${approved.featureTip}^`], repo).trim();
    const awaitingChangedPaths = git(
      ["diff-tree", "--no-commit-id", "--name-only", "-r", approved.awaitingReviewCommit],
      repo,
    ).trim().split("\n");
    const approvedChangedPaths = git(
      ["diff-tree", "--no-commit-id", "--name-only", "-r", approved.featureTip],
      repo,
    ).trim().split("\n");

    expect(awaitingParent).toBe(approved.reviewedFeature);
    expect(approvedParent).toBe(approved.awaitingReviewCommit);
    expect(awaitingChangedPaths).toEqual([checkpointPath]);
    expect(approvedChangedPaths).toEqual([checkpointPath]);
    expect(awaitingState.lifecycle).toEqual({
      phase: "awaiting-app-review",
      plan_approval: "approved",
      app_review: "pending",
      reviewed_main: approved.reviewedMain,
      reviewed_feature: approved.reviewedFeature,
    });
    expect(approvedState.lifecycle).toEqual({
      phase: "ready-to-merge",
      plan_approval: "approved",
      app_review: "approved",
      reviewed_main: approved.reviewedMain,
      reviewed_feature: approved.reviewedFeature,
    });
    expect(gitOut(
      ["diff", "--quiet", approved.reviewedFeature, approved.featureTip, "--", ".", `:(exclude)${checkpointPath}`],
      repo,
    ).status).toBe(0);
    expect(git(["rev-parse", `refs/heads/feat/${approved.slug}`], repo).trim()).toBe(approved.featureTip);
  });

  test("U26: refuses a post-review code commit without publishing, removing or changing the approved feature", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);
    const approved = prepareMergeFixture(repo, "merge-unreviewed-code");
    const mainBefore = git(["rev-parse", "refs/heads/main"], repo).trim();
    const featureTipBefore = approved.featureTip;
    const checkpointBefore = readFileSync(approved.checkpoint, "utf8");

    const unreviewedTip = commitRebaseFixtureFile(
      approved.feature,
      "src/unreviewed.ts",
      "not reviewed\n",
      "unreviewed code",
    );
    const run = runCli(["worktree", "merge", approved.slug], repo);

    expect(run.status).not.toBe(0);
    expect(git(["rev-parse", "refs/heads/main"], repo).trim()).toBe(mainBefore);
    expect(git(["rev-parse", `refs/heads/feat/${approved.slug}`], repo).trim()).toBe(unreviewedTip);
    expect(unreviewedTip).not.toBe(featureTipBefore);
    expect(gitOut(["merge-base", "--is-ancestor", approved.reviewedFeature, unreviewedTip], repo).status).toBe(0);
    expect(readFileSync(approved.checkpoint, "utf8")).toBe(checkpointBefore);
    expect(readFileSync(join(approved.feature, "src", "unreviewed.ts"), "utf8")).toBe("not reviewed\n");
    expect(existsSync(approved.feature)).toBe(true);
    expectWorktrees(repo, [repo, approved.feature]);
    expectNoMergeLock(repo);
  });

  test("F4: refuses a checkpoint-only commit that changes the reviewed plan", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);
    const approved = prepareMergeFixture(repo, "merge-unreviewed-plan");
    const mainBefore = git(["rev-parse", "refs/heads/main"], repo).trim();
    const checkpointPlan = JSON.parse(readFileSync(approved.checkpoint, "utf8")) as {
      checkpoints: Array<{ tasks: string[] }>;
    };
    const first = checkpointPlan.checkpoints[0];
    if (!first) throw new Error("reviewed merge fixture needs a checkpoint");
    first.tasks[0] = "task changed after human review";
    writeFileSync(approved.checkpoint, `${JSON.stringify(checkpointPlan, null, 2)}\n`);
    git(["add", `.ai-engineering/workflow/checkpoints/${approved.slug}.json`], approved.feature);
    git(["commit", "-q", "-m", "change reviewed plan"], approved.feature);
    const changedTip = git(["rev-parse", "HEAD"], approved.feature).trim();

    const run = runCli(["worktree", "merge", approved.slug], repo);

    expect(run.status).not.toBe(0);
    expect(`${run.stdout}${run.stderr}`).toContain("changes the reviewed checkpoint plan");
    expect(git(["rev-parse", "refs/heads/main"], repo).trim()).toBe(mainBefore);
    expect(git(["rev-parse", `refs/heads/feat/${approved.slug}`], repo).trim()).toBe(changedTip);
    expect(existsSync(approved.feature)).toBe(true);
    expect(readFileSync(approved.checkpoint, "utf8")).toContain("task changed after human review");
    expectWorktrees(repo, [repo, approved.feature]);
    expectNoMergeLock(repo);
  });

  test("F5: merged feature cleanup surfaces the ignored paths it removes", () => {
    const repo = tempRepo();
    cleanups.push(defaultRoot(repo));
    writeFileSync(join(repo, ".gitignore"), "local.env\n");
    git(["add", ".gitignore"], repo);
    git(["commit", "-q", "-m", "ignore local environment file"], repo);
    const approved = prepareMergeFixture(repo, "merge-ignored-content");
    writeFileSync(join(approved.feature, "local.env"), "LOCAL_ONLY=1\n");

    const run = runCli(["worktree", "merge", approved.slug], repo);

    expect(run.status).toBe(0);
    expect(`${run.stdout}${run.stderr}`).toContain("dropped ignored: local.env");
    expect(existsSync(approved.feature)).toBe(false);
    expect(gitOut(["show-ref", "--verify", `refs/heads/feat/${approved.slug}`], repo).status).not.toBe(0);
  });

  test("F5: branch-delete failure forwards unreadable scan warning after worktree removal", () => {
    const repo = tempRepo();
    cleanups.push(defaultRoot(repo));
    writeFileSync(join(repo, ".gitignore"), "local.env\n");
    git(["add", ".gitignore"], repo);
    git(["commit", "-q", "-m", "ignore local environment file"], repo);
    const approved = prepareMergeFixture(repo, "merge-branch-delete-failure");
    writeFileSync(join(approved.feature, "local.env"), "LOCAL_ONLY=1\n");

    const run = runCli(["worktree", "merge", approved.slug], repo, {
      ...shimEnv(join(repo, ".git", "branch-delete-failure.log")),
      GIT_TEST_FAIL_BRANCH_DELETE: "1",
      GIT_TEST_UNREADABLE_IGNORED_SCAN: "1",
    });
    const output = `${run.stdout}${run.stderr}`;

    expect(run.status).not.toBe(0);
    expect(output).toContain("is published, but safe feature cleanup failed");
    expect(output).toContain(`worktree ${approved.slug} was removed`);
    expect(output).toContain(`branch feat/${approved.slug} remains`);
    expect(output).toContain("ignored content could not be read");
    expect(output).toContain("anything it held was dropped unseen");
    expect(existsSync(approved.feature)).toBe(false);
    expect(branchNames(repo)).toContain(`feat/${approved.slug}`);
  });

  test("F5: post-removal verification failure reports ignored files and completed removal", () => {
    const repo = tempRepo();
    cleanups.push(defaultRoot(repo));
    writeFileSync(join(repo, ".gitignore"), "local.env\n");
    git(["add", ".gitignore"], repo);
    git(["commit", "-q", "-m", "ignore local environment file"], repo);
    const approved = prepareMergeFixture(repo, "merge-post-removal-verification");
    writeFileSync(join(approved.feature, "local.env"), "LOCAL_ONLY=1\n");
    const marker = join(repo, ".git", "test-feature-removal-complete");

    const run = runCli(["worktree", "merge", approved.slug], repo, {
      ...shimEnv(join(repo, ".git", "post-removal-verification-failure.log")),
      GIT_TEST_FAIL_POST_REMOVE_LIST: "1",
      GIT_TEST_POST_REMOVE_MARKER: marker,
    });
    const output = `${run.stdout}${run.stderr}`;

    expect(run.status).not.toBe(0);
    expect(output).toContain("dropped ignored: local.env");
    expect(output).toContain("post-removal verification failed");
    expect(output).toContain("worktree inventory is unreadable");
    expect(output).toContain("cleanup command reported success");
    expect(existsSync(approved.feature)).toBe(false);
    expect(gitOut(["show-ref", "--verify", `refs/heads/feat/${approved.slug}`], repo).status).not.toBe(0);
  });

  test("U26-U27: runs commit hooks in a detached temporary worktree, publishes exact reviewed parents, refreshes main, then safely removes only the approved feature", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);
    const approved = prepareMergeFixture(repo, "merge-approved");
    const sibling = addRebaseWorktree(repo, "merge-sibling");
    commitRebaseFixtureFile(sibling, "src/sibling.ts", "unapproved sibling\n", "unapproved sibling");
    const siblingCheckpoint = join(sibling, ".ai-engineering", "workflow", "checkpoints", "merge-sibling.json");
    mkdirSync(dirname(siblingCheckpoint), { recursive: true });
    writeFileSync(
      siblingCheckpoint,
      `${JSON.stringify(rebasePlan("merge-sibling"), null, 2)}\n`,
    );
    const siblingCheckpointContents = readFileSync(siblingCheckpoint, "utf8");
    const siblingTip = git(["rev-parse", "refs/heads/feat/merge-sibling"], repo).trim();
    const hookLog = join(root, "merge-hook.log");
    const hookParents = join(root, "merge-hook-parents.log");

    installHook(
      repo,
      "post-commit",
      [
        "printf '%s\\t%s\\t%s\\n' \"$PWD\" \"$(git rev-parse HEAD)\" \"$(git symbolic-ref -q --short HEAD || printf detached)\" >> \"$AI_ENG_TEST_HOOK_LOG\"",
        "git rev-list --parents -n 1 HEAD >> \"$AI_ENG_TEST_PARENT_LOG\"",
      ].join("\n"),
    );
    const primaryStatus = git(["status", "--porcelain", "--untracked-files=all"], repo);
    const log = join(root, "git-invocations.log");
    const run = runCli(["worktree", "merge", approved.slug], repo, {
      ...shimEnv(log),
      AI_ENG_TEST_HOOK_LOG: hookLog,
      AI_ENG_TEST_PARENT_LOG: hookParents,
    });

    expect(run.status).toBe(0);
    expect(existsSync(hookLog)).toBe(true);
    const [hookCwd, hookHead, hookBranch] = readFileSync(hookLog, "utf8").trim().split("\t");
    expect(hookCwd).toBeDefined();
    expect(hookCwd).not.toBe(repo);
    expect(hookHead).toBeDefined();
    expect(hookBranch).toBe("detached");
    const mergeCommit = git(["rev-parse", "refs/heads/main"], repo).trim();
    expect(hookHead).toBe(mergeCommit);
    expect(git(["rev-list", "--parents", "-n", "1", mergeCommit], repo).trim().split(" ")).toEqual([
      mergeCommit,
      approved.reviewedMain,
      approved.featureTip,
    ]);
    expect(readFileSync(hookParents, "utf8").trim().split(" ")).toEqual([
      mergeCommit,
      approved.reviewedMain,
      approved.featureTip,
    ]);
    expect(git(["rev-parse", "HEAD"], repo).trim()).toBe(mergeCommit);
    expect(git(["status", "--porcelain", "--untracked-files=all"], repo)).toBe(primaryStatus);
    expect(gitOut(["merge-base", "--is-ancestor", approved.reviewedFeature, mergeCommit], repo).status).toBe(0);
    expect(gitOut(["merge-base", "--is-ancestor", approved.featureTip, mergeCommit], repo).status).toBe(0);
    expect(
      gitOut(
        [
          "diff",
          "--quiet",
          approved.reviewedFeature,
          mergeCommit,
          "--",
          ".",
          `:(exclude).ai-engineering/workflow/checkpoints/${approved.slug}.json`,
        ],
        repo,
      ).status,
    ).toBe(0);
    expect(existsSync(approved.feature)).toBe(false);
    expect(gitOut(["show-ref", "--verify", `refs/heads/feat/${approved.slug}`], repo).status).not.toBe(0);
    expect(readFileSync(siblingCheckpoint, "utf8")).toBe(siblingCheckpointContents);
    expect(git(["rev-parse", "refs/heads/feat/merge-sibling"], repo).trim()).toBe(siblingTip);
    expect(readFileSync(join(sibling, "src", "sibling.ts"), "utf8")).toBe("unapproved sibling\n");
    expect(gitOut(["merge-base", "--is-ancestor", siblingTip, mergeCommit], repo).status).not.toBe(0);
    expectWorktrees(repo, [repo, sibling]);
    expectNoMergeLock(repo);
    const invocations = loggedInvocations(log);
    expect(invocations.some((args) => args[0] === "worktree" && args[1] === "lock")).toBe(false);
    expect(invocations.some((args) => args.some((arg) => /\.lock\b/i.test(arg)))).toBe(false);
    expect(JSON.parse(approved.checkpointContents).lifecycle.phase).toBe("ready-to-merge");
    expect(approved.checkpointContents).not.toContain('"phase": "complete"');
    expect(existsSync(approved.checkpoint)).toBe(false);
  });

  test("U29: a post-commit main advance loses the reviewed-main CAS without publishing stale merge or changing feature state", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);
    const approved = prepareMergeFixture(repo, "merge-main-race");
    const reviewedTree = git(["rev-parse", `${approved.reviewedMain}^{tree}`], repo).trim();
    const advancedMain = git(
      ["commit-tree", reviewedTree, "-p", approved.reviewedMain, "-m", "advance main during temporary commit"],
      repo,
    ).trim();
    const hookLog = join(root, "race-hook.log");
    installHook(
      repo,
      "post-commit",
      [
        "printf '%s\\n' \"$(git rev-parse HEAD)\" > \"$AI_ENG_TEST_HOOK_LOG\"",
        "git update-ref refs/heads/main \"$AI_ENG_TEST_ADVANCED_MAIN\" \"$AI_ENG_TEST_REVIEWED_MAIN\"",
      ].join("\n"),
    );

    const run = runCli(["worktree", "merge", approved.slug], repo, {
      AI_ENG_TEST_HOOK_LOG: hookLog,
      AI_ENG_TEST_ADVANCED_MAIN: advancedMain,
      AI_ENG_TEST_REVIEWED_MAIN: approved.reviewedMain,
    });
    const output = `${run.stdout}${run.stderr}`;
    expect(existsSync(hookLog)).toBe(true);
    const temporaryMerge = readFileSync(hookLog, "utf8").trim();

    expect(run.status).not.toBe(0);
    expect(git(["rev-list", "--parents", "-n", "1", temporaryMerge], repo).trim().split(" ")).toEqual([
      temporaryMerge,
      approved.reviewedMain,
      approved.featureTip,
    ]);
    expect(output).toContain(approved.reviewedMain);
    expect(output).toContain(advancedMain);
    expect(output.toLowerCase()).toMatch(/sync|review/);
    expect(git(["rev-parse", "refs/heads/main"], repo).trim()).toBe(advancedMain);
    expect(gitOut(["merge-base", "--is-ancestor", temporaryMerge, advancedMain], repo).status).not.toBe(0);
    expect(git(["rev-parse", "refs/heads/feat/merge-main-race"], repo).trim()).toBe(approved.featureTip);
    expect(git(["status", "--porcelain", "--untracked-files=all"], approved.feature)).toBe("");
    expect(readFileSync(approved.checkpoint, "utf8")).toBe(approved.checkpointContents);
    expect(readFileSync(join(approved.feature, "src", "approved.ts"), "utf8")).toBe(
      "merge-main-race approved feature\n",
    );
    expectWorktrees(repo, [repo, approved.feature]);
    expectNoMergeLock(repo);
    expect(approved.checkpointContents).not.toContain('"phase": "complete"');
  });

  test("U29: two prepared compare-and-swap transactions publish at most one merge and preserve the losing feature", async () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);
    const features = [
      prepareMergeFixture(repo, "merge-race-one"),
      prepareMergeFixture(repo, "merge-race-two"),
    ];
    expect(features[0]?.reviewedMain).toBe(features[1]?.reviewedMain);
    const barrierLog = join(root, "merge-barrier.log");
    installHook(
      repo,
      "post-commit",
      [
        "printf '%s\\t%s\\n' \"$(git rev-parse HEAD)\" \"$PWD\" >> \"$AI_ENG_TEST_BARRIER_LOG\"",
        "waits=0",
        "while [ \"$(wc -l < \"$AI_ENG_TEST_BARRIER_LOG\")\" -lt 2 ]; do",
        "  waits=$((waits + 1))",
        "  [ \"$waits\" -lt 401 ] || exit 91",
        "  sleep 0.025",
        "done",
      ].join("\n"),
    );

    const runs = await Promise.all(
      features.map((feature) =>
        runCliAsync(["worktree", "merge", feature.slug], repo, {
          AI_ENG_TEST_BARRIER_LOG: barrierLog,
        }),
      ),
    );

    expect(runs.filter((run) => run.status === 0)).toHaveLength(1);
    expect(runs.filter((run) => run.status !== 0)).toHaveLength(1);
    const surviving = features.filter((feature) => existsSync(feature.feature));
    expect(surviving).toHaveLength(1);
    const loser = surviving[0]!;
    const winner = features.find((feature) => feature.slug !== loser.slug)!;
    const mergeCommit = git(["rev-parse", "refs/heads/main"], repo).trim();
    const mergeParents = git(["rev-list", "--parents", "-n", "1", mergeCommit], repo).trim().split(" ");
    expect(mergeParents).toEqual([mergeCommit, winner.reviewedMain, winner.featureTip]);
    expect(
      git(["rev-list", "--merges", `${winner.reviewedMain}..refs/heads/main`], repo).trim().split("\n"),
    ).toEqual([mergeCommit]);
    expect(gitOut(["merge-base", "--is-ancestor", winner.reviewedFeature, mergeCommit], repo).status).toBe(0);
    expect(gitOut(["merge-base", "--is-ancestor", winner.reviewedFeature, winner.featureTip], repo).status).toBe(0);
    expect(gitOut(["merge-base", "--is-ancestor", loser.featureTip, mergeCommit], repo).status).not.toBe(0);
    expect(git(["rev-parse", `refs/heads/feat/${loser.slug}`], repo).trim()).toBe(loser.featureTip);
    expect(readFileSync(loser.checkpoint, "utf8")).toBe(loser.checkpointContents);
    expect(readFileSync(join(loser.feature, "src", "approved.ts"), "utf8")).toBe(
      `${loser.slug} approved feature\n`,
    );
    expect(existsSync(winner.feature)).toBe(false);
    expect(existsSync(winner.checkpoint)).toBe(false);
    expectWorktrees(repo, [repo, loser.feature]);
    const loserRun = runs[features.indexOf(loser)]!;
    expect(`${loserRun.stdout}${loserRun.stderr}`).toContain(winner.reviewedMain);
    expect(`${loserRun.stdout}${loserRun.stderr}`).toContain(mergeCommit);
    const preparedCommits = readFileSync(barrierLog, "utf8").trim().split("\n");
    expect(preparedCommits).toHaveLength(2);
    expect(new Set(preparedCommits.map((line) => line.split("\t")[0])).size).toBe(2);
    expectNoMergeLock(repo);
    expect(loser.checkpointContents).not.toContain('"phase": "complete"');
  });

  test("U29a: a failed temporary merge commit hook aborts and cleans only the temporary worktree", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);
    const approved = prepareMergeFixture(repo, "merge-hook-failure");
    const mainBefore = git(["rev-parse", "refs/heads/main"], repo).trim();
    const hookLog = join(root, "failed-hook.log");
    installHook(
      repo,
      "pre-commit",
      [
        "printf '%s\\t%s\\t%s\\n' \"$PWD\" \"$(git rev-parse HEAD)\" \"$(git rev-parse MERGE_HEAD)\" > \"$AI_ENG_TEST_HOOK_LOG\"",
        "exit 19",
      ].join("\n"),
    );
    const primaryStatus = git(["status", "--porcelain", "--untracked-files=all"], repo);

    const run = runCli(["worktree", "merge", approved.slug], repo, {
      AI_ENG_TEST_HOOK_LOG: hookLog,
    });
    expect(existsSync(hookLog)).toBe(true);
    const [temporaryPath, temporaryHead, temporaryMergeHead] = readFileSync(hookLog, "utf8").trim().split("\t");

    expect(run.status).not.toBe(0);
    expect(temporaryPath).toBeDefined();
    expect(temporaryPath).not.toBe(repo);
    expect(temporaryHead).toBe(approved.reviewedMain);
    expect(temporaryMergeHead).toBe(approved.featureTip);
    expect(existsSync(temporaryPath!)).toBe(false);
    expect(git(["rev-parse", "refs/heads/main"], repo).trim()).toBe(mainBefore);
    expect(git(["rev-parse", "refs/heads/feat/merge-hook-failure"], repo).trim()).toBe(
      approved.featureTip,
    );
    expect(gitOut(["rev-parse", "--verify", "MERGE_HEAD"], repo).status).not.toBe(0);
    expect(git(["status", "--porcelain", "--untracked-files=all"], repo)).toBe(primaryStatus);
    expect(git(["status", "--porcelain", "--untracked-files=all"], approved.feature)).toBe("");
    expect(readFileSync(approved.checkpoint, "utf8")).toBe(approved.checkpointContents);
    expectWorktrees(repo, [repo, approved.feature]);
    expectNoMergeLock(repo);
    expect(approved.checkpointContents).not.toContain('"phase": "complete"');
  });

  test("U32a: a pre-commit hook cannot publish content staged outside the reviewed merge tree", () => {
    const repo = tempRepo();
    const root = defaultRoot(repo);
    cleanups.push(root);
    const approved = prepareMergeFixture(repo, "merge-hook-content");
    const mainBefore = git(["rev-parse", "refs/heads/main"], repo).trim();
    const hookLog = join(root, "staged-hook-content.log");
    const stagedLog = join(root, "staged-hook-paths.log");
    installHook(
      repo,
      "pre-commit",
      [
        "printf 'unreviewed hook content\\n' > hook-added.txt",
        "git add -- hook-added.txt",
        "printf '%s\\t%s\\t%s\\n' \"$PWD\" \"$(git rev-parse HEAD)\" \"$(git rev-parse MERGE_HEAD)\" > \"$AI_ENG_TEST_HOOK_LOG\"",
        "git diff --cached --name-only > \"$AI_ENG_TEST_STAGED_LOG\"",
      ].join("\n"),
    );
    const primaryStatus = git(["status", "--porcelain", "--untracked-files=all"], repo);
    const primaryTree = treeFiles(repo);
    const featureTree = treeFiles(approved.feature);

    const run = runCli(["worktree", "merge", approved.slug], repo, {
      AI_ENG_TEST_HOOK_LOG: hookLog,
      AI_ENG_TEST_STAGED_LOG: stagedLog,
    });
    const output = `${run.stdout}${run.stderr}`;
    expect(existsSync(hookLog)).toBe(true);
    expect(readFileSync(stagedLog, "utf8")).toContain("hook-added.txt");
    const [temporaryPath, temporaryHead, temporaryMergeHead] = readFileSync(hookLog, "utf8").trim().split("\t");

    expect(run.status).not.toBe(0);
    expect(output).toContain("merge tree");
    expect(temporaryPath).toBeDefined();
    expect(temporaryPath).not.toBe(repo);
    expect(temporaryHead).toBe(approved.reviewedMain);
    expect(temporaryMergeHead).toBe(approved.featureTip);
    expect(existsSync(temporaryPath!)).toBe(false);
    expect(git(["rev-parse", "refs/heads/main"], repo).trim()).toBe(mainBefore);
    expect(treeFiles(repo)).toEqual(primaryTree);
    expect(git(["status", "--porcelain", "--untracked-files=all"], repo)).toBe(primaryStatus);
    expect(git(["rev-parse", `refs/heads/feat/${approved.slug}`], repo).trim()).toBe(approved.featureTip);
    expect(git(["rev-parse", "HEAD"], approved.feature).trim()).toBe(approved.featureTip);
    expect(treeFiles(approved.feature)).toEqual(featureTree);
    expect(git(["status", "--porcelain", "--untracked-files=all"], approved.feature)).toBe("");
    expect(readFileSync(approved.checkpoint, "utf8")).toBe(approved.checkpointContents);
    expectWorktrees(repo, [repo, approved.feature]);
    expectNoMergeLock(repo);
    expect(approved.checkpointContents).not.toContain('"phase": "complete"');
  });

  test("U30: retry recognizes an already-published merge after refresh or safe removal is interrupted", () => {
    for (const interruption of ["refresh", "removal"] as const) {
      const repo = tempRepo();
      const root = defaultRoot(repo);
      cleanups.push(root);
      const approved = prepareMergeFixture(repo, `merge-retry-${interruption}`);
      if (interruption === "refresh") {
        const checkpointContents = JSON.parse(readFileSync(approved.checkpoint, "utf8"));
        writeFileSync(approved.checkpoint, `${JSON.stringify(checkpointContents, null, 4)}\n`);
        git(["add", `.ai-engineering/workflow/checkpoints/${approved.slug}.json`], approved.feature);
        git(["commit", "-q", "-m", "valid checkpoint-only review update"], approved.feature);
        approved.featureTip = git(["rev-parse", "HEAD"], approved.feature).trim();
        approved.checkpointContents = readFileSync(approved.checkpoint, "utf8");
      }
      const hookLog = join(root, "retry-hook.log");
      installHook(
        repo,
        "post-commit",
        [
          "printf '%s\\n' \"$(git rev-parse HEAD)\" >> \"$AI_ENG_TEST_HOOK_LOG\"",
          "if [ \"$AI_ENG_TEST_INTERRUPTION\" = refresh ]; then",
          "  printf 'interrupted primary\\n' > \"$AI_ENG_TEST_PRIMARY/README.md\"",
          "else",
          "  printf 'interrupted feature\\n' > \"$AI_ENG_TEST_FEATURE/interrupted.txt\"",
          "fi",
        ].join("\n"),
      );
      const primaryStatus = git(["status", "--porcelain", "--untracked-files=all"], repo);
      const hookEnv = {
        AI_ENG_TEST_HOOK_LOG: hookLog,
        AI_ENG_TEST_INTERRUPTION: interruption,
        AI_ENG_TEST_PRIMARY: repo,
        AI_ENG_TEST_FEATURE: approved.feature,
      };

      const firstAttempt = runCli(["worktree", "merge", approved.slug], repo, hookEnv);
      const publishedMerge = git(["rev-parse", "refs/heads/main"], repo).trim();
      expect(firstAttempt.status).not.toBe(0);
      expect(git(["rev-list", "--parents", "-n", "1", publishedMerge], repo).trim().split(" ")).toEqual([
        publishedMerge,
        approved.reviewedMain,
        approved.featureTip,
      ]);
      expect(git(["rev-parse", `refs/heads/feat/${approved.slug}`], repo).trim()).toBe(
        approved.featureTip,
      );
      expect(existsSync(approved.feature)).toBe(true);
      expect(readFileSync(approved.checkpoint, "utf8")).toBe(approved.checkpointContents);
      expect(approved.checkpointContents).not.toContain('"phase": "complete"');

      if (interruption === "refresh") {
        expect(readFileSync(join(repo, "README.md"), "utf8")).toBe("interrupted primary\n");
        expect(git(["status", "--porcelain", "--untracked-files=all"], repo)).toContain("README.md");
        writeFileSync(join(repo, "README.md"), "# fixture\n");
        expect(gitOut(["diff", "--quiet", approved.reviewedMain, "--"], repo).status).toBe(0);
        expect(existsSync(join(repo, "src", "approved.ts"))).toBe(false);
      } else {
        expect(readFileSync(join(approved.feature, "interrupted.txt"), "utf8")).toBe("interrupted feature\n");
        expect(git(["status", "--porcelain", "--untracked-files=all"], repo)).toBe(primaryStatus);
        rmSync(join(approved.feature, "interrupted.txt"));
        expect(git(["status", "--porcelain", "--untracked-files=all"], approved.feature)).toBe("");
        expect(readFileSync(join(repo, "src", "approved.ts"), "utf8")).toBe(
          `${approved.slug} approved feature\n`,
        );
      }

      const retry = runCli(["worktree", "merge", approved.slug], repo);

      expect(retry.status).toBe(0);
      expect(git(["rev-parse", "refs/heads/main"], repo).trim()).toBe(publishedMerge);
      expect(git(["rev-list", "--parents", "-n", "1", publishedMerge], repo).trim().split(" ")).toEqual([
        publishedMerge,
        approved.reviewedMain,
        approved.featureTip,
      ]);
      expect(gitOut(["merge-base", "--is-ancestor", approved.reviewedFeature, publishedMerge], repo).status).toBe(0);
      expect(git(["status", "--porcelain", "--untracked-files=all"], repo)).toBe(primaryStatus);
      expect(existsSync(approved.feature)).toBe(false);
      expect(existsSync(approved.checkpoint)).toBe(false);
      expectWorktrees(repo, [repo]);
      expect(readFileSync(hookLog, "utf8").trim().split("\n")).toHaveLength(1);
      expectNoMergeLock(repo);
    }
  }, 30_000);
});
