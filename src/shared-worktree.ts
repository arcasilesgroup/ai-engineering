// src/shared-worktree.ts — where a worktree lives, what a slug may be, and the git
// argv the `ai-eng worktree` verb runs. It sits in the shared layer because the
// design-slot list is needed by both this verb and `ai-eng spec`, and shared may not
// import spec — so the one definition moves down rather than up (arch.rules.json).
// Every git value is an argv element: no command is ever assembled as a shell string.

import { existsSync, lstatSync, mkdirSync, readFileSync, realpathSync } from "node:fs";
import { randomUUID } from "node:crypto";
import { basename, isAbsolute, join, relative, resolve, sep } from "node:path";
import { spawnSync } from "node:child_process";
import { loadConfig, printable } from "./env.ts";

/** The four artifacts of a milestone. `spec open` scaffolds two and `spec close`
 *  sweeps all four; `ai-eng spec` is its only consumer. */
export const SLOT_FILES = ["spec.html", "plan.html", "brainstorm.html", "recap.html"] as const;

/** The design artifacts that must be committed before a worktree is cut
 *  (AGENTS.md `## Git workflow`). `recap.html` is absent on purpose: it is
 *  generated at the app review and arrives with the merge, so a dirty one must
 *  not block. One definition here, distinct from the `spec close` sweep. */
export const PRE_WORKTREE_SLOTS = ["brainstorm.html", "spec.html", "plan.html"] as const;

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

interface GitRun {
  status: number;
  stdout: string;
  stderr: string;
}

function git(cwd: string, args: string[]): GitRun {
  const done = spawnSync("git", args, { cwd, encoding: "utf8" });
  return { status: done.status ?? 1, stdout: done.stdout ?? "", stderr: done.stderr ?? "" };
}

/** git reports canonical paths — so the worktree root, and every comparison
 *  against a registered path, happens in the same realpathed form. */
function canonicalize(path: string): string {
  try {
    return realpathSync(path);
  } catch {
    return resolve(path);
  }
}

/** Whether a status path names a design slot: the slot itself, or anything nested
 *  under it when the slot was replaced by a directory. Both sides are compared as
 *  git and the filesystem name them (realpath, then case-folded — a case alias of
 *  the slot is the same file on a case-insensitive filesystem, and refusing one is
 *  the fail-closed side of the comparison on a case-sensitive one). */
function namesSlot(repo: string, path: string): string | null {
  const key = canonicalize(join(repo, path)).toLowerCase();
  for (const name of PRE_WORKTREE_SLOTS) {
    const slot = `.ai-engineering/${name}`;
    const slotKey = canonicalize(join(repo, slot)).toLowerCase();
    if (key === slotKey || key.startsWith(`${slotKey}/`)) return slot;
  }
  return null;
}

/** The primary checkout, asked of git — never the nearest `.git`, which inside a
 *  session worktree is that worktree. The common git dir of a non-bare repository is
 *  `<primary>/.git`, so its parent is the primary tree; anything else (bare repo,
 *  submodule) is refused rather than guessed. Every verb reasons about the primary
 *  tree and cuts the worktree from it. */
function primaryRepoRoot(): string | null {
  const cwd = process.cwd();
  const common = git(cwd, ["rev-parse", "--git-common-dir"]);
  if (common.status !== 0) return null;
  const dir = common.stdout.trim();
  if (dir === "" || basename(dir) !== ".git") return null;
  const root = canonicalize(resolve(cwd, join(dir, "..")));
  return existsSync(root) ? root : null;
}

/** `<repo>.worktrees` beside the repository, or `[git].worktrees_dir` from the
 *  primary checkout's `.ai-engineering/config.toml` when that key is present. The
 *  config is read from the primary tree, so a relative value is resolved there too:
 *  resolving it against the process directory would make the same repository report
 *  one root from the primary tree and another from inside an open worktree. */
export function worktreeRoot(repo: string): string {
  const configured = loadConfig(repo).git?.["worktrees_dir"];
  if (typeof configured === "string" && configured.trim()) return canonicalize(resolve(repo, configured.trim()));
  return `${repo}.worktrees`;
}

interface OpenWorktree {
  path: string;
  /** The branch short name, absent when the worktree is detached. */
  branch: string | undefined;
  /** What the user typed: the branch with the `feat/` prefix removed. */
  slug: string;
  detached: boolean;
}

/** Every worktree git knows, or the reason it could not be read — a list that cannot
 *  be read is never an empty list, because that would let a guard pass unexamined. */
function openWorktrees(repo: string): { worktrees: OpenWorktree[] } | { detail: string } {
  const listed = git(repo, ["worktree", "list", "--porcelain"]);
  if (listed.status !== 0) {
    return { detail: `git worktree list exited ${listed.status}: ${listed.stderr.trim()}` };
  }
  const worktrees: OpenWorktree[] = [];
  for (const block of listed.stdout.split("\n\n")) {
    if (block.trim() === "") continue;
    const lines = block.split("\n");
    const pathLine = lines.find((line) => line.startsWith("worktree "));
    if (!pathLine) return { detail: `unreadable worktree list entry ${JSON.stringify(printable(block))}` };
    const path = pathLine.slice("worktree ".length);
    const ref = lines.find((line) => line.startsWith("branch "))?.slice("branch ".length);
    const branch = ref?.startsWith("refs/heads/") ? ref.slice("refs/heads/".length) : undefined;
    worktrees.push({
      path,
      branch,
      slug: branch === undefined ? basename(path) : branch.replace(/^feat\//, ""),
      detached: lines.includes("detached"),
    });
  }
  return { worktrees };
}

/** Why a cut is refused: a slot change seen at `path`, or the status detail
 *  that could not be read. A guard that cannot decide denies. */
type SlotBlocker = { path: string } | { detail: string };

/** The paths one `-z` record carries and how many tokens it used. `-z` keeps every
 *  path as raw bytes — NUL-separated, nothing quoted and nothing C-escaped, so no
 *  path ever needs unescaping and a non-ASCII one cannot slip past a comparison.
 *  A rename or copy (R/C in either status column) carries its source as the next
 *  token. null means the record is unreadable, which blocks. */
function statusPaths(tokens: string[], index: number): { paths: string[]; next: number } | null {
  const record = tokens[index];
  if (record === undefined || record.length < 4 || record[2] !== " ") return null;
  const path = record.slice(3);
  const renamed = record.slice(0, 2).split("").some((flag) => flag === "R" || flag === "C");
  if (!renamed) return { paths: [path], next: index + 1 };
  const source = tokens[index + 1];
  if (source === undefined || source === "") return null;
  return { paths: [path, source], next: index + 2 };
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
    if (read === null) break;
    if (token.startsWith("!! ")) found.push(...read.paths);
    index = read.next;
  }
  return found;
}

/** The first design slot touched in the primary tree, or null. A slot counts as
 *  touched when a status record carries its path, the path a rename took it from, or
 *  anything nested under it (a slot replaced by a directory) — and an unreadable
 *  record blocks rather than passes.
 *
 *  The ceiling is git's own: a slot edit that git refuses to report (`assume-unchanged`,
 *  `skip-worktree`) or one hidden by `.gitignore` never reaches this status, and a slot
 *  that is a symlink is compared under its repository path, so an edit written through
 *  the link — to a target inside or outside the repository — is likewise invisible. Both
 *  are deliberate — the guard refuses what it cannot decide, and a status it cannot read
 *  has no record to inspect; neither is evidence that the primary tree is clean. */
function dirtySlot(repo: string): SlotBlocker | null {
  // `-uall` lists each untracked file instead of collapsing a wholly untracked
  // directory to `?? .ai-engineering/`, so an uncommitted slot is still seen; `-z`
  // carries the paths raw, so a quoted or escaped one is never misread.
  const status = git(repo, ["status", "--porcelain", "-uall", "-z"]);
  if (status.status !== 0) return { detail: `git status exited ${status.status}` };
  const tokens = status.stdout.split("\0");
  for (let index = 0; index < tokens.length; ) {
    if (tokens[index] === "") {
      index += 1; // the NUL that closes the last record
      continue;
    }
    const read = statusPaths(tokens, index);
    if (read === null) return { detail: `unreadable status record ${JSON.stringify(printable(tokens[index] ?? ""))}` };
    for (const path of read.paths) {
      const slot = namesSlot(repo, path);
      if (slot !== null) return { path: slot };
    }
    index = read.next;
  }
  return null;
}

export function worktreeNew(slug: string): WorktreeResult {
  const repo = primaryRepoRoot();
  if (repo === null) return { code: 2, out: "", err: "worktree new: not inside a git repository.\n" };
  // A slug is a branch-name fragment and a directory name: the pattern alone would
  // accept `alpha\n` (`$` matches before a final newline), and git would only refuse
  // the ref after the worktree root had already been created.
  if (!SLUG_PATTERN.test(slug) || /\p{C}/u.test(slug)) {
    return {
      code: 2,
      out: "",
      err: `worktree new: invalid slug "${printable(slug)}" — it must match ${SLUG_PATTERN} and carry no control character (no spaces, no "/", never starting with a separator).\n`,
    };
  }
  const blocked = dirtySlot(repo);
  if (blocked !== null) {
    return {
      code: 2,
      out: "",
      err:
        "path" in blocked
          ? `worktree new: ${blocked.path} has uncommitted changes in the primary tree — commit the design slot before opening a worktree.\n`
          : `worktree new: the primary tree's status is unreadable (${JSON.stringify(blocked.detail)}) — refusing to cut a worktree while the design slots are unknown.\n`,
    };
  }

  const root = worktreeRoot(repo);
  const target = join(root, slug);
  const branch = `feat/${slug}`;
  mkdirSync(root, { recursive: true });
  const added = git(repo, ["worktree", "add", target, "-b", branch, "refs/heads/main"]);
  if (added.status !== 0) {
    return { code: 1, out: "", err: `worktree new: git worktree add failed: ${added.stderr.trim()}\n` };
  }
  git(repo, ["config", `branch.${branch}.remote`, "."]);
  git(repo, ["config", `branch.${branch}.merge`, "refs/heads/main"]);

  return {
    code: 0,
    out: `✓ worktree ${slug} → ${target}\n`,
    err: "",
  };
}

interface StatusRead {
  paths: string[];
  detail?: string;
}

function worktreeStatus(path: string): StatusRead {
  const status = git(path, ["--no-optional-locks", "status", "--porcelain", "--untracked-files=all", "-z"]);
  if (status.status !== 0 || status.stderr.trim() !== "") {
    return { paths: [], detail: status.stderr.trim() || `git status exited ${status.status}` };
  }
  const paths: string[] = [];
  const tokens = status.stdout.split("\0");
  for (let index = 0; index < tokens.length; ) {
    if (tokens[index] === "") {
      index += 1;
      continue;
    }
    const read = statusPaths(tokens, index);
    if (read === null) return { paths: [], detail: "unreadable git status record" };
    paths.push(...read.paths);
    index = read.next;
  }
  return { paths: [...new Set(paths)] };
}

function hooksRoot(repo: string): string | null {
  const configured = git(repo, ["config", "--path", "--get", "core.hooksPath"]);
  if (configured.status !== 0 || configured.stderr.trim() !== "") return null;
  const hookPath = configured.stdout.trim();
  const root = canonicalize(isAbsolute(hookPath) ? hookPath : resolve(repo, hookPath));
  const primaryRoot = canonicalize(repo);
  return root !== primaryRoot && root.startsWith(`${primaryRoot}${sep}`) ? root : null;
}

function untrackedPaths(repo: string): { paths: string[] } | { detail: string } {
  const untracked = git(repo, ["ls-files", "--others", "--exclude-standard", "-z"]);
  if (untracked.status !== 0 || untracked.stderr.trim() !== "") {
    return { detail: untracked.stderr.trim() || `git ls-files exited ${untracked.status}` };
  }
  return { paths: untracked.stdout.split("\0").filter(Boolean) };
}

function isUnderHooksRoot(repo: string, path: string, root: string | null): boolean {
  if (root === null) return false;
  const absolutePath = canonicalize(join(repo, path));
  return absolutePath === root || absolutePath.startsWith(`${root}${sep}`);
}

function primaryStatus(repo: string): StatusRead {
  const status = worktreeStatus(repo);
  if (status.detail !== undefined) return status;
  const untracked = untrackedPaths(repo);
  if ("detail" in untracked) return { paths: [], detail: untracked.detail };
  const untrackedSet = new Set(untracked.paths);
  const configuredHooksRoot = hooksRoot(repo);
  return {
    paths: status.paths.filter((path) => {
      return !untrackedSet.has(path) || !isUnderHooksRoot(repo, path, configuredHooksRoot);
    }),
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

const LIFECYCLE_PHASES = new Set([
  "awaiting-plan-approval",
  "implementation",
  "blocked",
  "awaiting-app-review",
  "ready-to-merge",
]);

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

function checkpointShapeValid(plan: unknown): boolean {
  if (!isRecord(plan) || !Array.isArray(plan.checkpoints) || plan.checkpoints.length === 0) return false;
  return plan.checkpoints.every((checkpoint) => {
    if (
      !isRecord(checkpoint) ||
      (checkpoint.status !== "pending" && checkpoint.status !== "passed") ||
      !isRecord(checkpoint.gates)
    ) {
      return false;
    }
    const gates = checkpoint.gates;
    const gateNames = ["behavior", "ui", "review"];
    if (!gateNames.every((name) => {
      const gate = gates[name];
      return isRecord(gate) && ["pending", "failed", "passed", "n/a"].includes(String(gate.status));
    })) return false;
    return checkpoint.status !== "passed" || gateNames.every((name) => {
      const gate = gates[name];
      return isRecord(gate) && (gate.status === "passed" || gate.status === "n/a");
    });
  });
}

function lifecycleFields(plan: unknown): Record<string, unknown> | null {
  if (!checkpointShapeValid(plan) || !isRecord(plan) || !isRecord(plan.lifecycle)) return null;
  const lifecycle = plan.lifecycle;
  const lifecycleKeys = Object.keys(lifecycle);
  if (
    lifecycleKeys.length < 4 ||
    lifecycleKeys.length > 5 ||
    lifecycleKeys.some((key) => !["phase", "plan_approval", "app_review", "reviewed_main", "reviewed_feature"].includes(key))
  ) return null;
  if (
    typeof lifecycle.phase !== "string" ||
    !LIFECYCLE_PHASES.has(lifecycle.phase) ||
    !["pending", "approved"].includes(String(lifecycle.plan_approval)) ||
    !["not-started", "pending", "approved"].includes(String(lifecycle.app_review)) ||
    (lifecycle.reviewed_main !== null &&
      (typeof lifecycle.reviewed_main !== "string" || !/^(?:[0-9a-f]{40}|[0-9a-f]{64})$/.test(lifecycle.reviewed_main))) ||
    (lifecycle.reviewed_feature !== undefined &&
      lifecycle.reviewed_feature !== null &&
      (typeof lifecycle.reviewed_feature !== "string" ||
        !/^(?:[0-9a-f]{40}|[0-9a-f]{64})$/.test(lifecycle.reviewed_feature)))
  ) {
    return null;
  }
  const phase = lifecycle.phase;
  const approval = lifecycle.plan_approval;
  const review = lifecycle.app_review;
  const reviewedMain = lifecycle.reviewed_main;
  if (
    (phase === "awaiting-plan-approval" &&
      (approval !== "pending" || review !== "not-started" || reviewedMain !== null)) ||
    (phase === "implementation" &&
      (approval !== "approved" || review !== "not-started" || reviewedMain !== null)) ||
    (phase === "awaiting-app-review" &&
      (approval !== "approved" || review !== "pending" || typeof reviewedMain !== "string")) ||
    (phase === "ready-to-merge" &&
      (approval !== "approved" || review !== "approved" || typeof reviewedMain !== "string" ||
        typeof lifecycle.reviewed_feature !== "string")) ||
    (phase === "blocked" &&
      (approval === "pending"
        ? review !== "not-started" || reviewedMain !== null
        : review === "not-started"
          ? reviewedMain !== null
          : typeof reviewedMain !== "string"))
  ) {
    return null;
  }
  return lifecycle;
}

function gatesComplete(plan: unknown): boolean {
  if (!isRecord(plan) || !Array.isArray(plan.checkpoints) || plan.checkpoints.length === 0) return false;
  return plan.checkpoints.every((checkpoint) => {
    if (!isRecord(checkpoint) || checkpoint.status !== "passed" || !isRecord(checkpoint.gates)) return false;
    const gates = checkpoint.gates;
    return ["behavior", "ui", "review"].every((name) => {
      const gate = gates[name];
      return isRecord(gate) && (gate.status === "passed" || gate.status === "n/a");
    });
  });
}

function rebaseGatesComplete(plan: unknown): boolean {
  if (!gatesComplete(plan) || !isRecord(plan) || !Array.isArray(plan.checkpoints)) return false;
  return plan.checkpoints.every((checkpoint) => {
    if (!isRecord(checkpoint) || !isRecord(checkpoint.gates)) return false;
    const gates = checkpoint.gates;
    return ["behavior", "review"].every((name) => {
      const gate = gates[name];
      return isRecord(gate) && gate.status === "passed";
    });
  });
}

function lifecycleStatus(
  checkpointPath: string,
  worktreePath: string,
  slug: string,
  currentMain: string | null,
  repo: string,
  branch: string,
): { label: string; files: string[] } {
  let parsed: unknown;
  try {
    const checkpointStat = lstatSync(checkpointPath);
    const checkpointRelative = relative(canonicalize(worktreePath), realpathSync(checkpointPath));
    if (
      !checkpointStat.isFile() ||
      checkpointStat.isSymbolicLink() ||
      checkpointRelative === "" ||
      checkpointRelative === ".." ||
      checkpointRelative.startsWith(`..${sep}`) ||
      isAbsolute(checkpointRelative)
    ) {
      return { label: "unknown (checkpoint is not a worktree-local file)", files: [] };
    }
    parsed = JSON.parse(readFileSync(checkpointPath, "utf8"));
  } catch {
    return { label: "unknown (missing, unreadable or malformed checkpoint)", files: [] };
  }
  const files = checkpointFiles(parsed, slug);
  if (files === null) return { label: "unknown (checkpoint does not match this worktree)", files: [] };
  if (!isRecord(parsed) || !Object.hasOwn(parsed, "lifecycle")) {
    return { label: "unknown (legacy checkpoint without lifecycle)", files };
  }
  const lifecycle = lifecycleFields(parsed);
  if (lifecycle === null) return { label: "unknown (contradictory lifecycle)", files };
  const phase = lifecycle.phase as string;
  if (["awaiting-app-review", "ready-to-merge"].includes(phase) && !gatesComplete(parsed)) {
    return { label: "unknown (lifecycle gates are incomplete)", files };
  }
  if (lifecycle.reviewed_main !== null) {
    if (typeof lifecycle.reviewed_main !== "string") return { label: "unknown (invalid reviewed_main)", files };
    const exists = git(repo, ["cat-file", "-e", `${lifecycle.reviewed_main}^{commit}`]);
    if (exists.status !== 0) return { label: "unknown (invalid reviewed_main)", files };
    if (currentMain === null || lifecycle.reviewed_main !== currentMain) {
      return { label: "unknown (reviewed_main is stale)", files };
    }
  }
  if (phase === "ready-to-merge") {
    const reviewedFeature = lifecycle.reviewed_feature;
    const featureRef = git(repo, ["rev-parse", "--verify", `refs/heads/${branch}^{commit}`]);
    if (
      typeof reviewedFeature !== "string" ||
      featureRef.status !== 0 ||
      featureRef.stdout.trim() !== reviewedFeature
    ) {
      return { label: "unknown (reviewed_feature is stale)", files };
    }
  }
  return {
    label: `${phase} (plan ${String(lifecycle.plan_approval)}, app review ${String(lifecycle.app_review)})`,
    files,
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
  isFeature: boolean;
  status: StatusRead;
  checkpointPath: string | null;
  checkpointFiles: string[];
  lifecycle: string;
}

export function worktreeList(): WorktreeResult {
  const repo = primaryRepoRoot();
  if (repo === null) return { code: 2, out: "", err: "worktree list: not inside a git repository.\n" };
  const listed = openWorktrees(repo);
  if ("detail" in listed) {
    return { code: 2, out: "", err: `worktree list: the worktree list is unreadable (${listed.detail}).\n` };
  }
  const currentMainRead = git(repo, ["rev-parse", "--verify", "refs/heads/main^{commit}"]);
  const currentMain = currentMainRead.status === 0 ? currentMainRead.stdout.trim() : null;
  let statusUnreadable = false;
  const entries: ListedWorktree[] = listed.worktrees
    .filter((entry) => canonicalize(entry.path) !== repo)
    .map((entry) => {
      const pathExists = existsSync(entry.path);
      const status = pathExists ? worktreeStatus(entry.path) : { paths: [], detail: "worktree path is missing" };
      statusUnreadable ||= pathExists && status.detail !== undefined;
      const isFeature =
        entry.branch?.startsWith("feat/") === true &&
        SLUG_PATTERN.test(entry.slug) &&
        !/\p{C}/u.test(entry.slug);
      const checkpointPath = isFeature
        ? join(entry.path, ".ai-engineering", "workflow", "checkpoints", `${entry.slug}.json`)
        : null;
      const state = checkpointPath === null
        ? { label: "unknown (no feature branch)", files: [] }
        : lifecycleStatus(checkpointPath, entry.path, entry.slug, currentMain, repo, entry.branch ?? "");
      return {
        entry,
        isFeature,
        status,
        checkpointPath,
        checkpointFiles: state.files,
        lifecycle: state.label,
      };
    });

  const lines = entries.map(({ entry, isFeature, status, lifecycle }) => {
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
    return `${displayPath(entry.slug)}\t${displayPath(entry.path)}\t${classification}\t${cleanliness}\t${lifecycle}`;
  });

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
        `likely overlap: ${displayPath(first.entry.slug)} and ${displayPath(second.entry.slug)} ` +
        `(${[...evidence].map(displayPath).join(", ")}); ` +
        `checkpoints: ${displayPath(first.checkpointPath ?? "")}, ${displayPath(second.checkpointPath ?? "")}`,
      );
    }
  }

  lines.push(...overlaps);
  const out = lines.join("\n");
  return {
    code: statusUnreadable ? 2 : 0,
    out: out.length > 0 ? `${out}\n` : "",
    err: "",
  };
}

/** The managed worktree a slug names, or null: the worktree must live under the
 *  configured worktrees root AND sit on the branch this verb itself would have
 *  created (`feat/<slug>`). Matching the slug alone would let
 *  `worktree rm alpha --force` remove an unrelated worktree whose branch happens
 *  to end in `alpha`, wherever it lives. */
function findManagedWorktree(
  repo: string,
  root: string,
  slug: string,
  worktrees: { path: string; branch: string | undefined }[],
): { path: string; branch: string } | null {
  const managedBranch = `feat/${slug}`;
  const managedRoot = `${canonicalize(root)}/`;
  const primary = canonicalize(repo);
  const entry = worktrees.find((candidate) => {
    const path = canonicalize(candidate.path);
    if (path === primary) return false;
    return path.startsWith(managedRoot) && candidate.branch === managedBranch;
  });
  if (entry === undefined || entry.branch === undefined) return null;
  return { path: entry.path, branch: entry.branch };
}

function rebaseCheckpointProblem(path: string, slug: string): string | null {
  const checkpointPath = join(path, ".ai-engineering", "workflow", "checkpoints", `${slug}.json`);
  let checkpoint: unknown;
  try {
    const stat = lstatSync(checkpointPath);
    const checkpointRelative = relative(canonicalize(path), realpathSync(checkpointPath));
    if (
      !stat.isFile() ||
      stat.isSymbolicLink() ||
      checkpointRelative === "" ||
      checkpointRelative === ".." ||
      checkpointRelative.startsWith(`..${sep}`) ||
      isAbsolute(checkpointRelative)
    ) {
      return "checkpoint is not a worktree-local file";
    }
    checkpoint = JSON.parse(readFileSync(checkpointPath, "utf8"));
  } catch {
    return "checkpoint is missing, unreadable or malformed";
  }

  if (
    !isRecord(checkpoint) ||
    !Object.hasOwn(checkpoint, "lifecycle") ||
    checkpointFiles(checkpoint, slug) === null
  ) {
    return "checkpoint is legacy or does not match this worktree";
  }
  const lifecycle = lifecycleFields(checkpoint);
  if (
    lifecycle === null ||
    lifecycle.phase !== "implementation" ||
    lifecycle.plan_approval !== "approved" ||
    !rebaseGatesComplete(checkpoint)
  ) {
    return "checkpoint is not approved implementation state with all planned gates passed";
  }
  return null;
}

function gitOperationState(path: string): { name: string } | { detail: string } | null {
  for (const name of ["rebase-merge", "rebase-apply", "MERGE_HEAD"]) {
    const location = git(path, ["rev-parse", "--git-path", name]);
    if (location.status !== 0 || location.stderr.trim() !== "") {
      return { detail: `cannot read git ${name} state: ${location.stderr.trim() || `git exited ${location.status}`}` };
    }
    const gitPath = location.stdout.endsWith("\n") ? location.stdout.slice(0, -1) : location.stdout;
    if (gitPath === "") return { detail: `cannot read git ${name} state path` };
    if (existsSync(resolve(path, gitPath))) return { name };
  }
  return null;
}

function fullCommitRef(repo: string): string | null {
  const current = git(repo, ["rev-parse", "--verify", "refs/heads/main^{commit}"]);
  if (current.status !== 0 || current.stderr.trim() !== "") return null;
  const commit = current.stdout.trim();
  return /^(?:[0-9a-f]{40}|[0-9a-f]{64})$/.test(commit) ? commit : null;
}

function fullHead(repo: string): string | null {
  const current = git(repo, ["rev-parse", "--verify", "HEAD^{commit}"]);
  if (current.status !== 0 || current.stderr.trim() !== "") return null;
  const commit = current.stdout.trim();
  return /^(?:[0-9a-f]{40}|[0-9a-f]{64})$/.test(commit) ? commit : null;
}

interface MergeReadyState {
  path: string;
  branch: string;
  reviewedMain: string;
  reviewedFeature: string;
}

function mergeReadyFeature(repo: string, slug: string): { state: MergeReadyState } | { detail: string } {
  const root = worktreeRoot(repo);
  const listed = openWorktrees(repo);
  if ("detail" in listed) return { detail: `the worktree list is unreadable (${listed.detail})` };

  const branch = `feat/${slug}`;
  const matching = listed.worktrees.filter((entry) => entry.branch === branch);
  const entry = findManagedWorktree(repo, root, slug, listed.worktrees);
  if (matching.length !== 1 || entry === null || canonicalize(entry.path) !== canonicalize(join(root, slug))) {
    return { detail: `no exact registered managed worktree for ${branch} under ${canonicalize(root)}` };
  }
  if (!existsSync(entry.path)) return { detail: `${entry.path} is missing` };

  const checkedOutBranch = git(entry.path, ["symbolic-ref", "--quiet", "HEAD"]);
  if (
    checkedOutBranch.status !== 0 ||
    checkedOutBranch.stderr.trim() !== "" ||
    checkedOutBranch.stdout.trim() !== `refs/heads/${branch}`
  ) {
    return { detail: `${entry.path} is not checked out on ${branch}` };
  }
  const status = worktreeStatus(entry.path);
  if (status.detail !== undefined) return { detail: `${branch} status is unreadable (${status.detail})` };
  if (status.paths.length > 0) return { detail: `${branch} is dirty (${status.paths.map(displayPath).join(", ")})` };
  const operation = gitOperationState(entry.path);
  if (operation !== null) {
    return { detail: "detail" in operation ? operation.detail : `${operation.name} is in progress` };
  }

  const featureTip = git(repo, ["rev-parse", "--verify", `refs/heads/${branch}^{commit}`]);
  const featureHead = fullHead(entry.path);
  if (
    featureTip.status !== 0 ||
    featureTip.stderr.trim() !== "" ||
    featureHead === null ||
    featureTip.stdout.trim() !== featureHead
  ) {
    return { detail: `${branch} HEAD does not match its local branch ref` };
  }

  const checkpointPath = join(entry.path, ".ai-engineering", "workflow", "checkpoints", `${slug}.json`);
  let checkpoint: unknown;
  try {
    const stat = lstatSync(checkpointPath);
    const checkpointRelative = relative(canonicalize(entry.path), realpathSync(checkpointPath));
    if (
      !stat.isFile() ||
      stat.isSymbolicLink() ||
      checkpointRelative === "" ||
      checkpointRelative === ".." ||
      checkpointRelative.startsWith(`..${sep}`) ||
      isAbsolute(checkpointRelative)
    ) {
      return { detail: "checkpoint is not a worktree-local file" };
    }
    checkpoint = JSON.parse(readFileSync(checkpointPath, "utf8"));
  } catch {
    return { detail: "checkpoint is missing, unreadable or malformed" };
  }
  if (checkpointFiles(checkpoint, slug) === null) return { detail: "checkpoint does not match this worktree" };
  const lifecycle = lifecycleFields(checkpoint);
  if (
    lifecycle === null ||
    lifecycle.phase !== "ready-to-merge" ||
    lifecycle.plan_approval !== "approved" ||
    lifecycle.app_review !== "approved" ||
    !gatesComplete(checkpoint)
  ) {
    return { detail: "checkpoint is not ready-to-merge with approved plan, app review and completed gates" };
  }
  if (typeof lifecycle.reviewed_main !== "string" || typeof lifecycle.reviewed_feature !== "string") {
    return { detail: "checkpoint is missing full reviewed_main or reviewed_feature commit ids" };
  }
  if (lifecycle.reviewed_feature !== featureHead) {
    return { detail: `reviewed_feature ${lifecycle.reviewed_feature} is stale; ${branch} is ${featureHead}` };
  }
  return {
    state: {
      path: entry.path,
      branch,
      reviewedMain: lifecycle.reviewed_main,
      reviewedFeature: lifecycle.reviewed_feature,
    },
  };
}

function primaryCheckout(repo: string): { head: string; main: string } | { detail: string } {
  const branch = git(repo, ["symbolic-ref", "--quiet", "HEAD"]);
  if (branch.status !== 0 || branch.stderr.trim() !== "" || branch.stdout.trim() !== "refs/heads/main") {
    return { detail: "the primary checkout is not on local main" };
  }
  const status = primaryStatus(repo);
  if (status.detail !== undefined) return { detail: `primary status is unreadable (${status.detail})` };
  if (status.paths.length > 0) return { detail: `primary checkout is dirty (${status.paths.map(displayPath).join(", ")})` };
  const operation = gitOperationState(repo);
  if (operation !== null) {
    return { detail: "detail" in operation ? operation.detail : `${operation.name} is in progress` };
  }
  const head = fullHead(repo);
  const main = fullCommitRef(repo);
  if (head === null || main === null) return { detail: "primary HEAD or refs/heads/main is unreadable" };
  return { head, main };
}

function mergeParents(repo: string, commit: string): string[] | null {
  const result = git(repo, ["rev-list", "--parents", "-n", "1", commit]);
  if (result.status !== 0 || result.stderr.trim() !== "") return null;
  return result.stdout.trim().split(" ");
}

function hasReviewedParents(repo: string, commit: string, reviewedMain: string, reviewedFeature: string): boolean {
  const parents = mergeParents(repo, commit);
  return parents !== null && parents.length === 3 &&
    parents[0] === commit &&
    parents[1] === reviewedMain &&
    parents[2] === reviewedFeature;
}

function findPublishedMerge(
  repo: string,
  reviewedMain: string,
  reviewedFeature: string,
): { commit: string } | { detail: string } | null {
  const history = git(repo, ["rev-list", "--first-parent", "--merges", "--format=%H", "refs/heads/main"]);
  if (history.status !== 0 || history.stderr.trim() !== "") {
    return { detail: `local main history is unreadable (${history.stderr.trim() || `git exited ${history.status}`})` };
  }
  for (const candidate of history.stdout.split("\n")) {
    const commit = candidate.trim();
    if (!/^(?:[0-9a-f]{40}|[0-9a-f]{64})$/.test(commit)) continue;
    if (hasReviewedParents(repo, commit, reviewedMain, reviewedFeature)) return { commit };
  }
  return null;
}

function verifyPublishedMerge(
  repo: string,
  commit: string,
  reviewedMain: string,
  reviewedFeature: string,
): string | null {
  if (!hasReviewedParents(repo, commit, reviewedMain, reviewedFeature)) {
    return `published merge ${commit} does not have the exact reviewed parents`;
  }
  const published = git(repo, ["merge-base", "--is-ancestor", commit, "refs/heads/main"]);
  if (published.status !== 0 || published.stderr.trim() !== "") {
    return `merge ${commit} is not in local refs/heads/main history`;
  }
  const feature = git(repo, ["merge-base", "--is-ancestor", reviewedFeature, "refs/heads/main"]);
  if (feature.status !== 0 || feature.stderr.trim() !== "") {
    return `reviewed feature ${reviewedFeature} is not an ancestor of local main`;
  }
  return null;
}

function refreshPrimary(repo: string, reviewedMain: string): string | null {
  const branch = git(repo, ["symbolic-ref", "--quiet", "HEAD"]);
  if (branch.status !== 0 || branch.stderr.trim() !== "" || branch.stdout.trim() !== "refs/heads/main") {
    return "the primary checkout is not on local main";
  }
  const operation = gitOperationState(repo);
  if (operation !== null) return "detail" in operation ? operation.detail : `${operation.name} is in progress`;
  const main = fullCommitRef(repo);
  if (main === null) return "local refs/heads/main is unreadable";
  const ancestry = git(repo, ["merge-base", "--is-ancestor", reviewedMain, "refs/heads/main"]);
  if (ancestry.status !== 0 || ancestry.stderr.trim() !== "") {
    return `reviewed_main ${reviewedMain} is no longer an ancestor of refs/heads/main ${main}`;
  }
  const history = git(repo, ["rev-list", "--first-parent", "refs/heads/main"]);
  if (history.status !== 0 || history.stderr.trim() !== "") return "local main history is unreadable";
  const untracked = untrackedPaths(repo);
  if ("detail" in untracked) return untracked.detail;
  if (untracked.paths.some((path) => !isUnderHooksRoot(repo, path, hooksRoot(repo)))) {
    return "primary checkout has untracked files; refusing to refresh";
  }
  const matchesMainSnapshot = history.stdout.split("\n").some((candidate) => {
    const index = git(repo, ["diff", "--cached", "--quiet", candidate, "--"]);
    const working = git(repo, ["diff", "--quiet"]);
    return index.status === 0 && index.stderr.trim() === "" && working.status === 0 && working.stderr.trim() === "";
  });
  if (!matchesMainSnapshot) return "primary checkout has local changes; refusing to refresh";
  const reset = git(repo, ["reset", "--merge", "refs/heads/main"]);
  if (reset.status !== 0) return `git reset --merge refs/heads/main failed: ${reset.stderr.trim()}`;
  const refreshedBranch = git(repo, ["symbolic-ref", "--quiet", "HEAD"]);
  const refreshed = fullHead(repo);
  const refreshedMain = fullCommitRef(repo);
  const status = primaryStatus(repo);
  if (
    refreshedBranch.status !== 0 ||
    refreshedBranch.stdout.trim() !== "refs/heads/main" ||
    refreshed === null ||
    refreshedMain === null ||
    refreshed !== refreshedMain ||
    status.detail !== undefined ||
    status.paths.length > 0
  ) {
    return "primary refresh did not leave a clean checkout at local main";
  }
  return null;
}

function cleanupMergeWorktree(
  repo: string,
  path: string,
  reviewedMain: string,
  reviewedFeature: string,
  allowedHead?: string,
): string | null {
  const listed = openWorktrees(repo);
  if ("detail" in listed) return `cannot verify temporary worktree registration (${listed.detail})`;
  const matches = listed.worktrees.filter((entry) => canonicalize(entry.path) === canonicalize(path));
  if (matches.length === 0) return existsSync(path) ? `${path} is not a registered temporary worktree` : null;
  if (matches.length !== 1 || matches[0]?.branch !== undefined) {
    return `${path} is not the expected detached temporary worktree`;
  }

  const operation = gitOperationState(path);
  if (operation !== null && "name" in operation) {
    const mergeHead = git(path, ["rev-parse", "--verify", "MERGE_HEAD"]);
    if (
      operation.name !== "MERGE_HEAD" ||
      mergeHead.status !== 0 ||
      mergeHead.stderr.trim() !== "" ||
      mergeHead.stdout.trim() !== reviewedFeature
    ) {
      return `${path} has an operation that is not this transaction's merge`;
    }
    const aborted = git(path, ["merge", "--abort"]);
    if (aborted.status !== 0) return `could not abort this temporary merge: ${aborted.stderr.trim()}`;
    if (gitOperationState(path) !== null || fullHead(path) !== reviewedMain) {
      return `${path} was not restored to reviewed_main after abort`;
    }
  } else if (operation !== null) {
    return `cannot verify temporary merge state (${operation.detail})`;
  }

  const head = fullHead(path);
  if (head === null || (head !== reviewedMain && head !== allowedHead)) {
    return `${path} HEAD is not a known commit from this merge transaction`;
  }
  const status = worktreeStatus(path);
  if (status.detail !== undefined || status.paths.length > 0) {
    return `${path} is not clean${status.detail ? ` (${status.detail})` : ` (${status.paths.map(displayPath).join(", ")})`}`;
  }
  const removed = git(repo, ["worktree", "remove", path]);
  if (removed.status !== 0) return `could not remove clean temporary worktree: ${removed.stderr.trim()}`;
  if (existsSync(path)) return `temporary worktree path ${path} remains after removal`;
  const after = openWorktrees(repo);
  if ("detail" in after) return `cannot verify temporary worktree removal (${after.detail})`;
  if (after.worktrees.some((entry) => canonicalize(entry.path) === canonicalize(path))) {
    return `temporary worktree ${path} remains registered after removal`;
  }
  return null;
}

function removeMergedFeature(repo: string, slug: string, state: MergeReadyState, mergeCommit: string): WorktreeResult {
  const current = mergeReadyFeature(repo, slug);
  if ("detail" in current) {
    return {
      code: 1,
      out: "",
      err: `worktree merge: merge ${mergeCommit} is published, but ${current.detail}; preserve the feature worktree and retry after resolving it.\n`,
    };
  }
  if (
    current.state.path !== state.path ||
    current.state.reviewedMain !== state.reviewedMain ||
    current.state.reviewedFeature !== state.reviewedFeature
  ) {
    return {
      code: 1,
      out: "",
      err: `worktree merge: feature state changed after publishing ${mergeCommit}; preserve it and retry after review.\n`,
    };
  }
  const removed = worktreeRm(slug);
  if (removed.code !== 0) {
    return {
      code: 1,
      out: "",
      err: `worktree merge: merge ${mergeCommit} is published, but safe feature removal failed; preserve the feature worktree and retry: ${removed.err.trim()}\n`,
    };
  }
  const listed = openWorktrees(repo);
  const branchRef = git(repo, ["show-ref", "--verify", "--quiet", `refs/heads/${state.branch}`]);
  if (
    "detail" in listed ||
    listed.worktrees.some((entry) => entry.branch === state.branch) ||
    existsSync(state.path) ||
    branchRef.status === 0
  ) {
    return {
      code: 1,
      out: "",
      err: `worktree merge: safe removal returned, but removal of ${state.branch} could not be verified; do not claim completion.\n`,
    };
  }
  return {
    code: 0,
    out: `✓ merged ${slug} at ${mergeCommit} and removed its feature worktree\n`,
    err: "",
  };
}

export function worktreeMerge(slug: string): WorktreeResult {
  const repo = primaryRepoRoot();
  if (repo === null) return { code: 2, out: "", err: "worktree merge: not inside a git repository.\n" };
  if (!SLUG_PATTERN.test(slug) || /\p{C}/u.test(slug)) {
    return { code: 2, out: "", err: `worktree merge: invalid slug "${printable(slug)}".\n` };
  }

  const primaryBranch = git(repo, ["symbolic-ref", "--quiet", "HEAD"]);
  if (
    primaryBranch.status !== 0 ||
    primaryBranch.stderr.trim() !== "" ||
    primaryBranch.stdout.trim() !== "refs/heads/main"
  ) {
    return { code: 1, out: "", err: "worktree merge: the primary checkout is not on local main; refusing to merge.\n" };
  }
  const currentMain = fullCommitRef(repo);
  if (currentMain === null) return { code: 1, out: "", err: "worktree merge: refs/heads/main is unreadable.\n" };
  const ready = mergeReadyFeature(repo, slug);
  if ("detail" in ready) return { code: 1, out: "", err: `worktree merge: ${ready.detail}; refusing to merge.\n` };
  const state = ready.state;
  if (state.reviewedMain !== currentMain) {
    const alreadyPublished = findPublishedMerge(repo, state.reviewedMain, state.reviewedFeature);
    if (alreadyPublished !== null && "detail" in alreadyPublished) {
      return { code: 1, out: "", err: `worktree merge: ${alreadyPublished.detail}; preserve the feature worktree.\n` };
    }
    if (alreadyPublished === null) {
      return {
        code: 1,
        out: "",
        err:
          `worktree merge: reviewed_main ${state.reviewedMain} is stale; local main is ${currentMain}. ` +
          "Preserve the feature worktree and rerun synchronization, affected gates and human review.\n",
      };
    }
    const publishedError = verifyPublishedMerge(
      repo,
      alreadyPublished.commit,
      state.reviewedMain,
      state.reviewedFeature,
    );
    if (publishedError !== null) {
      return { code: 1, out: "", err: `worktree merge: ${publishedError}; preserve the feature worktree.\n` };
    }
    const refreshed = refreshPrimary(repo, state.reviewedMain);
    if (refreshed !== null) {
      return {
        code: 1,
        out: "",
        err: `worktree merge: ${refreshed}; merge ${alreadyPublished.commit} is already published, preserve the feature worktree and retry.\n`,
      };
    }
    const verified = verifyPublishedMerge(
      repo,
      alreadyPublished.commit,
      state.reviewedMain,
      state.reviewedFeature,
    );
    if (verified !== null) return { code: 1, out: "", err: `worktree merge: ${verified}; preserve the feature worktree.\n` };
    return removeMergedFeature(repo, slug, state, alreadyPublished.commit);
  }
  const primary = primaryCheckout(repo);
  if ("detail" in primary) return { code: 1, out: "", err: `worktree merge: ${primary.detail}; refusing to merge.\n` };
  if (primary.head !== state.reviewedMain) {
    return {
      code: 1,
      out: "",
      err: `worktree merge: primary HEAD ${primary.head} does not equal reviewed_main ${state.reviewedMain}; refusing to merge.\n`,
    };
  }

  const root = worktreeRoot(repo);
  mkdirSync(root, { recursive: true });
  const temporaryPath = join(canonicalize(root), `.ai-eng-merge-${slug}-${randomUUID()}`);
  const added = git(repo, ["worktree", "add", "--detach", temporaryPath, state.reviewedMain]);
  if (added.status !== 0) {
    const cleanup = cleanupMergeWorktree(repo, temporaryPath, state.reviewedMain, state.reviewedFeature);
    return {
      code: 1,
      out: "",
      err: `worktree merge: could not create detached merge worktree: ${added.stderr.trim()}${cleanup ? `; ${cleanup}` : ""}\n`,
    };
  }

  const merged = git(temporaryPath, ["merge", "--no-commit", "--no-ff", `refs/heads/${state.branch}`]);
  if (merged.status !== 0) {
    const cleanup = cleanupMergeWorktree(repo, temporaryPath, state.reviewedMain, state.reviewedFeature);
    return {
      code: 1,
      out: "",
      err: `worktree merge: git merge --no-commit --no-ff failed: ${merged.stderr.trim()}${cleanup ? `; ${cleanup}` : ""}\n`,
    };
  }
  const mergeHead = git(temporaryPath, ["rev-parse", "--verify", "MERGE_HEAD"]);
  if (
    mergeHead.status !== 0 ||
    mergeHead.stderr.trim() !== "" ||
    mergeHead.stdout.trim() !== state.reviewedFeature
  ) {
    const cleanup = cleanupMergeWorktree(repo, temporaryPath, state.reviewedMain, state.reviewedFeature);
    return {
      code: 1,
      out: "",
      err: `worktree merge: temporary merge does not name reviewed_feature ${state.reviewedFeature}${cleanup ? `; ${cleanup}` : ""}\n`,
    };
  }

  const committed = git(temporaryPath, ["commit", "-m", `chore(${slug}): merge ${state.branch}`]);
  const mergeCommit = fullHead(temporaryPath);
  const hasExactParents =
    mergeCommit !== null && hasReviewedParents(repo, mergeCommit, state.reviewedMain, state.reviewedFeature);
  if (committed.status !== 0 || !hasExactParents || mergeCommit === null) {
    const cleanup = cleanupMergeWorktree(
      repo,
      temporaryPath,
      state.reviewedMain,
      state.reviewedFeature,
      hasExactParents ? mergeCommit : undefined,
    );
    const reason = committed.status !== 0
      ? `git commit failed: ${committed.stderr.trim()}`
      : "temporary merge commit does not have the exact reviewed parents";
    return { code: 1, out: "", err: `worktree merge: ${reason}${cleanup ? `; ${cleanup}` : ""}\n` };
  }
  const temporaryStatus = worktreeStatus(temporaryPath);
  if (temporaryStatus.detail !== undefined || temporaryStatus.paths.length > 0 || gitOperationState(temporaryPath) !== null) {
    const cleanup = cleanupMergeWorktree(
      repo,
      temporaryPath,
      state.reviewedMain,
      state.reviewedFeature,
      mergeCommit,
    );
    return {
      code: 1,
      out: "",
      err:
        `worktree merge: temporary merge worktree is not clean after commit; refusing publication.` +
        `${cleanup ? ` ${cleanup}.` : ""}\n`,
    };
  }

  const published = git(repo, ["update-ref", "refs/heads/main", mergeCommit, state.reviewedMain]);
  if (published.status !== 0) {
    const changedMain = fullCommitRef(repo);
    const refreshed = refreshPrimary(repo, state.reviewedMain);
    const cleanup = cleanupMergeWorktree(
      repo,
      temporaryPath,
      state.reviewedMain,
      state.reviewedFeature,
      mergeCommit,
    );
    return {
      code: 1,
      out: "",
      err:
        `worktree merge: compare-and-swap lost; refs/heads/main changed from ${state.reviewedMain} ` +
        `to ${changedMain ?? "unreadable"}. Preserve the feature worktree and rerun synchronization, affected gates and human review.` +
        `${refreshed ? ` Primary refresh was not verified: ${refreshed}.` : ""}` +
        `${cleanup ? ` Temporary worktree was preserved: ${cleanup}.` : ""}\n`,
    };
  }

  const refreshed = refreshPrimary(repo, state.reviewedMain);
  if (refreshed !== null) {
    const cleanup = cleanupMergeWorktree(
      repo,
      temporaryPath,
      state.reviewedMain,
      state.reviewedFeature,
      mergeCommit,
    );
    return {
      code: 1,
      out: "",
      err:
        `worktree merge: ${refreshed}; merge ${mergeCommit} is published. Preserve the feature worktree and retry.` +
        `${cleanup ? ` Temporary worktree was preserved: ${cleanup}.` : ""}\n`,
    };
  }
  const verification = verifyPublishedMerge(repo, mergeCommit, state.reviewedMain, state.reviewedFeature);
  if (verification !== null) {
    const cleanup = cleanupMergeWorktree(
      repo,
      temporaryPath,
      state.reviewedMain,
      state.reviewedFeature,
      mergeCommit,
    );
    return {
      code: 1,
      out: "",
      err: `worktree merge: ${verification}; preserve the feature worktree.${cleanup ? ` ${cleanup}.` : ""}\n`,
    };
  }
  const cleanup = cleanupMergeWorktree(
    repo,
    temporaryPath,
    state.reviewedMain,
    state.reviewedFeature,
    mergeCommit,
  );
  if (cleanup !== null) {
    return {
      code: 1,
      out: "",
      err: `worktree merge: merge ${mergeCommit} is published and verified, but ${cleanup}; preserve the feature worktree and retry.\n`,
    };
  }
  return removeMergedFeature(repo, slug, state, mergeCommit);
}

export function worktreeRebase(slug: string): WorktreeResult {
  const repo = primaryRepoRoot();
  if (repo === null) return { code: 2, out: "", err: "worktree rebase: not inside a git repository.\n" };
  if (!SLUG_PATTERN.test(slug) || /\p{C}/u.test(slug)) {
    return { code: 2, out: "", err: `worktree rebase: invalid slug "${printable(slug)}".\n` };
  }

  const root = worktreeRoot(repo);
  const listed = openWorktrees(repo);
  if ("detail" in listed) {
    return { code: 2, out: "", err: `worktree rebase: the worktree list is unreadable (${listed.detail}).\n` };
  }
  const entry = findManagedWorktree(repo, root, slug, listed.worktrees);
  if (entry === null || !existsSync(entry.path)) {
    return {
      code: 1,
      out: "",
      err: `worktree rebase: no existing managed worktree for slug "${printable(slug)}" (expected feat/${slug} under ${canonicalize(root)}).\n`,
    };
  }

  const head = git(entry.path, ["symbolic-ref", "--quiet", "HEAD"]);
  if (head.status !== 0 || head.stderr.trim() !== "" || head.stdout.trim() !== `refs/heads/${entry.branch}`) {
    return { code: 1, out: "", err: `worktree rebase: ${entry.path} is not registered on ${entry.branch}.\n` };
  }

  const status = worktreeStatus(entry.path);
  if (status.detail !== undefined) {
    return { code: 1, out: "", err: `worktree rebase: git status is unreadable (${printable(status.detail)}); refusing to rebase.\n` };
  }
  if (status.paths.length > 0) {
    return {
      code: 1,
      out: "",
      err: `worktree rebase: ${entry.branch} is dirty (${status.paths.map(displayPath).join(", ")}); refusing to rebase.\n`,
    };
  }

  const checkpointProblem = rebaseCheckpointProblem(entry.path, slug);
  if (checkpointProblem !== null) {
    return { code: 1, out: "", err: `worktree rebase: ${checkpointProblem}; refusing to rebase.\n` };
  }

  const operation = gitOperationState(entry.path);
  if (operation !== null) {
    const detail = "detail" in operation ? operation.detail : `${operation.name} is in progress`;
    return { code: 1, out: "", err: `worktree rebase: ${detail}; refusing to rebase.\n` };
  }

  const mainBefore = fullCommitRef(repo);
  if (mainBefore === null) {
    return { code: 1, out: "", err: "worktree rebase: local refs/heads/main is unreadable; refusing to rebase.\n" };
  }

  const rebased = git(entry.path, ["rebase", "refs/heads/main"]);
  if (rebased.status !== 0) {
    const detail = rebased.stderr.trim();
    return {
      code: 1,
      out: "",
      err:
        `worktree rebase: git rebase refs/heads/main failed${detail ? `: ${printable(detail)}` : ` (exit ${rebased.status})`}; ` +
        `any conflict remains in progress in ${entry.path} for resolution or abort.\n`,
    };
  }

  const mainAfter = fullCommitRef(repo);
  if (mainAfter === null) {
    return {
      code: 1,
      out: "",
      err: "worktree rebase: local refs/heads/main changed or became unreadable during rebase; verify the feature worktree before continuing.\n",
    };
  }
  if (mainAfter !== mainBefore) {
    return {
      code: 1,
      out: "",
      err:
        `worktree rebase: local refs/heads/main advanced during rebase from ${mainBefore} to ${mainAfter}; ` +
        `the rewritten feature branch is preserved. Rerun sync with \`ai-eng worktree rebase ${slug}\` ` +
        `to include the new local main tip.\n`,
    };
  }
  const ancestry = git(entry.path, ["merge-base", "--is-ancestor", mainAfter, "HEAD"]);
  if (ancestry.status !== 0 || ancestry.stderr.trim() !== "") {
    return {
      code: 1,
      out: "",
      err: `worktree rebase: could not verify that local main ${mainAfter} is an ancestor of ${entry.branch}.\n`,
    };
  }

  return { code: 0, out: `✓ rebased worktree ${slug} onto local main ${mainAfter}\n`, err: "" };
}

export function worktreeRm(slug: string, force = false): WorktreeResult {
  const repo = primaryRepoRoot();
  if (repo === null) return { code: 2, out: "", err: "worktree rm: not inside a git repository.\n" };
  const root = worktreeRoot(repo);
  const listed = openWorktrees(repo);
  if ("detail" in listed) {
    return { code: 2, out: "", err: `worktree rm: the worktree list is unreadable (${listed.detail}).\n` };
  }
  const entry = findManagedWorktree(repo, root, slug, listed.worktrees);
  if (entry === null) {
    return {
      code: 1,
      out: "",
      err: `worktree rm: no managed worktree for slug "${printable(slug)}" (expected feat/${slug} under ${canonicalize(root)}).\n`,
    };
  }

  const branch = entry.branch;

  // Refuse before touching anything: the default delete deletes only a branch that
  // proved it landed in the local `main`, and a refusal must leave the worktree and
  // the branch exactly as they were. `merge-base --is-ancestor` pins both refs, so
  // the answer never depends on the mutable HEAD. Only an explicit `--force` skips
  // the proof, for the deliberately abandoned branch.
  if (!force) {
    const merged = git(repo, ["merge-base", "--is-ancestor", branch, "refs/heads/main"]);
    if (merged.status !== 0) {
      return {
        code: 1,
        out: "",
        err: `worktree rm: ${branch} is not merged into the local main — refusing to delete it, and the worktree is left in place. Pass --force to remove a deliberately abandoned branch.\n`,
      };
    }
  }

  // This verb is the explicit path — a person typed it, or the close ran it after
  // the merge landed — so unlike the automatic cleanup pass it removes the worktree
  // even when it holds ignored content. Read that content first and print it, so
  // the deletion is visible to whoever asked for it.
  const dropped = existsSync(entry.path) ? ignoredPaths(entry.path) : [];

  if (existsSync(entry.path)) {
    const removed = git(repo, ["worktree", "remove", entry.path]);
    if (removed.status !== 0) {
      return { code: 1, out: "", err: `worktree rm: git worktree remove failed: ${removed.stderr.trim()}\n` };
    }
  } else {
    // The directory is gone: prune the stale registration instead of failing on it.
    git(repo, ["worktree", "prune"]);
  }
  const deleted = git(repo, ["branch", force ? "-D" : "-d", branch]);
  if (deleted.status !== 0) {
    return { code: 1, out: "", err: `worktree rm: git branch ${force ? "-D" : "-d"} failed: ${deleted.stderr.trim()}\n` };
  }

  let droppedNote = "";
  if (dropped === null) {
    droppedNote = " — the ignored content could not be read (git status warned); anything it held was dropped unseen";
  } else if (dropped.length > 0) {
    droppedNote = ` — dropped ignored: ${dropped.join(", ")}`;
  }
  return {
    code: 0,
    out: force
      ? `✓ removed worktree ${slug} — deleted ${branch} with --force: it was not merged into main${droppedNote}\n`
      : `✓ removed worktree ${slug}${droppedNote}\n`,
    err: "",
  };
}
