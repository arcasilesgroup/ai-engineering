// src/shared-worktree.ts — where a worktree lives, what a slug may be, and the git
// argv the `ai-eng worktree` verb runs. It sits in the shared layer because the
// design-slot list is needed by both this verb and `ai-eng spec`, and shared may not
// import spec — so the one definition moves down rather than up (arch.rules.json).
// Every git value is an argv element: no command is ever assembled as a shell string.

import {
  existsSync,
  lstatSync,
  mkdirSync,
  readFileSync as readFile,
  realpathSync,
  renameSync,
  unlinkSync,
  writeFileSync,
} from "node:fs";
import { randomUUID } from "node:crypto";
import { basename, dirname, isAbsolute, join, relative, resolve, sep } from "node:path";
import { spawnSync } from "node:child_process";
import { isDeepStrictEqual } from "node:util";
import { loadConfig, printable } from "./env.ts";
import { resolveContext } from "./git/context.ts";
import {
  brainstormApprovalProblem,
  parseBrainstormApproval,
  parseCheckpoint,
  readCheckpoint,
  serializeCheckpoint,
  type Checkpoint,
} from "./workflow/checkpoint.ts";

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

type Declarations = Record<string, string[]>;

const DECLARATIONS = ".ai-eng-worktrees.json";

function emptyDeclarations(): Declarations {
  return Object.create(null) as Declarations;
}

function declarationPath(path: string): string | null {
  if (/\p{C}/u.test(path) || path.includes("\\") || /^[a-z]:/iu.test(path)) return null;
  const normalized = normalizedEvidencePath(path);
  if (normalized === null || normalized === "." || normalized.split("/").includes(".")) return null;
  return normalized;
}

function readDeclarations(root: string): { declarations: Declarations; present: boolean } | { detail: string } {
  const path = join(root, DECLARATIONS);
  let stat;
  try {
    stat = lstatSync(path);
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") {
      return { declarations: emptyDeclarations(), present: false };
    }
    return { detail: `${path} is unreadable (${error instanceof Error ? error.message : String(error)})` };
  }
  if (!stat.isFile() || stat.isSymbolicLink()) {
    return { detail: `${path} is not a worktree-root-local file` };
  }
  let contents: string;
  try {
    const relativePath = relative(canonicalize(root), realpathSync(path));
    if (
      relativePath === "" ||
      relativePath === ".." ||
      relativePath.startsWith(`..${sep}`) ||
      isAbsolute(relativePath)
    ) {
      return { detail: `${path} is not a worktree-root-local file` };
    }
    contents = readFile(path, "utf8");
  } catch (error) {
    return { detail: `${path} is unreadable (${error instanceof Error ? error.message : String(error)})` };
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(contents);
  } catch (error) {
    return { detail: `${path} is not valid JSON (${error instanceof Error ? error.message : String(error)})` };
  }
  if (!isRecord(parsed)) {
    return { detail: `${path} must map each slug to its declared files` };
  }

  const declarations = emptyDeclarations();
  for (const [slug, values] of Object.entries(parsed)) {
    if (!SLUG_PATTERN.test(slug) || /\p{C}/u.test(slug) || !Array.isArray(values)) {
      return { detail: `${path} contains an invalid slug or file list` };
    }
    const files = values.map((value) =>
      typeof value === "string" ? declarationPath(value) : null
    );
    if (files.some((file) => file === null)) {
      return { detail: `${path} declares an invalid relative file path for "${slug}"` };
    }
    declarations[slug] = [...new Set(files as string[])];
  }
  return { declarations, present: true };
}

function pruneDeclarations(root: string, declarations: Declarations): Declarations {
  const live = emptyDeclarations();
  for (const [slug, files] of Object.entries(declarations)) {
    if (existsSync(join(root, slug))) live[slug] = files;
  }
  return live;
}

function writeDeclarations(root: string, declarations: Declarations): string | null {
  const path = join(root, DECLARATIONS);
  try {
    mkdirSync(root, { recursive: true });
    let mode = 0o600;
    try {
      const stat = lstatSync(path);
      if (!stat.isFile() || stat.isSymbolicLink()) return `${path} is not a worktree-root-local file`;
      mode = stat.mode & 0o777;
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== "ENOENT") {
        return `${path} is unreadable (${error instanceof Error ? error.message : String(error)})`;
      }
    }
    return replaceFileAtomically(path, `${JSON.stringify(declarations, null, 2)}\n`, mode);
  } catch (error) {
    return error instanceof Error ? error.message : String(error);
  }
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

/** Every worktree git knows, or the reason it could not be read — a list that cannot
 *  be read is never an empty list, because that would let a guard pass unexamined. */
function openWorktrees(repo: string): { worktrees: OpenWorktree[] } | { detail: string } {
  const listed = git(repo, ["worktree", "list", "--porcelain"]);
  if (listed.status !== 0 || listed.stderr.trim() !== "") {
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
      prunable: lines.some((line) => line.startsWith("prunable")),
    });
  }
  return { worktrees };
}

export interface RepositoryWorktree {
  path: string;
  registeredPath: string;
  branch: string | null;
  slug: string;
  detached: boolean;
  prunable: boolean;
}

export interface RepositoryWorktreeInventory {
  repositoryRoot: string;
  worktreesRoot: string;
  worktrees: RepositoryWorktree[];
}

function inventoryWorktreesRoot(repo: string): { path: string } | { detail: string } {
  const metadataPath = join(repo, ".ai-engineering");
  try {
    const metadataStat = lstatSync(metadataPath);
    if (!metadataStat.isDirectory() || metadataStat.isSymbolicLink()) {
      return { detail: ".ai-engineering is not a repository-local directory" };
    }
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== "ENOENT") {
      return { detail: `cannot read .ai-engineering: ${error instanceof Error ? error.message : String(error)}` };
    }
    return { path: canonicalize(`${repo}.worktrees`) };
  }

  const configPath = join(metadataPath, "config.toml");
  try {
    const configStat = lstatSync(configPath);
    const canonicalConfig = realpathSync(configPath);
    const configRelative = relative(repo, canonicalConfig);
    if (
      !configStat.isFile() ||
      configStat.isSymbolicLink() ||
      configRelative === ".." ||
      configRelative.startsWith(`..${sep}`) ||
      isAbsolute(configRelative)
    ) {
      return { detail: "config.toml is not a repository-local file" };
    }
    const parsed: unknown = Bun.TOML.parse(readFile(configPath, "utf8"));
    if (!isRecord(parsed)) return { detail: "config.toml is not a TOML table" };
    if (
      parsed.git !== undefined &&
      (!isRecord(parsed.git) ||
        (parsed.git.worktrees_dir !== undefined && typeof parsed.git.worktrees_dir !== "string"))
    ) {
      return { detail: "config.toml [git].worktrees_dir is malformed" };
    }
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") {
      return { path: canonicalize(`${repo}.worktrees`) };
    }
    return { detail: `config.toml read failed: ${error instanceof Error ? error.message : String(error)}` };
  }
  return { path: canonicalize(worktreeRoot(repo)) };
}

/** A read-only inventory for callers that already resolved a repository root. */
export function repositoryWorktreeInventory(
  repositoryPath: string,
): RepositoryWorktreeInventory | { detail: string } {
  let repositoryRoot: string;
  try {
    repositoryRoot = realpathSync(repositoryPath);
  } catch (error) {
    return { detail: `repository root is unreadable: ${error instanceof Error ? error.message : String(error)}` };
  }

  const topLevel = git(repositoryRoot, ["rev-parse", "--show-toplevel"]);
  if (topLevel.status !== 0 || topLevel.stderr.trim() !== "") {
    return {
      detail: topLevel.stderr.trim() || `git rev-parse --show-toplevel exited ${topLevel.status}`,
    };
  }
  if (canonicalize(topLevel.stdout.trim()) !== repositoryRoot) {
    return { detail: "path is not the Git repository root" };
  }

  const configuredWorktreesRoot = inventoryWorktreesRoot(repositoryRoot);
  if ("detail" in configuredWorktreesRoot) return configuredWorktreesRoot;
  const listed = openWorktrees(repositoryRoot);
  if ("detail" in listed) return { detail: listed.detail };
  return {
    repositoryRoot,
    worktreesRoot: configuredWorktreesRoot.path,
    worktrees: listed.worktrees.map((entry) => {
      const registeredPath = isAbsolute(entry.path) ? resolve(entry.path) : resolve(repositoryRoot, entry.path);
      return {
        path: canonicalize(registeredPath),
        registeredPath,
        branch: entry.branch ?? null,
        slug: entry.slug,
        detached: entry.detached,
        prunable: entry.prunable,
      };
    }),
  };
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

function ignoredRemovalNote(dropped: string[] | null, removalState: "removed" | "unknown"): string {
  if (dropped === null) {
    return removalState === "removed"
      ? " — the ignored content could not be read (git status warned); anything it held was dropped unseen"
      : " — the ignored content could not be read (git status warned); whether it was removed is unknown";
  }
  if (dropped.length === 0) return "";
  const paths = dropped.map(displayPath);
  return removalState === "removed"
    ? ` — dropped ignored: ${paths.join(", ")}`
    : ` — ignored content found before removal: ${paths.join(", ")}; its remaining state is unknown`;
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

export function worktreeNew(slug: string, requestedFileHints: string[] = []): WorktreeResult {
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
  const normalizedHints = requestedFileHints.map(declarationPath);
  if (normalizedHints.some((path) => path === null)) {
    const invalidHint = requestedFileHints[normalizedHints.findIndex((path) => path === null)] ?? "";
    return {
      code: 2,
      out: "",
      err: `worktree new: invalid relative file hint "${printable(invalidHint)}".\n`,
    };
  }
  const fileHints = [...new Set(normalizedHints.filter((path): path is string => path !== null))];
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
  const read = readDeclarations(root);
  if ("detail" in read && fileHints.length > 0) {
    return {
      code: 2,
      out: "",
      err: `worktree new: the manifest is unusable (${read.detail}) — refusing to save requested file hints.\n`,
    };
  }
  const declarations = "detail" in read
    ? emptyDeclarations()
    : pruneDeclarations(root, read.declarations);
  const overlaps: string[] = [];
  if (fileHints.length > 0) {
    const listed = openWorktrees(repo);
    if ("detail" in listed) {
      return {
        code: 2,
        out: "",
        err: `worktree new: the worktree list is unreadable (${listed.detail}) — refusing to cut a worktree blindly.\n`,
      };
    }
    for (const entry of listed.worktrees) {
      if (canonicalize(entry.path) === repo || entry.prunable || !existsSync(entry.path)) continue;
      const declaredFiles = Object.hasOwn(declarations, entry.slug) ? declarations[entry.slug] ?? [] : [];
      for (const file of fileHints) {
        if (declaredFiles.includes(file)) overlaps.push(`${printable(entry.slug)} already declared ${file}`);
      }
    }
  }
  const target = join(root, slug);
  const branch = `feat/${slug}`;
  mkdirSync(root, { recursive: true });
  const added = git(repo, ["worktree", "add", target, "-b", branch, "refs/heads/main"]);
  if (added.status !== 0) {
    return { code: 1, out: "", err: `worktree new: git worktree add failed: ${added.stderr.trim()}\n` };
  }
  git(repo, ["config", `branch.${branch}.remote`, "."]);
  git(repo, ["config", `branch.${branch}.merge`, "refs/heads/main"]);
  if (!("detail" in read)) {
    if (fileHints.length > 0) declarations[slug] = fileHints;
    const removedStaleDeclarations = read.present &&
      Object.keys(declarations).length !== Object.keys(read.declarations).length;
    if (fileHints.length > 0 || removedStaleDeclarations) {
      const writeError = writeDeclarations(root, declarations);
      if (writeError !== null) {
        return {
          code: 1,
          out: `✓ worktree ${slug} → ${target}\n`,
          err:
            `worktree new: the worktree exists, but its advisory file hints were not saved ` +
            `(${printable(writeError)}); no lifecycle approval was recorded.\n`,
        };
      }
    }
  }

  return {
    code: 0,
    out: `✓ worktree ${slug} → ${target}\n`,
    err: overlaps.length > 0 ? `worktree new: overlap — ${overlaps.join("; ")}\n` : "",
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

function untrackedPaths(repo: string): { paths: string[] } | { detail: string } {
  const untracked = git(repo, ["ls-files", "--others", "--exclude-standard", "-z"]);
  if (untracked.status !== 0 || untracked.stderr.trim() !== "") {
    return { detail: untracked.stderr.trim() || `git ls-files exited ${untracked.status}` };
  }
  return { paths: untracked.stdout.split("\0").filter(Boolean) };
}

function primaryStatus(repo: string): StatusRead {
  const status = worktreeStatus(repo);
  if (status.detail !== undefined) return status;
  const untracked = untrackedPaths(repo);
  if ("detail" in untracked) return { paths: [], detail: untracked.detail };
  const untrackedSet = new Set(untracked.paths);
  return { paths: status.paths.filter((path) => !untrackedSet.has(path)) };
}

function untrackedPathCollision(repo: string, current: string, incoming: string): string | null {
  const untracked = untrackedPaths(repo);
  if ("detail" in untracked) return `primary untracked files are unreadable (${untracked.detail})`;
  if (untracked.paths.length === 0) return null;

  const changed = git(repo, ["diff", "--no-renames", "--name-only", "-z", current, incoming]);
  if (changed.status !== 0 || changed.stderr.trim() !== "") {
    return `incoming merge paths are unreadable (${changed.stderr.trim() || `git diff exited ${changed.status}`})`;
  }
  const ignoreCase = git(repo, ["config", "--bool", "--get", "core.ignorecase"]);
  if ((ignoreCase.status !== 0 && ignoreCase.status !== 1) || ignoreCase.stderr.trim() !== "") {
    return `filesystem case handling is unreadable (${ignoreCase.stderr.trim() || `git config exited ${ignoreCase.status}`})`;
  }
  const isCaseInsensitive = ignoreCase.stdout.trim() === "true";
  const normalize = (path: string): string => isCaseInsensitive ? path.toLowerCase() : path;
  const changedPaths = changed.stdout.split("\0").filter(Boolean).map(normalize);
  const collisions = untracked.paths.filter((untrackedPath) => {
    const candidate = normalize(untrackedPath);
    return changedPaths.some((changedPath) =>
      candidate === changedPath ||
      candidate.startsWith(`${changedPath}/`) ||
      changedPath.startsWith(`${candidate}/`)
    );
  });
  if (collisions.length === 0) return null;
  return `primary untracked files collide with incoming merge paths (${collisions.map(displayPath).join(", ")})`;
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

function gatesComplete(plan: Checkpoint): boolean {
  return plan.checkpoints.every((checkpoint) =>
    checkpoint.status === "passed" &&
    ["behavior", "ui", "review"].every((name) => {
      const status = checkpoint.gates[name as keyof Checkpoint["checkpoints"][number]["gates"]].status;
      return status === "passed" || status === "n/a";
    })
  );
}

function rebaseGatesComplete(plan: Checkpoint): boolean {
  return gatesComplete(plan) && plan.checkpoints.every((checkpoint) =>
    checkpoint.gates.behavior.status === "passed" &&
    checkpoint.gates.review.status === "passed"
  );
}

function lifecycleStatus(
  checkpointPath: string,
  worktreePath: string,
  slug: string,
  repo: string,
  branch: string,
): { label: string; files: string[] } {
  if (!existsSync(worktreePath) || !existsSync(checkpointPath)) {
    return { label: "unknown (missing, unreadable or malformed checkpoint)", files: [] };
  }
  let baseRef: string;
  try {
    const detectedBase = resolveContext(worktreePath).base;
    if (detectedBase === null) return { label: "unknown (base ref is not detectable)", files: [] };
    baseRef = `refs/heads/${detectedBase}`;
  } catch {
    return { label: "unknown (base ref is not readable)", files: [] };
  }
  const currentBaseRead = git(repo, ["rev-parse", "--verify", `${baseRef}^{commit}`]);
  const currentBase = currentBaseRead.status === 0 && currentBaseRead.stderr.trim() === ""
    ? currentBaseRead.stdout.trim()
    : null;
  let parsed: Checkpoint;
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
  if (["awaiting-app-review", "ready-to-merge"].includes(phase) && !gatesComplete(parsed)) {
    return { label: "unknown (lifecycle gates are incomplete)", files };
  }
  if (lifecycle.reviewed_base !== null) {
    if (currentBase === null || lifecycle.reviewed_base !== currentBase) {
      return { label: "unknown (reviewed_base is stale)", files };
    }
  }
  if (phase === "ready-to-merge") {
    const reviewedFeature = lifecycle.reviewed_feature;
    const featureRef = git(repo, ["rev-parse", "--verify", `refs/heads/${branch}^{commit}`]);
    if (typeof reviewedFeature !== "string" || featureRef.status !== 0) {
      return { label: "unknown (reviewed_feature or feature tip is unreadable)", files };
    }
    const chainProblem = reviewedFeatureChainProblem(
      repo,
      slug,
      lifecycle.reviewed_base as string,
      reviewedFeature,
      featureRef.stdout.trim(),
    );
    if (chainProblem !== null) {
      return { label: `unknown (${chainProblem})`, files };
    }
  }
  return {
    label: `${phase} (plan ${String(lifecycle.plan_approval)}, app review ${String(lifecycle.app_review)})`,
    files,
  };
}

export interface WorktreeBrainstormProjection {
  slug: string | null;
  label: string;
}

export function worktreeBrainstormProjection(repo: string, requestedSlug?: string): WorktreeBrainstormProjection {
  const path = join(repo, ".ai-engineering", "brainstorm.html");
  let html: string;
  try {
    const stat = lstatSync(path);
    const artifactRelative = relative(canonicalize(repo), realpathSync(path));
    if (
      !stat.isFile() ||
      stat.isSymbolicLink() ||
      artifactRelative === "" ||
      artifactRelative === ".." ||
      artifactRelative.startsWith(`..${sep}`) ||
      isAbsolute(artifactRelative)
    ) {
      return { slug: requestedSlug ?? null, label: "unknown (brainstorm is not a repository-local file)" };
    }
    html = readFile(path, "utf8");
  } catch {
    return { slug: requestedSlug ?? null, label: "unknown (brainstorm is missing or unreadable)" };
  }
  const approval = parseBrainstormApproval(html, requestedSlug ?? "", new Date());
  if (approval === null) {
    const reason = brainstormApprovalProblem(html, requestedSlug ?? "", new Date()) ??
      "brainstorm approval is invalid";
    return {
      slug: requestedSlug ?? null,
      label: `unknown (${reason})`,
    };
  }
  return {
    slug: approval.slug,
    label: `approval-before-start (brainstorm approved ${approval.approvedOn})`,
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
        : lifecycleStatus(checkpointPath, entry.path, entry.slug, repo, entry.branch ?? "");
      return {
        entry,
        isFeature,
        status,
        checkpointPath,
        checkpointFiles: state.files,
        lifecycle: state.label,
      };
    });

  const matchingEntries = requestedSlug === undefined
    ? entries
    : entries.filter(({ entry }) => entry.slug === requestedSlug);
  const lines = matchingEntries.map(({ entry, isFeature, status, lifecycle }) => {
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

  const hasWorktreeForSlug = (slug: string): boolean =>
    listed.worktrees.some((entry) =>
      canonicalize(entry.path) !== repo &&
      (
        entry.branch === `feat/${slug}` ||
        entry.slug === slug ||
        canonicalize(entry.path) === canonicalize(join(root, slug))
      )
    );
  const hasMatchingWorktree = requestedSlug !== undefined && hasWorktreeForSlug(requestedSlug);
  const projection = requestedSlug !== undefined
    ? hasMatchingWorktree
      ? null
      : worktreeBrainstormProjection(repo, requestedSlug)
    : worktreeBrainstormProjection(repo);
  const projectionSlug = projection === null ? null : requestedSlug ?? projection.slug;
  const featureBranchRead = projectionSlug === null
    ? null
    : git(repo, ["show-ref", "--verify", "--quiet", `refs/heads/feat/${projectionSlug}`]);
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
  if (projection !== null && (projection.slug !== null || requestedSlug !== undefined)) {
    const slug = requestedSlug ?? projection.slug ?? "unknown";
    const alreadyListed = hasWorktreeForSlug(slug);
    if (!alreadyListed && !hasFeatureBranch && !featureBranchUnknown) {
      lines.push(
        `${displayPath(slug)}\t-\tpre-worktree\tunknown\t${projection.label}`,
      );
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
        `likely overlap: ${displayPath(first.entry.slug)} and ${displayPath(second.entry.slug)} ` +
        `(${[...evidence].map(displayPath).join(", ")}); ` +
        `checkpoints: ${displayPath(first.checkpointPath ?? "")}, ${displayPath(second.checkpointPath ?? "")}`,
      );
    }
  }

  if (requestedSlug === undefined) lines.push(...overlaps);
  const out = lines.join("\n");
  return {
    code: statusUnreadable ? 2 : 0,
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
  return cleanupMergeWorktree(repo, path, baseCommit, baseCommit, head === baseCommit ? undefined : head);
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
  const matching = listed.worktrees.filter((entry) => entry.branch === `feat/${slug}`);
  const entry = findManagedWorktree(repo, root, slug, listed.worktrees);
  if (
    matching.length !== 1 ||
    entry === null ||
    canonicalize(entry.path) !== canonicalize(join(root, slug)) ||
    !existsSync(entry.path)
  ) {
    return {
      code: 1,
      out: "",
      err: `worktree request-changes: no exact live managed feat/${slug} worktree; preserve the review state.\n`,
    };
  }

  const branch = `refs/heads/feat/${slug}`;
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
        `but the current feat/${slug} tip is ${head ?? "unreadable"}. Return to app review; no files were changed.\n`,
    };
  }

  const checkedOutBranch = git(entry.path, ["symbolic-ref", "--quiet", "HEAD"]);
  if (
    checkedOutBranch.status !== 0 ||
    checkedOutBranch.stderr.trim() !== "" ||
    checkedOutBranch.stdout.trim() !== branch
  ) {
    return { code: 1, out: "", err: `worktree request-changes: ${entry.path} is not checked out on feat/${slug}.\n` };
  }
  const status = worktreeStatus(entry.path);
  if (status.detail !== undefined || status.paths.length > 0) {
    return {
      code: 1,
      out: "",
      err:
        `worktree request-changes: feat/${slug} is not clean` +
        `${status.detail ? ` (${printable(status.detail)})` : ` (${status.paths.map(displayPath).join(", ")})`}; ` +
        "preserve the review state and return to app review.\n",
    };
  }
  const operation = gitOperationState(entry.path);
  if (operation !== null) {
    const detail = "detail" in operation ? operation.detail : `${operation.name} is in progress`;
    return { code: 1, out: "", err: `worktree request-changes: ${printable(detail)}; preserve the review state.\n` };
  }

  const checkpointPath = join(entry.path, ".ai-engineering", "workflow", "checkpoints", `${slug}.json`);
  const checkpointRelative = `.ai-engineering/workflow/checkpoints/${slug}.json`;
  let checkpointContents: string;
  let checkpoint: Checkpoint;
  try {
    const stat = lstatSync(checkpointPath);
    const relativePath = relative(canonicalize(entry.path), realpathSync(checkpointPath));
    if (
      !stat.isFile() ||
      stat.isSymbolicLink() ||
      relativePath === "" ||
      relativePath === ".." ||
      relativePath.startsWith(`..${sep}`) ||
      isAbsolute(relativePath)
    ) {
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

  const transactionPath = join(root, `.request-changes-${slug}-${randomUUID()}`);
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
    const stat = lstatSync(transactionCheckpoint);
    const relativePath = relative(canonicalize(transactionPath), realpathSync(transactionCheckpoint));
    if (
      !stat.isFile() ||
      stat.isSymbolicLink() ||
      relativePath === "" ||
      relativePath === ".." ||
      relativePath.startsWith(`..${sep}`) ||
      isAbsolute(relativePath)
    ) {
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

  const committed = git(transactionPath, ["commit", "-m", `chore(${slug}): record requested changes`]);
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
    const cleanup = cleanupMergeWorktree(repo, transactionPath, expectedCheckpointCommit, expectedCheckpointCommit, transitionCommit);
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
    const cleanup = cleanupMergeWorktree(repo, transactionPath, expectedCheckpointCommit, expectedCheckpointCommit, transitionCommit);
    return {
      code: 1,
      out: "",
      err:
        `worktree request-changes: compare-and-swap lost; feat/${slug} no longer points to ` +
        `${expectedCheckpointCommit}. Return to app review; ${cleanup ? `${cleanup}.` : "the feature worktree is unchanged"}\n`,
    };
  }

  const sourceStatus = worktreeStatus(entry.path);
  let sourceCheckpoint: Checkpoint | null = null;
  try {
    sourceCheckpoint = readCheckpoint(checkpointPath, {
      repoPath: entry.path,
      slug,
      baseRef: "refs/heads/main",
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
    const cleanup = cleanupMergeWorktree(repo, transactionPath, expectedCheckpointCommit, expectedCheckpointCommit, transitionCommit);
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
          baseRef: "refs/heads/main",
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
    const cleanup = cleanupMergeWorktree(repo, transactionPath, expectedCheckpointCommit, expectedCheckpointCommit, transitionCommit);
    return {
      code: 1,
      out: "",
      err:
        `worktree request-changes: could not synchronize the committed checkpoint` +
        `${rollback.status === 0 && restored ? "; the ref and checkpoint were restored" : "; preserve the ref and worktree"}` +
        `${cleanup ? `; ${cleanup}` : ""}.\n`,
    };
  }

  const cleanup = cleanupMergeWorktree(repo, transactionPath, expectedCheckpointCommit, expectedCheckpointCommit, transitionCommit);
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
  let checkpoint: Checkpoint;
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
    checkpoint = readCheckpoint(checkpointPath, {
      repoPath: path,
      slug,
      baseRef: "refs/heads/main",
    });
  } catch {
    return "checkpoint is missing, unreadable, malformed or legacy";
  }

  const lifecycle = checkpoint.lifecycle;
  if (
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

function reviewedPlanPayload(plan: unknown): Record<string, unknown> | null {
  if (!isRecord(plan) || !Array.isArray(plan.checkpoints)) return null;
  const payload: Record<string, unknown> = { ...plan };
  delete payload.lifecycle;
  payload.checkpoints = plan.checkpoints.map((checkpoint) => {
    if (!isRecord(checkpoint)) return checkpoint;
    const checkpointPayload: Record<string, unknown> = { ...checkpoint };
    delete checkpointPayload.status;
    if (isRecord(checkpointPayload.gates)) {
      const gates: Record<string, unknown> = {};
      for (const [name, gate] of Object.entries(checkpointPayload.gates)) {
        if (!isRecord(gate)) {
          gates[name] = gate;
          continue;
        }
        const gatePayload: Record<string, unknown> = { ...gate };
        delete gatePayload.status;
        delete gatePayload.attempts;
        delete gatePayload.findings;
        gates[name] = gatePayload;
      }
      checkpointPayload.gates = gates;
    }
    return checkpointPayload;
  });
  return payload;
}

export function reviewedFeatureChainProblem(
  repo: string,
  slug: string,
  reviewedMain: string,
  reviewedFeature: string,
  featureTip: string,
  phase: "awaiting-app-review" | "ready-to-merge" = "ready-to-merge",
): string | null {
  const ancestry = git(repo, ["merge-base", "--is-ancestor", reviewedFeature, featureTip]);
  if (ancestry.status !== 0 || ancestry.stderr.trim() !== "") {
    return `reviewed_feature ${reviewedFeature} is not an ancestor of feat/${slug} ${featureTip}`;
  }
  const history = git(repo, ["rev-list", "--reverse", `${reviewedFeature}..${featureTip}`]);
  if (history.status !== 0 || history.stderr.trim() !== "") return "feature commits after reviewed_feature are unreadable";
  const commits = history.stdout.split("\n").map((commit) => commit.trim()).filter(Boolean);
  if (
    (phase === "awaiting-app-review" && commits.length !== 1) ||
    (phase === "ready-to-merge" && commits.length < 2)
  ) return "app-review lifecycle checkpoint commits are missing or duplicated";

  const checkpointPath = `.ai-engineering/workflow/checkpoints/${slug}.json`;
  const reviewedCheckpoint = git(repo, ["show", `${reviewedFeature}:${checkpointPath}`]);
  if (reviewedCheckpoint.status !== 0 || reviewedCheckpoint.stderr.trim() !== "") {
    return "reviewed_feature has no readable checkpoint plan";
  }
  let reviewedPlan: Checkpoint;
  try {
    reviewedPlan = parseCheckpoint(reviewedCheckpoint.stdout, {
      repoPath: repo,
      slug,
      baseRef: "refs/heads/main",
    });
  } catch {
    return "reviewed_feature has a malformed checkpoint plan";
  }
  const reviewedPayload = reviewedPlanPayload(reviewedPlan);
  if (reviewedPayload === null) return "reviewed_feature has no verifiable checkpoint plan";

  let previous = reviewedFeature;
  for (const [index, commit] of commits.entries()) {
    const parents = git(repo, ["rev-list", "--parents", "-n", "1", commit]);
    if (
      parents.status !== 0 ||
      parents.stderr.trim() !== "" ||
      parents.stdout.trim().split(" ").join(" ") !== `${commit} ${previous}`
    ) {
      return `feat/${slug} has a non-linear commit after reviewed_feature`;
    }
    const changed = git(repo, ["diff-tree", "--no-commit-id", "--name-only", "-r", "--no-renames", "-z", commit]);
    if (
      changed.status !== 0 ||
      changed.stderr.trim() !== "" ||
      changed.stdout.split("\0").filter(Boolean).join("\0") !== checkpointPath
    ) {
      return `commit ${commit} after reviewed_feature changes paths other than ${checkpointPath}`;
    }
    const checkpoint = git(repo, ["show", `${commit}:${checkpointPath}`]);
    if (checkpoint.status !== 0 || checkpoint.stderr.trim() !== "") {
      return `commit ${commit} has no readable lifecycle checkpoint`;
    }
    let parsed: Checkpoint;
    try {
      parsed = parseCheckpoint(checkpoint.stdout, {
        repoPath: repo,
        slug,
        baseRef: "refs/heads/main",
      });
    } catch {
      return `commit ${commit} has malformed lifecycle checkpoint metadata`;
    }
    const payload = reviewedPlanPayload(parsed);
    if (payload === null || !isDeepStrictEqual(reviewedPayload, payload)) {
      return `commit ${commit} changes the reviewed checkpoint plan`;
    }
    const lifecycle = parsed.lifecycle;
    const isPendingReview = index === 0;
    if (
      !gatesComplete(parsed) ||
      lifecycle.plan_approval !== "approved" ||
      lifecycle.reviewed_base !== reviewedMain ||
      lifecycle.reviewed_feature !== reviewedFeature ||
      lifecycle.phase !== (isPendingReview ? "awaiting-app-review" : "ready-to-merge") ||
      lifecycle.app_review !== (isPendingReview ? "pending" : "approved") ||
      (phase === "awaiting-app-review" && !isPendingReview)
    ) {
      return `commit ${commit} has invalid app-review lifecycle metadata`;
    }
    previous = commit;
  }
  return null;
}

interface MergeReadyState {
  path: string;
  branch: string;
  reviewedMain: string;
  reviewedFeature: string;
  featureTip: string;
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

  const featureRef = git(repo, ["rev-parse", "--verify", `refs/heads/${branch}^{commit}`]);
  const featureHead = fullHead(entry.path);
  if (
    featureRef.status !== 0 ||
    featureRef.stderr.trim() !== "" ||
    featureHead === null ||
    featureRef.stdout.trim() !== featureHead
  ) {
    return { detail: `${branch} HEAD does not match its local branch ref` };
  }

  const checkpointPath = join(entry.path, ".ai-engineering", "workflow", "checkpoints", `${slug}.json`);
  let checkpoint: Checkpoint;
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
    checkpoint = readCheckpoint(checkpointPath, {
      repoPath: entry.path,
      slug,
      baseRef: "refs/heads/main",
    });
  } catch {
    return { detail: "checkpoint is missing, unreadable or malformed" };
  }
  const lifecycle = checkpoint.lifecycle;
  if (
    lifecycle.phase !== "ready-to-merge" ||
    lifecycle.plan_approval !== "approved" ||
    lifecycle.app_review !== "approved" ||
    !gatesComplete(checkpoint)
  ) {
    return { detail: "checkpoint is not ready-to-merge with approved plan, app review and completed gates" };
  }
  if (typeof lifecycle.reviewed_base !== "string" || typeof lifecycle.reviewed_feature !== "string") {
    return { detail: "checkpoint is missing full reviewed_base or reviewed_feature commit ids" };
  }
  const featureTip = featureHead;
  const chainProblem = reviewedFeatureChainProblem(
    repo,
    slug,
    lifecycle.reviewed_base,
    lifecycle.reviewed_feature,
    featureTip,
  );
  if (chainProblem !== null) {
    return { detail: chainProblem };
  }
  return {
    state: {
      path: entry.path,
      branch,
      reviewedMain: lifecycle.reviewed_base,
      reviewedFeature: lifecycle.reviewed_feature,
      featureTip,
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

function hasReviewedParents(repo: string, commit: string, reviewedMain: string, featureTip: string): boolean {
  const parents = mergeParents(repo, commit);
  return parents !== null && parents.length === 3 &&
    parents[0] === commit &&
    parents[1] === reviewedMain &&
    parents[2] === featureTip;
}

function findPublishedMerge(
  repo: string,
  reviewedMain: string,
  featureTip: string,
): { commit: string } | { detail: string } | null {
  const history = git(repo, ["rev-list", "--first-parent", "--merges", "--format=%H", "refs/heads/main"]);
  if (history.status !== 0 || history.stderr.trim() !== "") {
    return { detail: `local main history is unreadable (${history.stderr.trim() || `git exited ${history.status}`})` };
  }
  for (const candidate of history.stdout.split("\n")) {
    const commit = candidate.trim();
    if (!/^(?:[0-9a-f]{40}|[0-9a-f]{64})$/.test(commit)) continue;
    if (hasReviewedParents(repo, commit, reviewedMain, featureTip)) return { commit };
  }
  return null;
}

function verifyPublishedMerge(
  repo: string,
  commit: string,
  reviewedMain: string,
  featureTip: string,
  reviewedFeature: string,
): string | null {
  if (!hasReviewedParents(repo, commit, reviewedMain, featureTip)) {
    return `published merge ${commit} does not have the exact reviewed parents`;
  }
  const published = git(repo, ["merge-base", "--is-ancestor", commit, "refs/heads/main"]);
  if (published.status !== 0 || published.stderr.trim() !== "") {
    return `merge ${commit} is not in local refs/heads/main history`;
  }
  const feature = git(repo, ["merge-base", "--is-ancestor", featureTip, "refs/heads/main"]);
  if (feature.status !== 0 || feature.stderr.trim() !== "") {
    return `feature tip ${featureTip} is not an ancestor of local main`;
  }
  const reviewed = git(repo, ["merge-base", "--is-ancestor", reviewedFeature, featureTip]);
  if (reviewed.status !== 0 || reviewed.stderr.trim() !== "") {
    return `reviewed feature ${reviewedFeature} is not an ancestor of feature tip ${featureTip}`;
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
  const snapshot = history.stdout.split("\n").find((candidate) => {
    const index = git(repo, ["diff", "--cached", "--quiet", candidate, "--"]);
    const working = git(repo, ["diff", "--quiet"]);
    return index.status === 0 && index.stderr.trim() === "" && working.status === 0 && working.stderr.trim() === "";
  });
  if (snapshot === undefined) return "primary checkout has local changes; refusing to refresh";
  const collision = untrackedPathCollision(repo, snapshot, "refs/heads/main");
  if (collision !== null) return collision;
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
  featureTip: string,
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
      mergeHead.stdout.trim() !== featureTip
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
    current.state.reviewedFeature !== state.reviewedFeature ||
    current.state.featureTip !== state.featureTip
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
      out: removed.out,
      err: `worktree merge: merge ${mergeCommit} is published, but safe feature cleanup failed: ${removed.err.trim()}\n`,
    };
  }
  const listed = openWorktrees(repo);
  const branchRef = git(repo, ["show-ref", "--verify", "--quiet", `refs/heads/${state.branch}`]);
  const problems: string[] = [];
  if ("detail" in listed) {
    problems.push(`worktree inventory is unreadable (${listed.detail})`);
  } else if (listed.worktrees.some((entry) => entry.branch === state.branch)) {
    problems.push(`worktree for ${state.branch} remains registered`);
  }
  if (existsSync(state.path)) problems.push(`worktree path ${state.path} remains`);
  if (branchRef.status === 0) {
    problems.push(`branch ${state.branch} remains`);
  } else if (branchRef.status !== 1 || branchRef.stderr.trim() !== "") {
    problems.push(`branch ${state.branch} could not be verified (${branchRef.stderr.trim() || `git show-ref exited ${branchRef.status}`})`);
  }
  if (problems.length > 0) {
    return {
      code: 1,
      out: removed.out,
      err: `worktree merge: merge ${mergeCommit} is published, but post-removal verification failed: ${problems.join("; ")}. The cleanup command reported success; do not claim completion.\n`,
    };
  }
  return {
    code: 0,
    out: `${removed.out}✓ merged ${slug} at ${mergeCommit} and removed its feature worktree\n`,
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
    const alreadyPublished = findPublishedMerge(repo, state.reviewedMain, state.featureTip);
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
      state.featureTip,
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
      state.featureTip,
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
  const collision = untrackedPathCollision(repo, state.reviewedMain, state.featureTip);
  if (collision !== null) {
    return { code: 1, out: "", err: `worktree merge: ${collision}; refusing to merge.\n` };
  }

  const root = worktreeRoot(repo);
  mkdirSync(root, { recursive: true });
  const temporaryPath = join(canonicalize(root), `.ai-eng-merge-${slug}-${randomUUID()}`);
  const added = git(repo, ["worktree", "add", "--detach", temporaryPath, state.reviewedMain]);
  if (added.status !== 0) {
    const cleanup = cleanupMergeWorktree(repo, temporaryPath, state.reviewedMain, state.featureTip);
    return {
      code: 1,
      out: "",
      err: `worktree merge: could not create detached merge worktree: ${added.stderr.trim()}${cleanup ? `; ${cleanup}` : ""}\n`,
    };
  }

  const merged = git(temporaryPath, ["merge", "--no-commit", "--no-ff", `refs/heads/${state.branch}`]);
  if (merged.status !== 0) {
    const cleanup = cleanupMergeWorktree(repo, temporaryPath, state.reviewedMain, state.featureTip);
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
    mergeHead.stdout.trim() !== state.featureTip
  ) {
    const cleanup = cleanupMergeWorktree(repo, temporaryPath, state.reviewedMain, state.featureTip);
    return {
      code: 1,
      out: "",
      err: `worktree merge: temporary merge does not name current feature tip ${state.featureTip}${cleanup ? `; ${cleanup}` : ""}\n`,
    };
  }

  const expectedMergeTree = git(temporaryPath, ["write-tree"]);
  const expectedTreeId = expectedMergeTree.stdout.trim();
  if (
    expectedMergeTree.status !== 0 ||
    expectedMergeTree.stderr.trim() !== "" ||
    !/^(?:[0-9a-f]{40}|[0-9a-f]{64})$/.test(expectedTreeId)
  ) {
    const cleanup = cleanupMergeWorktree(repo, temporaryPath, state.reviewedMain, state.featureTip);
    const detail = expectedMergeTree.stderr.trim() || `git write-tree exited ${expectedMergeTree.status}`;
    return {
      code: 1,
      out: "",
      err: `worktree merge: could not snapshot temporary merge index tree: ${detail}${cleanup ? `; ${cleanup}` : ""}\n`,
    };
  }

  const committed = git(temporaryPath, ["commit", "-m", `chore(${slug}): merge ${state.branch}`]);
  const mergeCommit = fullHead(temporaryPath);
  const hasExactParents =
    mergeCommit !== null && hasReviewedParents(repo, mergeCommit, state.reviewedMain, state.featureTip);
  const committedTree = mergeCommit === null
    ? null
    : git(temporaryPath, ["rev-parse", "--verify", `${mergeCommit}^{tree}`]);
  const hasExpectedTree =
    committedTree !== null &&
    committedTree.status === 0 &&
    committedTree.stderr.trim() === "" &&
    committedTree.stdout.trim() === expectedTreeId;
  if (committed.status !== 0 || !hasExactParents || mergeCommit === null || !hasExpectedTree) {
    const cleanup = cleanupMergeWorktree(
      repo,
      temporaryPath,
      state.reviewedMain,
      state.featureTip,
      hasExactParents ? mergeCommit : undefined,
    );
    const reason = committed.status !== 0
      ? `git commit failed: ${committed.stderr.trim()}`
      : !hasExactParents || mergeCommit === null
        ? "temporary merge commit does not have the exact reviewed parents"
        : committedTree === null || committedTree.status !== 0 || committedTree.stderr.trim() !== ""
          ? `could not verify temporary merge commit tree: ${committedTree?.stderr.trim() || "git rev-parse failed"}`
          : "temporary merge tree differs from reviewed merge result";
    return { code: 1, out: "", err: `worktree merge: ${reason}${cleanup ? `; ${cleanup}` : ""}\n` };
  }
  const temporaryStatus = worktreeStatus(temporaryPath);
  if (temporaryStatus.detail !== undefined || temporaryStatus.paths.length > 0 || gitOperationState(temporaryPath) !== null) {
    const cleanup = cleanupMergeWorktree(
      repo,
      temporaryPath,
      state.reviewedMain,
      state.featureTip,
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
    const cleanup = cleanupMergeWorktree(
      repo,
      temporaryPath,
      state.reviewedMain,
      state.featureTip,
      mergeCommit,
    );
    return {
      code: 1,
      out: "",
      err:
        `worktree merge: compare-and-swap lost; refs/heads/main changed from ${state.reviewedMain} ` +
        `to ${changedMain ?? "unreadable"}. Preserve the feature worktree and rerun synchronization, affected gates and human review.` +
        `${cleanup ? ` Temporary worktree was preserved: ${cleanup}.` : ""}\n`,
    };
  }

  const refreshed = refreshPrimary(repo, state.reviewedMain);
  if (refreshed !== null) {
    const cleanup = cleanupMergeWorktree(
      repo,
      temporaryPath,
      state.reviewedMain,
      state.featureTip,
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
  const verification = verifyPublishedMerge(
    repo,
    mergeCommit,
    state.reviewedMain,
    state.featureTip,
    state.reviewedFeature,
  );
  if (verification !== null) {
    const cleanup = cleanupMergeWorktree(
      repo,
      temporaryPath,
      state.reviewedMain,
      state.featureTip,
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
    state.featureTip,
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
  const declarationsRead = readDeclarations(root);
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
  const hasWorktreePath = existsSync(entry.path);
  const dropped = hasWorktreePath ? ignoredPaths(entry.path) : [];

  if (hasWorktreePath) {
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

  if (!("detail" in declarationsRead) && declarationsRead.present) {
    const declarations = pruneDeclarations(root, declarationsRead.declarations);
    delete declarations[slug];
    const writeError = writeDeclarations(root, declarations);
    if (writeError !== null) {
      return {
        code: 1,
        out: `✓ removed worktree ${slug}${ignoredRemovalNote(dropped, "removed")}\n`,
        err:
          `worktree rm: the worktree and branch were removed, but the advisory declarations were not updated ` +
          `(${printable(writeError)}).\n`,
      };
    }
  }

  const droppedNote = ignoredRemovalNote(dropped, "removed");
  return {
    code: 0,
    out: force
      ? `✓ removed worktree ${slug} — deleted ${branch} with --force: it was not merged into main${droppedNote}\n`
      : `✓ removed worktree ${slug}${droppedNote}\n`,
    err: "",
  };
}
