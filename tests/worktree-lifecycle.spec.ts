import { afterAll, beforeAll, describe, expect, test } from "bun:test";
import { spawnSync } from "node:child_process";
import {
  existsSync,
  cpSync,
  mkdirSync,
  mkdtempSync,
  readdirSync,
  readFileSync,
  realpathSync,
  rmSync,
  statSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { runWorktreeCommand } from "./fixtures/worktree-command.ts";

// `.native` expands Windows 8.3 names (RUNNER~1) the way git and the product do.
const root = mkdtempSync(join(realpathSync.native(tmpdir()), "worktree-lifecycle-"));
const emptyGitConfig = join(root, "empty-gitconfig");
writeFileSync(emptyGitConfig, "");
let repoTemplate = "";
const childEnv: NodeJS.ProcessEnv = {
  ...process.env,
  GIT_CONFIG_GLOBAL: emptyGitConfig,
  GIT_CONFIG_SYSTEM: emptyGitConfig,
  GIT_EDITOR: `"${process.execPath}" -e "process.exit(0)"`,
  GIT_TERMINAL_PROMPT: "0",
};

beforeAll(() => {
  repoTemplate = initializeRepo(join(root, "template"));
});

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

/** The worktree paths git registers, in the platform's own separators (git prints `C:/...` on Windows). */
function registeredPaths(repo: string): string[] {
  return git(["worktree", "list", "--porcelain"], repo)
    .split("\n")
    .filter((line) => line.startsWith("worktree "))
    .map((line) => resolve(line.slice("worktree ".length)));
}

function runList(cwd: string): Run {
  return runWorktreeCommand(["worktree", "list"], cwd, childEnv);
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

function initializeRepo(repo: string): string {
  mkdirSync(repo, { recursive: true });
  git(["init", "-q", "-b", "main"], repo);
  git(["config", "user.name", "Ada Lovelace"], repo);
  git(["config", "user.email", "ada@example.com"], repo);
  git(["config", "commit.gpgsign", "false"], repo);
  mkdirSync(join(repo, ".ai-engineering"), { recursive: true });
  writeFileSync(join(repo, ".ai-engineering", "config.toml"), '[git]\nbase = "main"\n');
  mkdirSync(join(repo, "src"));
  writeFileSync(join(repo, "README.md"), "# fixture\n");
  writeFileSync(join(repo, "src", "shared.ts"), "export const value = 1;\n");
  git(["add", "-A"], repo);
  git(["commit", "-q", "-m", "fixture base"], repo);
  return repo;
}

function initRepo(): string {
  const repo = join(mkdtempSync(join(root, "repo-")), "primary");
  cpSync(repoTemplate, repo, { recursive: true });
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
  return mergeLifecyclePlan(slug, "ready-to-merge", "approved", reviewedMain, reviewedFeature);
}

function mergeLifecyclePlan(
  slug: string,
  phase: string,
  appReview: string,
  reviewedMain: string,
  reviewedFeature: string,
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
      phase,
      plan_approval: "approved",
      app_review: appReview,
      reviewed_main: reviewedMain,
      reviewed_feature: reviewedFeature,
    },
  };
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

  test("legacy review checkpoints translate against the detected non-main base", () => {
    const repo = initRepo();
    const configPath = join(repo, ".ai-engineering", "config.toml");
    writeFileSync(configPath, '[git]\nbase = "develop"\n');
    git(["add", configPath], repo);
    git(["commit", "-q", "-m", "configure detected base"], repo);
    const reviewedBase = git(["rev-parse", "HEAD"], repo).trim();
    git(["branch", "develop", reviewedBase], repo);

    const feature = worktreePath(repo, "alpha");
    mkdirSync(dirname(feature), { recursive: true });
    git(["worktree", "add", "--quiet", "-b", "feat/alpha", feature, "refs/heads/develop"], repo);
    const reviewedFeature = commitFile(feature, "feature.txt", "feature\n", "feature work");
    writeCheckpoint(feature, "alpha", mergeLifecyclePlan(
      "alpha",
      "awaiting-app-review",
      "pending",
      reviewedBase,
      reviewedFeature,
    ));
    commitFile(repo, "main-only.txt", "main\n", "advance main");

    expect(git(["rev-parse", "refs/heads/develop"], repo).trim()).toBe(reviewedBase);
    expect(git(["rev-parse", "refs/heads/main"], repo).trim()).not.toBe(reviewedBase);
    expect(runGit(["merge-base", "--is-ancestor", reviewedBase, reviewedFeature], repo).status).toBe(0);

    const result = runList(repo);

    expect(result.status).toBe(0);
    expect(result.stdout).toContain("awaiting-app-review (plan approved, app review pending)");
    expect(result.stdout).not.toContain("unknown (reviewed_base is stale)");
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
    expect(resolve(git(["rev-parse", "--show-toplevel"], feature).trim())).toBe(realpathSync(feature));
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
    expect(registeredPaths(repo)).toContain(realpathSync(feature));
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
    expect(registeredPaths(repo)).toContain(realpathSync(failedGate));

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

});
