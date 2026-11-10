// src/git/shared-worktree.ts — where a worktree lives, what a slug may be, and the git
// argv the `ai-eng worktree` verb runs.
// Every git value is an argv element: no command is ever assembled as a shell string.

import {
  existsSync,
  lstatSync,
  mkdirSync,
  readdirSync,
  readFileSync as readFile,
  realpathSync,
  renameSync,
  unlinkSync,
  writeFileSync,
} from "node:fs";
import { randomUUID } from "node:crypto";
import { basename, dirname, join, resolve, sep } from "node:path";
import { isDeepStrictEqual } from "node:util";
import { pathIsWithin } from "../shared-project-fs.ts";
import { loadConfig, printable } from "../env.ts";
import { namedBase, resolveContext } from "./context.ts";
import { commitIdentityEnv, type GitResult, runGit } from "./run.ts";
import { reviewedFeatureChainProblem } from "./merge.ts";
import {
  canonicalize,
  gitOperationState,
  listWorktrees,
  statusPaths,
  worktreeRoot,
  worktreeStatus,
  type WorktreeStatus,
} from "./worktree.ts";
import {
  gatesComplete,
  parseCheckpoint,
  readCheckpoint,
  serializeCheckpoint,
  checkpointFileIdentity,
  type Checkpoint,
} from "../workflow/checkpoint.ts";

/** The shape of a slug: the user types it, and it becomes both `feat/<slug>` and the
 *  worktree directory name. The orchestrator compares it literally against
 *  `<meta name="ai-feature">`. `$` alone would accept a trailing newline, so the
 *  test also rules out control characters — see `isSlug`. */
export const SLUG_PATTERN = /^[a-z0-9][a-z0-9._-]*$/;

export interface WorktreeResult {
  code: number;
  out: string;
  err: string;
}

function git(cwd: string, args: string[]): GitResult {
  return runGit(args, { cwd, isolated: true });
}

function canonicalizeForCreation(path: string): string {
  let ancestor = resolve(path);
  const missing: string[] = [];
  while (true) {
    try {
      return resolve(realpathSync.native(ancestor), ...missing.reverse());
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
      try {
        lstatSync(ancestor);
      } catch (statError) {
        if ((statError as NodeJS.ErrnoException).code !== "ENOENT") throw statError;
        const parent = dirname(ancestor);
        if (parent === ancestor) throw error;
        missing.push(basename(ancestor));
        ancestor = parent;
        continue;
      }
      throw error;
    }
  }
}

/** The primary checkout, asked of git — never the nearest `.git`, which inside a
 *  session worktree is that worktree. The common git dir of a non-bare repository is
 *  `<primary>/.git`, so its parent is the primary tree; anything else (bare repo,
 *  submodule) is refused rather than guessed. Shared refs and worktree registration
 *  use this root; `worktree new` reads source state from its invoking checkout. */
function primaryRepoRoot(): string | null {
  const cwd = process.cwd();
  const common = git(cwd, ["rev-parse", "--git-common-dir"]);
  if (common.status !== 0) return null;
  const dir = common.stdout.trim();
  if (dir === "" || basename(dir) !== ".git") return null;
  const root = canonicalize(resolve(cwd, join(dir, "..")));
  return existsSync(root) ? root : null;
}

interface OpenWorktree {
  path: string;
  /** The branch short name, absent when the worktree is detached. */
  branch: string | undefined;
  /** What the user typed: the branch with the `feat/` prefix removed. */
  slug: string;
  detached: boolean;
  prunable: boolean;
}

/** Every worktree git knows, as the worktree verbs name it: the short branch and the slug. */
function openWorktrees(repo: string): { worktrees: OpenWorktree[] } | { detail: string } {
  const listed = listWorktrees(repo);
  if ("detail" in listed) return listed;
  return {
    worktrees: listed.worktrees.map((entry) => {
      const branch = entry.branchRef?.startsWith("refs/heads/") ? entry.branchRef.slice("refs/heads/".length) : undefined;
      return {
        path: entry.path,
        branch,
        slug: branch === undefined ? basename(entry.path) : branch.replace(/^feat\//, ""),
        detached: entry.detached,
        prunable: entry.prunable,
      };
    }),
  };
}

/** The ignored paths a worktree holds, so `worktree rm` can name what its removal
 *  drops before it drops it. `--untracked-files=normal` forces the untracked listing
 *  past the user's `status.showUntrackedFiles=no` — which would otherwise print
 *  nothing at all, ignored entries included, and let the removal name an empty set
 *  while dropping a `local.env` — while keeping a wholly ignored directory collapsed
 *  to one `dir/` entry, so the report stays bounded (a 2,000-file `node_modules` is
 *  one line, not 2,000) and matches the skill list's `dir/` entries literally. `-z`
 *  keeps each path raw, matching the status reads elsewhere. null means the status
 *  could not be trusted — a non-zero exit, or the warning git prints on stderr while
 *  still exiting 0 when it cannot read a subdirectory — so the caller never reports
 *  an empty set for content the read did not see. */
function ignoredPaths(path: string): string[] | null {
  const status = git(path, ["status", "--porcelain", "--ignored", "--untracked-files=normal", "-z"]);
  if (status.status !== 0 || status.stderr.trim() !== "") return null;
  const found: string[] = [];
  const tokens = status.stdout.split("\0");
  for (let index = 0; index < tokens.length; ) {
    const token = tokens[index] ?? "";
    if (token === "") {
      index += 1; // the NUL that closes the last record
      continue;
    }
    const read = statusPaths(tokens, index);
    if (read === null) return null;
    if (token.startsWith("!! ")) found.push(...read.paths);
    index = read.next;
  }
  return found;
}

function ignoredRemovalNote(dropped: string[] | null, removalState: "removed" | "unknown"): string {
  if (dropped === null) {
    return removalState === "removed"
      ? " — the ignored content could not be read (git status warned); anything it held was permanently deleted unseen"
      : " — the ignored content could not be read (git status warned); whether it was removed is unknown";
  }
  if (dropped.length === 0) return "";
  const paths = dropped.map(displayPath);
  return removalState === "removed"
    ? ` — permanently deleted ignored: ${paths.join(", ")}`
    : ` — ignored content found before removal: ${paths.join(", ")}; its remaining state is unknown`;
}

export function worktreeNew(branchInput: string): WorktreeResult {
  const repo = primaryRepoRoot();
  if (repo === null) return { code: 2, out: "", err: "worktree new: not inside a git repository.\n" };
  const topLevel = git(process.cwd(), ["rev-parse", "--path-format=absolute", "--show-toplevel"]);
  if (topLevel.status !== 0 || topLevel.stderr.trim() !== "" || topLevel.stdout.trim() === "") {
    return { code: 1, out: "", err: `worktree new: cannot resolve the invoking checkout root; inspect \`git -C ${process.cwd()} rev-parse --show-toplevel\`.\n` };
  }
  const source = canonicalize(topLevel.stdout.trim());
  if (branchInput === "" || /\p{C}/u.test(branchInput)) {
    return { code: 2, out: "", err: `worktree new: invalid slug or branch name "${printable(branchInput)}"; pass a Git branch name.\n` };
  }
  const exactBranch = branchInput.includes("/")
    ? null
    : git(repo, ["show-ref", "--verify", "--quiet", `refs/heads/${branchInput}`]);
  if (exactBranch !== null && exactBranch.status !== 0 && exactBranch.status !== 1) {
    return { code: 1, out: "", err: `worktree new: cannot inspect branch ${branchInput}; check it with \`git -C ${repo} show-ref --verify refs/heads/${branchInput}\`.\n` };
  }
  const branch = branchInput.includes("/") || exactBranch?.status === 0 ? branchInput : `feat/${branchInput}`;
  const validBranch = git(repo, ["check-ref-format", "--branch", branch]);
  if (validBranch.status !== 0 || validBranch.stdout.trim() !== branch) {
    return { code: 2, out: "", err: `worktree new: invalid branch name "${printable(branchInput)}"; check it with \`git -C ${repo} check-ref-format --branch ${printable(branch)}\`.\n` };
  }
  const root = worktreeRoot(repo);
  let canonicalRoot: string;
  try {
    canonicalRoot = canonicalizeForCreation(root);
  } catch (error) {
    return {
      code: 1,
      out: "",
      err: `worktree new: cannot resolve configured worktree root ${root} (${error instanceof Error ? error.message : String(error)}); inspect or repair that path, then retry.\n`,
    };
  }
  const directoryName = branchInput.startsWith("feat/") ? branchInput.slice("feat/".length) : branchInput;
  const target = resolve(canonicalRoot, directoryName);
  if (!pathIsWithin(canonicalRoot, target)) {
    return { code: 2, out: "", err: `worktree new: ${target} is outside the configured worktree root; choose a branch with a repository-local path.\n` };
  }
  const listed = openWorktrees(repo);
  if ("detail" in listed) {
    return { code: 1, out: "", err: `worktree new: cannot inspect registered worktrees (${listed.detail}); run \`ai-eng worktree list\`.\n` };
  }
  const existing = listed.worktrees.find((entry) => entry.branch === branch);
  if (existing !== undefined) {
    return { code: 1, out: "", err: `worktree new: branch ${branch} is already checked out at ${existing.path}; use that checkout or choose another branch.\n` };
  }
  const branchExists = git(repo, ["show-ref", "--verify", "--quiet", `refs/heads/${branch}`]);
  if (branchExists.status === 0) {
    return { code: 1, out: "", err: `worktree new: branch ${branch} already exists; choose another branch or inspect \`git -C ${repo} worktree list\`.\n` };
  }
  if (branchExists.status !== 1 || branchExists.stderr.trim() !== "") {
    return { code: 1, out: "", err: `worktree new: cannot verify whether branch ${branch} exists; inspect \`git -C ${repo} show-ref --verify refs/heads/${branch}\`.\n` };
  }
  if (existsSync(target)) {
    return { code: 1, out: "", err: `worktree new: path ${target} already exists; choose another branch or inspect that path.\n` };
  }
  const configuredBase = loadConfig(repo).git?.["base"];
  const remotes = git(repo, ["remote"]);
  if (remotes.status !== 0 || remotes.stderr.trim() !== "") {
    return { code: 1, out: "", err: `worktree new: remotes for ${repo} are unreadable; inspect \`git -C ${repo} remote -v\`.\n` };
  }
  let baseBranch: string | null;
  if (configuredBase !== undefined || remotes.stdout.trim() !== "") {
    try {
      // namedBase: starting a feature from a checkout on the base is the normal flow.
      baseBranch = namedBase(process.cwd());
    } catch (error) {
      return { code: 1, out: "", err: `worktree new: cannot detect the base (${error instanceof Error ? error.message : String(error)}); run \`ai-eng worktree list\`.\n` };
    }
  } else {
    const branch = git(source, ["symbolic-ref", "--quiet", "--short", "HEAD"]);
    baseBranch = branch.status === 0 && branch.stderr.trim() === "" ? branch.stdout.trim() : null;
  }
  if (baseBranch === null) {
    return { code: 1, out: "", err: `worktree new: no base branch is detectable; set [git] base in ${join(repo, ".ai-engineering", "config.toml")} or check out a branch.\n` };
  }
  const baseRef = `refs/heads/${baseBranch}`;
  const baseExists = git(repo, ["show-ref", "--verify", "--quiet", baseRef]);
  if (baseExists.status !== 0 || baseExists.stderr.trim() !== "") {
    return { code: 1, out: "", err: `worktree new: detected base ${baseRef} is unavailable; check it with \`git -C ${repo} show-ref --verify ${baseRef}\`.\n` };
  }
  const status = git(source, ["status", "--porcelain", "--untracked-files=all", "-z"]);
  if (status.status !== 0 || status.stderr.trim() !== "") {
    return { code: 1, out: "", err: `worktree new: status for ${source} is unreadable; inspect \`git -C ${source} status --short\` before retrying.\n` };
  }
  const touchedSlots = new Set<string>();
  const tokens = status.stdout.split("\0");
  for (let index = 0; index < tokens.length; ) {
    if (tokens[index] === "") {
      index += 1;
      continue;
    }
    const record = statusPaths(tokens, index);
    if (record === null) return { code: 1, out: "", err: `worktree new: status for ${source} contains an unreadable path; inspect \`git -C ${source} status --short\`.\n` };
    for (const path of record.paths) {
      const pathKey = path.toLowerCase();
      if (
        [".ai-engineering/brainstorm.html", ".ai-engineering/prd.html", ".ai-engineering/spec.html", ".ai-engineering/plan.html"]
          .some((slot) => pathKey === slot || pathKey.startsWith(`${slot}/`))
      ) touchedSlots.add(path);
    }
    index = record.next;
  }
  const sourceHead = fullHead(source);
  if (sourceHead === null) {
    return { code: 1, out: "", err: `worktree new: current HEAD for ${source} is unreadable; inspect \`git -C ${source} rev-parse --verify HEAD^{commit}\`.\n` };
  }
  const parent = dirname(target);
  let canonicalParent: string;
  try {
    canonicalParent = canonicalizeForCreation(parent);
  } catch (error) {
    return {
      code: 1,
      out: "",
      err: `worktree new: cannot resolve target parent ${parent} safely (${error instanceof Error ? error.message : String(error)}); inspect or repair its path components, then retry.\n`,
    };
  }
  if (!pathIsWithin(canonicalRoot, canonicalParent)) {
    return {
      code: 2,
      out: "",
      err: `worktree new: target parent ${parent} resolves to ${canonicalParent}, outside configured worktree root ${canonicalRoot}; remove or repair the symlink, then retry.\n`,
    };
  }
  mkdirSync(parent, { recursive: true });
  let currentRoot: string;
  let currentParent: string;
  try {
    currentRoot = canonicalizeForCreation(root);
    currentParent = canonicalizeForCreation(parent);
  } catch (error) {
    return {
      code: 1,
      out: "",
      err: `worktree new: cannot revalidate target ${target} after creating its parent (${error instanceof Error ? error.message : String(error)}); inspect or repair the configured root and parent, then retry.\n`,
    };
  }
  if (currentRoot !== canonicalRoot || !pathIsWithin(currentRoot, currentParent)) {
    return {
      code: 2,
      out: "",
      err: `worktree new: refusing target ${target}; parent ${parent} resolves to ${currentParent}, outside or redirected from configured worktree root ${canonicalRoot}; repair the path or symlink, then retry.\n`,
    };
  }
  const added = git(repo, ["worktree", "add", target, "-b", branch, sourceHead]);
  if (added.status !== 0) {
    return { code: 1, out: "", err: `worktree new: git worktree add failed for ${target}: ${added.stderr.trim()}; inspect \`git -C ${repo} worktree list\`.\n` };
  }
  const configuredRemote = git(repo, ["config", `branch.${branch}.remote`, "."]);
  const configuredMerge = git(repo, ["config", `branch.${branch}.merge`, baseRef]);
  if (configuredRemote.status !== 0 || configuredMerge.status !== 0) {
    return { code: 1, out: `✓ worktree ${branch} → ${target}\n`, err: `worktree new: the worktree exists at ${target}, but its local upstream config could not be written; inspect \`git -C ${repo} config --get branch.${branch}.merge\`.\n` };
  }
  return {
    code: 0,
    out: `✓ worktree ${branch} → ${target}\n`,
    err: touchedSlots.size > 0
      ? `worktree new: dirty design files stay in ${source} and do not travel: ${[...touchedSlots].join(", ")}.\n`
      : "",
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function checkpointFiles(plan: unknown, slug: string): string[] | null {
  if (!isRecord(plan) || plan.slug !== slug || !Array.isArray(plan.checkpoints)) return null;
  const files: string[] = [];
  for (const checkpoint of plan.checkpoints) {
    if (!isRecord(checkpoint)) return null;
    if (checkpoint.files === undefined) continue;
    if (!Array.isArray(checkpoint.files) || checkpoint.files.some((file) => typeof file !== "string")) return null;
    files.push(...checkpoint.files);
  }
  return files;
}

function isStaleReviewPin(checkpoint: Checkpoint, currentBase: string | null): boolean {
  const { phase, reviewed_base } = checkpoint.lifecycle;
  return ["awaiting-app-review", "ready-to-merge"].includes(phase) &&
    reviewed_base !== null &&
    currentBase !== null &&
    reviewed_base !== currentBase;
}

function checkpointBaseRefForValidation(
  checkpointPath: string,
  detectedBaseRef: string | null,
  branch: string | null,
): string | null {
  // This ref validates checkpoint structure only; only a detected ref proves freshness.
  if (detectedBaseRef !== null) return detectedBaseRef;
  try {
    const parsed = JSON.parse(readFile(checkpointPath, "utf8")) as {
      lifecycle?: { base_ref?: unknown };
    };
    if (typeof parsed.lifecycle?.base_ref === "string") return parsed.lifecycle.base_ref;
  } catch {
    // A malformed checkpoint has no declared base ref to validate against.
  }
  return branch === null ? null : `refs/heads/${branch}`;
}

function lifecycleStatus(
  checkpointPath: string,
  worktreePath: string,
  slug: string,
  repo: string,
  branch: string,
): { label: string; files: string[]; identity?: boolean } {
  if (!existsSync(worktreePath) || !existsSync(checkpointPath)) {
    return { label: "unknown (missing, unreadable or malformed checkpoint)", files: [] };
  }
  let detectedBaseRef: string | null = null;
  try {
    const detectedBase = resolveContext(worktreePath).base;
    if (detectedBase !== null) detectedBaseRef = `refs/heads/${detectedBase}`;
  } catch {
    // Validate a declared pin without treating it as evidence of current freshness.
  }
  const baseRef = checkpointBaseRefForValidation(
    checkpointPath,
    detectedBaseRef,
    branch === "" ? null : branch,
  );
  if (baseRef === null) return { label: "unknown (base ref is not detectable)", files: [] };
  let currentBase: string | null = null;
  if (detectedBaseRef !== null) {
    const currentBaseRead = git(repo, ["rev-parse", "--verify", `${detectedBaseRef}^{commit}`]);
    if (currentBaseRead.status === 0 && currentBaseRead.stderr.trim() === "") {
      currentBase = currentBaseRead.stdout.trim();
    }
  }
  let parsed: Checkpoint;
  try {
    if (checkpointFileIdentity(checkpointPath, worktreePath) === null) {
      return { label: "unknown (checkpoint is not a worktree-local file)", files: [] };
    }
    parsed = readCheckpoint(checkpointPath, { repoPath: worktreePath, slug, baseRef });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    if (/checkpoint lifecycle: must be an object/i.test(message)) {
      return { label: "unknown (legacy checkpoint without lifecycle)", files: [] };
    }
    if (/^checkpoint (?!JSON\b|path\b|slug\b|lifecycle: must be an object\b)/i.test(message)) {
      return { label: "unknown (contradictory lifecycle)", files: [] };
    }
    if (/checkpoint (?:slug|path):/i.test(message)) {
      return { label: "unknown (checkpoint does not match this worktree)", files: [] };
    }
    return { label: "unknown (missing, unreadable or malformed checkpoint)", files: [] };
  }
  const files = checkpointFiles(parsed, slug);
  if (files === null) return { label: "unknown (checkpoint does not match this worktree)", files: [] };
  const lifecycle = parsed.lifecycle;
  const phase = lifecycle.phase;
  if (isStaleReviewPin(parsed, currentBase)) {
    return { label: "stale (reviewed_base is stale)", files, identity: false };
  }
  if (["awaiting-app-review", "ready-to-merge"].includes(phase) && !gatesComplete(parsed)) {
    return { label: "unknown (lifecycle gates are incomplete)", files, identity: true };
  }
  if (lifecycle.reviewed_base !== null) {
    if (currentBase === null) {
      return { label: "unknown (base ref is not detectable)", files, identity: true };
    }
    if (lifecycle.reviewed_base !== currentBase) {
      return { label: "unknown (reviewed_base is stale)", files, identity: true };
    }
  }
  if (phase === "ready-to-merge") {
    const reviewedFeature = lifecycle.reviewed_feature;
    const featureRef = git(repo, ["rev-parse", "--verify", `refs/heads/${branch}^{commit}`]);
    if (typeof reviewedFeature !== "string" || featureRef.status !== 0) {
      return { label: "unknown (reviewed_feature or feature tip is unreadable)", files, identity: true };
    }
    const chainProblem = reviewedFeatureChainProblem(
      repo,
      slug,
      lifecycle.reviewed_base as string,
      reviewedFeature,
      featureRef.stdout.trim(),
      "ready-to-merge",
      baseRef,
    );
    if (chainProblem !== null) {
      return { label: `unknown (${chainProblem})`, files, identity: true };
    }
  }
  return {
    label: `${phase} (plan ${String(lifecycle.plan_approval)}, app review ${String(lifecycle.app_review)})`,
    files,
    identity: true,
  };
}

function normalizedEvidencePath(path: string): string | null {
  const normalized = path.replace(/^(?:\.\/)+/, "").replace(/\/+/g, "/");
  if (normalized === "" || normalized.startsWith("/") || normalized.split("/").some((part) => part === "..")) return null;
  return normalized;
}

function displayPath(path: string): string {
  return path.replace(/[\p{C}]/gu, "");
}

interface ListedWorktree {
  entry: OpenWorktree;
  slug: string;
  identity: boolean;
  isFeature: boolean;
  status: WorktreeStatus;
  checkpointPath: string | null;
  checkpointFiles: string[];
  lifecycle: string;
}

export function worktreeList(requestedSlug?: string): WorktreeResult {
  const repo = primaryRepoRoot();
  if (repo === null) return { code: 2, out: "", err: "worktree list: not inside a git repository.\n" };
  if (requestedSlug !== undefined && (!SLUG_PATTERN.test(requestedSlug) || /\p{C}/u.test(requestedSlug))) {
    return { code: 2, out: "", err: `worktree list: invalid slug "${printable(requestedSlug)}".\n` };
  }
  const root = worktreeRoot(repo);
  const listed = openWorktrees(repo);
  if ("detail" in listed) {
    return { code: 2, out: "", err: `worktree list: the worktree list is unreadable (${listed.detail}).\n` };
  }
  let statusUnreadable = false;
  const entries: ListedWorktree[] = [];
  for (const entry of listed.worktrees) {
    if (canonicalize(entry.path) === repo) continue;
    const pathExists = existsSync(entry.path);
    const status: WorktreeStatus = pathExists
      ? worktreeStatus(entry.path)
      : { paths: [], untracked: [], detail: "worktree path is missing" };
    statusUnreadable ||= pathExists && status.detail !== undefined;
    const checkpointDir = join(entry.path, ".ai-engineering", "workflow", "checkpoints");
    let checkpointSlugs: string[] = [];
    try {
      checkpointSlugs = readdirSync(checkpointDir)
        .filter((name) => name.endsWith(".json"))
        .map((name) => name.slice(0, -".json".length))
        .filter((slug) => SLUG_PATTERN.test(slug) && !/\p{C}/u.test(slug));
    } catch {
      // A checkout without a readable checkpoint directory has no checkpoint identity to classify.
    }
    if (requestedSlug !== undefined) {
      checkpointSlugs = checkpointSlugs.includes(requestedSlug) ? [requestedSlug] : [];
    }
    const matchedSlugs = new Set<string>();
    for (const slug of checkpointSlugs) {
      const checkpointPath = join(checkpointDir, `${slug}.json`);
      const state = lifecycleStatus(checkpointPath, entry.path, slug, repo, entry.branch ?? "");
      if (state.identity === undefined) continue;
      matchedSlugs.add(slug);
      entries.push({
        entry,
        slug,
        identity: state.identity,
        isFeature: state.identity,
        status,
        checkpointPath,
        checkpointFiles: state.files,
        lifecycle: state.label,
      });
    }

    const isLegacyFeature =
      entry.branch?.startsWith("feat/") === true &&
      SLUG_PATTERN.test(entry.slug) &&
      !/\p{C}/u.test(entry.slug);
    const matchesLegacyRequest = requestedSlug === undefined ||
      entry.slug === requestedSlug ||
      canonicalize(entry.path) === canonicalize(join(root, requestedSlug));
    const shouldKeepLegacyEntry = requestedSlug === undefined
      ? matchedSlugs.size === 0 || (isLegacyFeature && !matchedSlugs.has(entry.slug))
      : matchesLegacyRequest && !matchedSlugs.has(requestedSlug);
    if (!shouldKeepLegacyEntry) continue;
    const checkpointPath = isLegacyFeature
      ? join(entry.path, ".ai-engineering", "workflow", "checkpoints", `${entry.slug}.json`)
      : null;
    const state = checkpointPath === null
      ? { label: "unknown (no feature branch)", files: [] }
      : lifecycleStatus(checkpointPath, entry.path, entry.slug, repo, entry.branch ?? "");
    entries.push({
      entry,
      slug: entry.slug,
      identity: state.identity === true,
      isFeature: isLegacyFeature,
      status,
      checkpointPath,
      checkpointFiles: state.files,
      lifecycle: state.label,
    });
  }

  const matchingEntries = requestedSlug === undefined
    ? entries
    : entries.filter(({ slug }) => slug === requestedSlug);
  const checkpointCounts = new Map<string, number>();
  for (const { slug, identity } of entries) {
    if (identity) checkpointCounts.set(slug, (checkpointCounts.get(slug) ?? 0) + 1);
  }
  const ambiguousSlugs = [...checkpointCounts]
    .filter(([, count]) => count > 1)
    .map(([slug]) => slug);
  const lines = matchingEntries.map(({ entry, slug, isFeature, status, lifecycle }) => {
    const classification = isFeature
      ? "feature"
      : entry.detached
        ? "detached"
        : entry.branch === undefined
          ? "unclassified"
          : `unclassified (${printable(entry.branch)})`;
    const cleanliness = status.detail !== undefined
      ? `status unknown (${printable(status.detail)})`
      : status.paths.length === 0
        ? "clean"
        : `dirty (${status.paths.map(displayPath).join(", ")})`;
    return `${displayPath(slug)}\t${displayPath(entry.path)}\t${classification}\t${cleanliness}\t${lifecycle}`;
  });

  const hasWorktreeForSlug = (slug: string): boolean =>
    entries.some(({ slug: checkpointSlug, isFeature }) => isFeature && checkpointSlug === slug) ||
    listed.worktrees.some((entry) =>
      canonicalize(entry.path) !== repo &&
      (
        entry.branch === `feat/${slug}` ||
        entry.slug === slug ||
        canonicalize(entry.path) === canonicalize(join(root, slug))
      )
    );
  const hasMatchingWorktree = requestedSlug !== undefined && hasWorktreeForSlug(requestedSlug);
  const featureSlug = requestedSlug;
  const featureBranchRead = featureSlug === undefined
    ? null
    : git(repo, ["show-ref", "--verify", "--quiet", `refs/heads/feat/${featureSlug}`]);
  const hasFeatureBranch = featureBranchRead?.status === 0 && featureBranchRead.stderr.trim() === "";
  const featureBranchUnknown = featureBranchRead !== null &&
    !hasFeatureBranch &&
    !(featureBranchRead.status === 1 && featureBranchRead.stderr.trim() === "");
  if (requestedSlug !== undefined && hasMatchingWorktree && matchingEntries.length === 0) {
    const path = listed.worktrees.find((entry) =>
      canonicalize(entry.path) === canonicalize(join(root, requestedSlug))
    )?.path ?? "-";
    lines.push(
      `${displayPath(requestedSlug)}\t${displayPath(path)}\tunclassified\tunknown\tunknown (existing worktree does not match feat/${requestedSlug})`,
    );
  }
  if (requestedSlug !== undefined && !hasMatchingWorktree && hasFeatureBranch) {
    lines.push(
      `${displayPath(requestedSlug)}\t-\tbranch-only\tunknown\tunknown (feature branch exists without an open worktree)`,
    );
  }
  if (requestedSlug !== undefined && !hasMatchingWorktree && featureBranchUnknown) {
    lines.push(
      `${displayPath(requestedSlug)}\t-\tbranch-only\tunknown\tunknown (feature branch status is unreadable)`,
    );
  }
  const currentPath = resolveContext(process.cwd()).root;
  const currentCheckpointDir = join(currentPath, ".ai-engineering", "workflow", "checkpoints");
  const currentCheckpointSlugs = new Set<string>();
  let currentBaseRef: string | null = null;
  let currentBaseCommit: string | null = null;
  let currentBranch: string | null = null;
  try {
    const detected = resolveContext(currentPath);
    currentBranch = detected.branch;
    if (detected.base !== null) {
      currentBaseRef = `refs/heads/${detected.base}`;
      const baseCommitRead = git(currentPath, ["rev-parse", "--verify", `${currentBaseRef}^{commit}`]);
      if (baseCommitRead.status === 0 && baseCommitRead.stderr.trim() === "") {
        currentBaseCommit = baseCommitRead.stdout.trim();
      }
    }
  } catch {
    // The active checkpoint line is advisory; the registered-worktree list remains authoritative.
  }
  if (existsSync(currentCheckpointDir)) {
    for (const name of readdirSync(currentCheckpointDir).filter((entry) => entry.endsWith(".json"))) {
      const slug = name.slice(0, -".json".length);
      if (requestedSlug !== undefined && slug !== requestedSlug) continue;
      try {
        const checkpointPath = join(currentCheckpointDir, name);
        const checkpointBaseRef = checkpointBaseRefForValidation(
          checkpointPath,
          currentBaseRef,
          currentBranch,
        );
        if (checkpointBaseRef === null) continue;
        const checkpoint = readCheckpoint(checkpointPath, {
          repoPath: currentPath,
          slug,
          baseRef: checkpointBaseRef,
        });
        const hasStaleReviewPin = isStaleReviewPin(checkpoint, currentBaseCommit);
        if (canonicalize(currentPath) === repo && !hasStaleReviewPin) currentCheckpointSlugs.add(slug);
        if (hasStaleReviewPin) continue;
        if (checkpoint.lifecycle.phase !== "implementation" &&
          checkpoint.lifecycle.phase !== "awaiting-plan-approval" &&
          checkpoint.lifecycle.phase !== "blocked") continue;
        lines.push(`active checkpoint ${displayPath(slug)} in current checkout (${checkpoint.lifecycle.phase})`);
      } catch {
        // A malformed checkpoint is not active work.
      }
    }
  }
  const ambiguousCheckpointSlugs = new Set(ambiguousSlugs);
  for (const slug of currentCheckpointSlugs) {
    if (checkpointCounts.has(slug)) ambiguousCheckpointSlugs.add(slug);
  }
  const isRequestedCheckpointAmbiguous =
    requestedSlug !== undefined && ambiguousCheckpointSlugs.has(requestedSlug);
  if (isRequestedCheckpointAmbiguous) {
    lines.push(`worktree list: checkpoint ${displayPath(requestedSlug)} is ambiguous across Git-listed worktrees; no checkout selected`);
  } else if (requestedSlug === undefined) {
    for (const slug of ambiguousCheckpointSlugs) {
      lines.push(`worktree list: checkpoint ${displayPath(slug)} is ambiguous across Git-listed worktrees; no checkout selected`);
    }
  }

  if (existsSync(root)) {
    const registeredPaths = listed.worktrees.map((entry) => canonicalize(entry.path));
    for (const name of readdirSync(root)) {
      const path = join(root, name);
      const canonicalPath = canonicalize(path);
      if (registeredPaths.includes(canonicalPath) ||
        registeredPaths.some((registered) => registered.startsWith(`${canonicalPath}${sep}`))) continue;
      lines.push(`worktree list: ${displayPath(path)} is not registered in Git, not work`);
    }
  }

  if (requestedSlug !== undefined && !isRequestedCheckpointAmbiguous) {
    const exactMatches = matchingEntries.filter(({ identity }) => identity);
    const featureMatches = matchingEntries.filter(({ isFeature }) => isFeature);
    const selected = exactMatches.length === 1
      ? exactMatches[0]
      : exactMatches.length === 0 && featureMatches.length === 1
        ? featureMatches[0]
        : undefined;
    if (selected !== undefined && selected.isFeature && selected.status.detail === undefined) {
      const planned = new Set(selected.checkpointFiles.map(normalizedEvidencePath).filter((path) => path !== null));
      const own = selected.status.paths.filter((path) => {
        const normalized = normalizedEvidencePath(path);
        return normalized !== null && planned.has(normalized);
      });
      const foreign = selected.status.paths.filter((path) => {
        const normalized = normalizedEvidencePath(path);
        return normalized === null || !planned.has(normalized);
      });
      if (own.length > 0) lines.push(`continue with feature-owned changes: ${own.map(displayPath).join(", ")}`);
      if (foreign.length > 0) lines.push(`foreign files left alone: ${foreign.map(displayPath).join(", ")}`);
    }
  }

  const overlaps = new Set<string>();
  // todo: index paths if local worktree counts grow; pairwise comparison is O(n²).
  for (let left = 0; left < entries.length; left += 1) {
    const first = entries[left];
    if (first === undefined || !first.isFeature) continue;
    for (let right = left + 1; right < entries.length; right += 1) {
      const second = entries[right];
      if (second === undefined || !second.isFeature) continue;
      const firstFiles = new Set(first.checkpointFiles.map(normalizedEvidencePath).filter((path) => path !== null));
      const secondFiles = new Set(second.checkpointFiles.map(normalizedEvidencePath).filter((path) => path !== null));
      const firstStatus = new Set(first.status.paths.map(normalizedEvidencePath).filter((path) => path !== null));
      const secondStatus = new Set(second.status.paths.map(normalizedEvidencePath).filter((path) => path !== null));
      const evidence = new Set<string>();
      for (const path of firstFiles) if (secondFiles.has(path)) evidence.add(path);
      for (const path of firstStatus) if (secondFiles.has(path) || secondStatus.has(path)) evidence.add(path);
      for (const path of secondStatus) if (firstFiles.has(path)) evidence.add(path);
      if (evidence.size === 0) continue;
      overlaps.add(
        `likely overlap: ${displayPath(first.slug)} and ${displayPath(second.slug)} ` +
        `(${[...evidence].map(displayPath).join(", ")}); ` +
        `checkpoints: ${displayPath(first.checkpointPath ?? "")}, ${displayPath(second.checkpointPath ?? "")}`,
      );
    }
  }

  if (requestedSlug === undefined) lines.push(...overlaps);
  const out = lines.join("\n");
  return {
    code: statusUnreadable || isRequestedCheckpointAmbiguous ||
      (requestedSlug === undefined && ambiguousCheckpointSlugs.size > 0) ? 2 : 0,
    out: out.length > 0 ? `${out}\n` : "",
    err: "",
  };
}

function replaceFileAtomically(path: string, contents: string, mode: number): string | null {
  const temporaryPath = join(dirname(path), `.${basename(path)}.${randomUUID()}.tmp`);
  try {
    writeFileSync(temporaryPath, contents, { flag: "wx", mode: mode & 0o777 });
    renameSync(temporaryPath, path);
    return null;
  } catch (error) {
    try {
      unlinkSync(temporaryPath);
    } catch {
      // Keep the original write error; the temporary file may not exist.
    }
    return error instanceof Error ? error.message : String(error);
  }
}

function cleanupRequestChangesWorktree(
  repo: string,
  path: string,
  baseCommit: string,
  checkpointRelative: string,
): string | null {
  const head = fullHead(path);
  if (head === null) return `${path} has an unreadable transaction HEAD`;
  const status = worktreeStatus(path);
  if (status.detail !== undefined) return `${path} status is unreadable (${status.detail})`;
  if (status.paths.some((changedPath) => changedPath !== checkpointRelative)) {
    return `${path} contains unexpected changes (${status.paths.map(displayPath).join(", ")})`;
  }
  if (status.paths.length > 0) {
    const restored = git(path, ["restore", "--source", head, "--staged", "--worktree", "--", checkpointRelative]);
    if (restored.status !== 0) return `could not restore the transaction checkpoint in ${path}`;
    const afterRestore = worktreeStatus(path);
    if (afterRestore.detail !== undefined || afterRestore.paths.length > 0) {
      return `${path} was not clean after restoring its transaction checkpoint`;
    }
  }
  const ancestry = git(path, ["merge-base", "--is-ancestor", baseCommit, head]);
  if (ancestry.status !== 0 || ancestry.stderr.trim() !== "") {
    return `${path} is not a transaction child of ${baseCommit}`;
  }
  const listed = openWorktrees(repo);
  if ("detail" in listed) return `cannot verify transaction worktree registration (${listed.detail})`;
  const matches = listed.worktrees.filter((entry) => canonicalize(entry.path) === canonicalize(path));
  if (matches.length !== 1 || matches[0]?.branch !== undefined) {
    return `${path} is not the expected detached transaction worktree`;
  }
  const removed = git(repo, ["worktree", "remove", path]);
  if (removed.status !== 0) return `could not remove clean transaction worktree ${path}: ${removed.stderr.trim()}`;
  if (existsSync(path)) return `transaction worktree path ${path} remains`;
  return null;
}

export function worktreeRequestChanges(slug: string, expectedCheckpointCommit: string): WorktreeResult {
  const repo = primaryRepoRoot();
  if (repo === null) return { code: 2, out: "", err: "worktree request-changes: not inside a git repository.\n" };
  if (!SLUG_PATTERN.test(slug) || /\p{C}/u.test(slug)) {
    return { code: 2, out: "", err: `worktree request-changes: invalid slug "${printable(slug)}".\n` };
  }
  if (!/^(?:[0-9a-f]{40}|[0-9a-f]{64})$/.test(expectedCheckpointCommit)) {
    return {
      code: 2,
      out: "",
      err: "worktree request-changes: provide the full SHA of the pending app-review checkpoint-only commit.\n",
    };
  }

  const root = worktreeRoot(repo);
  const listed = openWorktrees(repo);
  if ("detail" in listed) {
    return { code: 2, out: "", err: `worktree request-changes: the worktree list is unreadable (${listed.detail}).\n` };
  }
  const checkpointRelative = `.ai-engineering/workflow/checkpoints/${slug}.json`;
  const candidates = listed.worktrees.filter((candidate) => {
    if (
      candidate.branch === undefined ||
      !existsSync(candidate.path) ||
      !existsSync(join(candidate.path, checkpointRelative))
    ) return false;
    return true;
  });
  const matching = candidates.filter((candidate) => {
    try {
      const context = resolveContext(candidate.path);
      const detectedBase = context.base;
      if (detectedBase === null) return true;
      const candidateBaseRef = `refs/heads/${detectedBase}`;
      const currentBase = git(repo, ["rev-parse", "--verify", `${candidateBaseRef}^{commit}`]);
      if (currentBase.status !== 0 || currentBase.stderr.trim() !== "") return true;
      const checkpoint = readCheckpoint(join(candidate.path, checkpointRelative), {
        repoPath: candidate.path,
        slug,
        baseRef: candidateBaseRef,
      });
      return !isStaleReviewPin(checkpoint, currentBase.stdout.trim());
    } catch {
      return true;
    }
  });
  if (matching.length > 1) {
    return {
      code: 1,
      out: "",
      err: `worktree request-changes: active checkpoint ${slug} is ambiguous across Git-listed worktrees; preserve the review state.\n`,
    };
  }
  const exactMatches = matching.filter((candidate) => {
    if (fullHead(candidate.path) !== expectedCheckpointCommit || candidate.branch === undefined) return false;
    const branchTip = git(repo, ["rev-parse", "--verify", `refs/heads/${candidate.branch}^{commit}`]);
    return branchTip.status === 0 &&
      branchTip.stderr.trim() === "" &&
      branchTip.stdout.trim() === expectedCheckpointCommit;
  });
  const entry = exactMatches.length === 1
    ? exactMatches[0]
    : matching.length === 1
      ? matching[0]
      : undefined;
  if (entry === undefined || entry.branch === undefined) {
    return {
      code: 1,
      out: "",
      err: `worktree request-changes: no exact live checkout for ${slug} in the current repository or registered Git worktrees; preserve the review state.\n`,
    };
  }

  const branchName = entry.branch;
  const branch = `refs/heads/${branchName}`;
  let baseRef: string;
  try {
    const detectedBase = resolveContext(entry.path).base;
    if (detectedBase === null) {
      return { code: 1, out: "", err: "worktree request-changes: detected base ref is unavailable.\n" };
    }
    baseRef = `refs/heads/${detectedBase}`;
  } catch {
    return { code: 1, out: "", err: "worktree request-changes: detected base ref is unreadable.\n" };
  }
  const head = fullHead(entry.path);
  const branchTip = git(repo, ["rev-parse", "--verify", `${branch}^{commit}`]);
  if (
    head !== expectedCheckpointCommit ||
    branchTip.status !== 0 ||
    branchTip.stderr.trim() !== "" ||
    branchTip.stdout.trim() !== expectedCheckpointCommit
  ) {
    return {
      code: 1,
      out: "",
      err:
        `worktree request-changes: stale checkpoint; expected ${expectedCheckpointCommit}, ` +
        `but the current ${printable(branchName)} tip is ${head ?? "unreadable"}. Return to app review; no files were changed.\n`,
    };
  }

  const checkedOutBranch = git(entry.path, ["symbolic-ref", "--quiet", "HEAD"]);
  if (
    checkedOutBranch.status !== 0 ||
    checkedOutBranch.stderr.trim() !== "" ||
    checkedOutBranch.stdout.trim() !== branch
  ) {
    return { code: 1, out: "", err: `worktree request-changes: ${entry.path} is not checked out on ${printable(branchName)}.\n` };
  }
  const status = worktreeStatus(entry.path);
  if (status.detail !== undefined || status.paths.length > 0) {
    return {
      code: 1,
      out: "",
      err:
        `worktree request-changes: ${printable(branchName)} is not clean` +
        `${status.detail ? ` (${printable(status.detail)})` : ` (${status.paths.map(displayPath).join(", ")})`}; ` +
        "preserve the review state and return to app review.\n",
    };
  }
  const operation = gitOperationState(entry.path);
  if (operation !== null) {
    return { code: 1, out: "", err: `worktree request-changes: ${printable(operation)}; preserve the review state.\n` };
  }

  const checkpointPath = join(entry.path, checkpointRelative);
  let checkpointContents: string;
  let checkpoint: Checkpoint;
  try {
    if (checkpointFileIdentity(checkpointPath, entry.path) === null) {
      return { code: 1, out: "", err: "worktree request-changes: checkpoint is not a worktree-local file.\n" };
    }
    checkpoint = readCheckpoint(checkpointPath, {
      repoPath: entry.path,
      slug,
      baseRef,
    });
    const snapshot = git(entry.path, ["show", `${expectedCheckpointCommit}:${checkpointRelative}`]);
    if (snapshot.status !== 0 || snapshot.stderr.trim() !== "") {
      return { code: 1, out: "", err: "worktree request-changes: checkpoint is missing, unreadable or malformed.\n" };
    }
    checkpointContents = snapshot.stdout;
    if (!isDeepStrictEqual(parseCheckpoint(checkpointContents, {
      repoPath: entry.path,
      slug,
      baseRef,
    }), checkpoint)) {
      return { code: 1, out: "", err: "worktree request-changes: checkpoint does not match this worktree.\n" };
    }
  } catch {
    return { code: 1, out: "", err: "worktree request-changes: checkpoint is missing, unreadable or malformed.\n" };
  }

  const lifecycle = checkpoint.lifecycle;
  if (
    lifecycle.phase !== "awaiting-app-review" ||
    lifecycle.plan_approval !== "approved" ||
    lifecycle.app_review !== "pending" ||
    !gatesComplete(checkpoint) ||
    typeof lifecycle.reviewed_base !== "string" ||
    typeof lifecycle.reviewed_feature !== "string"
  ) {
    return {
      code: 1,
      out: "",
      err: "worktree request-changes: checkpoint is not awaiting app review with pending review and complete gates.\n",
    };
  }
  const chainProblem = reviewedFeatureChainProblem(
    repo,
    slug,
    lifecycle.reviewed_base,
    lifecycle.reviewed_feature,
    expectedCheckpointCommit,
    "awaiting-app-review",
    baseRef,
  );
  if (chainProblem !== null) {
    return { code: 1, out: "", err: `worktree request-changes: ${chainProblem}; preserve the review state.\n` };
  }

  const nextPlan: Checkpoint = {
    ...checkpoint,
    lifecycle: {
      ...lifecycle,
      phase: "implementation",
      app_review: "not-started",
      reviewed_base: null,
      reviewed_feature: null,
      base_ref: null,
    },
  };
  const nextContents = serializeCheckpoint(nextPlan);
  const identity = commitIdentityEnv(repo);
  if (identity instanceof Error) {
    return { code: 1, out: "", err: `worktree request-changes: cannot commit the checkpoint: ${identity.message}; no files were changed.\n` };
  }

  // No slug in the name: the checkpoint path below repeats it, and with the temporary
  // file's UUID a long slug pushed paths past Windows' 260-character MAX_PATH.
  const transactionPath = join(root, `.ai-eng-changes-${randomUUID()}`);
  const added = git(repo, ["worktree", "add", "--detach", transactionPath, expectedCheckpointCommit]);
  if (added.status !== 0) {
    return {
      code: 1,
      out: "",
      err: `worktree request-changes: could not prepare a detached checkpoint transaction (${printable(added.stderr.trim())}).\n`,
    };
  }

  const transactionCheckpoint = join(transactionPath, checkpointRelative);
  let transactionMode: number;
  let transactionPlan: Checkpoint;
  try {
    const stat = checkpointFileIdentity(transactionCheckpoint, transactionPath);
    if (stat === null) {
      const cleanup = cleanupRequestChangesWorktree(repo, transactionPath, expectedCheckpointCommit, checkpointRelative);
      return {
        code: 1,
        out: "",
        err: `worktree request-changes: transaction checkpoint is not worktree-local${cleanup ? `; ${cleanup}` : ""}.\n`,
      };
    }
    transactionMode = stat.mode;
    transactionPlan = readCheckpoint(transactionCheckpoint, {
      repoPath: transactionPath,
      slug,
      baseRef,
    });
  } catch {
    const cleanup = cleanupRequestChangesWorktree(repo, transactionPath, expectedCheckpointCommit, checkpointRelative);
    return {
      code: 1,
      out: "",
      err: `worktree request-changes: transaction checkpoint is unreadable${cleanup ? `; ${cleanup}` : ""}.\n`,
    };
  }
  if (!isDeepStrictEqual(transactionPlan, checkpoint)) {
    const cleanup = cleanupRequestChangesWorktree(repo, transactionPath, expectedCheckpointCommit, checkpointRelative);
    return {
      code: 1,
      out: "",
      err: `worktree request-changes: transaction checkpoint differs from the captured review${cleanup ? `; ${cleanup}` : ""}.\n`,
    };
  }
  const writeError = replaceFileAtomically(transactionCheckpoint, nextContents, transactionMode);
  if (writeError !== null) {
    const cleanup = cleanupRequestChangesWorktree(repo, transactionPath, expectedCheckpointCommit, checkpointRelative);
    return {
      code: 1,
      out: "",
      err: `worktree request-changes: could not write the transaction checkpoint (${printable(writeError)})${cleanup ? `; ${cleanup}` : ""}.\n`,
    };
  }

  const staged = git(transactionPath, ["add", "--", checkpointRelative]);
  const stagedPaths = git(transactionPath, ["diff", "--cached", "--name-only", "--no-renames", "-z"]);
  if (
    staged.status !== 0 ||
    staged.stderr.trim() !== "" ||
    stagedPaths.status !== 0 ||
    stagedPaths.stderr.trim() !== "" ||
    stagedPaths.stdout.split("\0").filter(Boolean).join("\0") !== checkpointRelative
  ) {
    const cleanup = cleanupRequestChangesWorktree(repo, transactionPath, expectedCheckpointCommit, checkpointRelative);
    return {
      code: 1,
      out: "",
      err: `worktree request-changes: could not stage only the lifecycle checkpoint${cleanup ? `; ${cleanup}` : ""}.\n`,
    };
  }

  const committed = runGit(["commit", "-m", `chore(${slug}): record requested changes`], { cwd: transactionPath, isolated: true, env: identity });
  if (committed.status !== 0) {
    const cleanup = cleanupRequestChangesWorktree(repo, transactionPath, expectedCheckpointCommit, checkpointRelative);
    return {
      code: 1,
      out: "",
      err:
        `worktree request-changes: checkpoint commit failed${committed.stderr.trim() ? `: ${printable(committed.stderr.trim())}` : ""}` +
        `${cleanup ? `; ${cleanup}` : ""}; the feature worktree was not changed.\n`,
    };
  }

  const transitionCommit = fullHead(transactionPath);
  const parents = transitionCommit === null
    ? null
    : git(transactionPath, ["rev-list", "--parents", "-n", "1", transitionCommit]);
  const changedPaths = transitionCommit === null
    ? null
    : git(transactionPath, ["diff-tree", "--no-commit-id", "--name-only", "-r", "--no-renames", "-z", transitionCommit]);
  const clean = worktreeStatus(transactionPath);
  let transitionedPlan: Checkpoint | null = null;
  try {
    const committedCheckpoint = git(transactionPath, ["show", `${transitionCommit}:${checkpointRelative}`]);
    if (committedCheckpoint.status === 0 && committedCheckpoint.stderr.trim() === "") {
      transitionedPlan = parseCheckpoint(committedCheckpoint.stdout, {
        repoPath: transactionPath,
        slug,
        baseRef,
      });
    }
  } catch {
    // The verification below refuses an unreadable commit.
  }
  const transitionedLifecycle = transitionedPlan?.lifecycle;
  if (
    transitionCommit === null ||
    parents?.status !== 0 ||
    parents.stderr.trim() !== "" ||
    parents.stdout.trim() !== `${transitionCommit} ${expectedCheckpointCommit}` ||
    changedPaths?.status !== 0 ||
    changedPaths.stderr.trim() !== "" ||
    changedPaths.stdout.split("\0").filter(Boolean).join("\0") !== checkpointRelative ||
    clean.detail !== undefined ||
    clean.paths.length > 0 ||
    transitionedLifecycle?.phase !== "implementation" ||
    transitionedLifecycle.app_review !== "not-started" ||
    transitionedLifecycle.reviewed_base !== null ||
    transitionedLifecycle.reviewed_feature !== null ||
    transitionedLifecycle.base_ref !== null ||
    !isDeepStrictEqual(transitionedPlan, nextPlan)
  ) {
    return {
      code: 1,
      out: "",
      err:
        `worktree request-changes: the checkpoint commit could not be verified as a checkpoint-only child of ` +
        `${expectedCheckpointCommit}; preserve the detached transaction worktree at ${transactionPath}. ` +
        "The feature worktree was not changed.\n",
    };
  }

  const currentBranchTip = git(repo, ["rev-parse", "--verify", `${branch}^{commit}`]);
  const currentStatus = worktreeStatus(entry.path);
  if (
    fullHead(entry.path) !== expectedCheckpointCommit ||
    currentBranchTip.status !== 0 ||
    currentBranchTip.stderr.trim() !== "" ||
    currentBranchTip.stdout.trim() !== expectedCheckpointCommit ||
    currentStatus.detail !== undefined ||
    currentStatus.paths.length > 0
  ) {
    const cleanup = cleanupRequestChangesWorktree(repo, transactionPath, expectedCheckpointCommit, checkpointRelative);
    return {
      code: 1,
      out: "",
      err:
        `worktree request-changes: stale checkpoint; expected ${expectedCheckpointCommit}. Return to app review; ` +
        `${cleanup ? ` ${cleanup}` : "the feature worktree is unchanged"}.\n`,
    };
  }
  const published = git(repo, ["update-ref", branch, transitionCommit, expectedCheckpointCommit]);
  if (published.status !== 0) {
    const cleanup = cleanupRequestChangesWorktree(repo, transactionPath, expectedCheckpointCommit, checkpointRelative);
    return {
      code: 1,
      out: "",
      err:
        `worktree request-changes: compare-and-swap lost; ${printable(branchName)} no longer points to ` +
        `${expectedCheckpointCommit}. Return to app review; ${cleanup ? `${cleanup}.` : "the feature worktree is unchanged"}\n`,
    };
  }

  const sourceStatus = worktreeStatus(entry.path);
  let sourceCheckpoint: Checkpoint | null = null;
  try {
    sourceCheckpoint = readCheckpoint(checkpointPath, {
      repoPath: entry.path,
      slug,
      baseRef,
    });
  } catch {
    // A failed read below rolls back only if the exact feature ref still matches.
  }
  if (
    fullHead(entry.path) !== transitionCommit ||
    sourceStatus.detail !== undefined ||
    sourceStatus.paths.length !== 1 ||
    sourceStatus.paths[0] !== checkpointRelative ||
    !isDeepStrictEqual(sourceCheckpoint, checkpoint)
  ) {
    const rollback = git(repo, ["update-ref", branch, expectedCheckpointCommit, transitionCommit]);
    const cleanup = cleanupRequestChangesWorktree(repo, transactionPath, expectedCheckpointCommit, checkpointRelative);
    return {
      code: 1,
      out: "",
      err:
        `worktree request-changes: published checkpoint could not be synchronized safely` +
        `${rollback.status === 0 ? "; the ref was rolled back" : "; preserve the published ref and worktree"}` +
        `${cleanup ? `; ${cleanup}` : ""}.\n`,
    };
  }

  const synchronized = git(entry.path, [
    "restore",
    `--source=${transitionCommit}`,
    "--staged",
    "--worktree",
    "--",
    checkpointRelative,
  ]);
  const synchronizedStatus = worktreeStatus(entry.path);
  if (
    synchronized.status !== 0 ||
    synchronized.stderr.trim() !== "" ||
    fullHead(entry.path) !== transitionCommit ||
    synchronizedStatus.detail !== undefined ||
    synchronizedStatus.paths.length > 0
  ) {
    const rollback = git(repo, ["update-ref", branch, expectedCheckpointCommit, transitionCommit]);
    let restored = false;
    if (rollback.status === 0) {
      const currentStatus = worktreeStatus(entry.path);
      let currentContents: Checkpoint | null = null;
      try {
        currentContents = readCheckpoint(checkpointPath, {
          repoPath: entry.path,
          slug,
          baseRef,
        });
      } catch {
        // Leave unreadable work untouched.
      }
      if (
        currentStatus.detail === undefined &&
        currentStatus.paths.every((changedPath) => changedPath === checkpointRelative) &&
        (isDeepStrictEqual(currentContents, checkpoint) || isDeepStrictEqual(currentContents, nextPlan))
      ) {
        const restore = git(entry.path, [
          "restore",
          `--source=${expectedCheckpointCommit}`,
          "--staged",
          "--worktree",
          "--",
          checkpointRelative,
        ]);
        const afterRestore = worktreeStatus(entry.path);
        restored =
          restore.status === 0 &&
          restore.stderr.trim() === "" &&
          afterRestore.detail === undefined &&
          afterRestore.paths.length === 0;
      }
    }
    const cleanup = cleanupRequestChangesWorktree(repo, transactionPath, expectedCheckpointCommit, checkpointRelative);
    return {
      code: 1,
      out: "",
      err:
        `worktree request-changes: could not synchronize the committed checkpoint` +
        `${rollback.status === 0 && restored ? "; the ref and checkpoint were restored" : "; preserve the ref and worktree"}` +
        `${cleanup ? `; ${cleanup}` : ""}.\n`,
    };
  }

  const cleanup = cleanupRequestChangesWorktree(repo, transactionPath, expectedCheckpointCommit, checkpointRelative);
  if (cleanup !== null) {
    return {
      code: 1,
      out: "",
      err: `worktree request-changes: transition ${transitionCommit} succeeded, but ${cleanup}; preserve the feature worktree.\n`,
    };
  }
  return {
    code: 0,
    out: `✓ request changes ${slug}: checkpoint ${transitionCommit} → implementation; rerun affected gates before renewed app review.\n`,
    err: "",
  };
}

/** The managed worktree a slug names, or null: it must live at the path derived
 *  from its branch under the configured worktrees root. */
function findManagedWorktree(
  repo: string,
  root: string,
  slug: string,
  worktrees: { path: string; branch: string | undefined }[],
  branch = `feat/${slug}`,
): { path: string; branch: string } | null {
  const directoryName = branch.startsWith("feat/") ? branch.slice("feat/".length) : branch;
  const managedPath = canonicalize(resolve(root, directoryName));
  const managedRoot = `${canonicalize(root)}${sep}`;
  const primary = canonicalize(repo);
  const entry = worktrees.find((candidate) => {
    const path = canonicalize(candidate.path);
    if (path === primary) return false;
    return path.startsWith(managedRoot) && path === managedPath && candidate.branch === branch;
  });
  if (entry === undefined || entry.branch === undefined) return null;
  return { path: entry.path, branch: entry.branch };
}

function fullHead(repo: string): string | null {
  const current = git(repo, ["rev-parse", "--verify", "HEAD"]);
  if (current.status !== 0 || current.stderr.trim() !== "") return null;
  const commit = current.stdout.trim();
  return /^(?:[0-9a-f]{40}|[0-9a-f]{64})$/.test(commit) ? commit : null;
}

export function worktreeRm(slug: string, force = false): WorktreeResult {
  const repo = primaryRepoRoot();
  if (repo === null) return { code: 2, out: "", err: "worktree rm: not inside a git repository.\n" };
  const root = worktreeRoot(repo);
  const listed = openWorktrees(repo);
  if ("detail" in listed) {
    return { code: 2, out: "", err: `worktree rm: the worktree list is unreadable (${listed.detail}).\n` };
  }
  const entry = [slug, `feat/${slug}`]
    .map((branch) => findManagedWorktree(repo, root, slug, listed.worktrees, branch))
    .find((candidate) => candidate !== null) ?? null;
  if (entry === null) {
    return {
      code: 1,
      out: "",
      err: `worktree rm: no managed worktree for branch or slug "${printable(slug)}" under ${canonicalize(root)}.\n`,
    };
  }

  const branch = entry.branch;
  // Scan before ancestry checks so a later --force retry cannot hide the data-loss cost.
  const hasWorktreePath = existsSync(entry.path);
  const dropped = hasWorktreePath ? ignoredPaths(entry.path) : [];
  if (dropped === null) {
    return {
      code: 1,
      out: "",
      err: `worktree rm: refusing to remove ${entry.path} because ignored files could not be inspected; preserve the worktree and retry after \`git -C ${entry.path} status --ignored --short\` succeeds.\n`,
    };
  }
  if (dropped.length > 0 && !force) {
    return {
      code: 1,
      out: "",
      err:
        `worktree rm: refusing to remove ${entry.path}; ignored files would be permanently deleted: ` +
        `${dropped.map(displayPath).join(", ")}. Preserve them or rerun \`ai-eng worktree rm ${slug} --force\` ` +
        "only if you intend to permanently delete those files.\n",
    };
  }
  // Refuse before touching anything: the default delete deletes only a branch that
  // proved it landed in the detected base, and a refusal must leave the worktree and
  // the branch exactly as they were. `merge-base --is-ancestor` pins both refs, so
  // the answer never depends on the mutable HEAD. Only an explicit `--force` skips
  // the proof, for the deliberately abandoned branch, and so needs no base at all.
  if (!force) {
    let baseBranch: string | null;
    try {
      baseBranch = namedBase(process.cwd());
    } catch (error) {
      return { code: 1, out: "", err: `worktree rm: cannot detect the base (${error instanceof Error ? error.message : String(error)}); then rerun \`ai-eng worktree rm ${slug}\`.\n` };
    }
    if (baseBranch === null) {
      return {
        code: 1,
        out: "",
        err: `worktree rm: no base branch is detectable; set [git] base in ${join(repo, ".ai-engineering", "config.toml")}, then rerun \`ai-eng worktree rm ${slug}\`.\n`,
      };
    }
    const baseRef = `refs/heads/${baseBranch}`;
    const baseLabel = baseBranch === "main" ? "local main" : `detected base ${baseRef}`;
    const merged = git(repo, ["merge-base", "--is-ancestor", branch, baseRef]);
    if (merged.status !== 0) {
      return {
        code: 1,
        out: "",
        err: `worktree rm: ${branch} is not merged into the ${baseLabel} — refusing to delete it, and ${entry.path} is left in place. Pass \`ai-eng worktree rm ${slug} --force\` to remove a deliberately abandoned branch.\n`,
      };
    }
  }

  if (hasWorktreePath) {
    const status = worktreeStatus(entry.path);
    if (status.detail !== undefined || status.paths.length > 0) {
      const state = status.detail === undefined
        ? `dirty files: ${status.paths.map(displayPath).join(", ")}`
        : `status unreadable: ${printable(status.detail)}`;
      return {
        code: 1,
        out: "",
        err: `worktree rm: refusing to delete ${entry.path} with ${state}; preserve or commit that work, inspect \`git -C ${entry.path} status --short\`, then rerun \`ai-eng worktree rm ${slug}\`.\n`,
      };
    }
    if (dropped.length > 0) {
      process.stderr.write(
        `worktree rm: --force will permanently delete ignored files: ${dropped.map(displayPath).join(", ")}\n`,
      );
    }
    const removed = git(repo, ["worktree", "remove", entry.path]);
    if (removed.status !== 0) {
      const pathRemains = existsSync(entry.path);
      const branchRef = git(repo, ["show-ref", "--verify", "--quiet", `refs/heads/${branch}`]);
      const branchState =
        branchRef.status === 0
          ? `branch ${branch} remains`
          : branchRef.status === 1 && branchRef.stderr.trim() === ""
            ? `branch ${branch} is absent`
            : `branch ${branch} could not be verified (${branchRef.stderr.trim() || `git show-ref exited ${branchRef.status}`})`;
      return {
        code: 1,
        out: "",
        err:
          `worktree rm: git worktree remove failed: ${removed.stderr.trim()}; ` +
          `${pathRemains ? `worktree path ${entry.path} remains, but its contents may be partial` : `worktree path ${entry.path} is gone despite the failure`}; ` +
          `${branchState}${ignoredRemovalNote(dropped, pathRemains ? "unknown" : "removed")}\n`,
      };
    }
  } else {
    // The directory is gone: prune the stale registration instead of failing on it.
    git(repo, ["worktree", "prune"]);
  }
  const deleted = git(repo, ["branch", force ? "-D" : "-d", branch]);
  if (deleted.status !== 0) {
    const branchRef = git(repo, ["show-ref", "--verify", "--quiet", `refs/heads/${branch}`]);
    const branchState =
      branchRef.status === 0
        ? `branch ${branch} remains`
        : branchRef.status === 1 && branchRef.stderr.trim() === ""
          ? `branch ${branch} is absent`
          : `branch ${branch} could not be verified (${branchRef.stderr.trim() || `git show-ref exited ${branchRef.status}`})`;
    return {
      code: 1,
      out: "",
      err:
        `worktree rm: worktree ${slug} was removed, but git branch ${force ? "-D" : "-d"} failed: ${deleted.stderr.trim()}; ` +
        `${branchState}${ignoredRemovalNote(dropped, "removed")}\n`,
    };
  }

  const droppedNote = ignoredRemovalNote(dropped, "removed");
  return {
    code: 0,
    out: force
      ? `✓ removed worktree ${slug} — deleted ${branch} with --force, without proving it was merged${droppedNote}\n`
      : `✓ removed worktree ${slug}${droppedNote}\n`,
    err: "",
  };
}
