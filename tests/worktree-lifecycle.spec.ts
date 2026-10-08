import { afterAll, describe, expect, test } from "bun:test";
import { spawnSync } from "node:child_process";
import {
  existsSync,
  mkdirSync,
  mkdtempSync,
  readdirSync,
  readFileSync,
  realpathSync,
  rmSync,
  statSync,
  writeFileSync,
} from "node:fs";
import { dirname, join } from "node:path";

const CLI = join(import.meta.dir, "..", "src", "cli.ts");
const root = mkdtempSync(join(import.meta.dir, ".worktree-lifecycle-"));
const emptyGitConfig = join(root, "empty-gitconfig");
writeFileSync(emptyGitConfig, "");
const childEnv: NodeJS.ProcessEnv = {
  ...process.env,
  GIT_CONFIG_GLOBAL: emptyGitConfig,
  GIT_CONFIG_SYSTEM: emptyGitConfig,
  GIT_EDITOR: `"${process.execPath}" -e "process.exit(0)"`,
  GIT_TERMINAL_PROMPT: "0",
};

afterAll(() => rmSync(root, { recursive: true, force: true }));

interface Run {
  status: number;
  stdout: string;
  stderr: string;
}

function git(args: string[], cwd: string): string {
  const result = runGit(args, cwd);
  if (result.status !== 0) {
    throw new Error(`git ${args.join(" ")} failed in ${cwd}: ${result.stderr}`);
  }
  return result.stdout;
}

function runGit(args: string[], cwd: string): Run {
  const result = spawnSync("git", args, { cwd, encoding: "utf8", env: childEnv });
  return {
    status: result.status ?? 1,
    stdout: result.stdout ?? "",
    stderr: result.stderr ?? "",
  };
}

function runList(cwd: string): Run {
  const result = spawnSync(process.execPath, [CLI, "worktree", "list"], {
    cwd,
    encoding: "utf8",
    env: childEnv,
  });
  return {
    status: result.status ?? 1,
    stdout: result.stdout ?? "",
    stderr: result.stderr ?? "",
  };
}

function runWorktree(cwd: string, args: string[]): Run {
  const result = spawnSync(process.execPath, [CLI, "worktree", ...args], {
    cwd,
    encoding: "utf8",
    env: childEnv,
  });
  return {
    status: result.status ?? 1,
    stdout: result.stdout ?? "",
    stderr: result.stderr ?? "",
  };
}

function commitFile(worktree: string, relativePath: string, contents: string, message: string): string {
  const filePath = join(worktree, relativePath);
  mkdirSync(dirname(filePath), { recursive: true });
  writeFileSync(filePath, contents);
  git(["add", relativePath], worktree);
  git(["commit", "-q", "-m", message], worktree);
  return git(["rev-parse", "HEAD"], worktree).trim();
}

function pinRef(repo: string, name: string, source: string): string {
  const ref = `refs/test/worktree-lifecycle/${name}`;
  git(["update-ref", ref, source], repo);
  return ref;
}

function initRepo(): string {
  const base = mkdtempSync(join(root, "repo-"));
  const repo = join(base, "primary");
  mkdirSync(repo);
  git(["init", "-q", "-b", "main"], repo);
  git(["config", "user.name", "Ada Lovelace"], repo);
  git(["config", "user.email", "ada@example.com"], repo);
  git(["config", "commit.gpgsign", "false"], repo);
  mkdirSync(join(repo, "src"));
  writeFileSync(join(repo, "README.md"), "# fixture\n");
  writeFileSync(join(repo, "src", "shared.ts"), "export const value = 1;\n");
  git(["add", "-A"], repo);
  git(["commit", "-q", "-m", "fixture base"], repo);
  return repo;
}

function worktreePath(repo: string, name: string): string {
  return join(`${repo}.worktrees`, name);
}

function addBranchWorktree(repo: string, name: string, branch = `feat/${name}`): string {
  const path = worktreePath(repo, name);
  mkdirSync(dirname(path), { recursive: true });
  git(["worktree", "add", "--quiet", "-b", branch, path, "refs/heads/main"], repo);
  return path;
}

function addDetachedWorktree(repo: string, name: string): string {
  const path = worktreePath(repo, name);
  mkdirSync(dirname(path), { recursive: true });
  git(["worktree", "add", "--quiet", "--detach", path, "refs/heads/main"], repo);
  return path;
}

function addUnfetchedRemoteBranch(repo: string): string {
  const remote = join(root, "origin.git");
  git(["init", "--bare", "--quiet", remote], root);
  git(["remote", "add", "origin", remote], repo);
  git(["push", "--quiet", "origin", "refs/heads/main:refs/heads/main"], repo);
  git(["branch", "remote-only", "refs/heads/main"], repo);
  git(["push", "--quiet", "origin", "refs/heads/remote-only:refs/heads/remote-only"], repo);
  git(["branch", "-D", "remote-only"], repo);
  const remoteTrackingRefs = git(["for-each-ref", "--format=%(refname)", "refs/remotes/origin"], repo)
    .trim()
    .split("\n")
    .filter(Boolean);
  for (const ref of remoteTrackingRefs) git(["update-ref", "-d", ref], repo);
  return remote;
}

function checkpointPath(worktree: string, slug: string): string {
  return join(worktree, ".ai-engineering", "workflow", "checkpoints", `${slug}.json`);
}

function lifecycle(phase: string): object {
  return {
    phase,
    plan_approval: phase === "awaiting-plan-approval" ? "pending" : "approved",
    app_review: phase === "awaiting-app-review" ? "pending" : "not-started",
    reviewed_main: null,
  };
}

function checkpointPlan(slug: string, phase: string, files: string[] = [], status = "pending"): Record<string, unknown> {
  const gate = () => ({ status: "pending", attempts: 0, findings: [] });
  return {
    slug,
    checkpoints: [{
      id: 1,
      status,
      gates: { behavior: gate(), ui: gate(), review: gate() },
      files,
    }],
    lifecycle: lifecycle(phase),
  };
}

function mergeReadyPlan(
  slug: string,
  reviewedMain: string,
  reviewedFeature = reviewedMain,
): Record<string, unknown> {
  const gate = (status: string) => ({ status, attempts: 1, findings: [] });
  return {
    slug,
    checkpoints: [{
      id: 1,
      status: "passed",
      gates: { behavior: gate("passed"), ui: gate("passed"), review: gate("passed") },
      files: [],
    }],
    lifecycle: {
      phase: "ready-to-merge",
      plan_approval: "approved",
      app_review: "approved",
      reviewed_main: reviewedMain,
      reviewed_feature: reviewedFeature,
    },
  };
}

function ignoreLifecycleCheckpoints(repo: string): void {
  const exclude = join(repo, ".git", "info", "exclude");
  writeFileSync(exclude, "\n/.ai-engineering/workflow/checkpoints/*.json\n", { flag: "a" });
}

function writeCheckpoint(worktree: string, slug: string, value: object): string {
  const path = checkpointPath(worktree, slug);
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, `${JSON.stringify(value, null, 2)}\n`);
  return path;
}

function commitCheckpoint(worktree: string, path: string): void {
  git(["add", path], worktree);
  git(["commit", "-q", "-m", "add checkpoint"], worktree);
}

function repoSnapshot(repo: string, worktrees: string[], checkpointFiles: string[]): string {
  const contents = checkpointFiles.map((path) => {
    if (!existsSync(path)) return [path, "missing"];
    if (statSync(path).isDirectory()) return [path, "directory", ...readdirSync(path)];
    return [path, readFileSync(path, "utf8")];
  });
  return JSON.stringify({
    refs: git(["for-each-ref", "--format=%(refname) %(objectname)"], repo),
    registrations: git(["worktree", "list", "--porcelain"], repo),
    statuses: [repo, ...worktrees].map((path) => [
      realpathSync(path),
      git(["status", "--porcelain", "--untracked-files=all"], path),
    ]),
    contents,
  });
}

describe("ai-eng worktree lifecycle (checkpoint 2)", () => {
  test("U5: list uses only Git-listed feature worktrees and each worktree's own checkpoint path", () => {
    const repo = initRepo();
    const alpha = addBranchWorktree(repo, "alpha");
    const beta = addBranchWorktree(repo, "beta");

    writeCheckpoint(repo, "alpha", checkpointPlan("alpha", "primary-only"));
    writeCheckpoint(repo, "ghost", checkpointPlan("ghost", "not-listed"));
    writeCheckpoint(alpha, "alpha", checkpointPlan("alpha", "implementation"));
    writeCheckpoint(beta, "beta", checkpointPlan("beta", "awaiting-plan-approval"));

    const result = runList(repo);
    expect(result.status).toBe(0);
    expect(result.stdout).toContain("alpha");
    expect(result.stdout).toContain(realpathSync(alpha));
    expect(result.stdout).toContain("implementation");
    expect(result.stdout).toContain("beta");
    expect(result.stdout).toContain(realpathSync(beta));
    expect(result.stdout).toContain("awaiting-plan-approval");
    expect(result.stdout).not.toContain("primary-only");
    expect(result.stdout).not.toContain("not-listed");
    expect(result.stdout).not.toContain("ghost");
  });

  test("U6: clean, dirty, detached and unclassified Git worktrees report their status and evidence read-only", () => {
    const repo = initRepo();
    const clean = addBranchWorktree(repo, "alpha");
    const dirty = addBranchWorktree(repo, "beta");
    const detached = addDetachedWorktree(repo, "gamma");
    const unclassified = addBranchWorktree(repo, "delta", "topic/other");
    writeFileSync(join(dirty, "README.md"), "# local edit\n");

    expect(git(["status", "--porcelain", "--untracked-files=all"], clean)).toBe("");
    expect(git(["status", "--porcelain", "--untracked-files=all"], dirty)).toContain("README.md");
    expect(git(["worktree", "list", "--porcelain"], repo)).toContain("detached");
    expect(git(["worktree", "list", "--porcelain"], repo)).toContain("refs/heads/topic/other");

    const before = repoSnapshot(repo, [clean, dirty, detached, unclassified], []);
    const result = runList(repo);
    const after = repoSnapshot(repo, [clean, dirty, detached, unclassified], []);

    expect(result.status).toBe(0);
    expect(result.stdout).toContain(realpathSync(clean));
    expect(result.stdout.toLowerCase()).toContain("clean");
    expect(result.stdout).toContain(realpathSync(dirty));
    expect(result.stdout.toLowerCase()).toContain("dirty");
    expect(result.stdout).toContain("README.md");
    expect(result.stdout).toContain(realpathSync(detached));
    expect(result.stdout.toLowerCase()).toContain("detached");
    expect(result.stdout).toContain(realpathSync(unclassified));
    expect(result.stdout).toContain("topic/other");
    expect(result.stdout.toLowerCase()).toContain("unclassified");
    expect(after).toBe(before);
  });

  test("U7: missing, unreadable, malformed and legacy lifecycle state stays visible as unknown", () => {
    const repo = initRepo();
    const missing = addBranchWorktree(repo, "missing");
    const unreadable = addBranchWorktree(repo, "unreadable");
    const malformed = addBranchWorktree(repo, "malformed");
    const legacy = addBranchWorktree(repo, "legacy");
    const contradictory = addBranchWorktree(repo, "contradictory");

    const unreadablePath = checkpointPath(unreadable, "unreadable");
    mkdirSync(unreadablePath, { recursive: true });
    const malformedPath = writeCheckpoint(malformed, "malformed", {
      lifecycle: { phase: "ready-to-merge", plan_approval: "approved", app_review: "approved", reviewed_main: "not-a-commit" },
    });
    writeFileSync(malformedPath, "{ invalid json\n");
    const legacyPlan = checkpointPlan("legacy", "implementation");
    delete legacyPlan.lifecycle;
    writeCheckpoint(legacy, "legacy", legacyPlan);
    writeCheckpoint(contradictory, "contradictory", checkpointPlan("contradictory", "implementation", [], "passed"));

    const result = runList(repo);
    expect(result.status).toBe(0);
    for (const { slug, path } of [
      { slug: "missing", path: missing },
      { slug: "unreadable", path: unreadable },
      { slug: "malformed", path: malformed },
      { slug: "legacy", path: legacy },
      { slug: "contradictory", path: contradictory },
    ]) {
      expect(result.stdout).toContain(slug);
      expect(result.stdout).toContain(realpathSync(path));
    }
    expect(result.stdout.toLowerCase()).toContain("unknown");
    expect(result.stdout).toContain("unknown (contradictory lifecycle)");
    expect(result.stdout.match(/unknown/gi)?.length ?? 0).toBeGreaterThanOrEqual(5);
    expect(result.stdout).not.toContain("ready-to-merge");
    expect(result.stdout).not.toContain("approved");
  });

  test("U9: likely-overlap evidence names Git status and each relevant checkpoint path without mutation", () => {
    const repo = initRepo();
    const alpha = addBranchWorktree(repo, "alpha");
    const beta = addBranchWorktree(repo, "beta");
    const plan = (slug: string) => checkpointPlan(slug, "implementation", ["src/shared.ts"]);
    const alphaCheckpoint = writeCheckpoint(alpha, "alpha", plan("alpha"));
    const betaCheckpoint = writeCheckpoint(beta, "beta", plan("beta"));
    commitCheckpoint(alpha, alphaCheckpoint);
    commitCheckpoint(beta, betaCheckpoint);
    writeFileSync(join(alpha, "src", "shared.ts"), "export const value = 2;\n");

    expect(git(["status", "--porcelain", "--untracked-files=all"], alpha)).toContain("src/shared.ts");
    const before = repoSnapshot(repo, [alpha, beta], [alphaCheckpoint, betaCheckpoint]);
    const result = runList(repo);
    const after = repoSnapshot(repo, [alpha, beta], [alphaCheckpoint, betaCheckpoint]);

    expect(result.status).toBe(0);
    expect(result.stdout.toLowerCase()).toContain("overlap");
    expect(result.stdout).toContain("src/shared.ts");
    expect(result.stdout).toContain(alphaCheckpoint);
    expect(result.stdout).toContain(betaCheckpoint);
    expect(after).toBe(before);
  });

  test("U15: listing preserves dirty and uncertain work without resetting, removing or fetching", () => {
    const repo = initRepo();
    const remote = addUnfetchedRemoteBranch(repo);
    const dirty = addBranchWorktree(repo, "dirty");
    const missing = addBranchWorktree(repo, "missing");
    const uncertain = addBranchWorktree(repo, "uncertain");
    const dirtyFile = join(dirty, "README.md");
    const missingCheckpoint = checkpointPath(missing, "missing");
    const uncertainCheckpoint = writeCheckpoint(uncertain, "uncertain", checkpointPlan("uncertain", "implementation"));
    const originalDirtyContents = "# uncommitted user work\n";

    writeFileSync(dirtyFile, originalDirtyContents);
    writeFileSync(uncertainCheckpoint, "{ malformed checkpoint\n");

    expect(git(["--git-dir", remote, "for-each-ref", "--format=%(refname)"], repo)).toContain(
      "refs/heads/remote-only",
    );
    expect(git(["for-each-ref", "--format=%(refname)", "refs/remotes"], repo)).toBe("");

    const before = repoSnapshot(repo, [dirty, missing, uncertain], [missingCheckpoint, uncertainCheckpoint]);
    const result = runList(repo);
    const after = repoSnapshot(repo, [dirty, missing, uncertain], [missingCheckpoint, uncertainCheckpoint]);

    expect(result.status).toBe(0);
    expect(result.stdout).toContain(realpathSync(dirty));
    expect(result.stdout.toLowerCase()).toContain("dirty");
    expect(result.stdout).toContain("README.md");
    expect(result.stdout).toContain(realpathSync(missing));
    expect(result.stdout).toContain(realpathSync(uncertain));
    expect(result.stdout.toLowerCase()).toContain("unknown");
    expect(readFileSync(dirtyFile, "utf8")).toBe(originalDirtyContents);
    expect(after).toBe(before);
    expect(git(["for-each-ref", "--format=%(refname)", "refs/remotes"], repo)).toBe("");
  });
});

describe("ai-eng worktree lifecycle (checkpoint 5)", () => {
  test("U20: a clean feature worktree rebases onto the exact current local main commit", () => {
    const repo = initRepo();
    const feature = addBranchWorktree(repo, "sync-clean");
    const base = git(["rev-parse", "refs/heads/main"], repo).trim();
    const baseRef = pinRef(repo, "clean-base", base);
    const featureBefore = commitFile(feature, "src/feature.ts", "export const feature = true;\n", "feature change");
    const featureBeforeRef = pinRef(repo, "clean-feature-before", featureBefore);
    const localMain = commitFile(repo, "src/main.ts", "export const main = true;\n", "advance local main");
    const localMainRef = pinRef(repo, "clean-local-main", localMain);

    git(["branch", "remote-fixture", base], repo);
    git(["switch", "remote-fixture"], repo);
    const remoteTip = commitFile(repo, "src/remote.ts", "export const remote = true;\n", "advance remote fixture");
    git(["switch", "main"], repo);
    git(["update-ref", "refs/remotes/origin/main", remoteTip], repo);
    const remoteRef = pinRef(repo, "clean-remote-main", "refs/remotes/origin/main");
    git(["branch", "-D", "remote-fixture"], repo);

    expect(git(["rev-parse", baseRef], repo).trim()).toBe(base);
    expect(git(["rev-parse", featureBeforeRef], repo).trim()).toBe(featureBefore);
    expect(git(["rev-parse", localMainRef], repo).trim()).toBe(localMain);
    expect(git(["rev-parse", remoteRef], repo).trim()).toBe(remoteTip);
    expect(git(["rev-list", "--parents", "-n", "1", localMain], repo).trim().split(" ")).toEqual([
      localMain,
      base,
    ]);
    expect(git(["rev-list", "--parents", "-n", "1", remoteTip], repo).trim().split(" ")).toEqual([
      remoteTip,
      base,
    ]);

    const rebase = runGit(["rebase", "refs/heads/main"], feature);
    expect(rebase.status).toBe(0);

    const rebasedFeature = git(["rev-parse", "refs/heads/feat/sync-clean"], repo).trim();
    expect(git(["rev-list", "--parents", "-n", "1", rebasedFeature], repo).trim().split(" ")).toEqual([
      rebasedFeature,
      localMain,
    ]);
    expect(runGit(["merge-base", "--is-ancestor", remoteTip, rebasedFeature], repo).status).not.toBe(0);
    expect(git(["rev-parse", baseRef], repo).trim()).toBe(base);
    expect(git(["rev-parse", featureBeforeRef], repo).trim()).toBe(featureBefore);
    expect(git(["rev-parse", localMainRef], repo).trim()).toBe(localMain);
    expect(git(["rev-parse", remoteRef], repo).trim()).toBe(remoteTip);
    expect(git(["status", "--porcelain", "--untracked-files=all"], feature)).toBe("");
  });

  test("U21: a clear rebase conflict is resolved in the feature worktree and checked after sync", () => {
    const repo = initRepo();
    const feature = addBranchWorktree(repo, "sync-conflict");
    const featureContents = "export const value = 'feature';\n";
    const mainContents = "export const value = 'main';\n";
    const resolvedContents = "export const value = 'feature and main';\n";
    const featureCommit = commitFile(feature, "src/shared.ts", featureContents, "feature edit");
    const featureRef = pinRef(repo, "conflict-feature-before", featureCommit);
    const localMain = commitFile(repo, "src/shared.ts", mainContents, "main edit");
    const mainRef = pinRef(repo, "conflict-local-main", localMain);

    const rebase = runGit(["rebase", "refs/heads/main"], feature);
    expect(rebase.status).not.toBe(0);
    expect(git(["status", "--porcelain", "--untracked-files=all"], feature)).toContain("src/shared.ts");
    expect(git(["rev-parse", "--show-toplevel"], feature).trim()).toBe(realpathSync(feature));
    expect(readFileSync(join(feature, "src", "shared.ts"), "utf8")).not.toBe(mainContents);
    expect(readFileSync(join(repo, "src", "shared.ts"), "utf8")).toBe(mainContents);

    writeFileSync(join(feature, "src", "shared.ts"), resolvedContents);
    git(["add", "src/shared.ts"], feature);
    const continued = runGit(["rebase", "--continue"], feature);
    expect(continued.status).toBe(0);

    const rebasedFeature = git(["rev-parse", "HEAD"], feature).trim();
    expect(git(["rev-list", "--parents", "-n", "1", rebasedFeature], repo).trim().split(" ")).toEqual([
      rebasedFeature,
      localMain,
    ]);
    expect(git(["rev-parse", featureRef], repo).trim()).toBe(featureCommit);
    expect(git(["rev-parse", mainRef], repo).trim()).toBe(localMain);
    expect(readFileSync(join(feature, "src", "shared.ts"), "utf8")).toBe(resolvedContents);
    expect(readFileSync(join(repo, "src", "shared.ts"), "utf8")).toBe(mainContents);
    expect(runGit(["diff", "--check", `${featureRef}..${rebasedFeature}`], feature).status).toBe(0);
    expect(git(["status", "--porcelain", "--untracked-files=all"], feature)).toBe("");
  });

  test("U22: dirty preconditions refuse before rebase and preserve branch, worktree and edits", () => {
    const repo = initRepo();
    const feature = addBranchWorktree(repo, "sync-dirty");
    const checkpoint = writeCheckpoint(feature, "sync-dirty", checkpointPlan("sync-dirty", "implementation"));
    commitCheckpoint(feature, checkpoint);
    const checkpointContents = readFileSync(checkpoint, "utf8");
    const mainContents = "# main edit\n";
    const localMain = commitFile(repo, "README.md", mainContents, "advance local main");
    const dirtyContents = "# uncommitted feature edit\n";
    writeFileSync(join(feature, "README.md"), dirtyContents);
    const featureBefore = git(["rev-parse", "HEAD"], feature).trim();
    const before = repoSnapshot(repo, [feature], [checkpoint]);

    const rebase = runGit(["rebase", "refs/heads/main"], feature);

    expect(rebase.status).not.toBe(0);
    expect(readFileSync(checkpoint, "utf8")).toBe(checkpointContents);
    expect(git(["rev-parse", "HEAD"], feature).trim()).toBe(featureBefore);
    expect(git(["rev-parse", "refs/heads/main"], repo).trim()).toBe(localMain);
    expect(readFileSync(join(feature, "README.md"), "utf8")).toBe(dirtyContents);
    expect(repoSnapshot(repo, [feature], [checkpoint])).toBe(before);
    expect(git(["status", "--porcelain", "--untracked-files=all"], feature)).toContain("README.md");
    expect(git(["status", "--porcelain", "--untracked-files=all"], feature)).not.toContain("rebase");
  });

  test("U22: missing, unreadable and malformed lifecycle state refuses sync without mutation", () => {
    const repo = initRepo();
    const missing = addBranchWorktree(repo, "sync-missing-state");
    const malformed = addBranchWorktree(repo, "sync-malformed-state");
    const unreadable = addBranchWorktree(repo, "sync-unreadable-state");
    const missingCheckpoint = checkpointPath(missing, "sync-missing-state");
    const malformedCheckpoint = checkpointPath(malformed, "sync-malformed-state");
    const unreadableCheckpoint = checkpointPath(unreadable, "sync-unreadable-state");
    const malformedBytes = "{ malformed lifecycle checkpoint\n";

    mkdirSync(dirname(malformedCheckpoint), { recursive: true });
    writeFileSync(malformedCheckpoint, malformedBytes);
    git(["add", malformedCheckpoint], malformed);
    git(["commit", "-q", "-m", "add malformed checkpoint"], malformed);
    mkdirSync(unreadableCheckpoint, { recursive: true });
    commitFile(repo, "src/main.ts", "export const main = true;\n", "advance local main");

    expect(existsSync(missingCheckpoint)).toBe(false);
    expect(readFileSync(malformedCheckpoint, "utf8")).toBe(malformedBytes);
    expect(statSync(unreadableCheckpoint).isDirectory()).toBe(true);

    const checkpoints = [missingCheckpoint, malformedCheckpoint, unreadableCheckpoint];
    const before = repoSnapshot(repo, [missing, malformed, unreadable], checkpoints);
    const listing = runList(repo);

    expect(listing.status).toBe(0);
    for (const { slug, path } of [
      { slug: "sync-missing-state", path: missing },
      { slug: "sync-malformed-state", path: malformed },
      { slug: "sync-unreadable-state", path: unreadable },
    ]) {
      expect(listing.stdout).toContain(slug);
      expect(listing.stdout).toContain(realpathSync(path));
    }
    expect(listing.stdout.match(/unknown/gi)?.length ?? 0).toBeGreaterThanOrEqual(3);
    expect(existsSync(missingCheckpoint)).toBe(false);
    expect(readFileSync(malformedCheckpoint, "utf8")).toBe(malformedBytes);
    expect(statSync(unreadableCheckpoint).isDirectory()).toBe(true);
    expect(repoSnapshot(repo, [missing, malformed, unreadable], checkpoints)).toBe(before);
  });

  test("U22: unresolved conflicts abort before checkpoint updates and preserve original refs, status and content", () => {
    const repo = initRepo();
    const feature = addBranchWorktree(repo, "sync-abort");
    const blockedCheckpoint = writeCheckpoint(feature, "sync-abort", checkpointPlan("sync-abort", "implementation"));
    commitCheckpoint(feature, blockedCheckpoint);
    const originalCheckpointContents = readFileSync(blockedCheckpoint, "utf8");
    const originalFeatureContents = "export const value = 'feature';\n";
    const featureCommit = commitFile(feature, "src/shared.ts", originalFeatureContents, "feature edit");
    const originalFeatureTree = git(["rev-parse", `${featureCommit}^{tree}`], feature).trim();
    const featureRef = pinRef(repo, "abort-feature-before", featureCommit);
    const mainContents = "export const value = 'main';\n";
    const localMain = commitFile(repo, "src/shared.ts", mainContents, "main edit");
    const mainRef = pinRef(repo, "abort-local-main", localMain);

    const before = repoSnapshot(repo, [feature], [blockedCheckpoint]);
    expect(runGit(["rebase", "refs/heads/main"], feature).status).not.toBe(0);
    expect(git(["status", "--porcelain", "--untracked-files=all"], feature)).toContain("src/shared.ts");
    expect(readFileSync(blockedCheckpoint, "utf8")).toBe(originalCheckpointContents);
    expect(runGit(["rebase", "--abort"], feature).status).toBe(0);
    expect(repoSnapshot(repo, [feature], [blockedCheckpoint])).toBe(before);
    expect(git(["rev-parse", "HEAD"], feature).trim()).toBe(featureCommit);
    expect(git(["rev-parse", "HEAD^{tree}"], feature).trim()).toBe(originalFeatureTree);
    expect(git(["branch", "--show-current"], feature).trim()).toBe("feat/sync-abort");
    expect(git(["rev-parse", featureRef], repo).trim()).toBe(featureCommit);
    expect(git(["rev-parse", mainRef], repo).trim()).toBe(localMain);
    expect(git(["status", "--porcelain", "--untracked-files=all"], feature)).toBe("");
    expect(readFileSync(join(feature, "src", "shared.ts"), "utf8")).toBe(originalFeatureContents);
    expect(git(["worktree", "list", "--porcelain"], repo)).toContain(realpathSync(feature));
    writeCheckpoint(feature, "sync-abort", checkpointPlan("sync-abort", "blocked"));
    const abortedPlan = JSON.parse(readFileSync(blockedCheckpoint, "utf8")) as {
      lifecycle: {
        phase: string;
        plan_approval: string;
        app_review: string;
        reviewed_main: string | null;
      };
    };
    expect(abortedPlan.lifecycle).toEqual({
      phase: "blocked",
      plan_approval: "approved",
      app_review: "not-started",
      reviewed_main: null,
    });

    const failedGate = addBranchWorktree(repo, "sync-failed-gate");
    const initialPlan = checkpointPlan("sync-failed-gate", "implementation");
    const checkpoint = writeCheckpoint(failedGate, "sync-failed-gate", initialPlan);
    commitCheckpoint(failedGate, checkpoint);
    const originalFeatureContentsWithTrailingSpace = "export const value = 'feature'; \n";
    const originalFeature = commitFile(failedGate, "src/shared.ts", originalFeatureContentsWithTrailingSpace, "feature with failed check");
    const failedGateFeatureTree = git(["rev-parse", `${originalFeature}^{tree}`], failedGate).trim();
    const originalFeatureRef = pinRef(repo, "failed-gate-feature-before", originalFeature);
    const mainContentsForFailedGate = "export const value = 'main for failed gate';\n";
    const advancedMain = commitFile(repo, "src/shared.ts", mainContentsForFailedGate, "advance main");
    const failedGateMainRef = pinRef(repo, "failed-gate-local-main", advancedMain);
    const originalFailedGateCheckpoint = readFileSync(checkpoint, "utf8");
    const failedGateBefore = repoSnapshot(repo, [failedGate], [checkpoint]);

    expect(runGit(["rebase", "refs/heads/main"], failedGate).status).not.toBe(0);
    expect(git(["status", "--porcelain", "--untracked-files=all"], failedGate)).toContain("src/shared.ts");
    const failedResolutionContents = "export const value = 'resolved'; \n";
    writeFileSync(join(failedGate, "src", "shared.ts"), failedResolutionContents);
    git(["add", "src/shared.ts"], failedGate);
    expect(runGit(["diff", "--cached", "--check"], failedGate).status).not.toBe(0);
    expect(readFileSync(checkpoint, "utf8")).toBe(originalFailedGateCheckpoint);
    expect(runGit(["rebase", "--abort"], failedGate).status).toBe(0);
    expect(repoSnapshot(repo, [failedGate], [checkpoint])).toBe(failedGateBefore);
    expect(git(["rev-parse", "HEAD"], failedGate).trim()).toBe(originalFeature);
    expect(git(["rev-parse", "HEAD^{tree}"], failedGate).trim()).toBe(failedGateFeatureTree);
    expect(git(["branch", "--show-current"], failedGate).trim()).toBe("feat/sync-failed-gate");
    expect(git(["rev-parse", originalFeatureRef], repo).trim()).toBe(originalFeature);
    expect(git(["rev-parse", failedGateMainRef], repo).trim()).toBe(advancedMain);
    expect(git(["rev-parse", "refs/heads/main"], repo).trim()).toBe(advancedMain);
    expect(git(["status", "--porcelain", "--untracked-files=all"], failedGate)).toBe("");
    expect(readFileSync(join(failedGate, "src", "shared.ts"), "utf8")).toBe(originalFeatureContentsWithTrailingSpace);
    expect(readFileSync(join(repo, "src", "shared.ts"), "utf8")).toBe(mainContentsForFailedGate);
    expect(readFileSync(checkpoint, "utf8")).toBe(originalFailedGateCheckpoint);
    expect(git(["worktree", "list", "--porcelain"], repo)).toContain(realpathSync(failedGate));

    const blockedPlan = checkpointPlan("sync-failed-gate", "blocked");
    writeCheckpoint(failedGate, "sync-failed-gate", blockedPlan);
    const storedPlan = JSON.parse(readFileSync(checkpoint, "utf8")) as {
      lifecycle: { phase: string; plan_approval: string; app_review: string; reviewed_main: string | null };
    };

    expect(git(["rev-parse", "HEAD"], failedGate).trim()).toBe(originalFeature);
    expect(storedPlan.lifecycle).toEqual({ phase: "blocked", plan_approval: "approved", app_review: "not-started", reviewed_main: null });
  });

  test("U23: awaiting app review records the exact local main only after sync gates pass", () => {
    const repo = initRepo();
    const feature = addBranchWorktree(repo, "sync-review");
    const featureCommit = commitFile(feature, "src/feature.ts", "export const feature = true;\n", "feature change");
    const localMain = commitFile(repo, "src/main.ts", "export const main = true;\n", "advance local main");
    const featureRef = pinRef(repo, "review-feature-before", featureCommit);
    const initialPlan = checkpointPlan("sync-review", "implementation", [], "passed");
    const checkpoint = writeCheckpoint(feature, "sync-review", initialPlan);
    commitCheckpoint(feature, checkpoint);

    expect(runGit(["rebase", "refs/heads/main"], feature).status).toBe(0);
    const beforeGates = JSON.parse(readFileSync(checkpoint, "utf8")) as {
      lifecycle: {
        phase: string;
        plan_approval: string;
        app_review: string;
        reviewed_main: string | null;
      };
    };
    expect(beforeGates.lifecycle).toEqual({
      phase: "implementation",
      plan_approval: "approved",
      app_review: "not-started",
      reviewed_main: null,
    });
    expect(runGit(["diff", "--check", `${featureRef}..HEAD`], feature).status).toBe(0);
    expect(runGit(["merge-base", "--is-ancestor", localMain, "HEAD"], feature).status).toBe(0);
    const replayedCommits = git(["rev-list", "--reverse", `${localMain}..HEAD`], feature).trim().split("\n");
    expect(git(["rev-list", "--parents", "-n", "1", replayedCommits[0]!], feature).trim().split(" ")[1]).toBe(
      localMain,
    );

    const reviewedPlan = checkpointPlan("sync-review", "awaiting-app-review", [], "passed");
    reviewedPlan.lifecycle = {
      phase: "awaiting-app-review",
      plan_approval: "approved",
      app_review: "pending",
      reviewed_main: git(["rev-parse", "refs/heads/main"], repo).trim(),
    };
    writeCheckpoint(feature, "sync-review", reviewedPlan);
    const storedPlan = JSON.parse(readFileSync(checkpoint, "utf8")) as {
      lifecycle: {
        phase: string;
        plan_approval: string;
        app_review: string;
        reviewed_main: string | null;
      };
    };

    expect(storedPlan.lifecycle).toEqual({
      phase: "awaiting-app-review",
      plan_approval: "approved",
      app_review: "pending",
      reviewed_main: localMain,
    });
    expect(git(["rev-parse", "refs/heads/main"], repo).trim()).toBe(localMain);
  });
});

describe("ai-eng worktree lifecycle (checkpoint 6)", () => {
  test("U24: native merge state refuses a competing merge without committing or removing either feature", () => {
    const repo = initRepo();
    const approved = addBranchWorktree(repo, "merge-approved");
    const sibling = addBranchWorktree(repo, "merge-sibling");
    const reviewedMain = git(["rev-parse", "refs/heads/main"], repo).trim();
    const approvedFile = "approved feature data\n";
    const siblingFile = "unapproved sibling data\n";
    const approvedCommit = commitFile(approved, "src/approved.ts", approvedFile, "approved feature");
    const siblingCommit = commitFile(sibling, "src/sibling.ts", siblingFile, "unapproved sibling");
    const approvedCheckpoint = writeCheckpoint(
      approved,
      "merge-approved",
      mergeReadyPlan("merge-approved", reviewedMain),
    );
    const siblingCheckpoint = writeCheckpoint(
      sibling,
      "merge-sibling",
      checkpointPlan("merge-sibling", "implementation"),
    );
    commitCheckpoint(approved, approvedCheckpoint);
    commitCheckpoint(sibling, siblingCheckpoint);
    const approvedTip = git(["rev-parse", "refs/heads/feat/merge-approved"], repo).trim();
    const siblingTip = git(["rev-parse", "refs/heads/feat/merge-sibling"], repo).trim();

    expect(git(["branch", "--show-current"], repo).trim()).toBe("main");
    expect(git(["rev-parse", "refs/heads/main"], repo).trim()).toBe(reviewedMain);
    expect(git(["remote"], repo)).toBe("");
    expect(git(["for-each-ref", "--format=%(refname)", "refs/remotes"], repo)).toBe("");
    expect(git(["branch", "--show-current"], approved).trim()).toBe("feat/merge-approved");
    expect(git(["branch", "--show-current"], sibling).trim()).toBe("feat/merge-sibling");
    expect(runGit(["merge-base", "--is-ancestor", reviewedMain, approvedTip], repo).status).toBe(0);
    expect(runGit(["merge-base", "--is-ancestor", reviewedMain, siblingTip], repo).status).toBe(0);
    expect(runGit(["merge-base", "--is-ancestor", approvedCommit, approvedTip], repo).status).toBe(0);
    expect(runGit(["merge-base", "--is-ancestor", siblingCommit, siblingTip], repo).status).toBe(0);

    const firstMerge = runGit(["merge", "--no-commit", "--no-ff", "refs/heads/feat/merge-approved"], repo);
    expect(firstMerge.status).toBe(0);
    const mergeHeadPath = join(repo, ".git", "MERGE_HEAD");
    expect(readFileSync(mergeHeadPath, "utf8").trim()).toBe(approvedTip);
    const indexBeforeRetry = git(["ls-files", "--stage"], repo);
    const statusBeforeRetry = git(["status", "--porcelain", "--untracked-files=all"], repo);
    const registrationsBeforeRetry = git(["worktree", "list", "--porcelain"], repo);
    const refsBeforeRetry = git(["for-each-ref", "--format=%(refname) %(objectname)"], repo);

    const competingMerge = runGit(["merge", "--no-ff", "refs/heads/feat/merge-sibling"], repo);

    expect(competingMerge.status).not.toBe(0);
    expect(git(["rev-parse", "HEAD"], repo).trim()).toBe(reviewedMain);
    expect(git(["rev-parse", "refs/heads/main"], repo).trim()).toBe(reviewedMain);
    expect(readFileSync(mergeHeadPath, "utf8").trim()).toBe(approvedTip);
    expect(git(["ls-files", "--stage"], repo)).toBe(indexBeforeRetry);
    expect(git(["status", "--porcelain", "--untracked-files=all"], repo)).toBe(statusBeforeRetry);
    expect(git(["worktree", "list", "--porcelain"], repo)).toBe(registrationsBeforeRetry);
    expect(git(["for-each-ref", "--format=%(refname) %(objectname)"], repo)).toBe(refsBeforeRetry);
    expect(git(["rev-parse", "refs/heads/feat/merge-sibling"], repo).trim()).toBe(siblingTip);
    expect(readFileSync(join(approved, "src", "approved.ts"), "utf8")).toBe(approvedFile);
    expect(readFileSync(join(sibling, "src", "sibling.ts"), "utf8")).toBe(siblingFile);
    expect(readFileSync(approvedCheckpoint, "utf8")).toContain(reviewedMain);
    expect(readFileSync(siblingCheckpoint, "utf8")).toContain('"phase": "implementation"');
  });

  test("U25: a stale approved merge is aborted while retaining the advanced main and feature checkpoint", () => {
    const repo = initRepo();
    const feature = addBranchWorktree(repo, "merge-stale");
    const reviewedMain = git(["rev-parse", "refs/heads/main"], repo).trim();
    const featureContents = "preserved feature data\n";
    const featureCommit = commitFile(feature, "src/feature.ts", featureContents, "feature change");
    const checkpoint = writeCheckpoint(
      feature,
      "merge-stale",
      mergeReadyPlan("merge-stale", reviewedMain),
    );
    commitCheckpoint(feature, checkpoint);
    const approvedCheckpoint = readFileSync(checkpoint, "utf8");
    const featureTip = git(["rev-parse", "refs/heads/feat/merge-stale"], repo).trim();
    const featureRef = pinRef(repo, "stale-feature-before-merge", featureTip);
    expect(runGit(["merge-base", "--is-ancestor", featureCommit, featureTip], repo).status).toBe(0);
    expect(git(["remote"], repo)).toBe("");

    const mainAdvance = addBranchWorktree(repo, "merge-main-advance", "topic/main-advance");
    const advancedMain = commitFile(
      mainAdvance,
      "src/main-after-review.ts",
      "main advanced after approval\n",
      "advance main",
    );
    git(["worktree", "remove", mainAdvance], repo);
    expect(runGit(["merge-base", "--is-ancestor", reviewedMain, advancedMain], repo).status).toBe(0);
    expect(git(["rev-parse", "refs/heads/main"], repo).trim()).toBe(reviewedMain);
    expect(git(["branch", "--show-current"], feature).trim()).toBe("feat/merge-stale");

    const pendingMerge = runGit(["merge", "--no-commit", "--no-ff", "refs/heads/feat/merge-stale"], repo);
    expect(pendingMerge.status).toBe(0);
    expect(readFileSync(join(repo, ".git", "MERGE_HEAD"), "utf8").trim()).toBe(featureTip);
    git(["update-ref", "refs/heads/main", advancedMain], repo);
    expect(git(["rev-parse", "refs/heads/main"], repo).trim()).not.toBe(reviewedMain);

    const abort = runGit(["merge", "--abort"], repo);

    expect(abort.status).toBe(0);
    expect(runGit(["rev-parse", "--verify", "MERGE_HEAD"], repo).status).not.toBe(0);
    expect(git(["rev-parse", "HEAD"], repo).trim()).toBe(advancedMain);
    expect(git(["rev-parse", "refs/heads/main"], repo).trim()).toBe(advancedMain);
    expect(git(["status", "--porcelain", "--untracked-files=all"], repo)).toBe("");
    expect(git(["rev-parse", "refs/heads/feat/merge-stale"], repo).trim()).toBe(featureTip);
    expect(git(["rev-parse", featureRef], repo).trim()).toBe(featureTip);
    expect(git(["status", "--porcelain", "--untracked-files=all"], feature)).toBe("");
    expect(git(["worktree", "list", "--porcelain"], repo)).toContain(realpathSync(feature));
    expect(readFileSync(checkpoint, "utf8")).toBe(approvedCheckpoint);
    expect(readFileSync(join(feature, "src", "feature.ts"), "utf8")).toBe(featureContents);

    const invalidatedPlan = checkpointPlan("merge-stale", "blocked");
    writeCheckpoint(feature, "merge-stale", invalidatedPlan);
    expect(JSON.parse(readFileSync(checkpoint, "utf8")).lifecycle).toEqual({
      phase: "blocked",
      plan_approval: "approved",
      app_review: "not-started",
      reviewed_main: null,
    });
  });

  test("U26: only the approved feature gets a no-fast-forward merge, verified before safe removal", () => {
    const repo = initRepo();
    const approved = addBranchWorktree(repo, "merge-only-approved");
    const sibling = addBranchWorktree(repo, "merge-only-sibling");
    const reviewedMain = git(["rev-parse", "refs/heads/main"], repo).trim();
    const approvedCommit = commitFile(approved, "src/approved.ts", "approved only\n", "approved feature");
    const siblingCommit = commitFile(sibling, "src/sibling.ts", "sibling remains\n", "unapproved sibling");
    const approvedCheckpoint = writeCheckpoint(
      approved,
      "merge-only-approved",
      mergeReadyPlan("merge-only-approved", reviewedMain),
    );
    const siblingCheckpoint = writeCheckpoint(
      sibling,
      "merge-only-sibling",
      checkpointPlan("merge-only-sibling", "implementation"),
    );
    commitCheckpoint(approved, approvedCheckpoint);
    commitCheckpoint(sibling, siblingCheckpoint);
    const approvedTip = git(["rev-parse", "refs/heads/feat/merge-only-approved"], repo).trim();
    const siblingTip = git(["rev-parse", "refs/heads/feat/merge-only-sibling"], repo).trim();

    expect(git(["branch", "--show-current"], repo).trim()).toBe("main");
    expect(git(["rev-parse", "refs/heads/main"], repo).trim()).toBe(reviewedMain);
    expect(git(["branch", "--show-current"], approved).trim()).toBe("feat/merge-only-approved");
    expect(git(["branch", "--show-current"], sibling).trim()).toBe("feat/merge-only-sibling");
    expect(git(["rev-parse", "refs/heads/feat/merge-only-approved"], repo).trim()).toBe(approvedTip);
    expect(runGit(["merge-base", "--is-ancestor", reviewedMain, approvedTip], repo).status).toBe(0);
    expect(runGit(["merge-base", "--is-ancestor", approvedCommit, approvedTip], repo).status).toBe(0);
    expect(runGit(["merge-base", "--is-ancestor", siblingCommit, siblingTip], repo).status).toBe(0);
    expect(git(["remote"], repo)).toBe("");

    expect(runGit(["merge", "--no-commit", "--no-ff", "refs/heads/feat/merge-only-approved"], repo).status).toBe(0);
    expect(git(["rev-parse", "refs/heads/main"], repo).trim()).toBe(reviewedMain);
    expect(runGit(["merge-base", "--is-ancestor", "refs/heads/feat/merge-only-sibling", "refs/heads/main"], repo).status)
      .not.toBe(0);
    expect(runGit(["merge-base", "--is-ancestor", "refs/heads/feat/merge-only-approved", "refs/heads/main"], repo).status)
      .not.toBe(0);
    git(["commit", "-q", "-m", "chore(merge-only-approved): merge feature"], repo);

    const mergeCommit = git(["rev-parse", "refs/heads/main"], repo).trim();
    const mergeParents = git(["rev-list", "--parents", "-n", "1", mergeCommit], repo).trim().split(" ");
    expect(mergeParents).toEqual([mergeCommit, reviewedMain, approvedTip]);
    expect(runGit(["merge-base", "--is-ancestor", "refs/heads/feat/merge-only-approved", "refs/heads/main"], repo).status)
      .toBe(0);
    expect(runGit(["merge-base", "--is-ancestor", "refs/heads/feat/merge-only-sibling", "refs/heads/main"], repo).status)
      .not.toBe(0);
    expect(readFileSync(approvedCheckpoint, "utf8")).toContain('"app_review": "approved"');

    const removeApproved = runWorktree(repo, ["rm", "merge-only-approved"]);

    expect(removeApproved.status).toBe(0);
    expect(existsSync(approved)).toBe(false);
    expect(runGit(["show-ref", "--verify", "refs/heads/feat/merge-only-approved"], repo).status).not.toBe(0);
    expect(existsSync(sibling)).toBe(true);
    expect(git(["rev-parse", "refs/heads/feat/merge-only-sibling"], repo).trim()).toBe(siblingTip);
    expect(git(["worktree", "list", "--porcelain"], repo)).toContain(realpathSync(sibling));
    expect(readFileSync(join(sibling, "src", "sibling.ts"), "utf8")).toBe("sibling remains\n");
    expect(readFileSync(siblingCheckpoint, "utf8")).toContain('"phase": "implementation"');
  });

  test("U27: uncertain ancestry preserves the feature and verified ancestry is required before removal", () => {
    const repo = initRepo();
    const feature = addBranchWorktree(repo, "merge-unverified");
    const reviewedMain = git(["rev-parse", "refs/heads/main"], repo).trim();
    const featureContents = "keep until merge proof\n";
    const featureCommit = commitFile(feature, "src/feature.ts", featureContents, "feature change");
    const checkpoint = writeCheckpoint(
      feature,
      "merge-unverified",
      mergeReadyPlan("merge-unverified", reviewedMain),
    );
    commitCheckpoint(feature, checkpoint);
    const featureTip = git(["rev-parse", "refs/heads/feat/merge-unverified"], repo).trim();
    const checkpointContents = readFileSync(checkpoint, "utf8");
    expect(runGit(["merge-base", "--is-ancestor", featureCommit, featureTip], repo).status).toBe(0);
    expect(git(["remote"], repo)).toBe("");
    const beforeUnmergedRemoval = repoSnapshot(repo, [feature], [checkpoint]);

    const unmergedRemoval = runWorktree(repo, ["rm", "merge-unverified"]);

    expect(unmergedRemoval.status).not.toBe(0);
    expect(unmergedRemoval.stderr).toContain("not merged into the local main");
    expect(repoSnapshot(repo, [feature], [checkpoint])).toBe(beforeUnmergedRemoval);
    expect(git(["rev-parse", "refs/heads/feat/merge-unverified"], repo).trim()).toBe(featureTip);
    expect(readFileSync(checkpoint, "utf8")).toBe(checkpointContents);
    expect(readFileSync(join(feature, "src", "feature.ts"), "utf8")).toBe(featureContents);
    expect(existsSync(feature)).toBe(true);

    const advancedMain = commitFile(repo, "src/main-after-review.ts", "different first parent\n", "advance main");
    expect(git(["rev-parse", "refs/heads/main"], repo).trim()).toBe(advancedMain);
    expect(runGit(["merge", "--no-commit", "--no-ff", "refs/heads/feat/merge-unverified"], repo).status).toBe(0);
    git(["commit", "-q", "-m", "merge against unreviewed main"], repo);

    const unreviewedMerge = git(["rev-parse", "refs/heads/main"], repo).trim();
    const unreviewedParents = git(["rev-list", "--parents", "-n", "1", unreviewedMerge], repo).trim().split(" ");
    const featureIsAncestor = runGit(
      ["merge-base", "--is-ancestor", "refs/heads/feat/merge-unverified", "refs/heads/main"],
      repo,
    ).status === 0;
    expect(featureIsAncestor).toBe(true);
    expect(unreviewedParents[1]).not.toBe(reviewedMain);
    expect(unreviewedParents[1]).toBe(advancedMain);
    expect(existsSync(feature)).toBe(true);
    expect(git(["rev-parse", "refs/heads/feat/merge-unverified"], repo).trim()).toBe(featureTip);
    expect(readFileSync(checkpoint, "utf8")).toBe(checkpointContents);
    expect(readFileSync(join(feature, "src", "feature.ts"), "utf8")).toBe(featureContents);
  });

  test("U31: ready lifecycle remains active until the CLI merge removes its Git-listed feature worktree", () => {
    const repo = initRepo();
    const slug = "merge-lifecycle-close";
    const feature = addBranchWorktree(repo, slug);
    const reviewedMain = git(["rev-parse", "refs/heads/main"], repo).trim();
    const reviewedFeature = commitFile(feature, "src/active.ts", "approved work\n", "approved work");
    ignoreLifecycleCheckpoints(repo);
    const checkpoint = writeCheckpoint(
      feature,
      slug,
      mergeReadyPlan(slug, reviewedMain, reviewedFeature),
    );
    const checkpointContents = readFileSync(checkpoint, "utf8");
    const checkpointState = JSON.parse(checkpointContents) as {
      lifecycle: {
        phase: string;
        plan_approval: string;
        app_review: string;
        reviewed_main: string;
        reviewed_feature: string;
      };
    };

    expect(checkpointState.lifecycle).toEqual({
      phase: "ready-to-merge",
      plan_approval: "approved",
      app_review: "approved",
      reviewed_main: reviewedMain,
      reviewed_feature: reviewedFeature,
    });
    expect(checkpointContents).not.toContain('"phase": "complete"');
    expect(git(["status", "--porcelain", "--untracked-files=all"], feature)).toBe("");
    expect(git(["worktree", "list", "--porcelain"], repo)).toContain(realpathSync(feature));

    const merge = runWorktree(repo, ["merge", slug]);

    expect(merge.status).toBe(0);
    expect(git(["rev-list", "--parents", "-n", "1", "refs/heads/main"], repo).trim().split(" ")).toEqual([
      git(["rev-parse", "refs/heads/main"], repo).trim(),
      reviewedMain,
      reviewedFeature,
    ]);
    expect(runGit(["merge-base", "--is-ancestor", reviewedFeature, "refs/heads/main"], repo).status).toBe(0);
    expect(git(["worktree", "list", "--porcelain"], repo)).not.toContain(realpathSync(feature));
    expect(runGit(["show-ref", "--verify", `refs/heads/feat/${slug}`], repo).status).not.toBe(0);
    expect(existsSync(feature)).toBe(false);
    expect(existsSync(checkpoint)).toBe(false);
    expect(git(["status", "--porcelain", "--untracked-files=all"], repo)).toBe("");
  });
});
