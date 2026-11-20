// src/git/lanes.ts — the lane model: one task is one branch, one folder and, when there
// is a forge, one PR. Every lane leaves by one of three doors: it lands on the base, it
// is parked with a reason, or it is dropped into refs/archive/. Nothing here keeps state
// of its own: a lane's state is computed each time from git and the forge, so it cannot
// drift. The forge answer is cached in the git common dir, and only `ai-eng work`
// refreshes it — a session start reads the cache and nothing else.

import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, isAbsolute, join, resolve } from "node:path";
import { loadConfig } from "../env.ts";
import { namedBaseTrackingRef } from "./context.ts";
import { runGit } from "./run.ts";
import { listWorktrees, worktreeStatus } from "./worktree.ts";

const DAY_MS = 24 * 60 * 60 * 1000;
const FORGE_TTL_MS = 10 * 60 * 1000;
/** The git config key a parked branch carries: `<reason>` or `<reason>|<YYYY-MM-DD>`. */
export const PARK_KEY = "aiengparked";
/** The git config key `ai-eng worktree merge` leaves on a branch it merged: the tip it merged. */
export const MERGED_KEY = "aiengmerged";

export type LaneState = "active" | "ready" | "landed" | "parked" | "orphan" | "ghost";

export type PullRequest = { number: number; state: "OPEN" | "MERGED" | "CLOSED"; headRefName: string; headRefOid: string };

/** What git and the forge say about one branch. */
export type BranchFacts = {
  branch: string;
  tip: string;
  lastCommitMs: number;
  /** The worktree that has it checked out, if any. */
  path: string | null;
  isCurrent: boolean;
  dirty: number;
  upstreamGone: boolean;
  /** Reachable from the base: nothing of its own is left outside it. */
  inBase: boolean;
  /** How git proves the branch landed without the forge, or null: see `landingProof`. */
  landing: string | null;
  pr: PullRequest | null;
  parked: { reason: string; until: string | null } | null;
};

export type Lane = { state: LaneState; name: string; path: string | null; detail: string; ageDays: number | null; tip?: string };

/** Pure: one branch's lane, from its facts. `orphanDays` is how long silence lasts. */
export function classify(facts: BranchFacts, now: number, orphanDays: number): Lane {
  const ageDays = Math.floor((now - facts.lastCommitMs) / DAY_MS);
  const lane = (state: LaneState, detail: string): Lane => ({ state, name: facts.branch, path: facts.path, detail, ageDays, tip: facts.tip });
  // Landed only on proof: the forge merged exactly this tip, git can show the base took it,
  // or the base holds it and its remote branch is gone. A branch the base merely contains
  // could be one created a minute ago; that is not a landing.
  if (facts.pr?.state === "MERGED" && facts.pr.headRefOid === facts.tip) return lane("landed", `PR #${facts.pr.number} merged`);
  if (facts.landing !== null) return lane("landed", facts.landing);
  if (facts.inBase && facts.upstreamGone) return lane("landed", "in the base, remote branch gone");
  if (facts.parked !== null) {
    const expired = facts.parked.until !== null && facts.parked.until < new Date(now).toISOString().slice(0, 10);
    if (!expired) return lane("parked", facts.parked.until === null ? facts.parked.reason : `${facts.parked.reason} · until ${facts.parked.until}`);
    return lane("orphan", `parked until ${facts.parked.until}, which has passed: land, park again or drop`);
  }
  if (facts.pr?.state === "OPEN") return lane("ready", `PR #${facts.pr.number} open`);
  const dirty = facts.dirty > 0 ? ` · ${facts.dirty} uncommitted` : "";
  if (facts.isCurrent || facts.dirty > 0 || ageDays < orphanDays) return lane("active", `${facts.path === null ? "no folder" : "checked out"}${dirty}`);
  return lane("orphan", `${ageDays} days without a commit, no PR, not parked${dirty}`);
}

export type Board = {
  repo: string;
  base: string | null;
  lanes: Lane[];
  /** Why the forge column is missing or old, when it is. */
  forgeNote: string | null;
  maxActive: number;
};

export function workSettings(root: string): { maxActive: number; orphanDays: number } {
  const work = loadConfig(root)["work"] ?? {};
  const positive = (value: unknown, fallback: number): number => (typeof value === "number" && Number.isInteger(value) && value > 0 ? value : fallback);
  return { maxActive: positive(work["max_active"], 3), orphanDays: positive(work["orphan_days"], 3) };
}

function git(root: string, args: string[]): string | null {
  const done = runGit(args, { cwd: root, isolated: true });
  return done.status === 0 ? done.stdout : null;
}

function commonDir(root: string): string | null {
  const out = git(root, ["rev-parse", "--git-common-dir"])?.trim();
  if (!out) return null;
  return isAbsolute(out) ? out : resolve(root, out);
}

function forgeCachePath(root: string): string | null {
  const dir = commonDir(root);
  return dir === null ? null : join(dir, "ai-eng", "forge.json");
}

/** The PRs the forge knows, from the cache. `refresh` asks `gh` when the cache is older
 *  than ten minutes; a failed ask keeps the old answer and says so. Never throws. */
export function forgePulls(root: string, refresh: boolean, now: number = Date.now()): { pulls: PullRequest[]; note: string | null } {
  const path = forgeCachePath(root);
  let cached: { ts: number; pulls: PullRequest[] } | null = null;
  try {
    if (path !== null) cached = JSON.parse(readFileSync(path, "utf8")) as { ts: number; pulls: PullRequest[] };
  } catch {
    cached = null;
  }
  const isFresh = cached !== null && now - cached.ts < FORGE_TTL_MS;
  if (!refresh || isFresh) {
    if (cached === null) return { pulls: [], note: "no forge answer cached yet — ai-eng work asks it" };
    return { pulls: cached.pulls, note: isFresh ? null : `forge answer from ${Math.round((now - cached.ts) / 60000)} min ago` };
  }
  const asked = Bun.spawnSync(["gh", "pr", "list", "--state", "all", "--limit", "200", "--json", "number,state,headRefName,headRefOid"], { cwd: root, stdout: "pipe", stderr: "pipe", timeout: 10_000 });
  if (asked.exitCode !== 0) {
    return { pulls: cached?.pulls ?? [], note: "the forge could not be asked (gh missing, offline or not signed in): merged PRs are not seen" };
  }
  try {
    const pulls = JSON.parse(asked.stdout.toString()) as PullRequest[];
    if (path !== null) {
      mkdirSync(dirname(path), { recursive: true });
      writeFileSync(path, JSON.stringify({ ts: now, pulls }));
    }
    return { pulls, note: null };
  } catch {
    return { pulls: cached?.pulls ?? [], note: "the forge answered something that is not a PR list" };
  }
}

/** The tips `ai-eng worktree merge` recorded, by branch. */
function mergedTips(root: string): Map<string, string> {
  const merged = new Map<string, string>();
  for (const line of (git(root, ["config", "--get-regexp", MERGED_KEY]) ?? "").split("\n")) {
    const match = /^branch\.(.+)\.aiengmerged ([0-9a-f]{40,64})$/.exec(line);
    if (match !== null) merged.set(match[1]!, match[2]!);
  }
  return merged;
}

/** The base's own line of commits since `sinceUnix`: what a branch created on the base
 *  points at, and what a merge into the base does not add to. */
function firstParentLine(root: string, baseCommit: string, sinceUnix: number): Set<string> {
  const out = git(root, ["rev-list", "--first-parent", `--since=${sinceUnix}`, baseCommit]) ?? "";
  return new Set(out.split("\n").filter(Boolean));
}

/** Git's own proof that the base took this branch, without asking the forge. Null when
 *  there is none, including for a branch freshly created on the base: it points at a
 *  commit on the base's own line, which no merge produced.
 *  - `ai-eng worktree merge` recorded merging exactly this tip;
 *  - the tip is in the base but off its first-parent line, so a merge commit brought it;
 *  - the branch's whole change, squashed into one commit, is already in the base: a squash
 *    merge. `withSquash` is the human verbs only: it writes one throwaway object per branch. */
export function landingProof(
  root: string,
  branch: { name: string; tip: string; lastCommitUnix: number },
  base: { name: string; commit: string },
  merged: Map<string, string>,
  withSquash: boolean,
): string | null {
  if (merged.get(branch.name) === branch.tip) return "merged by ai-eng worktree merge";
  const mergeBase = git(root, ["merge-base", branch.tip, base.commit])?.trim();
  if (!mergeBase) return null;
  if (mergeBase === branch.tip) {
    // A day of slack: commit dates are the committer's clock, and a merge can be older than its parent.
    const line = firstParentLine(root, base.commit, branch.lastCommitUnix - 86_400);
    return line.has(branch.tip) ? null : `merged into ${base.name}`;
  }
  if (!withSquash) return null;
  const tree = git(root, ["rev-parse", `${branch.tip}^{tree}`])?.trim();
  if (!tree || tree === git(root, ["rev-parse", `${mergeBase}^{tree}`])?.trim()) return null; // no change of its own
  const identity = { GIT_AUTHOR_NAME: "ai-eng", GIT_AUTHOR_EMAIL: "ai-eng@localhost", GIT_COMMITTER_NAME: "ai-eng", GIT_COMMITTER_EMAIL: "ai-eng@localhost" };
  const squash = runGit(["commit-tree", tree, "-p", mergeBase, "-m", "ai-eng landing proof"], { cwd: root, isolated: true, env: identity });
  if (squash.status !== 0) return null;
  // `git cherry` marks with "-" a commit whose change the base already has.
  const cherry = git(root, ["cherry", base.commit, squash.stdout.trim()])?.trim() ?? "";
  return cherry.startsWith("-") ? `squash-merged into ${base.name}` : null;
}

/** Brings the remote branches up to date so a deleted one reads as gone. Best effort with a
 *  ten-second ceiling: offline, unreachable or no remote leaves the board as it was. */
function fetchPrune(root: string): void {
  if ((git(root, ["remote"]) ?? "").trim() === "") return;
  Bun.spawnSync(["git", "fetch", "--prune", "--quiet"], { cwd: root, stdout: "ignore", stderr: "ignore", timeout: 10_000, env: { ...process.env, GIT_TERMINAL_PROMPT: "0" } });
}

function parkedBranches(root: string): Map<string, { reason: string; until: string | null }> {
  const parked = new Map<string, { reason: string; until: string | null }>();
  // A plain word as the pattern: every key holding it, filtered to branch keys below.
  const out = git(root, ["config", "--get-regexp", PARK_KEY]) ?? "";
  for (const line of out.split("\n")) {
    const match = /^branch\.(.+)\.aiengparked (.*)$/.exec(line);
    if (match === null) continue;
    const [reason, until] = (match[2] ?? "").split("|");
    parked.set(match[1]!, { reason: reason || "parked", until: until && /^\d{4}-\d{2}-\d{2}$/.test(until) ? until : null });
  }
  return parked;
}

/** Every lane in the repo: each local branch but the base, every stash entry and every
 *  worktree whose folder is gone. `refresh` lets the forge be asked (a human verb only). */
export function lanes(root: string, opts: { refresh: boolean; now?: number }): Board {
  const now = opts.now ?? Date.now();
  const { maxActive, orphanDays } = workSettings(root);
  if (opts.refresh) fetchPrune(root);
  const tracking = (() => {
    try {
      return namedBaseTrackingRef(root);
    } catch {
      return null;
    }
  })();
  const base = tracking?.base ?? null;
  const baseCommit = tracking?.commit ?? (base === null ? null : git(root, ["rev-parse", "--verify", "--quiet", `refs/heads/${base}`])?.trim() ?? null);
  const forge = forgePulls(root, opts.refresh, now);
  const pullFor = (branch: string, tip: string): PullRequest | null =>
    forge.pulls.find((pull) => pull.headRefName === branch && pull.headRefOid === tip) ?? forge.pulls.find((pull) => pull.headRefName === branch && pull.state === "OPEN") ?? null;
  const parked = parkedBranches(root);
  const merged = mergedTips(root);
  const current = git(root, ["symbolic-ref", "--quiet", "--short", "HEAD"])?.trim() ?? null;
  const listed = listWorktrees(root);
  const worktrees = "worktrees" in listed ? listed.worktrees : [];

  const result: Lane[] = [];
  const refs = git(root, ["for-each-ref", "refs/heads", "--format=%(refname:short)%00%(objectname)%00%(committerdate:unix)%00%(upstream:track)"]) ?? "";
  for (const line of refs.split("\n")) {
    const [branch, tip, unix, track] = line.split("\0");
    if (!branch || !tip || branch === base) continue;
    const worktree = worktrees.find((entry) => entry.branchRef === `refs/heads/${branch}`) ?? null;
    // A session start has 200 ms: it skips the per-folder status, which only tells an
    // active lane with uncommitted work from an orphan — the board a person asks for reads it.
    const status = opts.refresh && worktree !== null && !worktree.prunable ? worktreeStatus(worktree.path) : null;
    const inBase = baseCommit !== null && runGit(["merge-base", "--is-ancestor", tip, baseCommit], { cwd: root, isolated: true }).status === 0;
    const pr = pullFor(branch, tip);
    // The forge already answered for a merged PR: no need to prove it twice.
    const isForgeMerged = pr?.state === "MERGED" && pr.headRefOid === tip;
    const landing = base === null || baseCommit === null || isForgeMerged
      ? null
      : landingProof(root, { name: branch, tip, lastCommitUnix: Number(unix) }, { name: base, commit: baseCommit }, merged, opts.refresh);
    result.push(
      classify(
        {
          branch,
          tip,
          lastCommitMs: Number(unix) * 1000,
          path: worktree?.path ?? null,
          isCurrent: branch === current,
          dirty: status?.paths.length ?? 0,
          upstreamGone: track === "[gone]",
          inBase,
          landing,
          pr,
          parked: parked.get(branch) ?? null,
        },
        now,
        orphanDays,
      ),
    );
  }
  const stashes = git(root, ["stash", "list", "--format=%gd%x00%gs%x00%ct"]) ?? "";
  for (const line of stashes.split("\n")) {
    const [ref, subject, unix] = line.split("\0");
    if (!ref) continue;
    const ageDays = Math.floor((now - Number(unix) * 1000) / DAY_MS);
    result.push({ state: "orphan", name: ref, path: null, detail: `${subject ?? "stash"} — keep it on a branch, or archive it`, ageDays });
  }
  for (const worktree of worktrees.filter((entry) => entry.prunable)) {
    result.push({ state: "ghost", name: worktree.branchRef?.replace("refs/heads/", "") ?? "(detached)", path: worktree.path, detail: "its folder is gone — ai-eng work tidy prunes it", ageDays: null });
  }
  return { repo: root, base, lanes: result, forgeNote: forge.note, maxActive };
}

/** Keeps a branch's tip at refs/archive/<branch>, or refs/archive/<branch>-<date> when that
 *  name is taken. Created, never overwritten. Returns the ref, or null when git refused. */
export function archiveTip(root: string, branch: string, tip: string, now: number = Date.now()): string | null {
  const isTaken = git(root, ["rev-parse", "--verify", "--quiet", `refs/archive/${branch}`]) !== null;
  const archive = isTaken ? `refs/archive/${branch}-${new Date(now).toISOString().slice(0, 10)}` : `refs/archive/${branch}`;
  return runGit(["update-ref", archive, tip, "0".repeat(tip.length)], { cwd: root, isolated: true }).status === 0 ? archive : null;
}

export type Closing = { isClosed: boolean; text: string };

/** Closes a landed lane: its tip goes to refs/archive first, then its folder if clean, then
 *  the branch if it still points at that tip. Never the branch checked out where the closing
 *  runs, never a folder with uncommitted work, never one `isHeldElsewhere` says another
 *  session is writing in. Each refusal keeps everything and says why. */
export function closeLane(root: string, lane: Lane, current: string | null, isHeldElsewhere: (path: string) => boolean = () => false): Closing {
  const kept = (why: string): Closing => ({ isClosed: false, text: `${lane.name} kept — ${why}` });
  if (lane.tip === undefined) return kept("its tip could not be read");
  if (lane.name === current) return kept("it is checked out here; switch to the base, then run tidy again");
  if (lane.path !== null) {
    if (isHeldElsewhere(lane.path)) return kept(`another session is writing in ${lane.path}`);
    const status = worktreeStatus(lane.path);
    if (status.detail !== undefined) return kept(`its folder ${lane.path} could not be read: ${status.detail}`);
    if (status.paths.length > 0) {
      const shown = status.paths.slice(0, 3).join(", ");
      const named = status.paths.length > 3 ? `${shown} and ${status.paths.length - 3} more` : shown;
      return kept(`its folder ${lane.path} has uncommitted work (${named})`);
    }
  }
  const archive = archiveTip(root, lane.name, lane.tip);
  if (archive === null) return kept(`its tip could not be archived under refs/archive/${lane.name}`);
  if (lane.path !== null) {
    const removed = runGit(["worktree", "remove", lane.path], { cwd: root, isolated: true });
    if (removed.status !== 0) return kept(`git worktree remove refused: ${removed.stderr.trim()} (tip kept at ${archive})`);
  }
  const deleted = runGit(["update-ref", "-d", `refs/heads/${lane.name}`, lane.tip], { cwd: root, isolated: true });
  if (deleted.status !== 0) return kept(`it moved since the board read it (tip kept at ${archive})`);
  runGit(["config", "--remove-section", `branch.${lane.name}`], { cwd: root, isolated: true });
  const folder = lane.path === null ? "" : `, and its folder ${lane.path}`;
  return { isClosed: true, text: `${lane.name} removed — ${lane.detail}${folder}; kept at ${archive}` };
}

/** The one line a session start shows; null when nothing needs a decision. */
export function laneSummary(board: Board): string | null {
  const count = (state: LaneState): number => board.lanes.filter((lane) => lane.state === state).length;
  const landed = count("landed");
  const orphans = board.lanes.filter((lane) => lane.state === "orphan");
  const ghosts = count("ghost");
  const active = count("active");
  const parts: string[] = [];
  if (landed > 0) parts.push(`${landed} landed to tidy`);
  if (orphans.length > 0) {
    const oldest = Math.max(...orphans.map((lane) => lane.ageDays ?? 0));
    parts.push(`${orphans.length} orphan${orphans.length === 1 ? "" : "s"} (oldest ${oldest} d)`);
  }
  if (ghosts > 0) parts.push(`${ghosts} ghost worktree${ghosts === 1 ? "" : "s"}`);
  if (active > board.maxActive) parts.push(`${active} active lanes, over the limit of ${board.maxActive}`);
  if (parts.length === 0) return null;
  return `lanes: ${parts.join(", ")} → ai-eng work`;
}
