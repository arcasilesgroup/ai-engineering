// `ai-eng work` — the lane board, and the three doors out of it. `tidy` removes only what
// is provably landed, `park` marks a branch with a reason (and a date), `drop` keeps the
// tip in refs/archive/ before the branch goes. Every write is a compare-and-swap on the
// tip the board saw, never --force, and a folder with uncommitted work is never removed.

import { repoRoot } from "../env.ts";
import { lanes, PARK_KEY, type Board, type Lane, type LaneState } from "../git/lanes.ts";
import { runGit } from "../git/run.ts";
import { worktreeStatus } from "../git/worktree.ts";
import { readLease, releaseLease } from "../guards/lease.ts";

const USAGE =
  "usage: ai-eng work [--json] | tidy | park <branch> <reason> [--until YYYY-MM-DD] | resume <branch> | drop <branch> | release\n";

const ORDER: LaneState[] = ["active", "ready", "parked", "landed", "orphan", "ghost"];

function git(root: string, args: string[]): { ok: boolean; out: string } {
  const done = runGit(args, { cwd: root, isolated: true });
  return { ok: done.status === 0, out: `${done.stdout}${done.stderr}`.trim() };
}

export function renderBoard(board: Board): string {
  const count = (state: LaneState): number => board.lanes.filter((lane) => lane.state === state).length;
  const totals = ORDER.filter((state) => count(state) > 0).map((state) => `${count(state)} ${state}`);
  const lines = [`${board.repo} · base ${board.base ?? "(none named)"} · ${totals.length > 0 ? totals.join(" · ") : "no lanes"}`, ""];
  const width = Math.max(0, ...board.lanes.map((lane) => lane.name.length));
  for (const state of ORDER) {
    for (const lane of board.lanes.filter((entry) => entry.state === state)) {
      const age = lane.ageDays === null ? "" : `${lane.ageDays} d  `;
      lines.push(`${state.padEnd(7)}  ${lane.name.padEnd(width)}  ${age}${lane.detail}`);
    }
  }
  if (board.lanes.length > 0) lines.push("");
  lines.push(`active lanes: ${count("active")}/${board.maxActive}`);
  if (board.forgeNote !== null) lines.push(`forge: ${board.forgeNote}`);
  const next = nextStep(board);
  if (next !== null) lines.push(next);
  return `${lines.join("\n")}\n`;
}

function nextStep(board: Board): string | null {
  if (board.lanes.some((lane) => lane.state === "landed" || lane.state === "ghost")) return "next: ai-eng work tidy — removes what has landed and the ghost worktrees";
  if (board.lanes.some((lane) => lane.state === "orphan")) return "next: decide each orphan — land it (open a PR), park it with a reason, or drop it";
  return null;
}

/** Remove one landed lane: its worktree when clean, then its branch only if its tip is
 *  still the one the board saw. The checked-out branch of this checkout stays. */
function tidyLane(root: string, lane: Lane, current: string | null): string {
  if (lane.name === current) return `· ${lane.name} kept — it is checked out here; switch to the base, then run tidy again`;
  if (lane.path !== null) {
    const status = worktreeStatus(lane.path);
    if (status.detail !== undefined || status.paths.length > 0) return `· ${lane.name} kept — its folder ${lane.path} has uncommitted work`;
    const removed = git(root, ["worktree", "remove", lane.path]);
    if (!removed.ok) return `· ${lane.name} kept — git worktree remove refused: ${removed.out}`;
  }
  const deleted = git(root, ["update-ref", "-d", `refs/heads/${lane.name}`, lane.tip ?? ""]);
  if (!deleted.ok) return `· ${lane.name} kept — it moved since the board read it`;
  git(root, ["config", "--remove-section", `branch.${lane.name}`]);
  return `✓ ${lane.name} removed — ${lane.detail}${lane.path === null ? "" : `, and its folder ${lane.path}`}`;
}

function tidy(root: string): number {
  const board = lanes(root, { refresh: true });
  const current = git(root, ["symbolic-ref", "--quiet", "--short", "HEAD"]).out || null;
  const lines = board.lanes.filter((lane) => lane.state === "landed").map((lane) => tidyLane(root, lane, current));
  if (board.lanes.some((lane) => lane.state === "ghost")) {
    const pruned = git(root, ["worktree", "prune"]);
    lines.push(pruned.ok ? "✓ ghost worktrees pruned" : `· ghost worktrees kept — git worktree prune: ${pruned.out}`);
  }
  if (lines.length === 0) lines.push("nothing has landed — nothing to tidy");
  if (board.forgeNote !== null) lines.push(`forge: ${board.forgeNote}`);
  process.stdout.write(`${lines.join("\n")}\n`);
  return 0;
}

function branchTip(root: string, branch: string): string | null {
  const tip = git(root, ["rev-parse", "--verify", "--quiet", `refs/heads/${branch}^{commit}`]);
  return tip.ok && tip.out !== "" ? tip.out : null;
}

function park(root: string, branch: string, reason: string, until: string | undefined): number {
  if (branchTip(root, branch) === null) return fail(`there is no branch ${branch}`);
  if (reason.trim() === "" || reason.includes("|")) return fail("park needs a reason, without |: ai-eng work park <branch> \"waiting for the API\"");
  if (until !== undefined && !/^\d{4}-\d{2}-\d{2}$/.test(until)) return fail(`--until takes a date as YYYY-MM-DD, not "${until}"`);
  const lane = lanes(root, { refresh: false }).lanes.find((entry) => entry.name === branch);
  // Parking is a decision about committed work: what is uncommitted would sit in a folder
  // nobody watches. Commit it on the branch first; stash is never the answer.
  if (lane?.path) {
    const status = worktreeStatus(lane.path);
    if (status.paths.length > 0) return fail(`${branch} has uncommitted work in ${lane.path} — commit it on the branch (git commit -m "wip: …"), then park`);
  }
  const value = until === undefined ? reason.trim() : `${reason.trim()}|${until}`;
  const set = git(root, ["config", `branch.${branch}.${PARK_KEY}`, value]);
  if (!set.ok) return fail(`could not record the park: ${set.out}`);
  process.stdout.write(`✓ ${branch} parked — ${reason.trim()}${until === undefined ? "" : ` · until ${until}`}\n`);
  return 0;
}

function resume(root: string, branch: string): number {
  if (branchTip(root, branch) === null) return fail(`there is no branch ${branch}`);
  git(root, ["config", "--unset", `branch.${branch}.${PARK_KEY}`]);
  process.stdout.write(`✓ ${branch} is active again\n`);
  return 0;
}

/** Drop: the tip goes to refs/archive/<branch> (created, never overwritten), then the
 *  folder if clean, then the branch if it still points at that tip. */
function drop(root: string, branch: string): number {
  const tip = branchTip(root, branch);
  if (tip === null) return fail(`there is no branch ${branch}`);
  const current = git(root, ["symbolic-ref", "--quiet", "--short", "HEAD"]).out;
  if (current === branch) return fail(`${branch} is checked out here — switch to the base first`);
  const lane = lanes(root, { refresh: false }).lanes.find((entry) => entry.name === branch);
  if (lane?.path) {
    const status = worktreeStatus(lane.path);
    if (status.detail !== undefined || status.paths.length > 0) return fail(`${branch} has uncommitted work in ${lane.path} — commit it on the branch first, then drop`);
  }
  const date = new Date().toISOString().slice(0, 10);
  const isTaken = git(root, ["rev-parse", "--verify", "--quiet", `refs/archive/${branch}`]).ok;
  const archive = isTaken ? `refs/archive/${branch}-${date}` : `refs/archive/${branch}`;
  const archived = git(root, ["update-ref", archive, tip, "0".repeat(tip.length)]);
  if (!archived.ok) return fail(`could not archive ${branch} at ${archive}: ${archived.out}`);
  if (lane?.path) {
    const removed = git(root, ["worktree", "remove", lane.path]);
    if (!removed.ok) return fail(`archived at ${archive}, but git worktree remove refused: ${removed.out}`);
  }
  const deleted = git(root, ["update-ref", "-d", `refs/heads/${branch}`, tip]);
  if (!deleted.ok) return fail(`archived at ${archive}, but ${branch} moved meanwhile — kept`);
  git(root, ["config", "--remove-section", `branch.${branch}`]);
  process.stdout.write(`✓ ${branch} dropped — kept at ${archive}; bring it back with: git branch ${branch} ${archive}\n`);
  return 0;
}

function fail(message: string): number {
  process.stderr.write(`work: ${message}\n`);
  return 2;
}

export function workMain(args: string[], flags: { json?: boolean; until?: string }): number {
  const root = repoRoot();
  if (root === null) return fail("not inside a git repository");
  const [action, branch, ...rest] = args;
  switch (action) {
    case undefined: {
      const board = lanes(root, { refresh: true });
      process.stdout.write(flags.json === true ? `${JSON.stringify(board, null, 2)}\n` : renderBoard(board));
      return 0;
    }
    case "tidy":
      return branch === undefined ? tidy(root) : fail(USAGE.trim());
    case "park":
      return branch === undefined || rest.length !== 1 ? fail(USAGE.trim()) : park(root, branch, rest[0] ?? "", flags.until);
    case "resume":
      return branch === undefined || rest.length > 0 ? fail(USAGE.trim()) : resume(root, branch);
    case "drop":
      return branch === undefined || rest.length > 0 ? fail(USAGE.trim()) : drop(root, branch);
    case "release": {
      if (branch !== undefined) return fail(USAGE.trim());
      const held = readLease(root);
      if (held === null) {
        process.stdout.write(`nothing to release — no session holds ${root}\n`);
        return 0;
      }
      releaseLease(root);
      process.stdout.write(`✓ ${root} released — it was held by session ${held.session.slice(0, 8)}; the next session to write here holds it\n`);
      return 0;
    }
    default:
      return fail(USAGE.trim());
  }
}
