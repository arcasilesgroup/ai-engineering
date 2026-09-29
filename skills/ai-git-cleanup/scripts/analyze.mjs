#!/usr/bin/env node
// ai-git-cleanup - read-only engine for the action-first v3 flow: a phase-0 migration
// plan, deterministic branch classification, the one delete batch and report data.
// Emits ONE JSON document on stdout and never mutates the repository: every command
// below is plan data the skill executes later under its single confirmation. Fail-closed
// by construction: any git command that misbehaves keeps the branch (KEEP/unanalyzed),
// never queues it for deletion.

import { spawnSync } from "node:child_process";
import { realpathSync } from "node:fs";

// Long-lived integration branches are never deletable. A regex, not an instruction
// to a model: an agent can be talked out of a rule, a regex cannot.
const PROTECTED =
  /^(main|master|trunk|develop|dev|integration|staging|production|preprod|qa|uat|next|canary|stable)$|^(release|hotfix|support|maint)[-/]/i;

// Fallback default-branch guesses, consulted only when origin/HEAD is missing or
// points at a branch this repository does not have. Never HEAD (R3/L16): anchoring
// the default on the checkout would make the true default a delete candidate.
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
  // Mode flag (--all default) plus the historical positional repo path: the flag names
  // which sections the document carries so every field is machine-assertable in its
  // exact mode instead of a consumer filtering prose.
  const MODES = new Set(["--sync", "--branches", "--all"]);
  let mode = "--all";
  const positional = [];
  for (const arg of process.argv.slice(2)) {
    if (MODES.has(arg)) mode = arg;
    else if (arg.startsWith("--")) fail(`error: unknown option ${arg}`);
    else positional.push(arg);
  }
  const repo = positional[0] ?? process.cwd();
  const wantsMigration = mode !== "--branches";
  const wantsClassification = mode !== "--sync";

  const probe = runGit(["rev-parse", "--git-dir"], repo);
  if (probe.error || probe.status !== 0) fail(`error: ${repo} is not a git repository`);

  const remotes = runGit(["remote"], repo)
    .stdout.split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
  // Best-effort prune before origin/HEAD is read: stale remote-tracking refs must not
  // decide the default branch. The outcome travels as fetchStatus so consumers can show
  // a failed fetch instead of silently leaving remote-derived state stale; with no origin
  // nothing remote-derived can be stale, so the status is ok without a fetch.
  const hasOrigin = remotes.includes("origin");
  let fetchStatus = "ok";
  if (hasOrigin) {
    const fetched = runGit(["fetch", "--prune", "origin"], repo);
    if (fetched.status !== 0) {
      const firstStderrLine = (fetched.stderr ?? "")
        .split("\n")
        .map((line) => line.trim())
        .find((line) => line.length > 0);
      fetchStatus = `failed: ${firstStderrLine ?? `git fetch exited ${fetched.status}`}`;
    }
  }

  const inventory = runGit(
    ["for-each-ref", "--format=%(refname:short)%09%(objectname)%09%(upstream:short)%09%(upstream:track)", "refs/heads"],
    repo,
  );
  if (inventory.status !== 0) {
    fail(`error: ref inventory failed${inventory.stderr ? `: ${inventory.stderr.trim()}` : ""}`);
  }
  // git hides broken refs behind a warning and exits 0: a partial inventory must never
  // read as a complete one, so every branch keeps (never gains) a delete plan instead.
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
  // With no origin/HEAD and no known default name, defaultBranch stays "" and every
  // branch fails closed to NO_DEFAULT_BRANCH instead of guessing (R3/L16).
  const defaultBranch =
    [originDefault, ...KNOWN_DEFAULTS].find((name) => name && localNames.has(name)) ?? "";

  // Ahead/behind vs a live upstream, cached per branch: report rows always carry the
  // counts and the tracked triage reuses the same numbers. A missing ref (gone or
  // broken remote) yields null — never a fabricated count.
  const countsCache = new Map();
  const upstreamCounts = (row) => {
    if (!row.upstream) return null;
    if (countsCache.has(row.branch)) return countsCache.get(row.branch);
    const result = runGit(["rev-list", "--left-right", "--count", `${row.branch}...${row.upstream}`], repo);
    const value =
      result.status === 0
        ? (() => {
            const [ahead, behind] = result.stdout.trim().split("\t").map(Number);
            return { ahead, behind };
          })()
        : null;
    countsCache.set(row.branch, value);
    return value;
  };

  // The main worktree's dirtiness decides the phase-0 stash step; an unreadable status
  // counts as dirty (stash conservatively rather than switch over unknown work).
  const status = runGit(["status", "--porcelain"], repo);
  const mainDirtyFiles = status.status === 0 ? status.stdout.split("\n").filter(Boolean) : [];
  const mainDirty = status.status !== 0 || mainDirtyFiles.length > 0;

  // ---- classification (branches/all modes) ----
  const clusterOf = buildClusters(rows.map((row) => row.branch));
  const batch = [];
  const keep = [];
  const unanalyzed = [];
  const decisions = new Map(); // branch -> { action, reason } for the report rows
  const worktreeEntries = [];
  const heldDirty = new Map(); // branch -> linked-worktree path, a protection filter input

  const classify = (branch, action, reason, evidence, extra = {}) => {
    // Single choke point for the checked-out protection (R3/L18): every classification
    // path funnels through here, so the current branch never reaches the batch as -d/-D
    // from any category, and never surfaces as the review-ambiguous REMOTE_GONE keep.
    // Work-safety keeps (unpushed/synced/local) report their own actionable reason.
    if (branch === currentBranch && (action !== "keep" || reason === "REMOTE_GONE")) {
      return classify(branch, "keep", "CURRENT_BRANCH", `checked out in this worktree; ${evidence}`);
    }
    const entry = { branch, ...extra, category: extra.category ?? reason, action, evidence };
    if (action === "keep") {
      entry.reason = reason;
      delete entry.action;
      delete entry.category;
      keep.push(entry);
      decisions.set(branch, { action: "keep", reason });
      return entry;
    }
    batch.push(entry);
    decisions.set(branch, { action, reason });
    return entry;
  };
  const park = (branch, reason, evidence) => {
    unanalyzed.push({ branch, reason, evidence });
    decisions.set(branch, { action: "keep", reason });
  };

  let mergedSet = null;
  if (wantsClassification) {
    // Linked worktrees are inventoried before triage: a dirty worktree's branch is a
    // protection-filter input (never batched), while a clean stale one is batched WITH
    // its worktreePath so the one ask can remove the worktree first.
    const worktreeList = runGit(["worktree", "list", "--porcelain"], repo);
    if (worktreeList.status !== 0) fail("error: worktree inventory failed");
    const parsed = [];
    let current = null;
    for (const line of worktreeList.stdout.split("\n")) {
      if (line.startsWith("worktree ")) {
        if (current) parsed.push(current);
        current = { path: line.slice("worktree ".length), branch: "" };
      } else if (line.startsWith("branch ") && current) {
        current.branch = normalizeLocalBranch(line.slice("branch ".length), remotes);
      } else if (line.trim() === "" && current) {
        parsed.push(current);
        current = null;
      }
    }
    if (current) parsed.push(current);
    // macOS: /var is a symlink into /private/var and `git worktree list` reports the
    // resolved path, while callers (tmpdir references, the repo argument) hold the
    // logical one. Emit the logical form when it names the same directory (L14: the
    // batch back-link must equal caller-held paths); a genuine /private/... tree has
    // no logical counterpart, so it keeps the resolved path.
    const logicalPath = (worktreePath) => {
      if (!worktreePath.startsWith("/private/")) return worktreePath;
      const candidate = worktreePath.slice("/private".length);
      try {
        return realpathSync(candidate) === worktreePath ? candidate : worktreePath;
      } catch {
        return worktreePath;
      }
    };
    for (const entry of parsed) {
      entry.path = logicalPath(entry.path);
      const wtStatus = runGit(["-C", entry.path, "status", "--porcelain"], repo);
      // An unreadable worktree counts as dirty: refuse rather than queue it for removal.
      const dirtyFiles = wtStatus.status === 0 ? wtStatus.stdout.split("\n").filter(Boolean) : [];
      const dirty = wtStatus.status !== 0 || dirtyFiles.length > 0;
      const record = { ...entry, dirty, dirtyFiles, requiresAcknowledgment: dirty };
      worktreeEntries.push(record);
      // The main worktree holds the current branch by definition; its own dirtiness is
      // the stash step's concern, not a hold — only linked worktrees hold branches.
      if (dirty && record.branch && record.branch !== currentBranch) {
        heldDirty.set(record.branch, record.path);
      }
    }

    if (defaultBranch) {
      const merged = runGit(["branch", "--merged", defaultBranch], repo);
      mergedSet =
        merged.status === 0
          ? new Set(
              merged.stdout
                .split("\n")
                // Markers are not part of refnames: "* name" is the current branch and
                // "+ name" a branch held by a linked worktree. Stripping only "*"
                // dropped worktree-held merged branches from this set, sending the
                // central worktree case down the empty-diff path instead of MERGED.
                .map((line) => line.trim().replace(/^[*+]\s*/, ""))
                .filter(Boolean),
            )
          : null;
    }

    for (const row of rows) {
      const { branch, sha, upstream, track } = row;
      const tip = sha.slice(0, 12);
      const gone = Boolean(upstream) && track.includes("[gone]");

      // Fail-closed gate first: a partial inventory cannot prove anything (the test
      // pins INVENTORY_INCOMPLETE even for the default branch).
      if (!isInventoryComplete) {
        classify(branch, "keep", "INVENTORY_INCOMPLETE", "ref inventory skipped a broken ref");
        continue;
      }
      // Protection filters run before every categorization path (R3/L18): the default,
      // protected names and dirty-worktree-held branches never reach a batch entry.
      if (defaultBranch && branch === defaultBranch) {
        classify(branch, "keep", "DEFAULT_BRANCH", `repository default branch; tip ${tip}`);
        continue;
      }
      if (PROTECTED.test(branch)) {
        classify(branch, "keep", "PROTECTED", `protected name; tip ${tip}`);
        continue;
      }
      const heldPath = heldDirty.get(branch);
      if (heldPath !== undefined) {
        classify(branch, "keep", "WORKTREE_HELD", `held by dirty worktree ${heldPath}`);
        continue;
      }
      if (!defaultBranch) {
        park(branch, "NO_DEFAULT_BRANCH", "no default branch to measure against");
        continue;
      }
      if (mergedSet === null) {
        park(branch, "MERGED_LIST_FAILED", `could not list branches merged into ${defaultBranch}`);
        continue;
      }
      // Checked-out protection is the classify() choke point (R3/L18): it stops every
      // delete-bound path below, while work-safety keeps (tracked/local) reach their
      // own actionable reason.
      if (mergedSet.has(branch)) {
        // The guard the ask's executor re-runs immediately before the delete names
        // refs/heads/<branch> and the default explicitly, so it cannot pass on a
        // stale or transposed commit (R4). Bundled into the one runnable command.
        classify(branch, "-d", "MERGED", `tip ${tip} is an ancestor of ${defaultBranch}`, {
          command:
            `git merge-base --is-ancestor ${shellQuote(`refs/heads/${branch}`)} ${shellQuote(defaultBranch)}` +
            ` && git branch -d ${shellQuote(branch)}`,
        });
        continue;
      }
      // Tree-identical (squash twin): the tip is not an ancestor but the branch holds no
      // content the default lacks — -D, with the [gone] state named in the evidence.
      const diff = runGit(["diff", "--quiet", `${defaultBranch}..${branch}`], repo);
      if (diff.status !== 0 && diff.status !== 1) {
        park(branch, "DIFF_FAILED", `could not diff ${branch} against ${defaultBranch}`);
        continue;
      }
      if (diff.status === 0) {
        const evidence = gone ? "[gone] + empty diff" : "empty diff vs default";
        classify(branch, "-D", gone ? "GONE_EMPTY" : "EMPTY_DIFF", evidence, {
          command: `git branch -D ${shellQuote(branch)}`,
        });
        continue;
      }
      if (gone) {
        classify(branch, "keep", "REMOTE_GONE", `upstream ${upstream} is [gone]; work not proven merged`);
        continue;
      }
      if (upstream) {
        const counts = upstreamCounts(row);
        if (counts === null) {
          park(branch, "UPSTREAM_COUNT_FAILED", `could not count commits vs ${upstream}`);
        } else if (counts.ahead > 0) {
          classify(branch, "keep", "UNPUSHED_WORK", `${counts.ahead} unpushed commit(s) ahead of ${upstream}`);
        } else {
          classify(
            branch,
            "keep",
            "SYNCED_WITH_REMOTE",
            `ahead 0 (behind ${counts.behind}) vs live upstream ${upstream}`,
          );
        }
        continue;
      }
      const unique = (() => {
        const result = runGit(["rev-list", "--count", `${defaultBranch}..${branch}`], repo);
        return result.status === 0 ? Number(result.stdout.trim()) : null;
      })();
      if (unique === null) {
        park(branch, "REVISION_COUNT_FAILED", `could not count commits vs ${defaultBranch}`);
      } else if (unique > 0) {
        classify(branch, "keep", "LOCAL_WORK", `${unique} commit(s) not in ${defaultBranch}`);
      } else {
        // Zero unique commits but a non-empty diff contradicts the merged list above:
        // inconsistent git state, so fail closed instead of guessing a bucket.
        park(branch, "CLASSIFICATION_INCONCLUSIVE", `diff vs ${defaultBranch} non-empty with 0 unique commits`);
      }
    }

    // Broken refs are surfaced, never silently dropped (they are not in the inventory
    // rows, so this cannot duplicate a classified entry).
    for (const ref of brokenRefs) {
      park(ref, "BROKEN_REF", "ref file does not hold a sha");
    }

    // Stale = clean worktree whose branch reached the batch: the ask orders the removal
    // before the branch delete. Dirty worktrees never queue (requiresAcknowledgment).
    for (const record of worktreeEntries) {
      const queued = batch.some((entry) => entry.branch === record.branch);
      if (queued && !record.dirty) {
        record.stale = true;
        record.command = `git worktree remove ${shellQuote(record.path)}`;
      } else {
        record.stale = false;
      }
    }
    // Back-link (L14): the batch candidate names the worktree entry the ask must
    // remove first — batched branches are held only by clean (stale) worktrees,
    // because a dirty-held branch never reached the batch above.
    for (const entry of batch) {
      const held = worktreeEntries.find((worktree) => worktree.branch === entry.branch);
      if (held) entry.worktreePath = held.path;
    }
    for (const entry of [...batch, ...keep, ...unanalyzed]) {
      const cluster = clusterOf.get(entry.branch);
      if (cluster) entry.cluster = cluster;
    }
  }

  // ---- migration plan (sync/all modes): plan data only, executed later by phase 0 ----
  // The one identity shared between the stash command and report.stashState: the report
  // names the exact stash this run's plan will create (digits-only, so no quoting).
  const stashMessage = `cleanup-auto-stash-${Date.now()}`;
  let migration;
  if (wantsMigration) {
    migration = { previousBranch: currentBranch, defaultBranch };
    if (defaultBranch) {
      // Steps appear in execution order. Stash first: uncommitted work must be safe
      // before the checkout moves.
      if (mainDirty) {
        migration.stash = {
          command: `git stash push -m ${stashMessage}`,
          warn: "WARN: stash push failed — stop and secure the uncommitted work manually before switching",
        };
      }
      migration.switch = {
        command: `git switch ${shellQuote(defaultBranch)}`,
        warn: "WARN: git switch failed — HEAD is not on the default branch; resolve the checkout before continuing",
      };
      // Pull pinned to the default branch as destination via the preceding switch,
      // never "HEAD-ambiguous" (R4/L17). Emitted only when the default is actually
      // behind its live upstream (decide-and-log: no pull to run when there is nothing
      // to fast-forward to); a failure WARNs and cleanup continues (assumption).
      const defaultRow = rows.find((row) => row.branch === defaultBranch);
      const counts = defaultRow ? upstreamCounts(defaultRow) : null;
      if (defaultRow && counts && counts.behind > 0) {
        const remote = defaultRow.upstream.split("/")[0];
        migration.pull = {
          command: `git pull --ff-only ${shellQuote(remote)} ${shellQuote(defaultBranch)}`,
          warn: "WARN: pull failed (offline or diverged) — continue cleanup against the local default branch",
        };
      }
      if (mainDirty) {
        migration.pop = {
          command: "git stash pop",
          warn: "WARN: stash pop failed (conflict) — the stash is left in place; inspect it with git stash list",
        };
      }
    }
  }

  // ---- assembled document ----
  const doc = { fetchStatus, defaultBranch };
  if (wantsMigration) doc.migration = migration;
  if (wantsClassification) {
    doc.batch = batch;
    doc.keep = keep;
    doc.unanalyzed = unanalyzed;
    doc.worktrees = worktreeEntries;
    // Prune exists only when a worktree removal is queued — a branch-only batch has
    // no worktree admin to clean, so the section is absent rather than empty.
    if (worktreeEntries.some((entry) => entry.stale === true)) {
      doc.postCleanup = { prune: "git worktree prune" };
    }
    doc.report = {
      previousBranch: currentBranch,
      // The auto-stash this document's migration plan will create, else none: report
      // describes this run, and --branches carries no stash step at all.
      stashState: migration?.stash ? stashMessage : "none",
      branches: rows.map((row) => {
        const decision = decisions.get(row.branch) ?? { action: "keep", reason: "UNCLASSIFIED" };
        const counts = upstreamCounts(row);
        return {
          branch: row.branch,
          action: decision.action,
          reason: decision.reason,
          upstream: row.upstream,
          ahead: counts?.ahead ?? null,
          behind: counts?.behind ?? null,
        };
      }),
    };
  }
  process.stdout.write(`${JSON.stringify(doc, null, 2)}\n`);
}

try {
  main();
} catch (error) {
  fail(`error: ${error instanceof Error ? error.message : String(error)}`);
}
