// src/shared-worktree.ts — where a worktree lives, what a slug may be, and the git
// argv the `ai-eng worktree` verb runs. It sits in the shared layer because the
// design-slot list is needed by both this verb and `ai-eng spec`, and shared may not
// import spec — so the one definition moves down rather than up (arch.rules.json).
// Every git value is an argv element: no command is ever assembled as a shell string.

import { existsSync, mkdirSync, readFileSync, realpathSync, writeFileSync } from "node:fs";
import { basename, join, resolve } from "node:path";
import { spawnSync } from "node:child_process";
import { loadConfig, repoRoot } from "./env.ts";

/** The four artifacts of a milestone. `spec open` scaffolds two and `spec close`
 *  sweeps all four; `ai-eng spec` is its only consumer. */
export const SLOT_FILES = ["spec.html", "plan.html", "brainstorm.html", "recap.html"] as const;

/** The design artifacts that must be committed before a worktree is cut
 *  (AGENTS.md `## Git workflow`). `recap.html` is absent on purpose: it is
 *  generated at the app review and arrives with the merge, so a dirty one must
 *  not block. One definition here, distinct from the `spec close` sweep. */
export const PRE_WORKTREE_SLOTS = ["brainstorm.html", "spec.html", "plan.html"] as const;

/** The slug is both the branch name and the worktree directory name, and the
 *  orchestrator compares it literally against `<meta name="ai-feature">`. */
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

function canonicalRepoRoot(): string | null {
  const root = repoRoot();
  return root === null ? null : canonicalize(root);
}

/** `<repo>.worktrees` beside the repository, or `[git].worktrees_dir` from the
 *  invoked repo's `.ai-engineering/config.toml` when that key is present. */
export function worktreeRoot(repo: string): string {
  const configured = loadConfig().git?.["worktrees_dir"];
  if (typeof configured === "string" && configured.trim()) return canonicalize(configured.trim());
  return `${repo}.worktrees`;
}

/** Declared files per slug, kept beside the worktrees — the worktrees themselves
 *  stay clean, so `git worktree remove` never needs a force. */
type Declarations = Record<string, string[]>;

const DECLARATIONS = ".ai-eng-worktrees.json";

function readDeclarations(root: string): Declarations {
  const path = join(root, DECLARATIONS);
  if (!existsSync(path)) return {};
  try {
    return JSON.parse(readFileSync(path, "utf8")) as Declarations;
  } catch {
    return {};
  }
}

function writeDeclarations(root: string, declarations: Declarations): void {
  mkdirSync(root, { recursive: true });
  writeFileSync(join(root, DECLARATIONS), `${JSON.stringify(declarations, null, 2)}\n`);
}

interface OpenWorktree {
  path: string;
  slug: string;
}

function openWorktrees(repo: string): OpenWorktree[] {
  const listed = git(repo, ["worktree", "list", "--porcelain"]);
  if (listed.status !== 0) return [];
  const entries: OpenWorktree[] = [];
  for (const block of listed.stdout.split("\n\n")) {
    const lines = block.split("\n");
    const pathLine = lines.find((line) => line.startsWith("worktree "));
    if (!pathLine) continue;
    const path = pathLine.slice("worktree ".length);
    const branch = lines.find((line) => line.startsWith("branch "))?.slice("branch ".length);
    entries.push({ path, slug: branch === undefined ? basename(path) : branch.replace(/^refs\/heads\//, "") });
  }
  return entries;
}

/** The first design slot with an uncommitted change in the primary tree, or null. */
function dirtySlot(repo: string): string | null {
  // `-uall` lists each untracked file instead of collapsing a wholly untracked
  // directory to `?? .ai-engineering/`, so an uncommitted slot is still seen.
  const status = git(repo, ["status", "--porcelain", "-uall"]);
  if (status.status !== 0) return null;
  for (const line of status.stdout.split("\n")) {
    if (line.length < 4) continue;
    const path = line.slice(3).replace(/^"(.*)"$/, "$1");
    const slot = PRE_WORKTREE_SLOTS.find((name) => path === `.ai-engineering/${name}`);
    if (slot) return slot;
  }
  return null;
}

export function worktreeNew(slug: string, files: string[]): WorktreeResult {
  const repo = canonicalRepoRoot();
  if (repo === null) return { code: 2, out: "", err: "worktree new: not inside a git repository.\n" };
  if (!SLUG_PATTERN.test(slug)) {
    return {
      code: 2,
      out: "",
      err: `worktree new: invalid slug "${slug}" — it must match ${SLUG_PATTERN} (no spaces, no "/", never starting with a separator).\n`,
    };
  }
  const dirty = dirtySlot(repo);
  if (dirty !== null) {
    return {
      code: 2,
      out: "",
      err: `worktree new: .ai-engineering/${dirty} has uncommitted changes in the primary tree — commit the design slot before opening a worktree.\n`,
    };
  }

  const root = worktreeRoot(repo);
  const target = join(root, slug);
  const declarations = readDeclarations(root);
  const overlaps = openWorktrees(repo)
    .filter((entry) => entry.path !== repo)
    .flatMap((entry) =>
      (declarations[entry.slug] ?? [])
        .filter((file) => files.includes(file))
        .map((file) => `${entry.slug} already declared ${file}`),
    );

  mkdirSync(root, { recursive: true });
  const added = git(repo, ["worktree", "add", target, "-b", slug, "main"]);
  if (added.status !== 0) {
    return { code: 1, out: "", err: `worktree new: git worktree add failed: ${added.stderr.trim()}\n` };
  }
  git(repo, ["config", `branch.${slug}.remote`, "."]);
  git(repo, ["config", `branch.${slug}.merge`, "refs/heads/main"]);
  if (files.length > 0) declarations[slug] = files;
  writeDeclarations(root, declarations);

  return {
    code: 0,
    out: `✓ worktree ${slug} → ${target}\n`,
    err: overlaps.length > 0 ? `worktree new: overlap — ${overlaps.join("; ")}\n` : "",
  };
}

export function worktreeList(): WorktreeResult {
  const repo = canonicalRepoRoot();
  if (repo === null) return { code: 2, out: "", err: "worktree list: not inside a git repository.\n" };
  const out = openWorktrees(repo)
    .filter((entry) => canonicalize(entry.path) !== repo)
    .map((entry) => `${entry.slug}\t${entry.path}`)
    .join("\n");
  return { code: 0, out: out.length > 0 ? `${out}\n` : "", err: "" };
}

export function worktreeRm(slug: string): WorktreeResult {
  const repo = canonicalRepoRoot();
  if (repo === null) return { code: 2, out: "", err: "worktree rm: not inside a git repository.\n" };
  const entry = openWorktrees(repo).find((candidate) => candidate.slug === slug && candidate.path !== repo);
  if (!entry) return { code: 1, out: "", err: `worktree rm: no open worktree for slug "${slug}".\n` };

  if (existsSync(entry.path)) {
    const removed = git(repo, ["worktree", "remove", entry.path]);
    if (removed.status !== 0) {
      return { code: 1, out: "", err: `worktree rm: git worktree remove failed: ${removed.stderr.trim()}\n` };
    }
  } else {
    // The directory is gone: prune the stale registration instead of failing on it.
    git(repo, ["worktree", "prune"]);
  }
  const deleted = git(repo, ["branch", "-D", slug]);
  if (deleted.status !== 0) {
    return { code: 1, out: "", err: `worktree rm: git branch -D failed: ${deleted.stderr.trim()}\n` };
  }

  const root = worktreeRoot(repo);
  const declarations = readDeclarations(root);
  if (declarations[slug] !== undefined) {
    delete declarations[slug];
    writeDeclarations(root, declarations);
  }
  return { code: 0, out: `✓ removed worktree ${slug}\n`, err: "" };
}
