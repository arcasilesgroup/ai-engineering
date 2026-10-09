import { lstatSync, readdirSync, readFileSync, realpathSync } from "node:fs";
import { basename, isAbsolute, join, relative, sep } from "node:path";
import { spawnSync } from "node:child_process";
import { isDeepStrictEqual } from "node:util";
import {
  SLUG_PATTERN,
  type RepositoryWorktree,
  type RepositoryWorktreeInventory,
  reviewedFeatureChainProblem,
} from "../shared-worktree.ts";

export type WorkspaceStatus = "needs-review" | "in-progress" | "blocked" | "closed" | "unknown";
export type WorkspaceFilter = "all" | WorkspaceStatus;

export interface WorkspaceItem {
  slug: string;
  branch: string | null;
  worktreePath: string | null;
  status: WorkspaceStatus;
  dirty: boolean | null;
  errors?: string[];
}

export interface WorkspaceHistoryItem extends WorkspaceItem {
  status: "closed";
}

export interface WorkspaceProject {
  root: string;
  items: WorkspaceItem[];
  history: WorkspaceHistoryItem[];
  errors: string[];
}

interface GitResult {
  status: number;
  stdout: string;
  stderr: string;
}

interface GitStatus {
  dirty: boolean | null;
  conflict: boolean;
  error?: string;
}

interface Lifecycle {
  phase: string;
  planApproval: string;
  appReview: string;
  reviewedMain: string | null;
  reviewedFeature: string | null;
}

interface Checkpoint {
  checkpoints: Record<string, unknown>[];
  lifecycle: Lifecycle;
  planPayload: Record<string, unknown>;
}

interface ReadCheckpoint {
  checkpoint?: Checkpoint;
  error?: string;
}

const COMMIT_PATTERN = /^(?:[0-9a-f]{40}|[0-9a-f]{64})$/;
const PLAN_FIELDS = [
  "feature",
  "slug",
  "summary",
  "plain_summary",
  "gating",
  "assumptions",
  "notes",
  "new_dependencies",
  "dependencies",
] as const;
const CHECKPOINT_PLAN_FIELDS = [
  "id",
  "title",
  "goal",
  "plain",
  "simple",
  "size",
  "builds_on",
  "tasks",
  "files",
  "acceptance",
  "verify",
  "ui",
  "new_dependencies",
  "dependencies",
] as const;
const LIFECYCLE_PHASES = new Set([
  "approval-before-start",
  "awaiting-plan-approval",
  "implementation",
  "blocked",
  "awaiting-app-review",
  "ready-to-merge",
  "complete",
]);

function runGit(repository: string, args: string[]): GitResult {
  const result = spawnSync("git", args, {
    cwd: repository,
    encoding: "utf8",
    env: {
      ...process.env,
      GIT_CONFIG_GLOBAL: "/dev/null",
      GIT_CONFIG_SYSTEM: "/dev/null",
      GIT_CONFIG_NOSYSTEM: "1",
      GIT_OPTIONAL_LOCKS: "0",
      GIT_TERMINAL_PROMPT: "0",
    },
  });
  return {
    status: result.status ?? 1,
    stdout: result.stdout ?? "",
    stderr: result.stderr ?? result.error?.message ?? "",
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function immutablePlanPayload(value: unknown): Record<string, unknown> | null {
  if (
    !isRecord(value) ||
    !Array.isArray(value.checkpoints) ||
    !value.checkpoints.every(isRecord)
  ) return null;

  const copyFields = (record: Record<string, unknown>, fields: readonly string[]) => {
    const payload: Record<string, unknown> = {};
    for (const field of fields) {
      if (Object.prototype.hasOwnProperty.call(record, field)) payload[field] = record[field];
    }
    return payload;
  };

  return {
    ...copyFields(value, PLAN_FIELDS),
    checkpoints: value.checkpoints.map((checkpoint) => copyFields(checkpoint, CHECKPOINT_PLAN_FIELDS)),
  };
}

function isWithin(root: string, path: string): boolean {
  const pathFromRoot = relative(root, path);
  return pathFromRoot === "" || (
    pathFromRoot !== ".." &&
    !pathFromRoot.startsWith(`..${sep}`) &&
    !isAbsolute(pathFromRoot)
  );
}

function gitError(result: GitResult, command: string): string | undefined {
  if (result.status === 0 && result.stderr.trim() === "") return undefined;
  return result.stderr.trim() || `git ${command} exited ${result.status}`;
}

function readGitStatus(worktreePath: string): GitStatus {
  const status = runGit(worktreePath, [
    "-c",
    "core.fsmonitor=false",
    "-c",
    "core.untrackedCache=false",
    "--no-optional-locks",
    "status",
    "--porcelain=v1",
    "--untracked-files=all",
    "-z",
  ]);
  const error = gitError(status, "status");
  if (error !== undefined) return { dirty: null, conflict: false, error };

  const records = status.stdout.split("\0").filter(Boolean);
  let conflict = false;
  for (let index = 0; index < records.length; ) {
    const record = records[index];
    if (record === undefined || record.length < 4 || record[2] !== " ") {
      return { dirty: null, conflict: false, error: "Git returned an unreadable status record" };
    }
    const state = record.slice(0, 2);
    conflict ||= state.includes("U") || state === "AA" || state === "DD";
    index += state.includes("R") || state.includes("C") ? 2 : 1;
    if (index > records.length) return { dirty: null, conflict: false, error: "Git returned an incomplete rename status" };
  }
  return {
    dirty: records.length > 0,
    conflict,
  };
}

function readCheckpoint(path: string, worktreePath: string, slug: string): ReadCheckpoint {
  try {
    const stat = lstatSync(path);
    const canonicalPath = realpathSync(path);
    const relativePath = relative(worktreePath, canonicalPath);
    if (
      !stat.isFile() ||
      stat.isSymbolicLink() ||
      relativePath === "" ||
      relativePath === ".." ||
      relativePath.startsWith(`..${sep}`) ||
      isAbsolute(relativePath)
    ) {
      return { error: "checkpoint is not a worktree-local file" };
    }
    const parsed: unknown = JSON.parse(readFileSync(path, "utf8"));
    const checkpoint = validateCheckpoint(parsed, slug);
    return checkpoint === null
      ? { error: "checkpoint is malformed, contradictory, or does not match this worktree" }
      : { checkpoint };
  } catch (error) {
    return {
      error: `checkpoint read failed: ${error instanceof Error ? error.message : String(error)}`,
    };
  }
}

function validateCheckpoint(value: unknown, slug: string): Checkpoint | null {
  if (
    !isRecord(value) ||
    value.slug !== slug ||
    !Array.isArray(value.checkpoints) ||
    value.checkpoints.length === 0 ||
    !isRecord(value.lifecycle)
  ) return null;

  const lifecycle = value.lifecycle;
  const phase = lifecycle.phase;
  const lifecycleKeys = Object.keys(lifecycle);
  if (
    typeof phase !== "string" ||
    !LIFECYCLE_PHASES.has(phase) ||
    lifecycleKeys.some((key) => !["phase", "plan_approval", "app_review", "reviewed_main", "reviewed_feature"].includes(key)) ||
    !["pending", "approved"].includes(String(lifecycle.plan_approval)) ||
    !["not-started", "pending", "approved"].includes(String(lifecycle.app_review)) ||
    (lifecycle.reviewed_main !== null &&
      (typeof lifecycle.reviewed_main !== "string" || !COMMIT_PATTERN.test(lifecycle.reviewed_main))) ||
    (lifecycle.reviewed_feature !== undefined &&
      lifecycle.reviewed_feature !== null &&
      (typeof lifecycle.reviewed_feature !== "string" || !COMMIT_PATTERN.test(lifecycle.reviewed_feature)))
  ) return null;

  const reviewedMain = typeof lifecycle.reviewed_main === "string" ? lifecycle.reviewed_main : null;
  const reviewedFeature = typeof lifecycle.reviewed_feature === "string" ? lifecycle.reviewed_feature : null;
  const hasReviewCommits = reviewedMain !== null && reviewedFeature !== null;
  if ((reviewedMain === null) !== (reviewedFeature === null)) return null;

  if (
    (phase === "awaiting-plan-approval" &&
      (lifecycle.plan_approval !== "pending" || lifecycle.app_review !== "not-started" || hasReviewCommits)) ||
    (phase === "approval-before-start" &&
      (lifecycle.plan_approval !== "approved" || lifecycle.app_review !== "not-started" || hasReviewCommits)) ||
    (phase === "implementation" &&
      (lifecycle.plan_approval !== "approved" || lifecycle.app_review !== "not-started" || hasReviewCommits)) ||
    (phase === "awaiting-app-review" &&
      (lifecycle.plan_approval !== "approved" || lifecycle.app_review !== "pending" || !hasReviewCommits)) ||
    (phase === "ready-to-merge" &&
      (lifecycle.plan_approval !== "approved" || lifecycle.app_review !== "approved" || !hasReviewCommits)) ||
    (phase === "complete" &&
      (lifecycle.plan_approval !== "approved" || lifecycle.app_review !== "approved" || !hasReviewCommits)) ||
    (phase === "blocked" &&
      (lifecycle.plan_approval === "pending"
        ? lifecycle.app_review !== "not-started" || hasReviewCommits
        : lifecycle.app_review === "not-started"
          ? hasReviewCommits
          : !hasReviewCommits))
  ) return null;

  const checkpoints: Record<string, unknown>[] = [];
  for (const checkpoint of value.checkpoints) {
    if (!isRecord(checkpoint) || !["pending", "passed", "blocked"].includes(String(checkpoint.status))) return null;
    if (!isRecord(checkpoint.gates)) return null;
    const gates = checkpoint.gates;
    const gateNames = ["behavior", "ui", "review"];
    if (!gateNames.every((name) => {
      const gate = gates[name];
      return isRecord(gate) && ["pending", "failed", "passed", "n/a", "blocked"].includes(String(gate.status));
    })) return null;
    if (
      checkpoint.files !== undefined &&
      (!Array.isArray(checkpoint.files) || checkpoint.files.some((file) => typeof file !== "string"))
    ) return null;
    const hasBlockedEvidence = checkpoint.status === "blocked" || gateNames.some((name) => {
      const gate = gates[name];
      return isRecord(gate) && gate.status === "blocked";
    });
    if (hasBlockedEvidence && phase !== "blocked") return null;
    if (checkpoint.status === "passed" && !gatesComplete([checkpoint]) && phase !== "awaiting-app-review") return null;
    checkpoints.push(checkpoint);
  }
  if ((phase === "ready-to-merge" || phase === "complete") && !gatesComplete(checkpoints)) return null;

  const planPayload = immutablePlanPayload(value);
  if (planPayload === null) return null;

  return {
    checkpoints,
    planPayload,
    lifecycle: {
      phase,
      planApproval: String(lifecycle.plan_approval),
      appReview: String(lifecycle.app_review),
      reviewedMain,
      reviewedFeature,
    },
  };
}

function gatesComplete(checkpoints: Record<string, unknown>[]): boolean {
  return checkpoints.every((checkpoint) => {
    if (checkpoint.status !== "passed" || !isRecord(checkpoint.gates)) return false;
    const gates = checkpoint.gates;
    return ["behavior", "ui", "review"].every((name) => {
      const gate = gates[name];
      return isRecord(gate) && (gate.status === "passed" || gate.status === "n/a");
    });
  });
}

function readMainCommit(repository: string, projectErrors: string[]): string | null {
  const result = runGit(repository, ["rev-parse", "--verify", "refs/heads/main^{commit}"]);
  const error = gitError(result, "rev-parse refs/heads/main");
  if (error !== undefined) {
    projectErrors.push(error);
    return null;
  }
  const commit = result.stdout.trim();
  if (!COMMIT_PATTERN.test(commit)) {
    projectErrors.push("Git returned an invalid local main commit");
    return null;
  }
  return commit;
}

function isAncestor(repository: string, ancestor: string, descendant: string): boolean | null {
  const result = runGit(repository, ["merge-base", "--is-ancestor", ancestor, descendant]);
  if (result.status === 0 && result.stderr.trim() === "") return true;
  if (result.status === 1 && result.stderr.trim() === "") return false;
  return null;
}

function readFeatureBranches(
  repository: string,
  projectErrors: string[],
): { branches: Set<string>; readable: boolean } {
  const result = runGit(repository, ["for-each-ref", "--format=%(refname:short)", "refs/heads/feat"]);
  const error = gitError(result, "for-each-ref refs/heads/feat");
  if (error !== undefined) {
    projectErrors.push(error);
    return { branches: new Set(), readable: false };
  }
  return {
    branches: new Set(result.stdout.split("\n").map((branch) => branch.trim()).filter(Boolean)),
    readable: true,
  };
}

function unknownItem(
  slug: string,
  branch: string | null,
  worktreePath: string | null,
  dirty: boolean | null,
  error?: string,
): WorkspaceItem {
  return {
    slug,
    branch,
    worktreePath,
    status: "unknown",
    dirty,
    ...(error === undefined ? {} : { errors: [error] }),
  };
}

function classifyWorktree(
  repository: string,
  entry: RepositoryWorktree,
  mainCommit: string | null,
  featureBranches: Set<string>,
  projectErrors: string[],
): WorkspaceItem {
  const branch = entry.branch;
  const slug = branch?.startsWith("feat/") ? branch.slice("feat/".length) : entry.slug || basename(entry.path);
  if (entry.prunable) {
    return unknownItem(slug, branch, entry.path, null, "Git marks this worktree prunable");
  }

  const worktreeStatus = readGitStatus(entry.path);
  if (worktreeStatus.error !== undefined) {
    projectErrors.push(`${slug}: Git status read failed: ${worktreeStatus.error}`);
    return unknownItem(slug, branch, entry.path, null, `Git status read failed: ${worktreeStatus.error}`);
  }
  if (entry.detached) {
    return unknownItem(slug, branch, entry.path, worktreeStatus.dirty, "detached worktree");
  }
  if (worktreeStatus.conflict) {
    return { slug, branch, worktreePath: entry.path, status: "blocked", dirty: true };
  }
  if (branch === null || !branch.startsWith("feat/") || !SLUG_PATTERN.test(slug) || /\p{C}/u.test(slug)) {
    return unknownItem(slug, branch, entry.path, worktreeStatus.dirty, "worktree is not on a valid feature branch");
  }
  if (!featureBranches.has(branch)) {
    return unknownItem(slug, branch, entry.path, worktreeStatus.dirty, "feature branch is missing from local Git refs");
  }

  const checkpointPath = join(entry.path, ".ai-engineering", "workflow", "checkpoints", `${slug}.json`);
  const read = readCheckpoint(checkpointPath, entry.path, slug);
  if (read.checkpoint === undefined) {
    projectErrors.push(`${slug}: ${read.error ?? "checkpoint is unreadable"}`);
    return unknownItem(slug, branch, entry.path, worktreeStatus.dirty, read.error ?? "checkpoint is unreadable");
  }
  const { lifecycle } = read.checkpoint;
  if (lifecycle.phase === "blocked") {
    return { slug, branch, worktreePath: entry.path, status: "blocked", dirty: worktreeStatus.dirty };
  }
  if (lifecycle.phase === "approval-before-start") {
    return unknownItem(slug, branch, entry.path, worktreeStatus.dirty, "approval-before-start checkpoint has a registered worktree");
  }
  if (lifecycle.phase === "awaiting-plan-approval") {
    if (lifecycle.reviewedMain !== null && lifecycle.reviewedMain !== mainCommit) {
      return unknownItem(slug, branch, entry.path, worktreeStatus.dirty, "lifecycle reviewed_main is stale");
    }
    return { slug, branch, worktreePath: entry.path, status: "needs-review", dirty: worktreeStatus.dirty };
  }
  if (lifecycle.phase === "awaiting-app-review") {
    if (
      mainCommit === null ||
      lifecycle.reviewedMain !== mainCommit ||
      lifecycle.reviewedFeature === null
    ) {
      return unknownItem(slug, branch, entry.path, worktreeStatus.dirty, "app-review lifecycle evidence is missing or stale");
    }
    const featureTipRead = runGit(repository, ["rev-parse", "--verify", `refs/heads/${branch}^{commit}`]);
    const featureTipError = gitError(featureTipRead, `rev-parse refs/heads/${branch}`);
    if (featureTipError !== undefined) {
      projectErrors.push(`${slug}: ${featureTipError}`);
      return unknownItem(slug, branch, entry.path, worktreeStatus.dirty, featureTipError);
    }
    const featureTip = featureTipRead.stdout.trim();
    if (!COMMIT_PATTERN.test(featureTip)) {
      return unknownItem(slug, branch, entry.path, worktreeStatus.dirty, "Git returned an invalid feature commit");
    }
    const chainProblem = reviewedFeatureChainProblem(
      repository,
      slug,
      lifecycle.reviewedMain,
      lifecycle.reviewedFeature,
      featureTip,
      "awaiting-app-review",
    );
    if (chainProblem !== null) {
      projectErrors.push(`${slug}: ${chainProblem}`);
      return unknownItem(slug, branch, entry.path, worktreeStatus.dirty, chainProblem);
    }
    return { slug, branch, worktreePath: entry.path, status: "needs-review", dirty: worktreeStatus.dirty };
  }
  if (lifecycle.phase !== "implementation" && lifecycle.phase !== "ready-to-merge") {
    return unknownItem(slug, branch, entry.path, worktreeStatus.dirty, "checkpoint phase is not an active lifecycle state");
  }

  const featureTipRead = runGit(repository, ["rev-parse", "--verify", `refs/heads/${branch}^{commit}`]);
  const featureTipError = gitError(featureTipRead, `rev-parse refs/heads/${branch}`);
  if (featureTipError !== undefined) {
    projectErrors.push(`${slug}: ${featureTipError}`);
    return unknownItem(slug, branch, entry.path, worktreeStatus.dirty, featureTipError);
  }
  const featureTip = featureTipRead.stdout.trim();
  if (!COMMIT_PATTERN.test(featureTip)) {
    return unknownItem(slug, branch, entry.path, worktreeStatus.dirty, "Git returned an invalid feature commit");
  }
  if (lifecycle.phase === "ready-to-merge") {
    if (mainCommit === null || lifecycle.reviewedMain !== mainCommit) {
      return unknownItem(slug, branch, entry.path, worktreeStatus.dirty, "lifecycle reviewed_main is stale or unreadable");
    }
    const reviewedFeature = lifecycle.reviewedFeature;
    if (reviewedFeature === null) {
      return unknownItem(slug, branch, entry.path, worktreeStatus.dirty, "lifecycle reviewed_feature is missing");
    }
    const chainProblem = reviewedFeatureChainProblem(
      repository,
      slug,
      lifecycle.reviewedMain,
      reviewedFeature,
      featureTip,
    );
    if (chainProblem !== null) {
      projectErrors.push(`${slug}: ${chainProblem}`);
      return unknownItem(slug, branch, entry.path, worktreeStatus.dirty, chainProblem);
    }
  }
  return { slug, branch, worktreePath: entry.path, status: "in-progress", dirty: worktreeStatus.dirty };
}

function readMainCheckpoint(repository: string, path: string, slug: string): ReadCheckpoint {
  if (path !== `.ai-engineering/workflow/checkpoints/${slug}.json`) {
    return { error: "main checkpoint is not at its canonical slug path" };
  }
  const result = runGit(repository, ["show", `refs/heads/main:${path}`]);
  const error = gitError(result, `show refs/heads/main:${path}`);
  if (error !== undefined) return { error };
  try {
    const parsed: unknown = JSON.parse(result.stdout);
    const checkpoint = validateCheckpoint(parsed, slug);
    return checkpoint === null
      ? { error: "main checkpoint is malformed, contradictory, or does not match its filename" }
      : { checkpoint };
  } catch (error) {
    return { error: `main checkpoint is malformed: ${error instanceof Error ? error.message : String(error)}` };
  }
}

function readReviewedCheckpoint(repository: string, reviewedFeature: string, slug: string): ReadCheckpoint {
  const path = `.ai-engineering/workflow/checkpoints/${slug}.json`;
  const result = runGit(repository, ["show", `${reviewedFeature}:${path}`]);
  const error = gitError(result, `show ${reviewedFeature}:${path}`);
  if (error !== undefined) return { error: `reviewed_feature checkpoint is missing or unreadable: ${error}` };
  try {
    const parsed: unknown = JSON.parse(result.stdout);
    const checkpoint = validateCheckpoint(parsed, slug);
    return checkpoint === null
      ? { error: "reviewed_feature checkpoint is malformed or does not match its slug" }
      : { checkpoint };
  } catch (error) {
    return { error: `reviewed_feature checkpoint is malformed: ${error instanceof Error ? error.message : String(error)}` };
  }
}

function hasRegisteredWorktreeForSlug(
  registeredWorktrees: RepositoryWorktree[],
  worktreesRoot: string,
  slug: string,
): boolean {
  const expectedPath = join(worktreesRoot, slug);
  return registeredWorktrees.some((entry) =>
    entry.branch === `feat/${slug}` ||
    entry.slug === slug ||
    entry.path === expectedPath ||
    entry.registeredPath === expectedPath
  );
}

function closedHistoryItem(
  repository: string,
  slug: string,
  checkpoint: Checkpoint,
  mainCommit: string | null,
  registeredWorktrees: RepositoryWorktree[],
  worktreesRoot: string,
  areFeatureBranchesReadable: boolean,
  featureBranches: Set<string>,
  projectErrors: string[],
): WorkspaceHistoryItem | null {
  const { lifecycle } = checkpoint;
  if (
    mainCommit === null ||
    !areFeatureBranchesReadable ||
    (lifecycle.phase !== "complete" && lifecycle.phase !== "ready-to-merge") ||
    lifecycle.planApproval !== "approved" ||
    lifecycle.appReview !== "approved" ||
    lifecycle.reviewedMain === null ||
    lifecycle.reviewedFeature === null ||
    lifecycle.reviewedMain === lifecycle.reviewedFeature ||
    hasRegisteredWorktreeForSlug(registeredWorktrees, worktreesRoot, slug)
  ) return null;

  const mainContainsReview = isAncestor(repository, lifecycle.reviewedMain, mainCommit);
  const mainContainsFeature = isAncestor(repository, lifecycle.reviewedFeature, mainCommit);
  if (mainContainsReview === null || mainContainsFeature === null) {
    projectErrors.push(`${slug}: Git could not verify local-main merge evidence`);
    return null;
  }
  if (mainContainsReview !== true || mainContainsFeature !== true) return null;

  const reviewedCheckpoint = readReviewedCheckpoint(repository, lifecycle.reviewedFeature, slug);
  if (reviewedCheckpoint.checkpoint === undefined) {
    projectErrors.push(`${slug}: ${reviewedCheckpoint.error ?? "reviewed_feature checkpoint is unreadable"}`);
    return null;
  }
  if (!isDeepStrictEqual(reviewedCheckpoint.checkpoint.planPayload, checkpoint.planPayload)) {
    projectErrors.push(`${slug}: local-main checkpoint plan differs from reviewed_feature`);
    return null;
  }

  if (featureBranches.has(`feat/${slug}`)) {
    const featureBranch = runGit(repository, ["rev-parse", "--verify", `refs/heads/feat/${slug}^{commit}`]);
    const featureBranchError = gitError(featureBranch, `rev-parse refs/heads/feat/${slug}`);
    if (featureBranchError !== undefined) {
      projectErrors.push(`${slug}: ${featureBranchError}`);
      return null;
    }
    const mainContainsFeatureTip = isAncestor(repository, featureBranch.stdout.trim(), mainCommit);
    if (mainContainsFeatureTip === null) {
      projectErrors.push(`${slug}: Git could not verify the local feature branch merge`);
      return null;
    }
    if (mainContainsFeatureTip !== true) return null;
  }

  return {
    slug,
    branch: `feat/${slug}`,
    worktreePath: null,
    status: "closed",
    dirty: null,
  };
}

function readClosedHistory(
  repository: string,
  mainCommit: string | null,
  registeredWorktrees: RepositoryWorktree[],
  worktreesRoot: string,
  areFeatureBranchesReadable: boolean,
  featureBranches: Set<string>,
  itemsBySlug: Map<string, WorkspaceItem>,
  projectErrors: string[],
): WorkspaceHistoryItem[] {
  if (mainCommit === null) return [];
  const listed = runGit(repository, [
    "ls-tree",
    "-rz",
    "--name-only",
    "refs/heads/main",
    ".ai-engineering/workflow/checkpoints",
  ]);
  const listError = gitError(listed, "ls-tree refs/heads/main checkpoints");
  if (listError !== undefined) {
    projectErrors.push(listError);
    return [];
  }

  const history: WorkspaceHistoryItem[] = [];
  const pathsBySlug = new Map<string, string[]>();
  for (const path of listed.stdout.split("\0").filter((candidate) => candidate.endsWith(".json"))) {
    const slug = basename(path, ".json");
    if (!SLUG_PATTERN.test(slug) || /\p{C}/u.test(slug)) continue;
    pathsBySlug.set(slug, [...(pathsBySlug.get(slug) ?? []), path]);
  }

  for (const [slug, paths] of pathsBySlug) {
    const canonicalPath = `.ai-engineering/workflow/checkpoints/${slug}.json`;
    if (paths.length !== 1 || paths[0] !== canonicalPath) {
      const reason = "main checkpoint is misplaced or duplicated";
      projectErrors.push(`${slug}: ${reason}`);
      const existing = itemsBySlug.get(slug);
      if (existing !== undefined) {
        existing.status = "unknown";
        existing.errors = [...(existing.errors ?? []), reason];
      } else {
        itemsBySlug.set(slug, unknownItem(slug, `feat/${slug}`, null, null, reason));
      }
      continue;
    }
    const path = paths[0]!;
    const read = readMainCheckpoint(repository, path, slug);
    if (read.error !== undefined) projectErrors.push(`${slug}: ${read.error}`);
    if (read.checkpoint?.lifecycle.phase === "approval-before-start") {
      const hasRegisteredWorktree = hasRegisteredWorktreeForSlug(registeredWorktrees, worktreesRoot, slug);
      if (!hasRegisteredWorktree && !featureBranches.has(`feat/${slug}`)) {
        const item: WorkspaceItem = {
          slug,
          branch: `feat/${slug}`,
          worktreePath: null,
          status: "needs-review",
          dirty: null,
        };
        itemsBySlug.set(slug, item);
        continue;
      }
    }
    const closed = read.checkpoint === undefined
      ? null
      : closedHistoryItem(
        repository,
        slug,
        read.checkpoint,
        mainCommit,
        registeredWorktrees,
        worktreesRoot,
        areFeatureBranchesReadable,
        featureBranches,
        projectErrors,
      );
    if (closed !== null) {
      history.push(closed);
      itemsBySlug.set(slug, closed);
      continue;
    }

    const existing = itemsBySlug.get(slug);
    const reason = read.error ?? "checkpoint has no complete Git merge evidence or a feature worktree remains registered";
    if (existing !== undefined) {
      existing.status = "unknown";
      existing.errors = [...(existing.errors ?? []), reason];
    } else {
      itemsBySlug.set(slug, unknownItem(slug, `feat/${slug}`, null, null, reason));
    }
  }
  return history;
}

function readApprovalProjections(
  inventory: RepositoryWorktreeInventory,
  featureBranches: Set<string>,
  areFeatureBranchesReadable: boolean,
  itemsBySlug: Map<string, WorkspaceItem>,
  projectErrors: string[],
): void {
  const directory = join(inventory.repositoryRoot, ".ai-eng-lifecycle");
  try {
    const directoryStat = lstatSync(directory);
    if (!directoryStat.isDirectory() || directoryStat.isSymbolicLink()) {
      projectErrors.push("approval lifecycle directory is not a repository-local directory");
      return;
    }
  } catch (error) {
    if (isRecord(error) && error.code === "ENOENT") return;
    projectErrors.push(`approval lifecycle directory read failed: ${error instanceof Error ? error.message : String(error)}`);
    return;
  }

  let filenames: string[];
  try {
    filenames = readdirSync(directory).filter((filename) => filename.endsWith(".json"));
  } catch (error) {
    projectErrors.push(`approval lifecycle directory read failed: ${error instanceof Error ? error.message : String(error)}`);
    return;
  }

  for (const filename of filenames) {
    const slug = filename.slice(0, -".json".length);
    if (!SLUG_PATTERN.test(slug) || /\p{C}/u.test(slug)) continue;
    const path = join(directory, filename);
    let record: unknown;
    try {
      const stat = lstatSync(path);
      const canonicalPath = realpathSync(path);
      if (!stat.isFile() || stat.isSymbolicLink() || !isWithin(inventory.repositoryRoot, canonicalPath)) {
        const error = "approval projection is not a repository-local file";
        projectErrors.push(`${slug}: ${error}`);
        itemsBySlug.set(slug, unknownItem(slug, `feat/${slug}`, null, null, error));
        continue;
      }
      record = JSON.parse(readFileSync(path, "utf8"));
    } catch (error) {
      const detail = `approval projection read failed: ${error instanceof Error ? error.message : String(error)}`;
      projectErrors.push(`${slug}: ${detail}`);
      itemsBySlug.set(
        slug,
        unknownItem(slug, `feat/${slug}`, null, null, detail),
      );
      continue;
    }

    const expectedWorktreePath = join(inventory.worktreesRoot, slug);
    const isVerified = isRecord(record)
      && Object.keys(record).length === 8
      && record.schema_version === 1
      && record.slug === slug
      && record.state === "approval-before-start"
      && isIsoTimestamp(record.timestamp)
      && record.branch === `feat/${slug}`
      && record.repository === inventory.repositoryRoot
      && record.worktrees_dir === inventory.worktreesRoot
      && record.worktree_path === expectedWorktreePath;
    const hasRegisteredWorktree = inventory.worktrees.some((entry) => entry.branch === `feat/${slug}`);
    const hasLocalBranch = featureBranches.has(`feat/${slug}`);
    const existing = itemsBySlug.get(slug);

    if (
      isVerified &&
      areFeatureBranchesReadable &&
      !hasRegisteredWorktree &&
      !hasLocalBranch &&
      existing === undefined
    ) {
      itemsBySlug.set(slug, {
        slug,
        branch: `feat/${slug}`,
        worktreePath: null,
        status: "needs-review",
        dirty: null,
      });
      continue;
    }

    const reason = isVerified && !areFeatureBranchesReadable
      ? "approval projection cannot be verified because local feature refs are unreadable"
      : isVerified
        ? "approval projection conflicts with local Git worktree or branch evidence"
        : "approval projection is malformed or does not match this repository";
    projectErrors.push(`${slug}: ${reason}`);
    if (existing !== undefined) {
      existing.status = "unknown";
      existing.errors = [...(existing.errors ?? []), reason];
    } else {
      itemsBySlug.set(slug, unknownItem(slug, `feat/${slug}`, null, null, reason));
    }
  }
}

function isIsoTimestamp(value: unknown): value is string {
  if (typeof value !== "string") return false;
  const parsed = Date.parse(value);
  if (!Number.isFinite(parsed)) return false;
  try {
    return new Date(parsed).toISOString() === value;
  } catch {
    return false;
  }
}

export function classifyRepository(
  inventory: RepositoryWorktreeInventory,
): Pick<WorkspaceProject, "items" | "history" | "errors"> {
  const projectErrors: string[] = [];
  const mainCommit = readMainCommit(inventory.repositoryRoot, projectErrors);
  const featureBranchRead = readFeatureBranches(inventory.repositoryRoot, projectErrors);
  const featureBranches = featureBranchRead.branches;
  const itemsBySlug = new Map<string, WorkspaceItem>();

  for (const entry of inventory.worktrees) {
    if (!isWithin(inventory.worktreesRoot, entry.registeredPath)) continue;
    if (!isWithin(inventory.worktreesRoot, entry.path)) {
      projectErrors.push("a registered worktree resolves outside its configured worktrees directory");
      continue;
    }
    if (entry.path === inventory.repositoryRoot) continue;
    const item = classifyWorktree(inventory.repositoryRoot, entry, mainCommit, featureBranches, projectErrors);
    itemsBySlug.set(item.slug, item);
  }

  const history = readClosedHistory(
    inventory.repositoryRoot,
    mainCommit,
    inventory.worktrees,
    inventory.worktreesRoot,
    featureBranchRead.readable,
    featureBranches,
    itemsBySlug,
    projectErrors,
  );

  for (const branch of featureBranches) {
    const slug = branch.slice("feat/".length);
    if (!SLUG_PATTERN.test(slug) || /\p{C}/u.test(slug) || itemsBySlug.has(slug)) continue;
    itemsBySlug.set(slug, unknownItem(slug, branch, null, null, "feature branch has no registered worktree"));
  }

  readApprovalProjections(inventory, featureBranches, featureBranchRead.readable, itemsBySlug, projectErrors);

  return {
    items: [...itemsBySlug.values()].sort((left, right) => left.slug.localeCompare(right.slug)),
    history: history.sort((left, right) => left.slug.localeCompare(right.slug)),
    errors: projectErrors,
  };
}
