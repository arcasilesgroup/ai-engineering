// src/shared-worktree.ts — where a worktree lives, what a slug may be, and the git
// argv the `ai-eng worktree` verb runs. It sits in the shared layer because the
// design-slot list is needed by both this verb and `ai-eng spec`, and shared may not
// import spec — so the one definition moves down rather than up (arch.rules.json).
// Every git value is an argv element: no command is ever assembled as a shell string.

import { existsSync, mkdirSync, readFileSync, realpathSync, writeFileSync } from "node:fs";
import { basename, join, resolve } from "node:path";
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

/** Declared files per slug, kept beside the worktrees root — outside the primary
 *  tree, so a session never dirties the checkout, and outside every worktree, so
 *  `git worktree remove` never needs a force and no session tree carries them. */
type Declarations = Record<string, string[]>;

const DECLARATIONS = ".ai-eng-worktrees.json";

/** The declarations the file really holds, or why it cannot be trusted. A file that
 *  is not an object of string arrays is refused rather than believed: `null` throws
 *  on the next read, and a top-level array swallows every key on write. */
function readDeclarations(root: string): { declarations: Declarations } | { detail: string } {
  const path = join(root, DECLARATIONS);
  if (!existsSync(path)) return { declarations: {} };
  let parsed: unknown;
  try {
    parsed = JSON.parse(readFileSync(path, "utf8"));
  } catch (error) {
    return { detail: `${path} is not valid JSON (${error instanceof Error ? error.message : String(error)})` };
  }
  if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
    return { detail: `${path} must hold an object mapping each slug to its declared files` };
  }
  const declarations: Declarations = {};
  for (const [slug, files] of Object.entries(parsed as Record<string, unknown>)) {
    if (!Array.isArray(files) || files.some((file) => typeof file !== "string")) {
      return { detail: `${path} declares "${slug}" as something other than a list of file paths` };
    }
    declarations[slug] = files as string[];
  }
  return { declarations };
}

/** A slug whose worktree is gone declares nothing: the entry is dropped before the
 *  file is written, so a worktree removed outside the verb leaves no declaration. */
function pruneDeclarations(root: string, declarations: Declarations): Declarations {
  const live: Declarations = {};
  for (const [slug, files] of Object.entries(declarations)) {
    if (existsSync(join(root, slug))) live[slug] = files;
  }
  return live;
}

function writeDeclarations(root: string, declarations: Declarations): void {
  mkdirSync(root, { recursive: true });
  writeFileSync(join(root, DECLARATIONS), `${JSON.stringify(declarations, null, 2)}\n`);
}

interface OpenWorktree {
  path: string;
  /** The branch short name, absent when the worktree is detached. */
  branch: string | undefined;
  /** What the user typed: the branch with the `feat/` prefix removed. */
  slug: string;
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
    const branch = ref !== undefined && ref.startsWith("refs/heads/") ? ref.slice("refs/heads/".length) : undefined;
    worktrees.push({ path, branch, slug: branch === undefined ? basename(path) : branch.replace(/^feat\//, "") });
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
  const renamed = record[0] === "R" || record[1] === "R" || record[0] === "C" || record[1] === "C";
  if (!renamed) return { paths: [path], next: index + 1 };
  const source = tokens[index + 1];
  if (source === undefined || source === "") return null;
  return { paths: [path, source], next: index + 2 };
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

export function worktreeNew(slug: string, files: string[]): WorktreeResult {
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
  const read = readDeclarations(root);
  if ("detail" in read) {
    return {
      code: 2,
      out: "",
      err: `worktree new: the declarations file is unusable (${read.detail}) — refusing to cut a worktree while the declarations are unknown.\n`,
    };
  }
  const declarations = pruneDeclarations(root, read.declarations);

  const listed = openWorktrees(repo);
  if ("detail" in listed) {
    return {
      code: 2,
      out: "",
      err: `worktree new: the worktree list is unreadable (${listed.detail}) — refusing to cut a worktree blindly.\n`,
    };
  }
  const overlaps = listed.worktrees
    .filter((entry) => canonicalize(entry.path) !== repo)
    .flatMap((entry) =>
      (declarations[entry.slug] ?? [])
        .filter((file) => files.includes(file))
        .map((file) => `${entry.slug} already declared ${file}`),
    );

  const target = join(root, slug);
  const branch = `feat/${slug}`;
  mkdirSync(root, { recursive: true });
  const added = git(repo, ["worktree", "add", target, "-b", branch, "refs/heads/main"]);
  if (added.status !== 0) {
    return { code: 1, out: "", err: `worktree new: git worktree add failed: ${added.stderr.trim()}\n` };
  }
  git(repo, ["config", `branch.${branch}.remote`, "."]);
  git(repo, ["config", `branch.${branch}.merge`, "refs/heads/main"]);
  if (files.length > 0) declarations[slug] = files;
  writeDeclarations(root, declarations);

  return {
    code: 0,
    out: `✓ worktree ${slug} → ${target}\n`,
    err: overlaps.length > 0 ? `worktree new: overlap — ${overlaps.join("; ")}\n` : "",
  };
}

export function worktreeList(): WorktreeResult {
  const repo = primaryRepoRoot();
  if (repo === null) return { code: 2, out: "", err: "worktree list: not inside a git repository.\n" };
  const listed = openWorktrees(repo);
  if ("detail" in listed) {
    return { code: 2, out: "", err: `worktree list: the worktree list is unreadable (${listed.detail}).\n` };
  }
  const out = listed.worktrees
    .filter((entry) => canonicalize(entry.path) !== repo)
    .map((entry) => `${entry.slug}\t${entry.path}`)
    .join("\n");
  return { code: 0, out: out.length > 0 ? `${out}\n` : "", err: "" };
}

export function worktreeRm(slug: string): WorktreeResult {
  const repo = primaryRepoRoot();
  if (repo === null) return { code: 2, out: "", err: "worktree rm: not inside a git repository.\n" };
  const root = worktreeRoot(repo);
  const read = readDeclarations(root);
  if ("detail" in read) {
    return {
      code: 2,
      out: "",
      err: `worktree rm: the declarations file is unusable (${read.detail}) — refusing to rewrite it blindly.\n`,
    };
  }
  const listed = openWorktrees(repo);
  if ("detail" in listed) {
    return { code: 2, out: "", err: `worktree rm: the worktree list is unreadable (${listed.detail}).\n` };
  }
  const entry = listed.worktrees.find(
    (candidate) => candidate.slug === slug && canonicalize(candidate.path) !== repo,
  );
  if (!entry) return { code: 1, out: "", err: `worktree rm: no open worktree for slug "${printable(slug)}".\n` };

  if (existsSync(entry.path)) {
    const removed = git(repo, ["worktree", "remove", entry.path]);
    if (removed.status !== 0) {
      return { code: 1, out: "", err: `worktree rm: git worktree remove failed: ${removed.stderr.trim()}\n` };
    }
  } else {
    // The directory is gone: prune the stale registration instead of failing on it.
    git(repo, ["worktree", "prune"]);
  }
  const branch = entry.branch;
  if (branch === undefined) {
    return { code: 1, out: "", err: `worktree rm: the worktree for slug "${slug}" is detached — refusing to guess a branch to delete.\n` };
  }
  const deleted = git(repo, ["branch", "-D", branch]);
  if (deleted.status !== 0) {
    return { code: 1, out: "", err: `worktree rm: git branch -D failed: ${deleted.stderr.trim()}\n` };
  }

  const declarations = pruneDeclarations(root, read.declarations);
  delete declarations[slug];
  writeDeclarations(root, declarations);
  return { code: 0, out: `✓ removed worktree ${slug}\n`, err: "" };
}
