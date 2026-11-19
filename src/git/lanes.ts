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
  pr: PullRequest | null;
  parked: { reason: string; until: string | null } | null;
};

export type Lane = { state: LaneState; name: string; path: string | null; detail: string; ageDays: number | null; tip?: string };

/** Pure: one branch's lane, from its facts. `orphanDays` is how long silence lasts. */
export function classify(facts: BranchFacts, now: number, orphanDays: number): Lane {
  const ageDays = Math.floor((now - facts.lastCommitMs) / DAY_MS);
  const lane = (state: LaneState, detail: string): Lane => ({ state, name: facts.branch, path: facts.path, detail, ageDays, tip: facts.tip });
  // Landed only on proof: the forge merged exactly this tip, or the base already holds it
  // and its remote branch is gone. A branch the base merely contains could be one
  // created a minute ago; that is not a landing.
  if (facts.pr?.state === "MERGED" && facts.pr.headRefOid === facts.tip) return lane("landed", `PR #${facts.pr.number} merged`);
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
          pr: pullFor(branch, tip),
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
