#!/usr/bin/env node
// ai-git-cleanup - read-only survey and triage of local branches and worktrees.
// Emits ONE JSON document on stdout and never mutates the repository: everything
// git can already prove runs here deterministically; judgment calls (squash merges,
// supersession) belong to the read-only investigators the skill spawns in the main
// session. Fail-closed by construction: any git command that misbehaves moves the
// branch to unanalyzed, never to a delete plan.

import { spawnSync } from "node:child_process";

// Long-lived integration branches are never deletable. A regex, not an instruction
// to a model: an agent can be talked out of a rule, a regex cannot.
const PROTECTED =
  /^(main|master|trunk|develop|dev|integration|staging|production|preprod|qa|uat|next|canary|stable)$|^(release|hotfix|support|maint)[-/]/i;

// Fallback default-branch guesses, consulted only when origin/HEAD is missing or
// points at a branch this repository does not have.
const KNOWN_DEFAULTS = ["main", "master", "trunk", "develop", "dev"];

function runGit(args, cwd) {
  // GIT_TERMINAL_PROMPT=0: a credential prompt must fail the command, not hang the run.
  return spawnSync("git", args, {
    cwd,
    encoding: "utf8",
    env: { ...process.env, GIT_TERMINAL_PROMPT: "0" },
  });
}

function fail(message) {
  console.error(message);
  process.exit(1);
}

// Git refname rules allow every shell metacharacter ('$(...)', backticks, ;, |, &),
// so emitted commands only ever paste names single-quoted; an apostrophe escapes by
// closing and reopening the quote.
function shellQuote(value) {
  return `'${value.replaceAll("'", "''")}'`;
}

// origin/HEAD and friends arrive as refs; classification compares local short names.
function normalizeLocalBranch(raw, remotes) {
  if (!raw) return "";
  if (raw.startsWith("refs/heads/")) return raw.slice("refs/heads/".length);
  if (raw.startsWith("refs/remotes/")) {
    const rest = raw.slice("refs/remotes/".length);
    const slash = rest.indexOf("/");
    return slash === -1 ? "" : rest.slice(slash + 1);
  }
  const slash = raw.indexOf("/");
  if (slash > 0 && remotes.includes(raw.slice(0, slash))) return raw.slice(slash + 1);
  return raw;
}

// Two branches cluster when one name extends the other at a word boundary: a shared
// first segment alone ("feature/api" vs "feature/login") never clusters. Components
// tie siblings transitively, so feature/api-v2 clusters with feature/api even though
// the two names are not prefixes of each other.
function buildClusters(names) {
  const parent = new Map(names.map((name) => [name, name]));
  const find = (name) => {
    let root = name;
    while (parent.get(root) !== root) root = parent.get(root);
    return root;
  };
  const linked = (a, b) =>
    a === b ||
    b.startsWith(`${a}-`) ||
    b.startsWith(`${a}/`) ||
    a.startsWith(`${b}-`) ||
    a.startsWith(`${b}/`);
  for (let i = 0; i < names.length; i += 1) {
    for (let j = i + 1; j < names.length; j += 1) {
      if (linked(names[i], names[j])) parent.set(find(names[i]), find(names[j]));
    }
  }
  const groups = new Map();
  for (const name of names) {
    const root = find(name);
    if (!groups.has(root)) groups.set(root, []);
    groups.get(root).push(name);
  }
  const clusterOf = new Map();
  for (const members of groups.values()) {
    if (members.length < 2) continue; // a lone branch has no group to display
    const id = [...members].sort((a, b) => a.length - b.length || a.localeCompare(b))[0];
    for (const member of members) clusterOf.set(member, id);
  }
  return clusterOf;
}

function main() {
  const repo = process.argv[2] ?? process.cwd();

  const probe = runGit(["rev-parse", "--git-dir"], repo);
  if (probe.error || probe.status !== 0) fail(`error: ${repo} is not a git repository`);

  const remotes = runGit(["remote"], repo)
    .stdout.split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
  // Best-effort prune before origin/HEAD is read: stale remote-tracking refs must not
  // decide the default branch, and a dead or absent origin skips cleanly.
  if (remotes.includes("origin")) runGit(["fetch", "--prune", "origin"], repo);

  const inventory = runGit(
    ["for-each-ref", "--format=%(refname:short)%09%(objectname)%09%(upstream:short)%09%(upstream:track)", "refs/heads"],
    repo,
  );
  if (inventory.status !== 0) {
    fail(`error: ref inventory failed${inventory.stderr ? `: ${inventory.stderr.trim()}` : ""}`);
  }
  // git hides broken refs behind a warning and exits 0: a partial inventory must
  // never read as a complete one, so every branch drops to unanalyzed instead.
  const brokenRefs = [...inventory.stderr.matchAll(/ignoring broken ref (\S+)/g)].map((match) =>
    normalizeLocalBranch(match[1], remotes),
  );
  const isInventoryComplete = brokenRefs.length === 0;

  const rows = inventory.stdout
    .split("\n")
    .filter(Boolean)
    .map((line) => {
      const [branch, sha, upstream, track] = line.split("\t");
      return { branch, sha, upstream: upstream ?? "", track: track ?? "" };
    });

  const head = runGit(["symbolic-ref", "--quiet", "--short", "HEAD"], repo);
  const currentBranch = head.status === 0 ? head.stdout.trim() : "";

  const originHead = runGit(["symbolic-ref", "--quiet", "refs/remotes/origin/HEAD"], repo);
  const originDefault =
    originHead.status === 0 ? normalizeLocalBranch(originHead.stdout.trim(), remotes) : "";
  const localNames = new Set(rows.map((row) => row.branch));
  // The checked-out branch is never an anchor: with HEAD on a feature branch over
  // an unchanged custom default it would declare the true default deletable. With
  // no origin/HEAD and no known default name, defaultBranch stays "" and every
  // branch fails closed to NO_DEFAULT_BRANCH instead of guessing.
  const defaultBranch =
    [originDefault, ...KNOWN_DEFAULTS].find((name) => name && localNames.has(name)) ?? "";

  // A git command that fails (or a missing default anchor) yields null: the caller
  // moves the branch to unanalyzed rather than guessing.
  const countCommits = (args) => {
    const result = runGit(args, repo);
    return result.status === 0 ? Number(result.stdout.trim()) : null;
  };

  const deleteCandidates = [];
  const needsReview = [];
  const keep = [];
  const unanalyzed = [];

  for (const row of rows) {
    const { branch, sha, upstream, track } = row;
    const tip = sha.slice(0, 12);

    if (!isInventoryComplete) {
      unanalyzed.push({ branch, reason: "INVENTORY_INCOMPLETE", evidence: "ref inventory skipped a broken ref" });
      continue;
    }
    if (PROTECTED.test(branch)) {
      keep.push({ branch, reason: "PROTECTED", evidence: `protected name; tip ${tip}` });
      continue;
    }
    if (defaultBranch && branch === defaultBranch) {
      keep.push({ branch, reason: "DEFAULT_BRANCH", evidence: `repository default branch; tip ${tip}` });
      continue;
    }
    if (upstream && track.includes("[gone]")) {
      needsReview.push({
        branch,
        reason: "REMOTE_GONE",
        evidence: `upstream ${upstream} is [gone]; work not proven merged`,
      });
      continue;
    }
    if (upstream) {
      // --left-right on branch...upstream: left column = local only (ahead), right = remote only.
      const counts = runGit(["rev-list", "--left-right", "--count", `${branch}...${upstream}`], repo);
      if (counts.status !== 0) {
        unanalyzed.push({ branch, reason: "UPSTREAM_COUNT_FAILED", evidence: `could not count commits vs ${upstream}` });
        continue;
      }
      const [ahead, behind] = counts.stdout.trim().split("\t").map((value) => Number(value));
      if (ahead > 0) {
        keep.push({ branch, reason: "UNPUSHED_WORK", evidence: `${ahead} unpushed commit(s) ahead of ${upstream}` });
      } else {
        keep.push({ branch, reason: "SYNCED_WITH_REMOTE", evidence: `ahead 0 (behind ${behind}) vs live upstream ${upstream}` });
      }
      continue;
    }
    if (!defaultBranch) {
      unanalyzed.push({ branch, reason: "NO_DEFAULT_BRANCH", evidence: "no default branch to measure against" });
      continue;
    }
    const unique = countCommits(["rev-list", "--count", `${defaultBranch}..${branch}`]);
    if (unique === null) {
      unanalyzed.push({ branch, reason: "REVISION_COUNT_FAILED", evidence: `could not count commits vs ${defaultBranch}` });
      continue;
    }
    if (unique > 0) {
      keep.push({ branch, reason: "LOCAL_WORK", evidence: `${unique} commit(s) not in ${defaultBranch}` });
      continue;
    }
    if (branch === currentBranch) {
      keep.push({ branch, reason: "CURRENT_BRANCH", evidence: "checked out in this worktree; tip " + tip });
      continue;
    }
    // The ancestry guard gate 2 runs again immediately before the delete. It names
    // refs/heads/<branch> rather than the reported sha, so it cannot pass on a stale
    // or transposed commit while the branch itself was never merged.
    const guard = runGit(["merge-base", "--is-ancestor", `refs/heads/${branch}`, defaultBranch], repo);
    if (guard.status === 0) {
      deleteCandidates.push({
        branch,
        reason: "SAFE_TO_DELETE",
        evidence: `tip ${tip} is an ancestor of ${defaultBranch}`,
        command: `git branch -d ${shellQuote(branch)}`,
        verifyWith: `git merge-base --is-ancestor ${shellQuote(`refs/heads/${branch}`)} ${shellQuote(defaultBranch)}`,
      });
    } else {
      // Not ancestor with zero unique commits should be unreachable; anything else is
      // a failed proof. Fail closed: investigate, never delete.
      unanalyzed.push({ branch, reason: "MERGE_PROOF_INCONCLUSIVE", evidence: `merge-base against ${defaultBranch} failed` });
    }
  }

  const worktreeList = runGit(["worktree", "list", "--porcelain"], repo);
  if (worktreeList.status !== 0) fail("error: worktree inventory failed");
  const worktrees = [];
  let current = null;
  for (const line of worktreeList.stdout.split("\n")) {
    if (line.startsWith("worktree ")) {
      if (current) worktrees.push(current);
      current = { path: line.slice("worktree ".length), branch: "" };
    } else if (line.startsWith("branch ") && current) {
      current.branch = normalizeLocalBranch(line.slice("branch ".length), remotes);
    } else if (line.trim() === "" && current) {
      worktrees.push(current);
      current = null;
    }
  }
  if (current) worktrees.push(current);

  const deletable = new Set(deleteCandidates.map((entry) => entry.branch));
  const worktreeEntries = worktrees.map((entry) => {
    const status = runGit(["-C", entry.path, "status", "--porcelain"], repo);
    // An unreadable worktree counts as dirty: refuse rather than queue it for removal.
    const dirtyFiles = status.status === 0 ? status.stdout.split("\n").filter(Boolean) : [];
    const dirty = status.status !== 0 || dirtyFiles.length > 0;
    const stale = !dirty && deletable.has(entry.branch);
    const result = { path: entry.path, branch: entry.branch, dirty, dirtyFiles, stale };
    if (stale) result.command = `git worktree remove ${shellQuote(entry.path)}`;
    return result;
  });

  const clusterOf = buildClusters(rows.map((row) => row.branch));
  for (const entry of [...deleteCandidates, ...needsReview, ...keep]) {
    const cluster = clusterOf.get(entry.branch);
    if (cluster) entry.cluster = cluster;
  }
  for (const entry of deleteCandidates) {
    const held = worktreeEntries.find((worktree) => worktree.branch === entry.branch);
    if (held) entry.worktreePath = held.path;
  }
  for (const ref of brokenRefs) {
    unanalyzed.push({ branch: ref, reason: "BROKEN_REF", evidence: "ref file does not hold a sha" });
  }

  const report = {
    defaultBranch,
    currentBranch,
    deleteCandidates,
    needsReview,
    keep,
    worktrees: worktreeEntries,
    unanalyzed,
  };
  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
}

try {
  main();
} catch (error) {
  fail(`error: ${error instanceof Error ? error.message : String(error)}`);
}
