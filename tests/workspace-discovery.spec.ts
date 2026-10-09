import { afterEach, beforeEach, describe, expect, test } from "bun:test";
import {
  existsSync,
  lstatSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  realpathSync,
  renameSync,
  rmSync,
  symlinkSync,
  writeFileSync,
} from "node:fs";
import { spawnSync } from "node:child_process";
import { dirname, join } from "node:path";
import { pathToFileURL } from "node:url";

type WorkspaceStatus = "needs-review" | "in-progress" | "blocked" | "closed" | "unknown";
type WorkspaceFilter = "all" | WorkspaceStatus;

interface WorkspaceItem {
  slug: string;
  branch: string | null;
  worktreePath: string | null;
  status: WorkspaceStatus;
  dirty: boolean;
}

interface WorkspaceProject {
  root: string;
  items: WorkspaceItem[];
  history: Array<{ slug: string }>;
}

interface WorkspaceDiscoveryResult {
  projects: WorkspaceProject[];
  errors: Array<{ root: string; detail: string }>;
}

interface WorkspaceDiscoveryApi {
  matchesDirectoryIdentity(path: string, expected: { device: number; inode: number }): boolean;
  discoverWorkspace(
    roots: string[],
    options?: { filter?: WorkspaceFilter; now?: Date },
  ): WorkspaceDiscoveryResult | Promise<WorkspaceDiscoveryResult>;
}

interface GitRun {
  status: number;
  stdout: string;
  stderr: string;
}

interface CheckpointOptions {
  checkpointStatus?: string;
  gateStatus?: string;
  reviewGateStatus?: string;
  phase?: string;
  planApproval?: string;
  appReview?: string;
  reviewedMain?: string | null;
  reviewedFeature?: string | null;
  checkpointSlug?: string;
}

const DISCOVERY_MODULE = join(import.meta.dir, "..", "src", "workspace", "discovery.ts");
const FIXED_DATE = "2026-10-09T12:00:00.000Z";
const FIXED_NOW = new Date(FIXED_DATE);
let discoveryApi: WorkspaceDiscoveryApi | undefined;
let discoveryImportError: unknown;
if (existsSync(DISCOVERY_MODULE)) {
  try {
    discoveryApi = (await import(pathToFileURL(DISCOVERY_MODULE).href)) as WorkspaceDiscoveryApi;
  } catch (error) {
    discoveryImportError = error;
  }
}

let sandbox = "";
let emptyGitConfig = "";
let gitEnvironment: NodeJS.ProcessEnv = {};

beforeEach(() => {
  sandbox = mkdtempSync(join(import.meta.dir, ".workspace-discovery-"));
  emptyGitConfig = join(sandbox, "empty-gitconfig");
  writeFileSync(emptyGitConfig, "");
  gitEnvironment = {
    ...process.env,
    GIT_CONFIG_GLOBAL: emptyGitConfig,
    GIT_CONFIG_SYSTEM: emptyGitConfig,
    GIT_TERMINAL_PROMPT: "0",
    GIT_AUTHOR_DATE: FIXED_DATE,
    GIT_COMMITTER_DATE: FIXED_DATE,
  };
});

afterEach(() => {
  rmSync(sandbox, { recursive: true, force: true });
});

function discovery(): WorkspaceDiscoveryApi {
  expect(existsSync(DISCOVERY_MODULE), "workspace discovery behavior is not implemented yet").toBe(true);
  if (discoveryImportError !== undefined) throw discoveryImportError;
  expect(typeof discoveryApi?.discoverWorkspace, "discoverWorkspace export is required").toBe("function");
  return discoveryApi!;
}

function runGit(args: string[], cwd: string): GitRun {
  const gitProcess = spawnSync("git", args, { cwd, encoding: "utf8", env: gitEnvironment });
  return {
    status: gitProcess.status ?? 1,
    stdout: gitProcess.stdout ?? "",
    stderr: gitProcess.stderr ?? "",
  };
}

function git(args: string[], cwd: string): string {
  const result = runGit(args, cwd);
  if (result.status !== 0) {
    throw new Error(`git ${args.join(" ")} failed in ${cwd}: ${result.stderr}`);
  }
  return result.stdout.trimEnd();
}

function initRepo(repoPath: string): string {
  mkdirSync(repoPath, { recursive: true });
  git(["init", "--quiet", "-b", "main"], repoPath);
  git(["config", "user.name", "Workspace Test"], repoPath);
  git(["config", "user.email", "workspace-test@example.invalid"], repoPath);
  git(["config", "commit.gpgsign", "false"], repoPath);
  writeFileSync(join(repoPath, "README.md"), "# fixture\n");
  git(["add", "README.md"], repoPath);
  git(["commit", "--quiet", "-m", "base"], repoPath);
  return realpathSync(repoPath);
}

function addWorktree(repoPath: string, slug: string, worktreesRoot = `${repoPath}.worktrees`): string {
  const worktreePath = join(worktreesRoot, slug);
  mkdirSync(dirname(worktreePath), { recursive: true });
  git(["worktree", "add", "--quiet", "-b", `feat/${slug}`, worktreePath, "refs/heads/main"], repoPath);
  return realpathSync(worktreePath);
}

function commitFile(repoPath: string, relativePath: string, contents: string, message: string): string {
  const filePath = join(repoPath, relativePath);
  mkdirSync(dirname(filePath), { recursive: true });
  writeFileSync(filePath, contents);
  git(["add", relativePath], repoPath);
  git(["commit", "--quiet", "-m", message], repoPath);
  return git(["rev-parse", "HEAD"], repoPath);
}

function checkpointPath(repoPath: string, slug: string): string {
  return join(repoPath, ".ai-engineering", "workflow", "checkpoints", `${slug}.json`);
}

function checkpointPlan(slug: string, options: CheckpointOptions = {}): Record<string, unknown> {
  const gateStatus = options.gateStatus ?? "pending";
  const reviewGateStatus = options.reviewGateStatus ?? gateStatus;
  const phase = options.phase ?? "implementation";
  return {
    feature: `Feature ${slug}`,
    slug: options.checkpointSlug ?? slug,
    summary: `Plan summary for ${slug}`,
    plain_summary: `Plain summary for ${slug}`,
    gating: "Run gates in order.",
    assumptions: [],
    notes: [`Plan note for ${slug}.`],
    new_dependencies: [],
    checkpoints: [{
      id: 1,
      title: `Checkpoint for ${slug}`,
      goal: `Complete ${slug}.`,
      plain: {
        what: `Complete ${slug}.`,
        why: `This is needed for ${slug}.`,
        check: `Verify ${slug}.`,
      },
      simple: `Complete ${slug}`,
      size: "s",
      builds_on: [],
      tasks: [`Implement ${slug}.`],
      acceptance: [`${slug} is complete.`],
      verify: [`bun test ${slug}`],
      ui: null,
      status: options.checkpointStatus ?? "pending",
      gates: {
        behavior: { status: gateStatus, attempts: 1, findings: [] },
        ui: { status: gateStatus, attempts: 1, findings: [] },
        review: { status: reviewGateStatus, attempts: 1, findings: [] },
      },
      files: [],
    }],
    lifecycle: {
      phase,
      plan_approval: options.planApproval ?? (phase === "awaiting-plan-approval" ? "pending" : "approved"),
      app_review: options.appReview ?? (phase === "awaiting-app-review" ? "pending" : "not-started"),
      reviewed_main: options.reviewedMain ?? null,
      reviewed_feature: options.reviewedFeature ?? null,
    },
  };
}

function writeCheckpoint(repoPath: string, slug: string, plan: Record<string, unknown>): string {
  const path = checkpointPath(repoPath, slug);
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, `${JSON.stringify(plan, null, 2)}\n`);
  return path;
}

function readCheckpointPlan(repoPath: string, slug: string): Record<string, unknown> {
  return JSON.parse(readFileSync(checkpointPath(repoPath, slug), "utf8")) as Record<string, unknown>;
}

function commitCheckpoint(worktreePath: string, slug: string, plan: Record<string, unknown>, message: string): string {
  const path = writeCheckpoint(worktreePath, slug, plan);
  git(["add", path], worktreePath);
  git(["commit", "--quiet", "-m", message], worktreePath);
  return git(["rev-parse", "HEAD"], worktreePath);
}

function commitMainCheckpoint(repoPath: string, slug: string, plan: Record<string, unknown>, message: string): void {
  const path = writeCheckpoint(repoPath, slug, plan);
  git(["add", path], repoPath);
  git(["commit", "--quiet", "-m", message], repoPath);
}

function createValidReviewLifecycle(
  worktreePath: string,
  slug: string,
  reviewedMain: string,
  finalPhase: "awaiting-app-review" | "ready-to-merge",
): void {
  const gatesComplete = {
    phase: "implementation",
    checkpointStatus: "passed",
    gateStatus: "passed",
    reviewGateStatus: "passed",
  };
  commitCheckpoint(worktreePath, slug, checkpointPlan(slug, gatesComplete), `checkpoint implementation ${slug}`);
  const reviewedFeature = git(["rev-parse", "HEAD"], worktreePath);
  commitCheckpoint(worktreePath, slug, checkpointPlan(slug, {
    ...gatesComplete,
    phase: "awaiting-app-review",
    appReview: "pending",
    reviewedMain,
    reviewedFeature,
  }), `checkpoint awaiting app review ${slug}`);
  if (finalPhase === "ready-to-merge") {
    commitCheckpoint(worktreePath, slug, checkpointPlan(slug, {
      ...gatesComplete,
      phase: "ready-to-merge",
      appReview: "approved",
      reviewedMain,
      reviewedFeature,
    }), `checkpoint ready to merge ${slug}`);
  }
}

function gitWorktreePaths(repoPath: string): string[] {
  return git(["worktree", "list", "--porcelain"], repoPath)
    .split(/\n\n/)
    .map((block) => block.split("\n").find((line) => line.startsWith("worktree "))?.slice("worktree ".length))
    .filter((path): path is string => path !== undefined)
    .map((path) => realpathSync(path));
}

async function discoverWorkspace(
  roots: string[],
  filter: WorkspaceFilter = "all",
): Promise<WorkspaceDiscoveryResult> {
  return await discovery().discoverWorkspace(roots, { filter, now: new Date(FIXED_NOW) });
}

function projectFor(snapshot: WorkspaceDiscoveryResult, repoPath: string): WorkspaceProject {
  const canonicalRoot = realpathSync(repoPath);
  const project = snapshot.projects.find((candidate) => candidate.root === canonicalRoot);
  expect(project, `discovery should include repository ${canonicalRoot}`).toBeDefined();
  return project!;
}

function itemFor(snapshot: WorkspaceDiscoveryResult, slug: string): WorkspaceItem {
  const item = snapshot.projects.flatMap((project) => project.items).find((candidate) => candidate.slug === slug);
  expect(item, `discovery should include lifecycle item ${slug}`).toBeDefined();
  return item!;
}

interface HistoryFixtureOptions {
  mergeToMain?: boolean;
  removeWorktree?: boolean;
  checkpointStatus?: string;
  gateStatus?: string;
  reviewGateStatus?: string;
  checkpointSlug?: string;
  omitCheckpoint?: boolean;
}

interface HistoryFixture {
  repoPath: string;
  worktreePath: string;
  featureCommit: string;
}

function createHistoryFixture(parentPath: string, slug: string, options: HistoryFixtureOptions = {}): HistoryFixture {
  const repoPath = initRepo(join(parentPath, slug));
  const worktreePath = addWorktree(repoPath, slug);
  const reviewedMain = git(["rev-parse", "refs/heads/main"], repoPath);
  const featureCommit = commitFile(worktreePath, "feature.txt", `${slug}\n`, `feature ${slug}`);

  if (!options.omitCheckpoint) {
    commitCheckpoint(worktreePath, slug, checkpointPlan(slug, {
      phase: "implementation",
    }), `checkpoint implementation ${slug}`);
    const reviewedFeature = git(["rev-parse", "HEAD"], worktreePath);
    const reviewPlan = {
      phase: "ready-to-merge",
      checkpointStatus: options.checkpointStatus ?? "passed",
      gateStatus: options.gateStatus ?? "passed",
      reviewGateStatus: options.reviewGateStatus ?? options.gateStatus ?? "passed",
      appReview: "pending",
      reviewedMain,
      ...(options.checkpointSlug === undefined ? {} : { checkpointSlug: options.checkpointSlug }),
    } as const;
    commitCheckpoint(worktreePath, slug, checkpointPlan(slug, {
      ...reviewPlan,
      phase: "awaiting-app-review",
      appReview: "pending",
      reviewedFeature,
    }), `checkpoint awaiting app review ${slug}`);
    commitCheckpoint(worktreePath, slug, checkpointPlan(slug, {
      ...reviewPlan,
      appReview: "approved",
      reviewedFeature,
    }), `checkpoint ready to merge ${slug}`);
  }

  if (options.mergeToMain) {
    git(["merge", "--no-ff", "--no-edit", "-m", `merge ${slug}`, `feat/${slug}`], repoPath);
  }
  if (options.removeWorktree) git(["worktree", "remove", "--force", worktreePath], repoPath);

  return { repoPath, worktreePath, featureCommit };
}

describe("workspace discovery and lifecycle status (checkpoint 9)", () => {
  test("U36 discovers only repositories beneath canonical configured roots and preserves scan errors", async () => {
    const api = discovery();
    const configuredRoot = join(sandbox, "configured");
    const inScopeRepo = initRepo(join(configuredRoot, "nested", "in-scope"));
    const outsideRoot = join(sandbox, "outside");
    const escapedRepo = initRepo(join(outsideRoot, "escaped"));
    const escapeLink = join(configuredRoot, "linked-outside");
    mkdirSync(configuredRoot, { recursive: true });
    symlinkSync(outsideRoot, escapeLink);

    const snapshot = await api.discoverWorkspace([realpathSync(configuredRoot)], {
      filter: "all",
      now: new Date(FIXED_NOW),
    });

    expect(snapshot.projects.map((project) => project.root)).toContain(inScopeRepo);
    expect(snapshot.projects.map((project) => project.root)).not.toContain(escapedRepo);

    const missingRoot = join(sandbox, "removed-after-configuration");
    mkdirSync(missingRoot);
    const canonicalMissingRoot = realpathSync(missingRoot);
    rmSync(missingRoot, { recursive: true, force: true });
    const incompleteScan = await api.discoverWorkspace([canonicalMissingRoot], {
      filter: "all",
      now: new Date(FIXED_NOW),
    });
    expect(incompleteScan.projects).toEqual([]);
    expect(incompleteScan.errors.some((error) => error.root === canonicalMissingRoot)).toBe(true);
  });

  test("U36a rejects a symlink replacement when revalidating a checked directory identity", () => {
    const api = discovery();
    const checkedPath = join(sandbox, "checked-directory");
    const replacementPath = join(sandbox, "replacement-directory");
    mkdirSync(checkedPath);
    mkdirSync(replacementPath);
    const identity = lstatSync(checkedPath);
    const expectedIdentity = { device: identity.dev, inode: identity.ino };
    const renamedPath = join(sandbox, "renamed-directory");
    renameSync(checkedPath, renamedPath);
    symlinkSync(replacementPath, checkedPath);

    expect(api.matchesDirectoryIdentity(checkedPath, expectedIdentity)).toBe(false);
  });

  test("U37 reports only Git-registered feature worktrees and honors an external git.worktrees_dir", async () => {
    discovery();
    const searchRoot = join(sandbox, "projects");
    const customWorktreesRoot = join(sandbox, "registered-worktrees");
    const repoPath = initRepo(join(searchRoot, "alpha"));
    const registeredWorktree = addWorktree(repoPath, "registered", customWorktreesRoot);
    const unregisteredRepo = initRepo(join(customWorktreesRoot, "unregistered"));
    mkdirSync(join(repoPath, ".ai-engineering"), { recursive: true });
    writeFileSync(
      join(repoPath, ".ai-engineering", "config.toml"),
      `[git]\nworktrees_dir = "${customWorktreesRoot}"\n`,
    );

    const registeredPathsBefore = gitWorktreePaths(repoPath);
    expect(registeredPathsBefore).toContain(realpathSync(repoPath));
    expect(registeredPathsBefore).toContain(registeredWorktree);
    expect(registeredPathsBefore).not.toContain(unregisteredRepo);

    const snapshot = await discoverWorkspace([realpathSync(searchRoot)]);
    const project = projectFor(snapshot, repoPath);
    const reportedWorktrees = project.items
      .map((item) => item.worktreePath)
      .filter((worktreePath): worktreePath is string => worktreePath !== null);

    expect(reportedWorktrees).toContain(registeredWorktree);
    expect(reportedWorktrees).not.toContain(unregisteredRepo);
    expect(reportedWorktrees.every((path) => registeredPathsBefore.includes(path))).toBe(true);
  });

  test("U38 maps explicit lifecycle and Git evidence to filters, never treating dirty state as active", async () => {
    discovery();
    const searchRoot = join(sandbox, "projects");
    const repoPath = initRepo(join(searchRoot, "statuses"));
    const preStartPath = writeCheckpoint(repoPath, "approved-before-start", checkpointPlan("approved-before-start", {
      phase: "approval-before-start",
      planApproval: "approved",
      appReview: "not-started",
    }));
    git(["add", preStartPath], repoPath);
    git(["commit", "--quiet", "-m", "record pre-worktree approval"], repoPath);
    const mainCommit = git(["rev-parse", "refs/heads/main"], repoPath);
    expect(git(["ls-tree", "-r", "--name-only", "refs/heads/main"], repoPath).split("\n"))
      .toContain(".ai-engineering/workflow/checkpoints/approved-before-start.json");
    const slugs = [
      "plan-review",
      "app-review",
      "app-review-missing-shas",
      "app-review-stale",
      "implementation",
      "ready",
      "ready-stale",
      "lifecycle-blocked",
      "git-conflict",
      "dirty-unknown",
      "malformed-unknown",
    ];
    const worktrees = new Map<string, string>();
    for (const slug of slugs) worktrees.set(slug, addWorktree(repoPath, slug));

    const plans: Array<[string, CheckpointOptions]> = [
      ["plan-review", { phase: "awaiting-plan-approval" }],
      ["implementation", { phase: "implementation" }],
      ["lifecycle-blocked", { phase: "blocked", checkpointStatus: "blocked", reviewGateStatus: "blocked" }],
    ];
    for (const [slug, options] of plans) {
      const path = writeCheckpoint(worktrees.get(slug)!, slug, checkpointPlan(slug, options));
      git(["add", path], worktrees.get(slug)!);
      git(["commit", "--quiet", "-m", `checkpoint ${slug}`], worktrees.get(slug)!);
    }
    createValidReviewLifecycle(worktrees.get("app-review")!, "app-review", mainCommit, "awaiting-app-review");
    createValidReviewLifecycle(worktrees.get("ready")!, "ready", mainCommit, "ready-to-merge");
    const missingReviewPath = writeCheckpoint(
      worktrees.get("app-review-missing-shas")!,
      "app-review-missing-shas",
      checkpointPlan("app-review-missing-shas", {
        phase: "awaiting-app-review",
        checkpointStatus: "passed",
        gateStatus: "passed",
        reviewGateStatus: "passed",
      }),
    );
    git(["add", missingReviewPath], worktrees.get("app-review-missing-shas")!);
    git(["commit", "--quiet", "-m", "checkpoint missing review shas"], worktrees.get("app-review-missing-shas")!);
    createValidReviewLifecycle(
      worktrees.get("app-review-stale")!,
      "app-review-stale",
      mainCommit,
      "awaiting-app-review",
    );
    commitFile(worktrees.get("app-review-stale")!, "post-review.txt", "stale review\n", "change code after app review");
    createValidReviewLifecycle(worktrees.get("ready-stale")!, "ready-stale", mainCommit, "ready-to-merge");
    commitFile(worktrees.get("ready-stale")!, "post-review.txt", "stale review\n", "change code after ready review");

    const conflictPath = worktrees.get("git-conflict")!;
    const conflictCheckpoint = writeCheckpoint(conflictPath, "git-conflict", checkpointPlan("git-conflict"));
    git(["add", conflictCheckpoint], conflictPath);
    git(["commit", "--quiet", "-m", "checkpoint git conflict"], conflictPath);
    commitFile(conflictPath, "README.md", "# feature side\n", "feature side");
    git(["switch", "--quiet", "-c", "topic/conflict", "refs/heads/main"], repoPath);
    commitFile(repoPath, "README.md", "# main side\n", "main side");
    git(["switch", "--quiet", "main"], repoPath);
    const mergeConflict = runGit(["merge", "topic/conflict"], conflictPath);
    expect(mergeConflict.status).not.toBe(0);
    expect(git(["status", "--porcelain"], conflictPath)).toContain("UU README.md");

    writeFileSync(join(worktrees.get("dirty-unknown")!, "local.txt"), "uncommitted\n");
    const detachedPath = join(`${repoPath}.worktrees`, "detached-unknown");
    mkdirSync(dirname(detachedPath), { recursive: true });
    git(["worktree", "add", "--quiet", "--detach", detachedPath, "refs/heads/main"], repoPath);
    worktrees.set("detached-unknown", realpathSync(detachedPath));
    const malformedPath = writeCheckpoint(
      worktrees.get("malformed-unknown")!,
      "malformed-unknown",
      checkpointPlan("malformed-unknown"),
    );
    writeFileSync(malformedPath, "{ invalid json\n");

    expect(gitWorktreePaths(repoPath)).not.toContain(join(repoPath, ".worktrees", "approved-before-start"));

    const snapshot = await discoverWorkspace([realpathSync(searchRoot)], "all");
    const expectedStatuses: Array<[string, WorkspaceStatus]> = [
      ["plan-review", "needs-review"],
      ["app-review", "needs-review"],
      ["app-review-missing-shas", "unknown"],
      ["app-review-stale", "unknown"],
      ["implementation", "in-progress"],
      ["ready", "in-progress"],
      ["ready-stale", "unknown"],
      ["lifecycle-blocked", "blocked"],
      ["git-conflict", "blocked"],
      ["dirty-unknown", "unknown"],
      ["detached-unknown", "unknown"],
      ["malformed-unknown", "unknown"],
      ["approved-before-start", "needs-review"],
    ];
    for (const [slug, expectedStatus] of expectedStatuses) {
      expect(itemFor(snapshot, slug).status, slug).toBe(expectedStatus);
    }
    expect(itemFor(snapshot, "dirty-unknown").dirty).toBe(true);
    expect(itemFor(snapshot, "approved-before-start").worktreePath).toBeNull();

    for (const status of ["needs-review", "in-progress", "blocked", "unknown"] as const) {
      const filtered = await discoverWorkspace([realpathSync(searchRoot)], status);
      const filteredItems = filtered.projects.flatMap((project) => project.items);
      expect(filteredItems.length).toBeGreaterThan(0);
      expect(filteredItems.every((item) => item.status === status)).toBe(true);
    }
    const needsReview = await discoverWorkspace([realpathSync(searchRoot)], "needs-review");
    expect(needsReview.projects.flatMap((project) => project.items).map((item) => item.slug)).toContain("approved-before-start");
    const unknown = await discoverWorkspace([realpathSync(searchRoot)], "unknown");
    expect(unknown.projects.flatMap((project) => project.items).map((item) => item.slug)).toContain("dirty-unknown");
  }, 20_000);

  test("U39 emits closed history only with matching main checkpoint, complete gates, merge proof, and no worktree", async () => {
    discovery();
    const searchRoot = join(sandbox, "projects");
    mkdirSync(searchRoot, { recursive: true });
    const closed = createHistoryFixture(searchRoot, "closed-valid", { mergeToMain: true, removeWorktree: true });
    const incompleteGates = createHistoryFixture(searchRoot, "closed-incomplete-gates", {
      mergeToMain: true,
      removeWorktree: true,
      reviewGateStatus: "pending",
    });
    const unmerged = createHistoryFixture(searchRoot, "unmerged-history", { removeWorktree: true });
    const stillRegistered = createHistoryFixture(searchRoot, "merged-but-open", { mergeToMain: true });
    const mismatched = createHistoryFixture(searchRoot, "mismatched-checkpoint", {
      mergeToMain: true,
      removeWorktree: true,
      checkpointSlug: "different-slug",
    });
    const missing = createHistoryFixture(searchRoot, "missing-checkpoint", {
      mergeToMain: true,
      removeWorktree: true,
      omitCheckpoint: true,
    });
    const detached = createHistoryFixture(searchRoot, "detached-closed", { mergeToMain: true });
    git(["switch", "--detach", "HEAD"], detached.worktreePath);
    const prunable = createHistoryFixture(searchRoot, "prunable-closed", { mergeToMain: true });
    rmSync(prunable.worktreePath, { recursive: true, force: true });
    const prunableEntry = git(["worktree", "list", "--porcelain"], prunable.repoPath)
      .split("\n\n")
      .find((block) => block.includes(prunable.worktreePath));
    expect(prunableEntry).toContain("prunable");

    const nestedOnly = createHistoryFixture(searchRoot, "nested-checkpoint", {
      mergeToMain: true,
      removeWorktree: true,
    });
    const nestedOnlyCheckpoint = checkpointPath(nestedOnly.repoPath, "nested-checkpoint");
    const nestedOnlyPath = join(
      nestedOnly.repoPath,
      ".ai-engineering",
      "workflow",
      "checkpoints",
      "archive",
      "nested-checkpoint.json",
    );
    const nestedOnlyContents = readFileSync(nestedOnlyCheckpoint, "utf8");
    rmSync(nestedOnlyCheckpoint);
    mkdirSync(dirname(nestedOnlyPath), { recursive: true });
    writeFileSync(nestedOnlyPath, nestedOnlyContents);
    git(["add", "-A"], nestedOnly.repoPath);
    git(["commit", "--quiet", "-m", "misplace nested checkpoint"], nestedOnly.repoPath);

    const duplicateCheckpoint = createHistoryFixture(searchRoot, "duplicate-checkpoint", {
      mergeToMain: true,
      removeWorktree: true,
    });
    const duplicateCanonical = checkpointPath(duplicateCheckpoint.repoPath, "duplicate-checkpoint");
    const duplicateNestedPath = join(
      duplicateCheckpoint.repoPath,
      ".ai-engineering",
      "workflow",
      "checkpoints",
      "archive",
      "duplicate-checkpoint.json",
    );
    mkdirSync(dirname(duplicateNestedPath), { recursive: true });
    writeFileSync(duplicateNestedPath, readFileSync(duplicateCanonical, "utf8"));
    git(["add", duplicateNestedPath], duplicateCheckpoint.repoPath);
    git(["commit", "--quiet", "-m", "duplicate checkpoint under archive"], duplicateCheckpoint.repoPath);

    expect(runGit(["merge-base", "--is-ancestor", "refs/heads/feat/closed-valid", "refs/heads/main"], closed.repoPath).status).toBe(0);
    expect(gitWorktreePaths(closed.repoPath)).not.toContain(closed.worktreePath);
    expect(existsSync(checkpointPath(closed.repoPath, "closed-valid"))).toBe(true);
    expect(runGit([
      "cat-file",
      "-e",
      "refs/heads/main:.ai-engineering/workflow/checkpoints/closed-valid.json",
    ], closed.repoPath).status).toBe(0);
    const closedPlan = JSON.parse(readFileSync(checkpointPath(closed.repoPath, "closed-valid"), "utf8")) as {
      slug: string;
      checkpoints: Array<{ gates: Record<string, { status: string }> }>;
    };
    expect(closedPlan.slug).toBe("closed-valid");
    expect(Object.values(closedPlan.checkpoints[0]!.gates).every((gate) => gate.status === "passed")).toBe(true);
    expect(runGit(["merge-base", "--is-ancestor", "refs/heads/feat/unmerged-history", "refs/heads/main"], unmerged.repoPath).status).not.toBe(0);
    expect(gitWorktreePaths(stillRegistered.repoPath)).toContain(stillRegistered.worktreePath);
    const incompletePlan = JSON.parse(readFileSync(checkpointPath(incompleteGates.repoPath, "closed-incomplete-gates"), "utf8")) as {
      checkpoints: Array<{ gates: Record<string, { status: string }> }>;
    };
    expect(Object.values(incompletePlan.checkpoints[0]!.gates).some((gate) => gate.status !== "passed")).toBe(true);
    expect(existsSync(checkpointPath(mismatched.repoPath, "mismatched-checkpoint"))).toBe(true);
    expect(existsSync(checkpointPath(missing.repoPath, "missing-checkpoint"))).toBe(false);
    const mismatchedPlan = JSON.parse(readFileSync(checkpointPath(mismatched.repoPath, "mismatched-checkpoint"), "utf8")) as {
      slug: string;
    };
    expect(mismatchedPlan.slug).not.toBe("mismatched-checkpoint");

    const snapshot = await discoverWorkspace([realpathSync(searchRoot)], "all");
    expect(itemFor(snapshot, "closed-valid").status).toBe("closed");
    for (const slug of [
      "detached-closed",
      "prunable-closed",
      "nested-checkpoint",
      "duplicate-checkpoint",
    ]) {
      expect(itemFor(snapshot, slug).status, slug).toBe("unknown");
    }
    for (const project of snapshot.projects) {
      expect(project.history.map((item) => item.slug)).not.toContain("detached-closed");
      expect(project.history.map((item) => item.slug)).not.toContain("prunable-closed");
      expect(project.history.map((item) => item.slug)).not.toContain("nested-checkpoint");
      expect(project.history.map((item) => item.slug)).not.toContain("duplicate-checkpoint");
    }
    for (const slug of [
      "closed-incomplete-gates",
      "unmerged-history",
      "merged-but-open",
      "mismatched-checkpoint",
      "missing-checkpoint",
    ]) {
      expect(itemFor(snapshot, slug).status, slug).toBe("unknown");
    }
    const closedFilter = await discoverWorkspace([realpathSync(searchRoot)], "closed");
    expect(closedFilter.projects.flatMap((project) => project.items).map((item) => item.slug)).toEqual(["closed-valid"]);
  }, 20_000);

  test("U39a requires the local-main checkpoint plan to match reviewed_feature", async () => {
    discovery();
    const searchRoot = join(sandbox, "projects");
    mkdirSync(searchRoot, { recursive: true });
    const identical = createHistoryFixture(searchRoot, "same-reviewed-plan", {
      mergeToMain: true,
      removeWorktree: true,
    });
    const changedScope = createHistoryFixture(searchRoot, "changed-reviewed-scope", {
      mergeToMain: true,
      removeWorktree: true,
    });
    const changedTasks = createHistoryFixture(searchRoot, "changed-reviewed-tasks", {
      mergeToMain: true,
      removeWorktree: true,
    });
    const changedNotes = createHistoryFixture(searchRoot, "changed-reviewed-notes", {
      mergeToMain: true,
      removeWorktree: true,
    });
    const missingReviewedPlan = createHistoryFixture(searchRoot, "missing-reviewed-plan", {
      mergeToMain: true,
      removeWorktree: true,
    });
    const malformedReviewedPlan = createHistoryFixture(searchRoot, "malformed-reviewed-plan", {
      mergeToMain: true,
      removeWorktree: true,
    });

    const unchangedPlan = readCheckpointPlan(identical.repoPath, "same-reviewed-plan");
    const unchangedLifecycle = unchangedPlan.lifecycle as Record<string, unknown>;
    const reviewedFeature = String(unchangedLifecycle.reviewed_feature);
    const reviewedPlan = JSON.parse(git([
      "show",
      `${reviewedFeature}:.ai-engineering/workflow/checkpoints/same-reviewed-plan.json`,
    ], identical.repoPath)) as Record<string, unknown>;
    expect(reviewedPlan.feature).toBe(unchangedPlan.feature);
    expect(reviewedPlan.summary).toBe(unchangedPlan.summary);
    expect(
      (reviewedPlan.checkpoints as Array<Record<string, unknown>>)[0]!.tasks,
    ).toEqual((unchangedPlan.checkpoints as Array<Record<string, unknown>>)[0]!.tasks);
    expect((reviewedPlan.lifecycle as Record<string, unknown>).phase).toBe("implementation");
    expect(unchangedLifecycle.phase).toBe("ready-to-merge");
    expect((reviewedPlan.checkpoints as Array<Record<string, unknown>>)[0]!.status).toBe("pending");
    expect((unchangedPlan.checkpoints as Array<Record<string, unknown>>)[0]!.status).toBe("passed");

    const scopePlan = readCheckpointPlan(changedScope.repoPath, "changed-reviewed-scope");
    scopePlan.summary = "Scope expanded after review.";
    commitMainCheckpoint(changedScope.repoPath, "changed-reviewed-scope", scopePlan, "change reviewed scope");
    const tasksPlan = readCheckpointPlan(changedTasks.repoPath, "changed-reviewed-tasks");
    (tasksPlan.checkpoints as Array<Record<string, unknown>>)[0]!.tasks = ["Replace the reviewed task."];
    commitMainCheckpoint(changedTasks.repoPath, "changed-reviewed-tasks", tasksPlan, "change reviewed tasks");
    const notesPlan = readCheckpointPlan(changedNotes.repoPath, "changed-reviewed-notes");
    notesPlan.notes = ["Changed after review."];
    commitMainCheckpoint(changedNotes.repoPath, "changed-reviewed-notes", notesPlan, "change reviewed notes");

    const missingPlan = readCheckpointPlan(missingReviewedPlan.repoPath, "missing-reviewed-plan");
    (missingPlan.lifecycle as Record<string, unknown>).reviewed_feature = missingReviewedPlan.featureCommit;
    commitMainCheckpoint(missingReviewedPlan.repoPath, "missing-reviewed-plan", missingPlan, "point to missing reviewed plan");

    const malformedPlan = readCheckpointPlan(malformedReviewedPlan.repoPath, "malformed-reviewed-plan");
    const malformedPath = checkpointPath(malformedReviewedPlan.repoPath, "malformed-reviewed-plan");
    writeFileSync(malformedPath, "{ malformed checkpoint\n");
    git(["add", malformedPath], malformedReviewedPlan.repoPath);
    git(["commit", "--quiet", "-m", "record malformed reviewed plan"], malformedReviewedPlan.repoPath);
    const malformedCommit = git(["rev-parse", "HEAD"], malformedReviewedPlan.repoPath);
    (malformedPlan.lifecycle as Record<string, unknown>).reviewed_feature = malformedCommit;
    commitMainCheckpoint(
      malformedReviewedPlan.repoPath,
      "malformed-reviewed-plan",
      malformedPlan,
      "point to malformed reviewed plan",
    );

    const snapshot = await discoverWorkspace([realpathSync(searchRoot)], "all");
    expect(itemFor(snapshot, "same-reviewed-plan").status).toBe("closed");
    for (const slug of [
      "changed-reviewed-scope",
      "changed-reviewed-tasks",
      "changed-reviewed-notes",
      "missing-reviewed-plan",
      "malformed-reviewed-plan",
    ]) {
      expect(itemFor(snapshot, slug).status, slug).toBe("unknown");
    }
  }, 20_000);
});
