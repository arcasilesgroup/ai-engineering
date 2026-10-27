import { randomUUID } from "node:crypto";
import {
  existsSync,
  lstatSync,
  mkdirSync,
  readFileSync,
  realpathSync,
  renameSync,
  unlinkSync,
  writeFileSync,
} from "node:fs";
import { basename, dirname, isAbsolute, join, relative, resolve, sep } from "node:path";
import { isDeepStrictEqual } from "node:util";
import { loadConfig, printable } from "../env.ts";
import { assertCheckpointTransition, parseCheckpoint, readCheckpoint, serializeCheckpoint, type Checkpoint, type CheckpointContext } from "../workflow/checkpoint.ts";
import { resolveContext } from "./context.ts";
import { runGit, type GitResult } from "./run.ts";

interface Worktree {
  path: string;
  branch: string | null;
}

interface FileStatus {
  paths: string[];
  untracked: string[];
  detail?: string;
}

interface ReadySource {
  path: string;
  branch: string;
  branchRef: string;
  baseRef: string;
  reviewedBase: string;
  reviewedFeature: string;
  featureTip: string;
  checkpointPath: string;
  checkpointRelative: string;
  checkpoint: Checkpoint;
}

const SHA = /^(?:[0-9a-f]{40}|[0-9a-f]{64})$/;

function git(cwd: string, args: string[]): GitResult {
  return runGit(args, { cwd, isolated: true });
}

function canonical(path: string): string {
  try {
    return realpathSync(path);
  } catch {
    return resolve(path);
  }
}

function fullCommit(cwd: string, revision: string): string | null {
  const result = git(cwd, ["rev-parse", "--verify", `${revision}^{commit}`]);
  const commit = result.stdout.trim();
  return result.status === 0 && result.stderr.trim() === "" && SHA.test(commit) ? commit : null;
}

function fullObject(cwd: string, revision: string): string | null {
  const result = git(cwd, ["rev-parse", "--verify", revision]);
  const object = result.stdout.trim();
  return result.status === 0 && result.stderr.trim() === "" && SHA.test(object) ? object : null;
}

function worktreeList(repo: string): { entries: Worktree[] } | { detail: string } {
  const listed = git(repo, ["worktree", "list", "--porcelain"]);
  if (listed.status !== 0 || listed.stderr.trim() !== "") {
    return { detail: listed.stderr.trim() || `git worktree list exited ${listed.status}` };
  }
  const entries: Worktree[] = [];
  for (const block of listed.stdout.split("\n\n")) {
    if (block.trim() === "") continue;
    const pathLine = block.split("\n").find((line) => line.startsWith("worktree "));
    if (pathLine === undefined) return { detail: `unreadable worktree entry ${JSON.stringify(printable(block))}` };
    const branchLine = block.split("\n").find((line) => line.startsWith("branch "));
    entries.push({
      path: pathLine.slice("worktree ".length),
      branch: branchLine?.slice("branch ".length) ?? null,
    });
  }
  return { entries };
}

function parseStatus(cwd: string): FileStatus {
  const status = git(cwd, ["--no-optional-locks", "status", "--porcelain", "--untracked-files=all", "-z"]);
  if (status.status !== 0 || status.stderr.trim() !== "") {
    return { paths: [], untracked: [], detail: status.stderr.trim() || `git status exited ${status.status}` };
  }
  const paths: string[] = [];
  const untracked: string[] = [];
  const tokens = status.stdout.split("\0");
  for (let index = 0; index < tokens.length; ) {
    const record = tokens[index] ?? "";
    if (record === "") {
      index += 1;
      continue;
    }
    if (record.length < 4 || record[2] !== " ") {
      return { paths: [], untracked: [], detail: "unreadable git status record" };
    }
    const path = record.slice(3);
    paths.push(path);
    if (record.startsWith("?? ")) untracked.push(path);
    const isRename = record.slice(0, 2).split("").some((flag) => flag === "R" || flag === "C");
    if (isRename) {
      const source = tokens[index + 1];
      if (source === undefined || source === "") {
        return { paths: [], untracked: [], detail: "unreadable renamed git status record" };
      }
      paths.push(source);
      index += 1;
    }
    index += 1;
  }
  return { paths: [...new Set(paths)], untracked: [...new Set(untracked)] };
}

function operationState(path: string): string | null {
  for (const name of ["rebase-merge", "rebase-apply", "MERGE_HEAD"]) {
    const location = git(path, ["rev-parse", "--git-path", name]);
    if (location.status !== 0 || location.stderr.trim() !== "") {
      return `cannot read git ${name} state (${location.stderr.trim() || `git exited ${location.status}`})`;
    }
    const gitPath = location.stdout.trim();
    if (gitPath === "") return `cannot read git ${name} state path`;
    if (existsSync(resolve(path, gitPath))) return `${name} is in progress`;
  }
  return null;
}

function worktreesRoot(repo: string): string {
  const configured = loadConfig(repo).git?.["worktrees_dir"];
  if (typeof configured === "string" && configured.trim() !== "") {
    return canonical(resolve(repo, configured.trim()));
  }
  return `${repo}.worktrees`;
}

function safeCheckpointPath(path: string, slug: string): string | null {
  const checkpointPath = join(path, ".ai-engineering", "workflow", "checkpoints", `${slug}.json`);
  try {
    const stat = lstatSync(checkpointPath);
    const resolved = realpathSync(checkpointPath);
    const relativePath = relative(canonical(path), resolved);
    if (
      !stat.isFile() ||
      stat.isSymbolicLink() ||
      relativePath === "" ||
      relativePath === ".." ||
      relativePath.startsWith(`..${sep}`) ||
      isAbsolute(relativePath)
    ) return null;
    return checkpointPath;
  } catch {
    return null;
  }
}

function readySource(entry: Worktree, slug: string): ReadySource | null {
  if (entry.branch === null || !existsSync(entry.path)) return null;
  const checkpointPath = safeCheckpointPath(entry.path, slug);
  if (checkpointPath === null) return null;
  let context;
  try {
    context = resolveContext(entry.path);
  } catch {
    return null;
  }
  if (context.base === null) return null;
  const baseRef = `refs/heads/${context.base}`;
  const checkpointContext = { repoPath: entry.path, slug, baseRef };
  let checkpoint: Checkpoint;
  try {
    checkpoint = readCheckpoint(checkpointPath, checkpointContext);
  } catch {
    return null;
  }
  if (
    checkpoint.lifecycle.phase !== "ready-to-merge" ||
    checkpoint.lifecycle.plan_approval !== "approved" ||
    checkpoint.lifecycle.app_review !== "approved" ||
    typeof checkpoint.lifecycle.reviewed_base !== "string" ||
    typeof checkpoint.lifecycle.reviewed_feature !== "string"
  ) return null;
  return {
    path: entry.path,
    branch: entry.branch.slice("refs/heads/".length),
    branchRef: entry.branch,
    baseRef,
    reviewedBase: checkpoint.lifecycle.reviewed_base,
    reviewedFeature: checkpoint.lifecycle.reviewed_feature,
    featureTip: fullCommit(entry.path, "HEAD") ?? "",
    checkpointPath,
    checkpointRelative: `.ai-engineering/workflow/checkpoints/${slug}.json`,
    checkpoint,
  };
}

function reviewedPlanPayload(value: unknown): Record<string, unknown> | null {
  if (typeof value !== "object" || value === null || Array.isArray(value)) return null;
  const plan = value as Record<string, unknown>;
  if (!Array.isArray(plan.checkpoints)) return null;
  const payload: Record<string, unknown> = { ...plan };
  delete payload.lifecycle;
  payload.checkpoints = plan.checkpoints.map((checkpoint) => {
    if (typeof checkpoint !== "object" || checkpoint === null || Array.isArray(checkpoint)) return checkpoint;
    const item = { ...(checkpoint as Record<string, unknown>) };
    delete item.status;
    if (typeof item.gates === "object" && item.gates !== null && !Array.isArray(item.gates)) {
      item.gates = Object.fromEntries(
        Object.entries(item.gates as Record<string, unknown>).map(([name, gate]) => {
          if (typeof gate !== "object" || gate === null || Array.isArray(gate)) return [name, gate];
          const result = { ...(gate as Record<string, unknown>) };
          delete result.status;
          delete result.attempts;
          delete result.findings;
          return [name, result];
        }),
      );
    }
    return item;
  });
  return payload;
}

export function reviewedFeatureChainProblem(
  repo: string,
  slug: string,
  reviewedBase: string,
  reviewedFeature: string,
  featureTip: string,
  phase: "awaiting-app-review" | "ready-to-merge",
  baseRef: string,
): string | null {
  const ancestry = git(repo, ["merge-base", "--is-ancestor", reviewedFeature, featureTip]);
  if (ancestry.status !== 0 || ancestry.stderr.trim() !== "") {
    return `reviewed_feature ${reviewedFeature} is not an ancestor of ${featureTip}`;
  }
  const history = git(repo, ["rev-list", "--reverse", `${reviewedFeature}..${featureTip}`]);
  if (history.status !== 0 || history.stderr.trim() !== "") return "feature commits after reviewed_feature are unreadable";
  const commits = history.stdout.split("\n").map((commit) => commit.trim()).filter(Boolean);
  if ((phase === "awaiting-app-review" && commits.length !== 1) ||
    (phase === "ready-to-merge" && commits.length < 2)) {
    return "app-review lifecycle checkpoint commits are missing or duplicated";
  }

  const checkpointPath = `.ai-engineering/workflow/checkpoints/${slug}.json`;
  const reviewedText = git(repo, ["show", `${reviewedFeature}:${checkpointPath}`]);
  if (reviewedText.status !== 0 || reviewedText.stderr.trim() !== "") {
    return "reviewed_feature has no readable checkpoint plan";
  }
  let reviewedPlan: Checkpoint;
  try {
    reviewedPlan = parseCheckpoint(reviewedText.stdout, { repoPath: repo, slug, baseRef });
  } catch {
    return "reviewed_feature has a malformed checkpoint plan";
  }
  const reviewedPayload = reviewedPlanPayload(reviewedPlan);
  if (reviewedPayload === null) return "reviewed_feature has no verifiable checkpoint plan";
  let previous = reviewedFeature;
  for (const [index, commit] of commits.entries()) {
    const parents = git(repo, ["rev-list", "--parents", "-n", "1", commit]);
    if (parents.status !== 0 || parents.stderr.trim() !== "" ||
      parents.stdout.trim().replace(/\s+/g, " ") !== `${commit} ${previous}`) {
      return `feature has a non-linear commit after reviewed_feature`;
    }
    const changed = git(repo, ["diff-tree", "--no-commit-id", "--name-only", "-r", "--no-renames", "-z", commit]);
    if (changed.status !== 0 || changed.stderr.trim() !== "" ||
      changed.stdout.split("\0").filter(Boolean).join("\0") !== checkpointPath) {
      return `commit ${commit} after reviewed_feature changes paths other than ${checkpointPath}`;
    }
    const checkpointText = git(repo, ["show", `${commit}:${checkpointPath}`]);
    if (checkpointText.status !== 0 || checkpointText.stderr.trim() !== "") {
      return `commit ${commit} has no readable lifecycle checkpoint`;
    }
    let checkpoint: Checkpoint;
    try {
      checkpoint = parseCheckpoint(checkpointText.stdout, { repoPath: repo, slug, baseRef });
    } catch {
      return `commit ${commit} has malformed lifecycle checkpoint metadata`;
    }
    const payload = reviewedPlanPayload(checkpoint);
    if (payload === null || !isDeepStrictEqual(reviewedPayload, payload)) {
      return `commit ${commit} changes the reviewed checkpoint plan`;
    }
    const lifecycle = checkpoint.lifecycle;
    const isPendingReview = index === 0;
    if (
      !checkpoint.checkpoints.every((item) => item.status === "passed" &&
        ["behavior", "ui", "review"].every((gate) => {
          const status = item.gates[gate as keyof typeof item.gates].status;
          return status === "passed" || status === "n/a";
        })) ||
      lifecycle.plan_approval !== "approved" ||
      lifecycle.reviewed_base !== reviewedBase ||
      lifecycle.reviewed_feature !== reviewedFeature ||
      lifecycle.phase !== (isPendingReview ? "awaiting-app-review" : "ready-to-merge") ||
      lifecycle.app_review !== (isPendingReview ? "pending" : "approved") ||
      (phase === "awaiting-app-review" && !isPendingReview)
    ) return `commit ${commit} has invalid app-review lifecycle metadata`;
    previous = commit;
  }
  return null;
}

function mergeParents(repo: string, commit: string): string[] | null {
  const result = git(repo, ["rev-list", "--parents", "-n", "1", commit]);
  if (result.status !== 0 || result.stderr.trim() !== "") return null;
  return result.stdout.trim().split(/\s+/);
}

function findPublishedMerge(
  repo: string,
  baseRef: string,
  reviewedBase: string,
  featureTip: string,
  expectedTree: string,
): { commit: string } | { detail: string } | null {
  const history = git(repo, ["rev-list", "--first-parent", "--merges", baseRef]);
  if (history.status !== 0 || history.stderr.trim() !== "") {
    return { detail: history.stderr.trim() || `git rev-list exited ${history.status}` };
  }
  for (const candidate of history.stdout.split("\n").map((line) => line.trim()).filter(Boolean)) {
    const parents = mergeParents(repo, candidate);
    if (parents === null) return { detail: `cannot read parents of ${candidate}` };
    if (parents.join(" ") !== `${candidate} ${reviewedBase} ${featureTip}`) continue;
    const tree = fullObject(repo, `${candidate}^{tree}`);
    if (tree === null) return { detail: `cannot read tree of ${candidate}` };
    if (tree === expectedTree) return { commit: candidate };
  }
  return null;
}

function changedPaths(repo: string, before: string, after: string): string[] | null {
  const changed = git(repo, ["diff", "--no-renames", "--name-only", "-z", before, after]);
  if (changed.status !== 0 || changed.stderr.trim() !== "") return null;
  return [...new Set(changed.stdout.split("\0").filter(Boolean))];
}

function intersects(path: string, incoming: string, ignoreCase: boolean): boolean {
  const left = ignoreCase ? path.toLowerCase() : path;
  const right = ignoreCase ? incoming.toLowerCase() : incoming;
  return left === right || left.startsWith(`${right}/`) || right.startsWith(`${left}/`);
}

function incomingCollisions(repo: string, status: FileStatus, incoming: string[]): string[] | null {
  const config = git(repo, ["config", "--bool", "--get", "core.ignorecase"]);
  if ((config.status !== 0 && config.status !== 1) || config.stderr.trim() !== "") return null;
  const ignoreCase = config.stdout.trim() === "true";
  return status.untracked.filter((path) => incoming.some((changed) => intersects(path, changed, ignoreCase)));
}

function atomicallyWrite(path: string, contents: string, mode: number): string | null {
  const temporary = join(dirname(path), `.${basename(path)}.${randomUUID()}.tmp`);
  try {
    writeFileSync(temporary, contents, { flag: "wx", mode: mode & 0o777 });
    renameSync(temporary, path);
    return null;
  } catch (error) {
    try {
      unlinkSync(temporary);
    } catch {
      // The original write error is the useful one.
    }
    return error instanceof Error ? error.message : String(error);
  }
}

function cleanupTemporary(repo: string, path: string, base: string, feature: string, allowedCommit?: string): string | null {
  const listed = worktreeList(repo);
  if ("detail" in listed) return `cannot verify temporary worktree registration (${listed.detail})`;
  const matches = listed.entries.filter((entry) => canonical(entry.path) === canonical(path));
  if (matches.length === 0) return existsSync(path) ? `${path} is not registered in Git` : null;
  if (matches.length !== 1 || matches[0]?.branch !== null) return `${path} is not the expected detached transaction worktree`;
  const mergeHead = git(path, ["rev-parse", "--verify", "--quiet", "MERGE_HEAD"]);
  if (mergeHead.status === 0 && mergeHead.stderr.trim() === "") {
    if (mergeHead.stdout.trim() !== feature) return `${path} has an unexpected merge in progress`;
    const aborted = git(path, ["merge", "--abort"]);
    if (aborted.status !== 0) return `could not abort the temporary merge in ${path}: ${aborted.stderr.trim()}`;
  } else if (mergeHead.status !== 1 || mergeHead.stderr.trim() !== "") {
    return `cannot verify temporary merge state in ${path}`;
  }
  const head = fullCommit(path, "HEAD");
  if (head === null || (head !== base && head !== allowedCommit)) return `${path} has an unexpected transaction commit`;
  const status = parseStatus(path);
  if (status.detail !== undefined || status.paths.length > 0) {
    return `${path} is not clean${status.detail ? ` (${status.detail})` : ` (${status.paths.map(printable).join(", ")})`}`;
  }
  const removed = git(repo, ["worktree", "remove", path]);
  if (removed.status !== 0) return `could not remove temporary worktree ${path}: ${removed.stderr.trim()}`;
  if (existsSync(path)) return `temporary worktree path ${path} remains`;
  return null;
}

function invalidateReview(repo: string, source: ReadySource, context: CheckpointContext): string {
  const lifecycle = source.checkpoint.lifecycle;
  const next: Checkpoint = {
    ...source.checkpoint,
    lifecycle: {
      ...lifecycle,
      phase: "implementation",
      app_review: "not-started",
      base_ref: null,
      reviewed_base: null,
      reviewed_feature: null,
    },
  };
  assertCheckpointTransition(source.checkpoint, next, context);
  const root = worktreesRoot(repo);
  mkdirSync(root, { recursive: true });
  const transaction = join(root, `.ai-eng-review-${randomUUID()}`);
  const added = git(repo, ["worktree", "add", "--detach", transaction, source.featureTip]);
  if (added.status !== 0) return `could not prepare review invalidation at ${transaction}: ${printable(added.stderr.trim())}`;
  const transactionCheckpoint = join(transaction, source.checkpointRelative);
  let mode = 0;
  try {
    const stat = lstatSync(transactionCheckpoint);
    const contents = readFileSync(transactionCheckpoint, "utf8");
    if (!stat.isFile() || stat.isSymbolicLink() ||
      !isDeepStrictEqual(parseCheckpoint(contents, context), source.checkpoint)) {
      throw new Error("checkpoint differs from the captured review");
    }
    mode = stat.mode;
  } catch (error) {
    const cleanup = cleanupTemporary(repo, transaction, source.featureTip, source.featureTip);
    return `cannot verify checkpoint for review invalidation at ${transaction} (${error instanceof Error ? error.message : String(error)})${cleanup ? `; ${cleanup}` : ""}`;
  }
  const writeError = atomicallyWrite(transactionCheckpoint, serializeCheckpoint(next), mode);
  const staged = git(transaction, ["add", "--", source.checkpointRelative]);
  const stagedPaths = git(transaction, ["diff", "--cached", "--name-only", "--no-renames", "-z"]);
  if (writeError !== null || staged.status !== 0 || staged.stderr.trim() !== "" ||
    stagedPaths.status !== 0 || stagedPaths.stderr.trim() !== "" ||
    stagedPaths.stdout.split("\0").filter(Boolean).join("\0") !== source.checkpointRelative) {
    const cleanup = cleanupTemporary(repo, transaction, source.featureTip, source.featureTip);
    return `could not stage only ${source.checkpointPath}${writeError ? ` (${writeError})` : ""}${cleanup ? `; ${cleanup}` : ""}`;
  }
  const committed = git(transaction, ["commit", "-m", `chore(${source.branch}): invalidate stale review`]);
  const transition = fullCommit(transaction, "HEAD");
  const parents = transition === null ? null : mergeParents(repo, transition);
  const changed = transition === null
    ? null
    : git(repo, ["diff-tree", "--no-commit-id", "--name-only", "-r", "--no-renames", "-z", transition]);
  let parsed: Checkpoint | null = null;
  try {
    const text = git(transaction, ["show", `${transition}:${source.checkpointRelative}`]);
    if (transition !== null && text.status === 0 && text.stderr.trim() === "") parsed = parseCheckpoint(text.stdout, context);
  } catch {
    parsed = null;
  }
  if (
    committed.status !== 0 ||
    transition === null ||
    parents?.join(" ") !== `${transition} ${source.featureTip}` ||
    changed?.status !== 0 ||
    changed.stderr.trim() !== "" ||
    changed.stdout.split("\0").filter(Boolean).join("\0") !== source.checkpointRelative ||
    !isDeepStrictEqual(parsed, next)
  ) {
    const cleanup = cleanupTemporary(repo, transaction, source.featureTip, source.featureTip, transition ?? undefined);
    return `could not verify checkpoint-only review invalidation${cleanup ? `; ${cleanup}` : ""}`;
  }
  const updated = git(repo, ["update-ref", source.branchRef, transition, source.featureTip]);
  if (updated.status !== 0) {
    const cleanup = cleanupTemporary(repo, transaction, source.featureTip, source.featureTip, transition);
    const current = fullCommit(repo, source.branchRef) ?? "unreadable";
    return `feature branch compare-and-swap lost; ${source.branchRef} is ${current}, expected ${source.featureTip}${cleanup ? `; ${cleanup}` : ""}`;
  }
  const synced = git(source.path, ["restore", `--source=${transition}`, "--staged", "--worktree", "--", source.checkpointRelative]);
  const sourceStatus = parseStatus(source.path);
  const syncProblem = synced.status !== 0 || synced.stderr.trim() !== "" ||
    sourceStatus.detail !== undefined || sourceStatus.paths.length > 0
    ? `could not synchronize ${source.checkpointPath}; run \`git -C ${source.path} restore --source=${transition} --staged --worktree -- ${source.checkpointRelative}\``
    : null;
  const cleanup = cleanupTemporary(repo, transaction, source.featureTip, source.featureTip, transition);
  if (syncProblem !== null || cleanup !== null) {
    return `${syncProblem ?? "review checkpoint updated"}${cleanup ? `; ${cleanup}` : ""}`;
  }
  return `review invalidated; ${source.branchRef} now points to ${transition}`;
}

function refreshBaseCheckouts(
  repo: string,
  entries: Worktree[],
  baseRef: string,
  mergeCommit: string,
  incoming: string[],
  invokingPath: string,
  initialStatuses: Map<string, FileStatus>,
): string[] {
  const notes: string[] = [];
  for (const entry of entries.filter((candidate) => candidate.branch === baseRef)) {
    const path = canonical(entry.path);
    if (!existsSync(path)) {
      notes.push(`${path}: base checkout is missing`);
      continue;
    }
    const status = initialStatuses.get(path) ?? parseStatus(path);
    const dirtyIncoming = status.detail === undefined
      ? status.paths.filter((changed) => incoming.some((file) => intersects(changed, file, false)))
      : [];
    if (status.detail !== undefined || dirtyIncoming.length > 0) {
      notes.push(`${path}: left untouched${status.detail ? ` (${status.detail})` : ` (${dirtyIncoming.map(printable).join(", ")})`}`);
      continue;
    }
    const restored = incoming.length === 0
      ? { status: 0, stdout: "", stderr: "" }
      : git(path, [
        "restore",
        `--source=${mergeCommit}`,
        "--staged",
        "--worktree",
        "--",
        ...incoming.map((file) => `:(literal)${file}`),
      ]);
    const after = parseStatus(path);
    if (restored.status !== 0 || restored.stderr.trim() !== "" || after.detail !== undefined ||
      after.paths.some((changed) => incoming.some((file) => intersects(changed, file, false)))) {
      notes.push(`${path}: could not safely refresh incoming paths${after.detail ? ` (${after.detail})` : ""}`);
      continue;
    }
    if (fullCommit(path, "HEAD") !== mergeCommit) {
      notes.push(`${path}: HEAD does not resolve to ${mergeCommit}`);
      continue;
    }
    if (path === invokingPath) notes.push(`${path}: advanced to ${mergeCommit}`);
  }
  return notes;
}

export function worktreeMerge(slug: string, cwd = process.cwd()): { code: number; out: string; err: string } {
  let context;
  try {
    context = resolveContext(cwd);
  } catch (error) {
    return { code: 2, out: "", err: `worktree merge: ${error instanceof Error ? error.message : String(error)}\n` };
  }
  const repo = context.root;
  const listed = worktreeList(repo);
  if ("detail" in listed) {
    return { code: 1, out: "", err: `worktree merge: cannot list Git worktrees (${listed.detail}); run \`ai-eng worktree list\`.\n` };
  }
  const candidates = listed.entries
    .map((entry) => readySource(entry, slug))
    .filter((source): source is ReadySource => source !== null);
  if (candidates.length === 0) {
    return {
      code: 1,
      out: "",
      err: `worktree merge: no Git-registered checkout has a ready-to-merge checkpoint for ${slug}; run \`ai-eng worktree new ${slug}\` or \`ai-eng worktree list\` and resume there.\n`,
    };
  }
  if (candidates.length > 1) {
    return {
      code: 1,
      out: "",
      err: `worktree merge: multiple ready-to-merge sources for ${slug}; choose one:\n${candidates.map((source) => `  ${source.path}`).join("\n")}\n`,
    };
  }
  const source = candidates[0]!;
  const sourcePath = canonical(source.path);
  const sourceHead = fullCommit(sourcePath, "HEAD");
  const branchHead = fullCommit(repo, source.branchRef);
  if (sourceHead === null || sourceHead !== source.featureTip || branchHead !== source.featureTip) {
    return { code: 1, out: "", err: `worktree merge: ${sourcePath} HEAD does not match ${source.branchRef}; preserve the source and rerun \`ai-eng worktree list\`.\n` };
  }
  const sourceBranch = git(sourcePath, ["symbolic-ref", "--quiet", "HEAD"]);
  if (sourceBranch.status !== 0 || sourceBranch.stderr.trim() !== "" ||
    sourceBranch.stdout.trim() !== source.branchRef || source.branchRef === source.baseRef) {
    return { code: 1, out: "", err: `worktree merge: ${sourcePath} is not checked out on a distinct feature branch; preserve it and rerun \`ai-eng worktree list\`.\n` };
  }
  const operation = operationState(sourcePath);
  if (operation !== null) {
    return { code: 1, out: "", err: `worktree merge: ${sourcePath} ${operation}; finish or resolve that operation before rerunning \`ai-eng worktree merge ${slug}\`.\n` };
  }
  const checkpointContext: CheckpointContext = { repoPath: sourcePath, slug, baseRef: source.baseRef };
  const chainProblem = reviewedFeatureChainProblem(
    repo,
    slug,
    source.reviewedBase,
    source.reviewedFeature,
    source.featureTip,
    "ready-to-merge",
    source.baseRef,
  );
  if (chainProblem !== null) {
    return { code: 1, out: "", err: `worktree merge: ${chainProblem}; request a new review, then rerun \`ai-eng worktree merge ${slug}\`.\n` };
  }
  const expectedTree = fullObject(repo, `${source.featureTip}^{tree}`);
  if (expectedTree === null) {
    return { code: 1, out: "", err: `worktree merge: expected tree for ${source.featureTip} is unreadable; rerun \`ai-eng worktree list\`.\n` };
  }
  const currentBase = fullCommit(repo, source.baseRef);
  if (currentBase === null) {
    return { code: 1, out: "", err: `worktree merge: ${source.baseRef} is unreadable; check it with \`git -C ${repo} rev-parse ${source.baseRef}\`.\n` };
  }
  if (currentBase !== source.reviewedBase) {
    const published = findPublishedMerge(
      repo,
      source.baseRef,
      source.reviewedBase,
      source.featureTip,
      expectedTree,
    );
    if (published !== null && "detail" in published) {
      return { code: 1, out: "", err: `worktree merge: published merge history is unreadable (${published.detail}); preserve the feature checkout.\n` };
    }
    const publishedMerge = published?.commit ?? null;
    if (publishedMerge !== null) {
      const incoming = changedPaths(repo, source.reviewedBase, source.featureTip);
      if (incoming === null) {
        return { code: 1, out: "", err: `worktree merge: incoming paths for published merge ${publishedMerge} are unreadable; preserve the feature checkout.\n` };
      }
      const entries = listed.entries;
      const initialStatuses = new Map(
        entries
          .filter((entry) => entry.branch === source.baseRef)
          .map((entry) => {
            const path = canonical(entry.path);
            return [path, existsSync(path) ? parseStatus(path) : { paths: [], untracked: [], detail: "worktree path is missing" }] as const;
          }),
      );
      const refreshed = refreshBaseCheckouts(
        repo,
        entries,
        source.baseRef,
        publishedMerge,
        incoming,
        canonical(context.root),
        initialStatuses,
      );
      return {
        code: 0,
        out: `✓ merged ${slug} at ${publishedMerge} into ${source.baseRef}; the feature checkout remains at ${source.path}. When ready, remove it with \`ai-eng worktree rm ${slug}\`.\n`,
        err: refreshed.length > 0 ? `${refreshed.join("\n")}\n` : "",
      };
    }
    const invalidation = invalidateReview(repo, source, checkpointContext);
    return {
      code: 1,
      out: "",
      err: `worktree merge: reviewed base ${source.reviewedBase} moved to ${currentBase}; ${invalidation}. Rerun affected gates and app review before \`ai-eng worktree merge ${slug}\`.\n`,
    };
  }
  const status = parseStatus(sourcePath);
  if (status.detail !== undefined || status.paths.length > 0) {
    return {
      code: 1,
      out: "",
      err: `worktree merge: source ${sourcePath} is not clean${status.detail ? ` (${status.detail})` : ` (${status.paths.map(printable).join(", ")})`}; preserve the work and rerun \`ai-eng worktree merge ${slug}\` after committing or resolving it.\n`,
    };
  }
  const incoming = changedPaths(repo, source.reviewedBase, source.featureTip);
  if (incoming === null) {
    return { code: 1, out: "", err: `worktree merge: incoming paths from ${source.reviewedBase} to ${source.featureTip} are unreadable; rerun \`ai-eng worktree list\`.\n` };
  }
  const entries = listed.entries;
  const invokingPath = canonical(context.root);
  const initialStatuses = new Map(
    entries
      .filter((entry) => entry.branch === source.baseRef)
      .map((entry) => {
        const path = canonical(entry.path);
        return [path, existsSync(path) ? parseStatus(path) : { paths: [], untracked: [], detail: "worktree path is missing" }] as const;
      }),
  );
  const invokingEntry = entries.find((entry) => canonical(entry.path) === invokingPath);
  if (invokingEntry?.branch === source.baseRef) {
    const destinationStatus = initialStatuses.get(invokingPath) ?? parseStatus(invokingPath);
    if (destinationStatus.detail !== undefined) {
      return { code: 1, out: "", err: `worktree merge: ${invokingPath} status is unreadable (${destinationStatus.detail}); preserve it and rerun \`ai-eng worktree merge ${slug}\`.\n` };
    }
    const collisions = incomingCollisions(repo, destinationStatus, incoming);
    if (collisions === null) {
      return { code: 1, out: "", err: `worktree merge: cannot determine incoming path collisions in ${invokingPath}; preserve it and rerun \`ai-eng worktree merge ${slug}\`.\n` };
    }
    if (collisions.length > 0) {
      return {
        code: 1,
        out: "",
        err: `worktree merge: untracked paths collide with incoming changes in ${invokingPath} (${collisions.map(printable).join(", ")}); move or commit those files, then rerun \`ai-eng worktree merge ${slug}\`.\n`,
      };
    }
    const trackedCollisions = destinationStatus.paths.filter((path) => !destinationStatus.untracked.includes(path) &&
      incoming.some((file) => intersects(path, file, false)));
    if (trackedCollisions.length > 0) {
      return {
        code: 1,
        out: "",
        err: `worktree merge: local changes collide with incoming paths in ${invokingPath} (${trackedCollisions.map(printable).join(", ")}); commit or resolve them, then rerun \`ai-eng worktree merge ${slug}\`.\n`,
      };
    }
  }

  const root = worktreesRoot(repo);
  mkdirSync(root, { recursive: true });
  const transaction = join(root, `.ai-eng-merge-${randomUUID()}`);
  const added = git(repo, ["worktree", "add", "--detach", transaction, source.reviewedBase]);
  if (added.status !== 0) {
    return { code: 1, out: "", err: `worktree merge: could not create detached transaction at ${transaction}: ${printable(added.stderr.trim())}; preserve the feature checkout.\n` };
  }
  const merged = git(transaction, ["merge", "--no-commit", "--no-ff", source.featureTip]);
  if (merged.status !== 0) {
    const cleanup = cleanupTemporary(repo, transaction, source.reviewedBase, source.featureTip);
    return { code: 1, out: "", err: `worktree merge: no-ff merge failed: ${printable(merged.stderr.trim())}${cleanup ? `; ${cleanup}` : ""}; rerun \`ai-eng worktree merge ${slug}\` after resolving the conflict.\n` };
  }
  const mergeHead = git(transaction, ["rev-parse", "--verify", "MERGE_HEAD"]);
  const mergeTree = git(transaction, ["write-tree"]);
  const mergeTreeId = mergeTree.stdout.trim();
  if (mergeHead.status !== 0 || mergeHead.stderr.trim() !== "" ||
    mergeHead.stdout.trim() !== source.featureTip || mergeTree.status !== 0 ||
    mergeTree.stderr.trim() !== "" || !SHA.test(mergeTreeId) || mergeTreeId !== expectedTree) {
    const cleanup = cleanupTemporary(repo, transaction, source.reviewedBase, source.featureTip);
    return { code: 1, out: "", err: `worktree merge: temporary merge tree or parent differs from the reviewed feature${cleanup ? `; ${cleanup}` : ""}; rerun \`ai-eng worktree merge ${slug}\` after review.\n` };
  }
  const committed = git(transaction, ["commit", "-m", `chore(${slug}): merge ${source.branch}`]);
  const mergeCommit = fullCommit(transaction, "HEAD");
  const parents = mergeCommit === null ? null : mergeParents(repo, mergeCommit);
  const committedTree = mergeCommit === null ? null : fullObject(repo, `${mergeCommit}^{tree}`);
  if (
    committed.status !== 0 ||
    mergeCommit === null ||
    parents?.join(" ") !== `${mergeCommit} ${source.reviewedBase} ${source.featureTip}` ||
    committedTree !== expectedTree
  ) {
    const cleanup = cleanupTemporary(repo, transaction, source.reviewedBase, source.featureTip, mergeCommit ?? undefined);
    return { code: 1, out: "", err: `worktree merge: temporary commit failed exact-parent or merge tree verification${cleanup ? `; ${cleanup}` : ""}; preserve the feature checkout and rerun \`ai-eng worktree merge ${slug}\` after review.\n` };
  }
  const temporaryStatus = parseStatus(transaction);
  if (temporaryStatus.detail !== undefined || temporaryStatus.paths.length > 0 || operationState(transaction) !== null) {
    const cleanup = cleanupTemporary(repo, transaction, source.reviewedBase, source.featureTip, mergeCommit);
    return { code: 1, out: "", err: `worktree merge: temporary checkout ${transaction} is not clean after commit${cleanup ? `; ${cleanup}` : ""}; preserve the feature checkout.\n` };
  }
  const latestFeature = fullCommit(repo, source.branchRef);
  if (latestFeature !== source.featureTip) {
    const cleanup = cleanupTemporary(repo, transaction, source.reviewedBase, source.featureTip, mergeCommit);
    return { code: 1, out: "", err: `worktree merge: ${source.branchRef} moved from reviewed tip ${source.featureTip} to ${latestFeature ?? "unreadable"}; request a new review before rerunning \`ai-eng worktree merge ${slug}\`${cleanup ? `; ${cleanup}` : ""}.\n` };
  }
  const published = git(repo, ["update-ref", source.baseRef, mergeCommit, source.reviewedBase]);
  if (published.status !== 0) {
    const changedBase = fullCommit(repo, source.baseRef) ?? "unreadable";
    const cleanup = cleanupTemporary(repo, transaction, source.reviewedBase, source.featureTip, mergeCommit);
    return { code: 1, out: "", err: `worktree merge: compare-and-swap lost; ${source.baseRef} changed from ${source.reviewedBase} to ${changedBase}. Preserve the feature and rerun synchronization, gates and app review.${cleanup ? ` ${cleanup}` : ""}\n` };
  }
  const publishedParents = mergeParents(repo, mergeCommit);
  const publishedTree = fullObject(repo, `${mergeCommit}^{tree}`);
  if (
    fullCommit(repo, source.baseRef) !== mergeCommit ||
    publishedParents?.join(" ") !== `${mergeCommit} ${source.reviewedBase} ${source.featureTip}` ||
    publishedTree !== expectedTree
  ) {
    const cleanup = cleanupTemporary(repo, transaction, source.reviewedBase, source.featureTip, mergeCommit);
    return { code: 1, out: "", err: `worktree merge: published merge ${mergeCommit} failed final verification; preserve the feature checkout${cleanup ? `; ${cleanup}` : ""}.\n` };
  }
  const refreshed = refreshBaseCheckouts(repo, entries, source.baseRef, mergeCommit, incoming, invokingPath, initialStatuses);
  const cleanup = cleanupTemporary(repo, transaction, source.reviewedBase, source.featureTip, mergeCommit);
  if (cleanup !== null) {
    return { code: 1, out: "", err: `worktree merge: ${mergeCommit} is published, but ${cleanup}; preserve the feature checkout.\n` };
  }
  return {
    code: 0,
    out: `✓ merged ${slug} at ${mergeCommit} into ${source.baseRef}; the feature checkout remains at ${source.path}. When ready, remove it with \`ai-eng worktree rm ${slug}\`.\n`,
    err: refreshed.length > 0 ? `${refreshed.join("\n")}\n` : "",
  };
}
